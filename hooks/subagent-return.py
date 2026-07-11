#!/usr/bin/env python3
"""SubagentStop: a guild subagent can't finish until it left the right trace.

A hook can't dispatch follow-on work, but it can refuse to let a subagent call
itself done when it skipped the protocol. Exit 2 feeds the reason back and the
subagent keeps working.

  Workers must have set their task to needs-check (or disputed) and listed the
  artifacts they produced. "I'm done" in prose doesn't count; the state file
  has to say so.

  Checkers/auditor must have written the verdict file for the attempt they were
  checking, with a real verdict, and a Diagnosis section when it's a FAIL.

Identifying which task finished means reading the subagent's transcript for its
Task-ID/Audit-ID. That parsing depends on Claude Code's transcript format, which
is not a stable contract — so any failure to read it, or a missing id, is the
loud fail-closed path (HOOK ERROR, exit 2), never a quiet pass. This is the kit's
most version-fragile point; the fixture tests pin the expected shape.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402


def _has_diagnosis(verdict_text):
    """True if a FAIL verdict carries actionable diagnosis, not just the
    template's comment placeholder."""
    idx = verdict_text.find("## Diagnosis")
    if idx == -1:
        return False
    tail = verdict_text[idx + len("## Diagnosis"):]
    tail = re.sub(r"<!--.*?-->", "", tail, flags=re.DOTALL)
    return bool(tail.strip())


def _verdict_ok(path, require_diagnosis_on_fail=True):
    """(ok, reason). ok=True if the file holds a valid verdict (and a FAIL has
    a diagnosis). ok=False with a reason the subagent can act on."""
    if not os.path.exists(path):
        return False, f"no verdict at {os.path.relpath(path, _lib.project_dir())}"
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm = _lib.parse_frontmatter(text)
    verdict = str(fm.get("verdict", "")).strip().upper()
    if verdict not in ("PASS", "FAIL", "ERROR"):
        return False, f"verdict field is '{verdict or 'missing'}', not PASS/FAIL/ERROR"
    if verdict == "FAIL" and require_diagnosis_on_fail and not _has_diagnosis(text):
        return False, "verdict is FAIL but has no actionable ## Diagnosis section"
    return True, verdict


def _latest_audit_verdict(audit_id):
    vdir = _lib.state_path("verdicts")
    if not os.path.isdir(vdir):
        return None
    matches = sorted(
        n for n in os.listdir(vdir)
        if n.startswith(audit_id + "-r") and n.endswith(".md")
    )
    return os.path.join(vdir, matches[-1]) if matches else None


def main(data):
    agent = data.get("agent_type", "")
    if agent not in _lib.GUILD_AGENTS:
        return 0  # matcher should exclude these, but don't assume

    transcript = data.get("transcript_path")
    if not transcript or not os.path.exists(transcript):
        # Fail closed: we can't identify the work, so we can't clear it.
        raise ValueError(
            f"transcript_path missing or unreadable ({transcript!r}); cannot "
            "identify which task this subagent ran"
        )

    # Raises on unreadable / unparseable / no-id — the fail-closed path.
    ident = _lib.id_from_transcript(transcript)

    if agent == "auditor":
        vpath = _latest_audit_verdict(ident)
        if vpath is None:
            return _lib.block(
                f"Auditor finished without writing a verdict for {ident}. Write "
                f"state/verdicts/{ident}-r0.md (or the next round) with a "
                "verdict of PASS/FAIL/ERROR before finishing."
            )
        ok, reason = _verdict_ok(vpath)
        if not ok:
            return _lib.block(f"Auditor verdict for {ident} is not valid: {reason}.")
        return 0

    task = _lib.read_task(ident)
    if task is None:
        raise ValueError(f"{ident} has no task file; cannot validate the return")

    if agent in _lib.WORKER_AGENTS:
        status = str(task.get("status", "")).strip()
        artifacts = task.get("artifacts")
        if status not in ("needs-check", "disputed"):
            return _lib.block(
                f"Protocol incomplete for {ident}: status is '{status}'. When "
                "the work is done, set status to needs-check and list the files "
                "you produced in `artifacts`. If you believe the last FAIL was "
                "wrong, file a dispute instead (see your agent instructions)."
            )
        if not artifacts:
            return _lib.block(
                f"Protocol incomplete for {ident}: status is '{status}' but "
                "`artifacts` is empty. List the repo-relative paths you produced "
                "so the checker knows what to verify."
            )
        return 0

    # Checker.
    tier = str(task.get("executor_model", "")).strip().lower()
    retries = str(task.get("retries", "0")).strip() or "0"
    vpath = _lib.state_path("verdicts", f"{ident}-{tier}-r{retries}.md")
    ok, reason = _verdict_ok(vpath)
    if not ok:
        return _lib.block(
            f"Checker for {ident} isn't done: {reason}. Write the verdict at "
            f"state/verdicts/{ident}-{tier}-r{retries}.md (tier + retries from "
            "the task file), with PASS/FAIL/ERROR and, for a FAIL, a Diagnosis "
            "naming file, clause, and expected vs actual."
        )
    return 0


if __name__ == "__main__":
    _lib.run("subagent-return", main)
