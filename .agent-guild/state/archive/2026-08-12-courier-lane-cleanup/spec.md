---
source: file
ref: /Users/k.arnett/.claude/plans/abstract-spinning-swing.md
fetched_at: 2026-08-12T03:24:54Z
---
# Courier-lane cleanup: #106 verify/close, #128, #47 + #116

## Context

The pasted notes proposed a three-step sequence built around #84 (the missing `codex-courier.py`). #84 has since closed, and the script it asked for landed — which changes the picture for #106 specifically:

- **#106's substance already shipped inside #84's script.** `codex-courier.py` validates before persisting (`_validate_structured_output` at `.agent-guild/scripts/codex-courier.py:340`), retries malformed output once, emits a schema-conforming `blocked` verdict on the second failure, and retains raw attempts under `state/log/courier-raw/`. `checker-courier.md` now instructs the courier to run the script and never hand-write a verdict, and `subagent-return.py:466-491` re-validates the lane-suffixed file on return. `test_codex_courier.py:465-501` covers malformed-once and malformed-twice. So #106 becomes a verification-and-close, not a build — unless the replay finds a gap.
- **#117 is also closed** (ledger rows carry `job`), so the "ledger pass" is #47 + #116 only.
- The notes' ordering logic survives: #128 first (small, and it settles the skip semantics anything later relies on), then the ledger pass.

One CI gap found during exploration, folded in below: `test_codex_courier.py` exists but is missing from `.github/workflows/plugin-build.yml`'s suite list.

**Repo mechanics that apply to every step:** `.agent-guild/scripts/*`, `guild-core/roles/*`, and `.agent-guild/CLAUDE.md` are sources; `plugin/` and `plugins/agent-guild/` are generated. After edits, run `python3 scripts/build-plugin.py` to refresh the tracked packages — never edit the generated copies by hand. Per user workflow: one branch per step off `main`, atomic commits, no pushing. Commit messages and any human-facing doc prose go through the `humanizer` skill before commit.

---

## Step 0 — #106: verify against the shipped script, then close

No code expected. Replay #106's exact failure through the existing harness and attach the evidence to the issue.

1. Drive a vendor response with unescaped double quotes inside a JSON string (the observed `evidence` payload shape) through `codex-courier.py`'s path — `test_codex_courier.py` already has the fake-CLI machinery (`mode == "malformed"`, `:178`); add or adapt a case using #106's literal payload shape if the existing malformed fixture doesn't cover embedded-quote truncation specifically.
2. Confirm the four live ACs: nothing reaches the lane-suffixed stem unvalidated; one retry on the fixed lane; second failure → `blocked` verdict with raw text preserved (`state/log/courier-raw/<stem>.jsonl`); test asserts `blocked` lands, not the malformed text.
3. AC "vendor JSON is never repaired, reformatted, or re-serialized": record on the issue that this was deliberately amended by #142/#144 — the runner stamps `model` locally and re-serializes, with the divergence recorded as an `info` finding and the raw response retained. The AC's intent (never make invalid output valid) holds; the letter changed by design.
4. If the replay passes clean: comment the evidence on #106 and close it. If it finds a gap, fix it in `codex-courier.py` on this branch before closing.
5. Same branch, small fix: add `python3 .agent-guild/scripts/test_codex_courier.py` to the suite list in `.github/workflows/plugin-build.yml` — the script #106's guarantee lives in is currently untested in CI.

## Step 1 — #128: script-checked clauses stop crossing the lane

**Composer** (`.agent-guild/scripts/compose-brief.py`):
- Partition cited clauses by their `- **check**:` line inside `extract_clause`'s block: keep a clause only when the check value starts with `checker-judgment:`; drop script-checked clauses entirely (not demoted to context — settled in the issue).
- All-script task → new distinct exit status (exit 3, stderr `compose-brief: nothing to cross: <task-id> cites only script-checked clauses`), separate from the existing exit-1 "zero clauses" error.
- `test_compose_brief.py`: three shapes — mixed (script omitted, judgment kept), all-judgment (byte-identical to today), all-script (exit 3, no brief written).

**Discharge for the skipped crossing** (not covered by the issue, but required — `second_opinion_debts` in `.agent-guild/hooks/_lib.py:230` would otherwise hold the turn open forever on an all-script task, since no verdict, sentinel, or waiver ever lands):
- New marker: orchestrator writes `.agent-guild/state/verdicts/T-NNN-<tier>-r<N>-<lane>.skipped` (one line naming the reason) when compose-brief exits 3. It's under `state/`, so the write-guard allows it.
- `_lib.second_opinion_debts`: add the `.skipped` check as a discharge route alongside `.denied` (`_lib.py:281`).
- `dispatch-guard.py`: deny a `checker-courier` dispatch on a stem carrying a `.skipped` marker, mirroring the exhausted-lane denial — a skip that was recorded shouldn't be crossable anyway.
- `test_hooks.py`: debt discharged by `.skipped`; courier dispatch denied on a skipped stem; wrong-lane `.skipped` discharges nothing (same trap as `.denied`).

**Docs/roles (sources, then rebuild):**
- `guild-core/roles/checker-courier.md`: a crossing happens only when the brief carries at least one judgment clause; on exit 3, report the skip instead of dispatching the lane; drop the "if evidence a clause requires was not supplied, the external check is blocked" fallback (nothing is left for a dispatcher to supply).
- `.agent-guild/CLAUDE.md`: amend the dual-check regime (courier after every checker of record → after every checker of record *whose task cites a judgment clause*), and add the `.skipped` marker to the state map with its lane trap.
- `.agent-guild/templates/task.md`: Courier comparison section records the skip as an honest absence (it already asks for this in spirit; make the skip case explicit).

**Byproduct to note on #34:** after Steps 0–1, `blocked` at the lane stem has a single meaning — vendor response unusable — since "the vendor was asked to run a script" can no longer occur.

## Step 2 — #47 + #116: the ledger pass

One branch; both issues touch `ledger-append.py`, `vendor-call.schema.json`, and the couriers.

**#47 — relativize artifacts in the shared script:**
- `ledger-append.py`: before validation, rewrite each `--artifacts` value that resolves under the repo root (cwd, same base the script already uses for `DEFAULT_LEDGER` and spec provenance) to repo-relative; leave paths outside the root as given — never emit `../` chains.
- `test_ledger_append.py`: absolute-under-root → relative; already-relative → unchanged; outside-root → untouched. No archived ledger is rewritten.
- The couriers' own `_courier_lib.repo_relative` pre-pass stays; the script-level fix is the backstop for any other caller.

**#116 — retries visible in the ledger (one row per crossing, chosen):**
- `vendor-call.schema.json`: add optional (non-required) `attempts` (integer) and `discarded` (array of `{reason, duration_ms, exit_code, tokens_in, tokens_out}`, nullable numerics per the existing convention). Optional keeps every archived row valid — the same pattern `job` used for #117. `additionalProperties: false` stays; the fields are simply added.
- `ledger-append.py`: `--attempts N` and a repeatable `--discarded` flag taking a JSON object per discarded call; validate the assembled line as today.
- `codex-courier.py`: time each `_run_once` individually and capture per-attempt usage (the loop at `:431` already collects both per call before summing into `usage_totals`); on a retried crossing, pass `--attempts` and one `--discarded` entry per non-final attempt with `reason` = the validation failure (top-level `tokens_in/out` remain the cumulative sums, so cost totals keep meaning what they meant). Mirror in `claude-courier.py`, which has the same two-attempt loop shape (`claude-courier.py:332`).
- Retry-behavior-defined-somewhere-an-agent-reads AC: satisfied since #84 by the script itself plus `checker-courier.md` steps 4/6; the role text's "a retried call sums its attempts into a single row" line gets the `discarded[]` detail added.
- Tests: `test_ledger_append.py` for the new flags and schema; `test_codex_courier.py`/`test_claude_courier.py` assert a retried crossing's row carries `attempts: 2` and one discarded entry, and that a quota abandonment stays distinguishable (`quota_event` unchanged).

## Verification (each step)

```sh
python3 .agent-guild/scripts/test_compose_brief.py
python3 .agent-guild/scripts/test_ledger_append.py
python3 .agent-guild/scripts/test_codex_courier.py
python3 .agent-guild/scripts/test_claude_courier.py
python3 .agent-guild/hooks/test_hooks.py
python3 .agent-guild/hooks/test_codex_adapter.py
python3 scripts/test_build_plugin.py
python3 scripts/build-plugin.py          # sync generated packages
python3 scripts/build-plugin.py --check  # then confirm clean
```

Plus the issue-specific repros: #128's brief-composition repro from the issue body (mixed-clause task → grep the brief for the script check line, expect absent), #47's two-row repro, and #106's malformed-payload replay.

## Out of scope

- #34 itself — these steps clean its evidence stream; the ruling stays open.
- Rewriting any archived brief, verdict, or ledger (every issue forbids it).
- The Codex-lane (`claude-courier.py`) equivalents beyond what #116 explicitly touches.
