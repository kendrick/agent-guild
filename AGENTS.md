# AGENTS.md

## Stack

- Enforcement hooks: Python 3, stdlib only, zero dependencies.
- Check scripts: Bash and Python, dependency-free; one exception, `check-a11y.mjs` (Node/ESM, self-installs `playwright` + `@axe-core/playwright` on first run).
- Agents, skills, and the orchestrator contract: Markdown, loaded by Claude Code as native primitives. No application runtime, no build.

## Build / Test / Lint

- Test the gates: `python3 .agent-guild/hooks/test_hooks.py` (should report all pass).
- Full manual smoke of every gate: walk `SMOKE.md` once in a fresh session.
- No build step and no repo-wide linter; the `.agent-guild/scripts/check-*` scripts are per-job verifiers a checker runs, not project lint.

<!-- working-memory:start -->
## Working Memory

This project uses a two-tier working memory at `_working-memory/`.

**AGENT INSTRUCTION:** scan this section BEFORE deciding what to read. If your task matches a row in the on-demand table, that file is required reading before you proceed.

### Always read on session start:

- `_working-memory/activeContext.md`: current focus, last decision, known risks (≤20 lines, local only / gitignored)

### Read on demand:

| File                 | Read when...                                                                                       |
| -------------------- | ------------------------------------------------------------------------------------------------- |
| `projectOverview.md` | Before starting a feature, or onboarding to the codebase                                          |
| `decisionLog.md`     | Before an architectural or scoping decision; check what's already been settled                     |
| `dataContracts.md`   | Before creating or changing anything that produces or consumes shared data                         |
| `conventions.md`     | Before writing new code, or when reviewing a pattern                                               |
| `openQuestions.md`   | When you hit ambiguity; check here before guessing                                                 |
| `antipatterns.md`    | Before proposing a refactor, library swap, or architectural change; check whether it's been tried  |

### Updating working memory:

- After completing a feature or making a significant decision, update `activeContext.md` and the relevant on-demand file.
- `activeContext.md` is a queue: evict completed items to `decisionLog.md`.
- `decisionLog.md` and `antipatterns.md` are both append-only. Never edit past entries.
- Never let `activeContext.md` exceed 20 lines.
<!-- working-memory:end -->

## Conventions

Full detail in `_working-memory/conventions.md`. The load-bearing few:

- Every guild dispatch prompt carries its id: `Task-ID: T-NNN` (worker/checker), `Audit-ID:` (auditor), `Audition-ID:` (audition). Untagged dispatches are blocked.
- Orchestrator-scoped gates constrain the main session only — but PreToolUse *does* fire inside subagents, so those gates no-op on the `agent_id` CC stamps on subagent calls (`_lib.in_subagent`). Subagent behavior is otherwise prompt-guided plus tool-allowlist-backstopped.
- Hooks stay Python stdlib-only and fail loud. Don't add a dependency.
- State files name their attempt: `T-NNN-<tier>-r<retries>.md` for verdicts and disputes.
- Conventional-commit messages with a scope; docs use unspaced chained em dashes, no hard wraps, Title Case headings.
