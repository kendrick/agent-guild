```
                                       █ ▗▄▖    ▗▖
 the                 ▐▌                ▀ ▝▜▌    ▐▌
 ▟██▖ ▟█▟▌ ▟█▙ ▐▙██▖▐███    ▟█▟▌▐▌ ▐▌ ██  ▐▌  ▟█▟▌
 ▘▄▟▌▐▛ ▜▌▐▙▄▟▌▐▛ ▐▌ ▐▌    ▐▛ ▜▌▐▌ ▐▌  █  ▐▌ ▐▛ ▜▌
▗█▀▜▌▐▌ ▐▌▐▛▀▀▘▐▌ ▐▌ ▐▌    ▐▌ ▐▌▐▌ ▐▌  █  ▐▌ ▐▌ ▐▌
▐▙▄█▌▝█▄█▌▝█▄▄▌▐▌ ▐▌ ▐▙▄   ▝█▄█▌▐▙▄█▌▗▄█▄▖▐▙▄▝█▄█▌
 ▀▀▝▘ ▞▀▐▌ ▝▀▀ ▝▘ ▝▘  ▀▀    ▞▀▐▌ ▀▀▝▘▝▀▀▀▘ ▀▀ ▝▀▝▘
      ▜█▛▘                  ▜█▛▘
```

# The Agent Guild

A copy-in kit that runs Claude Code as an org chart. An expensive orchestrator plans and rules but never builds; cheap worker subagents build; independent checker agents verify the workers without trusting a word they say. It's a recipe, not a framework: nothing here but Claude Code's own primitives, so there's no runner to install and no service to keep alive.

The idea it's built on: a cheap model doing well-specified work under an independent check is both cheaper and more reliable than one expensive model doing everything and grading itself.

```
                orchestrator (you, the main session)
                plans, writes the constitution and tasks, rules disputes
                 /              |               \
          workers           checkers            auditor
       build deliverables   verify workers'     verifies the
       haiku/sonnet/opus    work independently  orchestrator's own work
```

## The Four Mechanisms

**Constitution.** Phase 0 of any job writes `.agent-guild/state/constitution.md`: the standard "done right" is measured against, decided once. Every clause names how it's checked (a script, or a rubric a judgment-checker applies) and has to be falsifiable, meaning you can state an artifact that would fail it. A clause nobody can fail verifies nothing, and the auditor rejects it.

**Paired verification.** Every worker task has a checker task. The checker re-derives each claim from the artifact itself: it runs the build, diffs the file, fetches the URL. It never reads the worker's self-report, which lives in a separate file it's never pointed at. "I did it" is not evidence; the rebuilt output is. A task isn't done until a checker verdict file exists, and a hook enforces that rather than trusting the prompt.

**Retry ladder.** A failed check comes back to the same worker with the checker's specific diagnosis: file, line, the clause violated, expected versus actual. Each model tier gets its own retry budget. When a tier is spent, the work escalates to the next model (haiku to sonnet to opus to fable) with the budget reset, and the escalation is logged. Verification covers every rank, so the orchestrator's own constitution and task breakdown go to the auditor before any worker builds against them.

**Disputes.** Checkers can be wrong. A worker that believes a check failed valid work files a dispute instead of silently reworking; the orchestrator reads the artifact itself and rules against the constitution's text, correcting the checker when the worker is right. When one checker keeps getting overruled, the clause is usually the problem, not the checker.

## Where the Enforcement Actually Is

Be clear-eyed about this, because it decides how much the kit guarantees versus asks for good behavior. The gates constrain the main session only. Claude Code *does* fire PreToolUse inside subagents, so each orchestrator-scoped gate stands down when it sees the `agent_id` Claude Code stamps on a subagent call—that's what leaves a worker free to build. Everything mechanical lives at that main-session boundary:

- **dispatch-guard** blocks an illegal or untagged dispatch before it starts.
- **subagent-return** refuses to let a subagent finish until the state file proves it followed protocol.
- **stop-gate** won't let the turn end while a task is open, and hands over the exact next move.
- **orchestrator-write-guard** keeps the orchestrator out of deliverables while a job runs.

Everything a subagent does internally is guided by its prompt, not a hook. A checker is told to re-derive claims and never open `.agent-guild/state/notes/`; the auditor is told to hold the orchestrator to the constitution. Those are prompt rules, backstopped by tool allowlists (checkers ship without an Edit tool, so they can't quietly rewrite an artifact). Strong, but not the same as a gate. The fence runs along the main session; know which side of it a given guarantee sits on.

One known limit: the write-guard matches `Write`, `Edit`, and `MultiEdit`, not `Bash`. A shell redirect like `printf … > deliverable.txt` slips past it, so on that path the orchestrator's restraint rests on the contract rather than the gate. Detecting writes in arbitrary shell can't be done statically without both false alarms and misses, so the guard covers the tools an agent reaches for first and leaves the shell to the prompt. The stakes are low: the orchestrator is a cooperative agent following the contract, not an adversary.

One fragile spot worth naming: `subagent-return` identifies which task a subagent ran by parsing its transcript, and the transcript format is not a stable Claude Code contract. If a CC release changes it, the hook fails closed (blocks loudly) rather than passing silently. The expected shape is pinned in `.agent-guild/hooks/test_hooks.py`; that's the one place to update if a version bump breaks it.

## A Task Through the Lifecycle

Job: rewrite a pricing page. The constitution includes C-4, the tagline must ship verbatim (checked by `check-protected.py`), and C-9, the tone matches the brand voice (a `checker-judgment` rubric). The auditor has already passed the constitution, so workers are unblocked.

1. `/decompose` writes `.agent-guild/state/tasks/T-007.md`: executor `worker-craft`, checker `checker-judgment`, citing C-4 and C-9. Status `pending`.
2. The orchestrator sets it `assigned` and dispatches worker-craft with `Task-ID: T-007`. The worker writes the copy, sets `artifacts` and status `needs-check`, and drops its notes in `.agent-guild/state/notes/T-007.md`.
3. `subagent-return` sees the task at `needs-check` with artifacts listed and lets the worker finish. The orchestrator can't end its turn (stop-gate), so it sets the task `checking` and dispatches the checker.
4. The checker runs `check-protected.py`, which reports the tagline's em dash was swapped for a hyphen. It writes `.agent-guild/state/verdicts/T-007-opus-r0.md` as FAIL, diagnosis naming the file, the line, C-4, and the exact character. Status goes to `rework`.
5. The orchestrator copies that diagnosis into the task's `## Rework diagnosis`, sets it back to `assigned` (retries now 1), and re-dispatches the same worker.
6. This time the worker reads the manifest as forbidding the fix the checker wanted and thinks the check misfired. It files `.agent-guild/state/disputes/T-007-opus-r1.md` citing C-4's text and sets the task `disputed`.
7. The orchestrator reads the dispute, the verdict, and the artifact itself. The checker misread the manifest; the worker was right. It appends a ruling upholding the worker, marks the verdict superseded, and sets the task `complete`.

Every step is a file written under `.agent-guild/state/`. Nothing here required a person to watch it happen.

## Install

Copy two directories into your project:

```
.claude/  .agent-guild/
```

`.claude/` holds the guild's agents, skills, and the `settings.json` hooks block—Claude Code discovers those there and nowhere else. Everything the kit adds beyond that (the hooks, scripts, templates, runtime state, and the orchestrator contract) lives under the single `.agent-guild/` directory, so it stays out of your repo root.

Then:

- Make the contract law: add one line, `@.agent-guild/CLAUDE.md`, to your project's `CLAUDE.md` (create one at the root if you don't have it). That import is what loads the orchestrator contract every session; the kit deliberately doesn't drop a second `CLAUDE.md` at your root.
- If you already have `.claude/settings.json`, merge the `hooks` block from this one rather than overwriting; otherwise copy the file.
- Add `.agent-guild/state/` to your `.gitignore` (or copy this repo's ignore rules for it). The runtime bus is per-job and never committed.
- Edit the routing table in `.agent-guild/CLAUDE.md` to your own model tiers.
- Confirm the gates load: `python3 .agent-guild/hooks/test_hooks.py` should report all pass.

The hooks reference `$CLAUDE_PROJECT_DIR`, so they work wherever the repo lands. `.agent-guild/scripts/check-a11y.mjs` installs its own Node dependencies on first run; everything else is Python or Bash with no dependencies.

Walk through `SMOKE.md` once in a fresh session to watch every gate fire before it guards real work.

## Later: A Plugin

Most of the kit would package as a Claude Code plugin: agents, skills, and hooks move under a `.claude-plugin/plugin.json`, with hook commands rewired to `$CLAUDE_PLUGIN_ROOT`. The hooks are the clean part, since they already read state from `$CLAUDE_PROJECT_DIR`, so a plugin's gates would keep `.agent-guild/state/` in your project untouched.

The catch is the orchestrator contract. Plugins can't ship an always-on CLAUDE.md; they contribute context through skills, agents, and hooks that load on demand, not persistent project instructions. So a plugin would still need a per-project way to make the contract law: the same one-line `@.agent-guild/CLAUDE.md` import used above, or a SessionStart hook that injects it. Expect a hybrid (static tooling as a plugin, the contract and `.agent-guild/state/` staying in the project), not a one-command install. Worth it once you're running the kit across many projects, not before.
