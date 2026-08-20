---
name: constitution
description: Phase 0 of a guild job. Interview the user, then write .agent-guild/state/constitution.md—the falsifiable standard every task is checked against. Use when starting a job, defining what "done right" means, or writing or refreshing the constitution before decomposing work.
---

# Write the constitution

The constitution is the one place "done right" is defined, so every later task, verdict, and dispute ruling can point at a clause instead of arguing taste. Its governing property is **falsifiable**: every clause names a concrete check and describes an artifact that would fail it. A clause you cannot fail is a clause that verifies nothing.

Work through these steps in order. The output is `.agent-guild/state/constitution.md` (from `.agent-guild/templates/constitution.md`) plus, if the job has protected words, a passages manifest.

## 1. Interview

**If `.agent-guild/state/spec.md` exists** (typically written by the `job` intake skill, carrying a provenance header), collapse the interview instead of running the full question bank:
1. Read the spec end to end, including its provenance header (`source`, `ref`, `fetched_at`, and `issue`/`title` when the source is a GitHub issue).
2. Derive candidate quality bars straight from the spec's own content: its stated goal, Definition of Done, deliverables, constraints, and non-goals. Each candidate becomes a clause draft per steps 2-3 below.
3. Present the candidates to the user for confirmation and adjustment. Ask only what the spec leaves genuinely open — severity rankings, protected words, or target environments the spec doesn't name.
4. Never re-ask a question the spec already answers. If the spec states the goal, the audience, a constraint, or a non-goal, treat it as settled and move on to drafting.

**If no `.agent-guild/state/spec.md` exists**, run the full interview: load the question bank in [interview.md](interview.md) and work the user through it: the job's goal, its quality bars, any words that must ship verbatim, the target environments, and what's explicitly out of scope. Ask; don't assume. A constitution written from guesses fails the audit or, worse, passes and misdirects every worker.

Both paths end the same way: derive the job's **weight** before you draft a single clause. Ask the discriminator from the weight table under `## Job weight` in `CLAUDE.md`—does verification need an instrument built, or one that already exists invoked?—then adjust upward if the change runs unattended. Where the signals are ambiguous, take the heavier weight. State the result to the user in one line alongside the candidate quality bars ("This reads light: every acceptance check runs through the test command that's already there"), so it costs a word to correct and nothing to leave alone. Record it in the constitution's weight line, which is where the auditor reads it for the clause ceiling. If the user corrects your derivation, keep both in that line: the correction is the most useful thing the retrospective can report back.

Three fixtures worth checking a derivation against:

| Fixture | Signal | Weight |
| --- | --- | --- |
| kendrick/dotfiles#19 | verified through the existing `bats tests/` suite, but the guard runs unattended via chezmoi's `run_onchange` | standard |
| kendrick/dotfiles#21 | verifying the fix means building a mutation harness—inverting each converted assertion and confirming it goes red—which doesn't exist yet | deep |
| conflicting signals | every acceptance check runs through a command that already exists, but the job carries unattended blast radius, so the heavier weight wins | standard |

Done when you can state the job's quality bars in the user's own terms, not generic ones, and the job weight is stated and confirmed.

## 2. Draft clauses

Turn each quality bar into a clause in `.agent-guild/state/constitution.md`. Per the template, each clause carries an id, its text, a check method, a severity, and a failing example. The check method is one of:
- a script: `.agent-guild/scripts/check-foo.sh <args>`, which routes the clause to checker-deterministic;
- a rubric: `checker-judgment: <one line>`, which routes it to checker-judgment.

Those two are the whole list, and `check-job-spec.py` holds you to it before an auditor ever reads the file. A shell one-liner is not a third form: hand it to `.agent-guild/scripts/check-build.sh '<cmd>'` and it stays the first. The same script compares a clause's counts against its lists and cannot compare one against prose, so when a clause names N things, list them instead of spreading them across a sentence—#117 spent an audit round on a check that read "five files" above six of them. Run `python3 .agent-guild/scripts/check-job-spec.py --audit-id CON-audit` before you dispatch the auditor, since `dispatch-guard` refuses that dispatch until it passes.

When the check is a script invocation, declare its baseline too: `- **baseline**: red | green` alongside the `- **check**:` line. One question decides it—would this check pass right now, before any work? Green if yes, red if no. `check-baselines.py` runs every declared check against the current tree at CON-audit r0 and holds it to that answer, catching a red clause whose check already passes before a worker is ever dispatched against it. The field is optional, and a `checker-judgment:` clause carries none.

The CON-audit runs your checks rather than reading them, and for the ones whose logic this job wrote—an inline `check-build.sh` pipeline, or a self-test in a script the job adds—it first builds a reference implementation from what your clauses cite. A contract those clauses don't determine is a finding against the constitution, so write them so a stranger could build the same thing from the clause and the documents it names. A contract those clauses determine two ways is the same finding: where a clause's wording admits a second reading that would produce a materially different program, the auditor builds that reading too and fails the clause on the expression the two turn on—`kendrick/dotfiles#22` carried such a fork past CON-audit into DEC r0, where two faithful transcriptions a single gate expression apart disagreed about the clause's own count assertion. A check handing off to a script or suite the repo already has owes no such reconstruction. Name a job-added script through `check-build.sh` as well, since R5 requires a directly-named script to exist before the audit is dispatched.

State each clause so a violation is recognizable. "Every page's `<h1>` matches the nav label linking to it" is a clause. "The site feels welcoming" is not.

Keep the clause count inside the recorded weight's ceiling. Going over means one of two things: the clauses are over-built, or the weight was derived too light. Fix whichever is actually true, or—if the job genuinely needs the extra clause—record why in a `**Ceiling overrun**:` line directly beneath the weight line, rather than cutting a clause the job needs to make a number work. `check-job-spec.py`'s R18 blocks the auditor dispatch on an over-ceiling count that carries no such line, so an unrecorded overrun never reaches audit.

If `check-job-spec.py` blocks the auditor dispatch on a rule you believe misread the paperwork, check whether it exits 4 rather than 1. Exit 4 means the rule inferred the defect instead of proving one, and four rules do that: R2, R9, R10, R12'. Those can be wrong about a document that is fine. Record `**Lint exception**: R10 — <why it misread this>` in the preamble and re-run, one line per rule. Never reach for `state/PAUSED` here—it stands down every gate in the system to silence one rule. Exit 1 is a proof and has no waiver, because there is no reading of an unresolvable citation where the rule is the thing that's wrong.

When a clause changes a shared contract—a schema under `.agent-guild/schemas/`, a template shape, a hook-visible file format—its check must run the full consumer suites, not just the contract's own: today that means `python3 .agent-guild/hooks/test_hooks.py` alongside the contract's own tests. Falsify it in step 3 by asking "who else parses this shape?"—the #43 job scoped a schema's own tests but missed `test_hooks.py`'s verdict-fixture helper as a quiet consumer, shipping the hook suite red until the next job's worker hit the broken baseline.

Done when every quality bar from the interview is a clause with a named check.

## 3. Falsify each clause

For every clause, write its failing example: a specific artifact that would violate it. This is the load-bearing step. If you cannot describe what failure looks like, the clause is unfalsifiable—rewrite it into something checkable or cut it. An unfalsifiable clause survives audit only by luck and then lets any work through.

Then hold the clause's text and its check against one hypothetical artifact and ask whether the two can disagree about it. Both halves can be specific and still specify different things, and that failure is nastier than vagueness because it survives a read-through—each half looks right alone. On `kendrick/skills#17`, C-2's text required its parts "before the next scenario heading" while its check extracted "the text between heading N and the next heading of any level"; those agree only for a scenario with no subheadings, so a worker who organized one under `#### Prompt` had the pass-condition table sliced out of the extract, and a blocker clause failed correct work with no tiebreak to appeal to. Four clauses on that run carried the shape, and the repair was the same every time: where the target already ships an artifact that decides the question, cite it instead of paraphrasing it—`lint-scope.sh:218-230` decided C-9, `scope-decisions.md:21-25` decided C-7, and each clause got shorter and correct in the same edit.

Two companion questions catch what that one does not. *Does this check command actually run?*—the same run's r0 named a hook suite its target repo has never had, a check no artifact could clear, so every task citing it would have come back `blocked`. *Have I watched this instrument do what I claim it does?*—a check method asserted a linter guards against invented tokens, when the linter's token pass reads only `schema: 2` files and so exits 0 over a v1 fixture on a token that does not exist. The audit now catches both mechanically, by executing every runnable check and breaking a variant against it, so what asking them here buys is the round the auditor would otherwise spend.

Any check that mutates its input asserts the mutation landed before it asserts anything else. A mutation that silently failed makes every assertion after it vacuous, since the check is then reporting success against a run that did nothing. The `kendrick/skills#27` run is why this is a rule rather than a habit: a fixture was rewritten with `open(p, "w").write(re.sub(pattern, repl, open(p).read()))`, and Python opens for writing before it evaluates that argument, so the file truncated to zero bytes before the nested read ever ran. The fixture came out empty, empty files classified as v1, v1 records were skipped by the artifact under test, and every downstream assertion passed—including the one asserting `order-independent`, the exact string that clause existed to produce. The guard that fixes it runs first, asserting the precondition before anything else:

```python
raw = path.read_text()
assert raw, f"{path} is empty after the rewrite"
fixture = json.loads(raw)
assert fixture["version"] == "v2", f"{path} is {fixture['version']}, not v2"
assert "last_confirmed" not in fixture
```

On the truncated file, that fails loudly instead of passing over it. Four of the six occurrences on that run were in check code written specifically to catch this failure mode, which is why it belongs in the document rather than in somebody's memory—knowing about the trap did not prevent falling into it.

That rule is the first thing the next one owes. A clause whose job is proving an instrument discriminates—invert the assertion and confirm the check goes red—is itself a check that mutates its input, so it asserts the mutation landed before it reads anything into a survivor. `2026-08-11-issue-141`'s harness did exactly that: `assert repl in onDisk and needle not in onDisk` before every run. Without it an inversion that never applied reads as a mutation the suite survived, which fails a worker who did nothing wrong.

Four archived jobs rediscovered the rest of the family and each got a different part of it wrong: `2026-08-11-issue-100`, `2026-08-11-issue-141`, `2026-08-12-courier-lane-cleanup`, and `kendrick/dotfiles#22`. `2026-07-15-issue-20` is the exception worth knowing, because its C-5 is a `check-build.sh` pipeline mutating a regenerable build output—it passed at r0 with no FAIL anywhere in the run, and none of the venue apparatus below reaches it. A mutation clause routed to a script needs none of this. The rest is for the ones routed to `checker-judgment`, and that family is wider than mutation testing over a copied tree: `kendrick/dotfiles#22`'s C-5 mutated a test suite rather than a copied tree and still needed several of the rules that follow.

Wherever the mutation lands, it lands somewhere disposable and never in the job tree, because `checker-judgment` may not edit artifacts. A clause telling it to edit a file and revert afterward asks for something its role forbids: an honest checker returns `blocked` every round, and one obeying the clause mutates the artifact it was sent to judge. That cost `2026-08-12-courier-lane-cleanup` round 0 of the three its C-5 took. When the target is a suite rather than a tree, the venue is still named—the auditor's own apparatus directory is one—and the clause says which.

When the mutation target is a working tree, name the venue and name how the copy gets made. `cp -a` or `rsync -a`, because the copy has to carry uncommitted and untracked work, which is usually everything the job has built so far. `git clone --local` carries committed state only, so the copy cannot contain the work the clause was sent to mutate; that mistake cost `2026-08-12-courier-lane-cleanup` the second of three CON rounds on its C-5. Enumerate what to mutate from the task's artifact list rather than from a diff, since an uncommitted tree has no diff to read.

Put the venue and the enumeration source in the check line so no checker has to infer them—`checker-judgment: in a cp -a copy under its own mktemp -d outside the repo, invert one assertion at a time in the files the task's artifact list names, confirm each inversion is on disk, and confirm bats tests/ goes red for each` is the shape. The survivor rule below goes in the clause's `text` instead. A check line that spells out a conditional pass trips R9, which reads an instruction to pass alongside a defect word and cannot tell this clause from the ones it exists to catch. Phrase what the check does—record the category and the argument—and leave when a survivor is acceptable to the text.

Say in the clause's text that a surviving mutation is not automatically a finding, and say what a checker records instead. Some survivors are unreachable by construction and hardening against them is wasted work: `2026-08-12-courier-lane-cleanup` shipped with three across T-008 and T-009 that could not have changed the answer, since on a two-attempt crossing the only discarded attempt is the first, where the per-attempt clock and the cumulative clock nearly coincide and no fixture separates them. Each checker reasoned that out and supplied the category itself, correctly, though the clause never asked for it—a checker who did not would have reported covered behavior as uncovered. `kendrick/dotfiles#22` accepted its own last surviving attack on the same ground: the construction that survived is also red against a correct implementation, so it cannot arrive by accident. Ask for the category and the argument behind it, or the default reading of a survivor is another round.

Then hold the clause against the vacuity shapes that recur, each of which has cost a round somewhere in the archive:

- An invocation log shared across cases rather than owned by one. `kendrick/dotfiles#22`'s C-5 never said which, so a suite pooling its log through `BATS_SUITE_TMPDIR` went green against a broken implementation and satisfied the clause as written.
- Survivor and dropped-name patterns matched loosely. Same clause, same run: require exact matches, or a case meets every stated condition while asserting nothing that separates a fix from the bug.
- A check no conforming implementation can turn green. The `open(p, "w")` truncation above is this shape, and it reached `kendrick/skills#27`'s CON-audit-r2 as a defect in the clause rather than a bug in one check: every correct stamper reported a v1 skip while the headline string printed anyway.
- Wording that admits two readings producing materially different programs, the fork step 2 describes. It reaches a mutation clause through the task excerpt: `kendrick/dotfiles#22`'s DEC-audit-r0 built two faithful transcriptions a single gate expression apart, and only one satisfied a case the excerpt required.

The audit now fails the last two outright, so writing one costs a fresh CON round on amended bytes.

A job needing a mutation harness usually derives as deep; that is the `kendrick/dotfiles#21` row in step 1's fixture table. Watch the clause count while you add one, because a job at its ceiling pays for the next clause twice. `2026-08-19-issue-193`'s CON-audit-r1 found its constitution at budget and noted that closing two findings by adding a ninth clause would trip R18 and require an overrun line, while strengthening an existing check's assertions cost nothing. Reach for the existing clause first, and where the count has to go up anyway, record why in the `**Ceiling overrun**:` line R18 requires before the auditor dispatch.

Done when every clause has a concrete failing example, none is vague, no clause's text and check can disagree about the same artifact, every check that mutates its input asserts the mutation before anything else, and any clause proving an instrument discriminates asserts its mutations landed, names where they happen, and says in its text what a checker records for a survivor that could not have changed the answer.

## 4. Manifest protected words

If the interview surfaced words that must ship verbatim (taglines, quotes, legal copy), record them in a protected-passages manifest from `.agent-guild/templates/protected-passages.md`. Compute each hash from the exact text:

```
python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().rstrip("\n").encode()).hexdigest())'
```

Point every clause that guards protected content at `.agent-guild/scripts/check-protected.py <manifest>`. Skip this step only if nothing is protected.

## 5. Send it to audit

Dispatch the **auditor** with `Audit-ID: CON-audit`. Dispatch it rather than asking whether to: the audit is what verifies the constitution, so putting that choice to the user hands them the auditor's job. Until a CON-audit PASS verdict exists, `dispatch-guard` blocks every worker, so the constitution is verified before anything is built against it. If the audit fails, revise the flagged clauses and re-submit; do not route around it.

One exception, and only this one. When the clause count exceeds the recorded weight's ceiling, either the clauses are over-built or the weight was derived too light, and that call belongs to the user rather than the auditor. Put it to them as a single question naming the count against the ceiling—"9 clauses against standard's ceiling: re-weight to deep, cut one, or keep it and record why?"—and act on the answer. Re-weighting or cutting brings the count back under budget on its own; keeping it means writing the reason into the constitution's `**Ceiling overrun**:` line, since `check-job-spec.py`'s R18 blocks the auditor dispatch on an over-ceiling count that carries no such line. Everything else you are unsure about goes to the auditor, which is what it is for.

A PASS covers the text that was audited and nothing else. Edit a clause afterward and the gate closes again until another audit round passes on the current document, so batch late revisions into one round rather than trickling them in after the verdict. That PASS is also bounded by defect class, not only by text: a CON-audit settles what a clause carries on its own—a concrete check, text and check that agree, a describable failing example, a manifest that parses—but not anything whose falsifiability is a relationship to a schedule that doesn't exist yet. Clauses delegating coverage to other clauses, pairs that only contradict once someone builds the check, and claims turning on task order get re-opened by Phase 1's DEC-audit, so a PASS here isn't the last word on those.
