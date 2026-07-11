#!/usr/bin/env python3
"""PreToolUse(Task|Agent): every guild dispatch is legal, tagged, and logged.

Non-guild subagents pass through untouched. For a worker/checker/auditor
dispatch, this blocks unless:

  - the prompt carries a `Task-ID: T-NNN` (or `Audit-ID:`) line, so
    subagent-return can later identify what finished;
  - that task file exists;
  - the dispatch is state-legal for the role (worker ⇒ assigned,
    checker ⇒ checking);
  - a worker's tier budget isn't already spent (retries within max), catching
    a forgotten escalation;
  - a worker's dispatched model matches the task's current tier, catching a
    forgotten model override after an escalation;
  - for workers, the constitution has a PASS audit—verification reaches the
    orchestrator's own work before any worker builds against it.

Every passing dispatch appends one line to state/log/dispatches.log.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402


def _log(agent, task, model):
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(_lib.state_path("log", "dispatches.log"), "a", encoding="utf-8") as f:
            f.write(f"{ts} | {agent} | {task} | {model}\n")
    except Exception:
        # Logging is best-effort; never let it turn a legal dispatch into a block.
        pass


def main(data):
    ti = data.get("tool_input", {}) or {}
    agent = ti.get("subagent_type", "")
    if agent not in _lib.GUILD_AGENTS:
        return 0

    prompt = ti.get("prompt", "") or ""
    override = (ti.get("model") or "").strip().lower()

    # 1. The dispatch must name what it's working on.
    tm = _lib.TASK_ID_RE.search(prompt)
    am = _lib.AUDIT_ID_RE.search(prompt)
    if not tm and not am:
        want = "Audit-ID: CON-audit" if agent == "auditor" else "Task-ID: T-NNN"
        return _lib.block(
            f"Dispatch to {agent} has no id line. Put `{want}` in the prompt so "
            "the return gate can identify this subagent's work when it finishes."
        )

    # Auditor path: id is CON-audit / DEC-audit, no task file, no tier logic.
    if agent == "auditor":
        _log(agent, am.group(1), override or _lib.DEFAULT_MODEL[agent])
        return 0

    tid = tm.group(1) if tm else None
    if tid is None:
        return _lib.block(
            f"Dispatch to {agent} names an Audit-ID but {agent} is not the "
            "auditor. Workers and checkers take a Task-ID."
        )

    task = _lib.read_task(tid)
    if task is None:
        return _lib.block(
            f"Dispatch to {agent} references {tid}, but state/tasks/{tid}.md "
            "does not exist. Create the task before dispatching."
        )

    status = str(task.get("status", "")).strip()
    effective_model = override or _lib.DEFAULT_MODEL[agent]

    if agent in _lib.CHECKER_AGENTS:
        if status != "checking":
            return _lib.block(
                f"{tid} is '{status}', not 'checking'. Set status to checking "
                "and update the task before dispatching its checker."
            )
        _log(agent, tid, effective_model)
        return 0

    # Worker path.
    if not _lib.con_audit_passed():
        return _lib.block(
            "No PASS constitution audit yet. Run /constitution, then dispatch "
            "the auditor (Audit-ID: CON-audit) and get a PASS before any worker "
            "builds against the constitution. Verification applies to all ranks."
        )

    if status != "assigned":
        return _lib.block(
            f"{tid} is '{status}', not 'assigned'. A worker runs only on an "
            "assigned task. If this is rework, set status back to assigned "
            "first; if it's a fresh task, move it pending → assigned."
        )

    executor = str(task.get("executor", "")).strip()
    if executor and agent != executor:
        return _lib.block(
            f"{tid} names executor '{executor}', but this dispatch is to "
            f"'{agent}'. Escalation bumps the model, not the agent—dispatch "
            f"'{executor}' with a model override, or fix the task's executor."
        )

    tier = str(task.get("executor_model", "")).strip().lower()
    if tier and effective_model != tier:
        return _lib.block(
            f"{tid} is at tier '{tier}', but this dispatch would run on "
            f"'{effective_model}'. Pass model:'{tier}' on the Agent call so the "
            "model matches the task's current tier (an escalation that updated "
            "executor_model but not the dispatch is the usual cause)."
        )

    try:
        retries = int(str(task.get("retries", "0")).strip() or "0")
        max_retries = int(str(task.get("max_retries", "2")).strip() or "2")
    except ValueError:
        retries, max_retries = 0, 2

    if retries > max_retries:
        if tier == "fable":
            return _lib.block(
                f"{tid} has exhausted the top (fable) tier. Do not dispatch "
                "further—surface this to the user, or enrich the spec and "
                "reset. The ladder has no rung above fable."
            )
        return _lib.block(
            f"{tid} has spent its retry budget at tier '{tier}' "
            f"(retries {retries} > max {max_retries}). Escalate: bump "
            "executor_model to the next tier, reset retries to 0, append an "
            "entry to `escalations`, and log it to state/log/escalations.log."
        )

    _log(agent, tid, effective_model)
    return 0


if __name__ == "__main__":
    _lib.run("dispatch-guard", main)
