# Verdict: T-001 (sonnet r1, codex lane)

**Task:** T-001 — Add the second-opinion debt predicate to _lib.py
**Checker:** checker-courier (openai/gpt-5.6-terra)
**Outcome:** PASS
**Timestamp:** 2026-08-11T13:45:05Z

## Findings

### 1. C-2 (INFO)

Valid, discharged, and blocked-record cases returned the expected debts for cases 1–7.

**Evidence:** Scratch-fixture output: PASS 1–7; .agent-guild/hooks/_lib.py:238-280.

### 2. C-2 (INFO)

The unreadable-record sibling regression is discharged before parsing, preventing the round-0 livelock.

**Evidence:** Scratch-fixture output: PASS 8 unreadable + sibling: []; .agent-guild/hooks/_lib.py:238-260.

### 3. C-2 (INFO)

Unreadable and zero-byte records with no discharge route owe a codex-lane debt without raising.

**Evidence:** Scratch-fixture output: PASS 9 and PASS 11; .agent-guild/hooks/_lib.py:257-269.

### 4. C-2 (INFO)

A missing verdicts directory returns an empty debt list without raising.

**Evidence:** Scratch-fixture output: PASS 10 missing directory: []; .agent-guild/hooks/_lib.py:221-226.

### 5. C-2 (INFO)

Auditor stems and lane-suffixed verdicts are excluded from debts by the anchored record-stem matcher.

**Evidence:** Scratch-fixture output: PASS 12 and PASS 13; .agent-guild/hooks/_lib.py:187-192,229-235.

### 6. C-2 (INFO)

Lane selection resolves codex-host data to claude and default or absent data to codex.

**Evidence:** Scratch assertions passed for courier_lane({'hook_host': 'codex'}), courier_lane({}), and courier_lane(None); .agent-guild/hooks/_lib.py:170-179.

### 7. C-2 (INFO)

The module-level COURIER_LANES constant is used for sibling detection and no lane literal appears in the predicate AST.

**Evidence:** Scratch-fixture output: PASS 14; .agent-guild/hooks/_lib.py:29,238.

### 8. C-2 (INFO)

All malformed-input fixtures completed without exception.

**Evidence:** Scratch-fixture output: PASS 15 malformed/missing cases returned without exception.
