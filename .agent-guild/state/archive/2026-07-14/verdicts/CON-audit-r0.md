---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: FAIL
checked_at: 2026-07-14T00:00:00Z
---

<!--
CON-audit round 0. Scope per dispatch: offline + structural. The live
"gates fire in a fresh session" run is an explicit non-goal (C-7 / Non-goals)
and is NOT held against the constitution here. Deterministic check commands
were exercised mechanically against throwaway fixtures to confirm they pass on
a correct package and fail on the named failing example.
-->

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment: parse plugin.json, kebab regex on `name`, resolve `hooks` reference to an existing file | Rubric is applicable and falsifiable; failing example (`"name": "Agent Guild"`, or no `hooks` key) is concretely statable. Routing to judgment is sound: resolving "declares hooks pointing at a file that exists" requires interpreting the plugin-manifest schema, not a fixed one-liner. Presence of agents/skills is correctly deferred to C-2, no overlap. | a checker can apply the rubric and name a violating artifact | can | PASS |
| C-2 | `check-build.sh "diff <(ls .claude/agents) <(ls dist/plugin/agents) && diff <(ls .claude/skills) <(ls dist/plugin/skills)"` | Ran the mechanics through `check-build.sh`: identical listings → `exit 0`; a listing missing one file → `exit 1` (`< y.md`). Process substitution and `&&` work because the arg runs under `bash -c`. `.claude/agents` = 8 `.md` files, `.claude/skills` = 10 dirs; exact-match diff enforces "drops nothing." | exit 0 on complete package, non-zero when a file is missing | matches | PASS |
| C-3 | `check-build.sh "! grep -rq CLAUDE_PROJECT_DIR dist/plugin/hooks/hooks.json && grep -rq CLAUDE_PLUGIN_ROOT dist/plugin/hooks/hooks.json"` | Ran through `check-build.sh`: clean file (only `CLAUDE_PLUGIN_ROOT`) → `exit 0`; file with leftover `$CLAUDE_PROJECT_DIR` → `exit 1`; file missing `CLAUDE_PLUGIN_ROOT` → `exit 1`. Negation binds the first pipeline correctly under `bash -c`; both failure directions caught. | exit 0 only when the old path is gone AND the plugin var is present | matches | PASS |
| C-4 | judgment: read `hooks.json` vs `.claude/settings.json` side by side; every event, matcher, script target matches | Correctly judgment, not deterministic: the commands legitimately differ (`CLAUDE_PLUGIN_ROOT` vs `CLAUDE_PROJECT_DIR`), so a naive `diff` would false-fail — semantic equivalence needs a reader. The six-agent SubagentStop matcher is quoted verbatim and confirmed present in live `settings.json`. Failing example (dropped matcher) is falsifiable. | rubric applicable, falsifiable, sound routing | yes | PASS |
| C-5 | `check-build.sh "python3 dist/plugin/hooks/test_hooks.py"` | Copied `hooks/*.py` into a fake `dist/plugin/hooks/` and ran it: `49 passed, 0 failed`, `check-build exit 0`. `test_hooks.py` locates hooks via `os.path.dirname(os.path.abspath(__file__))` and runs them as subprocesses, so the packaged copy exercises the packaged `_lib.py` — as the clause claims. Deleting packaged `_lib.py` → `exit 1`, so the check also forces `test_hooks.py` to actually ship. | exit 0 on packaged copies, non-zero if logic/paths broke | matches | PASS |
| C-6 | judgment: read packaged `_lib.py`; confirm `project_dir()` returns `CLAUDE_PROJECT_DIR` when set and the two-dirs-up fallback is removed/corrected/commented | Correctly judgment (read-and-reason over the whole file). Falsifiable: the live `_lib.py:52-55` still carries the bare `os.path.dirname(...)×3` fallback with a comment asserting it is correct — exactly the failing example — so a verbatim copy fails the clause until the plugin hazard is flagged. Distinct from C-3: C-3 governs hook COMMAND paths (`CLAUDE_PLUGIN_ROOT`), C-6 governs STATE resolution (`CLAUDE_PROJECT_DIR`); complementary, not contradictory. | rubric applicable, falsifiable | yes | PASS |
| C-7 | judgment: read `README.md` against a four-part rubric (local-path install; contract + `.agent-guild/state/` stay per-project, with reason; import line what/why/how-it-got-there; post-install gate verification) | Each of the four sub-checks is falsifiable; failing example ("run `/plugin install` and stop") violates the first two. This clause is where the out-of-scope live-gate run is correctly parked as a documented manual procedure — consistent with the Non-goals, not a machine-verification demand. severity: major (only non-blocker), appropriate for docs. | rubric applicable, falsifiable | yes | PASS |
| C-8 | `check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates"` | Ran `git diff --quiet HEAD -- <paths>` on the live tree → `exit 0` (unchanged); a tracked-file edit would return 1. Clause text scopes to "tracked files," matching `git diff` semantics. `dist/` is not under these paths, so building the package does not contradict C-8. Failing example (rewrite `.claude/settings.json`) is caught. | exit 0 while live kit untouched, non-zero on any tracked-file change | matches | PASS |
| coverage | spec-requirement → clause mapping | The spec's explicit build requirement "Add `dist/` to `.gitignore`" (`spec.md:13`) is guarded by no clause. See Diagnosis. | every spec requirement mapped to a clause | one requirement unmapped | FAIL |

## Diagnosis

- **file**: `.agent-guild/state/constitution.md` (whole document; gap sits between C-8 and Non-goals)
  **clause**: coverage — the spec requirement at `.agent-guild/state/spec.md:13`, "The package is staged at `dist/plugin/` [...]. **Add `dist/` to `.gitignore`.**"
  **expected**: Every requirement the spec states as in-scope maps to at least one falsifiable clause (per the dispatch's charge to "flag any spec requirement no clause guards"). "Add `dist/` to `.gitignore`" is an in-scope build requirement — it is not among the Non-goals, which disclaim only the cutover, packaging `scripts/`/`state/`, the marketplace, the live-gate harness, and the Codex lane. It is trivially and deterministically checkable, e.g. `check-build.sh "git check-ignore -q dist/plugin/.claude-plugin/plugin.json"` (exit 0 = ignored) or a grep for a `dist/`-matching line in `.gitignore`.
  **actual**: No clause references `.gitignore` at all. C-8 governs the opposite concern (tracked files under `.claude/` and `.agent-guild/{hooks,scripts,templates}` must stay unchanged) and its path list excludes repo-root `.gitignore`, so it neither requires nor forbids the ignore entry. Because the guild requires every task to cite a constitution clause, this gap is load-bearing: with no clause to cite, `/decompose` cannot produce a compliant task for the `.gitignore` step, so the requirement is liable to be silently dropped — the build artifact then becomes committable and can pollute the repo the non-destructive constraint is trying to protect. Close it by adding one deterministic clause (routed to `checker-deterministic` via `check-build.sh`) that asserts `dist/` is gitignored, then re-submit for CON-audit r1.

<!--
Everything else is sound. All four deterministic check commands (C-2, C-3, C-5,
C-8) were exercised against fixtures and pass-on-correct / fail-on-defect as
written; all four judgment clauses (C-1, C-4, C-6, C-7) carry rubrics a checker
can actually apply and each has a statable failing artifact. Routing is correct:
scriptable, quote-safe checks are deterministic; the read-and-reason clauses are
judgment — notably C-4, where a plain diff would false-fail because the rewired
CLAUDE_PLUGIN_ROOT commands legitimately differ from the live CLAUDE_PROJECT_DIR
ones. No two clauses contradict (C-3 governs hook command paths; C-6 governs
state resolution — complementary). Protected content is legitimately "none" with
no manifest to parse. The one defect is the coverage gap above.
-->
