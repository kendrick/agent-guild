# Open Questions

Unresolved and shouldn't be guessed at. Answers move to [[decisionLog]] when settled.

## Does the working-memory kit get committed here, or stay a local overlay?

It's currently untracked (`_working-memory/`, `scripts/`, `.github/`, `AGENTS.md`, plus edits to `CLAUDE.md` and `.gitignore`). Committing it into the guild repo means the guild ships with a second kit bundled in; keeping it local keeps the two products separate. Not yet decided.

## When does the plugin packaging happen, and how does the contract ride along?

Packaging the `.claude/` half as a Claude Code plugin is deferred (see [[decisionLog]]). The unresolved part is the contract: a plugin can't ship an always-on `CLAUDE.md`, so it needs either the one-line `@.agent-guild/CLAUDE.md` import or a SessionStart hook that injects it. Which mechanism ships is open.

## Codex courier lane specifics, pending a live run

The second-vendor "courier" lane (a haiku subagent relaying work to an external CLI like `codex exec`) is designed and filed as GitHub issues but not built. Two things are explicitly "tune on first live encounter": the exact `codex exec` flags for read-only vs workspace-write sandboxing, and the quota/rate-limit failure shape the courier must detect to trip its exhaustion flag.
