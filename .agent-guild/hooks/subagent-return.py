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

Every resolved return (worker, checker, courier, audition—never a block, and
never a return whose id we couldn't identify) clears the in-flight marker
dispatch-guard.py wrote (_lib.clear_in_flight). A block leaves it in place:
the subagent hasn't finished, so nothing should read it as no longer working.

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
CLAUDE_COURIER_MODEL = _lib.LANE_IDENTITY["claude"]["model"]


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


def _courier_identity_violation_at(path, task_id, lane):
    """The identity check applied to a verdict already on disk. Unreadable or
    unparseable is not this check's problem: _validate_verdict_json has
    already run and would have said so."""
    try:
        with open(path, encoding="utf-8") as stream:
            verdict = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return None
    return _lib.courier_identity_violation(verdict, task_id, lane)


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


DISCARDED_ENTRY_FIELDS = {
    "reason", "duration_ms", "exit_code", "tokens_in", "tokens_out",
}


def _discarded_entries_violation(discarded):
    """None, or a string naming the field that failed, for the optional
    `ledger.discarded` array — one entry per attempt a retried crossing threw
    away, in the same shape C-4 pins for vendor-call.schema.json's own
    `discarded` field. Widening the ledger key set to admit this key is not
    licence to stop checking what's inside it."""
    if not isinstance(discarded, list):
        return "discarded is not an array"
    for index, entry in enumerate(discarded):
        if not isinstance(entry, dict):
            return f"discarded[{index}] is not an object"
        unexpected = set(entry) - DISCARDED_ENTRY_FIELDS
        missing = DISCARDED_ENTRY_FIELDS - set(entry)
        if unexpected or missing:
            return (
                f"discarded[{index}] fields must be exactly "
                f"{sorted(DISCARDED_ENTRY_FIELDS)!r}, got {sorted(entry)!r}"
            )
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            return f"discarded[{index}].reason is not a non-empty string"
        for key in ("duration_ms", "exit_code"):
            if type(entry[key]) is not int:
                return f"discarded[{index}].{key} is not an integer"
        if entry["duration_ms"] < 0:
            return f"discarded[{index}].duration_ms is negative"
        for key in ("tokens_in", "tokens_out"):
            value = entry[key]
            if value is not None and (type(value) is not int or value < 0):
                return (
                    f"discarded[{index}].{key} is neither a non-negative "
                    "integer nor null"
                )
    return None


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
    # `discarded` (#116/T-009) is optional, not required: claude-courier.py
    # only carries it on a row with a retried or otherwise discarded attempt,
    # so a payload with the key and one without it both have to pass. The
    # comparison still refuses anything outside this set — admitting one more
    # key is not the same as no longer checking.
    optional_ledger_fields = {"discarded"}
    unexpected = set(ledger) - ledger_fields - optional_ledger_fields
    missing = ledger_fields - set(ledger)
    if unexpected or missing:
        return (
            False,
            f"ledger fields must be exactly {sorted(ledger_fields)!r}, "
            f"optionally plus {sorted(optional_ledger_fields)!r}, got "
            f"{sorted(ledger)!r}",
        )
    if "discarded" in ledger:
        violation = _discarded_entries_violation(ledger["discarded"])
        if violation is not None:
            return False, f"ledger.{violation}"
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
    violation = _lib.courier_identity_violation(verdict, task_id, "claude")
    if violation is not None:
        field, actual, expected = violation
        return (
            False,
            f"verdict.{field} is {actual!r}, expected {expected!r}",
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
    """The verdict this return has to validate. Shares dispatch-guard's notion
    of "latest" deliberately: a round this gate accepts but the gate reads
    differently is a round nothing actually checked."""
    return _lib.latest_audit_round(audit_id)[1]


def _unidentifiable(reason):
    """We can't tell which task this subagent ran. Blocking it can't help—it can't
    fix a bad transcript by trying again—and this gate has no stall backstop, so a
    block here hangs the subagent forever (a worker once had to write PAUSED to
    break exactly this loop). Fail LOUD but let it finish: the task stays open, so
    the main-session stop-gate still forces the orchestrator to verify it, which is
    where enforcement lives anyway. Never silent—the reason hits stderr and the log.

    Two of the three callers (missing/unreadable transcript_path, no id readable
    from the transcript) reach here with no ident at all, and deliberately leave
    the in-flight marker alone. Clearing without an ident would mean globbing
    `*--{agent}.json` and deleting whatever matches, but a wave routinely runs
    several tasks under the same agent type at once—that glob would delete a LIVE
    sibling's marker along with the dead one, telling the stop gate a genuinely
    running subagent had finished and pushing it toward a spurious STALLED.md on
    healthy work. A leaked marker is bounded by AGENT_GUILD_INFLIGHT_STALE_S (an
    hour), and with #163 making the stall counter per-task, one leak now only
    costs that one task's backstop for the TTL rather than every task's—losing an
    hour beats killing a sibling's marker. (The third caller, "has no task file",
    does know its ident and clears its own marker before calling in here—see
    above.)

    The `_lib.block(...)` returns elsewhere in this file leave their markers in
    place on purpose too, same as always: the subagent hasn't finished, so nothing
    should read it as no longer working. That's pinned by an existing test and
    unchanged by any of this."""
    msg = (
        "subagent-return could not identify this subagent's task: " + reason
        + ". Letting it finish instead of hanging; the stop-gate will catch the "
        "still-open task on the main side. If this recurs, the host transcript "
        "shape probably changed—see _lib.dispatch_candidates and its fixtures."
    )
    try:
        # A wave's members return concurrently, so this append is too (#164);
        # it rides the same O_APPEND reliance dispatch-guard._log documents.
        with open(_lib.state_path("log", "return-gate.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    sys.stderr.write(msg + "\n")
    return 0


def main(data):
    # Intended scope: this hook fires on SubagentStop, so it only ever sees ONE
    # subagent's return at a time, and `ident` below is that subagent's own
    # Task-ID/Audit-ID. There's no separate in-subagent no-op to add—the scoping
    # is structural, not a data.get() check—and it's what keeps this gate from
    # ever demanding anything of a sibling task the returning subagent was never
    # dispatched on. That last part was an assumption rather than a fact until
    # #204: the transcript alone can only offer the LAST dispatch it recorded,
    # which is a coin flip once a wave goes out in one message, so ident_for_return
    # narrows on what this hook input knows about the agent that is returning.
    # Ambiguity it can't settle arrives here as an exception and routes to
    # _unidentifiable, which clears nothing.
    agent = _lib.bare_agent(data.get("agent_type", ""))
    if agent not in _lib.GUILD_AGENTS:
        return 0  # matcher should exclude these, but don't assume

    transcript = data.get("transcript_path")
    if not transcript or not os.path.exists(transcript):
        return _unidentifiable(f"transcript_path missing or unreadable ({transcript!r})")

    try:
        ident = _lib.ident_for_return(data)
    except Exception as exc:
        return _unidentifiable(f"no id readable from the transcript ({exc})")

    # Audition runs have no task file and no verdict; the battery scorer judges
    # them, not this gate. Nothing to validate, so let the subagent finish.
    if re.match(r"^A-\d+$", ident):
        _lib.clear_in_flight(ident, agent)
        return 0

    if agent == "auditor":
        vpath = _latest_audit_verdict(ident)
        if vpath is None:
            return _lib.block(
                f"Auditor finished without writing a verdict for {ident}. Write "
                f".agent-guild/state/verdicts/{ident}-r0.md (or the next round) with a "
                "verdict of PASS or FAIL before finishing."
            )
        ok, reason = _verdict_ok(vpath)
        if not ok:
            return _lib.block(f"Auditor verdict for {ident} is not valid: {reason}.")
        _lib.clear_in_flight(ident, agent)
        return 0

    task = _lib.read_task(ident)
    if task is None:
        # Unlike the two blind callers above, ident is known here—the marker
        # dispatch-guard wrote is `{ident}--{agent}.json`, so it can be named
        # and cleared directly. The subagent genuinely finished; leaving the
        # marker in place would suppress this one task's stall backstop for
        # up to an hour over a task file that no longer exists.
        _lib.clear_in_flight(ident, agent)
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
        _lib.clear_in_flight(ident, agent)
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
                _lib.clear_in_flight(ident, agent)
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
            if not ok:
                return _lib.block(
                    f"checker-courier for {ident} wrote a verdict at {rel} but it "
                    f"doesn't validate ({reason}). Fix it per "
                    ".agent-guild/schemas/verdict.schema.json, or—if this was meant "
                    "to be a quota bailout (C-3)—remove the file and finish per "
                    "that protocol instead (ledger line, then sentinel, no verdict)."
                )
            # The reciprocal lane has checked this since #92; this host did
            # not, which is how a verdict claiming `model: "gpt-5.6"` reached
            # the #34 corpus with nothing having verified it (#142).
            violation = _courier_identity_violation_at(vpath, ident, lane)
            if violation is not None:
                field, actual, expected = violation
                return _lib.block(
                    f"checker-courier for {ident} wrote a verdict at {rel} whose "
                    f"{field} is {actual!r}, but the {lane} lane's is "
                    f"{expected!r}. Re-run "
                    ".agent-guild/scripts/codex-courier.py, which stamps the "
                    "identity from the lane it actually ran. Don't hand-edit the "
                    "field: a verdict you corrected is one you co-authored, and "
                    "you commissioned this check."
                )
            # #100 verbatim: a courier dispatched for one task also wrote a
            # SIBLING task's verdict, and nothing noticed. Surface any other
            # lane-suffixed file sitting here with no courier dispatch of its
            # own (C-2). A log row, not a non-zero exit: blocking this
            # subagent's return would hang it over a file it may have had
            # nothing to do with and can't fix by retrying. Run before
            # clear_in_flight below so a sibling's live courier still reads as
            # in flight rather than as a foreign write.
            for file_tid, _fstem, name in _lib.foreign_stem_writes(ident, lane):
                _lib.surface_foreign_stem_write(ident, file_tid, name)
            _lib.clear_in_flight(ident, agent)
            return 0
        if _quota_return_ok(ident, lane):
            _lib.clear_in_flight(ident, agent)
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
        _lib.clear_in_flight(ident, agent)
        return 0

    # The file is the verdict of record wherever the checker can write one.
    # On Codex it can't, so the inline handoff is the only route it has, and
    # demanding the file there is the deadlock #68 describes.
    if data.get("hook_host") == "codex":
        inline_ok, inline_reason = _codex_inline_verdict_ok(
            data.get("last_assistant_message"), ident, agent
        )
        if inline_ok:
            _lib.clear_in_flight(ident, agent)
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
