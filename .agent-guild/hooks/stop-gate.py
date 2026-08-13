#!/usr/bin/env python3
"""Stop: the orchestrator can't end its turn while tasks are unfinished.

SubagentStop can validate that a worker followed protocol, but a hook can't
dispatch the checker that has to run next. This gate is what compels it: while
any task is non-terminal, the main session is blocked from stopping and handed
the exact next move for each open task. That closes the loop—worker returns,
gate refuses to let the turn end until the checker is dispatched and its verdict
acted on.

Livelock guard: the gate counts blocked turns PER ENTITY—one counter per open
task—and when any single counter reaches three while stop_hook_active is set,
it gives up loudly on that entity. It writes .agent-guild/state/STALLED.md
naming only the entities that actually tripped, rather than spinning forever.
Progress on an entity resets that entity's own counter: a status change, a
retry change, a verdict landing under its id.

Reporting an entity PARKS it. It stops holding the turn open, and the gate
goes right on blocking for everything else, so the turn ends only once every
open entity is parked. Standing the whole gate down on the first trip is
what this shipped as first, and it was strictly worse than the global
counter it replaced: a tripped entity's count only resets when its own
digest moves, so one task nobody ruled on disarmed the gate for the entire
job, permanently, and every other task then climbed toward its own trip
because nothing was compelling anyone to work on it.

This was one global counter until #163 measured what that costs under waves.
#111 taught the counter to hold while a subagent was genuinely in flight, but
the hold was an any() over every open task, so a single live worker made
every other task immune to the backstop. A task stuck at `disputed` sat
frozen at count=1 through eight blocked firings while a sibling churned
beside it. Phase 2 nearly always has something mid-flight, so the backstop
was off for most of it. Per-entity counters are what let a stuck task reach
STALLED.md on its own schedule, whatever its siblings are doing.

The gate gets sharper in exchange, and that's deliberate: what trips it now
is per-entity neglect rather than global stasis. Three blocked continuations
in which the orchestrator never touches a particular task, while doing real
work elsewhere, stall that task. Each of those blocks handed it an explicit
next move for that exact entity, so three turns of silence is a fair reading
of stuck.

_lib.in_flight() names every dispatch still inside its freshness TTL. A task
whose OWN dispatch is still fresh holds its OWN counter while its siblings
keep counting; dispatching again would duplicate a subagent already running,
and calling that task stuck would be just as wrong. A marker that outlives
its TTL is worth nothing: staleness is what lets the backstop resume on a
dead agent without anyone clearing state by hand.

Waves also fire this gate twice for ONE real blocked turn when both the
plugin's hooks.json and a copy-in settings.json are registered (#41): same
task state, same verdict set, same markers, because nothing has actually
happened between the two firings. No per-entity digest can tell that apart
from a genuine second strike—nothing in ANY entity changed—so the state file
also persists the main transcript's byte size, and that hold stays global.
Two firings against an unchanged transcript are one real block, not two, and
every counter holds rather than advancing.

A second opinion used to be an obligation this gate enforced: every verdict of
record on disk owed a courier crossing, and an undischarged one held the turn
open as its own entity. #167 retired that after #34 ruled the cross-family bet
does not pay. The courier is opt-in now, so nothing here counts crossings, and
tasks are the only entities left.

Presentation, and since #163 pacing too: this gate shells out to
.agent-guild/scripts/ready-set.py to group ready tasks into a wave, a
deferred list, and an attention list, fed `--running` from the fresh
in-flight markers this gate already computes (#125)—that script is the
single host-neutral source of these decisions, so a Claude host and a Codex
host announce them identically from identical inputs.

#125 promised those buckets were presentation only, and per-entity counters
break that promise on purpose. A task deferred because its dependency is
still running has no move available to it, as the gate's own message says, so
counting a blocked turn against it would stall a task nobody could have
advanced. A task in the `deferred` bucket therefore holds its counter, but
only for `kind: "deps"` and `kind: "owns"`. The other two kinds would each
wedge the backstop instead of protecting it, for reasons _deferral_held
spells out; `owns-undeclared` in particular reproduces #163's own bug,
because `owns: []` is the shipped template default. The buckets still never
touch WHETHER the gate blocks, only how fast a counter climbs.

Everything else stays eligible: wave and `checks` entries have a dispatch
available now, `attention` entries need a ruling now, and a task in no
bucket at all (`assigned`, `checking`, `rework`) is between dispatches with
its own marker to speak for it. A degrade—missing script, timeout, non-zero
exit, or a partial result—empties the deferred set, which makes every task
eligible and fails toward a LOUD spurious STALLED.md rather than a silently
suppressed backstop. #163's bug was that same trade taken the other way. A
kit too old to emit `kind` is the one degrade that isn't total: those reason
strings are stable enough to map back, so a legitimately waiting task isn't
punished for the far side's version.

One wedge the hold could create: a dependency cycle, or a dep naming a task
file that doesn't exist, where every task waits on another and nothing can
ever un-defer any of them. check-job-spec.py's R7 catches both, but only at
dispatch time, and dispatch time never arrives when nothing can dispatch.
The valve is to void the deferral hold for that firing, which lets the wedge
be named like anything else. It opens when every entity that could still
trip is deferral-held, nothing is in flight, and nothing moved since the
last firing. Already-parked entities are excluded from that test, since a
reported entity can no longer be the thing that surfaces a wedge sitting
behind it—without that exclusion a cycle stayed pinned at 1 forever beside
any one unrelated task. The in-flight half is a plain marker check rather
than a claim about open tasks: an opted-in courier can still be running
against a task the orchestrator has already moved to `complete` on its
checker of record, and open_tasks() cannot see that marker, so reasoning
from the open set alone stalls a task for taking this gate's own advice.

Every open task gets exactly one line, chosen by whichever of ready-set's
buckets names it—wave, deferred, or attention—so the gate's advice can
never contradict ready-set's own verdict on that task (#155). A task in
none of those (including every `rework` task: ready-set never offers one in
the wave, since dispatching it straight would skip the retry ladder's
diagnosis-copy and retries-increment steps and trip dispatch-guard's
`assigned`-only check for workers) falls through to _next_move, unchanged.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

STALL_LIMIT = 3

# ready-set.py `deferred` kinds that hold a task's stall counter (#163): the
# orchestrator has no move to make on either until something else finishes.
# "budget" and "owns-undeclared" are the two deliberately left out—see
# _deferral_held for why each one would wedge the backstop.
DEFERRAL_HOLD_KINDS = frozenset({"deps", "owns"})

# Reason-string prefixes for those same two kinds, used only when a task's
# `deferred` entry carries no `kind` at all (see _deferral_held).
_KIND_BY_REASON_PREFIX = (
    ("unmet deps:", "deps"),
    ("owns overlap with", "owns"),
)

# Short on purpose (#125): ready-set.py only parses a handful of small task
# files, nothing like check-job-spec.py's full paperwork lint, so there's no
# reason to hold the gate open anywhere near dispatch-guard's 20s budget.
# AGENT_GUILD_READY_SET_TIMEOUT is the same test-only seam as
# AGENT_GUILD_JOB_SPEC_TIMEOUT: it lets one test exercise a real
# subprocess.run() timeout without a real 5s wait for every run of this
# suite.
READY_SET_TIMEOUT_S = float(os.environ.get("AGENT_GUILD_READY_SET_TIMEOUT", "5"))


def _next_move(tid, status, retries, marker_state=None, marker_ts=None):
    # #111: `assigned` and `checking` are exactly the two statuses a task
    # sits at WHILE something is dispatched against it, so they're the two
    # statuses where "nothing has changed" is ambiguous between "nobody has
    # dispatched anything yet" and "a worker/checker is still running." The
    # in-flight marker (see _lib.mark_in_flight/in_flight) disambiguates:
    # fresh means don't dispatch again, absent means dispatch, stale means
    # whatever ran never came back.
    if status in ("assigned", "checking"):
        role = "executor" if status == "assigned" else "checker"
        if marker_state == "fresh":
            return (
                f"  {tid} [{status}] → mid-flight (dispatched {marker_ts}); "
                "do not dispatch another."
            )
        if marker_state == "stale":
            return (
                f"  {tid} [{status}] → its {role} never returned; investigate, "
                "then re-dispatch."
            )
        # An absent marker does NOT mean "nobody has run yet"—subagent-return
        # clears the marker on the way out, so a checker that has already
        # landed its verdict leaves exactly the same absence as one nobody
        # dispatched. The two are told apart by the verdict itself. Only
        # `checking` needs this: the CHECKER writes the verdict but the
        # ORCHESTRATOR moves the status off `checking`, so verdict-landed-and-
        # status-unmoved is the ordinary state of every checked task, and
        # telling the orchestrator to dispatch a second checker there would
        # duplicate a check that already passed. (`assigned` has no such
        # window—the worker moves itself to `needs-check`.)
        if status == "checking" and _verdict_landed_for(tid, retries):
            return (
                f"  {tid} [{status}] → its checker has landed a verdict; act "
                "on it (complete, or copy the diagnosis into rework)."
            )
        return f"  {tid} [{status}] → dispatch the {role}."
    moves = {
        "pending": "assign it and dispatch its executor.",
        "needs-check": "set status to checking and dispatch its checker.",
        "rework": f"copy the checker's diagnosis into ## Rework diagnosis, set "
                  f"status back to assigned (retries {retries}), and re-dispatch "
                  "the same worker.",
        "disputed": "read the dispute, verdict, and artifact yourself and rule; "
                    "append the ruling and set the task to complete or rework.",
    }
    return f"  {tid} [{status}] → {moves.get(status, 'resolve this task.')}"


def _running_ids(fresh_markers):
    """Task/Audit ids behind fresh in-flight markers, deduped and order-
    preserved. A marker stem is `<ident>--<agent>`; ready-set.py wants only
    the ids, since it's the caller's job (not ready-set.py's) to say what's
    already dispatched."""
    out = []
    seen = set()
    for m in fresh_markers:
        ident = m.split("--", 1)[0]
        if ident not in seen:
            seen.add(ident)
            out.append(ident)
    return out


def _compute_wave(fresh_markers):
    """ready-set.py's parsed JSON result, or None on any failure to
    produce one—missing script, timeout, non-zero exit, or unparseable
    stdout. None means "degrade to _next_move for everything," never
    "block less than before": every caller treats None exactly like an
    empty wave, so a broken ready-set.py can only ever make the message
    plainer, not the gate looser.

    Since #163 the result also paces the stall backstop (see the deferral
    hold in main), so None costs a second thing: no task is deferral-held,
    every counter advances, and a task that was legitimately waiting can
    reach STALLED.md. That direction is deliberate. A degraded ready-set.py
    that suppressed the backstop instead would recreate exactly the silent
    hole #163 was filed about."""
    script = os.path.join(
        _lib.project_dir(), ".agent-guild", "scripts", "ready-set.py"
    )
    if not os.path.exists(script):
        return None
    cmd = [
        sys.executable,
        script,
        _lib.state_path(),
        "--running",
        *_running_ids(fresh_markers),
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=_lib.project_dir(),
            capture_output=True,
            text=True,
            timeout=READY_SET_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    # All four buckets, not just `wave`: the presentation code indexes the
    # other three directly, so a result carrying only some of them would
    # crash this gate instead of degrading it. Degrading is always the
    # correct answer here—a broken ready-set.py must never take the loop's
    # own backstop down with it.
    if not isinstance(result, dict) or not all(
        k in result for k in ("wave", "checks", "deferred", "attention")
    ):
        return None
    return result


def _wave_block(wave):
    """The unmissable header for a computed wave, or None if it's empty.
    Two or more members is #125's headline case—independent tasks that
    used to get dispatched one at a time purely because nothing said
    otherwise—so that case gets an explicit, hard-to-miss instruction to
    fire them together in a single message."""
    if not wave:
        return None
    lines = []
    if len(wave) >= 2:
        lines.append(
            f"READY WAVE: {len(wave)} tasks have no unmet dependency on each "
            "other right now. Dispatch ALL of them in this ONE message, as "
            "parallel Task tool calls, before doing anything else:"
        )
    else:
        lines.append("Ready to dispatch now:")
    for w in wave:
        lines.append(f"  {w['id']} → dispatch {w['agent']} ({w['reason']}).")
    return "\n".join(lines)


def _state_file():
    return _lib.state_path("log", "stop-gate.state")


def _verdict_landed_for(tid, retries):
    """True if a verdict of record for `tid` at THIS retry round is on disk.

    Round-scoped on purpose: an older round's verdict survives a rework
    cycle, and treating it as this round's would tell the orchestrator to act
    on a verdict that judged a different artifact. Lane-suffixed files
    (`...-r0-codex.json`) are second opinions, never the verdict of record,
    so they don't count.
    """
    for name in _verdicts_landed():
        if not name.startswith(f"{tid}-"):
            continue
        stem = name.rsplit(".", 1)[0]
        if stem.endswith(f"-r{retries}"):
            return True
    return False


def _marker_info(tid, fresh_markers, all_markers):
    """(marker_state, dispatched_at) for tid's in-flight marker: 'fresh' with
    a timestamp, 'stale' with None, or (None, None) if no marker exists at
    all. `fresh_markers`/`all_markers` are pre-computed _lib.in_flight()
    results (default TTL, and an effectively-infinite TTL) so a caller
    walking every open task pays for exactly two directory scans total, not
    one per task. The timestamp comes from opening the named marker directly
    rather than re-listing the directory, which is what keeps that promise."""
    prefix = f"{tid}--"
    hit = next((m for m in sorted(fresh_markers) if m.startswith(prefix)), None)
    if hit is not None:
        try:
            path = _lib.state_path("log", "in-flight", f"{hit}.json")
            with open(path, encoding="utf-8") as f:
                return "fresh", json.load(f).get("dispatched_at")
        except Exception:
            # The marker was fresh a moment ago, so it existed; a read that
            # fails now means a concurrent return cleared it. Still report
            # fresh (the digest already counted it) and just lose the stamp.
            return "fresh", None
    if any(m.startswith(prefix) for m in all_markers):
        return "stale", None
    return None, None


def _transcript_size(data):
    """Byte size of the main-session transcript this Stop event names, or
    None if it's absent/unreadable. The #41 double-registration seam: the
    SAME real Stop event firing this gate twice (once per registered copy)
    hands both firings the identical file at the identical size, which is
    what tells that apart from a genuine second blocked turn (where the
    orchestrator did something in between and the transcript grew)."""
    path = data.get("transcript_path")
    if not isinstance(path, str) or not path:
        return None
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _verdicts_landed():
    """Verdict filenames, which move whenever a check finishes.

    (id, status, retries) can hold still across real work: a task sits at
    `checking` through its checker of record AND its courier second opinion, so
    two verdicts can land without the task tuple changing at all. Counting that
    as "no progress" is what wrote a spurious STALLED.md during the #78 run, and
    it's the same blindness behind #81—on Codex checkers hand their verdicts to
    the parent to write, which stretches the window between status changes and
    trips the backstop sooner. A stem carries task, tier, retry, and lane, so
    the set is a faithful progress signal without reading any file.
    """
    try:
        return sorted(os.listdir(_lib.state_path("verdicts")))
    except OSError:
        # No verdicts dir yet is a legitimate state, not an error—fall back to
        # the task tuple alone rather than letting the gate crash open.
        return []


def _load_state():
    """{"entries": {key: {"digest", "count"}}, "transcript_size": N}.

    A file written before #163 carries one flat digest+count pair for the
    whole job and no `entries` at all; it reads as no entries, which starts
    every counter over. There's no migration to write because there's nothing
    worth carrying across: the file tracks one job's blocked turns, and a
    guild job that's mid-flight during an upgrade loses at most two strikes
    of history."""
    try:
        with open(_state_file(), encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    return {"entries": entries, "transcript_size": raw.get("transcript_size")}


def _save_state(entries, transcript_size=None):
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        with open(_state_file(), "w", encoding="utf-8") as f:
            json.dump({"entries": entries, "transcript_size": transcript_size}, f)
    except Exception:
        pass


def _dispositions(ready_result):
    """{task_id: [bucket, reason, kind]} across all four of ready-set.py's
    buckets, or {} when it degraded. `kind` is None for the three buckets
    that don't carry one, and for a copied-in ready-set.py predating #163's
    `kind` field—both read as "not a hold" below, which is the fail-loud
    direction. No task appears in two buckets: ready-set `continue`s out of
    its loop the moment it places one."""
    out = {}
    if not ready_result:
        return out
    for bucket in ("wave", "checks", "deferred", "attention"):
        for entry in ready_result.get(bucket) or []:
            if not isinstance(entry, dict):
                continue
            tid = entry.get("id")
            if tid:
                out[tid] = [bucket, entry.get("reason"), entry.get("kind")]
    return out


def _deferral_held(tid, dispositions):
    """True if ready-set deferred this task for something the orchestrator
    cannot act on right now: an unmet dep, or an `owns` collision with a peer
    that genuinely claims the same paths.

    Two of the four deferral kinds are deliberately outside that set, both
    because waiting can never resolve them.

    `budget`—a spent retry budget is retry-ladder step 4 (escalate a tier,
    re-decompose, or surface the task). Holding it would leave a job whose
    only open task is budget-deferred blocked forever with no backstop.

    `owns-undeclared`—ready-set defers an undeclared task against every id in
    `--running`, and `owns: []` is what templates/task.md ships, so holding
    this one would let a single live subagent freeze every other pending
    task's counter. That is #163's own bug wearing a different hat, and
    review caught it here with a reproduction. The remedy ready-set names in
    its reason string ("declare it on both to run them together") is an
    orchestrator action, which puts this alongside `budget` rather than
    alongside a real wait."""
    d = dispositions.get(tid)
    if not d or d[0] != "deferred":
        return False
    kind = d[2]
    if kind is None:
        # Version skew: a project's copied-in ready-set.py from before #163
        # emits `deferred` with no `kind` at all, and reading that as "not a
        # hold" stalls tasks that are legitimately waiting. Its reason
        # strings are stable and documented, so map back the two that hold.
        # `kind` is authoritative wherever it exists; this is a fallback for
        # an old script, not a second source of truth.
        reason = d[1] or ""
        kind = next(
            (k for prefix, k in _KIND_BY_REASON_PREFIX if reason.startswith(prefix)),
            None,
        )
    return kind in DEFERRAL_HOLD_KINDS


def _task_digest(tid, status, retries, verdicts, fresh_markers):
    """This task's own slice of the job state, as the string its counter
    compares against.

    The task's ready-set disposition is deliberately NOT in here, though it
    was at first. Putting it in meant any oscillating input reset the counter
    forever: a ready-set.py that alternated healthy and degraded (it exits 3
    on a task file caught mid-rewrite) flipped every task's digest every
    firing and pinned every counter at 1, which is a silently disabled
    backstop. Review caught that with a reproduction.

    Leaving it out costs nothing real. A hold pauses an entity's clock; when
    the hold lifts the clock RESUMES rather than restarting, and a count
    above 1 was only ever earned during firings where the task was actionable
    and untouched."""
    return json.dumps([
        status,
        retries,
        [v for v in verdicts if v.startswith(f"{tid}-")],
        [m for m in fresh_markers if m.startswith(f"{tid}--")],
    ])


def main(data):
    # Supported hosts stamp agent_id on a subagent-scoped stop input. A
    # subagent's turn ending is subagent-return's jurisdiction, not this gate's—
    # this gate exists to hold open the ORCHESTRATOR's turn, and a subagent has
    # no say over the orchestrator's open-task picture. No-op unconditionally,
    # before touching open_tasks() or the livelock state file: a subagent Stop
    # must never increment (or reset) the counter that's tracking main-session
    # livelock, or parallel subagents finishing in sequence would trip a
    # spurious STALLED.md with nothing actually stuck.
    if _lib.in_subagent(data):
        return 0

    tasks = _lib.open_tasks()
    if not tasks:
        # Clean slate—clear any stale block counters and let the turn end.
        _save_state({}, None)
        return 0

    # Fresh markers ride in each task's own digest, so a dispatch, a return,
    # or a staleness transition (nothing renewing a marker before its TTL
    # lapses) changes that task's digest exactly like a status or retry
    # change would (#111)—and, since #163, changes only that task's.
    fresh_markers = _lib.in_flight()
    # Hoisted above the counter block (#163): ready-set's buckets now pace
    # the backstop as well as phrase the message, so the deferral hold needs
    # them before any counter moves. Computed once and reused by the
    # presentation code below—it's this gate's only subprocess, and running
    # it twice a firing would double the cost for nothing.
    ready_result = _compute_wave(fresh_markers)
    dispositions = _dispositions(ready_result)

    prev = _load_state()
    prev_entries = prev["entries"]
    stop_active = bool(data.get("stop_hook_active"))
    transcript_size = _transcript_size(data)
    verdicts = _verdicts_landed()

    # Held for a reason no per-entity digest can see (#41): the identical
    # transcript size across two firings means the same real Stop event fired
    # this gate twice (double registration), not that the orchestrator
    # blocked, did nothing, and got blocked again. Only compared when both
    # sides are known—an absent transcript_path (most of this test suite, and
    # any host that doesn't supply one) must fall through to the ordinary
    # advance-or-hold logic below, not silently freeze every counter on
    # None == None.
    same_transcript_size = (
        transcript_size is not None
        and prev.get("transcript_size") is not None
        and transcript_size == prev.get("transcript_size")
    )

    # One entity per open task: (key, digest, marker_held, deferral_held,
    # line).
    entities = [
        (
            tid,
            _task_digest(tid, status, retries, verdicts, fresh_markers),
            any(m.startswith(f"{tid}--") for m in fresh_markers),
            _deferral_held(tid, dispositions),
            f"- {tid} [{status}] retries={retries}",
        )
        for tid, status, retries in tasks
    ]

    def _prev_count(key):
        try:
            return int(prev_entries[key].get("count", 0))
        except (TypeError, ValueError, KeyError, AttributeError):
            return 0

    def _unchanged(key, digest):
        prev_entry = prev_entries.get(key)
        return isinstance(prev_entry, dict) and digest == prev_entry.get("digest")

    # The deferral hold's escape valve. A task waiting on a dep or an `owns`
    # collision shouldn't be punished for waiting, but the hold has to give
    # out when there's nothing left to wait FOR—otherwise a dependency cycle,
    # or a dep naming a task file that doesn't exist, holds every counter
    # forever and the job blocks with no backstop at all.
    #
    # It gives out when every entity that could still trip is deferral-held,
    # nothing is in flight, and nothing moved since the last firing. Entities
    # already at the limit are excluded from that test on purpose: they've
    # been reported and parked, so they can no longer be the thing that
    # surfaces a wedge sitting behind them. Without that exclusion a
    # dependency cycle stayed pinned at 1 forever beside any one unrelated
    # task, and was never named. The in-flight test is a plain marker check
    # rather than "is every open task deferred", because an opted-in courier
    # can still be running against a task already moved to `complete`, and
    # open_tasks() cannot see it. Both shapes came from review, with
    # reproductions.
    active = [e for e in entities if _prev_count(e[0]) < STALL_LIMIT]
    wedged = (
        not fresh_markers
        and bool(active)
        and all(deferral_held for _k, _d, _m, deferral_held, _l in active)
        and all(_unchanged(key, digest) for key, digest, _m, _d, _l in active)
    )

    entries = {}
    stalled = []
    for key, digest, marker_held, deferral_held, line in entities:
        held = marker_held or (deferral_held and not wedged)
        if _unchanged(key, digest):
            try:
                prev_count = int(prev_entries[key].get("count", 0))
            except (TypeError, ValueError):
                # A hand-mangled `count` starts this entity over rather than
                # crashing the gate that's holding the job together. It costs
                # the entity's history, which is the cheap direction: the
                # worst case is a few extra blocked turns before the backstop
                # catches up again.
                prev_count = 0
            count = prev_count if (held or same_transcript_size) else prev_count + 1
        else:
            count = 1
        # Entities are rebuilt from scratch every firing rather than merged
        # into what was loaded, which is what prunes a task that reached a
        # terminal status. A key that comes back later starts over at 1,
        # correctly: something moved.
        entries[key] = {"digest": digest, "count": count}
        if count >= STALL_LIMIT:
            stalled.append((key, f"{line} ({count} blocked turns, no progress)"))

    _save_state(entries, transcript_size)

    # Livelock backstop: some entity sat unchanged through the limit while
    # nothing ran against it and nothing held it. Give up loudly on that
    # entity, naming only it, so the report points at what's actually stuck
    # rather than at every task that happened to be open at the time (#163).
    #
    # Reporting an entity PARKS it: it stops holding the turn open, and the
    # gate goes right on blocking for everything else. Standing the whole
    # gate down here (what this first shipped as) meant one task nobody ruled
    # on disarmed the gate for the entire job, permanently—a per-entity
    # counter with a job-wide surrender, and worse than the global counter it
    # replaced, since that one at least re-armed whenever anything moved.
    # Caught by review with a reproduction. When every open entity is parked
    # the turn ends, which is the original backstop behavior in the only
    # state that warranted it.
    parked = set()
    if stop_active and stalled:
        parked = {key for key, _line in stalled}
        lines = [
            "# STALLED",
            "",
            "The stop gate blocked repeatedly with no progress on these, and "
            "nothing running against them:",
            "",
        ] + [line for _key, line in stalled] + [
            "",
            "Anything else still open is left out on purpose: it either moved, "
            "or something is still working on it. The gate goes on blocking "
            "for those and has stopped holding the turn open for these. "
            "Investigate by hand: a checker owing a verdict, a dispute "
            "needing a ruling, or a task that should be marked abandoned. "
            "Delete this file once resolved.",
        ]
        try:
            with open(_lib.state_path("STALLED.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
        tasks = [t for t in tasks if t[0] not in parked]
        if not tasks:
            return 0

    all_markers = _lib.in_flight(ttl=float("inf"))

    # Presentation, from the same ready_result the counter block above
    # already paced itself with (#125, #163): it never changes which tasks
    # are open—only which of them get folded
    # into the wave/deferred/attention lines instead of an ordinary
    # _next_move line. Every bucket stays empty whenever ready-set.py
    # degrades, which collapses this whole block straight back to the
    # pre-#125 behavior: every task gets its _next_move line, nothing gets a
    # wave header.
    #
    # Every open task gets exactly one line, and that line must never
    # contradict ready-set (#155): a task ready-set deferred (an unmet dep,
    # an owns collision, a spent budget) must never be told to just dispatch
    # its executor, and a task ready-set escalated to attention (a dep on an
    # abandoned task, same as `disputed`) must never be told the generic
    # move either—both cases carry ready-set's own reason string verbatim so
    # the two views of the same task can't drift apart.
    # Parked entities are dropped from the wave too. They're already named in
    # STALLED.md as needing a human, so re-advertising them as ready to
    # dispatch would put the gate's two messages at odds about the same task.
    wave = [w for w in (ready_result["wave"] if ready_result else [])
            if w["id"] not in parked]
    deferred = ready_result["deferred"] if ready_result else []
    attention = ready_result["attention"] if ready_result else []
    wave_ids = {w["id"] for w in wave}
    deferred_reasons = {d["id"]: d["reason"] for d in deferred}
    attention_reasons = {a["id"]: a["reason"] for a in attention}

    task_lines = []
    for t in tasks:
        tid, status, retries = t
        if tid in wave_ids:
            continue  # named in the wave header below, not here
        if tid in deferred_reasons:
            task_lines.append(
                f"  {tid} [{status}] → deferred (ready-set): "
                f"{deferred_reasons[tid]}."
            )
            continue
        if tid in attention_reasons:
            task_lines.append(
                f"  {tid} [{status}] → needs your judgment, not a dispatch "
                f"(ready-set): {attention_reasons[tid]}."
            )
            continue
        task_lines.append(
            _next_move(*t, *_marker_info(tid, fresh_markers, all_markers))
        )
    wave_block = _wave_block(wave)
    body_sections = ([wave_block] if wave_block else []) + [
        "\n".join(task_lines)
    ]
    body = "\n".join(body_sections)
    return _lib.block(
        f"{len(tasks)} task(s) still open—the turn can't end yet. "
        "Next move for each:\n"
        f"{body}\n"
        "Do the next move, then stop again. If you need to hand control back to "
        "the user mid-job, the user can `touch .agent-guild/state/PAUSED`."
    )


if __name__ == "__main__":
    _lib.run("stop-gate", main)
