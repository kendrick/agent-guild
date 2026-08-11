---
source: github-issue
ref: kendrick/agent-guild#20
issue: 20
title: "feat(build): build-plugin.py generates the committed plugin from in-repo sources"
fetched_at: 2026-07-15T00:33:44Z
---
# feat(build): build-plugin.py generates the committed plugin from in-repo sources

Part of #19. One script, stdlib python3, no dependencies: `scripts/build-plugin.py`.

It copies the guild agents, skills, and hooks into `plugin/`; generates `plugin/hooks/hooks.json` from `.claude/settings.json` by rewriting hook paths to `"${CLAUDE_PLUGIN_ROOT}"/hooks/` and appending the SessionStart nudge registration; assembles `plugin/project-template/` (contract, check scripts, task templates — the payload init copies into a project); and applies the bare-to-namespaced invocation map (`/constitution` becomes `/agent-guild:constitution`, etc.) to plugin-bound content only.

`--check` rebuilds into a temp dir, diffs against the committed `plugin/`, and runs `claude plugin validate --strict` with the plugin manifest isolated — with both manifests in one folder the validator only reads the marketplace one.

Design: docs/plugin-publish-plan.md, "Build script". Blocks the other children in this epic.
