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

The courier is comparison data, not the verdict of record. A missing CLI, authentication failure, timeout, or twice-malformed response produces a `blocked` suffixed second opinion; the in-family checker still decides the task and its retry budget is unchanged. A quota response records a ledger event and creates `.agent-guild/state/exhausted/<lane>` before the Guild falls back to the in-family checker. The sentinel is user-cleared after quota recovers.

## Choose One Installation Route Per Host

Do not combine a host's plugin and repo-local route in the same project. Both carry the same skills and gates, so combining them creates duplicate skill names and makes every gate fire twice.

### Claude Code Plugin

Start Claude Code in the target project, then add the marketplace and install the qualified plugin:

```text
/plugin marketplace add kendrick/agent-guild
/plugin install agent-guild@kendrick
/agent-guild:init
```

Start a fresh Claude Code session after init so the new project contract is present from the beginning. Run `/hooks` and confirm there is one Agent Guild registration for each gate, then start existing work with:

```text
/agent-guild:job <issue|file|url>
```

If this machine used Agent Guild 0.5.0 or earlier, remove the old marketplace identity before adding `kendrick`:

```text
/plugin uninstall agent-guild@agent-guild
/plugin marketplace remove agent-guild
```

Claude Code treats `agent-guild@agent-guild` and `agent-guild@kendrick` as separate plugins. Leaving both installed enables both copies and double-registers the gates.

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

If you do not want the Claude plugin, copy `.claude/` and `.agent-guild/` from this repository into the target project. Merge the `hooks` object from `.claude/settings.json` if the project already has that file; do not overwrite unrelated settings. Add `@.agent-guild/CLAUDE.md` to the root `CLAUDE.md`, add `.agent-guild/state/` to `.gitignore`, and create the state subdirectories.

This is Claude's repo-local route. Do not also enable the Claude plugin in that project.

## What Init Owns

Every route installs the same `.agent-guild/` project payload and runtime state directories. The installer is idempotent, preserves existing files it does not own, and fails before writing when it finds malformed ownership markers, redirected managed paths, or conflicting managed content.

Host-specific ownership stays narrow:

| Route | Project Guidance | Agents And Skills | Hooks |
| --- | --- | --- | --- |
| Claude plugin | Bounded import in `CLAUDE.md` | Supplied by the plugin | Supplied by the plugin; init never edits `.claude/settings.json` |
| Codex plugin | Bounded section in `AGENTS.md` | Agents copied to `.codex/agents/`; skills supplied by the plugin | Supplied by the plugin; init never writes `.codex/hooks.json` |
| Repo-local Codex | Bounded section in `AGENTS.md` | Agents copied to `.codex/agents/`; skills copied to `.agents/skills/` | Guild handlers merged into `.codex/hooks.json`; scripts copied to `.agent-guild/hooks/` |

All three preserve unrelated project guidance, agents, skills, hook groups, configuration, and global host state.

## Verify A Fresh Project

Run these shared checks from the initialized project:

```sh
test -f .agent-guild/CLAUDE.md && echo "contract present"
test -d .agent-guild/state/tasks && echo "state dirs present"
git check-ignore -q .agent-guild/state && echo "state dir gitignored"
```

Then check the selected route:

| Route | Fresh-Project Evidence |
| --- | --- |
| Claude plugin | `CLAUDE.md` imports `@.agent-guild/CLAUDE.md`; `/hooks` shows one copy of each Guild gate; `/agent-guild:job` is available |
| Codex CLI or desktop plugin | `AGENTS.md` has one bounded Agent Guild section; `.codex/agents/` has the nine-agent roster; `/hooks` shows one trusted copy of the Guild definitions; `$agent-guild:job` is available |
| Repo-local Codex IDE | The same `AGENTS.md` section and roster exist; `.agents/skills/job/SKILL.md`, `.codex/hooks.json`, and `.agent-guild/hooks/codex-hook-adapter.py` exist; `/hooks` shows one trusted copy; `$job` is available |

Finish with [SMOKE.md](../SMOKE.md). It runs one host-neutral lifecycle after these thin host setup checks.

## Avoid Double Registration

There must be exactly one provider of Agent Guild skills and hooks for a host in a project:

- Claude plugin plus a copied `.claude/settings.json` registers the same gates twice.
- Codex plugin plus repo-local `--project-skills` installs duplicate skills and hooks.
- The old and new Claude marketplace identities are distinct installations; remove the old one.

The common symptom is two copies of a hook in `/hooks` or two identical denial messages for one action. Remove or locally disable one installation; never patch a generated hook file to hide the symptom.
