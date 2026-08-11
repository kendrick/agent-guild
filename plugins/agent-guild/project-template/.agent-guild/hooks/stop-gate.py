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
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

STALL_LIMIT = 3


def _next_move(tid, status, retries, debts):
    # A task can sit at `checking` with its checker of record already landed
    # and only the courier crossing still missing. The generic "act on the
    # verdict" line in `moves` lets a well-behaved orchestrator walk straight
    # past that and call the task complete before the debt registers
    # anywhere, and the debt list in the block message only catches it after
    # the fact—so name the courier here instead. Matched to THIS retry round
    # (not just this task) because an older round's still-open debt from a
    # prior FAIL survives a rework cycle and shouldn't be mistaken for the
    # current round's own crossing.
    if status == "checking" and any(
        d_tid == tid and d_stem.endswith(f"-r{retries}")
        for d_tid, d_stem, _lane in debts
    ):
        return (
            f"  {tid} [{status}] → its checker of record has landed but the "
            "second opinion hasn't; dispatch checker-courier before "
            "completing."
        )
    moves = {
        "pending": "assign it and dispatch its executor.",
        "assigned": "its worker hasn't returned; dispatch the executor, or it's "
                    "mid-flight.",
        "needs-check": "set status to checking and dispatch its checker.",
        "checking": "its checker is running or owes a verdict; act on the "
                    "verdict (complete, or copy the diagnosis into rework).",
        "rework": f"copy the checker's diagnosis into ## Rework diagnosis, set "
                  f"status back to assigned (retries {retries}), and re-dispatch "
                  "the same worker.",
        "disputed": "read the dispute, verdict, and artifact yourself and rule; "
                    "append the ruling and set the task to complete or rework.",
    }
    return f"  {tid} [{status}] → {moves.get(status, 'resolve this task.')}"


def _state_file():
    return _lib.state_path("log", "stop-gate.state")


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
        return {"digest": None, "count": 0}


def _save_state(digest, count):
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        with open(_state_file(), "w", encoding="utf-8") as f:
            json.dump({"digest": digest, "count": count}, f)
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

    digest = json.dumps([sorted(tasks), _verdicts_landed(), debts])
    prev = _load_state()
    stop_active = bool(data.get("stop_hook_active"))

    if digest == prev.get("digest"):
        count = int(prev.get("count", 0)) + 1
    else:
        count = 1

    # Livelock backstop: same unfinished state, already in a continuation loop,
    # tripped the limit. Give up loudly instead of blocking forever.
    if stop_active and digest == prev.get("digest") and count >= STALL_LIMIT:
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
        _save_state(digest, count)
        return 0

    _save_state(digest, count)

    task_lines = [_next_move(*t, debts) for t in tasks]
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
