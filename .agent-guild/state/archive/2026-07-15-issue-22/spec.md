---
source: github-issue
ref: kendrick/agent-guild#22
issue: 22
title: "feat(skills): /agent-guild:init finishes a project install"
fetched_at: 2026-07-15T01:45:37Z
---
# feat(skills): /agent-guild:init finishes a project install

Part of #19. The hybrid install needs a per-project half a plugin cannot ship: the always-on orchestrator contract and the runtime state. `/agent-guild:init` finishes it idempotently — copy the contract if missing, add the `@.agent-guild/CLAUDE.md` import line with a one-line provenance comment, create the state directories, gitignore state, and copy the scripts/templates payload while skipping files that already exist. It never overwrites without asking.

Design: docs/plugin-publish-plan.md, "Init".
