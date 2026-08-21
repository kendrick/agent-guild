# Install Agent Guild

Agent Guild has one lifecycle and two host adapters. Every installation gives the host the same orchestrator contract, checked worker lifecycle, state bus, and four enforcement gates. The differences are limited to host discovery, skill invocation, agent representation, and hook trust; the Codex package also carries the project-local working-memory specialists that remain outside the lean Claude plugin.

Install the package once for each host you use, then initialize each project once. Run the setup in a throwaway project first and complete [the smoke suite](../SMOKE.md) before relying on the gates for real work.

## Prerequisites

- Python 3 is required. The hooks and installer use only the standard library.
- Install and authenticate the host you plan to use: Claude Code or Codex.
- Install and authenticate GitHub CLI if you want the `job` skill to fetch GitHub issues: `gh auth status` must succeed.
- For cross-vendor second opinions, authenticate the *other* host too. A Claude-hosted Guild calls `codex`; a Codex-hosted Guild calls `claude`.

Check the two courier credentials without starting a job:

```sh
codex login status
claude auth status --text
```

Treat a pass here as necessary, not sufficient. Both commands report on a stored credential without making a call, so both will say you are logged in while the lane fails. A stale refresh token still 401s, and on macOS the `claude` CLI reads the login keychain, which a sandboxed Codex session cannot open. A Codex-hosted courier needs two things before it can reach Claude at all: a headless token from `claude setup-token`, supplied as `CLAUDE_CODE_OAUTH_TOKEN`, and network egress from the sandbox, `sandbox_workspace_write.network_access = true`. The token alone trades a fast `Not logged in` for a silent timeout, because the credential then resolves and the request has nowhere to go. [The smoke suite's Part D](../SMOKE.md) probes each lane with a real crossing, which is the check that settles it.

The reciprocal direction has a smaller trap of its own. A Claude-hosted courier calls `codex`, so that account needs `codex login` and access to `gpt-5.6-terra`. The lane now passes `-m gpt-5.6-terra` and `--ignore-user-config`, which means a machine-local `~/.codex/config.toml` no longer decides which model answers, and an account that cannot reach the pinned model fails loudly with a 400 instead of quietly substituting whatever the default was. That is the intended trade: a lane that stops rather than one that reports a second opinion from a model nobody chose.

The courier is comparison data, not the verdict of record. A missing CLI, authentication failure, timeout, or twice-malformed response produces a `blocked` suffixed second opinion; the in-family checker still decides the task and its retry budget is unchanged. A quota response records a ledger event and creates `.agent-guild/state/exhausted/<lane>`; while that sentinel exists, tasks simply go without a second opinion, and nothing is substituted. The sentinel is user-cleared after quota recovers.

## Choose One Installation Route Per Host

Do not combine a host's plugin and repo-local route in the same project. Both carry the same skills and gates, so combining them creates duplicate skill names and makes every gate fire twice.

### Claude Code Plugin

Start Claude Code in the target project, then add the marketplace and install the qualified plugin:

```text
/plugin marketplace add kendrick/agent-guild
/plugin install agent-guild@kendrick
/agent-guild:init
```

Start a fresh Claude Code session after init so the new project contract is present from the beginning. Run `/hooks` and confirm five Agent Guild registrations appear, one copy of each: the four enforcement gates plus `session-nudge`, which only prints at session start (#67). Then start existing work with:

```text
/agent-guild:job <issue|file|url>
```

If this machine used Agent Guild 0.5.0 or earlier, remove the old marketplace identity before adding `kendrick`:

```text
/plugin uninstall agent-guild@agent-guild
/plugin marketplace remove agent-guild
```

Claude Code treats `agent-guild@agent-guild` and `agent-guild@kendrick` as separate plugins. Leaving both installed enables both copies and double-registers the gates.

Check that the new install came up enabled before you trust it. If the old identity was disabled, the replacement can inherit that state and land as `Status: ✘ disabled`, which registers no hooks and no agents while still looking installed. `claude plugin enable agent-guild@kendrick` fixes it.

### Codex Plugin From The CLI

Add the Git repository as a Codex marketplace and install the qualified plugin from a shell:

```sh
codex plugin marketplace add kendrick/agent-guild
codex plugin add agent-guild@kendrick
```

Start a new Codex session in the target project so the installed package is loaded, then invoke:

```text
$agent-guild:init
```

Open `/hooks`, review the exact Agent Guild definitions, and explicitly trust them before relying on the gates. Installation and init do not grant that trust. Start existing work with:

```text
$agent-guild:job <issue|file|url>
```

`codex plugin list --json` should report `agent-guild@kendrick` as installed and enabled. Use `codex plugin marketplace upgrade kendrick` when you need Codex to refresh the Git snapshot.

### Codex Plugin From The Desktop App

The desktop app and Codex CLI share configured marketplace sources. Add the repository once from a shell:

```sh
codex plugin marketplace add kendrick/agent-guild
```

Restart the ChatGPT desktop app, open the target project, select **Codex**, open **Plugins**, choose the **Kendrick** marketplace, and install **Agent Guild**. Start a new chat, invoke `$agent-guild:init`, then open `/hooks`, review the Agent Guild definitions, and explicitly trust them. Start work with `$agent-guild:job <issue|file|url>`.

If Agent Guild was already installed through the CLI, the desktop app should show the same plugin as installed; it is not a second copy. The fresh-project check is discovery in **Kendrick**, a successful init, one set of hook definitions, and the project files listed below.

### Repo-Local Codex For The IDE Extension

Use this route when the project should carry the Guild without a globally installed Codex plugin. From an Agent Guild source checkout, build the Codex package and run its bounded installer against the target project:

```sh
python3 scripts/build-plugin.py --target codex --out dist/codex-plugin
python3 dist/codex-plugin/project-template/install.py codex /absolute/path/to/project --project-skills
```

Open the target project in the Codex IDE extension and start a new chat. Open `/hooks`, review the exact Agent Guild definitions in the project's `.codex/hooks.json`, and explicitly trust them. Repo-local skills are unnamespaced, so start existing work with:

```text
$job <issue|file|url>
```

`--project-skills` is exclusive to this route. It installs the shared workflows under `.agents/skills/` and the shared hook scripts plus Guild handlers under project-local paths. Never add it during plugin init—the plugin already supplies those components.

### Manual Claude Copy-In

If you do not want the Claude plugin, copy `.claude/` and `.agent-guild/` from this repository into the target project. That copy carries `.agent-guild/CLAUDE.md`, the file the hook gates look for. Merge the `hooks` object from `.claude/settings.json` if the project already has that file; do not overwrite unrelated settings. Add `@.agent-guild/CLAUDE.md` to the root `CLAUDE.md`, add `.agent-guild/state/` to `.gitignore`, and create the state subdirectories.

This is Claude's repo-local route. Do not also enable the Claude plugin in that project.

## What Init Owns

Every route installs the same `.agent-guild/` project payload and runtime state directories. Every hook gate looks for `.agent-guild/CLAUDE.md` before running, so that file, not the `.agent-guild/` directory, is what makes a project initialized. The file is tracked, so removing the payload removes the Guild from the project. The installer is idempotent and preserves existing files it does not own. It fails before writing when it finds malformed ownership markers or a managed path redirected outside the project. A payload file whose bytes no longer match what the installer recorded shipping is preserved instead—the installer names it in a warning and keeps going, landing whatever payload files are still missing.

Host-specific ownership stays narrow:

| Route | Project Guidance | Agents And Skills | Hooks |
| --- | --- | --- | --- |
| Claude plugin | Bounded import in `CLAUDE.md` | Supplied by the plugin | Supplied by the plugin; init never edits `.claude/settings.json` |
| Codex plugin | Bounded section in `AGENTS.md` | Agents copied to `.codex/agents/`; skills supplied by the plugin | Supplied by the plugin; init never writes `.codex/hooks.json` |
| Repo-local Codex | Bounded section in `AGENTS.md` | Agents copied to `.codex/agents/`; skills copied to `.agents/skills/` | Guild handlers merged into `.codex/hooks.json`; scripts copied to `.agent-guild/hooks/` |

All three preserve unrelated project guidance, agents, skills, hook groups, configuration, and global host state.

Re-running init upgrades some of what it installed and preserves the rest, and the split does not follow the directory layout:

| Class | What a re-run does |
| --- | --- |
| Agents, skills, and the Codex project hooks | init overwrites each file whose shipped bytes differ (`_copy_owned`) |
| The payload: `.agent-guild/CLAUDE.md`, `scripts/`, `templates/`, `schemas/` | init lands each missing file, upgrades each file still matching its recorded hash, and preserves each file that differs, naming it in a warning (`_sync_payload`) |

The Codex project hooks land only on the repo-local `--project-skills` route, and they sit inside `.agent-guild/` like the payload does. Even so, `install()` splits them out of the payload before the drift check runs, so they upgrade on every re-init. A payload file already on disk upgrades only when its bytes still match the hash the installer recorded for it.

### The Provenance Record

Init writes `.agent-guild/provenance.json` on every run, beside the `.agent-guild/CLAUDE.md` marker. The record holds the plugin version that wrote the payload and a sha256 for each payload file, taken from the bytes the Guild shipped. Init gitignores `.agent-guild/state/` and nothing else, so the record commits with the payload it describes and every clone of the project carries it.

That record is how a re-run tells your edit from a version gap, one file at a time. When a file's bytes still match its recorded hash, nobody has touched it since init put it there, so this run brings it to current source and restamps the hash. The recorded version never enters that decision: a clean file upgrades whether its stamp trails the plugin's or matches it.

When the bytes differ from the recorded hash, somebody edited that file. Init keeps your bytes, names the path in a `local Agent Guild payload differs` warning, and carries the old hash forward untouched, so the next release refuses the same edit again instead of reading a version bump as consent. The refusal does not pin the project: the record still advances to the running plugin's version. To take the shipped copy back, delete the file and re-run init.

The run's `OK:` summary accounts for the whole payload in three terms. `updated` counts the files whose bytes changed, `preserved` counts the ones named in the warning, and `unchanged` carries the rest. Re-running init on a project nobody has edited reports zero preserved.

### Adopting A Pre-Provenance Project

A project installed before the record existed has payload on disk and no `provenance.json`. The first re-run adopts that payload instead of trusting it wholesale. Init records every file whose bytes match current source, at that hash and under the running plugin's version. It preserves every file that differs, names it in the warning, and leaves it out of the record entirely—all of them, not the first.

Leaving those files unrecorded is deliberate, and you will meet the warning again. A file with no entry gets the same treatment on every later re-run: preserved and reported, never overwritten, because nothing on disk separates an old release's bytes from an edit somebody made and meant. Restore the shipped bytes, or delete the file and re-run init, and the next run records the file and stops warning about it.

## Verify A Fresh Project

Run these shared checks from the initialized project:

```sh
test -f .agent-guild/CLAUDE.md && echo "contract present"
test -d .agent-guild/state/tasks && echo "state dirs present"
git check-ignore -q .agent-guild/state && echo "state dir gitignored"
git check-ignore -q .agent-guild/provenance.json; test $? -eq 1 && echo "provenance record tracked"
```

Then check the selected route:

| Route | Fresh-Project Evidence |
| --- | --- |
| Claude plugin | `CLAUDE.md` imports `@.agent-guild/CLAUDE.md`; `/hooks` shows the five Guild registrations, one copy each; `/agent-guild:job` is available |
| Codex CLI or desktop plugin | `AGENTS.md` has one bounded Agent Guild section; `.codex/agents/` has the nine-agent roster; `/hooks` shows one trusted copy of the Guild definitions; `$agent-guild:job` is available |
| Repo-local Codex IDE | The same `AGENTS.md` section and roster exist; `.agents/skills/job/SKILL.md`, `.codex/hooks.json`, and `.agent-guild/hooks/codex-hook-adapter.py` exist; `/hooks` shows one trusted copy; `$job` is available |

Every route in that table registers the same five handlers—`session-nudge`, `dispatch-guard`, `orchestrator-write-guard`, `subagent-return`, and `stop-gate`—so `/hooks` shows five entries (#67). The last four are the enforcement gates; the first only prints.

Finish with [SMOKE.md](../SMOKE.md). It runs one host-neutral lifecycle after these thin host setup checks.

## Avoid Double Registration

There must be exactly one provider of Agent Guild skills and hooks for a host in a project:

- Claude plugin plus a copied `.claude/settings.json` registers the same gates twice.
- Codex plugin plus repo-local `--project-skills` installs duplicate skills and hooks.
- The old and new Claude marketplace identities are distinct installations; remove the old one.

The common symptom is two copies of a hook in `/hooks` or two identical denial messages for one action. Remove or locally disable one installation; never patch a generated hook file to hide the symptom.
