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

Run Claude Code or Codex as an org chart: workers build, independent checkers verify, nobody grades their own work.

[![Plugin Build](https://github.com/kendrick/agent-guild/actions/workflows/plugin-build.yml/badge.svg)](https://github.com/kendrick/agent-guild/actions/workflows/plugin-build.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Hosts: Claude Code and Codex](https://img.shields.io/badge/hosts-Claude%20Code%20%7C%20Codex-8A63D2)](docs/installing.md)
[![Runtime: Python 3 stdlib](https://img.shields.io/badge/runtime-Python%203%20stdlib-3776AB)](AGENTS.md)

A copy-in kit and generated plugin that runs Claude Code or Codex as an org chart. An expensive orchestrator plans and rules but never builds; cheap worker subagents build; independent checker agents verify the workers without trusting a word they say. It's a recipe, not a framework: nothing here but each host's own primitives, so there's no runner to install and no service to keep alive.

The idea it's built on: a cheap model doing well-specified work under an independent check is both cheaper and more reliable than one expensive model doing everything and grading itself.

```
                orchestrator (you, the main session)
                plans, writes the constitution and tasks, rules disputes
                 /              |               \
          workers           checkers            auditor
       build deliverables   verify workers'     verifies the
       bulk/standard/craft  work independently  orchestrator's own work
```

## Contents

- [Install](#install)
- [The Four Mechanisms](#the-four-mechanisms)
- [Where the Enforcement Actually Is](#where-the-enforcement-actually-is)
- [A Task Through the Lifecycle](#a-task-through-the-lifecycle)
- [Documentation](#documentation)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Install

The hooks and installer need Python 3 and use only the standard library. You also need Claude Code or Codex, authenticated. The `job` skill calls `gh` when you point it at a GitHub issue.

On a Claude host, install the marketplace once and initialize each project once:

```text
/plugin marketplace add kendrick/agent-guild
/plugin install agent-guild@kendrick
/agent-guild:init
```

Start a fresh session, then hand the guild a piece of work:

```text
/agent-guild:job 42
```

The argument takes a GitHub issue number, a local file, or a URL. The spec lands at `.agent-guild/state/spec.md`, Phase 0 writes the constitution, the auditor reviews it, and no worker dispatches until that audit passes.

Run the setup in a throwaway project first and walk [SMOKE.md](SMOKE.md) before relying on the gates for real work.

[Install Agent Guild](docs/installing.md) is the one setup guide, and it covers the rest: the Codex Git marketplace from the CLI or the desktop app, repo-local Codex bootstrap for the IDE extension, hook trust, cross-vendor credentials and fallbacks, the older Claude marketplace migration, and the double-registration footgun.

Every route follows the same shape: install once for the host, initialize once per project, start a fresh session, verify exactly one set of hooks, then walk SMOKE.md.

## The Four Mechanisms

**Constitution.** Phase 0 of any job writes `.agent-guild/state/constitution.md`: the standard "done right" is measured against, decided once. Every clause names how it's checked (a script, or a rubric a judgment-checker applies) and has to be falsifiable, meaning you can state an artifact that would fail it. A clause nobody can fail verifies nothing, and the auditor rejects it.

**Paired verification.** Every worker task has a checker task. The checker re-derives each claim from the artifact itself: it runs the build, diffs the file, fetches the URL. It never reads the worker's self-report, which lives in a separate file it's never pointed at. "I did it" is not evidence; the rebuilt output is. A task isn't done until a checker verdict file exists, and a hook enforces that rather than trusting the prompt.

**Retry ladder.** A failed check comes back to the same worker with the checker's specific diagnosis: file, line, the clause violated, expected versus actual. Each model tier gets its own retry budget. When a tier is spent, the work escalates to the next model (haiku to sonnet to opus to fable) with the budget reset, and the escalation is logged. Verification covers every rank, so the orchestrator's own constitution and task breakdown go to the auditor before any worker builds against them.

**Disputes.** Checkers can be wrong. A worker that believes a check failed valid work files a dispute instead of silently reworking; the orchestrator reads the artifact itself and rules against the constitution's text, correcting the checker when the worker is right. When one checker keeps getting overruled, the clause is usually the problem, not the checker.

## Where the Enforcement Actually Is

Be clear-eyed about this, because it decides how much the kit guarantees versus asks for good behavior. The gates constrain the main session only. Claude Code and current Codex builds fire tool hooks inside subagents, so each orchestrator-scoped gate stands down when it sees the `agent_id` the host stamps on a subagent call—that's what leaves a worker free to build. Everything mechanical lives at that main-session boundary:

- **dispatch-guard** blocks an illegal or untagged dispatch before it starts.
- **subagent-return** refuses to let a subagent finish until the state file proves it followed protocol.
- **stop-gate** won't let the turn end while a task is open, and hands over the exact next move.
- **orchestrator-write-guard** keeps the orchestrator out of deliverables while a job runs.

Everything a subagent does internally is guided by its prompt, not a hook. A checker is told to re-derive claims and never open `.agent-guild/state/notes/`; the auditor is told to hold the orchestrator to the constitution. What backs those rules up depends on the host, and the two differ more than they look. Claude checkers ship without an Edit tool, so one that decided to rewrite the artifact it was grading couldn't—strong, though still not a gate. Codex has no equivalent. Its agent definitions carry no tool allowlist, and the `sandbox_mode = "read-only"` they declare turns out to be ignored for spawned agents: a read-only checker writes as freely as the session around it (#67). On that host the worker/checker separation rests on the prompt alone. The fence runs along the main session; know which side of it a given guarantee sits on.

One known limit: the write-guard matches the host's structured edit tools—`Write`, `Edit`, and `MultiEdit` on Claude; `apply_patch` and its aliases on Codex—not `Bash`. A shell redirect like `printf … > deliverable.txt` slips past it, so on that path the orchestrator's restraint rests on the contract rather than the gate. Detecting writes in arbitrary shell can't be done statically without both false alarms and misses, so the guard covers the tools an agent reaches for first and leaves the shell to the prompt. The stakes are low: the orchestrator is a cooperative agent following the contract, not an adversary.

One fragile spot worth naming: `subagent-return` identifies which task a subagent ran by parsing its transcript, and neither host treats transcript representation as a stable contract. If a release changes it, the hook fails loud without hanging the subagent; the main-session stop gate still catches the open task. Claude fixtures are pinned in `.agent-guild/hooks/test_hooks.py` and Codex fixtures in `.agent-guild/hooks/test_codex_adapter.py`.

## A Task Through the Lifecycle

Job: rewrite a pricing page. The constitution includes C-4, the tagline must ship verbatim (checked by `check-protected.py`), and C-9, the tone matches the brand voice (a `checker-judgment` rubric). The auditor has already passed the constitution, so workers are unblocked.

1. The decompose skill writes `.agent-guild/state/tasks/T-007.md`: executor `worker-craft`, checker `checker-judgment`, citing C-4 and C-9. Status `pending`.
2. The orchestrator sets it `assigned` and dispatches worker-craft with `Task-ID: T-007`. The worker writes the copy, sets `artifacts` and status `needs-check`, and drops its notes in `.agent-guild/state/notes/T-007.md`.
3. `subagent-return` sees the task at `needs-check` with artifacts listed and lets the worker finish. The orchestrator can't end its turn (stop-gate), so it sets the task `checking` and dispatches the checker.
4. The checker runs `check-protected.py`, which reports the tagline's em dash was swapped for a hyphen. It writes `.agent-guild/state/verdicts/T-007-opus-r0.md` as FAIL, diagnosis naming the file, the line, C-4, and the exact character. Status goes to `rework`.
5. The orchestrator copies that diagnosis into the task's `## Rework diagnosis`, sets it back to `assigned` (retries now 1), and re-dispatches the same worker.
6. This time the worker reads the manifest as forbidding the fix the checker wanted and thinks the check misfired. It files `.agent-guild/state/disputes/T-007-opus-r1.md` citing C-4's text and sets the task `disputed`.
7. The orchestrator reads the dispute, the verdict, and the artifact itself. The checker misread the manifest; the worker was right. It appends a ruling upholding the worker, marks the verdict superseded, and sets the task `complete`.

Every step is a file written under `.agent-guild/state/`. Nothing here required a person to watch it happen.

## Documentation

| Document                                  | Covers                                                                                    |
| ----------------------------------------- | ----------------------------------------------------------------------------------------- |
| [Install Agent Guild](docs/installing.md) | Every install route, hook trust, cross-vendor credentials, what a re-run of init upgrades |
| [SMOKE.md](SMOKE.md)                      | The manual smoke suite that proves every gate fires                                       |
| [The Roles](docs/roles.md)                | What each agent in the roster is for                                                      |
| [Building The Plugins](docs/building.md)  | Per-host build commands, source-versus-output rules, the CI artifact flow                 |
| [Publishing](docs/publishing.md)          | Release and distribution                                                                  |
| [CHANGELOG.md](CHANGELOG.md)              | Generated per release from the commit history                                             |

The orchestrator contract itself lives in [.agent-guild/CLAUDE.md](.agent-guild/CLAUDE.md), which is the authoritative description of the lifecycle and the state-file protocol.

## Development

The hooks and check scripts are Python 3 with no dependencies, so the suites run without a setup step:

```console
$ python3 .agent-guild/hooks/test_hooks.py
429 passed, 0 failed
```

The Claude and Codex packages are generated from one shared core under `guild-core/`. `--check` proves the checked-in packages still match a fresh build:

```console
$ python3 scripts/build-plugin.py --check
Validating plugin manifest: plugin/.claude-plugin/plugin.json

✔ Validation passed
OK: shared-core wrappers, both published packages, and both marketplaces match fresh builds; the Claude plugin passes strict validation
```

Never edit generated package content as behavior. Behavior is authored in `guild-core/`, host metadata in `scripts/plugin-src/adapters/`, and `scripts/build-plugin.py` combines them. See [Building The Plugins](docs/building.md) for the full rules, and [AGENTS.md](AGENTS.md) for the stack and conventions.

CI runs the same suites on every push and pull request, then builds both packages and diffs them against the checked-in trees.

## Contributing

Issues are welcome, and the most useful ones are cases where a gate let something through that it shouldn't have. For a pull request, open an issue first so the shape is settled before you spend the effort.

Before you push, run `python3 .agent-guild/hooks/test_hooks.py` and `python3 scripts/build-plugin.py --check`. Use conventional-commit messages with a scope.

## License

[MIT](LICENSE) © Kendrick Arnett
