---
task: CON-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-10T23:28:58Z
---

Audit of `.agent-guild/state/constitution.md` against `.agent-guild/state/spec.md` (the plan for #117, `source: file`).

## Per-clause results

| clause | severity | result | description | evidence |
| ------ | -------- | ------ | ----------- | -------- |
| C-1 | major | FAIL | check is a green-suite exit code over tests this same job authors; the clause's own failing example passes it | constitution.md:9 |
| C-2 | major | FAIL | same; `job` in `required` ships undetected if the paired test is never written | constitution.md:15 |
| C-3 | blocker | PASS | command verified runnable and green from repo root; `--check`-only is correct for a checker | verified, exit 0 |
| C-4 | major | FAIL | same green-suite problem; check cannot distinguish "scenario passes" from "scenario untested" | constitution.md:27 |
| C-5 | minor | PASS | rubric applies in one read; failing example is the file's literal current text | guild-core/workflows/retrospective/SKILL.md:24 |
| C-6 | blocker | FAIL | prescribed derivation is ambiguous for 8 of 18 rows, undefined for row 17, and names a validator that does not exist | constitution.md:39 |
| C-7 | major | PASS | command well-formed against `check-diff-scope.py`'s interface; verified `OK: 0 path(s) in scope` | verified, exit 0 |
| C-8 | minor | PASS | one-line rubric, distinct failing example (`val.strip("'\"")`) | constitution.md:51 |
| C-9 | minor | PASS | rubric applicable; see advisory A5 on check ordering | constitution.md:57 |
| coverage | — | FAIL | three spec bars carried by no clause: `docs/vendor-ledger.md` content, the working-memory updates, the reporting obligation | see D3–D5 |
| non-goals | — | PASS | no clause constrains out-of-scope work; C-6's "no other field altered" positively enforces them. See advisory A1 | constitution.md:65-73 |
| protected content | — | PASS | "none" is correct; the one verbatim-fidelity requirement is genuinely C-6's, not a manifest's | constitution.md:63 |

## Diagnosis

### C-6 (blocker): the check cannot be executed as written

Three separate defects. This clause governs the job's only irreversible artifact, so it needs to be right.

**(a) The tier segment is not a discriminator for the rows where attribution actually turns.** The check says to re-derive "from its artifact path's tier segment against that project's archive directories." Rows 0–6 and rows 7–10 all carry tier `judgment`, and the identical verdict stem lives in two archives:

```
T-001-judgment-r0-codex.json     held by: issue-17 issue-32
T-002-judgment-r0-codex.json     held by: issue-17 issue-32
T-003-judgment-r0-codex.json     held by: issue-17 issue-32
T-004-judgment-r0-codex.json     held by: issue-17 issue-32
T-005-judgment-r0-codex.json     held by: issue-17
T-007-judgment-r0-codex.json     held by: issue-17
```

So the prescribed procedure resolves rows 2, 3, 6 and 11–16 cleanly and returns two candidate archives for rows 0, 1, 4, 5, 7, 8, 9, 10 — 8 of 18, and precisely the rows straddling the #17/#32 boundary the backfill exists to draw. A checker told to distrust the table and follow this procedure would either stall or pick one arbitrarily.

The spec knows the real discriminator and C-6 dropped it: the #32 archive's own `log/vendor-calls.jsonl` holds rows 7–10 byte-identically (4 rows, verified), and the #17 archive holds all seven of T-001…T-007 `judgment`. Change the check to name that: match each row against the candidate archive's own ledger first, and fall back to stem-uniqueness only where no ledger copy exists.

**(b) Row 17 has no artifact path at all.** Its `artifacts` array is empty (verified — the `exit_code: 143` timeout). There is no tier segment, so the procedure produces nothing for it, yet the clause text assigns it `kendrick/skills#27` and the clause's own failing example makes mis-attributing row 17 a violation. The spec has a procedure for this row (append order in a chronological write log, plus the rows it sits among); it never made it into the check. Write it in, or the checker is left to invent one for the single row most likely to be attributed wrong.

**(c) "run every row through the amended validator" names no runnable thing.** There is no vendor-call validator in `.agent-guild/scripts/`. `ledger-append.py` validates only a line it assembles from CLI flags immediately before appending — it has no validate-a-file mode, and its docstring is explicit that it "never reads, rewrites, or repairs existing ledger content." A checker following this instruction has to write its own validator, which is the re-derivation the clause was trying to avoid. Name a concrete invocation over `.agent-guild/schemas/vendor-call.schema.json` for all 18 lines. Note this is load-bearing rather than ceremonial: the schema sets `"additionalProperties": false`, so if `job` is not added to `properties`, every backfilled row becomes invalid.

### C-1, C-2, C-4 (major): the check cannot see its own failing example

All three route to the same command, `check-build.sh "python3 .agent-guild/scripts/test_ledger_append.py"`. That command's exit code carries exactly one fact: the test suite is green. But the suite is an artifact **this job writes**, so a green exit is evidence only if the required cases exist — and nothing checks that they do.

Take C-2's stated failing example, `job` added to `required`. A worker who does that and does not write the pre-change-row case ships a suite that passes: exit 0, clause PASS, failing example undetected. Same shape for C-1 (a no-flag crossing that writes no `job`) and C-4 (two rows sharing `task_id: T-001`). Each clause's text asserts the coverage exists — C-4 says outright "`test_ledger_append.py` covers exactly that scenario" — but the check method verifies the suite runs, not that the assertion is true. A clause whose named failing example survives its own check is not falsifiable in practice.

The routing makes this worse rather than better. These are deterministic clauses, so they go to checker-deterministic, which reads exit codes. The suite does print per-case labels (`ok   <case name>`), but no clause tells a checker to read them, and the tier assigned to read them isn't the one dispatched.

Two remedies, either acceptable:

- **C-2 should not depend on the job's tests at all.** Its requirement is a property of a file on disk. Check it directly — one assertion over `vendor-call.schema.json` that `job` is in `properties` and not in `required` — and the clause becomes independent of whatever the worker chose to test.
- **C-1 and C-4 should require the cases to exist, not just to pass.** Name the exact case labels the clause depends on and have the check confirm they appear in the run's output, so a missing test fails the clause instead of passing it silently.

### D3 (coverage): nothing requires `docs/vendor-ledger.md` to document the field

The spec's Files list makes the doc a deliverable — "the field and how it's derived." No clause carries that bar. C-7 merely permits the path in the diff; C-9 audits the doc's prose *if prose exists*. A worker who never opens the file passes all nine clauses. The gap has a natural home: the doc's `## Fields` section is where `job` belongs, and the derivation precedence plus "absence means unattributed" is what a reader needs from it.

### D4 (coverage): nothing requires the working-memory updates

The spec's Wrap-up names two specific edits: `dataContracts.md` describes the ledger and needs the field, and `conventions.md` gets the archive-includes-`log/` rule. Both files exist. C-7 allows `_working-memory/` in the diff and nothing requires either edit — the same vacuous pass as D3.

The `conventions.md` half deserves its own emphasis. C-5 fixes one skill's step 3; the convention is what stops the next skill from repeating it. Dropping it silently is the exact failure mode #117 exists to close.

### D5 (coverage): "both get reported" is enforced nowhere

The constitution's own Non-goals say of the `/Users/karnett/` artifact paths and the fractional-seconds `started_at`: "Both get reported, neither gets fixed here." The spec adds the duplication finding and requires closing #117 with the attribution table.

The "not fixed" half is enforced — C-6's "no other field on any row is altered" catches it. The "reported" half has no clause at all. So a non-goal quietly carries a deliverable that no check will ever look for. That leaves a required fact living in prose someone has to remember, which is the #113 lesson C-1's own clause text cites as the reason `job` is derived rather than passed. Give the reporting obligation a clause, or stop asserting it in a non-goal.

## Advisory (not FAIL drivers)

- **A1 — the Non-goals expand past the spec.** The spec has no Non-goals section; its out-of-scope statements sit inline in Backfill and Wrap-up. Five of the constitution's eight track those faithfully. Three appear nowhere in the spec: the courier's local-time stamp, #116, and #99. They narrow scope rather than constrain work, so this is not over-reach in the harmful direction, but they came from the issue while the constitution names the spec as its source. Cite them or drop them.
- **A2 — C-3's text names three suites, its command runs two.** `test_ledger_append.py` is named in the clause text and absent from the check. C-1/C-2/C-4 run it, so the bar isn't lost across the constitution, but C-3 can report PASS with its own stated consumer set red. Fold the third command in.
- **A3 — keep C-3's `--check`-only form.** The spec's Verification runs `build-plugin.py && build-plugin.py --check`; C-3 runs only `--check`. That is the correct adaptation, not a transcription slip: regenerating would make the checker edit the tree it is judging. Verified green from the repo root, exit 0.
- **A4 — the two deterministic checks don't collide.** `check-build.sh` writes its log to `.agent-guild/state/log/`, which `check-diff-scope.py` always permits, so C-3's check cannot trip C-7's. Verified: `OK: 0 path(s) in scope`.
- **A5 — C-9 audits commit messages, which may not exist when the checker runs.** A checker dispatched before the commit lands can only return `blocked`. Order it in the task, not the clause.
- **A6 — C-1's fixture.** The spec calls for a fixture `spec.md`. If the new test writes it inside the repo rather than a temp dir, C-7's allowlist won't cover it. The existing suite uses temp dirs; keep it that way.
- **A7 — C-4's failing example is the weakest of the nine.** Read-time derivation from "whichever `spec.md` happens to be on disk" is a design nobody would plausibly build. It is still a distinct artifact and the named scenario would catch it, so it clears the falsifiability bar — but a sharper example would be two rows written by two real jobs where the second run's spec has already replaced the first's.

All nine failing examples describe distinct artifacts rather than restating their clauses. Falsifiability of the *examples* is sound throughout; the failures above are in the checks' ability to detect them.
