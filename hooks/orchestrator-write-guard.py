#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit): keep the orchestrator out of deliverables.

The main session is the boss. It writes specs, constitutions, task files, and
dispute rulings — all under state/ — and dispatches workers for everything
else. This turns that contract from prompt language into mechanism: while a job
is active, a main-session write outside state/ is blocked with an instruction,
not a bare denial.

Parent hooks do not fire for tool calls made inside subagents (a verified Claude
Code behavior), so workers writing real deliverables are unaffected. Only the
orchestrator's own hands are tied.

No open job means no gate: during Phase 0, before any task exists, the
orchestrator writes the constitution and spec freely. That window is
prompt-enforced, by design.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402


def main(data):
    if _lib.no_job_active():
        return 0

    ti = data.get("tool_input", {}) or {}
    fp = ti.get("file_path") or ti.get("path") or ""
    if not fp:
        # Nothing to check (unexpected shape) — don't invent a target.
        return 0

    abs_fp = fp if os.path.isabs(fp) else os.path.join(_lib.project_dir(), fp)
    abs_fp = os.path.realpath(abs_fp)
    state_root = os.path.realpath(_lib.state_path())

    if abs_fp == state_root or abs_fp.startswith(state_root + os.sep):
        return 0

    rel = os.path.relpath(abs_fp, _lib.project_dir())
    return _lib.block(
        f"Orchestrator contract: you don't write deliverables. Blocked write to "
        f"{rel}.\n"
        "A job is active, so the boss orchestrates — it does not build. To make "
        "this change:\n"
        "  - create a task (scripts/new-task.py) and dispatch a worker to write "
        "it, or\n"
        "  - if this really is orchestration state, put it under state/, or\n"
        "  - if you genuinely must edit it yourself, the user can `touch "
        "state/PAUSED` to lift every gate."
    )


if __name__ == "__main__":
    _lib.run("orchestrator-write-guard", main)
