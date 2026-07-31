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

  checker-courier, the cross-vendor second-opinion role, uses the SAME stem
  plus its host lane suffix (…-codex.json from Claude; …-claude.json from
  Codex)—comparison data, never the verdict of record. A writable Claude
  courier validates at that file path; a read-only Codex courier returns the
  marked claude-courier.py outcome for validation before parent persistence.
  Quota uses the same ledger-first, lane-sentinel-second, no-verdict contract;
  Codex returns that outcome before the parent performs those writes.

  We deliberately do NOT require the rendered `.md` sibling to exist here.
  The JSON is the record of record; the renderer is the checker's documented
  obligation, and the orchestrator can re-render it from the JSON at any
  time. Gating a subagent's return on a cosmetic artifact that's trivially
  reproducible from the one that matters would make this gate brittle for no
  safety gain.

Identifying which task finished means reading the host transcript for its
Task-ID/Audit-ID. Claude Code and Codex both treat transcript representation as
unstable. When identification fails we do NOT block: blocking a subagent over
something it can't fix only hangs it (this gate has no stall backstop the way
stop-gate does), so an id failure fails loud and lets the subagent finish,
leaving the task open for the main-session stop-gate to catch. This is the
kit's most version-fragile point; the fixture tests pin both host shapes.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402


CODEX_COURIER_OUTCOME_MARKER = "AGENT_GUILD_COURIER_OUTCOME\n"
CODEX_VERDICT_MARKER = "AGENT_GUILD_VERDICT\n"
CLAUDE_COURIER_MODEL = "claude-haiku-4-5-20251001"


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


def _quota_return_ok(task_id, lane):
    """True if a courier's quota bailout (constitution C-3) is evidenced for
    this task: the lane's exhaustion sentinel is set AND the vendor ledger's
    LAST line for this task carries quota_event: true. Callers only reach
    this after confirming no suffixed verdict file exists—the third leg of
    the documented combination (ledger line, then sentinel, then no verdict,
    in that order) is absence, not something this function re-checks."""
    if not _lib.lane_exhausted(lane):
        return False
    ledger_path = _lib.state_path("log", "vendor-calls.jsonl")
    if not os.path.exists(ledger_path):
        return False
    last_for_task = None
    with open(ledger_path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue  # a courier crash mid-write can't poison a later line
            if rec.get("task_id") == task_id:
                last_for_task = rec
    return bool(last_for_task) and last_for_task.get("quota_event") is True


def _codex_courier_outcome_ok(message, task_id):
    """Validate a read-only Codex courier return before parent persistence.

    A Codex project agent cannot write its own verdict, ledger, or exhaustion
    sentinel. It returns the deterministic claude-courier.py outcome instead;
    this gate validates that handoff, then the parent persists it in the
    documented order. Claude-hosted couriers keep the original file-backed
    return contract below.
    """
    if not isinstance(message, str) or not message.startswith(
        CODEX_COURIER_OUTCOME_MARKER
    ):
        return (
            False,
            "last message must be the AGENT_GUILD_COURIER_OUTCOME marker "
            "followed by the runner's JSON object",
        )
    raw = message[len(CODEX_COURIER_OUTCOME_MARKER):].strip()
    try:
        outcome = json.loads(raw)
    except json.JSONDecodeError as error:
        return False, f"outcome JSON is malformed: {error}"
    if not isinstance(outcome, dict):
        return False, "outcome JSON is not an object"

    required = {
        "status",
        "verdict",
        "ledger",
        "attempts",
        "diagnostic",
    }
    if set(outcome) != required:
        return (
            False,
            "outcome fields must be exactly "
            f"{sorted(required)!r}, got {sorted(outcome)!r}",
        )
    status = outcome.get("status")
    if status not in {"verdict", "quota"}:
        return False, f"status is {status!r}, not 'verdict' or 'quota'"
    attempts = outcome.get("attempts")
    if type(attempts) is not int or attempts not in {1, 2}:
        return False, f"attempts is {attempts!r}, not 1 or 2"
    diagnostic = outcome.get("diagnostic")
    if diagnostic is not None and not isinstance(diagnostic, str):
        return False, "diagnostic is neither a string nor null"

    ledger = outcome.get("ledger")
    if not isinstance(ledger, dict):
        return False, "ledger is not an object"
    ledger_fields = {
        "task_id",
        "vendor",
        "model",
        "started_at",
        "duration_ms",
        "exit_code",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "quota_event",
    }
    if set(ledger) != ledger_fields:
        return (
            False,
            "ledger fields must be exactly "
            f"{sorted(ledger_fields)!r}, got {sorted(ledger)!r}",
        )
    expected_ledger = {
        "task_id": task_id,
        "vendor": "claude",
        "model": CLAUDE_COURIER_MODEL,
    }
    for key, expected in expected_ledger.items():
        if ledger.get(key) != expected:
            return (
                False,
                f"ledger.{key} is {ledger.get(key)!r}, expected "
                f"{expected!r}",
            )
    if not isinstance(ledger.get("started_at"), str) or not ledger[
        "started_at"
    ].strip():
        return False, "ledger.started_at is not a non-empty string"
    for key in ("duration_ms", "exit_code"):
        value = ledger.get(key)
        if type(value) is not int:
            return False, f"ledger.{key} is not an integer"
    if ledger["duration_ms"] < 0:
        return False, "ledger.duration_ms is negative"
    for key in ("tokens_in", "tokens_out"):
        value = ledger.get(key)
        if value is not None and (
            type(value) is not int or value < 0
        ):
            return (
                False,
                f"ledger.{key} is neither a non-negative integer nor null",
            )
    cost = ledger.get("cost_usd")
    if cost is not None and (
        isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or cost < 0
    ):
        return (
            False,
            "ledger.cost_usd is neither a non-negative number nor null",
        )
    quota_event = ledger.get("quota_event")
    if type(quota_event) is not bool:
        return False, "ledger.quota_event is not boolean"

    verdict = outcome.get("verdict")
    if status == "quota":
        if verdict is not None:
            return False, "quota outcome must carry verdict: null"
        if quota_event is not True:
            return False, "quota outcome must carry ledger.quota_event: true"
        return True, None

    if quota_event is not False:
        return False, "verdict outcome must carry ledger.quota_event: false"
    if not isinstance(verdict, dict):
        return False, "verdict outcome does not carry an object verdict"
    expected_verdict = {
        "task_id": task_id,
        "checker": "checker-courier",
        "vendor": "anthropic",
        "model": CLAUDE_COURIER_MODEL,
    }
    for key, expected in expected_verdict.items():
        if verdict.get(key) != expected:
            return (
                False,
                f"verdict.{key} is {verdict.get(key)!r}, expected "
                f"{expected!r}",
            )

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json"
        ) as scratch:
            json.dump(verdict, scratch)
            scratch.flush()
            ok, reason = _validate_verdict_json(scratch.name)
    except OSError as error:
        return False, f"could not stage verdict for validation: {error}"
    if not ok:
        return False, f"returned verdict does not validate ({reason})"
    return True, None


def _codex_inline_verdict_ok(message, task_id, agent):
    """Validate a read-only in-family checker's returned verdict before the
    parent persists it.

    Same handoff as checker-courier's above, minus the ledger and quota
    envelope, because an in-family checker produces only a verdict. A Codex
    project agent is `sandbox_mode: read-only` and cannot write the file the
    file-backed branch demands, so without this the gate would instruct the
    agent to do the one thing its sandbox forbids (#68).
    """
    if not isinstance(message, str) or not message.startswith(
        CODEX_VERDICT_MARKER
    ):
        return (
            False,
            "last message must be the AGENT_GUILD_VERDICT marker followed by "
            "the verdict JSON object",
        )
    raw = message[len(CODEX_VERDICT_MARKER):].strip()
    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError as error:
        return False, f"verdict JSON is malformed: {error}"
    if not isinstance(verdict, dict):
        return False, "verdict JSON is not an object"

    # Identity is checked here rather than left to the schema: the validator
    # knows the shape of a verdict, not which task or checker this return
    # belongs to, and a verdict persisted against the wrong task is worse
    # than one rejected.
    for key, expected in (("task_id", task_id), ("checker", agent)):
        if verdict.get(key) != expected:
            return (
                False,
                f"verdict.{key} is {verdict.get(key)!r}, expected "
                f"{expected!r}",
            )

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json"
        ) as scratch:
            json.dump(verdict, scratch)
            scratch.flush()
            ok, reason = _validate_verdict_json(scratch.name)
    except OSError as error:
        return False, f"could not stage verdict for validation: {error}"
    if not ok:
        return False, f"returned verdict does not validate ({reason})"
    return True, None


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
        "still-open task on the main side. If this recurs, the host transcript "
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
    # Intended scope: this hook fires on SubagentStop, so it only ever sees ONE
    # subagent's return at a time, and `ident` below is that subagent's own
    # Task-ID/Audit-ID, read from its own dispatch. There's no separate
    # in-subagent no-op to add—the scoping is structural, not a data.get()
    # check—and it's exactly what keeps this gate from ever demanding anything
    # of a sibling task the returning subagent was never dispatched on.
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

    if agent == "checker-courier":
        # A second-opinion return writes a LANE-suffixed stem, never the
        # verdict of record—same schema, different path, same validator.
        lane = _lib.courier_lane(data)
        if data.get("hook_host") == "codex":
            ok, reason = _codex_courier_outcome_ok(
                data.get("last_assistant_message"), ident
            )
            if ok:
                return 0
            return _lib.block(
                f"checker-courier for {ident} returned an invalid read-only "
                f"Claude-lane outcome ({reason}). Run "
                ".agent-guild/scripts/claude-courier.py and return its JSON "
                f"under the {CODEX_COURIER_OUTCOME_MARKER.strip()} marker; "
                "the parent will persist the validated verdict and ledger."
            )
        rel = f".agent-guild/state/verdicts/{ident}-{tier}-r{retries}-{lane}.json"
        vpath = _lib.state_path("verdicts", f"{ident}-{tier}-r{retries}-{lane}.json")
        if os.path.exists(vpath):
            ok, reason = _validate_verdict_json(vpath)
            if ok:
                return 0
            return _lib.block(
                f"checker-courier for {ident} wrote a verdict at {rel} but it "
                f"doesn't validate ({reason}). Fix it per "
                ".agent-guild/schemas/verdict.schema.json, or—if this was meant "
                "to be a quota bailout (C-3)—remove the file and finish per "
                "that protocol instead (ledger line, then sentinel, no verdict)."
            )
        if _quota_return_ok(ident, lane):
            return 0
        return _lib.block(
            f"checker-courier for {ident} isn't done: no verdict JSON at {rel}, "
            f"and no quota bailout evidence either (needs "
            f".agent-guild/state/exhausted/{lane} plus a vendor-ledger line for "
            f"{ident} with quota_event: true). Write a conforming verdict, or "
            "complete the quota protocol, then finish."
        )

    rel = f".agent-guild/state/verdicts/{ident}-{tier}-r{retries}.json"
    vpath = _lib.state_path("verdicts", f"{ident}-{tier}-r{retries}.json")
    ok, reason = _validate_verdict_json(vpath)
    if ok:
        return 0

    # The file is the verdict of record wherever the checker can write one.
    # On Codex it can't, so the inline handoff is the only route it has, and
    # demanding the file there is the deadlock #68 describes.
    if data.get("hook_host") == "codex":
        inline_ok, inline_reason = _codex_inline_verdict_ok(
            data.get("last_assistant_message"), ident, agent
        )
        if inline_ok:
            return 0
        return _lib.block(
            f"Checker for {ident} isn't done: no valid verdict at {rel} "
            f"({reason}), and the returned verdict is unusable "
            f"({inline_reason}). This host runs you read-only, so return the "
            f"verdict instead of writing it: the line "
            f"{CODEX_VERDICT_MARKER.strip()} followed by the JSON object, and "
            "nothing else. The parent validates and persists it."
        )

    return _lib.block(
        f"Checker for {ident} isn't done: verdict JSON at {rel} is missing or "
        f"invalid ({reason}). Write a conforming verdict per "
        ".agent-guild/schemas/verdict.schema.json, self-check it with "
        "python3 .agent-guild/scripts/validate-verdict.py, then finish."
    )


if __name__ == "__main__":
    _lib.run("subagent-return", main)
