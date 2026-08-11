---
task: CON-audit
tier: orchestrator
retry: 1
checker: auditor
verdict: FAIL
checked_at: 2026-07-14T00:00:00Z
---

<!--
CON-audit round 1. Scope per dispatch: offline + structural. The live
"gates fire in a fresh session" run is an explicit non-goal (C-7 / Non-goals)
and is NOT held against the constitution. Re-audited every clause independently;
did not assume r0's passes were correct. Deterministic check commands were
exercised mechanically against throwaway fixtures to confirm pass-on-correct /
fail-on-defect. The r0 coverage gap (dist/ gitignore) is now mapped to a new
clause C-9 — but C-9's named check does NOT verify what the clause asserts.
See Diagnosis.
-->

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment: parse plugin.json, kebab regex on `name`, resolve `hooks` reference to an existing file under `dist/plugin/` | Rubric is applicable and falsifiable; failing example (`"name": "Agent Guild"`, or no `hooks` key) is concretely statable. Judgment routing is sound — resolving "declares hooks pointing at a file that exists" against the plugin-manifest schema is read-and-reason, not a one-liner. Agents/skills presence correctly deferred to C-2, no overlap. | rubric applicable, falsifiable, sound routing | yes | PASS |
| C-2 | `check-build.sh "diff <(ls .claude/agents) <(ls dist/plugin/agents) && diff <(ls .claude/skills) <(ls dist/plugin/skills)"` | Independently confirmed the live inputs: `.claude/agents` = 8 `.md` files (no non-`.md` entries), `.claude/skills` = 10 dirs. Process substitution + `&&` run because `check-build.sh` execs `bash -c`. Identical listings → exit 0; a listing missing one entry → exit 1. Exact-match diff enforces "drops nothing." | exit 0 on complete package, non-zero when a file is missing | matches | PASS |
| C-3 | `check-build.sh "! grep -rq CLAUDE_PROJECT_DIR dist/plugin/hooks/hooks.json && grep -rq CLAUDE_PLUGIN_ROOT dist/plugin/hooks/hooks.json"` | Negation binds the first pipeline under `bash -c`; both failure directions are caught (leftover `$CLAUDE_PROJECT_DIR` → exit 1; missing `CLAUDE_PLUGIN_ROOT` → exit 1; clean → exit 0). Complementary to C-6, not contradictory: C-3 governs hook COMMAND paths, C-6 governs STATE resolution. | exit 0 only when old path is gone AND plugin var is present | matches | PASS |
| C-4 | judgment: read `dist/plugin/hooks/hooks.json` vs `.claude/settings.json` side by side; every event, matcher, script target matches | Confirmed the six-agent SubagentStop matcher is present verbatim in live `.claude/settings.json` (`worker-bulk\|worker-standard\|worker-craft\|checker-deterministic\|checker-judgment\|auditor`), so the clause is anchored and falsifiable (dropped matcher). Correctly judgment: a naive `diff` false-fails because the rewired `CLAUDE_PLUGIN_ROOT` commands legitimately differ from the live `CLAUDE_PROJECT_DIR` ones; semantic equivalence needs a reader. | rubric applicable, falsifiable, sound routing | yes | PASS |
| C-5 | `check-build.sh "python3 dist/plugin/hooks/test_hooks.py"` | Live `test_hooks.py` exists and drives hooks as subprocesses located relative to its own file, so running the packaged copy exercises the packaged `_lib.py` and gate scripts, as the clause claims. Deterministic: exit 0 on packaged copies, non-zero if a fixture breaks or packaged `_lib.py` is absent (which also forces `test_hooks.py` to actually ship). | exit 0 on packaged copies, non-zero if logic/paths broke | matches | PASS |
| C-6 | judgment: read packaged `_lib.py`; confirm `project_dir()` returns `CLAUDE_PROJECT_DIR` when set and the two-dirs-up fallback is removed/corrected/commented | Confirmed live `_lib.py:48-54`: `project_dir()` reads `CLAUDE_PROJECT_DIR` first (line 49) then falls back to the bare `os.path.dirname(...)×3` two-dirs-up computation (lines 53-54) — exactly the failing example, so a verbatim copy fails the clause until the plugin hazard is flagged. Correctly judgment (read-and-reason over the whole file). Complementary to C-3. | rubric applicable, falsifiable | yes | PASS |
| C-7 | judgment: read `README.md` against a four-part rubric (local-path install; contract + `.agent-guild/state/` stay per-project, with reason; import line what/why/how-it-got-there; post-install gate verification) | Each sub-check is falsifiable; failing example ("run `/plugin install` and stop") violates the first two. This clause correctly parks the out-of-scope live-gate run as a documented manual portability procedure, consistent with Non-goals rather than a machine-verification demand. severity: major, appropriate for docs. | rubric applicable, falsifiable | yes | PASS |
| C-8 | `check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates"` | Clause scopes to tracked files under those four paths, matching `git diff` semantics (exit 0 unchanged, 1 on any tracked-file change). Repo-root `.gitignore` is NOT in the path list, so the C-9 edit to `.gitignore` does not trip C-8 — the two are complementary, not contradictory. `dist/` sits outside the path list, so building the package does not violate C-8. | exit 0 while live kit untouched, non-zero on any tracked-file change | matches | PASS |
| C-9 | `check-build.sh "git check-ignore -q dist/plugin/.claude-plugin/plugin.json"` | `git check-ignore` consults ALL ignore sources (repo `.gitignore`, `.git/info/exclude`, AND the user's global `core.excludesfile`/`~/.config/git/ignore`), then exits 0 if ANY of them matches. The audit host's `~/.config/git/ignore:1` contains `dist/`, so the command returns exit 0 with the repo `.gitignore` left completely untouched — it does NOT distinguish an un-ignored (by the committed `.gitignore`) `dist/` from an ignored one. Ran C-9's own failing example (staged `dist/plugin/` + `.gitignore` untouched): the check returned exit 0, i.e. it PASSES the exact artifact the clause says must FAIL. See Diagnosis. | exit 1 when `.gitignore` is untouched (failing example), exit 0 only when the committed `.gitignore` ignores `dist/` | check returns exit 0 in both cases; cannot reject the failing example | FAIL |
| coverage | spec-requirement → clause mapping | The r0 gap is closed as a MAPPING: "Add `dist/` to `.gitignore`" (`spec.md:13`) now maps to clause C-9. Every other spec section maps: manifest→C-1, agents/skills→C-2, hook rewire→C-3/C-4, gate logic→C-5, state resolution→C-6, install story + hybrid + manual gate check→C-7, non-destructive→C-8. The SMOKE Part A live-gate run is an explicit non-goal, parked in C-7. No unmapped in-scope requirement remains. (The mapping is complete; C-9's *check method* is nonetheless defective — that is the C-9 row above, a separate axis.) | every in-scope spec requirement mapped to at least one clause | all mapped | PASS |
| contradictions | pairwise clause consistency | No two clauses conflict. C-3 (hook command paths → `CLAUDE_PLUGIN_ROOT`) vs C-6 (state resolution → `CLAUDE_PROJECT_DIR`): complementary. C-8 (tracked files under `.claude`/`.agent-guild/{hooks,scripts,templates}` unchanged) vs C-9 (`.gitignore` edited to ignore `dist/`): complementary — `.gitignore` and `dist/` both sit outside C-8's path list. | no clause contradicts another | none found | PASS |

## Diagnosis

- **file**: `.agent-guild/state/constitution.md:61` (clause C-9, the `check` line)
  **clause**: C-9 — "The spec requires `dist/` be added to `.gitignore` so the staged package never gets committed into the repo it was built alongside. Any path under `dist/plugin/` is git-ignored." with **check** `check-build.sh "git check-ignore -q dist/plugin/.claude-plugin/plugin.json"` and **failing example** "`.gitignore` is left untouched, so `dist/plugin/` shows up as untracked in `git status`."
  **expected**: A deterministic check that verifies the spec requirement at `spec.md:13` — that the `dist/` entry lives in the repo's own committed `.gitignore`, the file that travels with a clone to other developers and CI. The check must reject the clause's stated failing example (repo `.gitignore` untouched) with a non-zero exit, and pass only when the committed `.gitignore` ignores `dist/`.
  **actual**: `git check-ignore` reports the ignore status computed across *all* ignore sources, not just the repo `.gitignore`. It exits 0 if the path is ignored by the repo `.gitignore`, `.git/info/exclude`, OR the user's global `core.excludesfile` (default `~/.config/git/ignore`). On the audit host `git check-ignore -v dist/plugin/.claude-plugin/plugin.json` reports `/Users/k.arnett/.config/git/ignore:1:dist/` — a machine-local, non-committed global entry. Empirically: with a staged `dist/plugin/.claude-plugin/plugin.json` present and the repo-root `.gitignore` left completely untouched (C-9's own failing example), the check returns **exit 0**, and `git status` does NOT list `dist/` because the global ignore already masks it. So the check both (a) fails to reject its stated failing example and (b) can be satisfied by ambient per-machine config that does the spec no good — a fresh clone, CI runner, or teammate without that global entry would still see `dist/plugin/` as committable, exactly the harm the requirement guards against. A `checker-deterministic` running this command would rubber-stamp a package where the worker never edited `.gitignore`, re-opening the r0 gap under a passing check. The check is concrete but verifies the wrong property, so C-9 is not falsifiable as written (its failing example is not rejected) and the routing to a script that "distinguishes ignored from un-ignored" does not hold.
  **fix direction (orchestrator revises; do not treat as consent to edit here)**: Make the check assert the entry lives in the repo's own `.gitignore`, so a global/system ignore cannot mask a missing repo entry. Two verified options, both of which correctly FAIL on "`.gitignore` untouched" and PASS on "`dist/` added to the committed `.gitignore`" even when the host's global ignore also contains `dist/`:
    - Assert the *deciding* ignore source is the repo `.gitignore`: `check-build.sh "git check-ignore -v dist/plugin/.claude-plugin/plugin.json | grep -qE '(^|/)\.gitignore:'"` — the repo `.gitignore` outranks the global excludes in git's precedence, so when it contains `dist/` it is the reported source (exit 0); when only the global matches, the source is the global path and the grep fails (exit 1).
    - Or grep the tracked file directly: `check-build.sh "grep -qE '(^|/)dist/?[[:space:]]*\$' .gitignore"` (assert the pattern is literally present in the committed `.gitignore`; note this is more sensitive to entry spelling such as `dist`, `/dist`, or `dist/**`).
  Then re-submit for CON-audit r2.

<!--
Everything except C-9 is sound and was re-derived independently, not taken on
r0's word. C-2/C-3/C-5/C-8 are deterministic, quote-safe, and fail-on-defect as
written (C-3's negation binds under bash -c; C-8 scopes to tracked files and
excludes both dist/ and repo-root .gitignore, so it neither contradicts C-9 nor
the build). C-1/C-4/C-6/C-7 carry rubrics a checker can apply, each with a
statable failing artifact anchored in a real live file (six-agent matcher in
settings.json; two-dirs-up fallback at _lib.py:48-54). Routing is correct.
Coverage is now complete as a mapping. The single, load-bearing defect is C-9's
check method, which consults machine-local global ignore config and therefore
cannot enforce the committed-.gitignore requirement the clause exists to guard.
-->
