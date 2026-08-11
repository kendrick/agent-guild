---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: FAIL
checked_at: 2026-07-14T22:20:00Z
---

<!-- CON-audit round 0. No prior CON-audit-r*.md existed. Audits
.agent-guild/state/constitution.md against .agent-guild/state/spec.md (intake of
kendrick/agent-guild#22) and docs/plugin-publish-plan.md "Init". -->

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment-rubric review | Rubric names five concrete steps, each with paths + payload source `${CLAUDE_PLUGIN_ROOT}/project-template/`; states settings.json prohibition; requires summary + next-steps. Traces to spec ("copy the contract if missing, add the `@.agent-guild/CLAUDE.md` import line... create the state directories, gitignore state, and copy the scripts/templates payload") and plan "Init". Falsifiable: failing example (scripts/ never copied) is a statable violation. | concrete, falsifiable, non-contradictory rubric | rubric applies; steps trace to spec/plan | PASS |
| C-2 | judgment-rubric review | Rubric requires each step to state exists→skip, differs→ask, and second-run-changes-nothing. Traces to spec "It never overwrites without asking" and issue "skipping files that already exist". Falsifiable: step-5 clobber example. | applicable idempotency rubric | rubric applies | PASS |
| C-3 | judgment-rubric review | Rubric requires unsubstituted-var and missing-path cases handled, honest error, no fallback source. Derives soundly from plan facts: payload lives only at `${CLAUDE_PLUGIN_ROOT}/project-template/` (build-plugin.py `assemble_project_template`), and the guild's house norm of honest failure (job/SKILL.md "a fetch failure produces an honest error, not a guess"). Falsifiable: literal-`${CLAUDE_PLUGIN_ROOT}`-as-dir example. | applicable rubric, traces to plan/norm | rubric applies | PASS |
| C-4 | `.agent-guild/scripts/check-build.sh '<build+grep+diff>'` | Ran the exact command: `check-build.sh: exit 1`. Build succeeded WITHOUT init (include-when-present, `OPTIONAL_SKILLS=["init"]` in build-plugin.py), then `test -d "$out/skills/init"` failed → the deliverable-missing assertion fires as designed, not a quoting error. Bracket-class quoting survives `bash -c`: simulated GOOD packaged file (namespaced, contains `skills/init/` path + heading + `/agent-guild:init` identity prose) → grep block exit 0 (no false-fail); BAD file with bare `` `/job` `` → exit 1, matched line 4. Positive grep asserts post-build namespacing (checks packaged copy, not source). | fail loud on missing `skills/init` via `test -d`; no false-fail on legit paths/headings; catch bare invocations | exactly that | PASS |
| C-5 | `.agent-guild/scripts/check-build.sh 'git diff --quiet HEAD -- <enumerated> && test -d .claude/skills/init'` | Enumerated paths are all real and currently clean (`git diff --quiet HEAD`→exit 0); `test -d .claude/skills/init`→missing, so the command exits nonzero solely on the missing deliverable, as the task predicted. BUT the check does not enforce the clause's "tracked changes are exactly the new directory / everything else unchanged from HEAD" claim (see Diagnosis). | check enforces "only skills/init changed" | check enforces a partial, bypassable subset | FAIL |
| C-6 | judgment-rubric review | Rubric references job/SKILL.md and constitution/SKILL.md, requires imperative voice, concrete paths, enumerated failure paths, no hand-waving; permits identity-prose namespacing. Falsifiable: "ensure the project is properly configured" example. Severity major. | applicable voice rubric | rubric applies | PASS |

## Coverage of spec

Every spec requirement maps to a clause. Five init steps → C-1 steps (1)-(5): contract copy, `@.agent-guild/CLAUDE.md` import with provenance comment, state dirs, gitignore, payload copy skipping existing. Idempotency / never-overwrite → C-2. Design pointer (docs/plugin-publish-plan.md "Init") → the settled positions all trace: explicit-only (`disable-model-invocation: true`, plan "Init (/agent-guild:init, explicit-only)"), payload from `${CLAUDE_PLUGIN_ROOT}/project-template/` (plan build-script bullet: "assembles plugin/project-template/... the per-project payload init copies"), ask-before-overwrite (spec "never overwrites without asking"), honest-error-outside-plugin (C-3, derived soundly from the plan's payload-source architecture plus the guild's honest-failure norm — a derivation, not verbatim, but not orchestrator invention). The collapsed-interview header is legitimate: no settled position contradicts or outruns the issue/plan. No clause pair contradicts. Protected content is "none" (no manifest to parse).

## Diagnosis

- **file**: `.agent-guild/state/constitution.md:38-40` (clause C-5)
  **clause**: C-5—"Tracked changes are exactly the new `.claude/skills/init/` directory. Everything else ... is unchanged from `HEAD`."
  **expected**: A check that FAILs on any tracked-or-untracked change anywhere in the repo outside `.claude/skills/init/`, so the clause's "exactly / everything else unchanged" promise is actually enforced.
  **actual**: The check is `git diff --quiet HEAD -- <enumerated list> && test -d .claude/skills/init`. It has two independently-confirmed false-green vectors:
    1. **Under-inclusive path list.** The enumerated list omits large tracked areas the clause's "everything else ... unchanged from `HEAD`" language covers: root `CLAUDE.md`, `README.md`, `AGENTS.md`, `SMOKE.md`, `docs/`, `.github/`, `.gitignore`, `.working-memoryrc.example`, `_working-memory/`, the non-guild skills (`.claude/skills/hydrate-*`, `.claude/skills/update-working-memory`), the non-guild agents (`hydrator.md`, `working-memory-synchronizer.md`), and — most pointedly — `.agent-guild/CLAUDE.md`, the orchestrator contract *source* that init itself copies. A worker that "improves" the contract source or edits a doc while authoring the skill passes both C-5 and C-4. Confirmed: `git ls-files .agent-guild/CLAUDE.md` shows it tracked and absent from the C-5 list.
    2. **`git diff --quiet HEAD` ignores untracked additions.** Even within the enumerated dirs, a *new* untracked file is invisible to `git diff`. Confirmed empirically: writing `.claude/agents/__audit_probe.md` left `git diff --quiet HEAD -- .claude/agents` reporting CLEAN. So a stray new file dropped anywhere in the repo passes C-5.
    **Falsifying artifact**: a worker adds one line to the root `CLAUDE.md` (or to `.agent-guild/CLAUDE.md`, or drops a scratch file at the repo root). The clause is violated ("tracked changes are exactly the new directory" is false); C-5 and C-4 both PASS. That is the exact false-green the plan doc's standing lesson warns against.
    **Suggested fix**: enforce exactness repo-wide with `git status --porcelain` (which, unlike `git diff`, lists untracked files) and a pathspec exclude — e.g. `test -d .claude/skills/init && test -z "$(git status --porcelain -- . ':!.claude/skills/init')"`. That FAILs on any modification, deletion, or addition outside `.claude/skills/init/` while still exiting nonzero today because the deliverable is missing.

## Notes for the orchestrator (non-blocking)

- C-3's honest-refuse behavior is a derivation, not a verbatim spec/plan line. It is sound (it follows from the payload living only under `${CLAUDE_PLUGIN_ROOT}` plus the guild's established honest-failure norm), so it holds — flagging only so the provenance is on record.
- C-4's trailing `git diff --quiet HEAD -- scripts/build-plugin.py scripts/plugin-src` shares vector (2) above: it catches *modifications* to `build-plugin.py` (a tracked file — the real risk, and enforced) but would miss a new untracked file added under `scripts/plugin-src/`. Low practical risk; noting for symmetry. C-4 remains PASS.
