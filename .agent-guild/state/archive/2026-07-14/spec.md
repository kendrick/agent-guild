# Spec: package the kit as a Claude Code plugin (#15)

## Goal

Produce a staged Claude Code plugin package of the guild's `.claude/` tooling — agents, skills, commands, and hooks — living under a `.claude-plugin/plugin.json`, and prove it installs and enforces correctly in a throwaway project. Advances issue #15 (phase 2 of the packaging endgame started in #14).

## Non-negotiable constraint: non-destructive

This session is enforced by the very hooks being packaged. The job MUST NOT move, delete, or rewrite the live `.claude/` tooling this session depends on. The plugin is built as a *separate staged artifact* (a build directory), leaving the current in-repo layout intact and the session's gates firing throughout. The repo-wide cutover — removing the old in-repo tooling and switching the project to the plugin — is explicitly OUT OF SCOPE; a human does that later, once this package is proven.

## Build location

The package is staged at `dist/plugin/` — a build artifact, not a repo-wide restructure. Add `dist/` to `.gitignore`. Every acceptance check references this concrete path.

## What to build

1. A plugin package directory rooted at `dist/plugin/` containing:
   - `.claude-plugin/plugin.json` — the plugin manifest.
   - The guild agents (from `.claude/agents/`) and skills (from `.claude/skills/`) under the plugin layout. `.claude/commands/` is empty — the slash commands are skills — so there is nothing to package there.
   - The hooks (from `.agent-guild/hooks/`), declared in a `hooks/hooks.json`, with every hook `command` rewired from `$CLAUDE_PROJECT_DIR/.agent-guild/hooks/...` to `$CLAUDE_PLUGIN_ROOT/...`.
   - `README.md` — the install story (see the hybrid catch below).
2. The hooks read state via `project_dir()`, so a plugin's gates keep `.agent-guild/state/` in the user's project untouched — verify this holds after the path rewire, don't assume it.

## The hybrid catch (must be handled, not worked around)

A plugin cannot ship an always-on CLAUDE.md; it contributes context only through skills, agents, and hooks that load on demand. So the orchestrator contract still rides per-project. The package standardizes on the existing one-line `@.agent-guild/CLAUDE.md` import (decided; not a SessionStart hook). The install story must document the hybrid: static tooling installs as a plugin, while the contract import and the runtime `.agent-guild/state/` stay in the user's repo. The docs must explain the import line itself to a reader who finds it in their CLAUDE.md — what it is, what it does, and that it was added when they installed the guild — so it never reads as a mystery line.

## Acceptance (what "done right" must prove)

- The staged package validates as a well-formed plugin (manifest parses; declared paths resolve).
- `python3 .agent-guild/hooks/test_hooks.py` still passes against the packaged hooks (the gate logic is unchanged by the move).
- With the staged plugin installed into a throwaway project, SMOKE Part A (the four hook gates) fires: no-job stop, missing-Task-ID denial, stop-gate hold, write-guard block. The gates behave identically to the in-repo kit.
- `.agent-guild/state/` in the throwaway project is created/read in the *project*, not under the plugin root.
- The install story is documented clearly enough that a new user can follow it without reading the source.

## Out of scope

- Deleting or rewriting the live in-repo `.claude/` tooling (the cutover).
- Packaging `.agent-guild/scripts/` (the job check tooling) or `.agent-guild/state/`; both stay project-side as part of the hybrid.
- Publishing to a plugin marketplace.
- An automated live-gate harness; the fresh-session gate run stays a documented manual portability procedure.
- The Codex courier lane (#2–#11) and any cross-vendor concern.
