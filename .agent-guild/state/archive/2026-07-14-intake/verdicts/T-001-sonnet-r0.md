---
task: T-001
tier: sonnet
retry: 0
checker: checker-deterministic
verdict: PASS
checked_at: 2026-07-14T23:23:23Z
---

## Per-clause results

| clause | method                                                                                                                                              | evidence                                     | expected | actual | result |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | -------- | ------ | ------ |
| C-3    | .agent-guild/scripts/check-build.sh "python3 .agent-guild/scripts/check-provenance.py --self-test"                                              | exit 0; "OK: self-test passed (5 fixtures)" | exit 0   | exit 0 | PASS   |
| C-7    | .agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude/settings.json .claude/agents .agent-guild/hooks/dispatch-guard.py ..." | exit 0; no diff output                      | exit 0   | exit 0 | PASS   |
