<!-- working-memory:start -->

## Working Memory

**AGENT INSTRUCTION:** before deciding what to read, scan the on-demand table under `## Working Memory` in [`AGENTS.md`](AGENTS.md). If your task matches a row, that file is required reading before you proceed.

Always read `_working-memory/activeContext.md` on session start. AGENTS.md is the canonical source for the on-demand table and update rules.
To sync working memory, run `/update-working-memory` or invoke the `working-memory-synchronizer` agent.

<!-- working-memory:end -->

# agent-guild

The orchestrator contract and every piece of guild tooling live under `.agent-guild/` so a copied-in kit leaves your repo root uncluttered. The contract is imported below, which Claude Code loads as always-on project instructions. When you copy the kit into your own project, add this one line to your existing `CLAUDE.md` (or create one) instead of copying a second file to your root.

@.agent-guild/CLAUDE.md
