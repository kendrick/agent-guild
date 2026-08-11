# Constitution: package the kit as a Claude Code plugin (#15)

<!-- Job spec: .agent-guild/state/spec.md. Scope is offline + structural: the
checks below are all runnable by a subagent that has Bash but cannot drive an
interactive `claude` session. The live "gates fire in a fresh session" run is
out of scope here and lives as a documented manual portability procedure (see
C-7 and Non-goals). Package staging root is dist/plugin/ throughout. -->

## Clauses

### C-1: manifest loads and declares the hooks
- **text**: `dist/plugin/.claude-plugin/plugin.json` is valid JSON; its `name` is a non-empty lowercase kebab-case string (`^[a-z0-9]+(-[a-z0-9]+)*$`); and it declares `hooks` pointing at a file that exists under `dist/plugin/`. Hooks have no auto-discovery, so a manifest that omits the `hooks` reference produces a plugin whose gates never register — a kit that looks installed but enforces nothing.
- **check**: checker-judgment: open the manifest; confirm it parses as JSON, `name` matches the kebab-case pattern, and the `hooks` value resolves to an existing file under `dist/plugin/`. Agents and skills may be declared or left to conventional-directory auto-discovery (`agents/`, `skills/`) — either is acceptable; their presence is C-2's job.
- **severity**: blocker
- **failing example**: a `plugin.json` with `"name": "Agent Guild"` (spaces and capitals), or one with no `hooks` key so `hooks/hooks.json` is never loaded and none of the four gates fire.

### C-2: every live component is in the package
- **text**: The package carries the same guild agents and skills as the live `.claude/` kit — the move drops nothing. `dist/plugin/agents/` holds exactly the `.md` files in `.claude/agents/`, and `dist/plugin/skills/` holds exactly the skill directories in `.claude/skills/`.
- **check**: .agent-guild/scripts/check-build.sh "diff <(ls .claude/agents) <(ls dist/plugin/agents) && diff <(ls .claude/skills) <(ls dist/plugin/skills)"
- **severity**: blocker
- **failing example**: `dist/plugin/agents/` is missing `worker-craft.md`, so a job that escalates to the opus worker tier dispatches an agent the plugin never shipped.

### C-3: hook commands point at the plugin, not the old project path
- **text**: Every hook `command` in `dist/plugin/hooks/hooks.json` references `${CLAUDE_PLUGIN_ROOT}` and none still references the pre-package `$CLAUDE_PROJECT_DIR/.agent-guild/hooks/` path. A leftover project path means the packaged gate tries to run a script that isn't there once the kit is out of the repo.
- **check**: .agent-guild/scripts/check-build.sh "! grep -rq CLAUDE_PROJECT_DIR dist/plugin/hooks/hooks.json && grep -rq CLAUDE_PLUGIN_ROOT dist/plugin/hooks/hooks.json"
- **severity**: blocker
- **failing example**: `hooks.json` still reads `python3 "$CLAUDE_PROJECT_DIR/.agent-guild/hooks/stop-gate.py"`, so after install the Stop gate points at a path the user's repo no longer contains.

### C-4: all four gates are registered, on the right events, with matchers intact
- **text**: `dist/plugin/hooks/hooks.json` registers all four gates against the same events and matchers as the live `.claude/settings.json`: `stop-gate` on Stop; `subagent-return` on SubagentStop with the six-agent matcher (`worker-bulk|worker-standard|worker-craft|checker-deterministic|checker-judgment|auditor`); `dispatch-guard` on PreToolUse matching `Task|Agent`; and `orchestrator-write-guard` on PreToolUse matching `Write|Edit|MultiEdit`. Each `command` targets the correct packaged script.
- **check**: checker-judgment: read `dist/plugin/hooks/hooks.json` and `.claude/settings.json` side by side; confirm every event, matcher, and script target matches, with no gate dropped and no matcher silently broadened or narrowed. A dropped SubagentStop matcher, for instance, would let the return gate fire for agents it should ignore or skip ones it must catch.
- **severity**: blocker
- **failing example**: the SubagentStop entry loses its matcher, so `subagent-return` no longer scopes to guild workers and either fires on unrelated subagents or fails to gate a real worker's return.

### C-5: the packaged gate logic still passes its own tests
- **text**: `test_hooks.py`, shipped alongside the packaged hooks, passes in full against the packaged copies — the relocation changed paths, not logic. The test drives each hook against a scratch `CLAUDE_PROJECT_DIR`, so running the packaged copy exercises the packaged `_lib.py` and gate scripts.
- **check**: .agent-guild/scripts/check-build.sh "python3 dist/plugin/hooks/test_hooks.py"
- **severity**: blocker
- **failing example**: a search-and-replace during packaging rewrites a string inside the packaged `_lib.py`, and a fixture that asserts a block message now fails.

### C-6: state resolves to the user's project, never the plugin root
- **text**: The packaged hooks resolve `.agent-guild/state/` under the user's project via `CLAUDE_PROJECT_DIR` (which stays set to the project inside a plugin hook), never under the plugin install directory. The `project_dir()` fallback that computes the repo root as "two directories up from `_lib.py`" is wrong once `_lib.py` ships in a plugin, so the packaged code must not depend on that fallback for correctness, and the hazard must be noted where a maintainer would see it.
- **check**: checker-judgment: read the packaged `_lib.py`; confirm `project_dir()` returns `CLAUDE_PROJECT_DIR` when set and that no state path is hardcoded relative to the plugin/hook location. Confirm the now-incorrect two-dirs-up fallback is either removed, corrected, or carries a comment flagging that it no longer locates the project from inside a plugin.
- **severity**: blocker
- **failing example**: packaged `_lib.py` keeps the bare `os.path.dirname(...×3)` fallback with no guard, so on any invocation where `CLAUDE_PROJECT_DIR` is unset the gates read and write state beside the plugin instead of in the user's repo.

### C-7: the install story documents the hybrid and explains the import line
- **text**: `dist/plugin/README.md` documents installing the plugin from a local path and makes the hybrid explicit: the plugin ships the agents, skills, and hooks, while the `@.agent-guild/CLAUDE.md` orchestrator-contract import and the runtime `.agent-guild/state/` stay in the user's project. It explains the import line to a reader who finds it in their `CLAUDE.md` — what it is, what it does, and that it appeared when they installed the guild — so it never reads as a mystery line. It also gives the manual portability check: how to confirm the four gates fire after install (the offline test plus a fresh-session walk of the gates).
- **check**: checker-judgment: read `dist/plugin/README.md` against this clause. Confirm it covers the local-path install, states plainly that the contract import and `.agent-guild/state/` remain per-project (with the reason: a plugin cannot ship an always-on CLAUDE.md), explains the import line's what/why/how-it-got-there, and documents how to verify the gates post-install. Fail if any of those four is missing or so terse a new user could not follow it.
- **severity**: major
- **failing example**: the README says "run `/plugin install`" and stops — no mention that the contract must stay in the repo, leaving a user with tooling installed and an orchestrator that was never told the contract.

### C-8: the live in-repo kit is untouched (non-destructive)
- **text**: The job adds the package under `dist/plugin/` and does not modify, move, or delete the live tooling this session depends on. The tracked files under `.claude/`, `.agent-guild/hooks/`, `.agent-guild/scripts/`, and `.agent-guild/templates/` are unchanged from `HEAD`.
- **check**: .agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates"
- **severity**: blocker
- **failing example**: a worker "helpfully" rewrites `.claude/settings.json` hook commands to point at the plugin, changing the live registration mid-job and risking the very gates enforcing this run.

### C-9: the build artifact is gitignored by the repo's own .gitignore
- **text**: The spec requires `dist/` be added to `.gitignore` so the staged package never gets committed into the repo it was built alongside. Any path under `dist/plugin/` is ignored by the repository's **own committed `.gitignore`** — not merely by a machine-local global excludes file, which would leave the artifact committable for a fresh clone, a teammate, or CI.
- **check**: .agent-guild/scripts/check-build.sh "git check-ignore -v dist/plugin/.claude-plugin/plugin.json | grep -qE '(^|/)\.gitignore:'"
- **severity**: major
- **failing example**: `.gitignore` is left untouched but the developer's global `core.excludesfile` happens to list `dist/`. A bare `git check-ignore -q` would exit 0 and rubber-stamp it, yet on a fresh clone `dist/plugin/` shows up as untracked and a routine `git add -A` commits the whole staged package. Requiring the repo's own `.gitignore` to be the deciding source rejects this.

## Protected content

<!-- No verbatim-protected passages in this job: it packages tooling, not
authored copy. No protected-passages manifest. -->
- none

## Non-goals

- The repo-wide cutover — deleting or rewriting the live in-repo `.claude/` and `.agent-guild/hooks/` and switching the project onto the plugin. This job proves the package; a human does the cutover later.
- Packaging `.agent-guild/scripts/` (the job check tooling) or `.agent-guild/state/`. Both stay project-side as part of the hybrid, alongside the contract import.
- Publishing to a plugin marketplace.
- An automated live-gate harness. "The four gates fire in a fresh `claude` session with the plugin installed" is inherently interactive and is not machine-verified here; it ships as the manual portability procedure documented per C-7.
- The Codex courier lane (#2–#11) and any cross-vendor concern.
