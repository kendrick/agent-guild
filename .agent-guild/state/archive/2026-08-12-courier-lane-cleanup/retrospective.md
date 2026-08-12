# Retrospective: Courier-lane cleanup (#106, #128, #47 + #116)

Nine tasks, thirteen commits, 31 dispatches. Every checker of record returned PASS on the first attempt: no retries, no escalations, no disputes. Twenty-two verdicts on disk, eight of them FAIL.

## The Catches

All eight FAILs landed on the orchestrator's work or came from the advisory lane. Not one turned back a worker.

Five came from the auditor. The constitution took three rounds and the decomposition took two.

The one that earned the whole apparatus was DEC-audit r0's blocker against T-008. As originally scoped, that task required per-attempt figures in the payload `claude-courier.py` returns. `subagent-return.py` validates that payload by exact key set twice over, so every route to the deliverable tripped a comparison and the hook would have blocked the courier's return. The crossing then never gets promoted, the debt never discharges, and the Codex-host lane stops working in the field, with every test still green, because both consumer fixtures hand-build their payloads instead of calling the courier. C-15's own check would have passed on precisely the artifact the hook rejects. Nothing in the constitution could see it. The auditor found it by reading `subagent-return.py` rather than the task file, split the work on the courier boundary, and gave the validator an owner. T-009's checker later confirmed the fix was load-bearing with a negative control: the real payload against the pre-widening validator is refused.

The other four auditor FAILs were the constitution failing to be checkable. Round 0 found three path guards built on `git diff main...HEAD`, which is empty whenever work is uncommitted—the state a checker sees the moment a worker returns. It demonstrated both vacuous-pass states on a throwaway clone rather than arguing them. The same round found C-5 instructing `checker-judgment` to revert edits in the working tree, which that role forbids; an honest checker would have returned `blocked` every round. Round 1 found my fix for that had moved the defect rather than closed it, because `git clone --local` carries committed state only and the mutation venue could not contain the work it was sent to mutate. Round 2 found the fix for T-001's C-10 misattribution had closed one hole by opening another: scoping the clause per task dropped it from six tasks that produce commits, so T-001's message ended up judged by nobody.

That last one is the pattern worth naming. Three of my five audit failures were fixes that relocated a defect instead of removing it, and the auditor caught each because it re-ran the probe rather than reading the diff.

Three more FAILs came from the courier lane, none of which changed a verdict. Those are covered below.

## Where the Work Strained

Nowhere on the worker side—and that deserves suspicion rather than satisfaction.

Nine tasks, nine first-attempt passes, zero retries. The benign reading is that the task files were good. DEC-audit forced the traps into them before dispatch, so T-004's worker was warned that the suite would go red before it wrote a line, and told the fix was the fixture rather than the filter, which is C-13's own failing example. The worker avoided it. That is decomposition doing its job.

The unflattering reading is that the checks were too easy, and the evidence runs against it. Checkers falsified rather than inspected. T-003's rewrote the single-lane discharge as an any-lane version and observed one case go red while another stayed green, which a both-lanes implementation with a matching test could not produce. T-004's substituted `in` for `startswith` and watched the same six cases fail as under a full revert. T-009's ran the emitted payload through the real hook process and confirmed a poisoned payload gave exit 2, so exit 0 meant acceptance rather than a silent no-op. None of those is a rubber stamp.

The strain moved to Phase 0 instead—five audit rounds against my own artifacts, against zero rework across nine workers'.

## Disputes

None. No worker contested a verdict.

## Check-Infrastructure Debt

`test_codex_courier.py` aborts under a `None` outcome, and two tasks failed to fix it. T-002's checker hit it first and evaluated its cases in isolation to work around it. T-008 was assigned the guard, guarded the site its task file named, and its checker found the suite dying identically ten lines earlier at a site nobody had named. T-009 guarded that one, and its checker found the run now reaching 18 checks and 13 real assertions before dying at a third site. Five remain: 505, 507, 795, 797, and 809. Guarding named sites one at a time loses to a file with several, so the next attempt should sweep it.

`test_ledger_append.py` fails hard rather than gracefully. Under two of T-007's mutations the suite raised `FileNotFoundError` at an earlier happy-path case and never reached the cases those mutations targeted. Its checker isolated them by running their predicates directly. Same class as the above, different file.

Both matter more than they look. C-5's mutation arm is the clause that establishes a test is genuine, and it works by breaking production code and watching a suite react. A suite that dies mid-run makes that arm unreliable exactly when it is being used.

## The Courier Lane

Six crossings, then three denied after the lane went down. 350,669 tokens in, 8,511 out, 268 seconds of vendor time. Three came back `blocked` and three `fail`, with no agreement reached with any checker of record.

Across the three crossings that returned judgments, the findings sort into two piles. The first is overlap, where the lane and the checker saw the same thing and graded it differently: the mislabelled AC 1 block on #106, the repeated "X rather than Y", the `discarded[]` forward reference. Every one was already caught in-family. The second pile is coverage claims the lane manufactured because it could not see what the checker was scoped to. It called C-7 unestablished on T-003 because a site went unjudged, and C-10 unestablished because the #106 comment went unread. Both were correct against the clause text and wrong against the task—and the vendor had no material with which to tell the difference.

The cause is the brief rather than the vendor. `compose-brief.py` assembles the constitution clause blocks and the `## Spec excerpt`, and never the task's `check_method`. So the far side reads a clause naming four sites, has no way to learn its checker was legitimately scoped to three, and reports the gap it can see. I tested a fix on T-005 by appending the `check_method` verbatim and saying plainly that a known gap was deliberate. The lane flagged the deliberate gap as a blocker anyway. The scoping note stops one failure mode and not the other, so it is worth doing without being sufficient.

Six crossings produced zero defect findings. Every unique lane finding was about evidence or coverage, and not one identified a fault in delivered code. Against that, the in-family checkers produced findings no brief could contain: the incomplete guard, the commit body that overclaimed because of it, the mutation arm that cannot independently kill one test case, and the sibling-prefix trap `agent-guild-other`. Those came from running things and watching where they died.

Two courier failures were the courier's own. T-004's crossing spent 124,687 input tokens, the most of the run, and returned `blocked` with an empty findings array, because the courier asked the far side to copy trees and run scripts. The vendor has no execution environment. That is the standing constraint for every crossing on this job—stated in the dispatch, and violated anyway. T-005's crossing, composed correctly, cost 21,283 and produced a real judgment. A correctly composed crossing is roughly a sixth the input cost of an incorrectly composed one. For a ruling that turns on cost against benefit, that ratio is the figure that matters, and it means the published cost for this lane is inflated by courier error rather than by vendor appetite.

The lane died on capacity and left no record of why. T-006's crossing got "selected model is at capacity"; the courier wrote `state/exhausted/codex` and denied every crossing after it. `vendor-call.schema.json` states that a `quota_event` line is always written before any exhaustion sentinel is touched, so the ledger always explains the sentinel. All six rows carry `quota_event: false`. The sentinel sits on disk with nothing accounting for it, which is the precise state that rule exists to prevent, produced by the one agent performing both halves.

The three denied crossings were the three the lane most needed. T-007 amends the shared ledger contract, T-008 and T-009 populate it, and T-009 repaired the Codex-host lane itself.

## What the Constitution Missed

C-10 was written from the constitution's idea of human-facing prose rather than from the standing user preferences it cites. Three separate checkers observed independently that its typographic rules do not reach code comments, and each passed on the clause text while saying the clause would need to say so. A fourth recorded that a commit body was hard-wrapped at 72 columns, which the user's preferences discourage and C-10 does not name. Each checker read the clause correctly. The clause was wrong: its enumeration of commit messages, the #106 comment, and C-8's docs is narrower than the preference it claims to encode.

A `blocked` verdict may carry no findings, and two did. T-004's crossing recorded `blocked` with an empty findings array and an empty rendered table. Nothing on disk said why, and the reason existed only in a return message no later reader of `state/` will have. This is the shape #100 and #141 closed at the authorization layer, still open at the content layer: an honest block is indistinguishable from a fabricated one. I closed it by instruction in later dispatches and T-006's crossing did record its reason, but instruction is not a gate, and the schema still admits the empty case.

C-5 cannot distinguish an unreachable mutation from an untested one. Two of T-008's mutations and one of T-009's survived, and in each case the checker established the mutation was semantically unreachable rather than uncovered. On a two-attempt crossing the only discarded attempt is the first, where the per-attempt and cumulative clocks nearly coincide. The clause asks whether a case goes red; it has no vocabulary for "this mutation could not have changed the answer." The checkers supplied that judgment themselves, correctly, but the clause did not ask for it.

Two `STALLED.md` false positives. Both times a checker was mid-flight with its verdict still coming. The gate counts blocked turns without distinguishing "no verdict because nobody dispatched one" from "no verdict yet because the check is still running."

The stop gate does not read `deps`. On a chained decomposition it demanded all pending tasks be dispatched every turn, which the dependency graph forbids. Roughly a dozen turns went to answering a question the gate could have avoided asking.

The worker and orchestrator status fight is real and has a specific cause. `subagent-return.py:434` accepts only `needs-check` or `disputed` from a worker and re-reads the file at return time, so a worker whose task the orchestrator has already advanced to `checking` cannot return cleanly and must rewind the field. I patched around it with a repair loop, which traded a silent state bug for a visible fight: T-007's worker spent real effort grepping the hooks to work out what was moving the field under it, and concluded correctly that something outside its own tool calls was responsible. The patch was mine. The defect is the ownership conflict.

Subagent returns are identified positionally. `_lib.id_from_transcript` returns the last dispatch in the parent transcript, so with four agents in flight the DEC-audit's return was attributed to T-002's worker and it wrote an `ERROR` record at a stem that was not its own. It checked the file was inert before writing and said so. Every dispatch after that ran serialized, which cost wall-clock the job did not otherwise need to spend.

## For the Next Phase 0

Four clauses to write differently:

- Scope prose clauses from the user's stated preferences, not from a summary of them. If a preference names code comments, the clause names code comments.
- Give the mutation clause a way to say "unreachable by construction," so a checker does not have to invent the category mid-check.
- When a clause is legitimately scoped per task, the scoping has to travel with the brief or the far side will report it as a gap.
- A path guard needs its precondition inside the check. Three of them failed open here because they assumed a state the checker never sees.
