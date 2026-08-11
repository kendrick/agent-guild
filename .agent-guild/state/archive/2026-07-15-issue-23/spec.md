---
source: github-issue
ref: kendrick/agent-guild#23
issue: 23
title: "feat(hooks): SessionStart nudge for partially-initialized projects"
fetched_at: 2026-07-15T04:11:14Z
---
# feat(hooks): SessionStart nudge for partially-initialized projects

Part of #19. `session-nudge.py` on the SessionStart event, `startup` matcher, one line of stdout, exit 0. It speaks only when a project shows partial init — `.agent-guild/` exists but the state directories or the root CLAUDE.md import line are missing — and stays silent on zero-evidence projects, because a user-scope install must never nag unrelated repos. Fresh adopters discover `/agent-guild:init` through the READMEs instead.

Unit tests follow the existing `test_hooks.py` fixture style.
