---
task: CON-audit
tier: orchestrator
retry: 1
checker: auditor
verdict: PASS
checked_at: 2026-07-14T22:35:00Z
---

<!-- CON-audit round 1. r0 (.agent-guild/state/verdicts/CON-audit-r0.md) FAILed
C-5 for two false-green vectors. C-5's text + check were rewritten to repo-wide
git-status-porcelain enforcement with a pathspec exclude. Re-audited in full,
independently; verification concentrated on the rewritten C-5. Every claim below
was re-derived on this machine (git 2.50.1, working tree clean at audit time). -->

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment-rubric review | Rubric names five concrete steps, each with a path + payload source `${CLAUDE_PLUGIN_ROOT}/project-template/`; states the settings.json prohibition; requires summary + next-steps. Traces to spec ("copy the contract if missing, add the `@.agent-guild/CLAUDE.md` import line... create the state directories, gitignore state, and copy the scripts/templates payload") and plan "Init". Falsifiable: scripts/-never-copied example is a statable violation. | concrete, falsifiable, non-contradictory rubric | rubric applies; steps trace to spec/plan | PASS |
| C-2 | judgment-rubric review | Rubric requires each step to state exists→skip, differs→ask, second-run-noop. Traces to spec "It never overwrites without asking" + issue "skipping files that already exist". C-1's "skipping files that already exist" is the exists→skip default; C-2 specializes it with a differs→ask escalation — a refinement, not a contradiction (the spec itself carries both sentences). Falsifiable: step-5 clobber example. | applicable, non-contradictory idempotency rubric | rubric applies; coherent with C-1 | PASS |
| C-3 | judgment-rubric review | Rubric requires unsubstituted-var and missing-path cases handled, honest error, no fallback source, writes nothing. Sound derivation: payload lives only at `${CLAUDE_PLUGIN_ROOT}/project-template/` (build-plugin.py) plus the guild's honest-failure norm (job/SKILL.md). Falsifiable: literal-`${CLAUDE_PLUGIN_ROOT}`-as-dir example. | applicable rubric, traces to plan/norm | rubric applies | PASS |
| C-4 | `.agent-guild/scripts/check-build.sh '<build+grep+diff>'` | Re-ran build: `python3 scripts/build-plugin.py --out "$out"` → exit 0 into a mktemp dir (`.../tmp.*/p` with `agents hooks project-template skills`). Porcelain lines before=0, after=0 → build does not touch the working tree, so it is invisible to C-5's porcelain and the two clauses cannot collide. r0 already verified the `test -d`/grep/`git diff` logic; unchanged. | build to mktemp only; tree stays clean; no C-5 collision | exactly that | PASS |
| C-5 | `.agent-guild/scripts/check-build.sh 'test -d .claude/skills/init && test -z "$(git status --porcelain -- . ":(exclude).claude/skills/init")"'` | Full battery below. Today (init absent, tree clean): check-build.sh exit 1, short-circuited on `test -d` (test-d exit 1; the porcelain half exits 0 empty — not a quoting fault). Pathspec `:(exclude).claude/skills/init` accepted by git 2.50.1 (exit 0). With a scratch deliverable present: clean tree → exit 0; tracked-file edit outside exclude (README.md, and specifically the contract source `.agent-guild/CLAUDE.md`) → exit 1; untracked stray outside exclude → exit 1 (porcelain `??`); tracked-file deletion outside exclude → exit 1 (porcelain ` D`); extra file *inside* `.claude/skills/init/` → exit 0 (deliverable content allowed). Gitignored `.agent-guild/state/` and `dist/` confirmed `git check-ignore`-ignored → never leak into porcelain. Quoting (single-quote outer arg, double quotes + `$()` inner) survives `bash -c "$CMD"` end-to-end. Tree restored clean (0 porcelain lines). | text↔check agree; both r0 false-green vectors caught; pathspec valid on this git; no ignored-path leak; quoting survives | exactly that | PASS |
| C-6 | judgment-rubric review | Rubric references job/SKILL.md and constitution/SKILL.md, requires imperative voice, concrete paths, enumerated failure paths, no hand-waving; permits identity-prose namespacing. Falsifiable: "ensure the project is properly configured" example. Severity major. | applicable voice rubric | rubric applies | PASS |

## Coverage of spec

Unchanged from r0 and re-confirmed. Five init steps → C-1 steps (1)-(5): contract copy, `@.agent-guild/CLAUDE.md` import with provenance comment, state dirs, gitignore, payload copy skipping existing. Idempotency / never-overwrite → C-2. Explicit-only, payload source, and honest-error-outside-plugin trace to plan "Init" + build-plugin.py + the guild's honest-failure norm. No clause pair contradicts (C-1/C-2 refine, don't collide; C-4/C-5 operate on disjoint surfaces — mktemp vs. working tree). Protected content is "none" (no manifest to parse).

## C-5 text/check agreement (the rewrite)

- **text**: "The job's entire working-tree footprint is the new `.claude/skills/init/` directory — no other modification, deletion, or untracked addition anywhere in the repo (gitignored paths like `.agent-guild/state/` are exempt by nature). Enforced repo-wide, not by an enumerated list."
- **check delivers exactly that**: `test -d .claude/skills/init` asserts the deliverable exists; `git status --porcelain -- . ":(exclude).claude/skills/init"` is repo-wide (`.`), lists modifications, deletions **and** untracked additions (unlike r0's `git diff --quiet`, empirically confirmed by the `??` stray vector), auto-omits gitignored paths, and excludes only the deliverable directory. `test -z` requires that set empty. The two r0 false-green vectors — the omitted-path list (fixed by `.` + single exclude, verified against the contract source `.agent-guild/CLAUDE.md`) and `git diff`'s untracked-blindness (fixed by porcelain) — are both closed.

## Notes for the orchestrator (non-blocking)

- The r0 note on C-4's trailing `git diff --quiet HEAD -- scripts/build-plugin.py scripts/plugin-src` still stands: it catches modifications to those tracked paths (the real risk) but would miss a brand-new untracked file dropped under `scripts/plugin-src/`. C-5's repo-wide porcelain now backstops exactly that gap for any working-tree run, so the residual exposure is nil in practice. C-4 remains PASS; no action required.
