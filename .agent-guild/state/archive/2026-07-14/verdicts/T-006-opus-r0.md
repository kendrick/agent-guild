---
task: T-006
tier: opus
retry: 0
checker: checker-judgment
verdict: PASS
checked_at: 2026-07-14T15:00:30Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-7 | judgment: read `dist/plugin/README.md` against the 4-part rubric | All four rubric parts present, substantive, and factually accurate — evidence below the table | install + hybrid+reason + import-line what/why/how + gate verification, each followable | all four covered and correct | PASS |
| C-8 | `.agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates"` | `check-build.sh: exit 0 (log: .../build-20260714T150025.log)`; `EXIT_CODE=0` | exit 0 (live kit untouched) | exit 0 | PASS |

### C-7 evidence, part by part (derived from `dist/plugin/README.md`)

1. **Local-path install** — section "Install From A Local Path" (lines 23–54). Step 1 creates `.claude-plugin/marketplace.json` next to `plugin.json` with a full JSON example; step 2 gives `/plugin marketplace add ./dist/plugin` then `/plugin install agent-guild@agent-guild-local`; step 3 states enablement is recorded in the settings file under `enabledPlugins` as `"agent-guild@agent-guild-local": true`. Cross-check: `dist/plugin/.claude-plugin/plugin.json` exists (`name: "agent-guild"`), so the "next to plugin.json" instruction resolves.

2. **Hybrid stays per-project, with the reason** — line 15: "An always-on `CLAUDE.md` ... is persistent project instructions Claude Code reads on every turn ... and a plugin has no way to contribute one. The orchestrator contract is exactly that ... So three pieces stay in your project rather than the plugin." Lists `.agent-guild/CLAUDE.md` (the contract, imported via the line below) and `.agent-guild/state/` (per-project runtime bus, resolved under `CLAUDE_PROJECT_DIR`). The reason is stated plainly, not just the steps.

3. **The import line, what/why/how-it-got-there** — section "About That `@.agent-guild/CLAUDE.md` Line" (lines 78–84): what it is ("an import. Claude Code expands an `@path` line ... by pulling that file's contents in as project instructions"); what it loads ("the orchestrator contract, the guild's always-on rules for the main session ... the piece the plugin can't ship as always-on"); how it got there ("you added it when you installed the guild"). Explicitly framed "so it never reads as a mystery."

4. **Verify the four gates post-install** — section "Confirm The Gates Fire After Install" (lines 86–104): the offline test `python3 hooks/test_hooks.py`, then a fresh-session walk of the observable gate behaviors (dispatch-guard denies a no-Task-ID dispatch, stop-gate holds a turn open, orchestrator-write-guard blocks a deliverable edit), then a pointer to `SMOKE.md` Part A for the full every-gate walk. Verified against reality: running `python3 hooks/test_hooks.py` from `dist/plugin/` prints exactly `49 passed, 0 failed` (matching the README's stated expectation), and `SMOKE.md` line 19 is `## Part A: The Four Hook Gates` (A1–A5), so the reference resolves.
