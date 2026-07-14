# Conventions

How we do things here. Stable patterns, not decisions—those live in [[decisionLog]].

## Dispatch Protocol

- Every worker or checker dispatch prompt must carry a `Task-ID: T-NNN` line; the auditor carries `Audit-ID: CON-audit` or `DEC-audit`; auditions carry `Audition-ID: A-NNN`. `dispatch-guard` blocks any guild dispatch missing its id. (`.agent-guild/hooks/dispatch-guard.py`)
- Never pass a `model` override that disagrees with the task's `executor_model`. `dispatch-guard` blocks the mismatch—it's the backstop for a tier bump you recorded but forgot to apply.
- A FAIL comes back to the same worker on the same model with the checker's verbatim diagnosis copied into the task's `## Rework diagnosis`. A tier gets `max_retries` (default 2) tries before escalation.

## State File Naming

- Tasks: `.agent-guild/state/tasks/T-NNN.md`. Notes: `.agent-guild/state/notes/T-NNN.md`.
- Verdicts and disputes embed tier and retry: `T-NNN-<tier>-r<retries>.md` (e.g. `T-007-opus-r1.md`), so a per-tier retry reset never overwrites an earlier tier's file. Audit verdicts use `CON-audit-rN.md` / `DEC-audit-rN.md`. (`.agent-guild/templates/verdict.md`)

## Hooks and Checks

- Hooks are Python 3, stdlib only, and fail loud / fail closed. Never add a dependency. (`.agent-guild/hooks/`)
- Check scripts are dependency-free (Bash or Python) with one exception: `check-a11y.mjs` self-installs its Node deps on first run into a gitignored `node_modules`. (`.agent-guild/scripts/`)
- Checkers ship without an Edit tool—a tool-allowlist backstop so a verifier can't quietly rewrite the artifact it's judging. (`.claude/agents/checker-*.md`)
- Main-session-only gates (chiefly `orchestrator-write-guard`) no-op inside subagents via the `agent_id` CC stamps on subagent hook input (`_lib.in_subagent`); PreToolUse *does* fire in subagents. (`.agent-guild/hooks/`)

## Commit Messages

- Conventional-commit style with a scope: `feat(agents):`, `fix(hooks):`, `refactor(packaging):`, `docs:`, `style(docs):`, `chore:`. (see `git log`)

## Prose Voice (docs and comments)

- Em dashes chain directly to the text on both sides—like this—never wrapped in spaces. Don't hard-wrap prose lines; let the display wrap. Headings are Title Case. Comments explain the why, not the what.
