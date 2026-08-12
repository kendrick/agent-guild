---
task: T-001
checker: checker-deterministic
vendor: anthropic
model: claude-haiku-4-5-20251001
verdict: PASS
checked_at: 2026-08-11T23:41:39Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | info | All seven test suites exit 0: test_compose_brief.py, test_ledger_append.py, test_codex_courier.py, test_claude_courier.py, test_hooks.py, test_codex_adapter.py, and test_build_plugin.py. | check-build.sh: 379 tests passed across all suites, exit 0 |
| C-2 | info | Generated packages are regenerated and match the sources at the commit tip; build-plugin.py --check validates each commit's packages. | check-build.sh: Validation passed, OK: shared-core wrappers, both published packages, and both marketplaces match fresh builds, exit 0 |
| C-9 | info | All changed files stay within the allowed paths: .agent-guild/scripts/, .agent-guild/hooks/, .agent-guild/schemas/, .agent-guild/templates/, .agent-guild/state/, guild-core/roles/, scripts/plugin-src/, plugin/, plugins/agent-guild/, .claude/agents/, .claude/skills/, .agent-guild/CLAUDE.md, docs/plugin-readme.md, and .github/workflows/plugin-build.yml. | check-build.sh: No files outside allowed paths detected, exit 0 |
| C-11 | info | The branch is chore/courier-lane-cleanup, has no upstream tracking ref, and all work outside .agent-guild/state/ is committed. | check-build.sh: Branch name verified, no upstream ref, no uncommitted work outside state/, exit 0 |
| C-12 | info | CI workflow includes python3 .agent-guild/scripts/test_codex_courier.py as a live indented line in the run block. | check-build.sh: grep matched the exact pattern in .github/workflows/plugin-build.yml, exit 0 |
