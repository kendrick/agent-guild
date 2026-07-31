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

- Every guild dispatch carries its id: `Task-ID: T-NNN` (worker/checker), `Audit-ID:` (auditor), `Audition-ID:` (audition). It rides in the prompt on a Claude host and in `task_name` on a Codex host, which encrypts the prompt. Codex restricts that field to lowercase, digits, and underscores, so it goes on the wire as `t_001` and canonicalizes back. Codex also wants that name unique per dispatch, so a discriminator follows the id (`t_001_r0_checker`) and the gate strips it. Untagged dispatches are blocked, as is any `followup_task` aimed at a guild agent.
- Orchestrator-scoped gates constrain the main session only — but PreToolUse *does* fire inside subagents, so those gates no-op on the `agent_id` CC stamps on subagent calls (`_lib.in_subagent`). Subagent behavior is otherwise prompt-guided plus tool-allowlist-backstopped.
- Hooks stay Python stdlib-only and fail loud. Don't add a dependency.
- State files name their attempt: `T-NNN-<tier>-r<retries>.md` for verdicts and disputes.
- Conventional-commit messages with a scope; docs use unspaced chained em dashes, no hard wraps, Title Case headings.

<!-- agent-guild:codex:start -->
## Agent Guild

Before running an Agent Guild job, read `.agent-guild/CLAUDE.md`; its lifecycle and state-file contract is authoritative. Apply the Codex host mapping below.

### Project Agent Roster

| Agent | Route | Sandbox |
| --- | --- | --- |
| `auditor` | Guild auditor for the constitution and task decomposition. Dispatch with an Audit-ID. | `read-only` |
| `checker-courier` | Read-only Guild courier for an independent second opinion. Dispatch with a Task-ID; its suffixed verdict never decides the task. | `read-only` |
| `checker-deterministic` | Read-only Guild checker that runs only the deterministic checks named by a task. Dispatch with a Task-ID. | `read-only` |
| `checker-judgment` | Read-only Guild checker that independently evaluates judgment clauses against artifact evidence. Dispatch with a Task-ID. | `read-only` |
| `hydrator` | Guild specialist for the five-phase working-memory hydration pipeline. | `workspace-write` |
| `worker-bulk` | Guild worker for mechanical, zero-judgment execution. Dispatch with a Task-ID. | `workspace-write` |
| `worker-craft` | Guild worker for user-facing, taste-sensitive work. Dispatch with a Task-ID. | `workspace-write` |
| `worker-standard` | Guild worker for clear-spec implementation judged primarily on correctness. Dispatch with a Task-ID. | `workspace-write` |
| `working-memory-synchronizer` | Guild specialist for synchronizing working memory after material project changes. | `workspace-write` |

### Codex Dispatch Boundary

- The main session is the orchestrator. Delegate Guild work to the exact project agent named by the routing table.
- Worker and checker dispatches carry `Task-ID: T-NNN`; auditor dispatches carry `Audit-ID: CON-audit` or `Audit-ID: DEC-audit`. Put the id in the prompt on a Claude host, in `task_name` on a Codex host, where it must be lowercased and underscored (`t_001`, `con_audit`).
- Read-only agents return the intended state-file path and complete content to the orchestrator. Never grant them write access to bypass that boundary.
- A read-only `checker-courier` returns an `AGENT_GUILD_COURIER_OUTCOME` from the fixed Claude runner. For a verdict outcome, persist the supplied verdict unchanged at the `-claude` suffixed path, validate and render it, then record the supplied metrics through `ledger-append.py`. For a quota outcome, append that ledger line first with `--quota-event`, then create `.agent-guild/state/exhausted/claude`; write no verdict. A courier outcome never replaces the unsuffixed in-family verdict.
- Agent Guild owns only this marked section of `AGENTS.md` and its generated files under `.codex/agents/`.

### Workflow Entry Point

- Start existing work with `$agent-guild:job <issue|file|url>`.
<!-- agent-guild:codex:end -->
