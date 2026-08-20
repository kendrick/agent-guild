# Decision Log

Append-only; newest entry on top. Don't edit past entries; supersede them with a new one.

Each entry follows this shape:

```markdown
## 2026-04-19: Short title

**Source:** the commit, PR, or discussion it came from (optional for hand-written entries)

**Context:** Why this came up.
**Decision:** What was decided.
**Alternatives considered:** What was rejected, and why.
```

## 2026-08-20: Jurisdiction Is The Tracked Marker, Not The Directory

**Source:** #98 and #212, shipped as PRs #210 (v0.7.0) and #213 (v0.7.1, closes #212)

**Context:** Installing the Claude plugin at user scope fires the hooks in every repo on the machine. Two gates wrote state before checking jurisdiction—the stop gate's clean-slate branch and dispatch-guard's auditor path, which carries no task file to check—leaving partial `.agent-guild/` skeletons in repos that never ran init. The 0.7.0 fix guarded on `isdir(.agent-guild)`, and that read a leftover state tree as consent: init gitignores `state/*`, so `git rm` of every tracked payload file leaves the tree standing, and with it the gates kept writing (`stop-gate.state`, `dispatches.log`, an in-flight marker, `return-gate.log`).

**Decision:** jurisdiction is `isfile(.agent-guild/CLAUDE.md)`, tested by `_lib.guild_initialized()`; every gate returns 0 without it. The helper copies `paused()`'s never-raises contract, because `_lib.run()` turns any exception into exit 2 and a raise here would block the Stop of every session in every unrelated repo. `project_dir()`'s two-up fallback and `codex-hook-adapter.py`'s independent walk-up test the same file, so the predicates can no longer disagree about what an initialized project is. Gates with no reachable write today (`orchestrator-write-guard`) carry the guard anyway, for the shape. Every released payload back to v0.3.1 ships the marker, so no upgrade loses jurisdiction.

**Alternatives considered:** keeping the directory test (rejected—a repo had no way to decline a user-scope install except permanently gitignoring a file it never wanted; see [[antipatterns]]). Note for the suite: `fresh_proj()` now writes the marker and backs 104 setups; without it every gate returns 0 unconditionally and the suite passes while proving nothing.

## 2026-08-20: A Drifted Payload File Preserves And Continues

**Source:** #183 narrow cut, shipped as PR #211; the issue stays open

**Context:** `_preflight_payload` aborted the whole install when any existing payload file differed from source, before any copying ran. A project pinned to an older release differs by definition, so re-running init—the documented upgrade path—could never deliver the net-new files a release ships. 0.7.0 made it bite: first net-new payload scripts since 0.6.0, with the plugin-scope auditor role telling every CON-audit to run `check-baselines.py`.

**Decision:** conflicts preserve and continue. `_preflight_payload` returns the list, `install()` warns on stdout naming each preserved file, and the summary counts them in their own `preserved` term so "unchanged" keeps meaning matches-source. `_require_beneath` still runs over every file—the symlink-redirect guard has to see all of them. A drifted file still never upgrades in place; telling "you edited this" from "the guild moved" needs per-file provenance the installer does not keep, which is the half of #183 still open.

**Gotcha worth its own line:** `_copy_owned` (agents, skills, Codex project hooks) overwrites on every re-init; `_copy_missing` (the payload) preserves. The tree layout hides this—the Codex hooks sit inside `.agent-guild/` and look like payload. Nothing pins the upgrade half; flagged on #183 as the durable fix.

## 2026-08-20: Return Identity Reads The Hook Input, Not The Transcript Tail

**Source:** #206

**Context:** `id_from_transcript` ended on `tool_ids[-1]`—the right answer while dispatches are serial and a coin flip the moment a wave goes out in one message, the shape the contract requires. On #193 a checker and a worker went out together, the checker resolved to the worker's task, the wrong marker sat in-flight for the full hour, and the gate exited 0.

**Decision:** `ident_for_return` reads the hook input. It narrows by the returning agent's own type, then by that agent's child transcript (`<session>/subagents/agent-<agent_id>.jsonl`, layout confirmed against live session data), then by which dispatches are still in flight—strongest evidence first. It never refuses: an unresolved id becomes `_unidentifiable`, which exits 0, skips every check below, and logs that it guessed. Declining would switch the gate off on the exact shape every wave uses.

**Alternatives considered:** raising on ambiguity (rejected—a worse failure than the bug it replaced); ranking marker liveness above the child transcript (rejected—the one marker that survives a TTL is as likely the sibling's as the returner's). A test for that second change caught `(os.altsep or "")`, an empty string and so a substring of everything, silently killing the tier it guarded.

## 2026-08-20: Apparatus Is Diffed Across Rounds, Not Cached

**Source:** #198, shipped as PR #205; #122 closed. Settles the parked question in [[openQuestions]].

**Context:** the written entry condition was met—#193's run kept both DEC apparatus directories, two consecutive DEC rounds against unchanged constitution bytes. The evidence went to #198's side: DEC r0 settled R21's audit-id guard silently, in both its implementations, on the same axis r1 built both ways and filed against C-3. A silent settlement is only visible with the two directories side by side; a within-round sweep cannot catch a fork the round never saw as one.

**Decision:** a predecessor's apparatus is a comparand, never a starting point. Build your own first, open the predecessor only after, diff what was built from matching source, file material divergences against the clause in the within-round fork's shape, record agreement in one line. Materiality is decided by running the clause's harness against both readings—an axis it accepts both ways is the contract leaving it free. Scoping is per document via a `SOURCE.sha256` each round writes as it builds; a job-wide byte key was rejected because the CON stamp covers CON dispatches alone and task files move between DEC rounds while the clauses sit still, so it would either never fire or fire wrongly. Apparatus therefore stands until the job ends; teardown still deletes rather than archives (ownership stays with #200, venue enforcement with #118).

## 2026-08-20: The Mutation Clause Is Step-3 Guidance, Not A Per-Job Reinvention

**Source:** #156, shipped as PR #209

**Context:** `mutation` appeared nowhere in the kit, yet four archived jobs reinvented the clause that proves an instrument discriminates, and each omission cost audit rounds—the courier-lane C-5 took three just to find a legal venue.

**Decision:** constitution step 3 carries the family: venue and enumeration rules scoped to a working tree, the rule that a survivor is not automatically a finding, and the four recurring vacuity shapes. Step 2 gets the producer-side fork rule, since a contract you can build two ways is an audit FAIL and nothing told an author so. Two placement rules are load-bearing: venue and enumeration go in the check line so no checker infers them, and the survivor rule goes in the clause text, because a check line spelling out a conditional pass trips R9. Verified by writing a constitution against the guidance and linting it under both audit ids, not by reading the rules.

## 2026-08-20: Delegating Notes Are Proved Against The Schedule

**Source:** #190, shipped as PR #208

**Context:** a clause can hand part of its coverage to others ("this binds coverage, not correctness, which is why C-2, C-3, C-4 exist"). Whether the note is true is a fact about the schedule—a clause checked before the artifact it must read exists covers nothing—and #143 measured that catching one came down to where a round's attention landed.

**Decision:** R22 walks the graph: for each clause naming other clause ids, it resolves the tasks carrying each and fails when every named clause is carried only by tasks strictly upstream of the delegator's own carriers. Only `text` and `note` are scanned—`check` and `failing example` name ids for non-delegation reasons, and since R20 refuses a waiver against a proof, a false positive there would have no recourse short of `state/PAUSED`. Precision wins that trade at a stated price: a delegation written into a `check` field goes uncaught. First sweep found a real one, #117's C-1 leaning on a C-2 that never reads its cases; `_corpus.py` repairs the suite's copy and the archive stays as it shipped.

## 2026-08-19: A Lint Rule Announces Whether It Proved Or Guessed

**Source:** #139 (PR #202, 2026-08-17) and #193 (PR #203, 2026-08-19); answers the question [[openQuestions]] carried as settled

**Context:** `check-job-spec.py` has proving rules and inferring rules and blocked identically on both. Warn-only was already ruled out by #132—`dispatch-guard` reads stderr and discards stdout, so a non-blocking rule prints where nobody looks.

**Decision:** `RULE_CLASS` declares every rule's class in one place; a violation exits 1 when proved and 4 when inferred, class named in the `job-spec:` line, both still blocking. The recourse is a `**Lint exception**: R10 — <why>` line in the constitution's preamble, one per rule, guarded by R20, which refuses a waiver naming a proof rule, an unknown id, or no reason; whether the reason is honest is auditor judgment. The adversarial read caught two holes before ship: the waiver scanner skipped `scoped()`, so a commented-out waiver was a live one, and the waived-note record went only to stdout. #193 then fixed the worst heuristic edges: R10 walks past intervening modifiers keyed on no word list, new proof R21 fails a task routing a `checker-judgment:` clause to checker-deterministic (clause kind read from the constitution, not the task's paraphrase, and it runs ahead of every heuristic), and R2 quotes the anchor it matched instead of two bare line numbers.

## 2026-08-17: A DEC Round Runs Every Runnable Clause, And A Fork Still Fails Its Clause

**Source:** #196, shipped as PR #201

**Context:** The whole execution requirement sat under `## CON-audit`. `## DEC-audit` had three reading passes and nothing to run, even though both incidents behind #191 were DEC rounds acting past their charter. Two questions had to be answered to close it, and the first draft got both wrong.

**Decision:** A DEC round runs every clause whose check is a command and reads the `checker-judgment:` rubrics, the same boundary the CON section already drew. And a fork found at DEC still fails its clause, keyed `C-N`, with the task-level repair named alongside it.

**Alternatives considered:** Scoping execution to only the clauses the reading passes "reopen" (rejected—the test for reopened was true of every clause, since an excerpt is a compression of its clause and R6 refuses an orphan; and the archive said the opposite of what the proposal claimed, with r0 and r1 running all five runnable clauses). Routing a fork to `T-NNN` when a task excerpt could settle it (rejected after three attempts—`## DEC-audit` already says "File both, the re-cut and the clause," so the cheap repair was never being lost, and the paragraph below it names a clause left standing for the next decomposition as the harm to avoid). The cost objection to running everything was itself the declined cache argument returning by the side door, since [[the apparatus cache is declined]] on the grounds that rebuilding is a finding source.

**Note on method:** four adversarial rounds, and each of the first three found a merge-blocker the 320-test suite could not. The third invoked the conventions rule about cutting a mechanism two rounds have broken, which is what retired the routing. The section ended at +19 lines where the first draft was +43.

## 2026-08-16: The Apparatus Cache Is Declined, Because Rebuilding It Is A Variance Oracle

**Source:** #122, partially shipped as PR #199; the alternative filed as #198

**Context:** #119 told the CON-auditor to build a reference implementation and run every clause's harness against it, and never said how many times. `kendrick/skills#27` built the same one six times inside 107 minutes. #122 read that as waste and proposed caching it.

**Decision:** don't cache. On `kendrick/dotfiles#19` two consecutive rounds rebuilt the same harness and disagreed about `$STUBS` placement and `PATH` prepend-versus-replace, and both disagreements were real constitution blockers no reading had caught. That divergence is a variance oracle: it surfaces ambiguities nobody thought to write a control for, and those cannot be enumerated in advance, because if they could the clause would not be ambiguous. Two supporting reasons. #191 binds the fork sweep to transcription, so a round reusing an artifact transcribes nothing and its sweep has an empty domain. And build-is-a-check is anti-correlated with cache hits, since a CON round N+1 exists precisely because the constitution just changed, which is when re-asking "is this still buildable" has the most to say.

**What shipped instead:** the venue rule — a throwaway repo goes in its own `mktemp -d`, never under the apparatus path, which is what the role actually instructed and what let one fixture break a whole repo's chezmoi rendering; round-scoping now carrying its reason rather than reading as reclaimable housekeeping; and apparatus named as the archive's explicit exception, deleted at teardown because `archive/` is tracked.

**Alternatives considered:** moving a persisted apparatus outside the repo (rejected — no job identity exists in the kit, `CON-audit-r0` is the same string in every job, and there is no precedent for a persistent out-of-tree path); keying reuse to a per-artifact digest (rejected, see [[antipatterns]]); a two-sided control carried by the cache (rejected — a control the harness's author writes is not independent of the harness's own misconception).

**Measured, across eleven archived runs:** 29 CON rounds, 20 DEC rounds, 9 DEC rounds after the first. Seven of the eleven have no round a cache could have helped, and four of the nine belong to #117 alone. Both issues now park on a written entry condition (see [[openQuestions]]).

## 2026-08-16: A Harness Red Against Everything Reported As Discriminating

**Source:** #191, landed as PR #197 (`d41cf9a`)

**Context:** #119's discrimination test asked only whether a harness stays green against a deliberately-broken variant, never whether it goes green against something correct. A harness red against *everything* satisfied that test and reported as discriminating. #182 named the blindness while scoping itself out of it, closing its non-goals with "#119's auditor prose remains the only coverage for a check that is red when it should be green." The prose did not carry it.

**Decision:** the auditor runs every check against the reference implementation it built and expects green, and a clause clears that section on green-then-red and on nothing else. A harness red against a faithful implementation fails its clause, named as a distinct defect from one that stays green against a variant: that check accepts too much, this one accepts nothing at all and no worker can ever satisfy it. The build step gains the matching case — a contract you can build two ways is the same finding as one you cannot build at all, and the sweep for it runs by enumeration over every clause transcribed rather than where the wording looks slippery.

**Incident:** `kendrick/skills#27` CON-audit-r2 found a check whose own setup truncated the record it then asserted against, so no conforming stamper could pass it while its headline pass string printed anyway. It was caught only because that auditor ran the check against a conforming reference implementation it wrote itself.

**Known limit:** the section is nested under `## CON-audit`, and both incidents that motivated the change are DEC rounds where the auditors built past their charter on initiative. Filed as #196.

## 2026-08-13: A Dep Is Ready When Its Worker Returns, And Invalidation Latches On Retry Counts

**Source:** #135, landed as #178

**Context:** A dependent waited for its dependency's verdict when what it needed was the artifact, which exists the moment the worker returns. Remeasuring the #117 archive before writing any code killed most of the issue's own numbers: "40 of 133 subagent-minutes" does not reproduce (that run is 166 minutes), nor does "646 seconds to 374" (the measurable leg is 696). The 30% ratio does reproduce, at 29.6%. #167 had already taken most of the prize, couriers being 26.1 minutes of critical path, leaving roughly 8.5 to 15.5 depending on one placeholder timestamp. Both of the issue's stated dependencies were gone: #134 closed infeasible, #136 closed not-planned.

**Decision, the predicate.** A dep satisfies if it is `complete`, or at `needs-check`/`checking` with every one of its OWN deps complete. That second clause derives the one-level cap with no new field: on a chain, nothing ever stands on two unverified artifacts at once, while the chain still collapses progressively. Diamonds need no special code, since the predicate is per-dep. The rule lives in `ready-set.py` as `dep_unmet_reason`/`unmet_deps` and `dispatch-guard` imports it by path, because the wave advises and the gate enforces and two derivations of one rule drift.

**Decision, no snapshot.** The issue's `git stash create` rollback was cut with the user's agreement. Rework already re-dispatches over the existing tree with no restore, and an invalidated descendant is that same situation with a different source of diagnosis. The issue's own design also has an unsolved case: restoring a whole owned file from a pre-wave snapshot reverts the dependency's later writes to that file, which #133 makes legal precisely because the two are ordered.

**The invalidation signal has to be latched, and this is the part that took two tries.** The first design derived it from the dependency's current status and argued statelessness as a feature. It is the defect: the ladder walks `rework` → `assigned` → re-dispatch and the worker returns the task to `needs-check`, all inside one turn, so a status-derived signal can vanish before any gate sees it. `task-status.py` now stamps `built_on` when a task moves to `assigned`, pairing each dep with that dep's retry count at the one moment that means anything, just before the worker reads those artifacts. Counts only move forward, so the comparison holds until the descendant is dispatched again, which is the only event that should clear it.

**`complete` stops being terminal, narrowly.** Invalidation has to move a descendant that already passed its own check, and the transition map had no edge: `complete` had no successors and `needs-check` reached only `checking`. Two edges now exist. Removing `complete` from `_lib.TERMINAL` was considered and rejected outright, since that set drives the stop gate's turn-holding and every finished task would keep its job alive forever; the gate surfaces attention entries for closed tasks instead.

**Alternatives considered:** holding a task at `checking` until its deps cleared, to keep the `complete` → `rework` edge rare (rejected, and the claim that justified it was false: a dep satisfies clause 2 only once its own deps are complete, so a task's completion is what releases its grandchildren, and sitting on a landed PASS stalls the chain speculation exists to unstall); a frontmatter marker set at invalidation time rather than at dispatch (rejected, it records the wrong moment); deriving invalidation from verdict files (rejected, it would make the wave a function of `verdicts/` and break the pure-function-of-task-files contract that keeps two hosts computing identical waves).

## 2026-08-13: Wave Count Is The Wrong Unit For The Wave Path's Own Claim

**Source:** #169, landed as #177; refined by #178's second replay leg

**Context:** v0.5.2 rests on waves beating serial dispatch and nothing tested it. #134 carried the criterion and was closed without it because the driver it named was infeasible, but the criterion never needed that driver: `ready-set.py` is a pure function of task files plus `--running`, so the replay runs offline.

**Decision:** the archived #117 graph is replayed through the real CLI, and the corpus is given `owns` by the same `add_owns` the linter suite uses, extracted to `_corpus.py` so one derivation serves both. Replayed without it, every pair reads as `owns-undeclared` and the result is seven waves of one, reproducing exactly the serial behaviour the test exists to disprove while appearing to pass.

**The metric was wrong the first time, and the failing test is what said so.** A speculative leg asserting fewer waves failed: both rules produce the same six waves in the same order, because the graph decides how many dependency layers there are, not the rule. What speculation changes is the waiting between them. Counting turns instead, with the `checking` turn the contract's own loop describes, the same composition takes 12 turns under the old rule and 8 under the new one. The turn count is pinned so a regression shows up as a number rather than as a wave shape nobody can tell apart.

**Six waves, not five.** T-004's only artifact is a `~/repos/...` path, so its cloned `owns` entry is a tilde path `owns_entry_problem` refuses, and it rides alone rather than pairing with T-002. That deferral is asserted by kind so the pinned composition reads as a consequence rather than a snapshot somebody later "corrects."

**Alternatives considered:** deriving `owns` a second way for this suite (rejected, two derivations drift and the fixture would agree with itself about the wrong thing); weakening the wave-count assertion to pass (rejected, the failure was the finding).

## 2026-08-13: Both Audits Gate, And A PASS Names The Bytes It Approved

**Source:** #110 and #161, closed together on `fix/audit-gates-161-110`

**Context:** Phase 0 audits the constitution and Phase 1 audits the decomposition, and neither verdict did what the contract implied. `con_audit_passed()` scanned the verdicts directory for any `CON-audit-*.md` reading PASS and returned on the first hit, so a constitution revised after approval kept dispatching workers and a later FAIL never revoked an earlier PASS. Nothing read a DEC-audit verdict at all. The open question [[openQuestions]] carried about whether a failed DEC-audit should gate anything is answered here.

**Decision, #161: gate it.** A bad decomposition doesn't announce itself. Workers build the tasks that exist, checkers pass them against real clauses, and the spec section no task covered is never built while every verdict in the job stays green. Coverage is the one property nothing downstream recovers, because a checker only ever verifies the task it was given. The other reading on the table, declaring DEC-audit advisory in the contract, was rejected: an audit whose verdict can't stop anything is a memo, and this one guards the failure no other check can see.

**Decision, #110: bind the PASS to bytes, and count only the latest round.** Both gates now run through one `audit_gate()` helper. A newer FAIL closes a gate an older PASS opened, and the CON gate additionally compares the constitution's sha256 against a stamp recorded for the approving round. Content and not mtime, so a no-op save costs nothing.

**The stamp's timing was the whole design, and the first answer was wrong.** Writing it when the auditor returned looked obviously right and failed twice. An auditor that returned without writing a verdict re-stamped the *previous* round with whatever was on disk, so the gate came to mean "an auditor round-tripped" rather than "this text was approved"—the exact defect #110 was filed about, rebuilt inside its own fix. And a Codex auditor runs read-only and returns its verdict for the orchestrator to persist, so on that host the stamp was never written at all and the gate could never open. Both went away by stamping at dispatch instead: `dispatch-guard` fingerprints the constitution it is sending the auditor to read, against the round the auditor is about to write. Only a commissioned round carries a digest, and the moment is one both hosts share.

**Fail closed on a missing stamp.** Nothing distinguishes a PASS that predates the mechanism from one whose stamp was deleted, and the recovery is a single audit round on a path that is never gated. The gate also reads the artifact before the stamp, so a constitution that went missing is reported as missing rather than as unstamped, which would send you to re-audit a document that isn't there.

**Alternatives considered:** the auditor writing the digest into its own verdict frontmatter (rejected—a verdict belongs to the agent that wrote it, and hook-computed arithmetic can't be transcribed wrong); grandfathering unstamped PASS verdicts (rejected, above); stamping DEC-audit too, so a future staleness rule would have data (rejected—task files change status all job long, so a digest over `tasks/` goes stale on the first transition, and a normalized digest is a decision nobody has made yet).

## 2026-08-13: A Trailing Slash Is Notation, And The Build Is A Serialization Point

**Source:** #162 and #164, closed together on `fix/162-164-owns-accuracy`

**Context:** `owns` is what makes a wave safe, and half of #162 had already landed (`e6212da`): an undeclared `owns` rides alone. What remained was that nothing validated an entry's shape, and that `paths_overlap` answered False for `src/lib` against `src/lib/`. #164 was the neighbouring gap: the wave modeled file ownership and nothing else, so two tasks editing disjoint sources could both run the build over the same output trees.

**Decision, #162.** `owns` stays optional at the linter. The wave-refusal mechanism already makes an absent claim safe, so requiring the field buys nothing and would retroactively fail all 40 archived task files, none of which carries it. R15 validates only the entries a task declares: `./`, `..`, absolute, `//`, backslash, globs, `~`/`$`, invisible characters, and (with a repo root) an entry whose spelling contradicts what's on disk. `paths_overlap` now treats the trailing slash as notation, so two entries overlap when they name the same node or when either is a parent of the other, tested at a separator. `ready-set.py` re-checks the textual half every turn under a new `owns-malformed` deferral kind, since a task file can be hand-edited after DEC-audit.

**The fix went in the wrong place first.** The initial cut put it all in R15's filesystem check, which only fires once the owned directory exists—and a task's job is usually to create it. Adversarial review caught that with a reproduction: two tasks, nothing on disk, one wave, and the reason string still claiming owns had been checked. The lesson generalizes: a validator that needs the world to already contain the thing being validated is the weakest possible place to enforce a property about creation.

**Decision, #164.** The collision is the build RUN, not the build-input EDIT. R16 requires one terminal regenerating task per job and refuses two regenerators with no dep path between them. The issue's literal wording (two build-input editors can't share a wave) was rejected outright: nearly every task in this repo edits `guild-core/` or `.agent-guild/`, so that rule would serialize every wave and give back what #125 bought. What no linter can prove—that a worker didn't run the build anyway—moved into the three worker roles as prose. The five concurrent append sites are documented as relying on O_APPEND rather than locked.

**Where the line between normalizing and rejecting falls.** `paths_overlap` normalizes exactly one thing, the trailing slash, because that's the only difference where both spellings still name the same node and the comparison can say so from the strings alone. Everything else is refused upstream instead. `./src/a.py` could be normalized too, but half the malformed spellings (a directory missing its slash, a slash on a file) can only be judged against the tree, and a predicate that silently repaired some of its inputs while other callers refused the rest would be the harder thing to reason about.

**Alternatives considered:** teaching `paths_overlap` to normalize every spelling difference (rejected, above); a sentinel spelling for "this task writes nothing" (rejected—an unverifiable promise, and it buys a wave seat for a task that blocks no peer's paths anyway); wiring `check-diff-scope.py --task-file` into a hook (rejected and the flag removed—under a wave the dirty tree mixes every in-flight task's writes and nothing can attribute one to a task, so a per-task run flags its peers).

## 2026-08-13: The Second Opinion Becomes Opt-In, And The Crossing Debt Goes

**Source:** #167, implementing #34's closure; landed as #170 + #171

**Context:** #34 measured cross-family checking over 69 crossings in three repos and ruled the bet does not pay: 2 real defects against 102 findings both sides reached independently, and 45 of the 46 in-family-only findings came from executing something or reading a repo path the courier's brief never carried. The advantage was tool access, not vendor diversity. The ruling said `checker-courier` "stays only as free capacity" without saying what that meant in the contract, which still opened its dual-check section with an expiry that had already passed.

**Decision:** The courier is opt-in. Nothing auto-dispatches it, the crossing debt is retired along with the four files that discharged it, the retrospective reports only crossings that ran, and the lane's plumbing stays wired for a future experiment on a different vendor. All 85 ledger rows are `gpt-5.6-terra`, so #34 ruled on one model rather than on cross-family checking in general.

**The sequencing was the trap.** #170 (prose) and #171 (code) were filed to land in that order, and they can't. `second_opinion_debts()` derived a debt per verdict-of-record file on disk, never from the contract, so deleting the prose first would have left the stop gate demanding crossings nothing explained and pointing at a `.denied` waiver the contract had just removed. They went in one branch, code first.

**What survives, and why.** `crossing_stem`, because an opted-in courier's verdict still lands at the lane-suffixed stem. `exhausted/<lane>`, as the lane's quota sentinel minus the debt framing. And #100's foreign-stem guard, re-based from the reservation records onto the in-flight marker: a courier writing a sibling task's verdict is still possible, and the marker is the same legal-dispatch signal with none of the bookkeeping.

**Alternatives considered:** Removing the lane outright (rejected—the corpus's one `changed_verdict: yes` came from a crossing that blocked, and a different vendor is a new experiment that shouldn't have to rebuild this); keeping auto-dispatch as advisory with no debt (rejected—it bills 30s and 37k input tokens per judgment crossing, with a 28% failure-to-produce rate, for data nothing consumes).

## 2026-08-12: The Stall Backstop Now Counts Per Task, Not Per Job

**Source:** #163

**Context:** `stop-gate.py`'s livelock counter was one digest+count pair for the whole job, and #111's in-flight hold was an `any()` over every open task, so one live subagent froze the counter for every other task. A task stuck at `disputed` sat at count=1 through eight blocked firings while a sibling churned beside it, and Phase 2 nearly always has something mid-flight, so the backstop was effectively off for its whole length.

**Decision:** One counter per open task, one per held courier debt, keyed in `state/log/stop-gate.state`'s `entries` map (`T-NNN`, or `debt:<stem>-<lane>`). The trip condition flips from global stasis to per-entity neglect: three blocked continuations in which the orchestrator never touches one particular task, while doing real work elsewhere, now stall that task on its own schedule. `STALLED.md` names only the entities that actually tripped, instead of every open task and every held debt.

**The likely first surprise.** A held courier debt is the obvious candidate to trip first: nothing about a debt changes until it's discharged, so its digest is constant by construction and it advances on every firing that doesn't hold it. A task genuinely waiting on a dependency is exempted by the deferral hold (see the companion entry on #125's narrowed promise, below); an outstanding debt is not, and was never meant to be—it's supposed to get dispatched.

**Alternatives considered:** Keeping the global counter and narrowing only the in-flight hold to per-task (rejected—the counter itself still moved in lockstep for every open task, so a live sibling would still reset everyone's progress every firing); scaling the strike limit to the number of open tasks (rejected—that reintroduces the crowding-out #163 was filed about, just at a higher number).

## 2026-08-12: #125's "Presentation Only" Promise Narrows On Purpose For The Deferral Hold

**Source:** #163, #125

**Context:** #125 gave `ready-set.py`'s `deferred`/`attention` buckets to `stop-gate.py` on the promise that they were presentation only, changing only how the block message reads, never whether the gate blocks. Per-task counters need more than presentation: a task deferred on an unmet dependency has no move available to it, and counting a blocked turn against it would stall a task nobody could have advanced.

**Decision:** A task in the `deferred` bucket holds its counter, but only for `kind: "deps"` and `kind: "owns"`. Two kinds are deliberately excluded. `"budget"`, because a spent retry budget is retry-ladder step 4 (escalate a tier, re-decompose, or hand the task to the user), an orchestrator judgment exactly like `disputed`, and holding it would wedge a job whose only open task sits at a spent budget with no backstop. And `"owns-undeclared"`, which adversarial review caught after the first version shipped it as a hold: ready-set defers an undeclared task against every id in `--running`, and `owns: []` is what `templates/task.md` ships, so holding it let one live subagent freeze every other pending task's counter. That is #163's own bug relocated from the marker hold to the deferral hold, and the remedy ready-set names in its reason string ("declare it on both") is an orchestrator action, which puts it alongside `budget` rather than alongside a real wait. The buckets still never decide *whether* the gate blocks, only how fast a counter climbs, so the load-bearing half of #125's promise survives; the "never touches behavior" half does not.

**The fail-loud reason this is acceptable.** A missing, slow, failing, or too-old `ready-set.py` (no `kind` field at all) empties the deferred set entirely, which makes every task eligible again and can produce a `STALLED.md` a waiting task didn't earn. That's chosen deliberately over the alternative, which would quietly suppress the backstop and rebuild the exact silent hole #163 was filed about. A spurious `STALLED.md` costs a few minutes reading a file; a silently disabled backstop costs nobody noticing a stuck job for as long as it stays stuck.

**Alternatives considered:** Holding every deferred kind including `budget` (rejected—deadlocks a job whose last open task is budget-deferred, with no backstop left to catch it); degrading a broken `ready-set.py` to "hold everything" rather than "hold nothing" (rejected—that's the silent failure mode #163 exists to close off).

## 2026-08-12: An Unidentifiable Subagent's Marker Is Left For Its TTL, Not Guess-Cleared

**Source:** #163

**Context:** `subagent-return.py` clears a task's in-flight marker on every resolved return, so the stall backstop doesn't mistake a finished checker for one still running. Two of its three "can't identify this subagent" paths (a missing or unreadable `transcript_path`, or no id readable from one that is) reach that point with no task id at all, so there's nothing to key a targeted `clear_in_flight(ident, agent)` call against.

**Decision:** Leave those two paths' markers in place rather than clearing by glob. The only alternative is `*--{agent}.json`, and a wave routinely runs several tasks under the same agent type at once, so that glob would delete a live sibling's marker along with the dead one, telling the stop gate a genuinely running subagent had finished and pushing it toward a spurious `STALLED.md` on healthy work. A leaked marker is bounded by `AGENT_GUILD_INFLIGHT_STALE_S` (an hour), and per-task counters mean one leak now costs only that one task's backstop for the TTL, not every task's. The third caller, a task id it can read with just no task file at that id, clears its own marker before falling through to the same logging, since it has an exact key to clear.

**Alternatives considered:** Globbing `*--{agent}.json` on all three blind paths (rejected—kills a live sibling's marker under ordinary wave concurrency); adding one global "something went unidentified" flag to suppress the backstop entirely (rejected—trades a bounded, localized leak for an unbounded one that also hides every other task's real stalls).

## 2026-08-12: An Undeclared `owns` Rides Alone Rather Than Deferring

**Source:** #162 half A, `09cff3e`, shipped inside #165; comment recorded on #162

**Context:** #133 gave tasks `owns` and the wave uses it to keep colliding writers apart. But `_owns_overlap` returned False whenever either side was empty, and `owns: []` is what the template ships, so the default task was the unchecked one. The wave grouped tasks nobody had compared and printed "no owns overlap" as the reason.

**Decision:** Two tasks share a wave only if both declare `owns`. A task declaring none still dispatches, alone. The reason strings now name what was actually compared.

**Why alone and not deferred.** Deferring every undeclared task looks stricter and is worse: in a decomposition that declares none, nothing would ever reach a wave, so nothing would ever dispatch and the job would deadlock behind a safety rule. Alone is the pre-wave behavior, so the failure mode of an unadopted field is losing the new speed, never losing the ability to run. That shape is worth reaching for whenever a conservative branch could stall a loop: degrade to the old behavior, not to a refusal.

**Why this half needed no decision.** The issue was filed whole because R13's opt-in scoping exists to keep archived corpora green. That constraint turned out not to reach `ready-set.py` at all: the script is new, no corpus runs through it, and no test asserted the permissive pairing. Splitting the issue on that line let the unsafe default get fixed before merge while the linter question stayed open on its own terms.

**Alternatives considered:** requiring `owns` at the linter now, rejected because it changes whether archived corpora pass and deserves an unhurried migration decision; fixing only the reason string, rejected because an honest label on an unsafe grouping is still an unsafe grouping.

## 2026-08-12: Guild Hooks Do Not Fire For Workflow-Spawned Agents

**Source:** #134 step 0 spike on `fanout-driver-and-gate-fixes`; comment recorded on #134

**Context:** #134 proposed driving Phase 2 from a `Workflow` script on a Claude host, with the script-and-prose driver as the shared baseline on both. The plan made the spike a hard gate: verify the guild's gates observe a workflow-spawned dispatch before building anything on top of it.

**The probe.** `dispatch-guard` refuses any dispatch to a `GUILD_AGENTS` member carrying no `Task-ID`, whether or not a job is active, so an id-less guild dispatch is a clean yes/no test that needs no job state. Dispatched `worker-bulk` with no id line from a workflow: it ran and returned. The identical dispatch through the Agent path was refused. No `dispatches.log` line, no in-flight marker: nothing ran, rather than something running and allowing.

**Decision:** The Workflow driver is not built. The script-and-prose driver is the sole driver on both hosts, and `.agent-guild/CLAUDE.md` now says so at the point where it tells you to dispatch a wave.

**Why this is worth writing down rather than retrying:** the failure mode is silent in the worst way. Such a driver would bypass `Task-ID` identity, the `executor_model` tier match, `reserve_crossing`, and the in-flight markers, and every gate would report green by never running. That is the same shape as #94 and #141, where work returned that no dispatch gate had authorized. Nothing about the wave depends on the Workflow tool: what was lost is an automatic executor, not the concurrency the milestone exists for.

**What would reopen it:** a way for hooks to observe workflow-spawned dispatches, or a documented statement from the harness that they are meant to. Until then this is unsafe, not merely unbuilt.

**Alternatives considered:** shipping the Workflow driver with the gates re-implemented inside the script, rejected because a second copy of the enforcement is the thing this repo's one-source build exists to prevent, and it would drift; treating the negative as a harness bug to work around, rejected because nothing here can distinguish "not yet supported" from "deliberately out of scope".

## 2026-08-12: An Adversarial Review Found Four Blockers A Green Suite Could Not

**Source:** opus review of `fanout-driver-and-gate-fixes` after all five Lane B commits landed; fixes in `c34bb85`; follow-ups #162, #163, #164

**Context:** Six suites passed at every commit and each lane's own agent verified its work. A review was run anyway, told to assume the branch was broken.

**What it found.** Every finding was in a state no test covered. The stop gate consumed only `ready-set.py`'s `wave` bucket and discarded `deferred`, `attention`, and `checks`, so a task with an unmet dep was told to dispatch its executor and a task with an abandoned dep was never surfaced at all. A `rework` task in the wave lost both mandatory steps of the retry ladder, because wave membership suppressed the per-task line. #108's ambiguity block fired on ids quoted inside pasted documentation while two ids of the same kind passed silently and resolved by position, which is the likelier mistake and the one that dispatches the wrong task.

**Decision:** Fix the four in the branch; file the three that are design decisions (#162, #163, #164) rather than improvise answers into it. The review also refuted one standing suspicion (the transcript-size hold is sound), which is worth as much as a finding.

**The lesson, which is about verification and not about this branch:** a green suite proves the states it covers, and every one of these defects lived in a state nobody had thought to write a test for. The two that mattered most came from the seam between two components that were each correct alone. Neither lane's agent could have caught them, because neither owned both sides. That seam is where an adversarial pass earns its cost, and it is the argument for running one against integration points specifically rather than against whole diffs.

**Alternatives considered:** shipping and letting the next real job surface them, rejected because the wave defects produce advice a well-behaved orchestrator would follow into a dependency violation; fixing all seven findings in-branch, rejected because `owns` enforcement changes whether archived corpora stay green, which is a decision to make deliberately rather than under momentum.

## 2026-08-12: Bound The Constitution, Not The Audit Loop

**Source:** #120 and #123 built together on `feat/audit-budget-job-weight`; three adversarial review rounds; PR #159

**Context:** Audits are 44-48% of a guild job's wall clock across three measured runs. #120 proposed a round budget and #123 a job weight that sizes ceremony. Both landed as contract prose, and the round budget was cut before merge.

**Decision:** Ship the weight and the clause ceiling; do not cap audit rounds. Weight is derived at Phase 0 from one discriminator (does verification need an instrument built, or one that already exists invoked?), adjusted upward for unattended blast radius, announced to the user in one line and overridable in a word. It sets a clause ceiling and nothing else. The ceiling is a budget the orchestrator may knowingly overrun with a reason recorded, not a gate.

**Why the round budget died:** measurement, not taste. Counting CON-audit stems on the three post-#132 runs, two of three exceed a deep budget of 3, and the round a cap would remove from the most recent run is where the auditor caught a constitution whose C-9 and C-2 made every worker fail by construction. [[antipatterns]] already said this and its precondition had been met; the numbers agreed with it anyway.

**What three review rounds cost and bought:** round 1 found the ship-with-minors exit deadlocked the job, because it produced no CON-audit PASS and `dispatch-guard` requires one. Round 2 found the fix for that was worse: a `## Carried minors` section landed after `## Clauses`, and `check-job-spec.parse_constitution` ends a clause block at the next `### C-N:` rather than at `##`, so a carried minor citing `path:line` failed R1 and hard-blocked every auditor dispatch. Round 3 found the surviving hand-off deadlocked Phase 1 instead of Phase 0, since no DEC-audit gate exists and `stop-gate` will not let the turn end while tasks are pending. Every critical finding across all three landed in the same feature. The rule that fell out: when two rounds find a blocker in one mechanism, cut the mechanism rather than patch it a third time.

**Not enforced by anything.** No script computes a weight, counts clauses against the ceiling, or reads the weight line. That is #160, deliberately deferred: the weight table was designed from two runs, so fixtures pinning it today would only confirm the design reproduces its own inputs.

**Alternatives considered:** re-deriving the budget numbers against the corpus (deep would need 5+, light 2+) and fixing the DEC hand-off with a PAUSED instruction—rejected because it keeps a feature the repo backed out of once, on a sample of eleven runs; patching ship-with-minors a third time—rejected on the two-rounds rule above.

## 2026-08-12: A Deterministic Clause Never Crosses, And The Brief Is What Limits A Second Opinion

**Source:** the courier-lane cleanup run (#106, #128, #47, #116), nine tasks, PR #155

**Context:** #128 held that a script-checked clause crosses to the courier lane as pre-run output the far side can only agree with, so the crossing costs a vendor call and returns nothing. The run shipped that, and in doing so produced six crossings of its own that say something sharper about what the lane can ever contribute.
**Decision:** `compose-brief.py` keeps a cited clause only when its check value begins `checker-judgment:`, anchored so a script invoked with a flag containing the word is still dropped. A task citing only script-checked clauses has nothing to cross: exit 3, no brief written, and an orchestrator-written `.skipped` marker discharges the debt that would otherwise hold the turn open forever. The dual-check regime now reads "after every checker of record whose task cites a judgment clause."
**What the run's own crossings showed:** six crossings, three `blocked` and three `fail`, no agreement with any checker of record, and zero defect findings. Every unique lane finding was about evidence or coverage, and two of them were manufactured by the brief rather than found in the work: `compose-brief.py` puts the constitution clause text in the brief and never the task's `check_method`, so the far side cannot tell a legitimately scoped check from an incomplete one (#151). Appending the `check_method` was tested on T-005 and is not sufficient; the vendor overrode an explicit note that a gap was deliberate. Meanwhile the in-family checkers produced four findings the lane structurally could not reach, all from running suites under mutation, which is the `unique_checker_access_derived` measure #137 asked for.
**Cost, which #34 needs:** a crossing composed as complete evidence plus a question cost 21,283 input tokens; one composed as instructions the far side cannot execute cost 124,687 and returned nothing. Same lane, same day, same class of task. Any published cost for this lane is inflated by courier error unless the packets are known well formed.
**Alternatives considered:** demoting script-checked clauses to context in the brief rather than dropping them (rejected in the issue — a clause the vendor is shown but cannot act on is what produced the blocked crossings in the first place).

## 2026-08-12: The Decomposition Audit Is Where A Silent Contract Break Gets Caught

**Source:** DEC-audit r0 against the courier-lane cleanup decomposition

**Context:** T-008 as first scoped required #116's per-attempt figures in the payload `claude-courier.py` returns. `subagent-return.py` validates that payload by exact key set twice over, so every route to the deliverable tripped a comparison and the hook would have blocked the courier's return: crossing never promoted, debt never discharged, Codex-host lane dead in the field. Nothing in the constitution could see it — both consumer fixtures hand-build their payloads instead of calling the courier, so the full verification block stays green, and C-15's own check would have passed on precisely the artifact the hook rejects.
**Decision:** Split on the courier boundary. T-008 takes `codex-courier.py` and is forbidden to touch `_courier_lib.ledger_record`, routing its per-attempt data to `_append_ledger` as a separate argument. T-009 takes `claude-courier.py`, widens `ledger_record` and `subagent-return.py`'s key set in the same commit, and adds the `test_codex_adapter.py` case that would have caught the gap. The validator now compares against a required set plus `optional_ledger_fields`, which is the seam the next optional key appends to.
**Verified how:** T-009's checker built the payload by running the courier rather than constructing a dict, pushed it through the real hook process (exit 0 accepted, a poisoned payload exit 2), and ran a negative control against the pre-widening validator at `dcf6b04^` to confirm the refusal was real.
**Also decided, and left standing:** C-10's typographic rules do not reach code comments, and three checkers said so independently while passing on the clause text. The clause enumerates commit messages, the #106 comment, and C-8's docs, which is narrower than the standing preference it claims to encode. Not widened mid-job — overturning would fail workers against a rule the constitution does not state. It is next Phase 0's input.
**Evicted from activeContext here:** #127's block-scalar disagreement between `compose-brief.py`/`check-provenance.py` and `check-job-spec.py`. Nine tasks used folded `check_method` scalars throughout and it never bit; the disagreement stands, the urgency does not.

## 2026-08-11: A Model's Account Of Its Own Name Is Not Evidence Of Its Identity

**Source:** #142, with four live probes against codex-cli 0.146.1

**Context:** The verdict schema carries a `model` field, and the way it got filled was to ask the far side to echo back the string it had been handed. Over the #100 run that produced one verdict of record carrying `gpt-5.6` where the adapter pins `gpt-5.6-terra`, and one crossing blocked over the same mismatch, throwing away a `fail` with two major findings. Both are the same defect from opposite ends: a field nothing could verify was being treated as though something had.
**Decision:** The lane establishes `model`; the vendor doesn't. `codex-courier.py` passes `-m gpt-5.6-terra` and stamps that value onto the verdict on every path, which is what `claude-courier.py` already does on the reciprocal lane. What the far side echoes is compared and recorded—an `info` finding and the retained raw response when it diverges—and decides nothing. Three probes against codex-cli 0.146.1 back the design. The `exec --json` event stream carries no model anywhere (`thread.started` has only `thread_id`, `turn.completed` only `usage`), so there is no vendor-structural source to prefer over the flag. A bad `-m` fails loudly with a 400 instead of silently substituting, which is what makes the flag worth trusting. And `--ignore-user-config` keeps auth, so the lane stops inheriting whatever a machine-local `~/.codex/config.toml` happened to set. A fourth probe reran #142's own reproduction five times with `-m` and got the pinned string back every time, which is worth less than it looks: the prompt was two lines, where the crossings that mis-echoed carried full briefs and artifact text.
**Alternatives considered:** Accepting a set of strings, or a normalization rule (rejected—it leaves the corpus carrying two names for one model, and that corpus is the measurement #34 exists to take); blocking on any mismatch (rejected—that is the T-004 harm, a sound judgment discarded over a field that was never evidence in the first place).

## 2026-08-11: The Second Opinion Is A Debt On Disk, Not A Step Someone Remembers

**Source:** #100, built as a guild job under the gates it was changing

**Context:** The dual-check regime has been contract since #34 opened: every checker of record gets a courier crossing. Nothing ever read `state/verdicts/` to confirm one landed. On the two live matrices of 2026-08-02, Codex dispatched a courier after every checker while Claude ran a task to `complete` without one, and no gate objected to either—so the corpus #34 will rule on grew or didn't depending on whether an orchestrator remembered.

**Decision:** Make the obligation a predicate over files. `second_opinion_debts()` in `_lib.py` scans `state/verdicts/` for stems shaped `T-NNN-<tier>-r<N>.json` and reports each one still owing, per retry round, so a rework's `-r1` is its own debt rather than something the earlier round's crossing covers. Five routes discharge one: a `-codex` lane sibling, a `-claude` lane sibling, `state/exhausted/<lane>` for the lane `courier_lane(data)` returns and no other, a `…-<lane>.denied` waiver the orchestrator writes by hand, and a verdict of record that itself reads `blocked`. Pinning route 3 to this host's lane is what keeps a Codex host from discharging its debts off `exhausted/codex`, a sentinel its own lane would never produce. A record that can't be read or parsed owes, loudly—but only route 5 is foreclosed by that, since a lane sibling is the very file a courier writes, and refusing to look for one before declaring the record corrupt would strand a debt no dispatch could ever clear.

Two gates read it. `stop-gate.py` computes debts before its open-task early exit, which is the whole point: that exit drops terminal tasks, and 2026-08-02's failure was a completed task with no crossing. Its block message names the missing lane-suffixed file and `checker-courier` as the dispatch that writes it, its `checking` next-move line says to dispatch the courier before completing rather than the generic "act on the verdict", and debts join the livelock digest so an `exhausted/<lane>` sentinel—which lives outside `verdicts/` and is invisible to the verdict listing—registers as progress instead of a third identical strike. `dispatch-guard.py` admits a courier on a debt-bearing task whatever its status, courier-only and debt-gated, because a debt exists precisely when nobody has reopened the task to collect it.

**`blocked` is exempt, and not to save a call.** A verdict of record reading `blocked` means the in-family check never ran, so there is no judgment for a crossing to sit beside; a courier sent after it compares against nothing. The saved vendor call is a consequence of that, not the argument for it—if a blocked record carried a judgment, the crossing would be worth paying for.

**Alternatives considered:** Leaving the regime prompt-only (rejected—2026-08-02 is the experiment, run twice, and it failed once). Requiring `status: checking` of the courier as well (rejected—a debt survives into `complete` and `rework`, so the status a courier would need is the one it can't have; the stop gate would demand a crossing the dispatch guard refuses and every job would end at `STALLED.md`). Treating an unreadable verdict of record as owing unconditionally (rejected—it creates a debt nothing can discharge, since a second courier writes a path that already exists).

## 2026-08-11: A Script Proves the Paperwork Before an Auditor Reads It

**Source:** #132 and #121, shipped as PR #138 (squashed to `6570005`); follow-up filed as #139

**Context:** Six of #117's eleven audit findings were provable mechanically, and each one cost a full opus round at 300-550 seconds. The decision below is the first half of the #126 arc; #119, #120, and #122 all get cheaper once mechanical defects stop reaching a round.

**Decision:** `.agent-guild/scripts/check-job-spec.py` runs eleven rules over the constitution and task set, proofs before heuristics, and exits nonzero naming the first thing it can prove wrong in one line. `dispatch-guard` refuses an auditor dispatch while it fails, mirroring the CON-audit gate on workers. Its regression suite is #117's own archive rather than invented fixtures: the DEC-audit-r4 state that shipped must exit 0, and each finding is reproduced as a one-line mutation of that same corpus, run against a pinned fixture repo root so the test doesn't rot when a cited file moves.

Testing against a real audit is what made it correct. Measurement overturned three rules that read fine on paper: a cross-artifact similarity threshold whose signal sat at 0.39 under a noise floor of 0.55, a build-ordering rule whose first formulation required a task to be upstream of itself, and an anchor rule that failed the very corpus it had to pass. A later adversarial check found four more, every one of them a false positive that blocked correct paperwork, and every one in an inferring rule rather than a proof.

**Alternatives considered:** A rule counting prose enumerations was cut rather than shipped warn-only, because a non-gating rule inside a hook-invoked subprocess produces output nothing reads; the constitution template and skill now ask for a list instead, which keeps the check mechanical. `markdown-it-py` and PyYAML were both rejected (see [[antipatterns]]). Coverage is stated honestly rather than rounded up: four of the six findings reproduce literally, two by class.

## 2026-08-10: Speed Comes From Not Auditing Cheap Defects, Not From Auditing Less

**Source:** #117's run measured end to end; design pass filed as #132-#136; epic #126 rewritten

**Context:** Three runs now measure the same shape — roughly half a guild job's wall clock is an opus auditor reading the orchestrator's own paperwork. #117 was 64 of 133 subagent-minutes across nine audit rounds, with every dispatch serial and 13 of 15 checks passing first time.

**Decision:** Four pieces, sequenced by risk to #34's corpus rather than by size. A pre-flight linter (#132) proves what a script can prove before an auditor is dispatched. Tasks declare the files they own (#133), with overlap legal only where a dependency edge orders it. The stop gate's existing next-move computation grows into a wave (#125) and something dispatches it (#134). A dependent task then starts on its dependency's artifact rather than its verdict (#135), with discarded crossings recorded as such (#136).

**The premise that was wrong:** #120 called a round budget the cheapest and largest win. #117 disproves it — a three-round cap would have stopped before the rounds that found a deadlocked task and a `check_method` instructing a verdict `validate-verdict.py` refuses to write. The round count was the symptom; six of eleven findings were mechanically provable and cost four opus rounds at 300-550 seconds each.

**The scheduler is machinery, not a role.** It computes; it never decides. Every FAIL, dispute, escalation, and ambiguous rollback wakes the orchestrator. The guild's roles are the things that exercise judgment and can be wrong in interesting ways; this one's failure mode is a bug.

**Honest ceiling:** about 2.5x on #117's numbers, not 10x. Six of its seven tasks sat on one dependency chain, so concurrency had little to bite on. Past that needs flatter decompositions, which no scheduler can fix, and #123's tiering so a small change stops paying a large one's ceremony.

**Alternatives considered:** parallel audit dimensions, several auditors per round (rejected for now — several of #117's rounds found defects introduced by the previous round's repair, which parallel dimensions cannot see); worktree isolation per worker with merge-back (rejected — overlap is usually a decomposition defect, and the merges most likely to conflict are the append-only files); a round budget as filed (deferred to after #132, when the argument is against different data).

## 2026-08-10: What The Vendor Must Know Lives In The Brief, And What A Field Means Lives In The Schema

**Source:** #113 and #115, fixed together

**Context:** Two live failures with one cause. A crossing was rejected twice for returning `checker: checker-judgment` and a guessed model, because the lane validates identity on receipt and nothing ever told the far side what to send; the workaround that then worked five times for five was prose someone typed into a dispatch. Separately, a `pass` came back carrying twelve `blocker` findings, every one affirming that something was correct, because `severity` had no enum, no stated relation to `verdict`, and no definition the vendor could read.

**Decision:** Split the two by delivery channel. Severity semantics go in `verdict.schema.json`, which both lanes already hand the vendor as the output schema (`codex exec --output-schema`, `claude --json-schema`) and which in-family checkers validate against, so one edit reaches every writer of a verdict. Identity can't go there, since `vendor` and `model` are lane-specific and the schema is generic, so `compose-brief.py` takes `--vendor`/`--model` and appends a `## Verdict contract` section carrying the whole instruction the courier used to retype: nine fields, four identity values to echo, null metrics, fail-needs-a-finding, and what severity means. Both flags or neither, so the existing golden briefs stay a real regression guard.

**The severity ruling:** `blocker`, `major`, `minor`, `info`, by defect impact. A finding recording a satisfied clause is `info`. The mechanism behind #115 was almost certainly the brief itself: it quotes clause text verbatim, a clause reads `**severity**: blocker`, and the roles ask for one finding per cited clause including on a pass, so the clause's severity became the label for every finding about it. A `pass` now carries only `info` and `minor`, enforced in `validate-verdict.py` as its third semantic rule, since a `blocker` or `major` asserts a defect and contradicts a verdict saying every clause is satisfied.

**Verified live** rather than by fixture alone. One codex-lane crossing with a deliberately blocker-severity clause that the artifact satisfies: `checker: checker-courier` and `model: gpt-5.6-terra` correct on the first attempt, the satisfied clause returned `info`, validator clean, 17,761 input tokens and 9 seconds.

**Alternatives considered:** Stamping identity onto the response after it returns, which #113 called the stronger option. Rejected because it makes the courier the author of a verdict it is supposed to transcribe, which is the separation the org chart exists to keep, and because it fixes the symptom while leaving the vendor uninformed. A lane table inside `compose-brief.py` (rejected—duplicates the pin the adapters already own, and single-sourcing vendor config is #35). Enforcing only `pass` + `blocker`, which is all #115's acceptance criteria demanded (rejected—`major` asserts a real defect too, and a rule with an unexplained hole is a rule nobody trusts).

## 2026-08-10: Teach The Frontmatter Parser Block Scalars Rather Than Take A YAML Dependency

**Source:** #109; commit d05d6ca

**Context:** `_lib.parse_frontmatter` set a block-scalar key to `""` and skipped its indented body, commented "we don't need its body." For `check_method` that body is the entire contract between a task and its checker, and `>-` is the natural spelling for a value running past a thousand characters. The #97 run's first T-001 cited eleven clauses and parsed to `''`. The file read correctly in an editor, `clauses:` parsed normally, and only a hand inspection before dispatch caught it.

**Decision:** Parse the body rather than refuse the file, which the issue offered as the equally acceptable alternative. `|` and `>` with any chomping indicator now parse; unsupported edges (explicit indentation indicators like `|2`, anchors, nesting) are named in the docstring instead of silently mishandled. The second half is a refusal: `dispatch-guard` blocks a task citing clauses with an empty `check_method`, ahead of the worker/checker split, because a checker with nothing to run reports a pass.

**How it was verified without a dependency:** Ruby's psych. pyyaml isn't installed and the stdlib-only rule covers the tests as much as the hooks, so thirteen fixtures were diffed against `ruby -ryaml`, which ships with macOS. All thirteen agree, including `|+`/`>+` chomping, blank-line runs, and more-indented folded lines. The harness stayed in the scratchpad; the committed tests assert the values it confirmed.

**Alternatives considered:** Adding pyyaml (rejected—the hooks are stdlib-only by design, and the issue ruled it out). Refusing a block scalar loudly instead of parsing it (rejected—the task template's own `check_method` example uses `>-`, so refusal would break every task written the documented way). Supporting only the three forms the issue names (rejected—`|-` and `>+` would keep the identical silent-empty bug under a different spelling). Fixing `compose-brief.py` and `check-provenance.py`'s own parsers alongside (deferred—neither reads `check_method`, so nothing is broken today).

**Still open:** the double-quoted-scalar escaping hazard the issue names as a separate defect, filed as #127 with its severity argument in the body.

## 2026-08-10: The Codex To Claude Lane Needs Two Things, And Auth Was The Smaller One

**Source:** #92; commits 0353930 and aeb8b09; the first live crossing, 2026-08-10

**Context:** Every courier crossing from a Codex host on macOS came back `blocked` with `Not logged in · Please run /login`, and the CLI was logged in. That read as a credential problem for months, and it was half of one.

**Decision:** Document both requirements, because each one hides behind the other. A headless token from `claude setup-token`, supplied as `CLAUDE_CODE_OAUTH_TOKEN`, clears the login keychain a sandboxed Codex session cannot open. `sandbox_workspace_write.network_access = true` in the Codex TOML gives the request somewhere to go. Supply only the token and the failure changes shape rather than clearing: the credential resolves, and the call then dies silent at the 120-second bound. `curl https://api.anthropic.com/v1/messages` fails to resolve in 1.3ms inside the sandbox, and Claude Code retries transport failures rather than erroring out, so a blackholed connection looks exactly like a hang. Both together produced the project's first non-blocked crossing: verdict pass, schema-valid, exit 0, 13 seconds, two cents.

**What it cost to find:** three separate auth-shaped error messages that each meant something else. A stale refresh token 401 on the Claude host while `codex login status` reported a healthy login; the keychain in the sandbox; and finally DNS. The courier's own timeout branch now recognizes the third: silence on both streams for the whole wall clock is the signature of a sandbox with no egress, so it names the curl check and the config key instead of reporting elapsed time.

**Alternatives considered:** Shipping the token as *the* fix, which the first commit did. Rejected once the live run showed it trades an error that names its cause for one that says nothing at all, which is nearly as costly as being wrong. Also rejected: treating the whole thing as a Codex sandbox limitation and declaring the reciprocal lane unviable, which the working config disproves.

## 2026-08-10: An Exhausted Courier Lane Substitutes Nothing

**Source:** #97; commit 1687dc4, merged as 20e93f0

**Context:** Four places disagreed about what happens when the lane goes down. The routing table named the in-family checker as the fallback, the state map said no substitution was needed, `docs/installing.md` said the Guild falls back, and `dispatch-guard`'s message advised a re-dispatch in the same breath as saying the denial costs nothing.

**Decision:** Nothing is substituted, and the reason is timing. A courier only goes out after the checker of record has returned, so by the time the lane is denied there is nothing left to re-run. Worse, a re-run landing at the lane-suffixed stem would let #34 count a same-host check as cross-vendor agreement, which is the one way to corrupt that sample without anyone noticing. The state map entry for `exhausted/<lane>` owns the rule; the guard message quotes it rather than paraphrasing.

**Alternatives considered:** Keeping the substitution and rewriting the state map to match. Rejected on the #34 contamination alone. The Claude smoke run's D2 had already followed the state map and written down why it was ignoring the guard's advice, so the working behavior was already the correct one.

## 2026-08-02: v0.5.1 Shipped On Two Live Smoke Runs, With Its Failures Written Down

**Source:** both host matrices run live; issues #88–#102; PR #93; commits 861eca9 and 1aaa4c5; tag v0.5.1

**Context:** SMOKE.md had been accurate about what the gates *say* since #78 and had never actually been executed. The milestone required both matrices to pass, so the tag hung on running them rather than reading them.

**Decision:** Run both, correct whatever they contradicted, and tag with the failures documented rather than hidden. C4 is now marked Claude-only: the ladder's rungs are Claude model names, Codex has nothing to put behind them, and an escalated task there wedges between the gate refusing the stale tier and the host refusing the new one (#88). The milestone description was rewritten three times before it described what shipped instead of what was intended.

**What the runs bought:** ten filed issues, one of which mattered immediately. The Claude package had been shipping six agents against Codex's nine since v0.5.0, missing `checker-courier`, so the dual-check regime the contract calls mandatory had never run for a single plugin user (#94). Fixed, and verified with a real crossing rather than a passing build: `T-001-opus-r0-codex.json`, vendor `openai`, model `gpt-5.6-terra`, verdict pass. First genuine cross-vendor second opinion the project has produced.

**Alternatives considered:** Filing the four small convention divergences separately was rejected for #101, which puts stem, dispute frontmatter, and timestamp behind the return gate — fix them one at a time and the next four appear. Re-milestoning #34 out of v0.6.0 was considered and rejected: the issue body and the milestone description both already name it the entry gate, so the ordering was written down and only its blockers were invisible. Recording the blockers was the smaller correct fix.

## 2026-08-01: One Codex Agent Name Per Dispatch, And No Re-Tasking Through `followup_task`

**Source:** issue #77; PR #80, verified live in a Codex session the same day

**Context:** Codex treats `task_name` as a unique agent name inside a session tree and rejects one already in use. Carrying one id per task (#71) therefore made the second dispatch for a task collide, and the obvious workaround `t_001_checker` was blocked because `bare_id` only parsed `t_001`. With both routes closed the model reached the running agent through `collaborationfollowup_task`, which no matcher covered. Four such calls ran in one session, one of them from inside a subagent. That call names no agent type, carries an encrypted message, and identifies its target only by agent path, so none of the dispatch checks can run against it, while `SubagentStop` still fires and the return gate judges whatever comes back. A whole job completed with `dispatch-guard` never applying.

**Decision:** Make the wire name unique per dispatch rather than per task (`t_001_r0_worker`, `t_001_r0_checker`, `con_audit_r0`), with `bare_id` stripping any trailing discriminator back to the canonical `T-001` so task files, verdict stems, and the dispatch log are untouched. The discriminator is free-form on purpose. Gate `followup_task` in the Codex matcher and refuse it outright whenever any segment of its target parses as a guild id, since refusal is the only move available when there is nothing left to check. The block names a spare `task_name` so it teaches rather than merely stops. Both halves ship together: closing the ungated path without fixing the collision would only move the pressure elsewhere.

**Alternatives considered:** Constraining the discriminator to a fixed role vocabulary (rejected—a too-tight shape is exactly what pushed the model off `spawn_agent`, and a re-dispatch repeating both role and retry count still needs room to name itself); recovering a Task-ID from the followup itself and checking it like a spawn (rejected—the target is an agent path and the message is encrypted, so there is no id to recover); allowing a followup at a guild agent whose task is in a legal state (rejected—state is the only thing that could be checked, and tier, executor identity, and the CON-audit precondition would all go unverified).

## 2026-07-31: The Guild Never Takes Work On Its Own Gates In This Repo

**Source:** #68 and #77 routing decisions

**Context:** Both issues were candidates for a dogfooded guild run, and both change files under `.agent-guild/hooks/`. This repo registers its gates from the working tree (`.claude/settings.json` points `PreToolUse` at `.agent-guild/hooks/dispatch-guard.py`), so a worker editing them is rewriting the machinery while the job depends on it.
**Decision:** Route any change to `.agent-guild/hooks/*.py` directly, never through a guild job. Everything outside `hooks/` stays eligible, which is why #78's docs sweep goes to the guild and #77's gate work does not. The failure this avoids is not hypothetical: `_lib` is imported by all four gates, so one bad edit takes down dispatching, the write guard, the return gate, and the stop gate at once, including the gate that would otherwise report the job stuck.
**Alternatives considered:** Splitting an issue so only its non-gate files go to the guild (rejected—it fragments one coherent change across two executors for no gain); running the job with `PAUSED` set (rejected—it disables the verification the job exists to exercise); accepting the risk because the suite would catch it (rejected—the suite runs after the edit, and the job needs the gates during it). Note this constraint belongs to this repo alone: a project consuming the kit never has its own gates as the artifact under change.

## 2026-07-31: The Codex Return Path Reads The Parent And Transcribes The Verdict

**Source:** issues #68 and #71; PRs #75 and #76

**Context:** The return gate recovered a task id from the child's transcript, where it has never existed, because the id rides in the parent's `spawn_agent` arguments and the child's dispatch message is encrypted. Against a live payload the gate resolved a worker's return as `CON-audit`, found no task file, and failed open. Separately, in-family checkers run `sandbox_mode: read-only` on Codex and could not write the verdict JSON the gate demanded, while `checker-courier` was the only agent given a Codex protocol at all.
**Decision:** Prefer the parent's `transcript_path` and fall back to the child only when the parent path is unusable. Let read-only in-family checkers return the verdict inline under an `AGENT_GUILD_VERDICT` marker, gate-validated for schema plus `task_id` and `checker` identity, then persisted unchanged by the parent. The orchestrator's write is a transcription and it must not edit the object: editing a verdict it commissioned would make it the author of its own check.
**Alternatives considered:** Correlating returns by `agent_id` instead of by transcript (rejected—the parent transcript records no mapping from a spawn call to the resulting agent id); leaving identity checks to `validate-verdict.py` (rejected—the validator knows a verdict's shape, not which task it belongs to, and a verdict persisted against the wrong stem is worse than one refused); documenting the read-only gap rather than closing it (rejected once #75 made the gate reachable, since checkers would have started deadlocking).

## 2026-07-31: The Codex Dispatch Id Rides In `task_name`, Lowercased And Underscored

**Source:** issue #71; PRs #72 and #74

**Context:** Codex encrypts a dispatch's `message` before any hook sees it, so `Task-ID: T-NNN` in the prompt is unreadable there. Three defects stacked underneath: the registered matcher never matched the tool name Codex reports (`collaborationspawn_agent`), `_bare_tool_name` rejected that name, and the id was unreadable regardless. Fixing the matcher alone would have taken the host from unenforced to unusable.
**Decision:** Carry the id in `task_name`, the one dispatcher-set field readable at both the dispatch payload and the transcript. Codex validates that field as an agent name and rejects anything outside `[a-z0-9_]`, so the wire form is `t_001` and `con_audit`; `_lib.bare_id` canonicalizes back to `T-001` so task filenames, verdict stems, and the dispatch log are unchanged. `dispatch-guard` reads the structured field first and falls back to the prompt line, leaving the Claude host untouched.
**Alternatives considered:** `tool_use_id`/`call_id` (rejected—host-generated, so they can correlate an id but never carry one); keeping the prompt line and accepting an unenforced Codex host (rejected—that is what milestone 7 shipped); renaming the canonical id repo-wide to fit the charset (rejected—the wire form is a host detail and everything downstream already keys on `T-NNN`).

## 2026-07-27: One Install Guide And One Smoke Lifecycle Serve Both Hosts

**Source:** issue #55

**Context:** First-Class Codex added real platform setup differences, but keeping Claude and Codex guides or lifecycle drills side by side would make shared Guild behavior drift and force users to reconcile near-copies.
**Decision:** Make `docs/installing.md` the one user installation source for Claude plugin, Codex CLI/desktop plugin, repo-local Codex IDE, cross-vendor credentials, hook trust, and duplicate-registration safety. Root and packaged READMEs point to it; `docs/building.md` remains a maintainer build reference. Keep one host-neutral `SMOKE.md` lifecycle with a small invocation/lane map and thin, independently checkable fresh-project launch drills for each supported surface.
**Alternatives considered:** Separate Claude and Codex install guides (rejected—the shared init and lifecycle would be duplicated); keeping user setup in the build reference (rejected—it mixes maintainer and adopter paths); cloning the full smoke lifecycle per host (rejected—only dispatch representation, skill syntax, hook trust, and courier lane differ).

## 2026-07-26: One Generated Codex Package Is The Git Marketplace Surface

**Source:** issue #53

**Context:** Codex had a complete generated package, but it lived only in ignored `dist/` with a committed hash. A Git marketplace needs a real package path inside the repository, and hand-maintained marketplace or package copies would recreate the parallel implementation surface the shared core removed.
**Decision:** Generate and commit the Codex package at `plugins/agent-guild/`, generate `.agents/plugins/marketplace.json` beside the existing Claude marketplace, and derive both marketplace views from `scripts/plugin-src/plugin.json` plus one `scripts/plugin-src/marketplace.json`. The default build syncs both package trees and marketplaces; `--check` rebuilds and diffs all four generated release views. Explicit `dist/` builds remain scratch/CI artifacts. The old Codex hash lock retires because the committed generated tree is now the stronger drift boundary.
**Alternatives considered:** Keep only the hash and publish an attached archive (rejected—the Git marketplace cannot resolve ignored content); author the Codex package or marketplace by hand (rejected—it creates a second implementation and metadata drift); publish from a separate repository (rejected—it creates a parallel release process).

## 2026-07-26: Claude Marketplace Identity Is `agent-guild@kendrick`

**Source:** issue #48; isolated Claude Code 2.1.212 marketplace experiment

**Context:** The plugin and marketplace were both named `agent-guild`, producing the typo-like qualified id `agent-guild@agent-guild`. Renaming the marketplace also creates a migration hazard if the old source remains configured.
**Decision:** Keep the plugin name `agent-guild`, rename only the Claude marketplace to `kendrick`, and use the qualified id `agent-guild@kendrick` in every install, disable, and uninstall surface. Tell existing users to uninstall the old qualified plugin and remove the old marketplace before adding the renamed source. An isolated CLI run proved both marketplace names, cache trees, and qualified plugins can coexist and both are enabled in a neutral project, which would double-register every hook.
**Alternatives considered:** Leaving the redundant identity (rejected—it obscures publisher ownership); relying on the unqualified plugin name (rejected—it is ambiguous once both marketplace sources coexist); asking users only to add the renamed marketplace (rejected—the stale installed copy stays independently enabled).

## 2026-07-26: Reciprocal couriers share one protocol and keep host commands in adapters

**Source:** issue #54

**Context:** Codex-hosted jobs needed an independent Claude second opinion, but the courier core still embedded the Claude-hosted `codex exec` route and Codex project agents are intentionally read-only.
**Decision:** Keep evidence, validation, ledger, quota, and second-opinion semantics in one host-neutral `checker-courier` role; put the exact Codex and Claude commands in thin agent adapter suffixes. The Codex lane invokes a stdlib-only `claude-courier.py` boundary that pins `claude-haiku-4-5-20251001`, isolates the CLI with no tools or MCP servers, adapts only the schema's top-level `$schema`, requires and independently validates `structured_output`, aggregates retry usage, classifies structured 429s, and enforces a wall-clock bound. A read-only Codex courier returns the marked outcome; the return gate validates it before the parent persists the `-claude` verdict and ledger, or appends the quota ledger line before creating `exhausted/claude`. The unsuffixed in-family verdict remains authoritative.
**Alternatives considered:** Duplicating the full courier procedure in the Codex adapter (rejected—it recreates the parallel implementation surface); granting the Codex courier workspace write (rejected—it weakens the read-only verifier boundary); trusting Claude's exit code or `--json-schema` alone (rejected—controlled malformed output can exit zero without `structured_output`); blocking the whole task when the external lane is unavailable (rejected—the second opinion is comparison data, not the verdict of record).

## 2026-07-26: Codex lifecycle adapters reuse the four shared gates

**Source:** issue #56

**Context:** Claude's four enforcement gates already held the Guild policy, but Codex names lifecycle fields and structured edits differently, discovers plugin and project hooks at different scopes, and requires explicit user trust for hook definitions.
**Decision:** Keep policy only in the existing four stdlib Python gates and translate Codex command-hook JSON through one `codex-hook-adapter.py`. Preserve exit code 2 plus stderr as the blocking/continuation protocol; map `spawn_agent`, multi-target `apply_patch`, child transcript paths, and subagent identity into the shared contract. Generate plugin and repo-local hook configs from one inventory. Plugin setup relies only on plugin hooks; repo-local bootstrap owns the shared scripts and merges only handler commands carrying the Guild adapter signature into `.codex/hooks.json`, preserving unrelated configuration. Setup always directs the user to review and explicitly trust definitions in `/hooks`; installation never claims trust.
**Alternatives considered:** Forking all four gates for Codex (rejected—the policies would drift); reimplementing policy inside a stateful adapter (rejected—the current Codex payload supplies subagent identity directly); overwriting `.codex/hooks.json` (rejected—it is project-owned shared configuration); installing project hooks alongside plugin hooks (rejected—every gate would fire twice); implying installation automatically trusted hooks (rejected—Codex intentionally keeps that authority with the user).

## 2026-07-26: One workflow core and installer engine serve both hosts

**Source:** issue #57

**Context:** Claude already carried the complete lifecycle and working-memory workflows, while the staged Codex package exposed only a subset and its separate installer guide duplicated setup behavior. Codex also has two valid skill scopes with different invocation names: plugin skills are namespaced, while repo-local skills are not.
**Decision:** Author all twelve workflow bodies only under `guild-core/workflows/`, render host frontmatter and the thin `init` command suffix from adapters, and ship one stdlib-only `install-project.py` engine in both packages. Claude plugin init preserves project settings and installs the payload plus bounded guidance. Codex plugin init installs the payload, roster, and bounded guidance while relying on plugin skills; repo-local Codex adds `--project-skills` to install `.agents/skills/`. The exact entrypoints are `/agent-guild:job`, `$agent-guild:job`, and `$job`, respectively.
**Alternatives considered:** Copying Claude skill bodies into a Codex source tree (rejected—it creates a second implementation); maintaining host-specific installation guides or engines (rejected—their safety and ownership rules would drift); always installing repo-local Codex skills (rejected—an installed plugin would expose duplicate skill names); translating Codex skills into slash commands (rejected—Codex's documented explicit syntax is `$skill-name`).

## 2026-07-26: Codex verifiers return content across a read-only host boundary

**Source:** issue #50

**Context:** The shared Guild checker and auditor roles describe writing their own state files, while Codex can enforce a stronger project-agent sandbox and the initializer must coexist with project and global user configuration.
**Decision:** Generate the complete nine-agent project roster as standalone `.codex/agents/*.toml` from the shared role bodies plus Codex adapter metadata. Auditor and checker agents run `read-only`; their host instructions override shared write steps and require returning the intended path and complete proposed content to the parent orchestrator for persistence. The initializer updates only the generated project roster and one bounded `AGENTS.md` section, preserves unrelated content, never reads or writes global Codex configuration, rejects redirected `.codex` paths, and fails closed on malformed ownership markers.
**Alternatives considered:** Granting checkers workspace write so shared prompts could remain literal (rejected—it weakens independent verification); forking Codex-specific role prose (rejected—it recreates the duplicate implementation surface); replacing all of `AGENTS.md` or `.codex/` (rejected—it would destroy project-owned configuration); installing into global `$CODEX_HOME` (rejected—Guild behavior is project-scoped).

## 2026-07-26: CI verifies and packages both hosts without committing output

**Source:** maintainer request during PR #60

**Context:** A shared-core build is only dependable if each host has an unambiguous command and pull requests catch stale generated state without creating another automated writer.
**Decision:** Expose explicit `claude`, `codex`, and `all` build targets; document their sources, outputs, sync command, and checks in one canonical guide. GitHub Actions runs the full suite and strict Claude validator, rejects generated drift, proves a fresh Claude build is identical to the established published package, and uploads both packages—including their hidden manifests—as an ephemeral artifact. It never commits generated files.
**Alternatives considered:** Keeping the target split implicit in maintainer-only commands (rejected—easy to build or edit the wrong tree); having CI auto-commit rebuilds (rejected—it obscures source/output mistakes and introduces a privileged writer); uploading only Codex (rejected—building both from the same revision is the clearest evidence that the shared-core contract holds).

## 2026-07-26: Host packages are rendered artifacts, not parallel source trees

**Source:** maintainer review of PR #60; supersedes the issue #51 decision immediately below

**Context:** The first #51 implementation called the dogfooded Claude tree a shared core and committed 47 Codex package files beside it; 45 were byte-identical copies, so the repository gained exactly the parallel content surface First-Class Codex was meant to avoid.
**Decision:** Author shared role behavior and workflow bodies/assets only under `guild-core/`; keep host-bound frontmatter and manifest metadata under `scripts/plugin-src/adapters/`; generate the dogfooded Claude wrappers and both packages from those inputs. Preserve the existing published Claude tree for marketplace compatibility, but stage Codex under ignored `dist/` and commit only its compact content lock until #53 defines the publishing surface. A check rejects edits to generated dogfood, stale Claude output, stale Codex content, and a hand-edited staged artifact.
**Alternatives considered:** Treating committed generated copies as sufficiently DRY (rejected—the edit path was singular but the repository surface was not); keeping `.claude/` as the semantic core (rejected—it mixed shared behavior with Claude representation); committing the incomplete Codex staging tree before #50, #56, and #57 supply its actual adapters (rejected—it looked like a second implementation and exposed Claude wrappers as Codex content).

## 2026-07-26: Both host distributions are generated from the dogfooded source graph

**Source:** issue #51

**Context:** First-Class Codex needs a package target without creating a second Agent Guild implementation or turning the repo's live Claude setup into another generated copy developers cannot edit directly.
**Decision:** Keep the dogfooded `.claude/` and `.agent-guild/` trees as the canonical shared source graph. `scripts/build-plugin.py` now generates both `plugin/` and `codex-plugin/` from that graph and one authored version. Schemas, scripts, templates, scenario assets, workflow bodies, and role definitions are single-sourced; target builders may change only platform representation, currently Claude invocation namespacing and Codex skill frontmatter/manifest metadata. `--check` rebuilds and diffs both committed targets, so hand edits fail regardless of host.
**Alternatives considered:** Maintaining a parallel Codex source tree (rejected—the drift #51 exists to prevent); moving every live source into a third abstract directory immediately (rejected—it would make both dogfooded host trees generated artifacts before the later agent, hook, and skill adapter issues define their stable representations).

## 2026-07-26: First-Class Codex targets v0.5.1

**Source:** maintainer direction during issue #52

**Context:** The First-Class Codex roadmap was filed under a speculative v0.9.0 milestone after v0.5.0 shipped, but the release target changed before implementation began.
**Decision:** Ship the First-Class Codex arc as v0.5.1, not v0.9.0. Work commits still leave the version untouched; the one mechanical release commit carries the 0.5.1 bump when the milestone wraps.
**Alternatives considered:** Keeping v0.9.0 because the issue bodies and milestone already named it (rejected—the maintainer explicitly changed the release target, and tracking metadata does not outrank the release decision).

## 2026-07-26: The reciprocal Claude lane requires a schema adapter and envelope validation

**Source:** issue #52, live Claude Code 2.1.212 probes

**Context:** The Codex-hosted second-opinion courier needs a concrete Claude CLI contract, including its read-only boundary, structured output, malformed output, authentication failures, and quota signals.
**Decision:** Pin `claude-haiku-4-5-20251001` and invoke Claude in safe mode with no tools, no MCP servers, plan permissions, no persistence, closed stdin, and all evidence inline. Generate the Claude `--json-schema` argument by removing only the canonical verdict schema's top-level `$schema` declaration; require and independently validate `structured_output` because malformed provider output can exit zero without it. Treat `api_error_status: 429` as quota and impose a courier-owned wall-clock bound because the CLI otherwise retries silently up to 11 attempts.
**Alternatives considered:** Passing the canonical Draft 2020-12 schema byte-for-byte (rejected—Claude CLI rejects its `$schema` URI before a model call); trusting exit code zero (rejected—a controlled malformed response exited zero with no `structured_output`); relying on the CLI's retry policy (rejected—it is silent, long, and ignored the tested retry-limit override).

## 2026-07-24: External dispatch costs ~100x the in-family marginal

**Source:** issue #33, `docs/handoff-cost.md`, measured over six courier dispatches

**Context:** The multi-provider roadmap kept deferring to an economic number nobody had measured.
**Decision:** Measured, not decided: serialized context for an external check runs 49.8x to 202.9x the orchestrator's in-family marginal (mean 99x, aggregate 102.5x)—99% of what a vendor receives is overhead the in-family path never pays, because an in-family checker reads artifacts from disk while a vendor must receive everything inline. Denominated in tokens; the lane reports no per-call dollars. The v0.7.0 write-granted-lane gate becomes numeric: ratio ≥ 100, with extrapolation assumptions labeled (worker briefs run larger, iteration multiplies calls, blind-diff retries re-pay full context). Cross-family checking is affordable at these rates; cross-family working re-pays the multiplier every loop.
**Alternatives considered:** Waiting for worker-lane data before setting a gate (rejected—#36 needs the constraint now, and check-lane data plus labeled assumptions beats a vibe).

## 2026-07-24: The cross-family lane ships as checker-courier under an auto-dual regime

**Source:** issue #8 (commit 2be781f), amended by #44 (269a249)

**Context:** An executor and checker from the same model family share correlated blind spots; breaking that correlation is the entire multi-provider premise.
**Decision:** `checker-courier` — a haiku courier relaying judgment checks to an external vendor CLI over a lane (codex today, `gpt-5.6-terra` far side), producing a SECOND-OPINION verdict at a lane-suffixed stem that never decides a task. Named lane-neutral from birth so #11 adds lanes rather than renaming an agent. Until #34 closes, every task reaching `checking` also gets a courier crossing, so the evaluation fills through ordinary work. The compose step inlines everything the vendor needs (brief, artifacts, clause-referenced evidence); the vendor fetches and executes nothing.
**Alternatives considered:** A codex-specific `checker-codex` (rejected per the standing #8 comment—renaming later is churn); making the second opinion able to fail a task (rejected—a second opinion is not a second gate).

## 2026-07-24: Release cadence is minor-only while the user base is small

**Source:** docs/publishing.md (commits f13e7c5, 3f43098)

**Context:** Per-job patch releases (0.3.2 through 0.4.1) were becoming the de facto rule without anyone deciding they should be.
**Decision:** Phase-dependent, not doctrine. In dev mode with barely an installed base, work accumulates across jobs and ships as one 0.X.0 cut at milestone close. Patch releases stay first-class for the cases that warrant them (security fixes, broken installs), and their importance grows with the user base.
**Alternatives considered:** Ruling patch releases out entirely (rejected—sometimes crucial); keeping per-job releases (rejected—ceremony without readers).

## 2026-07-24: Releases are two-commit, tagged per bump, with generated changelogs

**Source:** issue #42 (commit 952b82e), the tag-per-bump amendment (3c113c8), first live runs at v0.3.6 and v0.4.0

**Context:** Releases left no reader-facing record, nothing enforced remembering a changelog, and fix-level versions had no tags — half a record.
**Decision:** `make-changelog.py` harvests commits between plugin.json version-bump boundaries into unwrapped conventional sections (group headings, bold scope leads, linked hashes); it never invents prose. Enforcement is mechanical: `build-plugin.py --check` fails a bumped-but-sectionless version, and `--notes` refuses to cut a noteless release. The ritual is two-commit — work commits never touch the version; one mechanical release commit carries bump + in-flight section + rebuild — and every release commit gets tagged with a GitHub release, patch bumps included; a milestone close is just the bump that closes it. Kit-payload jobs leave the version untouched; the release is the maintainer ritual at wrap.
**Alternatives considered:** git-cliff/conventional-changelog tooling (rejected for now — tags-as-boundaries would add a forgettable parallel discipline; recorded as the exit ramp on #42 if the format ever needs to grow); milestone-only tags (rejected — the version field and changelog exist per bump, so taglessness left the record incomplete).

## 2026-07-24: Verdicts are canonical JSON; blocked absorbs ERROR

**Source:** issue #29 (commit 1594cf8)

**Context:** A second checker family (#8) needs a contract to write against; Markdown verdicts could only be validated by parsing conventions that drift.
**Decision:** JSON is the verdict of record, schema-validated, with Markdown rendered from it; `subagent-return` mechanically rejects nonconforming checker returns; a fail requires evidence-backed findings. The enum is `pass|fail|blocked`, with `blocked` carrying the old ERROR semantics (couldn't run, doesn't count against the worker) so one vocabulary covers broken checks and vendor quota alike. The schema stays structured-output-safe (no conditionals); semantic rules live in the validator. The migration dogfooded itself mid-run — the job's own later verdicts were gate-validated JSON.
**Alternatives considered:** Adding `error` to the enum (rejected — two near-synonymous states); keeping ERROR outside the schema (rejected — broken checks would produce forever-nonconforming files).

## 2026-07-24: Isolation strategy — patch-return default, worktrees only for workspace-write lanes

**Source:** issue #32, closed with this decision

**Context:** Claude Code supports `isolation: worktree` for subagents; #36 (per-lane write mode) needed a fed decision, and the question of native-worker isolation was open.
**Decision:** Native guild workers get no worktrees — structurally blocked anyway, since the message bus is the gitignored `.agent-guild/state/` and worktrees materialize tracked files only, so a worktree'd worker can't see its own task file. External lanes default to patch-return (vendor emits a diff, the haiku courier applies it — the apply step is mechanically cheap; the real price is the vendor can't iterate against its own edits). Workspace-write is a measured per-lane exception that arrives worktree-required, because a write-granted foreign process is an untrusted writer that could otherwise reach the unrecoverable state bus. No task-scoped claims layer until a real collision happens.
**Alternatives considered:** Worktrees everywhere (rejected — merge-back cost plus the state-bus incompatibility); "writes bypass hooks" as the justification (rejected as dishonest — native workers can Bash-write past the hooks too; the real differentials are writer trust and bus exposure).

## 2026-07-24: Open-weight ships as lane config, never a privileged path; OpenCode rejected as universal shim

**Source:** issue #31, closed with this decision

**Context:** Two filed paths for open-weight models: pure-function tier zero (direct Ollama calls for mechanical subtasks) vs a harness-wrapped courier via OpenCode, with the side question of OpenCode replacing all vendor shims.
**Decision:** The kit ships no open-weight slot; vendors are manifest lane recipes (the v0.6.0 substrate), and open-weight joins that way when the #34 evaluation justifies it. OpenCode is rejected as the forced universal shim — each vendor keeps a direct recipe — but adopted as this maintainer's personal lane recipe for open-weight, which the config-not-architecture design makes possible without imposing it on other guild users. Tier zero stays unbuilt for lack of measured need.
**Alternatives considered:** OpenCode as the one shim for all vendors (rejected — a dependency on one project's abstraction before the first direct lane even ran); building tier zero now (rejected — no evidence of need).

## 2026-07-23: Ship the guild as a public Claude Code plugin (v0.3.1)

**Source:** commits b294bf7, e7058df, edba55b; epic #19; issues #24, #25

**Context:** Plugin packaging was deferred since the kit began (a standing open question), the blocker being that a plugin can't ship an always-on `CLAUDE.md`.
**Decision:** Published. The repo is its own marketplace (`.claude-plugin/marketplace.json` sources `./plugin`); `scripts/build-plugin.py` assembles `plugin/` from in-repo sources; `/agent-guild:init` finishes each install by copying the per-project payload (contract, scripts, templates) and adding the `@.agent-guild/CLAUDE.md` import; a SessionStart nudge catches partial installs. Verified end to end by SMOKE Part C in a real project (add, install, init, and the plugin's own dispatch-guard denying an untagged dispatch). Tagged v0.3.1, not v0.3.0—see the hooks-load antipattern in [[antipatterns]].
**Alternatives considered:** A SessionStart hook injecting the contract (rejected—`additionalContext` persistence is undocumented, so the one-line import is the reliable path).

## 2026-07-23: Version the roadmap with v0.X.0 milestones, checker lane first

**Source:** the multi-provider planning session; the (now retired) backlog.md; GitHub milestones v0.3.1–v0.8.0

**Context:** The repo had no versions and a loose multi-provider backlog that overlapped the existing codex-lane issues.
**Decision:** Six milestones (v0.3.1 through v0.8.0) tracking `plugin.json`, git-tagged at close. The multi-provider arc ships the cross-family **checker** lane before any external worker lane, gated on a 10-task dual-check evaluation that decides whether external workers get built at all. External vendors are always parallel lanes, never rungs on the Claude-only escalation ladder.
**Alternatives considered:** The existing epic #9's worker-first order (rejected—the checker is read-only, has no write-guard collision surface, is cheaper to build, and produces the go/no-go data the worker lanes depend on).

## 2026-07-22: `/job` flows into `/constitution` instead of stopping at a handoff

**Source:** commit 1c0dfee; issue #26

**Context:** Intake ended by pointing the user at `/constitution`, which read as the guild stalling—especially in auto mode, where the stop gate can't help because intake is pre-Phase-0 and no task exists yet.
**Decision:** Step 5 of the `job` skill invokes `/constitution` in the same turn once `check-provenance.py` passes. Every failure path still stops with an honest message and never invokes `/constitution`; the collapsed interview's confirm-and-adjust step stays the user's touchpoint.
**Alternatives considered:** Leaving the handoff and documenting it (rejected—the stall was the whole complaint).

## 2026-07-14: Scope orchestrator gates to the main session via `agent_id`

**Source:** SMOKE.md B2 run in a copied-in kit; confirmed against the CC hooks docs.

**Context:** The kit assumed "parent hooks do not fire for tool calls made inside subagents," so `orchestrator-write-guard` treated any trip as the orchestrator overreaching. False on CC 2.1.x — PreToolUse fires inside subagents too, so the guard was blocking workers from writing their own deliverables. The guild only appeared to work because workers fell back to `Bash`, which the guard's `Write|Edit|MultiEdit` matcher never covered.
**Decision:** Scope main-session-only gates by the `agent_id` Claude Code stamps on subagent hook input (absent in the main session). Added `_lib.in_subagent(data)`; `orchestrator-write-guard` no-ops when it's true. Corrected the docstring, README, projectOverview, and AGENTS.
**Alternatives considered:** A settings.json scope option (none exists); branching on `agent_type` (present in the main session under `--agent`, so it would wrongly disable the gate). Left open: the guard still ignores `Bash`, so the orchestrator could bypass it via shell redirection — tracked as a separate gap.

## 2026-07-14: Read the dispatch id from the tool_use block, and backstop SubagentStop

**Source:** commit ed29c54, PR #17

**Context:** `subagent-return` couldn't tell which task a subagent ran. `id_from_transcript` scanned `role:user` messages, but CC hands SubagentStop the PARENT transcript, where the dispatch is an assistant `tool_use(Task|Agent)` block. The id was never found, the gate failed closed, and with no backstop on SubagentStop the worker hung indefinitely.
**Decision:** Read the id from the assistant `tool_use(Task|Agent)` `input.prompt` (last dispatch, the one that just finished), with `role:user` text as a fallback. Add a stall backstop to `subagent-return` mirroring the Stop gate's.
**Alternatives considered:** PAUSED (lifts every gate); loosening the regex (the id was well-formed, just where the parser never looked).

## 2026-07-14: Commit the working-memory kit into the guild repo

**Source:** commit e5f6ac0

**Context:** The WM overlay (see the 2026-07-13 entry below) went in untracked, leaving open whether it belonged in this repo or should stay local.
**Decision:** Committed it (e5f6ac0), so the guild ships the working-memory kit bundled in. Closes the corresponding open question, now removed from openQuestions.

## 2026-07-13: Install the working-memory kit as an untracked overlay

**Source:** working tree (untracked `_working-memory/`, `scripts/`, `.github/`, `AGENTS.md`; modified `CLAUDE.md`, `.gitignore`)

**Context:** The guild repo had no durable, cross-session project memory. A separate copy-in kit provides one.
**Decision:** Layer the working-memory kit onto the guild and hydrate its files from the codebase before committing. The kit is not yet tracked—whether it lands in this repo or stays local is still open (see [[openQuestions]]).
**Alternatives considered:** Hand-writing context into `CLAUDE.md` (rejected—it bloats the always-on contract and has no update discipline).

## 2026-07-13: Consolidate the kit under `.agent-guild/`

**Source:** commit 5546d19, PR #16

**Context:** A copy-in install used to spray five entries across the host repo root (`CLAUDE.md`, `.claude/`, `hooks/`, `scripts/`, `templates/`, plus a runtime `state/`). That's a lot of surface for anyone trying the kit or keeping a repo tidy.
**Decision:** Move `hooks/`, `scripts/`, `templates/`, and the runtime `state/` bus under a single hidden `.agent-guild/`, and the orchestrator contract to `.agent-guild/CLAUDE.md`. The root `CLAUDE.md` becomes a one-line `@.agent-guild/CLAUDE.md` import. Install footprint drops to two directories: `.claude/` and `.agent-guild/`.
**Alternatives considered:** Ship as a plugin now (deferred—see the plugin entry). Keep the flat layout (rejected—clutters the host root).

## 2026-07-11: Let auditions through the gates with an allow path, not PAUSED

**Source:** commit d330792, PR #10

**Context:** Audition dispatches carry no `Task-ID`, so `dispatch-guard` blocked them and `subagent-return` failed closed on the id-less transcript—an audition subagent could never finish.
**Decision:** Add an `Audition-ID: A-NNN` allow path (log-and-pass) across `_lib.py` and both hooks, mirroring the auditor precedent.
**Alternatives considered:** The `PAUSED` escape hatch (rejected—it lifts every gate, which makes the audition run unrepresentative of a gated job).

## 2026-07-10: Enforcement lives at the main-session boundary only

**Source:** commit 39693ea

**Context:** Claude Code hooks fire on the main session's actions, not on tool calls made inside a subagent.
**Decision:** Put all four mechanical gates at main-session boundaries (`dispatch-guard`, `subagent-return`, `stop-gate`, `orchestrator-write-guard`) and back subagent-internal behavior with prompts plus tool allowlists (e.g. checkers ship with no Edit tool). Be explicit in the docs about which guarantees are gated and which are prompt-guided.
**Alternatives considered:** Treating prompt rules as equivalent to gates (rejected—it overstates what the kit guarantees).

## 2026-07-10: Fixed model ladder haiku → sonnet → opus → fable

**Source:** commit 66cfbf1 (orchestrator contract)

**Context:** Tasks vary from mechanical to taste-heavy, and a failed tier needs somewhere to escalate.
**Decision:** Route each task by the work, not a default. Escalation climbs the ladder with the retry budget reset at each rung; `fable` is the reserved final rung for genuinely hard, ambiguous problems. There is no rung above it.
**Alternatives considered:** A single model for everything (rejected—the kit's whole premise is that a cheap model under an independent check beats one expensive model grading itself).

## Deferred: package the kit as a Claude Code plugin

**Source:** README "Later: A Plugin"; commit 4cc4d9d

**Context:** Most of the kit (agents, skills, hooks) would package as a plugin under `.claude-plugin/plugin.json`.
**Decision:** Defer. A plugin can't ship an always-on `CLAUDE.md`, so the contract still needs a per-project import or a SessionStart hook that injects it. Expect a hybrid (static tooling as a plugin, the contract and `state/` staying in the project), worth it only once the kit runs across many projects.
