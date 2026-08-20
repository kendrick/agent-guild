# Publishing The Guild As A Public Claude Code Plugin

The design reference for the Job 2 epic. Job 1 (the `/job` intake skill, the provenance validator, the collapsed constitution interview, the `project_dir()` hardening) already landed; each Job 2 issue below is consumed through `/job <n>`, so every kickoff doubles as a live test of the intake path.

## Fixed Decisions

- The plugin ships guild-only content: the lifecycle skills (constitution, decompose, retrospective, audition, job, init), the six guild agents, and the four hook gates plus a SessionStart nudge. Working-memory tooling stays out.
- The published host packages live in committed `plugin/` and `plugins/agent-guild/` directories, generated from the same in-repo sources by one build script with a deterministic drift check. Gitignored `dist/` is only for explicit scratch or CI builds.
- This repo is its own `kendrick` marketplace on both hosts: `.claude-plugin/marketplace.json` points Claude at `./plugin`, while `.agents/plugins/marketplace.json` points Codex at `./plugins/agent-guild`. Both views are generated from the same release and marketplace metadata.
- Plugin components are always invoked namespaced (`/agent-guild:constitution`). Repo-local copies keep bare names; the build script rewrites the known invocation tokens in plugin-bound content only.

## Verified Platform Facts

- ~~Hooks have no auto-discovery: `plugin.json` must declare `"hooks": "./hooks/hooks.json"`.~~ Stale as of 2026-07-23: Claude Code now auto-loads a plugin's `hooks/hooks.json`, and declaring that standard path in `manifest.hooks` fails the plugin load as a duplicate ("manifest.hooks should only reference additional hook files"). Caught by the first live SMOKE Part C run; fixed in 0.3.1 by dropping the key. `${CLAUDE_PLUGIN_ROOT}` still substitutes in hook commands and skill content, and `${CLAUDE_PROJECT_DIR}` still points at the user's project inside plugin hooks, so state stays project-side.
- Plugins cannot ship an always-on CLAUDE.md, and `@`-imports don't expand env vars, so the orchestrator contract must be copied into each project. That is what `/agent-guild:init` is for. SessionStart `additionalContext` persistence is undocumented, so the contract never rides on it.
- SessionStart hooks take matchers (`startup|resume|clear|compact`); a nudge is one stdout line with exit 0.
- `plugin.json`'s `version` field drives update detection; bump it to publish.

## The Pieces

**Build script** (`scripts/build-plugin.py`, stdlib): renders the Claude and Codex packages from the shared core plus thin adapters; generates their hook files, project templates, manifests, and marketplace views; and applies host-specific invocation namespacing. `--check` rebuilds into a temporary directory, diffs both committed packages and marketplaces, and runs `claude plugin validate --strict` against the Claude package.

**Init** (`/agent-guild:init`, explicit-only): idempotent project setup — copy the contract if missing, add the `@.agent-guild/CLAUDE.md` import line with a provenance comment, create the state directories, gitignore state, copy the scripts/templates payload skipping existing files. Never overwrites without asking.

**Nudge** (`session-nudge.py`, `startup` matcher): speaks only on partial init—`.agent-guild/CLAUDE.md` exists but the state dirs or the import line are missing. Zero-evidence projects stay silent, because a user-scope install must never nag unrelated repos; fresh adopters find init through the READMEs.

**Marketplace and docs**: generated Claude and Codex marketplace views, manifests with `author` as an object, one canonical install guide, a separate maintainer build reference, a publishing checklist, one host-neutral smoke lifecycle with thin launch drills, and a documented footgun: enabling a plugin alongside the same repo-local hooks double-registers the gates.

## Standing Lessons From The Dogfoods

Deterministic checks must assert the source of a property, not the observable outcome — a machine-local global gitignore and a hand-rolled manifest rubric each produced a false green before this rule existed. Use the platform's own validators where they exist (`claude plugin validate --strict`), and expect the auditor's catches to land at Phase 0, on the orchestrator's clauses, before any worker runs.
