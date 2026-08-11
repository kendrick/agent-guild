---
task: DEC-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-11T07:28:00Z
---

Round 1 audit of the five task files under `.agent-guild/state/tasks/` against `.agent-guild/state/spec.md`, `.agent-guild/state/constitution.md` (round 2, ten clauses), and the routing table in `.agent-guild/CLAUDE.md`.

**All three r0 FAIL findings close.** Each was fixed at the root rather than papered over: C-9 gives the fifteen cases a substance check and T-003 reroutes to a judgment checker that can run it; C-4's confirmation (4) now names a constructible fixture and adds the `rework` case r0 flagged as most likely to survive; C-10 moves commit-message authorship into each task, and walked one task at a time, every one of the five messages is written by its own worker and read by its own checker before the orchestrator makes that task's commit. The scheduling hazard closes too, and more completely than asked — `T-003` in T-004's `deps` makes the graph a total order, which removes the `build-plugin.py` race and, incidentally, a lost-update race on `commit-message.md` that the new cadence would otherwise have created.

Coverage is complete across all ten clauses, routing is correct on every task, and the DAG is sound. `check-job-spec.py --audit-id DEC-audit` exits 0. C-5 and C-6 both pass on the current tree.

Three defects fail the round. One is new and load-bearing: T-002's brief makes a false claim about existing test coverage, and the widening it describes has a natural shape that silently drops the courier's read-only and no-override guarantees on exactly the dispatches the widening creates. The other two are repairs that moved rather than closed — the commit-message cadence lands with no worker instructed to run the humanizer, and the pinned return shape is self-contradictory in the one element two tasks disagree about.

**State note, recorded because it changes what a FAIL costs here.** `dispatches.log` shows this audit dispatched at 02:20:09 and T-001's worker at 02:21:10. T-001 is at `needs-check` with `_lib.py` landed and the three trees regenerated. The decomposition is being built while it is being audited, which is legal (`dispatch-guard` gates workers on a CON-audit PASS, not a DEC-audit PASS) but means finding 3 below arrives after the artifact it predicts. I cite that artifact only as evidence that an ambiguity in T-001's brief is real, not as a judgment on the worker — that is its checker's call.

## Per-task results

| task | clauses | routing | verdict | description | evidence |
| ---- | ------- | ------- | ------- | ----------- | -------- |
| T-001 | C-2, C-5, C-6, C-10 | worker-standard/sonnet, checker-judgment | **FAIL** | The excerpt is otherwise self-sufficient and every line citation resolves. Two defects: the `stem` element of the pinned return tuple is defined as two different strings in the same sentence, and the brief never tells the worker to invoke the humanizer skill over the commit message its own C-10 check audits. Route 4's lane is also left unpinned where the constitution now pins it. See Diagnosis 2 and 3, and Note 1. | task line 30 (`stem` = "the lane-suffixed filename") vs. line 55 (no humanizer instruction); constitution C-2 route 4 = "for the same lane route 3 pins and no other" vs. task line 37, silent; `_lib.py:150` `paused`, `:158` `lane_exhausted`, `:170` `courier_lane` |
| T-002 | C-3, C-4, C-5, C-6, C-10 | worker-standard/sonnet, checker-judgment | **FAIL** | The r0 fixture defect is fully closed — line 51 carries the exhausted-lane subtlety and line 53 the `rework` case, both matching C-4's amended confirmations. All eight line citations into `stop-gate.py` and `dispatch-guard.py` resolve. The new defect is line 49's third boundary: it tells the worker three preserved courier conditions are already covered by existing suite cases, and they are not covered on the path this task creates. See Diagnosis 1. | `test_hooks.py:824-826` — `proj_courier` holds `T-020` at `status: checking`, and `con_pass()` writes only `CON-audit-r0.md`, so the project has no verdict of record and `second_opinion_debts()` returns `[]` for all five existing cases; `dispatch-guard.py:280` checker branch, `:293` override, `:299` workspace-write, `:307` lane exhausted; `stop-gate.py:33`, `:94`, `:98`, `:103` |
| T-003 | C-1, C-9, C-5, C-6, C-10 | worker-standard/sonnet, checker-judgment | PASS | The r0 hole closes cleanly. C-9 is cited and keyed byte-identically, the reroute to `checker-judgment` is correct and mandatory, and C-1's script half still runs — a judgment checker can invoke `check-build.sh` where a deterministic one could never read the source C-9 needs. The excerpt carries r0's own `so: an auditor stem owes nothing` example as the named trap and asks for a positive control in the same case, which preserves the label grep C-1 depends on. Fifteen bullets compared programmatically against C-1's fifteen text bullets and its fifteen grep labels: all three lists identical. One residual tension at Note 2. | C-1 text bullets == C-1 for-loop labels == T-003 bullets, zero diffs; `test_hooks.py:63` `check()`, `:73` `fresh_proj`, `:80` `write_task`, `:102` `con_pass`, `:170` `write_verdict_json`; excerpt line 48 vs. line 57 |
| T-004 | C-7, C-5, C-6, C-10 | worker-craft/opus, checker-judgment | **FAIL** | `deps: [T-002, T-003]` closes the r0 scheduling hazard. The five files, the `activeContext.md` arithmetic, and the read-the-hooks-first instruction all survive intact. Fails only on the humanizer gap it shares with T-001 through T-003. Line 55's promise that T-005 audits this prose is now half true and worth correcting alongside it. See Diagnosis 2 and Note 4. | task line 53 (commit-message paragraph, no skill invocation) and line 55; C-8's five pieces exclude `conventions.md`, `openQuestions.md`, `activeContext.md`; `AGENTS.md:42`, `wc -l _working-memory/activeContext.md` = 22 |
| T-005 | C-8, C-5, C-6, C-10 | worker-craft/opus, checker-judgment | PASS | The r0 ordering contradiction is gone. The excerpt correctly states the first four sections are already committed and must not be edited, points at `git log -p` rather than `git status` with the reason attached, and makes the `build-plugin.py` run unconditional. C-8's narrowing is reflected accurately: five pieces, authored elsewhere, audited here. This is the one task whose brief does invoke the humanizer skill by name, which is what makes its absence from the other four visible. | task line 46 (already committed), line 55 (`git log -p`), line 59 (unconditional); line 28 "Invoke the `humanizer` skill and run its audit-and-revise loop" |

## Diagnosis

- **T-002** (major, on a blocker clause): line 49 asserts that the courier's three preserved conditions are "already covered by existing suite cases; don't disturb them." That is false for the code path this task creates, and it is the sentence most likely to stop a worker from protecting them. I checked the fixtures directly. All five existing courier cases run against `proj_courier`, whose task `T-020` sits at `status: checking` and whose only verdict file is the `CON-audit-r0.md` that `con_pass()` writes — an auditor stem, and `.md` at that. The project therefore has no verdict of record, `second_opinion_debts()` returns `[]`, and every existing case enters through the no-debt fall-through. Nothing exercises a debt-bearing courier dispatch against the override, read-only, or lane checks.

  That matters because the shape the task recommends — "Moving the `checker-courier` branch ahead of the generic status check is the straightforward shape" — invites an early allow:

  ```python
  if agent == "checker-courier" and tid in {d[0] for d in _lib.second_opinion_debts(data)}:
      return 0
  ```

  placed before the status check, with the override (`:293`), `workspace-write` (`:299`), and lane (`:307`) checks left where they are, further down. Walk C-4's five confirmations against that mutant and all five pass: (1) courier/complete/debt exits 0; (2) courier/complete/no-debt falls through to the status check and exits 2; (3) `checker-judgment` is not the courier, so status refuses it; (4) an exhausted lane discharges the debt, so that dispatch also falls through and is refused on the sentinel; (5) courier/rework/debt exits 0. C-1's three dispatch-guard labels pass. C-9 reads the tests, not the gate. The five existing cases pass. Yet under the new regime a courier is only ever dispatched *because* a debt exists, so the mutant makes "no model override" and "read-only by contract" dead letters for every real courier dispatch — and `checker-courier` being unable to write is not a style rule.

  Fix, no CON re-audit needed. Replace line 49's last sentence with something that states the truth and the obligation: *The existing cases at `test_hooks.py:828-864` all run against a debt-free task, so none of them exercises the path this change adds. Gate the debt so it relaxes the status requirement only — a debt-bearing `checker-courier` dispatch must still be refused for a model override, for `workspace-write` or `danger-full-access`, and for an exhausted lane.* Then add one sentence to T-003 directing a sixteenth and seventeenth `so:`-labelled case (courier on a debt-bearing task with a model override exits 2; with `workspace-write` exits 2), which T-003 line 59 already permits. If you would rather bind it, amend C-4 with a sixth confirmation and re-run CON-audit; the excerpt fix alone is enough to make it catchable, since C-4 already orders a source read and its text already forbids the regression.

- **T-001, T-002, T-003, T-004** (moderate): no worker is told to run the humanizer over the commit message its own checker will audit with it. `spec.md:108` says prose bound for the commit message "goes through the `humanizer` skill before merge," and C-10 requires the message to pass "the same humanizer audit" C-8 describes, with each task's C-10 check having the *checker* run that audit. T-005's excerpt invokes the skill by name at line 28 and again at line 53. The other four give the constraints — no hard wrap, no attribution trailer, WHY over WHAT — and never name the skill. The standing project preference is explicit that applying the principles from memory is not enough because it consistently misses tells, so this is four tasks held to an output standard their brief does not tell them how to meet, on a check that will be applied to all four. The likely cost is a rework round apiece on a clause that could have passed first time.

  Fix: add one sentence to the commit-message paragraph of T-001 (line 55), T-002 (line 61), T-003 (line 63), and T-004 (line 53) — *Invoke the `humanizer` skill and run its audit-and-revise loop over the message before you finish, with the three house overrides C-8 names: em dashes chained directly to the text on both sides, Title Case headings, and a list of exactly three where three is the true count.* No constitution change; C-10 already requires the outcome.

- **T-001** (moderate): the return shape is pinned at the tuple level and self-contradictory in the one element two tasks have to agree on. Line 30 reads "`(task_id, stem, lane)` — `task_id` like `T-001`, `stem` the lane-suffixed filename the crossing would have landed at," then "Pin it, don't improvise; a worker downstream reads this file to learn the contract and there is no other place it is written down." But "stem" and "the lane-suffixed filename" are different strings: for `T-001-sonnet-r0.json` awaiting a codex crossing they are `T-001-sonnet-r0` and `T-001-sonnet-r0-codex.json` respectively. The brief names the field one thing and defines it as the other.

  This is not hypothetical. The `_lib.py` now in the working tree returns the record stem (`stem = name[: -len(".json")]`, then `debts.append((task_id, stem, lane))`), not the lane-suffixed filename — so a brief that said "pin it" has already produced the other reading. The consequence lands on T-002, whose line 34 requires each block-message line to name "the missing lane-suffixed stem" and whose C-3 confirmation (2) checks exactly that. With the landed shape, T-002's worker must build `f"{stem}-{lane}.json"` itself, and nothing in either brief tells it to; a worker that prints the tuple's `stem` verbatim emits the record stem and fails C-3's confirmation (2), or passes it in front of a lenient checker.

  Fix: rewrite line 30's second clause to state one string and say which. Either *`stem` the verdict-of-record stem with no lane suffix and no extension, e.g. `T-001-sonnet-r0`* — in which case add to T-002 that the block message composes `f"{stem}-{lane}.json"` — or *`stem` the full lane-suffixed filename the crossing would have landed at, e.g. `T-001-sonnet-r0-codex.json`*. The first matches what has landed and costs T-002 one sentence; the second matches T-002's current wording and costs T-001 a rework. Pick one and make both files say it.

## Coverage

Every spec section binds to at least one task, and all ten clauses are cited and keyed. I compared every `check_method` body against its clause in the constitution programmatically.

| spec | task | clause |
| ---- | ---- | ------ |
| Change 1, `_lib.py` predicate and `COURIER_LANES` | T-001 | C-2 |
| Change 2, `stop-gate.py` enforcement (all four bullets) | T-002 | C-3 |
| Change 3, `dispatch-guard.py` widening | T-002 | C-4 |
| Change 4, the `.denied` waiver | T-001 recognizes it (route 4); T-004 documents it | C-2, C-7 |
| Change 5, docs — `CLAUDE.md` plus four working-memory files | T-004 | C-7 |
| Change 6, regenerate the published views | all five | C-5 |
| Tests, the case list | T-003 | C-1 |
| Tests, that the cases assert something | T-003 | C-9 |
| Verification, the three commands | all five | C-5 |
| Verification, the five-step end-to-end pass | T-002 (steps 1, 2, 3, 5 in C-3's rubric; step 4 in C-4's) | C-3, C-4 |
| Notes, the humanizer pass over shipped prose | T-005 | C-8 |
| Notes, the humanizer pass over the commit message | all five | C-10 |

Clause-to-task: C-1 and C-9 to T-003; C-2 to T-001; C-3 and C-4 to T-002; C-5, C-6, and C-10 to all five; C-7 to T-004; C-8 to T-005. No clause is uncited. Every `check_method` body for C-1, C-4, C-5, C-6, C-7, C-9, and C-10 is byte-identical to the constitution's. Three carry cosmetic renderings, all harmless and all defensible for a reader holding the task file:

- T-001's C-2 renders "do not read C-1's assertions" as "do not read the test suite's assertions" (carried over from r0) and drops one rationale sentence, "Both sentinels present at once proves nothing, since a predicate that hardcodes one lane discharges that fixture exactly as a correct one does." The procedure that sentence justifies survives verbatim — "call the predicate four times ... placing exactly one sentinel at a time and removing it before the next" — so the checker still performs the discriminating test. Restoring the sentence would cost nothing and would stop a checker from deciding the four-call ritual is redundant.
- T-002's C-3 drops the bold on one "and". Immaterial.
- T-005's C-8 renders "the three overrides above" as "the three house overrides" and "The task carrying this clause" as "This task". Both referents resolve.

Nothing is claimed by two tasks. The five commit-message sections are per-task by construction and each brief tells the worker to leave the others alone, which the total-order DAG now guarantees is safe.

One spec requirement is only partly covered, recorded at Note 4 rather than as a Diagnosis item: `spec.md:108` names "the working-memory entries" as humanizer-bound, and C-8's five pieces include `decisionLog.md` but not `conventions.md`, `openQuestions.md`, or `activeContext.md`.

## Routing

Every assignment matches the table, and every `executor_model` matches `_lib.DEFAULT_MODEL` (verified against `_lib.py:33-45`), which `dispatch-guard` enforces.

- T-001, T-002, T-003: `worker-standard`/`sonnet`. Clear-spec implementation judged on correctness. Correct at all three; `worker-bulk` would be wrong for any of them and `worker-craft` would be overspend.
- T-004, T-005: `worker-craft`/`opus`. Read by people, and T-005 is a taste pass by definition. Correct.
- Checkers: all five are `checker-judgment`, and all five must be. C-10 is a rubric and now sits on every task, so no task can route to `checker-deterministic` regardless of what else it carries. **T-003's reroute is correct and was mandatory**, not merely permitted — it carries two rubrics now (C-9 and C-10) where at r0 it carried none.
- **C-1's script half still runs.** T-003 keys C-1 to the full `check-build.sh` invocation, byte-identical to the constitution's, and a judgment checker can invoke a script where a deterministic one could never read the test source C-9 requires. The asymmetry is the reason the reroute costs nothing: moving up a tier keeps the grep and adds the source read. C-1's coverage half and C-9's substance half are now held by the same agent on the same artifact, which is what C-1's note claims and, at r0, did not have.

## The dependency graph

`T-001 → T-002 → T-003 → T-004 → T-005`. Acyclic (verified by DFS), every referenced id exists, no self-reference, no orphan. T-004's `T-002` and T-005's first three entries are transitively implied and harmless.

Adding `T-003` to T-004's `deps` did more than close the hazard r0 named — it made the graph a **total order**, so no two tasks can ever be in flight at once. I checked this exhaustively rather than by inspection: every pair of tasks stands in an ancestor relation. Two consequences, both good:

1. The `build-plugin.py` race is gone by construction, not by convention. `build_codex()` calls `shutil.rmtree(out_dir)`, so two concurrent workers could have had one observe a tree the other was mid-delete on, and C-5 would have reported it as drift.
2. A race the *new* cadence would have introduced is gone with it. Under r0's graph, T-003 and T-004 both became ready when T-002 completed, and both now append to `.agent-guild/state/commit-message.md`. Concurrent read-modify-write on one file is a lost-update bug, and the losing section would simply be absent when its checker ran C-10. The fix for the older hazard happened to cover this one; worth knowing it was load-bearing twice, in case anyone is later tempted to relax the edge as redundant.

The cost is wall-clock only. Nothing in the job can be parallelized now, which was already nearly true.

## The C-10 ordering, walked one task at a time

This is the repair most likely to have moved the problem instead of solving it, so I walked all five rather than sampling. The cadence is `constitution.md:17`: the orchestrator commits each task "after that task's verdict of record lands and its second opinion is settled." C-10 requires each task to append its own section "before that task finishes."

| task | writes its section | its C-10 check reads it | its commit exists | readable first? |
| ---- | ------------------ | ----------------------- | ----------------- | --------------- |
| T-001 | worker, before `needs-check` (creates the file) | T-001's `checker-judgment` | after T-001's verdict settles | yes |
| T-002 | worker, before `needs-check` (appends) | T-002's `checker-judgment` | after T-002's verdict settles | yes |
| T-003 | worker, before `needs-check` (appends) | T-003's `checker-judgment` | after T-003's verdict settles | yes |
| T-004 | worker, before `needs-check` (appends) | T-004's `checker-judgment` | after T-004's verdict settles | yes |
| T-005 | worker, before `needs-check` (appends) | T-005's `checker-judgment` | after T-005's verdict settles | yes |

All five. The ordering is now satisfiable for every message rather than for one, which is what r0 asked for and is the whole of option (a). Three details I checked rather than assumed:

- **The create/append handoff is unambiguous and matches the DAG.** T-001 says "create"; T-002 says "create the file if you are the first to get there; append if it exists"; T-003 and T-004 say append and leave other sections alone; T-005 says the file "already holds sections for T-001 through T-004." Under the total order every one of those statements is true when its worker reads it. T-002's defensive both-ways phrasing is harmless.
- **C-6 permits the writes.** `check-diff-scope.py:112` grants `.agent-guild/state/` unconditionally, so `commit-message.md` never needs an allowlist entry no matter which task touches it.
- **T-005 no longer contradicts itself about what it can see.** The four earlier commits exist by the time it runs, so `git log -p` is the right instruction and C-8's "diff each reworded passage against its state before this task" resolves against HEAD cleanly. This is strictly better than r0's arrangement, where the same instruction pointed at an empty working tree.

One consequence of option (a) worth stating so it is not later mistaken for a defect: T-005 rewords docstrings in files T-001 and T-002 already committed, so the history shows un-audited prose landing and being fixed a commit later. That is inherent to option (a) — the alternative was option (b), which the constitution's preamble at line 19 rejects for a stronger reason — and it washes out at squash-merge. Not a finding.

## Reading each excerpt cold

I re-read all five as a worker holding only that file and the constitution. What is still guessable, beyond the Diagnosis items:

- **T-001** is otherwise complete. The five discharge routes are enumerated, the host-lane trap is named with its exact failure, the never-raise contract cites two existing functions that hold to it, and the helpers to imitate are named. Route 4's unpinned lane is Note 1.
- **T-002** grew by two paragraphs (lines 51 and 53) and neither is redundant with what was there. Line 51 resolves the fixture question r0 raised and does not restate line 49's exhausted-lane bullet — one is about which fixture the checker builds, the other about which condition survives. Line 53 is the `rework` case and is new information. Both agree with C-4's amended text.
- **T-003** grew by the C-9 paragraph (line 55) and the trap paragraph (line 57). The trap paragraph is the strongest addition in this revision: it names the failing case, explains why it is vacuous, and gives the positive-control pattern in a form that keeps the label intact. The tension with line 48 is Note 2.
- **T-004** is unchanged except for the dependency and the commit-message paragraph. Note 4.
- **T-005** is the cleanest of the five and needs nothing beyond the humanizer point, which it already satisfies.

Nothing added this round contradicts what was already there, with the one exception at Note 2.

## C-5 and C-6 on the current tree

Both pass. Re-run at audit time, from the repo root, exactly as written in the task files:

- **C-5** exits 0. `test_hooks.py` reports 146 passed, 0 failed; `test_codex_adapter.py` runs 27 tests, OK; `build-plugin.py --check` reports both published packages and both marketplaces matching fresh builds, with strict plugin validation passing. Log at `.agent-guild/state/log/build-20260811T022050.log`.
- **C-6** exits 0, reporting 4 paths in scope: `.agent-guild/hooks/_lib.py` and its three regenerated copies. All four are allowlisted.

The tree is no longer a clean baseline — T-001's worker landed `COURIER_LANES` and `second_opinion_debts()` mid-audit — but both checks pass on it, which is the useful fact: the clauses are runnable as written and green on real work rather than only on an empty diff. Worth recording that C-6 reported "0 path(s) in scope" earlier in this same session, before those writes landed. That is the script's honest output for a clean tree, not a vacuous pass, but it is a reminder that a C-6 green line carries no information until you read the count.

## Notes

Four minor findings. None is a condition of this FAIL.

1. **T-001's route 4 lane was pinned in the constitution and not propagated to the excerpt.** C-2 route 4 now reads "for the same lane route 3 pins and no other" — r0's minor finding 1, correctly fixed. T-001's line 37 still reads only "a waiver `…-r<N>-<lane>.denied` exists," while its line 36 does carry route 3's pinning. Within the excerpt the contrast now reads as deliberate when it is a missed edit. The worker holds the constitution, so the governing text is available, and the code that has landed pins the lane correctly. Cheap to fix while T-001 is open for Diagnosis 3 anyway.

2. **T-003's line 48 and line 57 pull against each other on the same case.** Line 48 tells the worker a `CON-audit-r0.json` "alone produces no debt. Assert on a clean exit, not on message text." Line 57 names that exact construction as the trap C-9 exists for and asks for a positive control in the same fixture. They reconcile if line 48's "alone" is read as the proposition under test rather than the fixture's contents, but a worker reading top to bottom builds line 48's version first. One clause on line 48 fixes it: *…alone produces no debt — see the positive-control requirement below before you write this one.*

3. **T-002's line 49 citation of "existing suite cases" is worth keeping** once Diagnosis 1 is applied. The cases genuinely do pin the override, read-only, and lane refusals on the pre-existing path, and a worker should not disturb them. The correction is to add what they do not cover, not to delete the sentence.

4. **`spec.md:108` names the working-memory entries as humanizer-bound and C-8 covers only one of the four.** C-8's five pieces include the `decisionLog.md` entry but not `conventions.md:15`, `openQuestions.md:19`, or `activeContext.md`. T-004's line 55 tells its worker "T-005 runs a humanizer pass over this prose afterward," which is true of the `CLAUDE.md` section and the decisionLog entry and false of the other three files T-004 writes. I am not asking for C-8 to be widened: the two uncovered edits are a line deletion and a line replacement, and `activeContext.md` is a bulleted queue under a hard line ceiling, so there is little prose surface for an audit to find. Correct T-004's line 55 to name what T-005 actually audits, so the worker does not draft the three working-memory files expecting a safety net that is not there.

The `classify-crossings.py:122` off-by-one survives into T-001's excerpt again, inside a "do not touch this file" instruction that drives no check. Leave it, for the same reason r0 gave.
