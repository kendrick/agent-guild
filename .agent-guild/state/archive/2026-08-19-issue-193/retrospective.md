# Retrospective: Three Defect Shapes The Linter Can Catch Mechanically (#193)

**Job weight**: deep, corrected from standard by the user, because verification turned out to need an instrument built rather than one invoked—a ~750-line probe harness, a reference implementation rebuilt by each audit round, and a "done" the spec states as a property (discriminating cases drawn from the archive) no existing command can check

Final constitution: 9 clauses, seven script-checked and two rubrics. Audit rounds: CON-audit r0 through r8, DEC-audit r0 through r1. Task verdicts: three, all PASS on the first dispatch.

## Catches

Nine FAIL verdicts, every one of them from the auditor. No task-level check failed. T-001, T-002 and T-003 each passed first time, with no retries, no escalations, and no disputes anywhere in the run.

That distribution is the whole story of this job. Eleven audit rounds against three clean task checks means the cost landed almost entirely in Phase 0, and so did the defects. Ten blockers were found and fixed in a document. None reached an artifact.

Where those ten blockers landed:

| Clause | Blockers | What it was |
| --- | --- | --- |
| C-9 | 6 | The suite-coverage clause and its mutation machinery |
| C-5 | 1 | The R2 diagnostic clause |
| C-3 | 1 | The R21 routing clause |
| C-1 | 1 | The R10 adjacency clause |
| C-10 | 1 | The archive-drawn clause, later folded into C-9 |

## Strain

None at the task layer, which is where a retrospective usually finds it. Nothing retried, nothing escalated, and the routing held: sonnet built both substantive artifacts and haiku ran the regeneration, each passing on first dispatch.

The strain was in Phase 0, and it moved over the course of the run. Rounds r0 through r2 found defects in the standard itself: clauses that were vague, that contradicted their own checks, or that delegated coverage to a clause running too early. From r3 onward the standard was mostly settled and the defects moved into the instrument. Five of the ten blockers were bugs in the probe harness written to verify the clauses, and every one of those five was a false FAIL, a check that would have refused correct work rather than let broken work through.

That is a pattern rather than a run of bad luck, and it is the most transferable thing this job learned. **Every check added to close a hole was over-tight in its first version.** A check written in response to a finding gets written while the finding is vivid, so it reaches for the narrowest thing that would have caught it: a backtick, a fixed adjective, a parameter name. The next round builds a faithful implementation that spells the same idea differently, and the check refuses it. Round 4's wrapper was the worst case, sitting below `sys.exit(main())` where a subprocess run never reached it, which left C-9 red against every possible implementation and would have failed the job by construction.

The fix was in how the audits were commissioned rather than in any clause. Once the charters told auditors to attack with *faithful* implementations instead of only with wrong ones, and to build two that factored the code differently, the blockers stopped. Rounds r7 and r8 found none, and r6 was the round that first reported both reference implementations passing.

## Disputes

None. No worker contested a verdict.

## Check-Infra Debt

No ERROR verdicts, so every check ran when asked. Two pieces of debt surfaced anyway.

**The return gate misidentifies concurrent dispatches.** `_lib.py` resolves an agent's identity by taking the last `Task-ID` in the transcript, so when a wave dispatches two agents in one message, which the contract requires, both returns resolve to the second dispatch. T-001's checker filed its verdict correctly but could not be identified on return, and left a stale in-flight marker behind. The remaining dispatches were serialized by hand to protect the verdict record, which means this job never got the parallelism the wave mechanism exists to provide. The fix belongs in `hooks/`, so `conventions.md` puts it out of the guild's reach.

**Two transient API failures cost most of a round each.** CON r5's auditor died mid-summary and its verdict survived only because it had already been written to disk. Round 6's first two attempts produced nothing at all. Filing the verdict before composing any prose became a standing instruction in every later charter, and it earned its place.

## What The Constitution Missed

**A clause count is not a cost estimate.** The weight was derived as standard and corrected to deep by the user, but only after r2 showed the spec's test-coverage criterion covered by nothing. The correction was right and it arrived late, because the derivation asked whether verification needed an instrument built and then answered from the acceptance criteria, which all named commands that already existed. What actually needed building was the thing that would prove those commands discriminate. A cheap tell for next time: if a check has to prove a property *of a test*, the instrument does not exist yet.

**Two mechanisms had to be cut, and both were cut late.** `conventions.md` says to cut a mechanism once two rounds find a blocker in it. C-5 ran four rounds as a regex trying to decide whether a sentence states a position. C-9's mutation machinery ran three. Both became rubrics, and both went quiet immediately afterward. The rule works. It was applied a round or two later than it should have been, each time because the next patch looked small.

**A judgment rubric is the right instrument for "does this actually check anything."** #141 reached that conclusion first and this run re-derived it independently. A script cannot tell a real test from a written one, and it cannot tell a message that states a position from one that merely mentions a line number. The two clauses that survived to the end as rubrics are exactly the two carrying those questions.

**Five known minors ship with the constitution.** All were deferred on purpose: editing the document re-closes the Phase 0 gate and costs a fresh round for wording that changes nothing a worker builds. Three came from CON r8, one from DEC r0, and one from DEC r1, and each is recorded in the verdict that found it.

**One defect only the decomposition could catch**, which is the case the contract predicts and the reason DEC-audit re-reads the constitution. C-7 reads the uncommitted working tree, and only one of three task files told its worker not to commit. A commit at the wrong moment leaves that check reporting zero paths in scope and passing without inspecting anything. Nothing about that is visible until a schedule exists to read the clause against.

## Apparatus, Deliberately Preserved

This run satisfies the condition #122 and #198 have been parked behind: **two consecutive DEC-audit rounds against unchanged constitution bytes, with both rounds' apparatus kept.** DEC r0 and r1 ran against a `constitution.md` last modified before either of them, still byte-identical to the digest CON-audit r8's PASS was bound to, so nothing about the document moved between the two rounds.

`apparatus/DEC-audit-r0/` and `apparatus/DEC-audit-r1/` are therefore archived rather than deleted. That is an explicit opt-out of the teardown rule #199 introduced, recorded here because the rule says a run collecting this evidence has to say so. The two directories are 36K and 32K, so the cost the rule exists to prevent (one `kendrick/dotfiles#22` round moved 33M across 3,182 files into tracked history) does not apply at this size.

Every CON-audit apparatus directory was deleted at teardown as normal, along with an aborted r4 directory left behind when two dispatches died to API errors. Those totalled roughly 1.1M and none of it is evidence for anything now that its round has a verdict.

The run's `log/` was pruned the same way and less carefully. `check-build.sh` tees every invocation to a timestamped file, and 146 of them had accumulated at 36K each, 1.6M in total, with exactly one verdict citing any of them. Pruning the uncited ones was right; the command that did it word-split badly and took the two cited files as well. The cost is small but real: `T-001-sonnet-r0`'s C-8 finding names `build-20260819T002430.log`, which is no longer there. That verdict quotes the exit code and the output inline, so the evidence survives and only the raw tee is gone. `dispatches.log`, `return-gate.log`, `stop-gate.state` and the stale in-flight marker are all intact, and no courier ran, so there is no vendor ledger to have lost.

## Weight Against Outcome

| | |
| --- | --- |
| Weight line | deep, corrected from standard by the user |
| Clauses | 9 (deep has no ceiling) |
| CON-audit rounds | 9 (r0 to r8) |
| DEC-audit rounds | 2 (r0 to r1) |
| Task checks | 3, all PASS at r0 |
| Retries / escalations / disputes | 0 / 0 / 0 |

Nine CON rounds against a nine-clause constitution is the number to argue with next time. In its defence: ten blockers died in a document rather than in an artifact, and five of them were checks that would have failed correct work and cost a worker a retry each. Against it: three of those rounds went to finding bugs in an instrument this job wrote for itself, and a smaller instrument would have had fewer of them.
