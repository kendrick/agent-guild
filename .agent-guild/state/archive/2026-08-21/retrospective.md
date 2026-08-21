# Retrospective: payload provenance (#183)

Four tasks, eighteen verdicts, no retries, no escalations, no disputes. Every worker passed on its first dispatch, and that is the headline finding rather than a happy accident: fifty-one defects were caught before a worker ran, by audits of the orchestrator's own paperwork.

## Catches

Ten FAIL verdicts, and not one of them was a checker turning back a worker. All ten were audit rounds against the constitution and the decomposition.

| Gate | Rounds | Verdict | Findings |
| --- | --- | --- | --- |
| CON-audit | r0–r10 | FAIL ×8, then PASS at r8, r9, r10 | ~44 across eight failing rounds |
| DEC-audit | r0–r2 | FAIL ×2, PASS at r2 | 5 plus two advisories |
| Task checks | T-001..T-004 | PASS ×4 | none |

The four task checks passing first time is what the front-loading bought. Each worker got a specification that eleven CON rounds and three DEC rounds had already been attacked from every angle, so there was very little left to get wrong.

Three catches are worth naming because each would have shipped a defect that every green check in the job would have missed.

**A user's edit destroyed on the second release** (CON r0). Every clause checked the refusal of a locally edited file exactly once, in the run that first sees the edit. A one-line variant that preserves the edit and then restamps its recorded hash from the bytes on disk passed all six probes and the whole suite, and then overwrote the user's edit on the next release, because by then the edit read as clean. That is the precise outcome this job was commissioned to prevent.

**Provenance silently skipped on Codex** (CON r1, then again at r2 one file over). Wrapping the record write in `if host == "claude":` left every probe green and every suite green while half the product stayed pre-provenance forever. The same manifest split reappeared in the nudge's own version lookup a round later.

**C-8 never running on the tree the job ships** (DEC r0). C-8 runs the suites and `--check`, and only T-001 cited it, so it executed once—before T-002 wrote one of the files it runs. Measured, not inferred: with a deliberately red `test_build_plugin.py` on an otherwise finished tree, every check in the decomposition came back green. This is the class of defect no CON round can reach, because it is a fact about the schedule rather than about any clause read alone.

## Strain

None in Phase 2. Zero retries, zero escalations, zero disputes, and no tier climbed.

All the strain was in Phase 0. Eleven CON rounds is the number to look at, and the shape of it matters more than the count: findings did not converge smoothly. Rounds r0 through r5 each produced four to eight findings, and r7—a round dispatched purely to convert a standing FAIL into the PASS the worker gate needs—found a blocker in the repairs made after r6.

Two of my own repair patterns account for much of that. The first was fixing a property in one clause and leaving its twin alone: the manifest-lookup trap was closed in C-5 at r4 and left open in C-1 until r5, where the stamp actually matters, and C-1's Codex arms asserted a strict subset of what its Claude arm asserted until r6.

The second was writing assertions that pass rather than assertions that separate. Two of four repairs after r6 did not discriminate at all. One was worse than useless: to catch a nudge that suppresses the partial-init report, I asserted on the string `partially initialized` but built the fixture by deleting a payload file, and `_missing_pieces` reads only the five `state/` subdirectories. The string was unreachable, so the assertion went red against a correct implementation and red against the variant it was meant to catch, and it made C-5 unsatisfiable.

## Disputes

None. No worker contested a verdict.

## Check-Infra Debt

No ERROR verdicts: every check that was dispatched could run.

The debt is elsewhere, in six infrastructure stalls that killed dispatched agents outright. Five correlated with machine saturation—load reached 32 with Microsoft Defender and Spotlight indexing the file churn each audit round creates—and one did not, at a load of 2.9. The mitigation that worked was a per-round churn budget: one whole-tree copy patched in place with `git show HEAD:` rather than cloned per variant, each venue deleted as its result is read. Rounds run under that budget finished at a load under 5.

`STALLED.md` was written three times naming tasks that were not stalled. The stop gate counts a blocked turn against a task even when the orchestrator is correctly waiting on an audit gate that blocks every worker, and an in-flight marker for `DEC-audit` does not hold `T-001`'s counter. This is adjacent to #165, where the gate advised a dependency violation.

## What The Constitution Missed

The gap that recurred, in seven clauses across five rounds, is **a requirement a clause states plainly that no check reaches**. It appeared in C-8's coverage half, twice in C-5 (the no-writes sentence, then the silent direction), in C-3's diagnostic set, in C-2's `unchanged` term, and—after being named and swept for—in C-5 again at r10, where the combined double-registered state that the two readings turn on appeared in no arm.

A related shape cost three more rounds: **a set-wide claim proved on a one-element fixture**. Fixtures held exactly one edited file, so "the only path the diagnostic names" was satisfied by an implementation that names thirty-seven, and "every file whose bytes match its recorded hash" was satisfied by one that upgrades only the first.

The most valuable single finding for the next job's Phase 0 is what DEC r1 produced with the comparand diff. CON r9's reference implementation and DEC r1's, built independently from identical constitution bytes, implemented C-5 differently, and every check in the job accepted both. Nothing else in the apparatus can surface that: one round's build settles an ambiguity without noticing it was one. Two builds side by side is the only instrument that finds a fork.

One clause defect is knowingly outstanding: C-7's `check:` line names "the four behaviors" while its text now names five, and the `#214` table it points at is not the split sentence the revision added. It is recorded as minor because checkers dispatch against `check_method`, and T-003's carries the requirement verbatim. It should be folded in whenever C-7 is next touched, along with C-5's wording note from r10—"this job moves the notice above them" describes the wrong motion, since it is the double-registration return that has to move.

## Weight Against Outcome

**Job weight**: deep, corrected from standard by the user on CON-audit r4's finding, because verification did require building an instrument rather than invoking one: a ~600-line probe harness covering three install shapes and four nudge deployments, and a reference implementation each audit round rebuilds and mutates. The original derivation read "the suites already exist" off the spec and missed that none of those suites asserts anything about provenance, which the preamble had already noticed and the weight line had not.

The document reached **nine clauses**. CON-audit spent **eleven rounds** (r0–r10) and DEC-audit **three** (r0–r2).

The correction is the number worth carrying forward. Derived as standard, the job would have been capped at eight clauses and the ninth—C-9, which owns regression coverage—would have needed an overrun line to exist at all. It exists because CON r0 found C-8's coverage half unfalsifiable and #141 had already established that a script cannot verify a test suite carries real cases. The original derivation failed on a signal that was visible in the spec: the suites named in the acceptance criteria existed, but none of them asserted anything about the property being built. "Does a harness exist" is the wrong question. "Does a harness exist that can see this property" is the right one.

## Teardown

`apparatus/` held 1.1M across fourteen round directories and was deleted at teardown rather than archived, since `archive/` is tracked. Nothing else in the kit removes it, which is #200.
