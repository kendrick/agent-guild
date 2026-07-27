# Building The Plugins

Agent Guild has one implementation and two generated host packages. Shared role behavior and workflow bodies live in `guild-core/`; host-specific metadata lives in `scripts/plugin-src/adapters/`. Never implement a feature by editing both generated packages.

## Prerequisites

Building either package requires only Python 3 and repository checkout—there is no dependency install or compile step. The `claude` CLI is required for the strict repository check, not for the build commands themselves. No Codex CLI is required to build the Codex package.

## Build Claude

```sh
python3 scripts/build-plugin.py --target claude --out dist/claude-plugin
```

The package is written to `dist/claude-plugin/`, with its manifest at `dist/claude-plugin/.claude-plugin/plugin.json`. A Claude-target build must reproduce the established published `plugin/` tree exactly. Load or publish it as a Claude Code plugin, run `/agent-guild:init` once in each project, then start existing work with `/agent-guild:job <issue|file|url>`.

## Build Codex

```sh
python3 scripts/build-plugin.py --target codex --out dist/codex-plugin
```

The package is written to `dist/codex-plugin/`, with its manifest at `dist/codex-plugin/.codex-plugin/plugin.json`. When it is installed as a Codex plugin, run `$agent-guild:init` once in each project, then start existing work with `$agent-guild:job <issue|file|url>`.

Its `project-template/` contains the generated nine-agent Guild roster, one bounded `AGENTS.md` section, and the same dependency-free project installer engine as the Claude package. The roster TOML is rendered from the same `guild-core/roles/` bodies as Claude; model, reasoning, sandbox, and host-bound instruction metadata come from `scripts/plugin-src/adapters/codex.json`.

## Bootstrap A Codex Project

Build the Codex package, then point its initializer at the target project root:

```sh
python3 dist/codex-plugin/project-template/install.py codex /path/to/project --project-skills
```

`--project-skills` is the IDE-bootstrap switch: it installs the complete workflow set under the project's `.agents/skills/`, where Codex discovers repo-local skills. Omit it when the Codex plugin itself is installed—the plugin already supplies the same skills, and copying them into the project would create duplicate names. After IDE bootstrap, start existing work with `$job <issue|file|url>`.

The installer creates or refreshes only the packaged roster under `.codex/agents/`, the packaged workflows under `.agents/skills/` when requested, and the section of the root `AGENTS.md` bounded by `<!-- agent-guild:codex:start -->` and `<!-- agent-guild:codex:end -->`. It preserves all text outside that section, `.codex/config.toml`, unrelated project agents and skills, working-memory content, audition results, and every user/global Codex path. Re-running it is idempotent; malformed ownership markers or a managed path redirected outside the project fail closed before any write.

The generated read-only checker and auditor configurations keep their verification boundary by returning the intended state-file path and complete proposed content to the parent orchestrator. The parent persists that content; do not grant a checker write access to work around the handoff.

## Workflow Surface

Both host packages render the same twelve workflow bodies from `guild-core/workflows/`: `init`, `job`, `constitution`, `decompose`, `retrospective`, `audition`, `hydrate-discover`, `hydrate-extract`, `hydrate-draft`, `hydrate-reconcile`, `hydrate-propose`, and `update-working-memory`. Host adapters add only frontmatter and the thin `init` command suffix.

| Context | Initialize | Start Existing Work |
| --- | --- | --- |
| Installed Claude plugin | `/agent-guild:init` | `/agent-guild:job <issue\|file\|url>` |
| Installed Codex plugin | `$agent-guild:init` | `$agent-guild:job <issue\|file\|url>` |
| Repo-local Codex bootstrap | Run the installer command above | `$job <issue\|file\|url>` |

Codex skills use `$skill-name` or the `/skills` picker; they are not Claude-style slash commands. The two Codex forms differ only because plugin skills are namespaced while repo-local skills are not.

## Build Both

```sh
python3 scripts/build-plugin.py --target all --out dist/packages
```

This writes two standalone packages:

```text
dist/packages/
├── claude-plugin/
└── codex-plugin/
```

Explicit target builds only write beneath the requested output directory. They do not update tracked generated files or the Codex release lock.

## Sync The Repository

Maintainers use the default build after changing shared sources, adapter metadata, or the authored manifest:

```sh
python3 scripts/build-plugin.py
```

This command:

- refreshes the generated Claude wrappers under `.claude/`;
- rebuilds the tracked published Claude package under `plugin/`;
- stages the ignored Codex package under `dist/codex-plugin/`; and
- refreshes the tracked Codex artifact lock at `scripts/plugin-src/codex.sha256`.

The published Claude layout is a compatibility surface. After a packaging refactor, `git diff --exit-code origin/main -- .claude plugin` must stay clean unless the feature intentionally changes Claude behavior.

## Verify

Run the behavioral build tests first:

```sh
python3 scripts/test_build_plugin.py
```

Then run the repository check:

```sh
python3 scripts/build-plugin.py --check
```

`--check` rebuilds from the shared sources, rejects drift in the dogfooded Claude wrappers and published Claude package, verifies the Codex artifact lock, and runs `claude plugin validate --strict plugin`. It therefore requires the `claude` CLI on `PATH`. The check does not require `dist/codex-plugin/` to exist; when that local staging tree is present, it is checked for hand edits too.

## Know What To Edit

| Path | Role | Edit Directly? |
| --- | --- | --- |
| `guild-core/` | Shared role behavior for the complete roster, workflow bodies, and workflow assets | Yes |
| `scripts/plugin-src/adapters/` | Host-specific frontmatter and metadata | Yes |
| `scripts/plugin-src/install-project.py` | Shared Claude/Codex project installer engine | Yes |
| `scripts/plugin-src/plugin.json` | Authored plugin identity and version | Yes—version bumps only during the release ritual |
| `.agent-guild/` | Host-neutral runtime payload copied into both packages | Yes |
| `.claude/agents/`, `.claude/skills/` | Generated Claude dogfood wrappers | No |
| `plugin/` | Generated, tracked Claude package | No |
| `dist/` | Generated, ignored local packages | No |
| `scripts/plugin-src/codex.sha256` | Generated Codex artifact lock | No |

For version bumps, changelog generation, tagging, and releases, continue with [Publishing](publishing.md).

## Continuous Integration

The [Plugin Build workflow](../.github/workflows/plugin-build.yml) runs the build tests, full dependency-free test suite, drift check, and strict Claude validator. It then builds both host packages, proves the CI-built Claude package matches the tracked published package, and uploads the two packages as one workflow artifact.

CI never commits generated files. If a source change makes generated output stale, the workflow fails and the author runs the repository sync command locally.
