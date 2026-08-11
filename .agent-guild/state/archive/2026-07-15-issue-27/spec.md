---
source: github-issue
ref: kendrick/agent-guild#27
issue: 27
title: "fix(hooks): dispatch-guard must recognize namespaced plugin agent types"
fetched_at: 2026-07-15T03:40:53Z
---
# fix(hooks): dispatch-guard must recognize namespaced plugin agent types

Part of #19, discovered live when the dist-era plugin came online in the dev session: plugin-shipped agents surface with namespaced `subagent_type` values (`agent-guild:worker-standard`, `agent-guild:auditor`, ...), but `_lib.GUILD_AGENTS` and `DEFAULT_MODEL` key on bare names. `dispatch-guard` therefore treats every namespaced guild dispatch as a non-guild agent and waves it through — no Task-ID requirement, no CON-audit precondition, no tier/model matching. In a plugin-installed project the central gate simply doesn't gate.

The SubagentStop matcher happens to survive (regex substring match on `worker-bulk|...`), which makes it worse: the return gate fires and fail-closes against state the dispatch gate never enforced.

Fix in `_lib.py`: normalize `subagent_type` by stripping a `<plugin>:` prefix (or match on the suffix) before the `GUILD_AGENTS`/`DEFAULT_MODEL` lookups, with fixture coverage in `test_hooks.py` for both bare and namespaced forms. Must land before #21 commits the plugin tree, since #21's acceptance implies the gates work when installed.

Also observed, for the record: enabling the plugin inside this repo double-registers all four gates alongside `.claude/settings.json` — the footgun #25 documents. The stale dist-era package (10 skills, pre-#20 content) should be uninstalled/disabled here either way.
