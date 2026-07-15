# Publishing The Guild As A Public Claude Code Plugin

The design reference for the Job 2 epic. Job 1 (the `/job` intake skill, the provenance validator, the collapsed constitution interview, the `project_dir()` hardening) already landed; each Job 2 issue below is consumed through `/job <n>`, so every kickoff doubles as a live test of the intake path.

## Fixed Decisions

- The plugin ships guild-only content: the lifecycle skills (constitution, decompose, retrospective, audition, job, init), the six guild agents, and the four hook gates plus a SessionStart nudge. Working-memory tooling stays out.
- The published plugin lives in a committed `plugin/` directory at the repo root, generated from the in-repo sources by a build script with a deterministic drift check. The gitignored `dist/` staging area from the first packaging dogfood retires.
- This repo is its own marketplace: `.claude-plugin/marketplace.json` at the repo root, `plugins[].source` pointing at `./plugin`. Colleagues install with `/plugin marketplace add kendrick/agent-guild` and `/plugin install`.
- Plugin components are always invoked namespaced (`/agent-guild:constitution`). Repo-local copies keep bare names; the build script rewrites the known invocation tokens in plugin-bound content only.

## Verified Platform Facts

- Hooks have no auto-discovery: `plugin.json` must declare `"hooks": "./hooks/hooks.json"`. `${CLAUDE_PLUGIN_ROOT}` substitutes in hook commands and skill content. `${CLAUDE_PROJECT_DIR}` still points at the user's project inside plugin hooks, so state stays project-side.
- Plugins cannot ship an always-on CLAUDE.md, and `@`-imports don't expand env vars, so the orchestrator contract must be copied into each project. That is what `/agent-guild:init` is for. SessionStart `additionalContext` persistence is undocumented, so the contract never rides on it.
- SessionStart hooks take matchers (`startup|resume|clear|compact`); a nudge is one stdout line with exit 0.
- `plugin.json`'s `version` field drives update detection; bump it to publish.

## The Pieces

**Build script** (`scripts/build-plugin.py`, stdlib): copies the guild agents, skills, and hooks into `plugin/`; generates `plugin/hooks/hooks.json` from `.claude/settings.json` by rewriting hook paths to `"${CLAUDE_PLUGIN_ROOT}"/hooks/` and appending the nudge registration; assembles `plugin/project-template/` (contract, check scripts, task templates — the per-project payload init copies); applies the namespacing map. `--check` rebuilds into a temp dir, diffs against the committed `plugin/`, and runs `claude plugin validate --strict` with the plugin manifest isolated (with both manifests in one folder, the validator only reads the marketplace one).

**Init** (`/agent-guild:init`, explicit-only): idempotent project setup — copy the contract if missing, add the `@.agent-guild/CLAUDE.md` import line with a provenance comment, create the state directories, gitignore state, copy the scripts/templates payload skipping existing files. Never overwrites without asking.

**Nudge** (`session-nudge.py`, `startup` matcher): speaks only on partial init — `.agent-guild/` exists but the state dirs or the import line are missing. Zero-evidence projects stay silent, because a user-scope install must never nag unrelated repos; fresh adopters find init through the READMEs.

**Marketplace and docs**: root `marketplace.json` (with a description — the strict validator warns without one), `plugin.json` at 0.2.0 with `author` as an object (a string fails schema validation at install time; learned the hard way), root README leading with the marketplace install, a plugin README adapted from the dist-era one, a publishing checklist, a SMOKE plugin-install drill, and a documented footgun: enabling the plugin inside this repo double-registers the gates alongside `.claude/settings.json`.

## Standing Lessons From The Dogfoods

Deterministic checks must assert the source of a property, not the observable outcome — a machine-local global gitignore and a hand-rolled manifest rubric each produced a false green before this rule existed. Use the platform's own validators where they exist (`claude plugin validate --strict`), and expect the auditor's catches to land at Phase 0, on the orchestrator's clauses, before any worker runs.
