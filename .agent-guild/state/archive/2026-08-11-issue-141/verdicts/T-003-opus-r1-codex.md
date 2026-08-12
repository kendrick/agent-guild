---
task: T-003
checker: checker-courier
vendor: openai
model: gpt-5.6-terra
verdict: PASS
checked_at: 2026-08-11T00:00:00Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | info | Both passages accurately distinguish a legal dispatch that left an unpromoted reservation, which a re-dispatch can promote, from a file-bearing stem with no reservation, which cannot be rescued by re-dispatch and requires a waiver. | .agent-guild/CLAUDE.md:87; .agent-guild/hooks/_lib.py:480-492; reserve_crossing() and promote_crossing() supplied source |
| C-1 | info | Neither passage overstates re-dispatch as universally successful or universally futile; both consistently prefer re-dispatch when the earlier legal reservation exists and reserve the waiver for the no-reservation case. | .agent-guild/CLAUDE.md:87; .agent-guild/hooks/_lib.py:480-492 |
