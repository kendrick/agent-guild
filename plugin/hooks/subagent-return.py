#!/usr/bin/env python3
"""SubagentStop: a guild subagent can't finish until it left the right trace.

A hook can't dispatch follow-on work, but it can refuse to let a subagent call
itself done when it skipped the protocol. Exit 2 feeds the reason back and the
subagent keeps working.

  Workers must have set their task to needs-check (or disputed) and listed the
  artifacts they produced. "I'm done" in prose doesn't count; the state file
  has to say so.

  Checkers must have written a verdict of record at
  state/verdicts/T-NNN-<tier>-r<retries>.json that conforms to
  verdict.schema.json (checked via validate-verdict.py, not hand-parsed here—
  one schema, one validator, no drift between what the hook accepts and what
  the checker agents are told to produce). The auditor still writes the older
  Markdown verdict shape (audit verdicts are out of scope for the JSON
  migration; see the constitution's non-goals), so its check is unchanged.

  We deliberately do NOT require the rendered `.md` sibling to exist here.
  The JSON is the record of record; the renderer is the checker's documented
  obligation, and the orchestrator can re-render it from the JSON at any
  time. Gating a subagent's return on a cosmetic artifact that's trivially
  reproducible from the one that matters would make this gate brittle for no
  safety gain.

Identifying which task finished means reading the subagent's transcript for its
Task-ID/Audit-ID. That parsing depends on Claude Code's transcript format, which
is not a stable contract. When identification fails we do NOT block: blocking a
subagent over something it can't fix only hangs it (this gate has no stall backstop
the way stop-gate does), so an id failure fails loud and lets the subagent finish,
leaving the task open for the main-session stop-gate to catch. This is the kit's
most version-fragile point; the fixture tests pin the expected shape.
"""
import os
import re
import subprocess
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


def _validate_verdict_json(path):
    """(ok, reason) for a checker's verdict-of-record JSON. reason is None on
    success; on failure it's a message naming the failing path—either this
    file's own path (missing/unreadable) or the JSON path within it that
    validate-verdict.py rejected (e.g. "findings[0].evidence").

    Runs validate-verdict.py as a subprocess rather than importing it: the
    script's filename has a hyphen (not import-able without importlib
    surgery), its CLI is the documented contract, and invoking it the same
    way test_verdict_tools.py does means this gate can never drift from what
    that contract actually enforces."""
    if not os.path.exists(path):
        return False, f"no verdict JSON at {os.path.relpath(path, _lib.project_dir())}"
    validator = os.path.join(_lib.project_dir(), ".agent-guild", "scripts", "validate-verdict.py")
    proc = subprocess.run(
        [sys.executable, validator, path], capture_output=True, text=True,
    )
    if proc.returncode == 0:
        return True, None
    detail = proc.stderr.strip() or f"validate-verdict.py exited {proc.returncode}"
    return False, detail


def _latest_audit_verdict(audit_id):
    vdir = _lib.state_path("verdicts")
    if not os.path.isdir(vdir):
        return None
    matches = sorted(
        n for n in os.listdir(vdir)
        if n.startswith(audit_id + "-r") and n.endswith(".md")
    )
    return os.path.join(vdir, matches[-1]) if matches else None


def _unidentifiable(reason):
    """We can't tell which task this subagent ran. Blocking it can't help—it can't
    fix a bad transcript by trying again—and this gate has no stall backstop, so a
    block here hangs the subagent forever (a worker once had to write PAUSED to
    break exactly this loop). Fail LOUD but let it finish: the task stays open, so
    the main-session stop-gate still forces the orchestrator to verify it, which is
    where enforcement lives anyway. Never silent—the reason hits stderr and the log."""
    msg = (
        "subagent-return could not identify this subagent's task: " + reason
        + ". Letting it finish instead of hanging; the stop-gate will catch the "
        "still-open task on the main side. If this recurs, Claude Code's transcript "
        "shape probably changed—see id_from_transcript and its fixtures."
    )
    try:
        with open(_lib.state_path("log", "return-gate.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    sys.stderr.write(msg + "\n")
    return 0


def main(data):
    agent = data.get("agent_type", "")
    if agent not in _lib.GUILD_AGENTS:
        return 0  # matcher should exclude these, but don't assume

    transcript = data.get("transcript_path")
    if not transcript or not os.path.exists(transcript):
        return _unidentifiable(f"transcript_path missing or unreadable ({transcript!r})")

    try:
        ident = _lib.id_from_transcript(transcript)
    except Exception as exc:
        return _unidentifiable(f"no id readable from the transcript ({exc})")

    # Audition runs have no task file and no verdict; the battery scorer judges
    # them, not this gate. Nothing to validate, so let the subagent finish.
    if re.match(r"^A-\d+$", ident):
        return 0

    if agent == "auditor":
        vpath = _latest_audit_verdict(ident)
        if vpath is None:
            return _lib.block(
                f"Auditor finished without writing a verdict for {ident}. Write "
                f".agent-guild/state/verdicts/{ident}-r0.md (or the next round) with a "
                "verdict of PASS/FAIL/ERROR before finishing."
            )
        ok, reason = _verdict_ok(vpath)
        if not ok:
            return _lib.block(f"Auditor verdict for {ident} is not valid: {reason}.")
        return 0

    task = _lib.read_task(ident)
    if task is None:
        return _unidentifiable(f"{ident} has no task file")

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

    # Checker. The verdict of record is JSON; validate-verdict.py is the one
    # place schema + semantic rules live, so this gate defers to it entirely
    # rather than re-deriving conformance itself.
    tier = str(task.get("executor_model", "")).strip().lower()
    retries = str(task.get("retries", "0")).strip() or "0"
    rel = f".agent-guild/state/verdicts/{ident}-{tier}-r{retries}.json"
    vpath = _lib.state_path("verdicts", f"{ident}-{tier}-r{retries}.json")
    ok, reason = _validate_verdict_json(vpath)
    if not ok:
        return _lib.block(
            f"Checker for {ident} isn't done: verdict JSON at {rel} is missing or "
            f"invalid ({reason}). Write a conforming verdict per "
            ".agent-guild/schemas/verdict.schema.json, self-check it with "
            "python3 .agent-guild/scripts/validate-verdict.py, then finish."
        )
    return 0


if __name__ == "__main__":
    _lib.run("subagent-return", main)
