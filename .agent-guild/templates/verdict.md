---
task: T-000
tier: sonnet
retry: 0
checker: checker-deterministic
verdict: PASS
checked_at: 2026-01-01T00:00:00Z
---

<!--
FILENAME: .agent-guild/state/verdicts/<task>-<tier>-r<retries>.md  (e.g. T-001-sonnet-r1.md)
  Task verdicts embed tier + the task's `retries` value at check time, so a
  per-tier retry reset never overwrites an earlier tier's verdict.
AUDIT verdicts use ids CON-audit-rN.md / DEC-audit-rN.md with tier: orchestrator.

verdict field:
  PASS:  every clause satisfied, each backed by evidence YOU derived.
  FAIL:  one or more clauses violated. A `## Diagnosis` section is REQUIRED.
  ERROR: the check itself could not run (script missing, crashed, exit 3,
         URL unreachable). NOT a retry, so the orchestrator fixes the check
         and it does not count against the worker's tier budget.
-->

## Per-clause results

| clause | method               | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | -------------------- | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1    | .agent-guild/scripts/check-foo.sh | `exit 0`                                                   | exit 0   | exit 0 | PASS   |

## Diagnosis

<!-- REQUIRED for FAIL, omit otherwise. One entry per defect. Each must be
actionable by the worker without re-reading the whole verdict: name the file,
the line, the clause id + the quoted clause text it violates, and expected vs
actual. A FAIL a worker cannot act on is itself a defective verdict. -->

- **file**: path/to/artifact.ext:42
  **clause**: C-1—"<quoted clause text>"
  **expected**: <what the clause requires>
  **actual**: <what the artifact does instead>
