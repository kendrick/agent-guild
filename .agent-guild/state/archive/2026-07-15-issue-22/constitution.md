# Constitution: /agent-guild:init (Issue #22)

<!-- Spec: .agent-guild/state/spec.md (intake of kendrick/agent-guild#22).
Fully-collapsed interview: the issue plus docs/plugin-publish-plan.md ("Init")
settle every open call — explicit-only skill, payload sourced from
${CLAUDE_PLUGIN_ROOT}/project-template/, "never overwrites without asking"
means the skill asks interactively, and non-plugin invocation errors honestly.
No user questions were outstanding. The deliverable is authored bare in-repo at
.claude/skills/init/SKILL.md; the build script namespaces it when packaging
(include-when-present flips on with zero build-script changes). -->

## Clauses

### C-1: the skill covers the whole per-project half, and only that
- **text**: `.claude/skills/init/SKILL.md` has frontmatter `name: init`, a description that triggers on "finish the guild install here" / "set up this project for the guild", and `disable-model-invocation: true` (explicit-only). Its body instructs all five setup steps, each sourced from `${CLAUDE_PLUGIN_ROOT}/project-template/`: (1) copy `.agent-guild/CLAUDE.md` (the contract) when missing; (2) ensure the root `CLAUDE.md` carries the `@.agent-guild/CLAUDE.md` import, creating the file if absent, appending with a one-line provenance comment if present without it; (3) create `.agent-guild/state/{tasks,verdicts,disputes,notes,log}` with `.gitkeep`s; (4) append `.agent-guild/state/` to `.gitignore` when absent; (5) copy the `scripts/` and `templates/` payload, skipping files that already exist. It must NOT touch `.claude/settings.json` (plugin users get hooks from the plugin, not merged settings) and must end with a summary of what changed plus next steps (`/agent-guild:job` or `/agent-guild:constitution`).
- **check**: checker-judgment: read the SKILL.md against this clause; every step explicit with concrete paths and the payload source named, the settings.json prohibition stated, the summary/next-steps ending present. Fail on any missing step or a settings.json merge instruction.
- **severity**: blocker
- **failing example**: the skill creates the state dirs and the import line but never copies `scripts/`, so the first constitution clause that names `check-build.sh` sends a checker to a path that doesn't exist in the user's repo.

### C-2: idempotent, and it never overwrites without asking
- **text**: Every step states its re-run behavior: an existing contract, import line, state dir, gitignore entry, or payload file is detected and skipped with a report, never silently rewritten. When an existing file differs from the payload version (a drifted contract, an old check script), the skill asks the user before replacing — and when asking isn't possible, it skips and reports, never overwrites. Running init twice in a row must be explicitly safe.
- **check**: checker-judgment: read each step's instructions; confirm a stated exists→skip path, a differs→ask path, and an explicit statement that a second run changes nothing. Fail if any step's re-run behavior is implicit or any path overwrites without an ask.
- **severity**: blocker
- **failing example**: step 5 says "copy the payload into `.agent-guild/`" with no existence check, so a re-run clobbers a user's locally patched `check-a11y.mjs` with the shipped copy.

### C-3: honest outside a plugin context
- **text**: When `${CLAUDE_PLUGIN_ROOT}` is unavailable — the literal string arrived unsubstituted, or the path doesn't exist — the skill stops with an error naming the situation (init is the plugin's install-finisher; without an installed plugin there is no payload to copy) and pointing at the plugin install. It never guesses a payload location, never falls back to copying from a sibling checkout, and writes nothing.
- **check**: checker-judgment: read the failure-path instructions; confirm the unsubstituted-variable and missing-path cases are both handled, the error names the actual problem, and no fallback source is offered. Fail on any guessed path or silent partial setup.
- **severity**: blocker
- **failing example**: run bare in this dev repo, the skill treats the literal string `${CLAUDE_PLUGIN_ROOT}` as a relative directory name, creates it, and "initializes" a project from an empty payload.

### C-4: the build picks init up automatically, namespaced
- **text**: With `.claude/skills/init/` present, an unmodified `scripts/build-plugin.py` includes it in the package (include-when-present working as designed — zero build-script changes in this job), and the packaged copy's invocation references are namespaced (`/agent-guild:job`, `/agent-guild:constitution`, and self-references to `/agent-guild:init`).
- **check**: .agent-guild/scripts/check-build.sh 'out=$(mktemp -d)/p && python3 scripts/build-plugin.py --out "$out" && test -d "$out/skills/init" && grep -q "agent-guild:constitution\|agent-guild:job" "$out/skills/init/SKILL.md" && ! grep -qE "(^|[[:space:]\`])/(job|constitution|init)([[:space:]\`.,)]|$)" "$out/skills/init/SKILL.md" && git diff --quiet HEAD -- scripts/build-plugin.py scripts/plugin-src'
- **severity**: blocker
- **failing example**: the skill's next-steps line ships as bare `/job` in the packaged copy because the author wrote it in a code fence the transform skips, leaving plugin users pointed at a command that doesn't exist under that name.

### C-5: the job adds only the skill; the live kit is untouched
- **text**: The job's entire working-tree footprint is the new `.claude/skills/init/` directory — no other modification, deletion, or untracked addition anywhere in the repo (gitignored paths like `.agent-guild/state/` are exempt by nature). Enforced repo-wide, not by an enumerated list: a list can't see the file it forgot to name, and `git diff` can't see an untracked stray at all.
- **check**: .agent-guild/scripts/check-build.sh 'test -d .claude/skills/init && test -z "$(git status --porcelain -- . ":(exclude).claude/skills/init")"'
- **severity**: blocker
- **failing example**: the worker "improves" the job skill's hand-off wording while in the neighborhood, changing a shipped artifact under a task that never cited it.

### C-6: reads like the house's skills
- **text**: The SKILL.md matches the established skill voice (`job/SKILL.md` and `constitution/SKILL.md` are the references): imperative instructions to the agent, concrete commands and paths, failure paths enumerated, no hand-waving ("handle errors appropriately" fails). Authored bare (`/job`, `/constitution`) so the build's transform namespaces it — hard-coding `agent-guild:` in the source fails, except where the skill *names* its own packaged identity in prose.
- **check**: checker-judgment: read next to the two reference skills; fail on vague steps, missing frontmatter fields, or source-side hard-coded namespacing outside identity prose.
- **severity**: major
- **failing example**: the body says "ensure the project is properly configured" instead of naming the five files and directories the configuration consists of.

## Protected content

- none.

## Non-goals

- The nudge hook (#23), committing the plugin tree (#21), the marketplace file (#24), docs/README/SMOKE (#25), the `/job` flow-through fix (#26), and the namespaced-dispatch gate fix (#27 — load-bearing for #21, not for this skill's authoring).
- Making init useful when run bare in this dev repo; C-3 requires it to refuse honestly instead.
