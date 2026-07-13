# Project Overview

## What This Is

The Agent Guild is a copy-in kit that runs Claude Code as an org chart: an expensive orchestrator plans and rules but never builds, cheap worker subagents build, and independent checker agents verify the workers without trusting a word of their self-reports. It's a recipe, not a framework—nothing but Claude Code's own primitives, so there's no runner to install and no service to keep alive.

## Stack

- Language: Python 3 for the enforcement hooks (stdlib only, zero deps); Bash and one Node/ESM script for the check scripts.
- Framework: none. Pure Claude Code primitives—custom agents, skills, hooks, and `CLAUDE.md` memory.
- Data layer: a file-based message bus under `.agent-guild/state/` (Markdown with YAML frontmatter). No database.
- Only manifest: `.agent-guild/scripts/package.json` (`playwright` + `@axe-core/playwright`), self-installed on first run for `check-a11y.mjs` alone. Every other check is dependency-free.
- Deployment: copy two directories into a host repo. No build step.

## Repository Structure

- `.claude/` — the guild's agents, skills, and the `settings.json` hooks block. Claude Code discovers these here by location and nowhere else.
- `.agent-guild/` — everything else the kit owns: `hooks/`, `scripts/`, `templates/`, the orchestrator contract at `.agent-guild/CLAUDE.md`, and the runtime `state/` bus (gitignored).
- `CLAUDE.md` (root) — a one-line `@.agent-guild/CLAUDE.md` import that loads the contract every session.
- `docs/roles.md` — the guild roster: a bio per dispatchable member.
- `_working-memory/`, `scripts/`, `.github/`, `AGENTS.md` — the working-memory kit, a separate copy-in tool layered on top of the guild. Currently an untracked overlay (see [[decisionLog]]).

## Key Constraints

- The enforcement fence runs along the main session only. Claude Code hooks fire on the main session's actions, never on tool calls made inside a subagent—so every mechanical guarantee (`dispatch-guard`, `subagent-return`, `stop-gate`, `orchestrator-write-guard`) lives at a main-session boundary. Everything a subagent does internally is guided by its prompt and backstopped by tool allowlists (checkers ship without an Edit tool), not gated. Always know which side of that fence a given guarantee sits on.
- `subagent-return` identifies which task a subagent ran by parsing its transcript, and the transcript format is not a stable Claude Code contract. On a format change the hook fails closed (blocks loudly) rather than passing silently. The expected shape is pinned in `.agent-guild/hooks/test_hooks.py`; that's the one place to update if a CC version bump breaks it.
- Hooks are Python stdlib only and fail loud. Don't add a dependency to reach for convenience.
