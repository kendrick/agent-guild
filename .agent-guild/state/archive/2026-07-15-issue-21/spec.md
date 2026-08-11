---
source: github-issue
ref: kendrick/agent-guild#21
issue: 21
title: "feat(packaging): commit the plugin/ directory (guild-only), retire dist/"
fetched_at: 2026-07-15T04:29:03Z
---
# feat(packaging): commit the plugin/ directory (guild-only), retire dist/

Part of #19. Run the build for real and commit its output: a `plugin/` directory at the repo root carrying guild-only content — the lifecycle skills plus `init` and `job`, the six guild agents, the four gates plus the nudge, and a manifest with `author` as an object (a string fails schema validation at install time) and version 0.2.0. Working-memory tooling stays out. The gitignored `dist/` staging area from the first packaging dogfood retires.

Depends on the build script, and on init (#22) and the nudge (#23) existing so they can be packaged.
