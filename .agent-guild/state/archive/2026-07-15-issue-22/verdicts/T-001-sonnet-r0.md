---
task: T-001
tier: sonnet
retry: 0
checker: checker-judgment
verdict: PASS
checked_at: 2026-07-14T22:33:00Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment: read SKILL.md against clause | Frontmatter `name: init`, `disable-model-invocation: true`, description triggers verbatim on "finish the guild install here" / "set up this project for the guild". All five steps explicit with concrete paths sourced from `${CLAUDE_PLUGIN_ROOT}/project-template/`: (1) contract copy L22-28, (2) import line L30-40, (3) state dirs+`.gitkeep` L42-49, (4) gitignore L51-57, (5) payload copy L59-79. `.claude/settings.json` prohibition stated L81-83. Summary + next steps L85-92. | all five steps + settings prohibition + summary/next-steps, no settings merge | present in full | PASS |
| C-2 | judgment: re-run behavior per step | exists→skip: step1 identical→report L27, step2 present→report L40, step3 mkdir -p no-op L49, step4 covered→report L57, step5 exists→skip L68-69/L79. differs→ask: step1 "ask the user before replacing... no way to ask → skip and report, never overwriting" L28. Second-run statement explicit L11 and L92. No path overwrites without an ask (step5 skips, never overwrites). | exists→skip + differs→ask + explicit second-run-safe, no silent overwrite | all present | PASS |
| C-3 | judgment: failure-path instructions | Step 0 L13-20 handles both cases: unsubstituted literal `${CLAUDE_PLUGIN_ROOT}/project-template/` L17, path-doesn't-exist L18, both name the situation and point at `/plugin marketplace add` + `/plugin install agent-guild`. L20: "never guess another payload location — not a sibling checkout, not a hardcoded repo path... nothing is written." | both cases stop, error names problem, no fallback, nothing written | present | PASS |
| C-4 | `.agent-guild/scripts/check-build.sh '...'` (exact from clause) | `check-build.sh: exit 0`; built to temp dir; `test -d skills/init` ok; `grep agent-guild:constitution\|agent-guild:job` matched; negative grep for bare `/job\|/constitution\|/init` found none; `git diff --quiet HEAD -- scripts/build-plugin.py scripts/plugin-src` clean. Packaged copy inspected: summary shows `/agent-guild:job` + `/agent-guild:constitution`, `/agent-guild:init` identity refs intact (L intro/idempotent/summary), `/plugin ...` left alone, no mangled paths. | exit 0 | exit 0 | PASS |
| C-5 | `.agent-guild/scripts/check-build.sh '...'` (exact from clause) | `check-build.sh: exit 0`. `git status --porcelain` shows only `?? .claude/skills/init/` — no other tracked change, deletion, or stray untracked file anywhere in repo. | exit 0 | exit 0 | PASS |
| C-6 | judgment: read next to job/ + constitution/ | Imperative agent-directed voice matching the references; concrete commands and paths throughout (mkdir -p incantation L46-47, diff -q L27, payload loop L64-76); failure paths enumerated not hand-waved (step 0's two hard-stops, step-by-step exists/differs cases). Source authored bare: only `agent-guild:` occurrences are `/agent-guild:init` identity prose (L9, L11, L92); `/job` and `/constitution` written bare (L89-90) for the build transform. Frontmatter fields all present. | house voice, concrete, enumerated failures, bare except identity | matches | PASS |

