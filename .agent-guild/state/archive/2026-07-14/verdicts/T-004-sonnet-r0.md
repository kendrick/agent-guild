---
task: T-004
tier: sonnet
retry: 0
checker: checker-judgment
verdict: PASS
checked_at: 2026-07-14T14:47:00Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1 | checker-judgment: parse manifest, check kebab-case `name`, resolve `hooks` target under `dist/plugin/` | `json.load` on `dist/plugin/.claude-plugin/plugin.json` → `PARSES_OK`, `name='agent-guild'`, `hooks='./hooks/hooks.json'`; `re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', 'agent-guild')` → `True`; `./hooks/hooks.json` resolved against plugin root `dist/plugin/` → `dist/plugin/hooks/hooks.json`, `test -f` → `RESOLVED: dist/plugin/hooks/hooks.json exists` (1.1K) | valid JSON; `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$`; `hooks` resolves to a file that exists under `dist/plugin/` | parses clean; `name` matches; `hooks` target exists | PASS |
| C-8 | `.agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates"` | `check-build.sh: exit 0 (log: .../build-20260714T144639.log)`; wrapper exit `0`; isolated `git diff --quiet HEAD -- ...` → `raw_git_exit:0` (no output = no diff) | exit 0 (live in-repo kit unchanged from HEAD) | exit 0 | PASS |
