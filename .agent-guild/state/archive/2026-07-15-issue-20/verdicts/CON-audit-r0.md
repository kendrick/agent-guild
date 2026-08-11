---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: PASS
checked_at: 2026-07-14T00:00:00Z
---

<!--
CON-audit round 0. No prior CON-audit-r*.md exists in the live verdicts/ dir
(only .gitkeep; earlier rounds are under state/archive/). Constitution audited
against spec.md (intake of kendrick/agent-guild#20). Deliverables do not exist
yet, so deterministic checks were verified as well-formed and fail-loud, not run
to green.
-->

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment rubric (stdlib imports, exec bit, `--help`, manifest props) | rubric is concrete and falsifiable; refs a real deliverable path `scripts/plugin-src/plugin.json`; failing example (imports `yaml`) is statable | applicable rubric, judgment routing | rubric names specific pass/fail conditions; correctly routed to checker-judgment (adequacy of `--help` and manifest shape need reading) | PASS |
| C-2 | `check-build.sh '...'` (cmp agents, test -d skills, cmp 6 hooks, test -f/-d template + manifest, `! grep` excludes) | dry-run via check-build.sh → `exit 2`, `can't open file '.../scripts/build-plugin.py'` — fails loud on MISSING SCRIPT, not a shell error. Six named agents + five named skills + six hook files all present in repo today; exclude patterns (`hydrator\|working-memory`, `hydrate\|update-working-memory`) match the excluded surface and none of the guild subset | fail-loud pre-build; assertions correct; named components match repo | confirmed on all counts | PASS |
| C-3 | `check-build.sh '...'` (json parse + rewire/leak/dangling/gate asserts) | as-written dry-run → `exit 2` on missing script (loud). Verbatim command run against a stub build that emits a valid hooks.json → `hooks.json ok`, `exit 0`: single-quote wrapping survives `CMD="$*"` + `bash -c`, the embedded multi-line `python -c` with `\"`-escapes parses, and `OUT="$out"` env handoff resolves. Negative case (injected `$CLAUDE_PROJECT_DIR`) → assert fires (`caught leak`), so the check discriminates | parses and fails loud on missing script; asserts live | confirmed | PASS |
| C-4 | judgment rubric (grep spot-check for `/agent-guild:` invocations + read for path/heading overreach + `git status` on sources) | concrete deterministic spot-check plus judgment for mangled-path overreach; failing example (rewrite corrupts `skills/decompose/` path) statable; scoped to contract + skill bodies only, which is consistent with C-2 checking skills by `test -d` (not `cmp`) and the contract by `test -f` | applicable rubric, judgment routing, no contradiction with C-2 | consistent; correctly routed | PASS |
| C-5 | `check-build.sh '... ; rc=$?; rm -rf plugin; exit $rc'` | traced the `&&`/`!` chain with a configurable stub: correct behavior → `rc=0`; early build failure (`BUILD_FAIL`) → `rc=5`; broken `--check` that returns 0 on drift → `rc=1`. `rc=$?` faithfully captures the last-executed command of the chain (final status on full run, failing-step status on short-circuit); cleanup `rm -rf plugin` does not clobber rc. As-written on missing script → fails loud | rc reports pass/fail faithfully; fails loud | confirmed, no misreport | PASS |
| C-6 | `check-build.sh 'python3 build-plugin.py --out "$out" && claude plugin validate --strict "$out"'` | `claude` resolves to real binary `/opt/homebrew/bin/claude` in plain `bash -c` (not just the interactive shell function); `claude plugin validate --strict <path>` exists and fails loud on a bad path (`exit 1`). As-written on missing script → `exit 2` (loud). Isolation reasoning (marketplace at repo root per #24, no shadowing) matches spec | validator present; fails loud; isolation covered | confirmed | PASS |
| C-7 | `check-build.sh '... && git diff --quiet HEAD -- <sources>'` | as-written → `exit 2` on missing script (loud). Read-only source list matches the actual build inputs (`.claude/settings.json`, agents, skills, `.agent-guild/hooks|scripts|templates`); check harness writes only under `state/log/` and builds to a temp `$out`, so no false-positive diff. New surface lands in the pre-existing repo-root `scripts/`, consistent with C-1's "no other new top-level surface" | fails loud; read-only list sound; no self-inflicted diff | confirmed | PASS |
| C-8 | judgment rubric (read next to `check-provenance.py` + `new-task.py`) | both reference files exist (`.agent-guild/scripts/check-provenance.py`, `new-task.py`); rubric names concrete fail conditions (uncommented transform map, monolithic main, subjectless errors); failing example statable; severity major (not blocker) is appropriate for style | applicable rubric, real refs, judgment routing | confirmed | PASS |

## Coverage of in-scope spec duties

Every in-scope duty in the issue maps to at least one clause:

- Copy guild agents/skills/hooks into the plugin → C-2.
- Generate `hooks/hooks.json` from `.claude/settings.json`, rewrite paths to `"${CLAUDE_PLUGIN_ROOT}"/hooks/`, no dangling refs → C-3.
- Assemble `project-template/` (contract, check scripts, task templates) → C-2.
- Bare-to-namespaced invocation map on plugin-bound content only → C-4.
- `--check` semantics: rebuild-to-temp, diff against `plugin/`, hard-fail on absence and missing `claude` CLI → C-5; `validate --strict` with manifest isolation → C-6 (and exercised on-match inside C-5).

Read-only-sources and the exact-declared-surface guarantee are covered by C-7; house code style by C-8. No spec duty is left unclaused.

## Observations (non-blocking, no clause failed)

Two clauses assert slightly more than their deterministic checks exercise. Neither threatens the plausible failure surface, so neither is a FAIL — recording them so a future refinement can tighten the checks if desired:

- **C-3 event binding.** The clause requires each gate on its correct event (Stop→stop-gate, SubagentStop→subagent-return, PreToolUse→dispatch-guard + orchestrator-write-guard), but the check only asserts each script name appears *somewhere* in the joined commands (`assert g in joined`), not under the right event key. A path-rewrite build preserves event structure by construction, and the real risks the clause names (dangling refs, unrewired paths, `CLAUDE_PROJECT_DIR` leak) are all verified — so this is tolerable.
- **C-5 missing-CLI path.** The clause requires `--check` to hard-fail when `claude` is absent from PATH, but the deterministic check runs on a machine where `claude` is present and does not simulate its absence (e.g. via a scrubbed `PATH`). The drift and `plugin/`-absent hard-fails are exercised; the missing-CLI branch is asserted in text and left to the build's own logic plus C-8's read. Falsifiable and sound; just not exercised end-to-end here.

No contradictions found between clauses. C-2 (agents byte-identical, skills/contract by existence only) and C-4 (namespacing rewrites skills + contract, never agents) are mutually consistent by design. C-1's "no other new top-level surface" and C-7's "exactly `scripts/build-plugin.py` and `scripts/plugin-src/`" agree, and land inside the already-existing repo-root `scripts/`.
