# Constitution: GitHub-Issue Intake (Job 1)

<!-- Spec: .agent-guild/state/spec.md. Quality bars come from the user's plan-mode
directives, not a fresh interview. Verification scope is offline: every check is
runnable by a subagent with Bash. The live DoD run (/job <issue#> into a collapsed
constitution) is the orchestrator's post-job demonstration, not a clause. Lesson
carried from the last job: deterministic checks assert the SOURCE of a property,
never ambient machine state. -->

## Clauses

### C-1: /job covers every intake form and only writes the spec
- **text**: `.claude/skills/job/SKILL.md` instructs handling of all five argument situations — bare number/`#N` (current repo), `owner/repo#N`, GitHub issue URL, existing local file path, other URL — plus the no-argument case, which explains the two paths instead of guessing. The skill's only file output is `.agent-guild/state/spec.md`, structured as the provenance header first, then the spec content; for issues, the content is the issue title plus the full body with the issue's own markdown preserved (no summarizing, no stripping). On a `gh` failure (missing CLI, unauthenticated, issue not found) it reports the real error and writes nothing; it never fabricates spec content.
- **check**: checker-judgment: read the SKILL.md against this clause; confirm each of the six situations has explicit instructions, the write target is exactly `.agent-guild/state/spec.md`, the output ordering (header, then content) and the title-plus-verbatim-body rule for issues are stated, and the failure path forbids fabrication. Fail if any form is missing, the content contract is absent, or the skill invents content on error.
- **severity**: blocker
- **failing example**: a SKILL.md that handles `#N` and file paths but is silent on `owner/repo#N`, so a cross-repo issue silently falls through to URL fetching without `gh` auth.

### C-2: the skill's provenance header matches the validator's contract (user-directed)
- **text**: The header format the skill instructs writing is exactly the contract `check-provenance.py` enforces: YAML frontmatter with flat keys `source` (`github-issue|file|url`), `ref`, `fetched_at` (ISO-8601 UTC), plus `issue` and `title` required when `source: github-issue`. No drift between what the skill writes and what the validator accepts.
- **check**: checker-judgment: read `.claude/skills/job/SKILL.md` and `.agent-guild/scripts/check-provenance.py` side by side; confirm every key, allowed value, and requiredness rule matches in both directions (nothing the skill writes would fail the validator; nothing the validator requires is absent from the skill's instructions).
- **severity**: blocker
- **failing example**: the skill writes `fetched-at:` (hyphen) while the validator requires `fetched_at:` (underscore), so every freshly generated spec fails validation.

### C-3: the validator proves itself with one command (user-directed)
- **text**: `.agent-guild/scripts/check-provenance.py --self-test` runs an embedded fixture battery and exits 0 only if all fixtures behave: a fully valid github-issue header passes; missing `fetched_at` fails; a malformed timestamp fails; `source: github-issue` without `issue` fails; `--issue N` mismatch fails. For every failing fixture, the self-test also asserts the validator emitted a diagnostic line naming the first violated rule — a bare nonzero exit with no message is itself a self-test failure. The validator is python3 stdlib only.
- **check**: .agent-guild/scripts/check-build.sh "python3 .agent-guild/scripts/check-provenance.py --self-test"
- **severity**: blocker
- **failing example**: the self-test passes a header whose `fetched_at` is `yesterday`, because the validator only checks key presence, not that the timestamp parses.

### C-4: constitution skill collapses when a spec exists
- **text**: `.claude/skills/constitution/SKILL.md` gains a pre-interview step: when `.agent-guild/state/spec.md` exists, derive candidate quality bars from its content and confirm/adjust them with the user rather than running the full question bank; never re-ask what the spec already answers. When no spec exists, the full interview path is unchanged.
- **check**: checker-judgment: read the edited SKILL.md; confirm the spec-exists branch derives-and-confirms rather than interviews, explicitly preserves the no-spec interview path, and forbids re-asking answered questions. Fail if the collapse is a vague suggestion rather than an instruction.
- **severity**: blocker
- **failing example**: the edit adds "you may skim spec.md if present" but leaves the interview mandatory, so `/job` output still triggers the full question bank.

### C-5: the project_dir fallback validates its candidate
- **text**: In `.agent-guild/hooks/_lib.py`, when `CLAUDE_PROJECT_DIR` is unset, `project_dir()` returns the two-dirs-up candidate only if that candidate contains a `.agent-guild/` directory; otherwise it raises `RuntimeError` with a message naming the failure. The primary `CLAUDE_PROJECT_DIR` path is unchanged. `test_hooks.py` gains coverage for both fallback branches (valid candidate accepted; invalid candidate raises).
- **check**: checker-judgment: read `_lib.py`'s `project_dir()` and the new test(s); confirm the guard, the raise, the unchanged primary path, and that the tests actually exercise both branches (e.g. by pointing the module at a scratch tree without `.agent-guild/`).
- **severity**: blocker
- **failing example**: the guard checks `os.path.exists(candidate)` (the parent dir always exists) instead of `candidate/.agent-guild`, so the fallback still silently misresolves from a plugin install.

### C-6: the full hook suite stays green
- **text**: `python3 .agent-guild/hooks/test_hooks.py` reports 0 failed after all changes, including the new fallback tests. The pass count is at least 50 (49 existing + at least one new).
- **check**: .agent-guild/scripts/check-build.sh "python3 .agent-guild/hooks/test_hooks.py 2>&1 | grep -qE '[5-9][0-9]+ passed, 0 failed|[1-9][0-9]{2,} passed, 0 failed'"
- **severity**: blocker
- **failing example**: the hardening breaks the no-`CLAUDE_PROJECT_DIR` code path an existing fixture relies on, and the suite reports 48 passed, 1 failed.

### C-7: the live enforcement kit outside the declared scope is untouched
- **text**: This job modifies only its declared surface. The gate registrations and gate scripts stay unchanged from `HEAD`: `.claude/settings.json`, `.agent-guild/hooks/dispatch-guard.py`, `orchestrator-write-guard.py`, `stop-gate.py`, `subagent-return.py`, and everything under `.claude/agents/`. (`_lib.py` and `test_hooks.py` are in scope by deliverable 4; `.claude/skills/job/` and `.claude/skills/constitution/SKILL.md` by deliverables 1 and 3.)
- **check**: .agent-guild/scripts/check-build.sh "git diff --quiet HEAD -- .claude/settings.json .claude/agents .agent-guild/hooks/dispatch-guard.py .agent-guild/hooks/orchestrator-write-guard.py .agent-guild/hooks/stop-gate.py .agent-guild/hooks/subagent-return.py"
- **severity**: blocker
- **failing example**: a worker "tidies" the SubagentStop matcher in `.claude/settings.json` while adding the fallback tests, changing live gate behavior mid-job.

### C-8: new skill prose holds the house style
- **text**: The `/job` skill and the constitution-skill edit read like the repo's existing skills (`constitution/SKILL.md` is the reference): imperative instructions to the agent, concrete paths and commands, a frontmatter `name` + `description` that triggers correctly, self-contained enough to act on cold. Stdlib/dependency-free instructions only.
- **check**: checker-judgment: read the new/edited SKILL.md files next to `constitution/SKILL.md`; fail on hand-waving ("handle errors appropriately"), missing frontmatter, instructions that require tools the session may not have (other than `gh`, which the skill itself must handle the absence of), or a description that wouldn't trigger on "start a job from issue 15".
- **severity**: major
- **failing example**: `job/SKILL.md` has `description: Job intake.` — too vague for the Skill tool to ever select it from "kick off a job from issue #15".

## Protected content

- none — this job packages behavior, not authored copy.

## Non-goals

- The live DoD demonstration (`/job <issue#>` → collapsed constitution) is run by the orchestrator after tasks complete; it is a demonstration, not a clause a subagent checks.
- Everything deferred to Job 2: build script, `plugin/` dir, init, nudge, manifests, marketplace, docs/SMOKE/README changes, namespacing.
- The humanizer loop for SKILL.md files (agent-facing instructions; clarity is checked by C-8 instead).
