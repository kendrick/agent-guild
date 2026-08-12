#!/usr/bin/env python3
"""Stop: the orchestrator can't end its turn while tasks are unfinished.

SubagentStop can validate that a worker followed protocol, but a hook can't
dispatch the checker that has to run next. This gate is what compels it: while
any task is non-terminal, the main session is blocked from stopping and handed
the exact next move for each open task. That closes the loop—worker returns,
gate refuses to let the turn end until the checker is dispatched and its verdict
acted on.

Livelock guard: if the same open-task state blocks three times in a row while
stop_hook_active is set, the gate gives up loudly—it writes .agent-guild/state/STALLED.md
naming the stuck tasks and lets the turn end, rather than spinning forever. Any
real progress resets the counter: a status change, a retry change, or a verdict
landing.

A subagent that's genuinely still working is not real progress by that
definition, but it isn't a stall either (#111). _lib.in_flight() names every
dispatch still inside its freshness TTL, and its fresh names ride in the
digest alongside the task/verdict/debt state. A task whose dispatch is still
fresh holds the counter rather than advancing it—dispatching again would
duplicate a subagent already running, and declaring the loop stuck would be
just as wrong. A marker that outlives its TTL is worth nothing: staleness is
what lets the backstop resume on a dead agent without anyone clearing state
by hand.

Waves also fire this gate twice for ONE real blocked turn when both the
plugin's hooks.json and a copy-in settings.json are registered (#41): same
task state, same verdict set, same markers, because nothing has actually
happened between the two firings. The digest alone can't tell that apart from
a genuine second strike, so the state file also persists the main
transcript's byte size. Two firings against an unchanged transcript are one
real block, not two, and the counter holds rather than advancing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

STALL_LIMIT = 3


def _next_move(tid, status, retries, debts, marker_state=None, marker_ts=None):
    # A task can sit at `checking` with its checker of record already landed
    # and only the courier crossing still missing. The generic "act on the
    # verdict" line in `moves` lets a well-behaved orchestrator walk straight
    # past that and call the task complete before the debt registers
    # anywhere, and the debt list in the block message only catches it after
    # the fact—so name the courier here instead. Matched to THIS retry round
    # (not just this task) because an older round's still-open debt from a
    # prior FAIL survives a rework cycle and shouldn't be mistaken for the
    # current round's own crossing. Takes precedence over the marker-based
    # wording below on purpose: a task can reach this branch with its own
    # in-flight marker already cleared (the checker of record already
    # returned), and the debt is still the more specific, more actionable
    # thing to say.
    if status == "checking" and any(
        d_tid == tid and d_stem.endswith(f"-r{retries}")
        for d_tid, d_stem, _lane in debts
    ):
        return (
            f"  {tid} [{status}] → its checker of record has landed but the "
            "second opinion hasn't; dispatch checker-courier before "
            "completing."
        )
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


def _state_file():
    return _lib.state_path("log", "stop-gate.state")


def _verdict_landed_for(tid, retries):
    """True if a verdict of record for `tid` at THIS retry round is on disk.

    Round-scoped on purpose, matching the courier-debt branch above: an older
    round's verdict survives a rework cycle, and treating it as this round's
    would tell the orchestrator to act on a verdict that judged a different
    artifact. Lane-suffixed files (`...-r0-codex.json`) are second opinions,
    never the verdict of record, so they don't count.
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
    try:
        with open(_state_file(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"digest": None, "count": 0, "transcript_size": None}


def _save_state(digest, count, transcript_size=None):
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        with open(_state_file(), "w", encoding="utf-8") as f:
            json.dump(
                {"digest": digest, "count": count, "transcript_size": transcript_size},
                f,
            )
    except Exception:
        pass


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

    # Computed before open_tasks()'s early exit below, on purpose: that call
    # drops terminal tasks, so a task the orchestrator already moved to
    # `complete` is invisible to everything past this line—exactly the state
    # the 2026-08-02 Claude run ended in, a completed T-001 with no crossing,
    # and the gate said nothing because nothing here ever looked. A debt
    # survives status changes the open-task picture doesn't, so it has to be
    # checked independently of whether any task is still open.
    debts = _lib.second_opinion_debts(data)
    tasks = _lib.open_tasks()
    if not tasks and not debts:
        # Clean slate—clear any stale block counter and let the turn end.
        _save_state(None, 0)
        return 0

    # Fresh markers ride in the digest itself, so a dispatch, a return, or a
    # staleness transition (nothing renewing a marker before its TTL lapses)
    # each change it exactly like a status or retry change would (#111).
    fresh_markers = _lib.in_flight()
    digest = json.dumps([sorted(tasks), _verdicts_landed(), debts, fresh_markers])
    prev = _load_state()
    stop_active = bool(data.get("stop_hook_active"))
    transcript_size = _transcript_size(data)

    same_digest = digest == prev.get("digest")
    # Held, not reset: a fresh marker on any open task means something is
    # genuinely still running, so an unchanged digest is expected, not a
    # symptom of being stuck. Advancing here would race a legitimate
    # long-running dispatch toward STALLED.md; resetting to 1 would hide a
    # REAL stall that happens to start the moment a marker goes fresh.
    has_fresh_marker_on_open_task = any(
        any(m.startswith(f"{t[0]}--") for m in fresh_markers) for t in tasks
    )
    # Held for a second, distinct reason (#41): the identical transcript size
    # across two firings with an otherwise-unchanged digest means the same
    # real Stop event fired this gate twice (double registration), not that
    # the orchestrator blocked, did nothing, and got blocked again. Only
    # compared when both sides are known—an absent transcript_path (most of
    # this test suite, and any host that doesn't supply one) must fall
    # through to the ordinary advance-or-hold-by-marker logic below, not
    # silently freeze the counter on None == None.
    same_transcript_size = (
        transcript_size is not None
        and prev.get("transcript_size") is not None
        and transcript_size == prev.get("transcript_size")
    )

    if same_digest:
        if has_fresh_marker_on_open_task or same_transcript_size:
            count = int(prev.get("count", 0))  # held: no increment, no reset
        else:
            count = int(prev.get("count", 0)) + 1
    else:
        count = 1

    # Livelock backstop: same unfinished state, already in a continuation loop,
    # tripped the limit. Give up loudly instead of blocking forever.
    if stop_active and same_digest and count >= STALL_LIMIT:
        lines = [
            "# STALLED",
            "",
            f"The stop gate blocked {count} times with no change to these tasks "
            f"and no verdict landing:",
            "",
        ] + [f"- {t[0]} [{t[1]}] retries={t[2]}" for t in tasks] + [
            f"- {d_tid}: second opinion outstanding for {d_stem}-{d_lane}.json"
            for d_tid, d_stem, d_lane in debts
        ] + [
            "",
            "The gate has stood down so the turn can end. Investigate by hand: a "
            "checker owing a verdict, a dispute needing a ruling, a second "
            "opinion nobody dispatched, or a task that should be marked "
            "abandoned. Delete this file once resolved.",
        ]
        try:
            with open(_lib.state_path("STALLED.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
        _save_state(digest, count, transcript_size)
        return 0

    _save_state(digest, count, transcript_size)

    all_markers = _lib.in_flight(ttl=float("inf"))
    task_lines = [
        _next_move(*t, debts, *_marker_info(t[0], fresh_markers, all_markers))
        for t in tasks
    ]
    # Named by the missing FILE, not the bare stem: a debt's `stem` is the
    # verdict-of-record's own name (T-001-sonnet-r0), and printing that alone
    # would point the orchestrator at the file that already exists instead of
    # the lane-suffixed one (T-001-sonnet-r0-codex.json) that's actually
    # missing.
    debt_lines = [
        f"  {d_tid}: second opinion outstanding—dispatch checker-courier to "
        f"write {d_stem}-{d_lane}.json."
        for d_tid, d_stem, d_lane in debts
    ]
    body = "\n".join(task_lines + debt_lines)
    return _lib.block(
        f"{len(tasks)} task(s) still open and {len(debts)} second opinion(s) "
        "outstanding—the turn can't end yet. Next move for each:\n"
        f"{body}\n"
        "Do the next move, then stop again. If you need to hand control back to "
        "the user mid-job, the user can `touch .agent-guild/state/PAUSED`."
    )


if __name__ == "__main__":
    _lib.run("stop-gate", main)
