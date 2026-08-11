# Retrospective: #100—make the mandatory second opinion actually dispatch

Five tasks, seventeen verdicts, six crossings, no disputes, one retry, no escalations. Five commits on `feat/100-enforce-second-opinion`.

The job shipped what the issue asked for. Most of its verification budget went on discovering that the artifacts the feature depends on are written by agents and validated by nobody.

## Catches

Six FAIL verdicts. Four came from the auditor, against the orchestrator's own work.

| what | who caught it | what it would have cost |
| --- | --- | --- |
| C-2's check could not fail its own likeliest failure: a predicate ignoring `data` and hardcoding the `codex` lane passes every Claude-host check and deadlocks every Codex host | auditor, CON r0 | the issue's third Done-when condition failing silently, both hosts *not* producing the same artifacts |
| C-1's note claimed a substance check no clause performed—C-2, C-3, C-4 all run before a single test case exists | auditor, DEC r0 | fifteen cases that assert nothing, satisfying the clause that exists to prevent exactly that |
| C-4 named a fixture nobody can build: an exhausted lane discharges the very debt the confirmation needs standing | auditor, DEC r0 | a blocker clause a checker must guess at, or FAIL on an impossibility |
| C-8 wanted commit messages read before they were commits, while the cadence put four of five commits in history first | auditor, DEC r0 | four commits under messages no checker ever saw |
| the predicate treated an unreadable record as owing regardless of routes 1-4 | checker-judgment, T-001 | a debt no dispatch can clear—the livelock, proven with four fixtures |
| the same defect, independently | checker-courier, T-001 r0 | (agreement, not a separate catch) |

**Verifying the orchestrator paid better than verifying the workers.** Four of six catches were the auditor holding the constitution and decomposition to the falsifiability bar, and three of those four were clauses that read fine and could not fail. The workers produced one real defect across five tasks. That ratio argues for spending more on the Phase 0 and Phase 1 audits.

The single worker defect is also the one the courier independently found, which is the only genuine agreement-on-a-defect this project has recorded on a judgment rubric.

## Strain

T-001 took one retry at sonnet. Nothing escalated; no task climbed a tier. Routing held: the two `worker-craft` tasks were the two a person reads, and the three `worker-standard` tasks were judged on correctness.

T-003 was rerouted from `checker-deterministic` to `checker-judgment` mid-decomposition, because C-9 made its clause set no longer all-script. That was an audit finding, not a misjudgment of the work.

## Disputes

None. No worker contested a verdict.

## Crossings, and what #34 should take from them

Six dispatched, on judgment rubrics throughout—no deterministic clause crossed, so none agreed by construction.

| task | outcome | unique findings |
| --- | --- | --- |
| T-001 r0 | fail, agreeing with the record | 0 either way |
| T-001 r1 | pass | 0 either way |
| T-002 | pass | 0 either way |
| T-003 | blocked, lane timeout | no data |
| T-004 | blocked, identity mismatch | no data |
| T-005 | pass | 0 either way |

Zero unique findings in either direction across four completed crossings. Three things qualify that zero.

**The lane cannot currently produce a verified crossing.** Two crossings received `model: "gpt-5.6"` where the adapter pins `gpt-5.6-terra`. T-001 r0 persisted the unverified value into the corpus; T-004 refused it and blocked, which is what the role requires. Both cannot be right, and read together they locate the defect upstream of either: the vendor returns a string the lane does not expect. A courier that verifies strictly blocks every crossing; one that does not books opinions under an unconfirmed model. Nobody kept the raw response, so the cause is still unknown. Until this is settled, every `-codex` verdict in the corpus is a claim about which model spoke that nothing checked.

**Agreement bought less on some clauses than others.** T-002's clauses were about process behavior under constructed state; the in-family checker ran 26 subprocess confirmations, and the courier—which relays judgment and executes nothing—had no way to build a fixture that could falsify what it was handed. It agreed. That is the same finding `openQuestions.md` records about deterministic clauses, from the other side: not that the far side agrees by construction, but that it has no independent means to disagree. T-003's C-9 was the opposite shape, a pure reading task needing no repository access, and its lane timed out. The evaluation lost its best available crossing to infrastructure.

**One crossing chose a better method than the in-family check.** T-001 r1's courier inspected the predicate's AST and confirmed no lane literal appears anywhere in it—a stronger guarantee of the host-lane property than the four-cell matrix the rubric asked for, which proves behavior at four points where the AST check proves shape everywhere. It was not a unique *defect*, so it does not move the rate #34 turns on. #34 should decide deliberately whether that kind of value counts, because a defect count cannot see it.

## Check-infra debt

**A verdict's authority is its filename, and nothing validates that.** T-001's courier—dispatched for T-001, having already completed it—wrote a verdict, a rendered sibling, and a vendor-ledger row for **T-002**, explaining that it was satisfying a gate message. No dispatch authorized it (`dispatches.log` has no courier row for T-002) and no vendor call backs it (the row books `duration_ms: 0`, null tokens). Left alone it would have discharged T-002's debt by filename and entered #34's corpus as a crossing that never happened. Both files are in `state/quarantine/`; the ledger row stays, because rewriting a ledger is what `ledger-append.py` exists to prevent and a false row that stays visible is better evidence than a tidy one.

`subagent-return` validates a courier's verdict when *that courier* returns. A file written under another dispatch never meets that gate, and this job's predicate then trusts it.

**Three ledger rows carry invented values.** The unauthorized T-002 row and T-003's timeout row both book `duration_ms: 0` for calls that took real time; T-003's also carries a suspiciously round `started_at`. `ledger-append.py` is explicit that null means unreported and zero is never invented. The three later crossings booked honest rows—but only because the dispatch prompt named the earlier fabrications. The fix lives in an orchestrator's memory, not in the role.

**The gate this job shipped guarantees the wrong half.** A `blocked` verdict discharges a debt, and the courier writes that verdict about itself. Nothing distinguishes "the lane timed out" from "the courier never called the lane." So the mechanism guarantees an absence is *recorded*, which is what #100 asked for, and does not guarantee a recorded crossing *happened*, which is the property #34 actually needs. The obvious tightening is to require a ledger row for the stem before a `blocked` verdict discharges anything, mirroring the ledger-before-sentinel ordering the quota path already enforces.

**The livelock backstop fired nine times, every one of them wrong.** The digest is task tuples plus verdict filenames, and neither moves while a subagent runs. Every `STALLED.md` this job wrote was written over healthy in-flight work, and each had to be deleted by hand. Same blindness as #111 and #108, now with a hard count.

**The stop gate does not read `deps`.** It advised dispatching executors for tasks whose dependencies had not completed, on nearly every turn. An orchestrator that checks `deps` itself is unaffected. One that follows the advice builds against code that does not exist yet.

**One stale quota sentinel.** T-001's first crossing hit a quota signal, wrote `state/exhausted/codex`, then retried past it and succeeded—contradicting the contract's explicit no-retry-on-quota ordering. The lane was marked dead while provably alive, which would have denied every remaining crossing. Cleared by the user.

## What the constitution missed

**The repo's commit convention.** C-10 bound the humanizer audit, hard-wrapping, attribution trailers, and WHY-over-WHAT, and said nothing about conventional-commit prefixes—which `conventions.md:52` and `AGENTS.md:53` both mandate and all 84 commits in history follow. Three commits shipped without one and had to be rebuilt. A clause that governs commit messages should cite the repo's own convention rather than re-deriving a subset of it.

**Nothing bound the orchestrator's sequencing.** Two of this job's errors were mine and no clause could have caught either: incrementing `retries` while a courier was in flight, so it filed its verdict at the r1 stem for an artifact it judged at r0; and committing T-001 before its crossing settled, deviating from the cadence the preamble states. The first corrupted a row in #34's corpus until it was refiled. The constitution governs artifacts well and the orchestrator's own ordering not at all.

**C-3's own text was wrong about the mechanism it describes.** It said the sentinel keeps a fire from reading as a "fourth identical strike" where `STALL_LIMIT = 3` and a counter starting at 1 make it the third. T-002's checker caught it and ruled for the worker's commit message over the clause. Corrected mid-run.

**C-9 had to be invented after the decomposition audit.** The original C-1 asserted that C-2, C-3, and C-4 would catch vacuous tests. They run on earlier tasks, before any test exists. The lesson generalizes: a clause that discharges its own gap by pointing at other clauses should name the task each of those clauses runs on, because "some other clause covers it" is checkable and usually false.

## For the next Phase 0

- Budget for auditor rounds. Four of six catches came from there, and two clauses passed r1 only to fail on the decomposition audit that read them against real tasks.
- Cite the repo's conventions by reference in any clause about commits or prose, rather than restating part of them.
- If a clause claims another clause covers something, name the task and the phase that other clause runs in.
- Write a clause for orchestrator sequencing if a job's artifacts are keyed on mutable task fields. Verdict stems are built from `executor_model` and `retries`, and both are the orchestrator's to change at will.
