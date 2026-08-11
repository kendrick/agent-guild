---
task: T-004
tier: sonnet
retry: 0
checker: checker-judgment
verdict: PASS
checked_at: 2026-07-14T18:34:00Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-5 | checker-judgment: read `_lib.py` `project_dir()` + new tests | `_lib.py:61` `if os.path.isdir(os.path.join(candidate, ".agent-guild")): return candidate` then `:63` `raise RuntimeError(...)` naming the missing `.agent-guild/`. `git diff HEAD -- _lib.py` shows +16/-2, all inside the fallback; primary path `_lib.py:48-51` (`d = os.environ.get("CLAUDE_PROJECT_DIR")` / `if d and os.path.isdir(d): return d`) is byte-identical. `test_hooks.py:118-139` pops `CLAUDE_PROJECT_DIR`, then (a) points `__file__` at `scratch_ok/pkg/hooks/_lib.py` with a real `.agent-guild/` two-up → asserts `project_dir()==scratch_ok`; (b) points at `scratch_bad/pkg/hooks/_lib.py` with no `.agent-guild/` → asserts `RuntimeError` with `.agent-guild` in the message. Real tempdirs, both branches. | guard on `candidate/.agent-guild`; RuntimeError otherwise; primary path unchanged; both branches tested for real | exactly that | PASS |
| C-6 | `.agent-guild/scripts/check-build.sh "python3 .agent-guild/hooks/test_hooks.py 2>&1 \| grep -qE ..."` | `check-build.sh: exit 0`; direct run tail: `51 passed, 0 failed` | exit 0, >=50 passed, 0 failed | exit 0, 51 passed, 0 failed | PASS |
| C-7 | `.agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude/settings.json .claude/agents ...dispatch-guard.py orchestrator-write-guard.py stop-gate.py subagent-return.py"` | `check-build.sh: exit 0` — no diff against HEAD on any protected path | exit 0 (untouched) | exit 0 | PASS |

## Diagnosis

<!-- No FAIL. -->
