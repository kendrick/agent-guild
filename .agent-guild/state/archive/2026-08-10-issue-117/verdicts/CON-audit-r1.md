---
task: CON-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-10T23:38:23Z
---

Round 1 audit of the revised `.agent-guild/state/constitution.md` against `.agent-guild/state/spec.md` (the plan for #117, `source: file`). Prior round: `.agent-guild/state/verdicts/CON-audit-r0.md`.

Two of r0's three defect clusters close cleanly. C-6's derivation procedure is now executable — I ran it against the real archives and it resolves all 18 rows. C-1, C-2, and C-4 each now have a check that trips its own failing example. The document still fails on C-6's validator and on coverage, and the C-1/C-2 repair traded one gap for a smaller one.

## Per-clause results

| clause | severity | result | description | evidence |
| ------ | -------- | ------ | ----------- | -------- |
| C-1 | major | PASS | both failing examples trip the rubric; see coverage row for what the rewrite dropped | constitution.md:13 |
| C-2 | major | PASS | rubric settles all three schema facts and the null path; over-priced at opus, see A2 | constitution.md:19 |
| C-3 | blocker | PASS | three-command chain verified runnable and green from repo root, exit 0; `&&` masking is real but non-fatal, see A1 | verified, exit 0 |
| C-4 | major | PASS | unchanged bar plus an explicit "open the file and confirm a case covers it"; the model C-1 should follow | constitution.md:31 |
| C-5 | minor | PASS | rubric applies in one read; failing example is still the file's literal current text | guild-core/workflows/retrospective/SKILL.md:26 |
| C-6 | blocker | FAIL | derivation now sound and verified; the `--validate` deliverable is unfunded, unfalsifiable, and its invocation is unpinned | constitution.md:43 |
| C-7 | major | PASS | allowlist covers every path the job touches, including `openQuestions.md` via `_working-memory/`; verified `OK: 0 path(s) in scope` | verified, exit 0 |
| C-8 | minor | PASS | one-line rubric, distinct failing example; the half that matters is a grep, see A2 | constitution.md:55 |
| C-9 | minor | PASS | rubric applicable; prose list is incomplete (see D2) and ordering caveat A3 carries over from r0 | constitution.md:61 |
| C-10 | major | PASS | closes r0's D3, D4, and D5; four named files, each fact enumerated | constitution.md:67 |
| coverage | — | FAIL | four of the spec's five named test cases, the close comment, the branch/commit shape, and two prose deliverables carry no clause | see D2 |
| non-goals | — | PASS | no clause constrains out-of-scope work; the paths/`started_at` bullet now cross-references C-10, which is r0's D5 closed properly | constitution.md:81 |
| protected content | — | PASS | "none" is still correct | constitution.md:73 |

## Diagnosis

### D1 — C-6 (blocker): the derivation is fixed; the validator is not

**What closed.** I re-derived the attribution from the real archives rather than taking the clause's word for it, and all three discriminators hold:

- Rows 7-10 are byte-identical to the four rows in `2026-08-08-issue-32/log/vendor-calls.jsonl` (exact string match on all four, verified).
- `T-005`/`T-006`/`T-007` `judgment` stems exist only in the #17 archive; #32's archive holds only T-001 through T-004, and #27's archive holds no `judgment` tier at all. That pins rows 2, 3, and 6.
- `sonnet` and `opus` stems exist only in #27's archive, pinning rows 11-16.
- The intake claim is accurate: `2026-08-08-issue-32/spec.md` carries `fetched_at: 2026-08-08T14:47:08Z`. Rows 0-6 form one ascending run from 2026-08-07T23:33:54Z to 2026-08-08T01:38:02Z, entirely before it and entirely after #17's own intake at 2026-08-07T19:53:23Z, which resolves the four rows (0, 1, 4, 5) that stem-matching alone leaves ambiguous.
- Exactly one row has an empty `artifacts` array (row 17), so "the one row" is accurate, and append position puts it after #27's block.

r0's defects (a) and (b) are closed. The clause could state the rows-0-5 step more crisply — the three intake timestamps alone partition rows 0-16 with no ambiguity anywhere — but as written a checker can execute it. Also verified: the target file is tracked in the skills repo at commit `bf28bfa` with a clean worktree, so "diff the file against its git baseline" is runnable.

**(a) `--validate` is a deliverable no clause verifies.** C-6 is the only clause that mentions it, and it exercises the mode exactly once, against a file the same clause has already required to be correct. A `--validate` implementation that parses its argument, prints nothing, and exits 0 unconditionally satisfies C-6 in full. Nothing requires a test case for it (the spec's five new cases don't include it, and C-3 only runs the suite), nothing requires it documented (C-10 requires only `job` in `docs/vendor-ledger.md`), and nothing exercises its stated failure behavior — "exits nonzero naming the first bad row." So the constitution mandates shipping a new public CLI surface into three trees with zero coverage, while C-4's own failing example condemns exactly that shape: "the behavior works but no test covers it."

**(b) The invocation names neither a path nor which copy of the script.** The check ends "run `ledger-append.py --validate` over it." `SCHEMA_PATH` in that script is resolved relative to the script's own directory (`ledger-append.py:46-48`), and a frozen copy of both the script and the schema sits in the skills repo, whose `vendor-call.schema.json` contains no `job` at all (verified: zero occurrences). Run that copy and all 18 rows fail; run this repo's and they pass. For a blocker clause governing the job's only irreversible artifact, the invocation has to be pinned: this repo's absolute script path, and the absolute path of the archive file.

**On scope, plainly: as the spec stands, the mode is over-reach.** The spec's Files list says exactly what `ledger-append.py` gets — "`--job`, a small `derive_job()` reading the provenance header, docstring" — and a file-walking validation mode is not on it. It is also not the smallest thing that makes the spec's verification runnable, which is the constitution's stated justification (constitution.md:7). `ledger-append.py` already exposes `load_schema()` and `schema_violation(instance, schema, path="")` at module scope — the exact primitives a validation pass needs. A fixed invocation spelled out verbatim in the clause, importing those two functions and looping the file, is reproducible byte for byte, ships nothing, and is not the "checker writes its own validator" that r0 objected to, because the clause supplies the text rather than the checker inventing it.

Either remedy is acceptable:

- **Drop the mode.** Replace the last step of C-6's check with a literal, copy-pasteable invocation over `load_schema` and `schema_violation`, pinned to this repo's script and the archive's absolute path.
- **Keep it and fund it.** Amend the spec to add `--validate PATH` to the Files list, add a test case for it to the spec's new-coverage list, add a line to `docs/vendor-ledger.md`, and have C-6 name the case label the way C-4 does. Then pin the invocation as above.

### D2 — coverage: eight spec bars carry no clause

**(a) Four of the five test cases the spec names.** The spec's Verification requires new coverage in `test_ledger_append.py`: `job` derived from a fixture `spec.md`; `--job` overriding derivation; the key absent when no spec exists; a pre-change row with no `job` still validating; and two rows sharing `task_id: T-001`. Only the last has a clause requiring it to exist — C-4's "then open `test_ledger_append.py` and confirm a case covers it."

This is r0's defect moved rather than closed. r0 failed C-1/C-2/C-4 for checking the suite's exit code, which cannot see a missing case. The rewrite swung the other way: C-1 has the checker run the three derivation scenarios by hand in a scratch directory, and C-2 reads the schema file. Both now trip their own failing examples, which is the falsifiability repair working. But neither requires the cases to land in the suite, so a worker who ships correct behavior and writes no tests passes C-1 and C-2 cleanly, and the next edit to `derive_job()` silently removes the behavior with every suite green. That is C-4's own stated failing example, applied to the four cases C-4 doesn't cover.

The fix is one sentence in each clause, copied from C-4: name the case labels the clause depends on and require them present. The suite prints `  ok   {label}` for every case (`test_ledger_append.py:26`), so this also makes the cheap version available — see A2.

**(b) The close comment.** Wrap-up bullet 4: "Close #117 with the attribution table and the two out-of-scope findings named." C-10 relocates the two findings to `_working-memory/openQuestions.md`, which is a genuine improvement on a GitHub comment, but it does not carry the close comment or the attribution table, and a clause cannot retire a spec bar by substituting a different artifact for it. Add it to C-10 or list it as a non-goal explicitly.

**(c) The branch and commit shape.** Wrap-up bullet 1: branch `fix/117-ledger-job-identity`, one commit here, a separate commit in the skills repo. No clause. Nothing stops a worker committing to `main`. This is the cheapest deterministic check in the document — `git rev-parse --abbrev-ref HEAD` and `git log --oneline` — and it belongs to checker-deterministic, not to any of the eight judgment clauses.

**(d) Two prose deliverables.** The Files list requires the schema's new property to carry "a description saying what absence means"; C-2 requires the property, its type, and its absence from `required`, but not the description, and C-9 audits that description's *quality* while presuming it exists. The same list requires `ledger-append.py`'s docstring to be updated; no clause mentions it, and C-9's enumeration of prose this job wrote leaves it out. Both are one phrase each — add the description's content bar to C-2 and the docstring to C-9's list.

## Advisory (not FAIL drivers)

- **A1 — C-3's `&&` chain matters, and the fix is one line.** The clause's own stated failing example is `build-plugin.py --check` reporting drift, and that command is last in the chain, so it is invisible whenever either suite is red — which is exactly the state during a rework round. The clause can still fail, so this isn't a falsifiability defect, but the diagnosis it produces is systematically partial: a worker fixes the reported failure, gets re-checked, discovers the next one, and against a 2-per-tier retry budget that serial rediscovery can force an escalation the work doesn't deserve. `check-build.sh` hands its argument to `bash -c` (`check-build.sh:33`), so running all three with `;`, capturing each status, and exiting on their OR works today with no script change. I verified the current chain green from the repo root: 136 hook tests passed, plugin validation passed, `OK: shared-core wrappers, both published packages, and both marketplaces match fresh builds`, exit 0.
- **A2 — the document routes eight clauses to opus, not five, and four of them needn't be there.** C-1, C-2, C-4, C-5, C-6, C-8, C-9, and C-10 all read `checker-judgment`; only C-3 and C-7 are deterministic. Against #122 and #123, four are worth reconsidering. **C-2** is the clearest: "present under `properties`, typed `string`, absent from `required`" is a three-assertion script over a JSON file, and r0 recommended exactly that. **C-8**'s load-bearing half is the *absence* of `str.strip("'\"")`, which is a grep. **C-1** and **C-4** become deterministic for free if D2(a) is fixed the way C-4 already does it: once the clause names its case labels and the suite prints `  ok   {label}`, the check is "suite green and these labels present," which is checker-deterministic reading exit codes and output. That takes judgment routing from eight clauses to four and closes a coverage gap in the same edit. C-5, C-6, C-9, and C-10 are genuinely judgment; leave them.
- **A3 — r0's A5 still applies.** C-9 audits commit messages, which may not exist when the checker runs. Order it in the task, not the clause.
- **A4 — r0's A1 still applies, unchanged.** Three non-goals (the courier's local-time stamp, #116, #99) appear nowhere in the spec the constitution names as its source. They narrow scope rather than constrain work, so this stays harmless, but cite them or drop them.
- **A5 — r0's A6 still applies.** C-1's check runs a fixture `spec.md` in a scratch directory. Keep it out of the repo tree; C-7's allowlist won't cover it. Worth noting the scratch-directory instruction is what makes C-1's second failing example trip: a script-relative `derive_job()` run from a scratch directory resolves to this repo's own `spec.md`, whose `ref` is `/Users/k.arnett/.claude/plans/lets-fix-gh-issue-tidy-cook.md` and therefore visibly not the fixture's. The clause's parenthetical "(row carries that ref)" is doing that work — don't weaken it to "a `job` key is present."
- **A6 — no contradictions.** I checked every pair: C-2's "not in `required`" against C-6's "validates against the amended schema," C-6's "no other field altered" against the non-goals, C-3's "never hand-edited" against C-7's allowlist permitting those trees, C-1's omit-the-key against C-2's absence-is-the-only-spelling. All consistent.
- **A7 — C-10's rubric is the right shape.** It enumerates each fact per file rather than saying "documents the field," which is what makes a vacuous pass impossible. C-1 and C-2 should be written the same way.
