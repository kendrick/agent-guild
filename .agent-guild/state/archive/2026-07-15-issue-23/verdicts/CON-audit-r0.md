---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: PASS
checked_at: 2026-07-14T23:15:00Z
---

<!--
CON-audit round 0 for the SessionStart nudge constitution (Issue #23).
No prior CON-audit-r*.md existed. Deterministic checks (C-2..C-5) were run
empirically today against the missing deliverable to confirm they fail for the
right reason, and C-4 was re-run with a stub nudge present to confirm it passes
on a correct build. Judgment clauses (C-1, C-6) were audited for a concrete,
falsifiable rubric.
-->

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | checker-judgment rubric: read script, confirm predicate (both partial-init triggers, both silence conditions), one line, `/agent-guild:init` named, `_lib.run()` wrap, exit 0 | Rubric names five specific, readable properties; falsifying artifact given (nudges before requiring `.agent-guild/` to exist → nags unrelated repos). Matches `_lib` API: `project_dir()`/`state_path()` exist. | concrete + falsifiable | concrete + falsifiable | PASS |
| C-2 | check-build.sh four-scenario battery | Ran today: short-circuits at first `out=$(... python3 "$h")` with `can't open file`, `exit 2` — missing-script failure, not quoting. `&&` chain carries substitution exit status, so `test -z "$out"` is never reached vacuously. | fail today (missing script), non-vacuous | exit 2, non-vacuous | PASS |
| C-3 | check-build.sh regex floor on `test_hooks.py` summary | `grep -qE "(5[8-9]\|[6-9][0-9]\|[1-9][0-9]{2,}) passed, 0 failed"`: rejects `55`,`57`; accepts `58`,`59`,`60`,`100`,`158`; rejects `1 failed`,`10 failed`. Suite prints `55 passed, 0 failed` today; floor 58 = 55+3. | reject 55/57, accept 58+, reject nonzero-failed | exactly that | PASS |
| C-4 | check-build.sh build-integration | Today: build runs OK, `test -f .../session-nudge.py` fails → `exit 1` (not quoting). With a stub nudge present: `nudge registration ok`, `exit 0`. `build-plugin.py:208-220` emits `matcher:"startup"` + `python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/session-nudge.py` — byte-for-byte what C-4 asserts. | fail today at `test -f`; pass on correct build | exit 1 today, exit 0 with nudge | PASS |
| C-5 | check-build.sh two-exclude porcelain | Ran today: `exit 1` at the `test -f session-nudge.py` gate. Excludes exactly the two files the job may touch. Auditor left tree clean (`git status --porcelain` empty). | fail today only at `test -f` | exit 1 | PASS |
| C-6 | checker-judgment rubric: read next to `stop-gate.py`/`subagent-return.py` | Rubric names three concrete failure conditions (reimplemented project-dir resolution, missing asymmetry comment, opaque fixture labels); falsifying artifact given (own `os.getcwd()` logic). `_lib.project_dir()`/`state_path()` exist to reuse. | concrete + falsifiable | concrete + falsifiable | PASS |

## Cross-cutting checks

- **Concrete check methods**: every clause names either a runnable `.agent-guild/scripts/check-build.sh` invocation (C-2..C-5) or a checker-judgment rubric enumerating specific readable properties (C-1, C-6). None vague or absent.
- **Falsifiability**: each clause carries a `failing example` naming a specific artifact that would violate it, and each is genuinely violable.
- **No contradictions**: C-4 (a `SessionStart`/`startup` registration must appear) and C-5 (nothing modified but `session-nudge.py` and `test_hooks.py`; `build-plugin.py` unmodified) are mutually consistent *only because* `scripts/build-plugin.py` already carries the #20 include-when-present logic (`OPTIONAL_HOOKS = ["session-nudge.py"]` at line 64; the `if "session-nudge.py" in shipped_hooks` append at 208-220). Verified present, so landing the source alone flips the registration on with zero build change — the two clauses reinforce rather than conflict. C-1/C-2/C-3 agree on the predicate (partial-init nudge, zero-evidence + fully-init silence) with no divergence.
- **Coverage of issue #23 requirements**: SessionStart + `startup` matcher → C-4; one stdout line, exit 0 → C-1 (one line) + C-2 (`wc -l == 1`, exit 0 gated by the `&&` chain across all four scenarios); partial-init predicate → C-1/C-2/C-3; zero-evidence silence → C-1/C-2 (scenario 1) / C-3 fixture; fixture-style tests → C-3. Every requirement maps to at least one clause.
- **Protected content**: `none` — nothing to point at a manifest.

## Notes on soundness of the deterministic constructions

- **C-2 non-vacuity (the key trap)**: `out=$(CLAUDE_PROJECT_DIR=... python3 "$h" </dev/null)` takes the substituted command's exit status as the assignment's status, so a crashing or missing script fails the assignment and the `&&` chain short-circuits *before* `test -z "$out"`. Empirically confirmed: the battery stopped at the first scenario with exit 2 rather than silently passing on empty output. Exit-0 is therefore enforced for the two nudging scenarios too, since their capturing assignment gates the subsequent `grep`. The `wc -l` assertion is exact: `$(...)` strips trailing newlines and `printf "%s\n"` re-adds exactly one, so a one-line nudge counts as 1 and a two-line nudge as 2.
- **C-2 scenario isolation**: tree 2 (`mkdir .agent-guild` only) isolates the missing-state-dirs trigger; tree 3 (all five state subdirs, no root `CLAUDE.md`) isolates the missing-import trigger, then writing `@.agent-guild/CLAUDE.md` and re-running asserts silence — cleanly separating the two partial-init branches from the fully-initialized case.
- **C-4 registration shape**: `ss[0]` is unambiguously the nudge entry because the live `.claude/settings.json` carries no `SessionStart` block and C-5 forbids adding one, so `setdefault("SessionStart", []).append(...)` leaves the nudge at index 0. The asserted `matcher`, `${CLAUDE_PLUGIN_ROOT}`, and `session-nudge.py` all match the build output verbatim — no risk of failing a correct deliverable.
