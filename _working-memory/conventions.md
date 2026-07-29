# Conventions

How we do things here. Stable patterns, not decisions—those live in [[decisionLog]].

## Dispatch Protocol

- Every worker or checker dispatch must carry a `Task-ID: T-NNN`; the auditor carries `Audit-ID: CON-audit` or `DEC-audit`; auditions carry `Audition-ID: A-NNN`. `dispatch-guard` blocks any guild dispatch missing its id. (`.agent-guild/hooks/dispatch-guard.py`)
- Where that id rides depends on the host. A Claude dispatch puts it in the prompt; a Codex dispatch puts it in `task_name`, because Codex encrypts the prompt before any hook runs. `dispatch-guard` reads the structured field first and falls back to the prompt line, so one dispatch shape works on both. (#71)
- Never pass a `model` override that disagrees with the task's `executor_model`. `dispatch-guard` blocks the mismatch—it's the backstop for a tier bump you recorded but forgot to apply.
- A FAIL comes back to the same worker on the same model with the checker's verbatim diagnosis copied into the task's `## Rework diagnosis`. A tier gets `max_retries` (default 2) tries before escalation.
- Dual-check regime: until #34 closes, every task reaching `checking` also gets a `checker-courier` second opinion after its checker of record returns. Claude hosts use the `codex` suffix/lane; Codex hosts use `claude`. The suffixed verdict is comparison data—it never outvotes the standard stem—and a disagreement is dispute-grade input the orchestrator reads directly.

## State File Naming

- Tasks: `.agent-guild/state/tasks/T-NNN.md`. Notes: `.agent-guild/state/notes/T-NNN.md`.
- Verdicts and disputes embed tier and retry: `T-NNN-<tier>-r<retries>.md` (e.g. `T-007-opus-r1.md`), so a per-tier retry reset never overwrites an earlier tier's file. Audit verdicts use `CON-audit-rN.md` / `DEC-audit-rN.md`. (`.agent-guild/templates/verdict.md`)

## Hooks and Checks

- Hooks are Python 3, stdlib only, and fail loud / fail closed. Never add a dependency. (`.agent-guild/hooks/`)
- Check scripts are dependency-free (Bash or Python) with one exception: `check-a11y.mjs` self-installs its Node deps on first run into a gitignored `node_modules`. (`.agent-guild/scripts/`)
- Checkers ship without an Edit tool—a tool-allowlist backstop so a verifier can't quietly rewrite the artifact it's judging. (`.claude/agents/checker-*.md`)
- Main-session-only gates (chiefly `orchestrator-write-guard` and `stop-gate`) no-op inside subagents via the `agent_id` supported hosts stamp on subagent hook input (`_lib.in_subagent`); tool hooks *do* fire in subagents. Every hook carries an explicit in-subagent decision—a no-op or an intended-scope comment—so a gate's reach is never implicit. (`.agent-guild/hooks/`)
- Checkers emit JSON verdicts, self-validate with `validate-verdict.py`, and render the `.md` sibling with `render-verdict.py` — never hand-written Markdown. (`.claude/agents/checker-*.md`)
- Scoped-diff clauses use `.agent-guild/scripts/check-diff-scope.py <allowed>... [--ignore <path>]`, which routes them to checker-deterministic. Don't hand-roll the listing rule as judgment prose; thirteen jobs did, and the phrasing drifted every time.
- A job changing a shared contract (a schema, a template shape, a hook-visible format) carries a clause running every consumer suite, not just the contract's own — `python3 .agent-guild/hooks/test_hooks.py` alongside the contract's tests. The falsify question is "who else parses this shape?" (`.claude/skills/constitution/SKILL.md`)

## Releases

- Two-commit pattern: work commits never touch the version; one mechanical release commit carries the bump (in `scripts/plugin-src/plugin.json`), the generated changelog section, the rebuilt published tree, and the refreshed Codex artifact lock. Kit-payload jobs leave the version untouched — the release is the maintainer ritual at wrap, per `docs/publishing.md`.
- Every release commit gets tagged with a GitHub release, patch bumps included; notes come from `make-changelog.py --notes`, never retyped. A milestone close is just the bump that closes it.
- The changelog is generated, never hand-edited: `--check` fails a bumped-but-sectionless version, `--notes` refuses a noteless release.

## Commit Messages

- Conventional-commit style with a scope: `feat(agents):`, `fix(hooks):`, `refactor(packaging):`, `docs:`, `style(docs):`, `chore:`. (see `git log`)

## Plugin Packaging

- Shared behavior is authored only under `guild-core/`; host frontmatter and manifest metadata live under `scripts/plugin-src/adapters/`. The dogfooded `.claude` wrappers plus published `plugin/` and `plugins/agent-guild/` trees are generated views. Never develop inside a package tree. `scripts/plugin-src/plugin.json` owns shared plugin identity/version, and `scripts/plugin-src/marketplace.json` owns shared marketplace identity/presentation metadata; the builder generates both host marketplace files.
- All twelve workflow bodies are authored under `guild-core/workflows/`. Claude and Codex frontmatter and the thin host-specific `init` suffixes live in adapters; never clone a workflow body or installation guide into an adapter.
- `scripts/plugin-src/install-project.py` is the sole project installer engine. Codex plugin mode omits `--project-skills` and invokes namespaced skills such as `$agent-guild:job`; repo-local Codex adds `--project-skills` and invokes `$job`. Claude invokes `/agent-guild:job`.
- Hook policy remains in the four shared scripts under `.agent-guild/hooks/`; `codex-hook-adapter.py` translates host JSON only. Codex plugin and repo-local hook configs are generated from one inventory. Plugin mode never installs project hooks; repo-local mode owns the packaged hook scripts and only Guild handler commands in `.codex/hooks.json`. Users review and trust Codex hook definitions explicitly through `/hooks`.
- Codex project agents are generated from `guild-core/roles/` plus `scripts/plugin-src/adapters/codex.json`. The installer owns only the packaged roster under `.codex/agents/`, the packaged `.agents/skills/` and `.agent-guild/hooks/` files plus Guild handlers in `.codex/hooks.json` in repo-local mode, and the bounded `<!-- agent-guild:codex:start -->`…`<!-- agent-guild:codex:end -->` section in `AGENTS.md`; it never owns unrelated project configuration, agents or skills, runtime audition results, or global Codex paths.
- Shared courier behavior stays in `guild-core/roles/checker-courier.md`; exact `codex exec` and Claude CLI routes live only in the respective adapter's `agent_body_suffixes`. The Codex route uses `claude-courier.py` and returns a marked, validated outcome for parent persistence—never grant the courier write access to avoid that handoff.
- Use the explicit `--target claude`, `--target codex`, or `--target all` commands for standalone artifacts; use the bare command only to sync the repository's generated state. CI verifies and uploads packages but never commits output. (`docs/building.md`)
- Bump the version in the authored manifest `scripts/plugin-src/plugin.json`, never a generated manifest—rebuilds revert output-only changes, and the one source writes the same version to both targets. (`docs/publishing.md`)
- `/agent-guild:init` never touches `.claude/settings.json`; plugin installs get their gates from the plugin's own `hooks/hooks.json`. Registering them again would double-fire every gate. (`.claude/skills/init/SKILL.md`)

## Prose Voice (docs and comments)

- Em dashes chain directly to the text on both sides—like this—never wrapped in spaces. Don't hard-wrap prose lines; let the display wrap. Headings are Title Case. Comments explain the why, not the what.
