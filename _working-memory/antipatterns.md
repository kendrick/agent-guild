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
