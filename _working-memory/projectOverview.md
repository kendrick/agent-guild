# Project Overview

## What This Is

The Agent Guild is a copy-in kit and generated plugin that runs Claude Code or Codex as an org chart: an expensive orchestrator plans and rules but never builds, cheap worker subagents build, and independent checker agents verify the workers without trusting a word of their self-reports. It's a recipe, not a framework—nothing but host primitives, so there's no runner to install and no service to keep alive.

## Stack

- Language: Python 3 for the enforcement hooks (stdlib only, zero deps); Bash and one Node/ESM script for the check scripts.
- Framework: none. Host primitives only—agents, skills, hooks, and persistent project guidance—with Claude and Codex packages generated from one source set.
- Data layer: a file-based message bus under `.agent-guild/state/` (Markdown with YAML frontmatter). No database.
- Only manifest: `.agent-guild/scripts/package.json` (`playwright` + `@axe-core/playwright`), self-installed on first run for `check-a11y.mjs` alone. Every other check is dependency-free.
- Deployment: install a generated host plugin or copy the generated repo-local payload into a project. No application runtime or compile step.

## Repository Structure

- `guild-core/` — the only authored home for shared role behavior and published workflow bodies/assets. It contains no Claude agent frontmatter or Codex TOML; host representation belongs to adapters.
- `.claude/` — generated shared wrappers plus host-only agents, skills, and the `settings.json` hooks block used to dogfood the Claude host. Claude Code discovers these here by location and nowhere else. Its generated `checker-courier` uses the Codex lane; the reciprocal Codex wrapper uses the Claude lane.
- `.agent-guild/` — everything else the kit owns: `hooks/`, `scripts/`, `templates/`, `schemas/` (the verdict and vendor-call JSON contracts), the orchestrator contract at `.agent-guild/CLAUDE.md`, and the runtime `state/` bus (gitignored).
- `CLAUDE.md` (root) — a one-line `@.agent-guild/CLAUDE.md` import that loads the contract every session.
- `plugin/` — the committed Claude plugin tree (agents, skills, hooks, and the per-project `project-template/` payload), assembled from in-repo sources by `scripts/build-plugin.py`. Never hand-edited (see [[conventions]]).
- `dist/codex-plugin/` — the ignored, release-stage Codex artifact generated from the shared core. It carries the complete `.codex/agents/` roster, all twelve shared workflows, plugin hooks, and a project template whose bounded installer can merge the same hooks for repo-local use; only the compact `scripts/plugin-src/codex.sha256` drift lock is committed until #53 defines the publishing surface.
- `.claude-plugin/marketplace.json` — makes this repo its own plugin marketplace, sourcing `./plugin`.
- `scripts/plugin-src/adapters/` — thin host-bound frontmatter, exact courier lane commands, and Codex interface metadata. `scripts/plugin-src/install-project.py` is the sole project installer engine for Claude, Codex plugin, and repo-local Codex. `scripts/build-plugin.py` renders dogfood and both packages from core plus adapters, and `--check` verifies generated wrappers, the published Claude tree, the staged Codex tree when present, and its committed lock; scripts under `.agent-guild/scripts/` include the fixed stdlib-only Claude CLI boundary plus the existing state/verdict helpers. `scripts/make-changelog.py` generates `CHANGELOG.md` sections from version-bump boundaries. `docs/` — `roles.md` (the guild roster), `publishing.md` (the release ritual), `vendor-ledger.md` (the ledger contract), `handoff-cost.md` (what an external dispatch costs, measured), `plugin-readme.md` (built into `plugin/README.md`), and `plugin-publish-plan.md`.
- `_working-memory/`, `scripts/`, `.github/`, `AGENTS.md` — the working-memory kit, a separate copy-in tool layered on top of the guild, committed into this repo (see [[decisionLog]]).

## Key Constraints

- The enforcement fence runs along the main session only, but **not** because hooks skip subagents—supported Claude Code and Codex builds fire tool hooks inside subagents too. Each orchestrator-scoped gate no-ops when it sees the `agent_id` the host stamps on a subagent call (`_lib.in_subagent`); that's what leaves a worker free to write its deliverable. Everything a subagent does internally is otherwise guided by its prompt and backstopped by tool allowlists. Codex adapter coverage is limited to tool paths that emit documented hook events, so it is a cooperative guardrail rather than a complete security boundary.
- `subagent-return` identifies which task a subagent ran by parsing its transcript, and neither host treats transcript representation as stable. On an unknown shape the gate fails loud but lets the subagent return instead of hanging; the main-session stop gate catches the still-open task. Claude fixtures are pinned in `.agent-guild/hooks/test_hooks.py` and Codex fixtures in `.agent-guild/hooks/test_codex_adapter.py`.
- Courier lanes map by host: Claude → `codex`, Codex → `claude`. The Codex courier remains project-read-only and returns an `AGENT_GUILD_COURIER_OUTCOME`; the gate validates that outcome before parent persistence. Missing/auth/malformed/timeout results are blocked second opinions, while quota returns require ledger-before-sentinel ordering. None can replace the unsuffixed in-family verdict.
- Hooks are Python stdlib only and fail loud. Don't add a dependency to reach for convenience.
