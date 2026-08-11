---
task: CON-audit
tier: orchestrator
retry: 2
checker: auditor
verdict: PASS
checked_at: 2026-07-14T00:00:00Z
---

<!--
CON-audit round 2. Scope per dispatch: offline + structural. The live
"gates fire in a fresh session" run is an explicit non-goal (C-7 / Non-goals)
and is NOT held against the constitution. Re-audited all nine clauses
independently; did not take r0/r1 passes on trust. Deterministic check commands
were exercised mechanically against throwaway fixtures for pass-on-correct /
fail-on-defect. Focus of this round: whether C-9's revised check now rejects its
own failing example (repo .gitignore untouched while the host global excludes
already lists dist/) and passes only when the committed .gitignore decides.
It does — verified empirically against an isolated fixture repo with a global
core.excludesfile containing dist/. See the C-9 row.
-->

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment: parse plugin.json, kebab regex `^[a-z0-9]+(-[a-z0-9]+)*$` on `name`, resolve `hooks` to an existing file under `dist/plugin/` | Rubric is applicable and falsifiable; failing example (`"name": "Agent Guild"` with spaces/caps, or no `hooks` key so no gate loads) is concretely statable. Routing to judgment is sound: resolving "declares hooks pointing at a file that exists" against the plugin-manifest schema is read-and-reason, not a fixed one-liner. Agents/skills presence correctly deferred to C-2, so no overlap. | rubric applicable, falsifiable, sound routing | yes | PASS |
| C-2 | `check-build.sh "diff <(ls .claude/agents) <(ls dist/plugin/agents) && diff <(ls .claude/skills) <(ls dist/plugin/skills)"` | Independently confirmed live inputs: `.claude/agents` = 8 `.md` files, `.claude/skills` = 10 dirs. Ran the mechanics under `bash -c` (as `check-build.sh` execs): identical listings → exit 0; a listing missing entries → exit 1 (`< auditor.md ...`). Process substitution + `&&` bind correctly. Exact-match diff enforces "drops nothing." | exit 0 on complete package, non-zero when a file is missing | matches | PASS |
| C-3 | `check-build.sh "! grep -rq CLAUDE_PROJECT_DIR dist/plugin/hooks/hooks.json && grep -rq CLAUDE_PLUGIN_ROOT dist/plugin/hooks/hooks.json"` | Ran the negation under `bash -c` against fixtures: clean file (only `CLAUDE_PLUGIN_ROOT`) → exit 0; leftover `$CLAUDE_PROJECT_DIR` → exit 1; missing `CLAUDE_PLUGIN_ROOT` → exit 1. Both failure directions caught; negation binds the first pipeline. Complementary to C-6, not contradictory (C-3 governs hook COMMAND paths, C-6 governs STATE resolution). | exit 0 only when the old path is gone AND the plugin var is present | matches | PASS |
| C-4 | judgment: read `dist/plugin/hooks/hooks.json` vs `.claude/settings.json` side by side; every event, matcher, and script target matches | Confirmed live `.claude/settings.json` registers all four gates on the right events: Stop→stop-gate; SubagentStop with the verbatim six-agent matcher `worker-bulk\|worker-standard\|worker-craft\|checker-deterministic\|checker-judgment\|auditor`→subagent-return; PreToolUse `Task\|Agent`→dispatch-guard; PreToolUse `Write\|Edit\|MultiEdit`→orchestrator-write-guard. Clause is anchored and falsifiable (dropped matcher). Correctly judgment: a naive `diff` false-fails because rewired `CLAUDE_PLUGIN_ROOT` commands legitimately differ from live `CLAUDE_PROJECT_DIR` ones; semantic equivalence needs a reader. | rubric applicable, falsifiable, sound routing | yes | PASS |
| C-5 | `check-build.sh "python3 dist/plugin/hooks/test_hooks.py"` | Live `.agent-guild/hooks/test_hooks.py` exists (18.8K) and drives hooks as subprocesses located relative to its own file, so running the packaged copy exercises the packaged `_lib.py` and gate scripts, as the clause claims. Deterministic: exit 0 on packaged copies, non-zero if a fixture breaks or packaged `_lib.py` is absent (which also forces `test_hooks.py` to actually ship). | exit 0 on packaged copies, non-zero if logic/paths broke | matches | PASS |
| C-6 | judgment: read packaged `_lib.py`; confirm `project_dir()` returns `CLAUDE_PROJECT_DIR` when set and the two-dirs-up fallback is removed/corrected/commented | Confirmed live `_lib.py:48-54`: `project_dir()` reads `CLAUDE_PROJECT_DIR` first (line 49) then falls back to the bare `os.path.dirname(...)×3` computation (lines 53-54) — exactly the failing example, so a verbatim copy fails the clause until the plugin hazard is flagged. Correctly judgment (read-and-reason over the whole file). Complementary to C-3, not contradictory. | rubric applicable, falsifiable | yes | PASS |
| C-7 | judgment: read `README.md` against a four-part rubric (local-path install; contract + `.agent-guild/state/` stay per-project, with reason; import line what/why/how-it-got-there; post-install gate verification) | Each sub-check is falsifiable; failing example ("run `/plugin install` and stop") violates the first two. This clause correctly parks the out-of-scope live-gate run as the documented manual portability procedure — consistent with Non-goals rather than a machine-verification demand. severity: major (only non-blocker), appropriate for docs. | rubric applicable, falsifiable | yes | PASS |
| C-8 | `check-build.sh "git diff --quiet HEAD -- .claude .agent-guild/hooks .agent-guild/scripts .agent-guild/templates"` | Clause scopes to tracked files under those four paths, matching `git diff` semantics (exit 0 unchanged, 1 on any tracked-file change). Confirmed repo-root `.gitignore` is NOT in that path list, and `dist/` sits outside it, so the C-9 `.gitignore` edit and building the package do not trip C-8. Complementary to C-9. | exit 0 while live kit untouched, non-zero on any tracked-file change | matches | PASS |
| C-9 | `check-build.sh "git check-ignore -v dist/plugin/.claude-plugin/plugin.json \| grep -qE '(^\|/)\.gitignore:'"` | Empirically verified in an isolated fixture repo whose global `core.excludesfile` lists `dist/` (mirroring the audit host's `~/.config/git/ignore:1`). **Scenario 1 (failing example):** repo `.gitignore` untouched → `git check-ignore -v` reports the GLOBAL source (`.../global_ignore:1:dist/`), `git status` shows nothing, but the C-9 command **exits 1** — it now REJECTS its stated failing example. **Scenario 2:** repo `.gitignore` contains `dist/` → `-v` reports `.gitignore:1:dist/` (the repo file outranks global in git precedence) → C-9 **exits 0** (PASS). **Scenario 3:** repo `.gitignore` present but without a dist entry → only global masks it → **exits 1**. So the check now verifies the committed-`.gitignore` property the clause asserts. Deterministic, quote-safe under `bash -c` (grep is the pipeline's last command; its exit propagates as `PIPESTATUS[0]`). | exit 1 when the repo `.gitignore` lacks a dist entry (even with a global `dist/`); exit 0 only when the committed `.gitignore` ignores the artifact | matches | PASS |
| coverage | spec-requirement → clause mapping | Every in-scope spec section maps: manifest (`spec.md:18`)→C-1; agents/skills (`:19`)→C-2 (`.claude/commands/` is empty, nothing to package there, per the spec itself); hook rewire to `CLAUDE_PLUGIN_ROOT` (`:20`)→C-3; all gates on right events/matchers→C-4; `test_hooks.py` still passes (`:31`)→C-5; state resolves in-project via `project_dir()` (`:22,:33`)→C-6; install story + hybrid + import-line explanation + manual gate verify (`:24-26,:34`)→C-7; non-destructive (`:7-9`)→C-8; "Add `dist/` to `.gitignore`" (`:13`)→C-9. The SMOKE Part A live-gate run (`:32`) is an explicit non-goal, parked as the manual procedure in C-7 — not held against the constitution per dispatch scope. No unmapped in-scope requirement remains. | every in-scope spec requirement mapped to at least one clause | all mapped | PASS |
| contradictions | pairwise clause consistency | No two clauses conflict. C-3 (hook command paths → `CLAUDE_PLUGIN_ROOT`) vs C-6 (state resolution → `CLAUDE_PROJECT_DIR`): complementary. C-8 (tracked files under `.claude`/`.agent-guild/{hooks,scripts,templates}` unchanged) vs C-9 (`.gitignore` edited, `dist/` staged): complementary — repo-root `.gitignore` and `dist/` both sit outside C-8's path list, confirmed on disk. | no clause contradicts another | none found | PASS |
| protected content | manifest presence/parse | "Protected content" is "none" with no manifest declared. Legitimate: the job packages tooling, not authored copy, so there is no verbatim passage to protect and no manifest that must parse. | protected content points at a real manifest that parses, or is legitimately empty | legitimately empty | PASS |

## Diagnosis

<!-- No FAIL this round. -->

The r1 defect is closed. C-9's revised check (`git check-ignore -v ... | grep -qE '(^|/)\.gitignore:'`) now enforces exactly what the clause asserts: the deciding ignore source must be the repository's own committed `.gitignore`. Because the repo `.gitignore` outranks a machine-local global `core.excludesfile` in git's precedence, `-v` reports `.gitignore:` as the source only when the committed file is the reason `dist/` is ignored; when only the global excludes matches, the reported source is the global path (which does not end in `.gitignore:`) and the grep fails with exit 1. Verified against a fixture whose global excludes lists `dist/`:
- repo `.gitignore` untouched (C-9's own failing example) → exit 1 (correctly rejected), even though `git status` hides `dist/` via the global entry;
- repo `.gitignore` containing `dist/` → exit 0 (correctly passes);
- repo `.gitignore` present without a dist entry → exit 1 (correctly rejected).

<!--
Advisory, non-blocking: the grep `(^|/)\.gitignore:` would also match a global
`core.excludesfile` that is itself literally named `.gitignore` (e.g. a user who
set core.excludesfile=~/.gitignore). That is a non-default, pathological config
and is NOT the clause's stated failing example — the realistic global is
~/.config/git/ignore (filename `ignore`, no match) or ~/.gitignore_global
(`.gitignore_global:`, no `.gitignore:` match). The clause rejects its stated
failing example on the actual host, so it remains falsifiable and sound. The r1
diagnosis's grep-the-file alternative would sidestep this edge but is more
sensitive to entry spelling (`dist` vs `/dist` vs `dist/**`); the chosen option
is an acceptable trade. Recorded so the orchestrator can harden later if it ever
targets that config, but it does not warrant a FAIL.

Everything else was re-derived independently, not taken on r0/r1's word. The four
deterministic checks (C-2, C-3, C-5, C-8) plus C-9 are quote-safe under bash -c
and fail-on-defect as written; the four judgment clauses (C-1, C-4, C-6, C-7)
carry rubrics a checker can apply, each anchored to a real live artifact (8
agents / 10 skills; six-agent matcher in settings.json; two-dirs-up fallback at
_lib.py:48-54; the README four-part rubric). Routing is correct: scriptable,
quote-safe checks route to checker-deterministic; read-and-reason clauses route
to checker-judgment (notably C-4, where a plain diff would false-fail on the
rewired CLAUDE_PLUGIN_ROOT commands). Coverage is complete for in-scope
requirements; the live-gate run is a documented non-goal. No two clauses
contradict. Protected content is legitimately empty. The constitution is sound.
-->
