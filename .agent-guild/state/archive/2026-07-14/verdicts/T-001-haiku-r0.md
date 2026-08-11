---
task: T-001
tier: haiku
retry: 0
checker: checker-deterministic
verdict: PASS
checked_at: 2026-07-14T14:33:00Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-2 | .agent-guild/scripts/check-build.sh "diff <(ls .claude/agents) <(ls dist/plugin/agents) && diff <(ls .claude/skills) <(ls dist/plugin/skills)" | exit 0 | exit 0 | exit 0 | PASS |
| C-8 | .agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates" | exit 0 | exit 0 | exit 0 | PASS |
