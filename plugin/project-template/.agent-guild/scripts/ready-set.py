#!/usr/bin/env python3
"""The host-neutral computation of which tasks are ready to dispatch right
now, as one wave.

    .agent-guild/scripts/ready-set.py [STATE_DIR] [--running T-NNN ...]

STATE_DIR defaults to the repo's `.agent-guild/state` (this script's own
grandparent directory plus `state/`). `--running`, repeatable-by-space, names
task ids the caller has already dispatched—typically the ids behind
stop-gate.py's fresh in-flight markers.

This is a pure function of the task files under STATE_DIR/tasks/*.md plus
the supplied --running list. It deliberately does NOT read the in-flight
marker directory itself: the caller supplies what is running, which is what
lets a Claude host and a Codex host compute identical wave decisions from
identical inputs. "Helpfully" falling back to reading markers here would
reintroduce exactly the host-specific drift this script exists to remove.

Emits one JSON object on stdout with four keys, in this order:

    wave      — tasks to dispatch as executors right now, each
                {"id", "agent" (the task's `executor`), "reason"}.
    checks    — checker fan-outs due now: every task at `needs-check`, each
                {"id", "agent" (the task's `checker`), "reason"}.
    deferred  — tasks held back, each {"id", "reason"}. A reason is one of:
                "unmet deps: ..." (naming each unmet dep and its status),
                "owns overlap with T-NNN" (naming the task it collides
                with), or "spent retry budget: retries=N max_retries=M".
    attention — tasks needing a human/orchestrator judgment call, each
                {"id", "reason"}: a `disputed` task, or a task whose `deps`
                names an `abandoned` task (waiting it out can never
                resolve, so it's never just "unmet"—it's escalated
                straight past `deferred`).

A task counted in --running is excluded from `wave` and from every other
bucket—the caller already knows it's in flight, so it would be redundant
data, not new information. Only `pending` tasks are wave candidates.
`rework` is deliberately never one: the retry ladder requires the
orchestrator to copy the checker's diagnosis, increment `retries`, and move
the task to `assigned` before it's legal to dispatch (dispatch-guard.py
refuses a worker on anything else), so offering a `rework` task in the wave
would invite skipping those steps. A `rework` task therefore never appears
in `wave`, `deferred`, or `attention`—the caller's own `_next_move`-style
per-task advice is what owns it, same as `assigned`/`checking` tasks
(already dispatched, per the caller's own bookkeeping), which also don't
appear anywhere in this output—the caller's existing mid-flight/stale-marker
logic still owns those.

Determinism is a hard requirement: same inputs always produce the same
output, key order included. Every bucket is sorted ascending by numeric
task id. Where two dep-free candidates overlap in `owns`, exactly one goes
in the wave and the other defers—the one processed first in ascending id
order wins, so T-002 beats T-010.

Exit codes: 0, a set was computed (possibly all-empty buckets, including
when STATE_DIR/tasks/ doesn't exist—no job active is not an error). 3,
infrastructure trouble: a task file that can't be read, or whose
frontmatter can't be parsed, or is missing one of the required keys (id,
status, retries, deps, executor, checker), or whose `id` duplicates one
already declared by an earlier file—reported on stderr, prefixed
`ready-set: `, naming the file(s). A task silently skipped here is a task
nobody would ever dispatch, so this fails loud rather than dropping it.

Imports `paths_overlap` from check-diff-scope.py via the `_load_module`
idiom check-job-spec.py already uses for the same import, rather than
reimplementing ownership-overlap semantics a third time.

Stdlib only, so the kit stays copy-in portable.
"""
import argparse
import glob
import importlib.util
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(name, filename):
    path = os.path.join(SCRIPT_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paths_overlap = _load_module(
    "check_diff_scope_module_scope", "check-diff-scope.py"
).paths_overlap


DEFAULT_MAX_RETRIES = 2
REQUIRED_KEYS = ("id", "status", "retries", "deps", "executor", "checker")
TASK_FILENAME_RE = re.compile(r"^T-\d+\.md$")

_KEY_RE = re.compile(r"^([A-Za-z0-9_]+):\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^\s+-\s+(.*)$")
_ID_NUM_RE = re.compile(r"^T-(\d+)$")


class TaskParseError(Exception):
    """A task file could not be trusted enough to compute a ready set
    from—raised instead of returning a partial/best-guess result, per this
    script's fail-loud contract."""


def _coerce(val):
    """A frontmatter value: an inline `[a, b]` list, or a scalar with
    matching quotes stripped. Mirrors hooks/_lib.py's `_coerce`, kept as a
    separate copy here (not imported) so scripts/ stays independent of
    hooks/—the same posture every other script in this directory takes."""
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip("'\"") for x in inner.split(",")]
    return val.strip("'\"")


def parse_task_frontmatter(text, path):
    """Parse a task file's leading `--- ... ---` block. Handles scalars,
    inline `[a, b]` lists, and block `- item` list continuations—the two
    shapes `deps` and `owns` actually appear in. Deliberately narrower than
    hooks/_lib.py's parser: no block-scalar (`|`/`>`) decoding, because
    ready-set.py never reads a block-scalar field (check_method is the only
    one any task carries, and it isn't read here). A block scalar's
    indented body lines simply fail to match any key or list-item pattern
    and are skipped—harmless, since nothing here consumes them.

    Raises TaskParseError, naming `path`, if the opening or closing '---'
    delimiter is missing—the one failure mode that leaves the result
    genuinely untrustworthy rather than just incomplete.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise TaskParseError(
            f"{path}: missing opening '---' frontmatter delimiter"
        )
    fm = {}
    key = None  # the key a following '- item' line would extend
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        m = _LIST_ITEM_RE.match(line)
        if m and key is not None:
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(m.group(1).strip().strip("'\""))
            continue
        m = _KEY_RE.match(line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if v == "":
                fm[k] = ""
                key = k
            else:
                fm[k] = _coerce(v)
                key = None
        # else: a block scalar's body line, or blank—ignored (see docstring)
    if not closed:
        raise TaskParseError(
            f"{path}: missing closing '---' frontmatter delimiter"
        )
    return fm


def _as_list(val):
    """"" (an fm key present with a blank scalar and no following '- item'
    lines—an empty `deps:`/`owns:`) is the same as []; anything else that
    isn't already a list is a caller error."""
    if val == "":
        return []
    return val


def read_task(path):
    """Parse one task file into the flat dict compute_ready_set() needs.
    Raises TaskParseError—naming `path` and the specific defect—for
    anything unreadable, unparseable, or missing a required key."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise TaskParseError(f"{path}: cannot read: {e}")

    fm = parse_task_frontmatter(text, path)

    missing = [k for k in REQUIRED_KEYS if k not in fm]
    if missing:
        raise TaskParseError(
            f"{path}: missing required frontmatter field(s): "
            f"{', '.join(missing)}"
        )

    try:
        retries = int(str(fm["retries"]).strip())
    except (ValueError, TypeError):
        raise TaskParseError(f"{path}: retries is not an integer: {fm['retries']!r}")

    deps = _as_list(fm["deps"])
    if not isinstance(deps, list):
        raise TaskParseError(f"{path}: deps is not a list: {fm['deps']!r}")

    owns = _as_list(fm.get("owns", []))
    if not isinstance(owns, list):
        raise TaskParseError(f"{path}: owns is not a list: {fm.get('owns')!r}")

    max_retries_raw = fm.get("max_retries", DEFAULT_MAX_RETRIES)
    if max_retries_raw == "":
        max_retries_raw = DEFAULT_MAX_RETRIES
    try:
        max_retries = int(str(max_retries_raw).strip())
    except (ValueError, TypeError):
        raise TaskParseError(
            f"{path}: max_retries is not an integer: {fm.get('max_retries')!r}"
        )

    return {
        "id": str(fm["id"]).strip(),
        "status": str(fm["status"]).strip(),
        "retries": retries,
        "deps": deps,
        "owns": owns,
        "executor": str(fm["executor"]).strip(),
        "checker": str(fm["checker"]).strip(),
        "max_retries": max_retries,
    }


def _sort_key(tid):
    """Ascending numeric order for T-NNN ids (T-002 before T-010), falling
    back to plain string order for anything that doesn't match the shape—
    so a malformed id sorts last and deterministically rather than
    crashing the whole computation."""
    m = _ID_NUM_RE.match(tid)
    if m:
        return (0, int(m.group(1)), tid)
    return (1, 0, tid)


def load_tasks(state_dir):
    """{id: task dict} for every T-NNN.md under state_dir/tasks/, loaded
    regardless of status—dep resolution needs to see complete/abandoned
    tasks too, not just the open ones.

    A state dir with no tasks/ subdir is no job active, which is not an
    error: {}. A state dir that isn't there at all is a different animal,
    and it exits 3. Both would otherwise print an empty wave, and a caller
    reading that JSON cannot tell "nothing is ready" from "I was pointed at
    the wrong path"—which is the same silent-drop failure the per-file exit
    3 below exists to prevent, just one directory up.

    Keying on frontmatter `id` rather than filename means two files can
    declare the same id—a copy-paste of a task file that forgot to update
    its own `id:` line, say. Silently letting the second one overwrite the
    first in this dict would make the earlier file (and whatever task it
    actually names) vanish from every bucket with no error anywhere: a task
    nobody would ever dispatch, and nothing on stderr to explain why. That's
    exactly the silent-skip this module's fail-loud contract exists to rule
    out, so a repeated id raises TaskParseError naming both files instead.
    """
    if not os.path.isdir(state_dir):
        raise TaskParseError(f"state dir does not exist: {state_dir}")
    tasks_dir = os.path.join(state_dir, "tasks")
    if not os.path.isdir(tasks_dir):
        return {}
    tasks = {}
    sources = {}  # id -> path that first declared it, for the duplicate error
    for name in sorted(os.listdir(tasks_dir)):
        if not TASK_FILENAME_RE.match(name):
            continue
        path = os.path.join(tasks_dir, name)
        t = read_task(path)
        tid = t["id"]
        if tid in tasks:
            raise TaskParseError(
                f"{path}: id {tid!r} is already declared by {sources[tid]}—"
                "two task files cannot share one id"
            )
        tasks[tid] = t
        sources[tid] = path
    return tasks


def _owns_overlap(owns_a, owns_b):
    """True if any entry in owns_a overlaps any entry in owns_b. A task
    with no declared owns can't collide with anything and can't be
    collided into—there's nothing here for another task's diff to step
    on."""
    if not owns_a or not owns_b:
        return False
    return any(paths_overlap(a, b) for a in owns_a for b in owns_b)


def compute_ready_set(tasks, running):
    """The four buckets, computed from `tasks` ({id: task dict}, as
    load_tasks() returns) and `running` (an iterable of task ids the
    caller already has in flight)."""
    running = set(running)
    ids_sorted = sorted(tasks.keys(), key=_sort_key)

    attention = []
    for tid in ids_sorted:
        if tid in running:
            continue
        if tasks[tid]["status"] == "disputed":
            attention.append(
                (
                    tid,
                    "disputed: worker filed a dispute; rule on it and set "
                    "the task to complete or rework",
                )
            )

    wave = []
    wave_owns = []  # [(tid, owns)] already placed, in placement order
    deferred = []

    for tid in ids_sorted:
        t = tasks[tid]
        # rework is deliberately excluded from wave candidacy (see the
        # module docstring): the retry ladder requires the orchestrator to
        # do the diagnosis-copy/retries-increment/assigned steps first, and
        # a rework task offered here would invite skipping them straight
        # into a dispatch-guard refusal.
        if t["status"] != "pending":
            continue
        if tid in running:
            continue

        abandoned_deps = sorted(
            (d for d in t["deps"] if d in tasks and tasks[d]["status"] == "abandoned"),
            key=_sort_key,
        )
        if abandoned_deps:
            attention.append(
                (tid, f"depends on abandoned task(s): {', '.join(abandoned_deps)}")
            )
            continue

        if t["retries"] >= t["max_retries"]:
            deferred.append(
                (
                    tid,
                    f"spent retry budget: retries={t['retries']} "
                    f"max_retries={t['max_retries']}",
                )
            )
            continue

        unmet = [
            f"{d} ({tasks[d]['status'] if d in tasks else 'unknown'})"
            for d in t["deps"]
            if d not in tasks or tasks[d]["status"] != "complete"
        ]
        if unmet:
            deferred.append((tid, f"unmet deps: {', '.join(unmet)}"))
            continue

        collision = None
        for other_tid, other_owns in wave_owns:
            if _owns_overlap(t["owns"], other_owns):
                collision = other_tid
                break
        if collision is None:
            for rtid in sorted(running, key=_sort_key):
                if rtid in tasks and _owns_overlap(t["owns"], tasks[rtid]["owns"]):
                    collision = rtid
                    break
        if collision is not None:
            deferred.append((tid, f"owns overlap with {collision}"))
            continue

        wave.append(
            {
                "id": tid,
                "agent": t["executor"],
                "reason": "deps complete, no owns overlap, retry budget available",
            }
        )
        wave_owns.append((tid, t["owns"]))

    checks = [
        {
            "id": tid,
            "agent": tasks[tid]["checker"],
            "reason": "worker finished; checker of record is owed",
        }
        for tid in ids_sorted
        if tasks[tid]["status"] == "needs-check" and tid not in running
    ]

    deferred_sorted = sorted(deferred, key=lambda pair: _sort_key(pair[0]))
    attention_sorted = sorted(attention, key=lambda pair: _sort_key(pair[0]))

    return {
        "wave": wave,
        "checks": checks,
        "deferred": [{"id": tid, "reason": reason} for tid, reason in deferred_sorted],
        "attention": [{"id": tid, "reason": reason} for tid, reason in attention_sorted],
    }


def _default_state_dir():
    # This file lives at .agent-guild/scripts/ready-set.py, so the repo
    # root's .agent-guild/state is two directories up from here plus
    # 'state'—the same copy-in-kit assumption check-diff-scope.py and its
    # siblings make (see this module's own SCRIPT_DIR).
    return os.path.join(os.path.dirname(SCRIPT_DIR), "state")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Compute the host-neutral ready-to-dispatch task wave."
    )
    ap.add_argument(
        "state_dir",
        nargs="?",
        default=None,
        metavar="STATE_DIR",
        help="defaults to the repo's .agent-guild/state",
    )
    ap.add_argument(
        "--running",
        nargs="*",
        default=[],
        metavar="T-NNN",
        help="task ids the caller already has dispatched (repeatable)",
    )
    args = ap.parse_args(argv)

    state_dir = args.state_dir if args.state_dir is not None else _default_state_dir()

    try:
        tasks = load_tasks(state_dir)
    except TaskParseError as e:
        sys.stderr.write(f"ready-set: {e}\n")
        return 3

    result = compute_ready_set(tasks, args.running)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
