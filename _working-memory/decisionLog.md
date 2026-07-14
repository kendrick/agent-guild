# Decision Log

Append-only; newest entry on top. Don't edit past entries; supersede them with a new one.

Each entry follows this shape:

```markdown
## 2026-04-19: Short title

**Source:** the commit, PR, or discussion it came from (optional for hand-written entries)

**Context:** Why this came up.
**Decision:** What was decided.
**Alternatives considered:** What was rejected, and why.
```

## 2026-07-14: Scope orchestrator gates to the main session via `agent_id`

**Source:** SMOKE.md B2 run in a copied-in kit; confirmed against the CC hooks docs.

**Context:** The kit assumed "parent hooks do not fire for tool calls made inside subagents," so `orchestrator-write-guard` treated any trip as the orchestrator overreaching. False on CC 2.1.x — PreToolUse fires inside subagents too, so the guard was blocking workers from writing their own deliverables. The guild only appeared to work because workers fell back to `Bash`, which the guard's `Write|Edit|MultiEdit` matcher never covered.
**Decision:** Scope main-session-only gates by the `agent_id` Claude Code stamps on subagent hook input (absent in the main session). Added `_lib.in_subagent(data)`; `orchestrator-write-guard` no-ops when it's true. Corrected the docstring, README, projectOverview, and AGENTS.
**Alternatives considered:** A settings.json scope option (none exists); branching on `agent_type` (present in the main session under `--agent`, so it would wrongly disable the gate). Left open: the guard still ignores `Bash`, so the orchestrator could bypass it via shell redirection — tracked as a separate gap.

## 2026-07-14: Read the dispatch id from the tool_use block, and backstop SubagentStop

**Source:** commit ed29c54, PR #17

**Context:** `subagent-return` couldn't tell which task a subagent ran. `id_from_transcript` scanned `role:user` messages, but CC hands SubagentStop the PARENT transcript, where the dispatch is an assistant `tool_use(Task|Agent)` block. The id was never found, the gate failed closed, and with no backstop on SubagentStop the worker hung indefinitely.
**Decision:** Read the id from the assistant `tool_use(Task|Agent)` `input.prompt` (last dispatch, the one that just finished), with `role:user` text as a fallback. Add a stall backstop to `subagent-return` mirroring the Stop gate's.
**Alternatives considered:** PAUSED (lifts every gate); loosening the regex (the id was well-formed, just where the parser never looked).

## 2026-07-14: Commit the working-memory kit into the guild repo

**Source:** commit e5f6ac0

**Context:** The WM overlay (see the 2026-07-13 entry below) went in untracked, leaving open whether it belonged in this repo or should stay local.
**Decision:** Committed it (e5f6ac0), so the guild ships the working-memory kit bundled in. Closes the corresponding open question, now removed from openQuestions.

## 2026-07-13: Install the working-memory kit as an untracked overlay

**Source:** working tree (untracked `_working-memory/`, `scripts/`, `.github/`, `AGENTS.md`; modified `CLAUDE.md`, `.gitignore`)

**Context:** The guild repo had no durable, cross-session project memory. A separate copy-in kit provides one.
**Decision:** Layer the working-memory kit onto the guild and hydrate its files from the codebase before committing. The kit is not yet tracked—whether it lands in this repo or stays local is still open (see [[openQuestions]]).
**Alternatives considered:** Hand-writing context into `CLAUDE.md` (rejected—it bloats the always-on contract and has no update discipline).

## 2026-07-13: Consolidate the kit under `.agent-guild/`

**Source:** commit 5546d19, PR #16

**Context:** A copy-in install used to spray five entries across the host repo root (`CLAUDE.md`, `.claude/`, `hooks/`, `scripts/`, `templates/`, plus a runtime `state/`). That's a lot of surface for anyone trying the kit or keeping a repo tidy.
**Decision:** Move `hooks/`, `scripts/`, `templates/`, and the runtime `state/` bus under a single hidden `.agent-guild/`, and the orchestrator contract to `.agent-guild/CLAUDE.md`. The root `CLAUDE.md` becomes a one-line `@.agent-guild/CLAUDE.md` import. Install footprint drops to two directories: `.claude/` and `.agent-guild/`.
**Alternatives considered:** Ship as a plugin now (deferred—see the plugin entry). Keep the flat layout (rejected—clutters the host root).

## 2026-07-11: Let auditions through the gates with an allow path, not PAUSED

**Source:** commit d330792, PR #10

**Context:** Audition dispatches carry no `Task-ID`, so `dispatch-guard` blocked them and `subagent-return` failed closed on the id-less transcript—an audition subagent could never finish.
**Decision:** Add an `Audition-ID: A-NNN` allow path (log-and-pass) across `_lib.py` and both hooks, mirroring the auditor precedent.
**Alternatives considered:** The `PAUSED` escape hatch (rejected—it lifts every gate, which makes the audition run unrepresentative of a gated job).

## 2026-07-10: Enforcement lives at the main-session boundary only

**Source:** commit 39693ea

**Context:** Claude Code hooks fire on the main session's actions, not on tool calls made inside a subagent.
**Decision:** Put all four mechanical gates at main-session boundaries (`dispatch-guard`, `subagent-return`, `stop-gate`, `orchestrator-write-guard`) and back subagent-internal behavior with prompts plus tool allowlists (e.g. checkers ship with no Edit tool). Be explicit in the docs about which guarantees are gated and which are prompt-guided.
**Alternatives considered:** Treating prompt rules as equivalent to gates (rejected—it overstates what the kit guarantees).

## 2026-07-10: Fixed model ladder haiku → sonnet → opus → fable

**Source:** commit 66cfbf1 (orchestrator contract)

**Context:** Tasks vary from mechanical to taste-heavy, and a failed tier needs somewhere to escalate.
**Decision:** Route each task by the work, not a default. Escalation climbs the ladder with the retry budget reset at each rung; `fable` is the reserved final rung for genuinely hard, ambiguous problems. There is no rung above it.
**Alternatives considered:** A single model for everything (rejected—the kit's whole premise is that a cheap model under an independent check beats one expensive model grading itself).

## Deferred: package the kit as a Claude Code plugin

**Source:** README "Later: A Plugin"; commit 4cc4d9d

**Context:** Most of the kit (agents, skills, hooks) would package as a plugin under `.claude-plugin/plugin.json`.
**Decision:** Defer. A plugin can't ship an always-on `CLAUDE.md`, so the contract still needs a per-project import or a SessionStart hook that injects it. Expect a hybrid (static tooling as a plugin, the contract and `state/` staying in the project), worth it only once the kit runs across many projects.
