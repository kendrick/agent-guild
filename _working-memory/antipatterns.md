# Antipatterns

<!-- Negative knowledge. Things the team tried that didn't work, captured so   -->
<!-- agents and humans don't re-litigate closed loops. Append-only, like        -->
<!-- decisionLog.md.                                                            -->
<!--                                                                            -->
<!-- Format: -->
<!-- ## YYYY-MM-DD — [Short title in imperative voice — what to avoid]         -->
<!-- **Tried:** What was attempted                                              -->
<!-- **What broke:** Observed failure mode                                      -->
<!-- **Why we backed out:** Root cause if known; otherwise the observed pain    -->
<!-- **Don't suggest:** Specific things agents should not re-propose            -->
<!--                                                                            -->
<!-- The last line is the agent-targeted lever. Be specific. "Don't suggest    -->
<!-- moving X to Y" beats "don't suggest big refactors."                       -->

## 2026-07-24: Don't ship optional properties in a schema bound for strict structured output

**Tried:** `verdict.schema.json` with `duration_ms`/`cost_usd` as optional properties, checked for codex compatibility by feature-subset inspection (no conditionals, conservative keywords) because no CLI existed to probe.
**What broke:** The first live `codex exec --output-schema` probe (issue #2, 2026-07-24) got a 400: OpenAI strict mode requires `required` to include every key in `properties`. Optionality itself is the rejected feature.
**Why we backed out:** Strict mode's contract is all-required; the expressive equivalent is required-but-nullable, which also matches the ledger's null-means-unreported convention. Proven live: the all-required variant round-tripped a conforming verdict from gpt-5.6-terra. Fix filed as #43.
**Don't suggest:** optional properties in any schema a vendor's strict structured output will consume. Make every field required and type the optional ones nullable.

## 2026-07-24: Don't inline derivable facts into task spec excerpts

**Tried:** The #42 task excerpt hardcoded the version-boundary commit list as orientation for the worker.
**What broke:** The list was wrong — it skipped the 0.2.0 and 0.3.0 bumps. Harmless only because the same excerpt instructed deriving boundaries from git, which the worker did; a checker taking the list literally would have computed wrong verification ranges (the r1 checker caught this).
**Why we backed out:** Excerpts are copied prose; anything derivable drifts the moment it's inlined.
**Don't suggest:** embedding git-derivable lists (boundaries, hashes, counts) in task excerpts. Name the derivation command and let workers and checkers run it.

## 2026-07-23: Don't declare `hooks/hooks.json` in a plugin's `manifest.hooks`

**Tried:** `scripts/plugin-src/plugin.json` declared `"hooks": "./hooks/hooks.json"` (correct when first designed; the plan doc's "hooks have no auto-discovery" platform fact backed it).
**What broke:** The plugin installed but failed to load—current Claude Code auto-loads a plugin's `hooks/hooks.json`, so declaring that standard path is rejected as a duplicate ("manifest.hooks should only reference additional hook files"). Caught by the first live SMOKE Part C run.
**Why we backed out:** Platform behavior changed; the standard path loads on its own now. Fixed in 0.3.1 by dropping the key and rebuilding.
**Don't suggest:** adding a `hooks` key to `scripts/plugin-src/plugin.json` for the standard path, or teaching `build-plugin.py` to emit one. `manifest.hooks` is only for *additional* hook files beyond `hooks/hooks.json`.

## 2026-07-14: Don't assume parent hooks skip subagent tool calls

**Tried:** Building orchestrator-write-guard (and the docs' mental model) on "parent PreToolUse hooks don't fire for tool calls made inside a subagent."
**What broke:** On CC 2.1.x PreToolUse fires in subagents too, so the guard fired in every worker and blocked the deliverable it was dispatched to write. The guild only worked because workers silently fell back to `Bash`.
**Why we backed out:** The assumption was never true on this CC version; `agent_id` is stamped only on subagent calls (confirmed against the hooks docs).
**Don't suggest:** scoping a gate by assuming hooks won't reach subagents. Scope main-session-only gates by checking `agent_id` (`_lib.in_subagent`). See #18.

## 2026-07-14: Don't identify a subagent's task from role:user transcript messages

**Tried:** `id_from_transcript` scanned only `role:"user"` messages for a `Task-ID:` line.
**What broke:** SubagentStop hands the hook the PARENT transcript, where the dispatch is an assistant `tool_use(Task|Agent)` block, not a user message. The id was never found, the gate failed closed, and the worker hung.
**Why we backed out:** Wrong place to look; the authoritative dispatch record is the assistant tool_use.
**Don't suggest:** reading the dispatch id from user messages. Read it from the assistant `tool_use(Task|Agent)` `input.prompt` (last dispatch). See #17.
