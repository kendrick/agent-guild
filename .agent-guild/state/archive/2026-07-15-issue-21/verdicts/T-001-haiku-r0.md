---
task: T-001
tier: haiku
retry: 0
checker: checker-deterministic
verdict: PASS
checked_at: 2026-07-14T23:45:49Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1    | `.agent-guild/scripts/check-build.sh 'python3 scripts/build-plugin.py --check'` | `✔ Validation passed` `OK: /Users/k.arnett/repos/agent-guild/plugin matches a fresh build and passes claude plugin validate --strict` | exit 0 | exit 0 | PASS |
| C-2    | `.agent-guild/scripts/check-build.sh '! git check-ignore -q plugin/.claude-plugin/plugin.json && ! git check-ignore -q plugin/hooks/hooks.json && ! git check-ignore -q plugin/skills/job/SKILL.md'` | No output from check-ignore; negation succeeds | exit 0 | exit 0 | PASS |
| C-3    | `.agent-guild/scripts/check-build.sh 'python3 -c "import json..." && test "$(ls plugin/skills..." && ! ls plugin/skills...'` | `manifest ok` | exit 0 | exit 0 | PASS |
| C-4    | `.agent-guild/scripts/check-build.sh 'test ! -e dist && ! grep -qiE "(^|/)dist" .gitignore && ! grep -qiF "Build artifacts" .gitignore'` | No errors from test conditions; all pass | exit 0 | exit 0 | PASS |
| C-5    | `.agent-guild/scripts/check-build.sh 'test -d plugin && test -z "$(git status --porcelain -- . ":(exclude)plugin" ":(exclude)scripts/plugin-src" ":(exclude).gitignore")"'` | plugin/ exists; git status clean except for excludes | exit 0 | exit 0 | PASS |
