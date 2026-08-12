#!/usr/bin/env python3
"""PreToolUse(Task|Agent): every guild dispatch is legal, tagged, and logged.

Non-guild subagents pass through untouched. For a worker/checker/auditor
dispatch, this blocks unless:

  - the dispatch carries a `Task-ID: T-NNN` (or `Audit-ID:`), so
    subagent-return can later identify what finished—as a prompt line, or in
    `task_name` on a host that encrypts the prompt;
  - that task file exists, and names a check for the clauses it cites—a task
    with none is unverifiable, and its checker would report a pass on an empty
    check list (#109);
  - the dispatch is state-legal for the role (worker ⇒ assigned,
    checker ⇒ checking);
  - a worker's tier budget isn't already spent (retries within max), catching
    a forgotten escalation;
  - a worker's dispatched model matches the task's current tier, catching a
    forgotten model override after an escalation;
  - for workers, the constitution has a PASS audit—verification reaches the
    orchestrator's own work before any worker builds against it;
  - for an auditor, .agent-guild/scripts/check-job-spec.py doesn't reject the
    paperwork first—so an opus auditor is never spent on a defect a stdlib
    script could have proven in about two seconds (#132).

A legal checker-courier dispatch also reserves its crossing (_lib.reserve_crossing)
before returning—#141's fix for #100, where a courier dispatched for T-001 wrote
T-002's verdict and nothing tied that file to any dispatch. subagent-return.py
promotes the same reservation once the return validates.

A Codex followup, which re-tasks a running agent rather than spawning one, is
refused outright when it targets a guild agent: it carries nothing left to
check (#77).

Every passing dispatch appends one line to .agent-guild/state/log/dispatches.log.
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402


def _log(agent, task, model):
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        # Use UTC with a trailing Z to match verdict and ledger timestamps.
        # dispatches.log is compared against those timestamps to establish
        # ordering, and a local-time stamp is silently wrong by the machine's offset.
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(_lib.state_path("log", "dispatches.log"), "a", encoding="utf-8") as f:
            f.write(f"{ts} | {agent} | {task} | {model}\n")
    except Exception:
        # Logging is best-effort; never let it turn a legal dispatch into a block.
        pass


def _log_gate_gap(ident, timeout_s):
    """Best-effort record that check-job-spec didn't finish for `ident`, so
    the auditor dispatched with the paperwork gate un-consulted. Same path
    resolution and bare except Exception: pass posture as _log above—this is
    the one thing that makes an allow-through-on-timeout auditable instead of
    silent, so it must never itself be the reason a dispatch fails."""
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(_lib.state_path("log", "gate-gaps.log"), "a", encoding="utf-8") as f:
            f.write(
                f"{ts} | check-job-spec | {ident} | timed out after "
                f"{timeout_s}s, auditor dispatched with the gate un-run\n"
            )
    except Exception:
        pass


def _join_sentence(lead, tail):
    """Join two sentence fragments so the result reads as prose regardless of
    whether `lead` (the linter's own stderr line) already ends in
    punctuation. Without this, a stderr line with no trailing period runs
    straight into the sentence appended after it."""
    lead = lead.rstrip()
    if lead and lead[-1] not in ".!?":
        lead += "."
    return f"{lead} {tail}"


# 20s: real headroom over the ~3s check-job-spec takes on a 7-task job today,
# while staying well clear of the PreToolUse hook's own 30s budget (see
# plugin/hooks/hooks.json)—that budget covers this subprocess plus Python
# startup plus every check_method's own work, so the gap between 20 and 30
# has to absorb all of that, not just the linter's run time.
#
# Test-only seam: production always waits the full JOB_SPEC_TIMEOUT_S below.
# The timeout test needs to actually exercise a real subprocess.run() timeout
# to prove the branch works, and waiting out a real 20s would make every run
# of this suite crawl. AGENT_GUILD_JOB_SPEC_TIMEOUT lets that one test shrink
# the wait to a fraction of a second while running the identical code path;
# no real dispatch has any reason to set it.
JOB_SPEC_TIMEOUT_S = float(os.environ.get("AGENT_GUILD_JOB_SPEC_TIMEOUT", "20"))


def _job_spec_block(ident):
    """None if the auditor may proceed for `ident`; else the message to hand
    _lib.block(). Shells out to check-job-spec.py rather than importing it,
    same reasoning as subagent-return.py's validate-verdict.py call: the CLI
    is the documented contract, and a subprocess can't drift from it.

    Missing script and a stalled linter both resolve to None (let the auditor
    through), not a block. install.py never upgrades a project's copied-in
    .agent-guild/ payload (see _working-memory/conventions.md's payload-freeze
    note), so a repo can be running hooks newer than its own scripts/—and a
    gate that hard-fails when check-job-spec.py simply isn't there yet would
    brick every auditor dispatch on that payload. A timeout gets the same
    allow-through, for the same deadlock-avoidance reason: a hard fail on a
    slow linter would block every job behind it. But it is not the same as
    "free"—an unresponsive linter is exactly the epistemic state exit 3 is,
    "the gate did not run," and unlike exit 3 it would otherwise be silent.
    That's a real gap: the auditor still runs, but nothing checked the
    paperwork first, and #132 exists because that check catches things worth
    catching. _log_gate_gap() and the stderr note below are what keep the gap
    auditable instead of invisible.
    """
    linter = os.path.join(_lib.project_dir(), ".agent-guild", "scripts", "check-job-spec.py")
    if not os.path.exists(linter):
        return None
    repo_root = _lib.project_dir()
    cmd = [sys.executable, linter, "--audit-id", ident, "--repo-root", repo_root]
    reproduce = f"python3 {linter} --audit-id {ident} --repo-root {repo_root}"
    try:
        proc = subprocess.run(
            cmd, cwd=repo_root, capture_output=True, text=True,
            timeout=JOB_SPEC_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        _log_gate_gap(ident, JOB_SPEC_TIMEOUT_S)
        sys.stderr.write(
            f"dispatch-guard: check-job-spec timed out after "
            f"{JOB_SPEC_TIMEOUT_S:g}s for {ident}—the paperwork gate did not "
            f"run for this dispatch. Logged to "
            ".agent-guild/state/log/gate-gaps.log; the auditor is dispatched "
            "unchecked.\n"
        )
        return None
    if proc.returncode == 0:
        return None
    if proc.returncode == 3:
        return (
            f"check-job-spec couldn't read the paperwork for {ident} (exit "
            f"3): {proc.stderr.strip()}. An infra failure isn't evidence the "
            f"paperwork is sound—fix whatever check-job-spec choked on, then "
            f"reproduce with: {reproduce}"
        )
    detail = proc.stderr.strip() or f"check-job-spec exited {proc.returncode}"
    return _join_sentence(
        detail,
        "Fix that before spending an opus auditor on a defect a script "
        f"already proved. Reproduce with: {reproduce}",
    )


def main(data):
    # Intended scope: no in_subagent no-op here, and none is needed. Unlike
    # stop-gate or orchestrator-write-guard, this hook doesn't constrain the
    # orchestrator's own turn—it constrains every Task/Agent dispatch, wherever
    # it originates. A nested guild dispatch (one subagent spinning up another)
    # has to carry the same Task-ID/Audit-ID and pass the same legality checks
    # as a top-level one, so this gate deliberately fires inside subagents too.
    ti = data.get("tool_input", {}) or {}

    # A followup re-tasks an agent that already exists, so it names no agent
    # type and carries no readable prompt: its message is encrypted like every
    # other Codex dispatch message. All it names is the target's agent path,
    # built from the `task_name` of the spawn that created it. If any segment
    # of that path parses as a guild id, work is being handed to a guild agent
    # behind this gate's back, skipping every check below. SubagentStop still
    # fires afterward, so the return gate ends up judging work no dispatch
    # gate ever authorized. Refusal is the only move left, since there's
    # nothing here to check the call against.
    target = ti.get("followup_target")
    if target is not None:
        for segment in str(target).split("/"):
            kind, ident = _lib.bare_id(segment)
            if kind is None:
                continue
            wire = ident.replace("-", "_").lower()
            return _lib.block(
                f"Re-tasking {ident}'s agent through followup_task is not "
                "allowed. This call names no agent type and its message is "
                "encrypted, so none of the dispatch checks can run against "
                "it—yet the return gate will still judge whatever comes back. "
                "Spawn a fresh agent instead, with task_name set to a name no "
                f"dispatch in this session has used yet ({wire}_r0_checker, "
                "say). One name per dispatch, not one per task."
            )
        return 0

    raw = ti.get("subagent_type", "")
    agent = _lib.bare_agent(raw)
    if agent not in _lib.GUILD_AGENTS:
        return 0

    prompt = ti.get("prompt", "") or ""
    override = (ti.get("model") or "").strip().lower()

    # Two mechanisms carry the same id, because one host makes the other
    # impossible: Codex encrypts the dispatch `message` before any hook runs,
    # so a labelled line in the prose has nothing to match against. There the
    # adapter lifts the dispatcher-set `task_name` into `dispatch_id`, which is
    # readable at dispatch and again at return (#71). The structured field wins
    # where both exist—it's the one the dispatcher set deliberately.
    kind, ident = _lib.bare_id(ti.get("dispatch_id"))
    if kind is None:
        aud = _lib.AUDITION_ID_RE.search(prompt)
        tm = _lib.TASK_ID_RE.search(prompt)
        am = _lib.AUDIT_ID_RE.search(prompt)
        match = aud or tm or am
        if match:
            kind = "audition" if aud else ("task" if tm else "audit")
            ident = match.group(1)

    # Audition path: a tryout runs outside the lifecycle—no task file, no tier,
    # no CON-audit precondition. An Audition-ID is enough to log and pass; the
    # battery's score.py judges the output, not this gate.
    if kind == "audition":
        _log(raw, ident, override or _lib.DEFAULT_MODEL[agent])
        return 0

    # 1. The dispatch must name what it's working on.
    if kind is None:
        want = "Audit-ID: CON-audit" if agent == "auditor" else "Task-ID: T-NNN"
        if str(data.get("hook_host", "")).strip().lower() == "codex":
            # Underscores, not the canonical hyphen: this host rejects a
            # task_name outside [a-z0-9_], so quoting `T-NNN` here would send
            # the operator to fix one block by tripping a different one.
            bare = "con_audit" if agent == "auditor" else "t_nnn"
            return _lib.block(
                f"Dispatch to {agent} carries no readable id. This host "
                f"encrypts the dispatch message, so set task_name to `{bare}` "
                "instead (lowercase and underscored, which is all this host "
                "accepts there). That field survives to the return gate, "
                "which is what identifies this work when it finishes."
            )
        return _lib.block(
            f"Dispatch to {agent} has no id line. Put `{want}` in the prompt so "
            "the return gate can identify this subagent's work when it finishes."
        )

    # Auditor path: id is CON-audit / DEC-audit, no task file, no tier logic.
    if agent == "auditor":
        if kind != "audit":
            return _lib.block(
                f"Dispatch to auditor names {ident}, but the auditor takes an "
                "Audit-ID (CON-audit or DEC-audit). Workers and checkers take "
                "a Task-ID."
            )
        job_spec_msg = _job_spec_block(ident)
        if job_spec_msg:
            return _lib.block(job_spec_msg)
        _log(raw, ident, override or _lib.DEFAULT_MODEL[agent])
        return 0

    tid = ident if kind == "task" else None
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

    # Ahead of the role split on purpose: a task that cites clauses and names
    # no check is undispatchable to anyone. Sending the worker means building
    # against a standard nothing will measure; sending the checker means a
    # verdict derived from an empty check list.
    defect = _lib.unverifiable(tid, task)
    if defect:
        return _lib.block(defect)

    status = str(task.get("status", "")).strip()
    effective_model = override or _lib.DEFAULT_MODEL[agent]

    if agent in _lib.CHECKER_AGENTS:
        is_courier = agent == "checker-courier"
        # A debt only relaxes the status check for the courier itself, and
        # only when one is actually outstanding on this task—`complete` and
        # `rework` are the two statuses second_opinion_debts() finds a task
        # parked at with a crossing still owed, so this is what lets a debt
        # survive a FAIL verdict rather than clearing on the next status
        # change. checker-deterministic and checker-judgment never set this,
        # so their branch below is untouched: they still require `checking`
        # no matter what the debt ledger says.
        owes_debt = is_courier and any(
            d_tid == tid for d_tid, _stem, _lane in _lib.second_opinion_debts(data)
        )
        if status != "checking" and not owes_debt:
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
        #
        # The courier is explicitly not a second gate—CLAUDE.md's dual-check
        # section says the standard-stem verdict alone decides complete or
        # rework—so its dispatch legality doesn't need to track the task's
        # gate status the way an in-family checker's does. A debt is owed
        # precisely because nothing reopened the task to collect it, so
        # requiring `checking` here would make the debt permanently
        # uncollectable on any task the orchestrator already moved on from.
        # Every OTHER courier condition below—model override, workspace
        # access, exhausted lane—still applies unconditionally.
        if agent == "checker-courier":
            if override:
                return _lib.block(
                    f"Dispatch to checker-courier for {tid} carries a model "
                    f"override ({override!r}). Drop the override—the courier "
                    "runs its host-selected lane and pinned far-side model."
                )
            if "workspace-write" in prompt or "danger-full-access" in prompt:
                return _lib.block(
                    f"Dispatch to checker-courier for {tid} requests "
                    "workspace-write or danger-full-access. The lane is "
                    "read-only by contract; drop the request."
                )
            lane = _lib.courier_lane(data)
            effective_model = lane
            if _lib.lane_exhausted(lane):
                return _lib.block(
                    f"checker-courier's '{lane}' lane is exhausted "
                    f"(.agent-guild/state/exhausted/{lane} exists). Nothing is "
                    f"substituted: {tid}'s checker of record ran before the "
                    "courier went out, so its verdict already stands and no "
                    "retry budget moves. The sentinel is user-cleared, like "
                    "PAUSED."
                )
            # #141: reserve THIS dispatch's crossing before the courier ever
            # runs, so subagent-return.py has something to promote a return
            # against instead of trusting whatever filename shows up (#100,
            # where a courier dispatched for T-001 wrote T-002's verdict and
            # nothing tied that file to any dispatch). tier/retries are read
            # from the task file now, at the moment authorization is legal to
            # grant—not recomputed from a verdict filename later, which is
            # exactly the trust #100 exploited.
            courier_tier = str(task.get("executor_model", "")).strip().lower()
            courier_retries = str(task.get("retries", "0")).strip() or "0"
            stem = _lib.crossing_stem(tid, courier_tier, courier_retries)
            _lib.reserve_crossing(tid, stem, lane)
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
