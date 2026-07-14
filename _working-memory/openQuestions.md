# Open Questions

Unresolved and shouldn't be guessed at. Answers move to [[decisionLog]] when settled.

## When does the plugin packaging happen, and how does the contract ride along?

Packaging the `.claude/` half as a Claude Code plugin is deferred (see [[decisionLog]]). The unresolved part is the contract: a plugin can't ship an always-on `CLAUDE.md`, so it needs either the one-line `@.agent-guild/CLAUDE.md` import or a SessionStart hook that injects it. Which mechanism ships is open.

## Codex courier lane specifics, pending a live run

The second-vendor "courier" lane (a haiku subagent relaying work to an external CLI like `codex exec`) is designed and filed as GitHub issues but not built. Two things are explicitly "tune on first live encounter": the exact `codex exec` flags for read-only vs workspace-write sandboxing, and the quota/rate-limit failure shape the courier must detect to trip its exhaustion flag.
