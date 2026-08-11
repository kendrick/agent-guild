---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: PASS
checked_at: 2026-07-14T00:00:00Z
---

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | checker-judgment: read `_lib.py` diff + `dispatch-guard.py` for one normalization point, log fidelity, no out-of-scope behavior change | Text is concrete and falsifiable: names a single helper mapping `<ns>:` prefix → bare suffix for the `GUILD_AGENTS`/`DEFAULT_MODEL` lookups, log keeps original string, other hooks untouched. Falsifying artifact: normalization applied inside `_log()` (log shows `worker-standard` for a `agent-guild:worker-standard` dispatch). Rubric a judgment checker can apply. No contradiction with C-2 (both satisfied by one `rsplit(":",1)[-1]` reassignment of `agent`). Routed to checker-judgment — correct for diff-reading/seam judgment. | sound clause | sound clause | PASS |
| C-2 | `check-build.sh '<two-payload pipeline>'` | Ran the exact command against today's buggy code: overall exit 1. Traced halves: namespaced no-id dispatch → `rc1=0`, stderr empty, `grep "has no id line"` rc=1 → the `&&` chain short-circuits at the discriminating first half (NOT on quoting/JSON — payload parsed cleanly, exit 0 = non-guild passthrough, a crash would be exit 2 + HOOK ERROR banner). Namespaced auditor second payload exits 0 today too (also waved through), so the auditor half cannot discriminate — but the blocked-no-id first half does, and it flips 0→2 exactly when the fix lands. JSON escaping survived `bash -c "$*"` rejoin. Check flips FAIL→PASS precisely on the fix. Deterministic → checker-deterministic. | FAIL today, PASS post-fix | FAILs today at first half for the right reason | PASS |
| C-3 | `check-build.sh 'test_hooks.py \| grep -qE "(5[3-9]\|[6-9][0-9]\|[1-9][0-9]{2,}) passed, 0 failed"'` | Suite today: `51 passed, 0 failed` (single line, verified) → check exits 1 (FAIL) as required. Regex unit-tested: rejects `51`/`52 passed, 0 failed`; accepts `53`/`60`/`153 passed, 0 failed`; rejects `53 passed, 2 failed` and `530 passed, 1 failed` — never accepts nonzero-failed. Requires ≥53 (51 baseline + 2 new). Deterministic → checker-deterministic. | FAIL today (51), PASS at ≥53/0 | FAILs today | PASS |
| C-4 | `check-build.sh 'test -z "$(git status --porcelain -- . :(exclude)_lib.py :(exclude)test_hooks.py)"'` | Two-exclude pathspec syntax works on git 2.50.1 (raw rc=0). Verified both directions: out-of-footprint untracked file → non-empty → would FAIL; only the two allowed files modified → empty → PASSES; clean tree → PASSES. Footprint bound is exactly the two hook files. Deterministic → checker-deterministic. | correct footprint assertion | works both directions | PASS |
| C-5 | checker-judgment: read helper comment + fixture labels | Concrete rubric: fail on bare `# strip prefix` or fixture names that don't state the behavior under test; anchors on `in_subagent()`'s comment voice. Falsifying artifact: helper ships with no why-comment. Severity major (documentation, non-blocking to the gate). Routed to checker-judgment — correct. | sound clause | sound clause | PASS |

Coverage of the issue's requirements: normalize-before-lookup is pinned by C-1 (text/implementation) + C-2 (behavior); bare+namespaced fixture coverage by C-3 (+ C-1/C-5 on fixture quality); footprint discipline by C-4; the "land before #21" constraint is honored by scoping the job to `_lib.py` + `test_hooks.py` only (C-4) and excluding the plugin-tree commit as a non-goal. The SubagentStop matcher and the double-registration/stale-dist footgun are correctly scoped out as non-goals. No two clauses contradict. No protected content to resolve.

## Notes (non-blocking; do not gate)

These do not undermine soundness — each affected requirement is enforced by a partner clause — but the orchestrator should know:

- **C-2's failing example is caught by C-1, not C-2.** A helper that strips only the literal `agent-guild:` prefix (defeated by a plugin rename) would still PASS C-2's check, which only exercises the `agent-guild:` namespace. Rename-robustness lives in C-1's text ("or any `<ns>:` prefix ... to its bare suffix"), enforced by the judgment read. Answer to the posed question: C-2's *text* does not itself require rename-robust normalization; C-1's does, and the two are consistent (complementary, not contradictory). The failing example is pedagogically attached to C-2 but discriminated by C-1.

- **C-3's failing example is caught by C-2, not C-3.** C-3's count check cannot confirm that the specific *legal namespaced worker* fixture exists — a worker could reach 53/0 with other passing fixtures. But the underlying bug it describes (normalization reaches membership yet a legal namespaced dispatch is rejected, or `DEFAULT_MODEL[<namespaced>]` KeyErrors) is caught behaviorally by C-2's second payload: a namespaced auditor that isn't fully normalized falls past `agent == "auditor"` to the tid-None block (exit 2) or KeyErrors (exit 2), failing C-2's `test $? -eq 0`. The namespaced-worker-legal path proper (executor/model-match comparisons) is enforced by C-1's single-normalization-point judgment (one `agent = normalize(agent)` reassignment makes all downstream comparisons see the bare name). So the "ships green" scenario does not actually ship green once the clause set runs together.
