---
task: T-001
checker: checker-deterministic
vendor: anthropic
model: claude-haiku-4-5-20251001
verdict: PASS
checked_at: 2026-08-21T00:00:00Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | info | Probe c1 confirmed that install writes the provenance record across all three install shapes. | probe c1: ok |
| C-2 | info | Probe c2 confirmed that clean-but-stale files upgrade in place with correct reporting. | probe c2: ok |
| C-3 | info | Probe c3 confirmed that a mixed run refuses only real edits and upgrades clean files. | probe c3: ok |
| C-4 | info | Probe c4 confirmed that a pre-provenance kit adopts what matches and preserves edited files. | probe c4: ok |
| C-6 | info | Probe c6 confirmed that the provenance record is trackable in git and not ignored. | probe c6: ok |
| C-8 | info | Test suite passed: 371 tests in test_hooks.py, 50 tests in test_build_plugin.py, and build-plugin.py --check validation succeeded. | 371 passed in test_hooks.py, 50 passed in test_build_plugin.py, validation passed |
