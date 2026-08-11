---
task: T-002
tier: sonnet
retry: 0
checker: checker-judgment
verdict: PASS
checked_at: 2026-07-14T14:38:00Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-5 | `.agent-guild/scripts/check-build.sh "python3 dist/plugin/hooks/test_hooks.py"` | ran the packaged suite; tail reads `49 passed, 0 failed` then `check-build.sh: exit 0`. All four gates + `_lib.py` exercised (stop-gate, dispatch-guard, subagent-return, orchestrator-write-guard). | exit 0, full pass | exit 0, 49 passed / 0 failed | PASS |
| C-6 | read `dist/plugin/hooks/_lib.py` directly; judged against rubric; byte-compared against source `.agent-guild/hooks/_lib.py` | `project_dir()` L48-51: `d = os.environ.get("CLAUDE_PROJECT_DIR"); if d and os.path.isdir(d): return d`. `state_path()` L72: `os.path.join(project_dir(), ".agent-guild", "state", *parts)` — routes through `project_dir()`, no `__file__`. Two-dirs-up fallback removed, replaced by `raise RuntimeError(...)` L63-66 with a 10-line comment L52-62 flagging it "is wrong once this file ships inside a plugin." Python byte-comparison: files identical outside the `project_dir()` body. | returns CLAUDE_PROJECT_DIR when set; no state path hardcoded to plugin/hook location; two-dirs-up fallback removed/corrected/comment-flagged; no other runtime logic altered | all satisfied; sole change isolated to `project_dir()`; the only behavioral divergence (raise vs two-dirs-up) is on the CLAUDE_PROJECT_DIR-unset branch, which is the intended hardening, not a regression C-5 would need to catch | PASS |
| C-8 | `.agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates"` | `check-build.sh: exit 0` — the four live-kit paths are byte-identical to HEAD. (check-build.sh's own log writes land under `.agent-guild/state/log/`, outside all four checked paths, so they don't dirty the diff.) | exit 0 (live kit untouched) | exit 0 | PASS |
