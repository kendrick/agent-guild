#!/usr/bin/env python3
"""Fixture-based tests for ready-set.py. Every fixture is a scratch
`state/tasks/` directory in a fresh temp dir, and the script runs as a
subprocess so these tests exercise the real CLI contract (exit codes,
stdout JSON)—matching test_check_diff_scope.py's approach for its sibling
script.

Run: python3 .agent-guild/scripts/test_ready_set.py
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPTS_DIR, "ready-set.py")

sys.path.insert(0, SCRIPTS_DIR)
from _corpus import ARCHIVE_117, add_owns  # noqa: E402

passed = failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {label}")
    else:
        failed += 1
        print(f"  FAIL {label}  {detail}")


def write_task(
    state_dir,
    tid,
    status="pending",
    deps=(),
    owns=(),
    executor="worker-standard",
    checker="checker-deterministic",
    retries=0,
    max_retries=2,
):
    """A minimal but complete task fixture—every field ready-set.py
    requires, in the flat `--- ... ---` frontmatter shape real task files
    use."""
    deps_str = "[" + ", ".join(deps) + "]"
    owns_str = "[" + ", ".join(owns) + "]"
    content = (
        "---\n"
        f"id: {tid}\n"
        f"status: {status}\n"
        f"retries: {retries}\n"
        f"deps: {deps_str}\n"
        f"owns: {owns_str}\n"
        f"executor: {executor}\n"
        f"checker: {checker}\n"
        f"max_retries: {max_retries}\n"
        "---\n\n## Spec excerpt\n\nFixture body.\n"
    )
    tasks_dir = os.path.join(state_dir, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    path = os.path.join(tasks_dir, f"{tid}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def run_script(state_dir, *extra_argv):
    proc = subprocess.run(
        [sys.executable, SCRIPT, state_dir, *extra_argv],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_and_parse(state_dir, *extra_argv):
    rc, out, err = run_script(state_dir, *extra_argv)
    try:
        return rc, json.loads(out), err
    except json.JSONDecodeError:
        return rc, None, err


def ids(entries):
    return [e["id"] for e in entries]


# --------------------------------------- 1. two dep-free disjoint tasks (headline)
print("two dep-free disjoint tasks land in ONE wave")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["file-a.py"])
    write_task(d, "T-002", owns=["file-b.py"])
    rc, result, err = run_and_parse(d)
    check("headline: exit 0", rc == 0, f"rc={rc} err={err}")
    check(
        "headline: both land in the SAME wave call",
        ids(result["wave"]) == ["T-001", "T-002"],
        result,
    )
    check("headline: nothing deferred", result["deferred"] == [], result)
    check("headline: nothing needs attention", result["attention"] == [], result)

# --------------------------------------------------- 2. owns overlap defers
print("owns overlap defers the higher-numbered task, naming the collision")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-002", owns=["shared/"])
    write_task(d, "T-010", owns=["shared/file.py"])
    rc, result, err = run_and_parse(d)
    check("overlap: exit 0", rc == 0, f"rc={rc} err={err}")
    check("overlap: lower id wins the wave", ids(result["wave"]) == ["T-002"], result)
    check(
        "overlap: higher id defers",
        ids(result["deferred"]) == ["T-010"],
        result,
    )
    check(
        "overlap: reason names the colliding task",
        "T-002" in result["deferred"][0]["reason"],
        result["deferred"],
    )
    check(
        "overlap: kind is owns",
        result["deferred"][0]["kind"] == "owns",
        result["deferred"],
    )

# ------------------------------------- 2b. undeclared owns never shares a wave
# #162: `owns: []` is what templates/task.md ships and what new-task.py
# stamps, so undeclared is the DEFAULT state of a fresh task. Reading it as
# "writes nothing" let the wave group tasks nobody had checked and then
# announce "no owns overlap" as the reason, certifying a comparison it had
# skipped. Undeclared is now treated as unknown, and unknown rides alone.
print("a task with undeclared owns never shares a wave, and says so")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001")  # no owns
    write_task(d, "T-002")  # no owns
    rc, result, err = run_and_parse(d)
    check("undeclared: exit 0", rc == 0, f"rc={rc} err={err}")
    # Not deadlock: deferring EVERY undeclared task would mean nothing ever
    # reaches a wave in a decomposition that declares none, and the job
    # would never dispatch anything at all.
    check(
        "undeclared: one task still dispatches, so the job can't deadlock",
        len(result["wave"]) == 1 and result["wave"][0]["id"] == "T-001",
        result,
    )
    check(
        "undeclared: the peer defers rather than riding along unchecked",
        ids(result["deferred"]) == ["T-002"],
        result,
    )
    check(
        "undeclared: the deferral says what to do about it",
        "owns" in result["deferred"][0]["reason"]
        and "T-001" in result["deferred"][0]["reason"],
        result["deferred"],
    )
    check(
        "undeclared: kind is owns-undeclared",
        result["deferred"][0]["kind"] == "owns-undeclared",
        result["deferred"],
    )

# One declared, one not: the unknown side is what blocks the pairing, so a
# task that did its homework still can't ride with one that didn't.
with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001")                      # no owns
    write_task(d, "T-002", owns=["file-b.py"])  # declared
    rc, result, err = run_and_parse(d)
    check(
        "mixed: a declared task can't pair with an undeclared one",
        ids(result["wave"]) == ["T-001"] and ids(result["deferred"]) == ["T-002"],
        result,
    )
    check(
        "mixed: kind is owns-undeclared",
        result["deferred"][0]["kind"] == "owns-undeclared",
        result["deferred"],
    )

# The reason string is the assertion the gate makes about its own work, so
# it must never claim an overlap check that no task could have supplied.
with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001")
    rc, result, err = run_and_parse(d)
    check(
        "undeclared: the wave reason never claims 'no owns overlap'",
        "no owns overlap" not in result["wave"][0]["reason"],
        result["wave"],
    )
    check(
        "undeclared: the wave reason names the undeclared owns instead",
        "undeclared" in result["wave"][0]["reason"],
        result["wave"],
    )

# --------------------------------------- 2c. a malformed owns entry rides alone
# #162's other half. R15 refuses `./file-a.py` at DEC-audit, but nothing
# stops a task file from being hand-edited after the audit passed, and this
# script runs on every turn. `paths_overlap('./file-a.py', 'file-a.py')` is
# False, so without this the two tasks below would ride together over one
# file with the wave reporting a clean check.
print("a task whose owns entry is malformed never shares a wave either")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["file-a.py"])
    write_task(d, "T-002", owns=["./file-a.py"])
    rc, result, err = run_and_parse(d)
    check("malformed: exit 0, not a parse failure", rc == 0, f"rc={rc} err={err}")
    check(
        "malformed: the well-formed task dispatches, the other defers",
        ids(result["wave"]) == ["T-001"] and ids(result["deferred"]) == ["T-002"],
        result,
    )
    check(
        "malformed: kind is owns-malformed",
        result["deferred"][0]["kind"] == "owns-malformed",
        result["deferred"],
    )
    check(
        "malformed: the deferral quotes the offending entry back",
        "./file-a.py" in result["deferred"][0]["reason"],
        result["deferred"],
    )

# The malformed task itself still dispatches (deferring both sides would
# deadlock a job whose every task carries a typo), and its wave reason says
# why it's alone rather than claiming a check nobody could run.
with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["src/lib/", "../outside.py"])
    rc, result, err = run_and_parse(d)
    check(
        "malformed alone: still dispatches",
        ids(result["wave"]) == ["T-001"],
        result,
    )
    check(
        "malformed alone: the wave reason never claims owns was checked",
        "owns checked" not in result["wave"][0]["reason"],
        result["wave"],
    )
    check(
        "malformed alone: the wave reason names the bad entry",
        "../outside.py" in result["wave"][0]["reason"],
        result["wave"],
    )

# #162's opening reproduction, end to end and with nothing on disk. Two
# tasks name one directory, one of them without its trailing slash. The
# linter refuses that spelling when the directory already exists, which it
# usually doesn't when the task's job is to create it, so the wave has to
# catch this pair on the strings alone.
with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["src/lib"])
    write_task(d, "T-002", owns=["src/lib/"])
    rc, result, err = run_and_parse(d)
    check(
        "'src/lib' and 'src/lib/' never share a wave",
        ids(result["wave"]) == ["T-001"] and ids(result["deferred"]) == ["T-002"],
        result,
    )
    check(
        "'src/lib' vs 'src/lib/': deferred as a real overlap, not as a typo",
        result["deferred"][0]["kind"] == "owns",
        result["deferred"],
    )

# A file and the directory above it are the same territory too.
with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["src/foo"])
    write_task(d, "T-002", owns=["src/foo/bar.py"])
    rc, result, err = run_and_parse(d)
    check(
        "a file claim under another task's slashless directory claim defers",
        ids(result["wave"]) == ["T-001"] and ids(result["deferred"]) == ["T-002"],
        result,
    )

# A malformed entry outranks an undeclared peer: same wave refusal either
# way, and naming the typo is the more actionable of the two reasons.
with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["/absolute/file-a.py"])
    write_task(d, "T-002")  # no owns
    rc, result, err = run_and_parse(d)
    check(
        "malformed beats undeclared: kind is owns-malformed",
        result["deferred"][0]["kind"] == "owns-malformed",
        result["deferred"],
    )

# ------------------------------------------------- 3. --running excludes a task
print("--running excludes a task from the wave")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["file-a.py"])
    write_task(d, "T-002", owns=["file-b.py"])
    rc, result, err = run_and_parse(d, "--running", "T-001")
    check("running: exit 0", rc == 0, f"rc={rc} err={err}")
    check(
        "running: only the non-running task waves",
        ids(result["wave"]) == ["T-002"],
        result,
    )
    check(
        "running: excluded task isn't dumped into deferred either",
        result["deferred"] == [],
        result,
    )

# ------------------------------------- 3b. --running excludes EVERY bucket
# The module docstring promises "excluded from `wave` and from every other
# bucket," but the `attention` loop and the `checks` comprehension used to
# never consult `running` at all—a task named with --running still came back
# in attention or checks. Both buckets pull from statuses the wave loop
# never touches (`disputed`, `needs-check`), so this needs its own fixture
# rather than reusing #3's pending/owns one.
print("--running excludes a task from attention and checks too, not just wave")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", status="disputed")
    write_task(d, "T-002", status="needs-check")
    rc, result, err = run_and_parse(d, "--running", "T-001", "T-002")
    check("running (all buckets): exit 0", rc == 0, f"rc={rc} err={err}")
    check(
        "running (all buckets): a disputed task named in --running is "
        "excluded from attention",
        result["attention"] == [],
        result,
    )
    check(
        "running (all buckets): a needs-check task named in --running is "
        "excluded from checks",
        result["checks"] == [],
        result,
    )

# ------------------------------------------- 4. dep on an abandoned task
print("a task whose dep is abandoned lands in attention")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", status="abandoned")
    write_task(d, "T-002", deps=["T-001"])
    rc, result, err = run_and_parse(d)
    check("abandoned-dep: exit 0", rc == 0, f"rc={rc} err={err}")
    check("abandoned-dep: not in wave", result["wave"] == [], result)
    check("abandoned-dep: not in deferred", result["deferred"] == [], result)
    check(
        "abandoned-dep: lands in attention naming T-001",
        len(result["attention"]) == 1
        and result["attention"][0]["id"] == "T-002"
        and "T-001" in result["attention"][0]["reason"],
        result["attention"],
    )

# ------------------------------------------------- 5. malformed task file
print("a malformed task file exits 3")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    tasks_dir = os.path.join(d, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    with open(os.path.join(tasks_dir, "T-001.md"), "w", encoding="utf-8") as f:
        f.write("not frontmatter at all\n")
    rc, out, err = run_script(d)
    check("malformed: exit 3", rc == 3, f"rc={rc} out={out}")
    check("malformed: names the offending file", "T-001.md" in err, err)
    check("malformed: uses the ready-set: prefix", "ready-set:" in err, err)

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    tasks_dir = os.path.join(d, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    # Missing required fields (status, deps, executor, checker): frontmatter
    # parses fine, but the task can't be trusted to compute a ready set from.
    with open(os.path.join(tasks_dir, "T-002.md"), "w", encoding="utf-8") as f:
        f.write("---\nid: T-002\nretries: 0\n---\n")
    rc, out, err = run_script(d)
    check("missing-fields: exit 3", rc == 3, f"rc={rc} out={out}")
    check("missing-fields: names T-002.md", "T-002.md" in err, err)

# ------------------------------------------- 5b. duplicate frontmatter id
# load_tasks() keys its dict on the frontmatter `id`, not the filename—two
# files declaring the same id used to collapse silently into one dict entry,
# so the earlier file (and whatever real task it names) vanished from every
# bucket with nothing on stderr to explain why. This module's own fail-loud
# contract says a task silently skipped here is a task nobody would ever
# dispatch, so a repeated id has to raise, naming both files.
print("two task files declaring the same id exits 3, naming both files")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["file-a.py"])
    write_task(d, "T-005", owns=["file-b.py"])
    # write_task() names the file after its first arg, but its frontmatter's
    # `id:` line is written the same way—force the collision by rewriting
    # T-005.md's own id to T-001 directly, the on-disk shape a stale
    # copy-paste of a task file would actually produce.
    dup_path = os.path.join(d, "tasks", "T-005.md")
    with open(dup_path, encoding="utf-8") as f:
        content = f.read()
    content = content.replace("id: T-005", "id: T-001", 1)
    with open(dup_path, "w", encoding="utf-8") as f:
        f.write(content)
    rc, out, err = run_script(d)
    check("duplicate-id: exit 3", rc == 3, f"rc={rc} out={out}")
    check(
        "duplicate-id: names both files",
        "T-001.md" in err and "T-005.md" in err,
        err,
    )
    check("duplicate-id: names the duplicated id", "T-001" in err, err)
    check("duplicate-id: uses the ready-set: prefix", "ready-set:" in err, err)

# ------------------------------------------------------------ 6. determinism
print("determinism: same input, byte-identical output across repeated runs")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", owns=["file-a.py"])
    write_task(d, "T-002", owns=["file-b.py"], deps=["T-001"], status="rework", retries=1)
    write_task(d, "T-003", status="needs-check")
    write_task(d, "T-004", status="disputed")
    outputs = set()
    for _ in range(5):
        rc, out, err = run_script(d)
        check("determinism: each run exits 0", rc == 0, f"rc={rc} err={err}")
        outputs.add(out)
    check(
        "determinism: every run produced byte-identical stdout",
        len(outputs) == 1,
        outputs,
    )

# --------------------------------------------------------- bonus: needs-check
print("a needs-check task owes its checker")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", status="needs-check", checker="checker-judgment")
    rc, result, err = run_and_parse(d)
    check("needs-check: exit 0", rc == 0, f"rc={rc} err={err}")
    check(
        "needs-check: shows up in checks naming its checker",
        result["checks"] == [
            {
                "id": "T-001",
                "agent": "checker-judgment",
                "reason": "worker finished; checker of record is owed",
            }
        ],
        result["checks"],
    )

# --------------------------------------------------- bonus: spent retry budget
print("a task with a spent retry budget defers instead of waving")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", status="pending", retries=2, max_retries=2)
    rc, result, err = run_and_parse(d)
    check("spent-budget: exit 0", rc == 0, f"rc={rc} err={err}")
    check("spent-budget: not in wave", result["wave"] == [], result)
    check(
        "spent-budget: deferred naming the budget",
        len(result["deferred"]) == 1
        and result["deferred"][0]["id"] == "T-001"
        and "retries=2" in result["deferred"][0]["reason"],
        result["deferred"],
    )
    check(
        "spent-budget: kind is budget",
        result["deferred"][0]["kind"] == "budget",
        result["deferred"],
    )

# ------------------------------------------------- bonus: rework is never waved
# The retry ladder (.agent-guild/CLAUDE.md) requires the orchestrator to copy
# the checker's diagnosis, increment `retries`, and move the task back to
# `assigned` before a worker may run on it—dispatch-guard.py refuses a
# worker dispatch on anything but `assigned`. A `rework` task offered in the
# wave would invite skipping straight past those steps into that refusal, so
# ready-set.py must never place one there—or in `deferred`/`attention`
# either: those buckets exist for pending-task obstacles, and a rework
# task's next move is the ladder itself, which only the caller (not
# ready-set) knows how to word.
print("a rework task is never offered in any bucket, even with no obstacles")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", status="rework", owns=["file-a.py"], retries=1)
    rc, result, err = run_and_parse(d)
    check("rework: exit 0", rc == 0, f"rc={rc} err={err}")
    check("rework: not in wave", result["wave"] == [], result)
    check("rework: not in deferred", result["deferred"] == [], result)
    check("rework: not in attention", result["attention"] == [], result)

# --------------------------------------------------------- bonus: unmet deps
print("a task with an unmet (incomplete) dep defers, naming it")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", status="assigned")
    write_task(d, "T-002", deps=["T-001"])
    rc, result, err = run_and_parse(d)
    check("unmet-deps: exit 0", rc == 0, f"rc={rc} err={err}")
    check("unmet-deps: not in wave", result["wave"] == [], result)
    check(
        "unmet-deps: deferred naming T-001 and its status",
        len(result["deferred"]) == 1
        and result["deferred"][0]["id"] == "T-002"
        and "T-001" in result["deferred"][0]["reason"]
        and "assigned" in result["deferred"][0]["reason"],
        result["deferred"],
    )
    check(
        "unmet-deps: kind is deps",
        result["deferred"][0]["kind"] == "deps",
        result["deferred"],
    )

# ------------------------------------------------------ bonus: no job active
print("an absent tasks/ directory is a clean empty result, not an error")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    rc, result, err = run_and_parse(d)
    check("no-job: exit 0", rc == 0, f"rc={rc} err={err}")
    check(
        "no-job: every bucket empty",
        result == {"wave": [], "checks": [], "deferred": [], "attention": []},
        result,
    )

# A state dir that ISN'T THERE is a different animal from one holding no
# tasks/. Both would print the same empty wave, and a caller reading that
# JSON could not tell "nothing is ready" from "I was pointed at the wrong
# path"—the same silent-drop failure the per-file exit 3 exists to stop,
# one directory up. The workflow driver in #134 reads this JSON to decide a
# job is finished, so the two must not look alike.
print("a state dir that does not exist exits 3, unlike one with no tasks/")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    missing = os.path.join(d, "no-such-state")
    rc, out, err = run_script(missing)
    check("missing-state-dir: exit 3", rc == 3, f"rc={rc} out={out}")
    check("missing-state-dir: names the path", missing in err, err)
    check("missing-state-dir: prints no JSON", out.strip() == "", out)

# --------------------------------------------------------- bonus: disputed
print("a disputed task lands in attention, not deferred or wave")

with tempfile.TemporaryDirectory(prefix="ready-set-fixture-") as d:
    write_task(d, "T-001", status="disputed")
    rc, result, err = run_and_parse(d)
    check("disputed: exit 0", rc == 0, f"rc={rc} err={err}")
    check("disputed: not in wave", result["wave"] == [], result)
    check("disputed: not in deferred", result["deferred"] == [], result)
    check(
        "disputed: lands in attention",
        ids(result["attention"]) == ["T-001"],
        result["attention"],
    )

# ------------------------------------------- replay: the archived #117 graph
# Everything above is a fixture built to exercise one rule. This section is the
# only case driven by a job that actually ran (#169). The wave path's headline
# claim is that grouping beats the serial dispatch it replaced, and until this
# existed nothing would have failed if a change to the grouping quietly
# serialized the whole thing again.
#
# #134 carried this criterion and was closed without it, because the driver it
# specified turned out to be infeasible—guild hooks don't fire for
# workflow-spawned agents. The criterion never needed that driver. ready-set.py
# is a pure function of task files plus --running, so the replay runs offline:
# no hosts, no agents, no vendor calls.
if not os.path.isdir(ARCHIVE_117):
    print(f"note: corpus archive not found at {ARCHIVE_117} — skipping the "
          f"replay. This suite ships into user projects; the archive under "
          f"state/ does not, so the skip is expected there and the remaining "
          f"cases still cover the script.")
else:
    print("replaying the archived #117 graph takes fewer waves than the run did")

    def corpus_deps():
        """Each task's declared deps, read from the archive itself so the
        dependency-order assertion can't drift from the graph it checks."""
        deps = {}
        for name in sorted(os.listdir(os.path.join(ARCHIVE_117, "tasks"))):
            with open(os.path.join(ARCHIVE_117, "tasks", name), encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"^deps:\s*\[(.*)\]\s*$", line)
                    if m:
                        deps[name[:-3]] = [d.strip() for d in m.group(1).split(",") if d.strip()]
                        break
        return deps

    def dispatched_tasks():
        """The tasks the real run actually sent workers to. Read from the
        run's own log rather than hardcoded, so "covers the same work" is
        anchored to what happened. Every line in this log appears twice—the
        run predates #41's double-registration fix—and T-006 was genuinely
        dispatched twice after a FAIL, so dedupe by task rather than by line
        and count tasks, not dispatches."""
        seen = set()
        with open(os.path.join(ARCHIVE_117, "log", "dispatches.log"), encoding="utf-8") as f:
            for line in f:
                fields = [p.strip() for p in line.split("|")]
                if len(fields) >= 3 and "worker-" in fields[1]:
                    seen.add(fields[2])
        return seen

    def set_status(state_dir, tid, status):
        path = os.path.join(state_dir, "tasks", f"{tid}.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(re.sub(r"^status:.*$", f"status: {status}", text, count=1, flags=re.M))

    def archive_digest():
        """A fingerprint of the archived tasks, so "the fixture works on a
        copy" is checked rather than asserted. add_owns mutates on disk by
        contract, and pointing it one directory to the left would rewrite the
        run this suite exists to preserve—a slip only `git status` would
        otherwise catch, and only if someone looked."""
        h = hashlib.sha256()
        tasks = os.path.join(ARCHIVE_117, "tasks")
        for name in sorted(os.listdir(tasks)):
            h.update(name.encode())
            with open(os.path.join(tasks, name), "rb") as f:
                h.update(f.read())
        return h.hexdigest()

    before = archive_digest()

    with tempfile.TemporaryDirectory(prefix="ready-set-replay-") as d:
        state = os.path.join(d, "state")
        os.makedirs(state)
        shutil.copytree(os.path.join(ARCHIVE_117, "tasks"), os.path.join(state, "tasks"))

        # The archive holds the job as it finished. Rewind it to the state the
        # orchestrator faced at the start: every task pending, no retries
        # spent. T-006's `retries: 1` wouldn't have deferred it on budget
        # anyway (the ladder defers at retries >= max_retries, and its max is
        # 2), so clearing it changes no wave here—it's rewound because a
        # replay that starts mid-run isn't replaying the run. The archived
        # files themselves are never touched; this is a copy.
        for name in sorted(os.listdir(os.path.join(state, "tasks"))):
            path = os.path.join(state, "tasks", name)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            text = re.sub(r"^status:.*$", "status: pending", text, count=1, flags=re.M)
            text = re.sub(r"^retries:.*$", "retries: 0", text, count=1, flags=re.M)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

        # The corpus predates #133 and carries no `owns`. Replayed as-is every
        # pair reads as owns-undeclared, every wave holds one task, and the
        # replay reproduces exactly the serial behavior it exists to disprove
        # while appearing to pass. Same derivation the linter suite proves
        # against, imported rather than repeated.
        add_owns(state)

        waves = []
        deferrals = []
        remaining = set(corpus_deps())
        # A cap, not a loop bound: an empty wave with work left means the
        # grouping stalled, and that has to fail loudly rather than spin.
        for _ in range(12):
            if not remaining:
                break
            rc, result, err = run_and_parse(state)
            if rc != 0 or result is None or not result["wave"]:
                check("replay: every call yields a non-empty wave",
                      False, f"rc={rc} err={err} result={result}")
                break
            members = sorted(ids(result["wave"]))
            waves.append(members)
            deferrals.append(result["deferred"])
            for tid in members:
                set_status(state, tid, "complete")
                remaining.discard(tid)

        check("replay: every task was dispatched", not remaining, f"left={sorted(remaining)}")

        # What the real run did: seven tasks, dispatched one at a time.
        serial = dispatched_tasks()
        covered = {tid for wave in waves for tid in wave}
        check("replay: covers exactly the tasks the run dispatched workers for",
              covered == serial, f"replayed={sorted(covered)} run={sorted(serial)}")

        # The thesis. Fewer waves than serial dispatches, with the count named
        # so a regression in grouping fails here instead of passing quietly.
        check(f"replay: {len(waves)} waves against {len(serial)} serially dispatched tasks",
              len(waves) < len(serial), f"waves={waves}")
        check("replay: takes exactly 6 waves", len(waves) == 6, f"waves={waves}")

        # Composition, not just count: a change that holds the number while
        # shuffling membership is still a change to the grouping.
        check(
            "replay: wave composition is unchanged",
            waves == [
                ["T-001", "T-005"],
                ["T-002"],
                ["T-004"],
                ["T-006"],
                ["T-007"],
                ["T-003"],
            ],
            waves,
        )

        # T-004 is why this is six waves and not five. Its lone artifact is
        # `~/repos/skills/...`, so the cloned owns entry is a tilde path, which
        # owns_entry_problem refuses—an unreadable claim is an unknown one, so
        # it rides alone instead of pairing with T-002. Asserted so the pinned
        # composition reads as a consequence rather than a snapshot.
        check(
            "replay: T-004 defers on malformed owns, splitting it from T-002",
            len(deferrals) > 1 and any(
                e["id"] == "T-004" and e["kind"] == "owns-malformed"
                for e in deferrals[1]),
            deferrals,
        )

        # No wave may contain a task whose dep hasn't already landed.
        deps = corpus_deps()
        # corpus_deps reads only the inline `deps: [...]` shape, which is what
        # the corpus uses. ready-set.py also accepts a block sequence, so a
        # task respelled that way would drop out of this dict and its
        # constraint would go unchecked while everything still reported green.
        # Parsing has to be complete before the comparison means anything.
        check("replay: parsed deps for every replayed task",
              set(deps) == covered, f"parsed={sorted(deps)} replayed={sorted(covered)}")
        wave_of = {tid: i for i, wave in enumerate(waves) for tid in wave}
        violations = [
            (tid, dep) for tid, dep_ids in deps.items() for dep in dep_ids
            if tid in wave_of and dep in wave_of and wave_of[dep] >= wave_of[tid]
        ]
        check("replay: no task waves at or before one of its deps",
              violations == [], f"violations={violations}")

    check("replay: the archived corpus is left untouched",
          archive_digest() == before, "the replay wrote to the archive")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
