# Building The Plugins

Agent Guild has one implementation and two generated host packages. Shared role behavior and workflow bodies live in `guild-core/`; host-specific metadata lives in `scripts/plugin-src/adapters/`. Never implement a feature by editing both generated packages. This is the maintainer build reference; user setup lives in [Install Agent Guild](installing.md).

## Prerequisites

Building either package requires only Python 3 and repository checkout—there is no dependency install or compile step. The `claude` CLI is required for the strict repository check, not for the build commands themselves. No Codex CLI is required to build the Codex package.

## Build The Claude Package

```sh
python3 scripts/build-plugin.py --target claude --out dist/claude-plugin
```

The package is written to `dist/claude-plugin/`, with its manifest at `dist/claude-plugin/.claude-plugin/plugin.json`. A Claude-target build must reproduce the established published `plugin/` tree exactly.

## Build The Codex Package

```sh
python3 scripts/build-plugin.py --target codex --out dist/codex-plugin
```

The package is written to `dist/codex-plugin/`, with its manifest at `dist/codex-plugin/.codex-plugin/plugin.json` and its lifecycle configuration at `dist/codex-plugin/hooks/hooks.json`.

Codex hooks are not automatically trusted. The installation guide requires users to open `/hooks`, review the exact Agent Guild definitions, and explicitly trust them before relying on the gates. The package and installer never claim or grant trust on the user's behalf.

Its `project-template/` contains the generated nine-agent Guild roster, one bounded `AGENTS.md` section, the repo-local hook configuration, and the same dependency-free project installer engine as the Claude package. The roster TOML is rendered from the same `guild-core/roles/` bodies as Claude; model, reasoning, sandbox, and host-bound instruction metadata come from `scripts/plugin-src/adapters/codex.json`.

Both targets render the same twelve workflow bodies from `guild-core/workflows/`: `init`, `job`, `constitution`, `decompose`, `retrospective`, `audition`, `hydrate-discover`, `hydrate-extract`, `hydrate-draft`, `hydrate-reconcile`, `hydrate-propose`, and `update-working-memory`. Host adapters add only frontmatter, agent representation, hook representation, and the thin `init` suffix. The exact plugin and repo-local invocation forms belong to the installation guide.

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

Explicit target builds only write beneath the requested output directory. They do not update tracked generated files or marketplaces.

## Sync The Repository

Maintainers use the default build after changing shared sources, adapter metadata, or the authored manifest:

```sh
python3 scripts/build-plugin.py
```

This command:

- refreshes the generated Claude wrappers under `.claude/`;
- rebuilds the tracked published Claude package under `plugin/`;
- rebuilds the tracked published Codex package under `plugins/agent-guild/`; and
- generates the Claude and Codex marketplace files from `scripts/plugin-src/plugin.json` and `scripts/plugin-src/marketplace.json`.

Both published layouts are compatibility surfaces. After a packaging refactor, `git diff --exit-code origin/main -- .claude plugin plugins/agent-guild` must stay clean unless the feature intentionally changes host behavior.

## Verify

Run the behavioral build tests first:

```sh
python3 scripts/test_build_plugin.py
python3 scripts/test_codex_hooks_packaging.py
python3 .agent-guild/hooks/test_hooks.py
python3 .agent-guild/hooks/test_codex_adapter.py
```

Then run the repository check:

```sh
python3 scripts/build-plugin.py --check
```

`--check` rebuilds from the shared sources, rejects drift in the dogfooded Claude wrappers, both published packages, and both marketplace files, then runs `claude plugin validate --strict plugin`. It therefore requires the `claude` CLI on `PATH`.

## Know What To Edit

| Path | Role | Edit Directly? |
| --- | --- | --- |
| `guild-core/` | Shared role behavior for the complete roster, workflow bodies, and workflow assets | Yes |
| `scripts/plugin-src/adapters/` | Host-specific frontmatter and metadata | Yes |
| `scripts/plugin-src/install-project.py` | Shared Claude/Codex project installer engine | Yes |
| `scripts/plugin-src/plugin.json` | Authored plugin identity and version | Yes—version bumps only during the release ritual |
| `scripts/plugin-src/marketplace.json` | Authored shared marketplace identity and presentation metadata | Yes |
| `.agent-guild/` | Host-neutral runtime payload copied into both packages | Yes |
| `.claude/agents/`, `.claude/skills/` | Generated Claude dogfood wrappers | No |
| `plugin/` | Generated, tracked Claude package | No |
| `plugins/agent-guild/` | Generated, tracked Codex package exposed by the Git marketplace | No |
| `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json` | Generated host marketplace views | No |
| `dist/` | Generated, ignored local packages | No |

For version bumps, changelog generation, tagging, and releases, continue with [Publishing](publishing.md).

## Continuous Integration

The [Plugin Build workflow](../.github/workflows/plugin-build.yml) runs the build tests, full dependency-free test suite, drift check, and strict Claude validator. It then builds both host packages, proves each CI-built package matches its tracked published package, and uploads the two packages as one workflow artifact.

CI never commits generated files. If a source change makes generated output stale, the workflow fails and the author runs the repository sync command locally.
