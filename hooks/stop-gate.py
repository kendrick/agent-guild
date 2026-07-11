#!/usr/bin/env python3
"""Stop: the orchestrator can't end its turn while tasks are unfinished.

SubagentStop can validate that a worker followed protocol, but a hook can't
dispatch the checker that has to run next. This gate is what compels it: while
any task is non-terminal, the main session is blocked from stopping and handed
the exact next move for each open task. That closes the loop—worker returns,
gate refuses to let the turn end until the checker is dispatched and its verdict
acted on.

Livelock guard: if the same open-task state blocks three times in a row while
stop_hook_active is set, the gate gives up loudly—it writes state/STALLED.md
naming the stuck tasks and lets the turn end, rather than spinning forever. Any
real progress (a status or retry change) resets the counter.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

STALL_LIMIT = 3


def _next_move(tid, status, retries):
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
    tasks = _lib.open_tasks()
    if not tasks:
        # Clean slate—clear any stale block counter and let the turn end.
        _save_state(None, 0)
        return 0

    digest = json.dumps(sorted(tasks))
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
            f"The stop gate blocked {count} times with no change to these tasks:",
            "",
        ] + [f"- {t[0]} [{t[1]}] retries={t[2]}" for t in tasks] + [
            "",
            "The gate has stood down so the turn can end. Investigate by hand: a "
            "checker owing a verdict, a dispute needing a ruling, or a task that "
            "should be marked abandoned. Delete this file once resolved.",
        ]
        try:
            with open(_lib.state_path("STALLED.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
        _save_state(digest, count)
        return 0

    _save_state(digest, count)

    body = "\n".join(_next_move(*t) for t in tasks)
    return _lib.block(
        f"{len(tasks)} task(s) still open—the turn can't end yet. Next move "
        "for each:\n"
        f"{body}\n"
        "Do the next move, then stop again. If you need to hand control back to "
        "the user mid-job, the user can `touch state/PAUSED`."
    )


if __name__ == "__main__":
    _lib.run("stop-gate", main)
