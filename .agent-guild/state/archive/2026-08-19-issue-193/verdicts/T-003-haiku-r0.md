---
task: T-003
checker: checker-deterministic
vendor: anthropic
model: claude-haiku-4-5-20251001
verdict: PASS
checked_at: 2026-08-19T00:45:30Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-6 | info | All four consumer commands exited 0 and the published trees match a fresh build. | check-build.sh exit 0: test_check_job_spec.py (230 passed), check-job-spec.py --self-test (OK), test_hooks.py (324 passed), build-plugin.py --check (OK) |
| C-7 | info | The working tree diff touches only the source files and their generated views, with no unrelated files. | check-diff-scope.py exit 0: 6 paths in scope (.agent-guild/scripts/check-job-spec.py, .agent-guild/scripts/test_check_job_spec.py, plugin/project-template/.agent-guild/scripts/check-job-spec.py, plugin/project-template/.agent-guild/scripts/test_check_job_spec.py, plugins/agent-guild/project-template/.agent-guild/scripts/check-job-spec.py, plugins/agent-guild/project-template/.agent-guild/scripts/test_check_job_spec.py) |
