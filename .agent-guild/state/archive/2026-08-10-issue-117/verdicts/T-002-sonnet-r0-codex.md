---
task: T-002
checker: checker-courier
vendor: openai
model: gpt-5.6-terra
verdict: PASS
checked_at: 2026-08-10T00:00:00Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | info | All six required verbatim job-field cases are present, passing, and contain behavior-specific assertions that would detect their respective regressions. | Artifact excerpt: six check() calls labelled `job: ...`; `.agent-guild/state/log/ledger-suite.out`: six corresponding `ok` lines and `43 passed, 0 failed`. |
