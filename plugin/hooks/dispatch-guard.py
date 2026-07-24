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

Every passing dispatch appends one line to .agent-guild/state/log/dispatches.log.
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
    # Intended scope: no in_subagent no-op here, and none is needed. Unlike
    # stop-gate or orchestrator-write-guard, this hook doesn't constrain the
    # orchestrator's own turn—it constrains every Task/Agent dispatch, wherever
    # it originates. A nested guild dispatch (one subagent spinning up another)
    # has to carry the same Task-ID/Audit-ID and pass the same legality checks
    # as a top-level one, so this gate deliberately fires inside subagents too.
    ti = data.get("tool_input", {}) or {}
    raw = ti.get("subagent_type", "")
    agent = _lib.bare_agent(raw)
    if agent not in _lib.GUILD_AGENTS:
        return 0

    prompt = ti.get("prompt", "") or ""
    override = (ti.get("model") or "").strip().lower()

    # Audition path: a tryout runs outside the lifecycle—no task file, no tier,
    # no CON-audit precondition. An Audition-ID is enough to log and pass; the
    # battery's score.py judges the output, not this gate.
    aud = _lib.AUDITION_ID_RE.search(prompt)
    if aud:
        _log(raw, aud.group(1), override or _lib.DEFAULT_MODEL[agent])
        return 0

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
        _log(raw, am.group(1), override or _lib.DEFAULT_MODEL[agent])
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
            f"Dispatch to {agent} references {tid}, but .agent-guild/state/tasks/{tid}.md "
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
        # Deliberate: this branch never reads the task's `checker` field, so
        # a dispatch is legal on ANY checking-status task regardless of which
        # in-family checker is named as checker of record. That's exactly
        # what the second-opinion contract needs—checker-courier below rides
        # this same allowance to run alongside the checker of record rather
        # than in place of it.
        if agent == "checker-courier":
            if override:
                return _lib.block(
                    f"Dispatch to checker-courier for {tid} carries a model "
                    f"override ({override!r}). Drop the override—the courier "
                    "runs its own default; there is no Claude model named codex."
                )
            if "workspace-write" in prompt or "danger-full-access" in prompt:
                return _lib.block(
                    f"Dispatch to checker-courier for {tid} requests "
                    "workspace-write or danger-full-access. The lane is "
                    "read-only by contract; drop the request."
                )
            lane = _lib.DEFAULT_MODEL[agent]
            if _lib.lane_exhausted(lane):
                in_family = str(task.get("checker", "")).strip() or "its checker of record"
                return _lib.block(
                    f"checker-courier's '{lane}' lane is exhausted "
                    f"(.agent-guild/state/exhausted/{lane} exists). Re-dispatch "
                    f"{tid}'s in-family checker ('{in_family}') instead—a "
                    "second-opinion denial costs nothing, the verdict of "
                    "record is unaffected. The sentinel is user-cleared, "
                    "like PAUSED."
                )
        _log(raw, tid, effective_model)
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
            "entry to `escalations`, and log it to .agent-guild/state/log/escalations.log."
        )

    _log(raw, tid, effective_model)
    return 0


if __name__ == "__main__":
    _lib.run("dispatch-guard", main)
