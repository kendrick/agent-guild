---
name: init
description: Finishes a guild plugin install inside a project by copying the per-project payload (the orchestrator contract, check-script tooling, and templates) that a plugin can't ship as always-on config. Explicit-only — the model never invokes this on its own; the user runs it by name. Use when the user says "finish the guild install here" or "set up this project for the guild".
disable-model-invocation: true
---

# Finish the guild install

`/agent-guild:init` is the plugin's install-finisher. A plugin ships the guild's agents, skills, and hooks, but it cannot ship an always-on `CLAUDE.md`, and `@`-imports don't expand environment variables — so the orchestrator contract and the runtime state have to live in the user's own repo. The plugin carries that per-project payload at `${CLAUDE_PLUGIN_ROOT}/project-template/` (built by `scripts/build-plugin.py`): `.agent-guild/CLAUDE.md` (the contract, already namespaced), `scripts/` (the check tooling constitutions cite by path), and `templates/` (task/verdict/dispute templates). This skill copies that payload into the project and wires the import.

Its governing property is **idempotent, never silently destructive**: every step below states what happens when its target already exists, and running `/agent-guild:init` again — at any point — is safe. A second run reports the same five things as already in place and writes nothing new.

## 0. Confirm the payload actually exists

Resolve `${CLAUDE_PLUGIN_ROOT}/project-template/` before touching anything else. Two ways this fails, and both are a hard stop, not a fallback:

- **The variable never substituted.** If the path you're working with is still the literal string `${CLAUDE_PLUGIN_ROOT}/project-template/`, you're not running inside an installed plugin. Stop and tell the user exactly that: init is the plugin's install-finisher, and without an installed plugin there's no payload to copy. Point them at `/plugin marketplace add <marketplace>` and `/plugin install agent-guild`.
- **The path doesn't exist.** If `${CLAUDE_PLUGIN_ROOT}` did substitute but `${CLAUDE_PLUGIN_ROOT}/project-template/` isn't a real directory on disk, stop and name that exact path in the error. Same pointer to the plugin install.

In both cases: never guess another payload location — not a sibling checkout, not a hardcoded repo path — and never run any of steps 1–5 partially. If step 0 fails, nothing else in this skill runs, and nothing is written.

## 1. The contract

Target: `.agent-guild/CLAUDE.md`. Source: `${CLAUDE_PLUGIN_ROOT}/project-template/.agent-guild/CLAUDE.md`.

- Missing → copy it.
- Present and identical (`diff -q` the two) → report it's already in place. Leave it alone.
- Present and different → ask the user before replacing it; a drifted contract may carry local edits worth keeping. If there's no way to ask (no interactive channel available), skip it and report the mismatch instead of overwriting.

## 2. The import line

Target: the project's root `CLAUDE.md`. It must contain the line `@.agent-guild/CLAUDE.md`.

- File missing → create it with a one-line comment noting the guild was installed, then the import line:
  ```
  <!-- Added when the agent-guild plugin was installed -->
  @.agent-guild/CLAUDE.md
  ```
- File exists, line absent → append both lines (comment, then import) to the end of the file.
- File exists, line already present → report it's already wired. Don't duplicate it.

## 3. State directories

Run:
```
mkdir -p .agent-guild/state/{tasks,verdicts,disputes,notes,log}
touch .agent-guild/state/{tasks,verdicts,disputes,notes,log}/.gitkeep
```
`mkdir -p` and re-touching an existing file are both already no-ops on a second run, so this step needs no separate existence check — report the five directories as created or already present, whichever is true per directory.

## 4. Gitignore

Target: the repo's `.gitignore`. It must have a line that covers `.agent-guild/state/`.

- File missing → create it with `.agent-guild/state/` as its content.
- File exists, no line already covers `.agent-guild/state/` → append `.agent-guild/state/`.
- File exists, a line already covers it (an exact match, or a broader pattern like `.agent-guild/` that already excludes it) → report, don't add a duplicate line.

## 5. The payload

Copy `scripts/` and `templates/` from `${CLAUDE_PLUGIN_ROOT}/project-template/.agent-guild/` into `.agent-guild/`, file by file:

```
for tree in scripts templates; do
  src="${CLAUDE_PLUGIN_ROOT}/project-template/.agent-guild/$tree"
  for f in $(cd "$src" && find . -type f); do
    dest=".agent-guild/$tree/$f"
    if [ -e "$dest" ]; then
      echo "skip (exists): $dest"
    else
      mkdir -p "$(dirname "$dest")"
      cp "$src/$f" "$dest"
      echo "copied: $dest"
    fi
  done
done
```

A file that already exists is skipped, not overwritten — a user's local patches (a hand-edited check script, a customized template) survive re-init. Report the copied/skipped count per directory, not just a total.

## Never touch `.claude/settings.json`

Plugin users get the four hook gates from the plugin's own `hooks/hooks.json`, registered at install time. Do not create, edit, or merge anything into `.claude/settings.json` at any point in this skill — doing so would register every gate twice and double-fire on every tool call.

## Summary and hand-off

End every run — including a second run that changed nothing — with a short summary: which of steps 1–5 created something, which reported already-in-place, and which were skipped pending a user decision (step 1 or 2's differs-case). Then name the next step:

- Run `/agent-guild:job <issue|file|url>` to intake existing work into a spec.
- Run `/agent-guild:constitution` to author a spec fresh through the interview.

Running `/agent-guild:init` again at any point is safe: every target above is checked before it's written, so a second pass reports five "already in place" lines and writes nothing new.
