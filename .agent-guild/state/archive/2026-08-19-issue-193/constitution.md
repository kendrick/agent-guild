# Constitution: three defect shapes the linter can catch mechanically (#193)

**Job weight**: deep, corrected from standard by the user, because verification turned out to need an instrument built rather than one invoked—a ~750-line probe harness, a reference implementation rebuilt by each audit round, and a "done" the spec states as a property (discriminating cases drawn from the archive) no existing command can check

<!--
Job source: kendrick/agent-guild#193. Three independently landable fixes to
`.agent-guild/scripts/check-job-spec.py`, each for a defect shape that cost
`kendrick/dotfiles#22` an audit round the linter could have saved.

WHY THE CHECKS LOOK LIKE THIS. C-1 through C-4 check a BEHAVIOR of the linter
and run a probe at `.agent-guild/state/checks/probe.py` rather than reading the
test suite. C-6, C-7 and C-8 check the tree around it and invoke commands that
already exist. C-5 and C-9 are rubrics: both hand the checker a probe to run
and then ask for a ruling its exit code cannot give, which is what #141's
prohibition on *scripts* leaves open. #141
spent three audit rounds proving why: a check that greps test SOURCE was
satisfied by seven appended comment lines, and a check that greps test RUNTIME
OUTPUT was satisfied by `check("<label>", True, "")`, a case asserting nothing.
A check cannot tell a real test from a written one. Each probe instead builds
an artifact, runs the shipped linter over it, and reads what the linter did.

The probes were run against the tree as this job finds it, and each baseline
below is that observed result rather than an intention. Of the seven clauses
carrying one, two fail today and five pass; C-5 and C-9 are rubrics and carry
none. A pass declared red would be exactly the #141 defect the baseline field
exists to catch.

Every probe carries a control in the opposite direction, because a rule that
stops firing altogether would satisfy both no-regression clauses by accident.
`r10-adjective` asserts the bare count still fires and a correct count still
stays silent; `r10-corpus` asserts the same call it sweeps with does fire on a
known-bad fixture; `r21-unsafe` proves its fixture clean before mutating it.

FIXTURES ARE SYNTHETIC wherever a probe constructs one, and drawn from the
archive wherever the archive is itself the instrument: C-2's sweep, and C-9's
symlinked corpus plus its requirement that the suite's own new cases be
archive-drawn. The synthetic half is not a preference. The linter reports only
the first violation across all rules, so a fixture tripping anything ahead of
the rule under test measures nothing—and the archived #117 corpus trips that
way, citing `conventions.md:65` for a bullet that has since moved, firing R3
four rules ahead of R2. The archive-drawn half is not a preference either: a
no-regression sweep over invented inputs proves nothing about regressions.

SPEC DIVERGENCE, ruled by the user rather than inherited, and LIVE rather than
historical. `spec.md`'s R2 criterion asks for the anchor's line "distinct from
the two line numbers it already reports." That is false whenever the anchor
sits on the citing line, which CON-audit r2 demonstrated, and an implementation
honoring it literally is either wrong or silent on the ordinary case. C-5
overrides that sentence. Anything excerpting the spec into a worker's brief
must carry C-5's text instead of the criterion's.

READING THE REVISION NOTES BELOW. Everything from `REVISION r1` onward is a
history, one entry per revision, each describing the document as it stood
then. Clause ids and counts inside those notes mean what they meant at the
time: the constitution was eight clauses through the document CON-audit r2
read, nine at r3, ten at r4 and r5, and nine again from r6 onward, once C-9's
machinery was cut and C-10 folded into it. No `REVISION` note is a statement
about the current text, and a decompose step should excerpt the clauses rather
than that history. Three paragraphs are LIVE rather than historical and are
not covered by this guard: the SPEC DIVERGENCE ruling above, `RULE NUMBERING`
below, and this one.

REVISION r8, after CON-audit r6 failed with two blockers and five lesser
findings — all of them in C-9's wording or in the text its probe prints into a
checker's lap, and none asking for the cut mechanism back. The round's real
result was the opposite of a finding: two faithful implementations, one with
the R10 relaxation in `_governs_plural_noun` and one in `find_r10_violation`,
both passed all seven script-checked clauses. The constitution determines an
implementation now, and does not over-determine its factoring.

The first blocker was r5's blocker relocated, and it turned on a fixture that
could not reach the case it claimed to cover. `wrapper_is_live` measured the
probe's own `ANCHOR_TEXT`, which carried no quote characters, so `repr()` had
nothing to escape and the by-value strip looked correct for every quoting
style. The corpus anchor an archive-drawn case must actually quote
(`archive/2026-08-10-issue-117/tasks/T-001.md:57`) contains both `"` and `'`,
where `repr()` escapes them and a raw-form strip matches nothing — so an
`!r`-quoting implementation was told its wrapper worked and then failed for
"no case asserts the anchor is quoted," against a suite whose case asserted
exactly that. Worse than r5's version, because the affirmative liveness line
forecloses the "the seam does not match this factoring" reading the rubric
otherwise offers. The fixture anchor now carries both quote characters, the
wrapper strips the raw and `repr` forms, and liveness accepts the anchor in
any form on both sides. Re-verified across backticks, `!r`, and no quoting,
and against a decoy whose message never carried the anchor.

The second blocker was a requirement dropped from the text but left standing
in the check: folding C-10 into C-9 lost r4's declaration of the
`r2_anchor_message` seam, so an inline diagnostic passed C-5 and the whole
suite and then failed a seam nothing had asked for. The text declares it
again, and the rubric now says how to rule when it is absent — against the
seam requirement, not against test coverage.

The majors: `revert_adjacency`'s printed detail still told a worker to move
the modifier walk into the predicate, contradicting the rubric two paragraphs
above it that calls the caller-side factoring legitimate; a checker weighting
machine output over prose would have failed correct work. All three git reads
went blind on a STAGED tree — `git status --porcelain` shows `M ` so the
FAIL-on-empty rule does not fire, but neither diff carries content — so the
first read is now `git diff HEAD`. The history guard written in r7 was true of
the revision notes and false of the SPEC DIVERGENCE ruling sitting below it,
licensing a decompose step to skip the one paragraph that keeps the spec's
wrong R2 sentence out of a brief; the ruling moved above the guard and the
guard now names what it covers. And C-9 claimed `.agent-guild/state/` is
"gitignored in full," which `.gitignore:5-6` contradicts by un-ignoring
`archive/` — 378 tracked files, and the exception is precisely what lets C-9's
own archive-drawn cases keep working.

C-10's failing example, dropped in the fold, is restored as C-9's second one.

RULE NUMBERING. The routing rule takes R21. R20 is the highest defined, taken
by #139's lint-exception guard. This pushes #190's proof rule to R22, and
#190's issue text still suggests R20.

REVISION r1, after CON-audit r0 failed with one blocker and five lesser
findings. The blocker was C-3, and it was the kind only an audit that builds
things finds: the round wrote a variant of R21 that reads the task's own
`check_method` instead of the constitution's clause, and it passed all eight
clauses. The fixture made the two indistinguishable, because `task()`
interpolates a clause's check text verbatim into `check_method` and the task
cited exactly one clause. That variant names the wrong clause on any task
citing several—36 of the archive's 40 tasks—and refuses legal dispatches at a
proof exit code, which `rule_R20` gives no waiver path. C-3's fixture now
cites two clauses with the rubric second and asserts the innocent one is NOT
named; C-4 picks up the false-positive shape, a deterministic task whose check
command merely contains the string `checker-judgment:`.

The rest: C-7 claimed to catch a hand-edited generated tree and cannot, since
an allowlist sees paths and not provenance (verified—the hand-edit exits 0),
so C-6 owns that alone now. C-5's text demanded the anchor's line differ from
the two already reported, which is false whenever the anchor sits on the
citing line. C-2 counted `>= 11` archives, a floor rather than a census. The
weight line's stated reason was wrong—six of eight clauses run a probe
harness written for this job—so the reason changed and the weight did not.

REVISION r2, after CON-audit r1 failed with two majors, both on C-5, plus two
minors. C-5 is now the clause two consecutive rounds have found a defect in,
which is one round short of `conventions.md`'s rule to cut a mechanism rather
than patch it a third time. It is being patched rather than cut because it
carries a required acceptance criterion of the spec—cutting it would drop
coverage—and because both repairs move the contract out of C-5's prose and
into the probe, which is the direction that stops the recurrence. If a third
round finds a defect in C-5, cut it and re-derive.

Both majors were the same failure in different clothes: C-5's text made a
claim the probe never exercised. `r2-anchor` hard-coded a two-line gap between
citation and anchor, so the implementation that omits the anchor's line
exactly when it equals the citing line passed all eight clauses—r1 built it.
And the probe had no silence control, so replacing the guard that keeps R2
quiet when the quoted span is absent from the whole target file also passed
everything, shipping a linter that refuses correct paperwork. The probe now
runs three cases: anchor away from the citation, anchor on the citing line,
and a span absent from the target that must stay silent.

The minors: C-2's census failed a green blocker on an archive directory
carrying a constitution and no tasks, which is what a job abandoned between
Phase 0 and Phase 1 leaves behind, and it returned before sweeping anything.
It now sweeps every directory carrying a constitution. R21's placement in
`run_rules` was an unpinned fork—every clause stayed green whether the rule
ran before or after the heuristics, while the choice decides whether an author
sees an unwaivable proof or a waivable guess first. C-3's text now pins it and
`r21-unsafe` carries a fixture with both defects to keep that falsifiable.

REVISION r3, after CON-audit r2 failed with three majors. The weight changed
here, from standard to deep, on the user's call: r2's third major showed the
spec's test-suite criterion covered by nothing, and the ninth clause that
closes it would have run over standard's ceiling. The evidence had been
accumulating anyway—verification needed a ~750-line probe harness built, every
audit round rebuilt a full reference implementation, and the spec's own "done"
names a property no existing command checks. That is deep's definition, so the
overrun was a symptom of a weight derived a rung too light rather than of a
constitution one clause too fat. The derived value stays in the weight line.

C-5 was CUT and re-derived, not patched a third time. r2 found a third defect
in it, which is the condition r2's own predecessor note committed to. Its
probe survived the cut—all three cases discriminate correctly—and only the
text was re-derived, now stating exactly what the probe checks and no more.
The specific overreach: case B demanded the anchor's line number appear twice,
which silently settled a fork the clause had left open, failing an
implementation that writes "on that same line" and reads better for it. The
wording is now the author's choice and the clause says so.

C-1 was pinned against one word. Both its adjective cases were built on
`further`, so a two-word allowlist and an `er/ly/ing/ed` morphology gate each
passed all eight clauses. It now runs five adjectives sharing no stem or
suffix. C-3's placement claim was pinned against one heuristic of four, and
`RULE_CLASS` marks R2, R9, R10, and R12—so R21 sitting between R9 and R10 also
passed. R2 is both the earliest heuristic `run_rules` reaches and the rule this
job edits, which makes it the binding case; the probe now pins both R2 and R10.

REVISION r4, after CON-audit r3 failed with two blockers. C-5 is now a
JUDGMENT clause. Four consecutive rounds found a defect in it, the cut was
already spent, and every one of those defects was the same shape: a pattern
match trying to decide whether a human-readable sentence states a position.
r3's variant printed "the anchor ... is not on that line; it is at
src/fixture.py:29"—stating no position at all—and satisfied a regex looking
for the phrase `that line`. #141 hit this exact wall and its constitution
records the resolution: no amount of pattern-hardening changes what a regex
can read, so the behavioral claim moves to a rubric where a checker who
re-derives is the right instrument. `probe.py r2-anchor` survives as that
checker's tool, running the three fixtures and printing the diagnostics for a
person to rule on, and its remaining assertions are mechanical only—R2 fires
on A and B, stays silent on C.

C-9's second blocker was its R2 escape hatch, which said the gap "closes
through C-5 instead." That was false when written and doubly false now that
C-5 is a rubric: C-5's probe lives in the very harness C-9 exists because it
vanishes. C-9 now carries four seams rather than three, and requires the R2
diagnostic to be built by a function named `r2_anchor_message` so the quoted
anchor can be stripped while every older R2 case stays standing. A blunt stub
took those down too and passed for the wrong reason.

Three of r3's majors: `revert_adjacency`'s guard compared an unterminated
join against a newline-terminated file and so reported every no-op revert as
landed—a FALSE FAIL that would have cost a worker a retry for a correct
implementation. C-1's five fixed adjectives fell to a six-word allowlist, so
one is now a nonce generated from the run's pid, which no allowlist written
beforehand can contain and C-8's stdlib-only rule leaves no dictionary to
resolve. And C-9's stub of `nearest_anchor` was cut as dead weight, since it
proved coverage that predated this job.

C-10 is new, closing the half of the spec's sixth criterion nothing covered:
that the added cases be drawn from the archive rather than invented. No
script can judge that—#141 forbids grepping test source precisely because a
script cannot tell a real case from a written one—but a checker reading the
diff can, so it is a rubric. R21 now also owes an explicit `PROOF` entry in
`RULE_CLASS` rather than riding the unrecognized-rule default.

REVISION r5, after CON-audit r4 failed with two blockers, five majors and two
minors. Both blockers were in checks written for r4 itself, and both were
false FAILs—the kind that fails correct work rather than passing broken work.

C-9's R2 wrapper was appended to the END of the copied linter, below
`if __name__ == "__main__": sys.exit(main())`. The suite runs the linter as a
subprocess, so the interpreter exits at that guard and the redefinition never
ran. C-9 was red against every possible implementation, which its blocker
severity turned into a job that could not be completed. It survived a whole
round because it was the one mutation in that probe asserting nothing about
whether it took effect—the exact rule this document's own preamble states.
The wrapper is now spliced above the LAST `__main__` guard (the literal occurs
twice; the first is inside the self-test's fixture strings), and a companion
assertion runs the wrapped linter and confirms the anchor is really gone from
the diagnostic.

C-1's nonce carried digits, so an implementation whose modifier class mirrors
the shipped predicate's own alphabet—`[A-Za-z][A-Za-z-]*`, straight from the
code—failed on a token that is not a word under any reading of the clause's
own term "adjectives." Meanwhile `zqx`/`ish` were fixed affixes in a file any
worker can read, so the allowlist hole never closed. The modifiers are now
three letters-only tokens invented at run time with no shared affix.

The majors, all in the two rubrics and the preamble: C-5's rubric never told
the checker its probe's exit code decides anything, so an implementation with
the silence guard removed—whose [A] and [B] output is byte-identical to a
conforming one's—passed a checker doing exactly what the rubric said. It said
"three diagnostics" over two printed blocks, and "Case C must print nothing at
all" of a case that prints two `ok` lines: a count disagreeing with what it
counts, which is the defect R10 exists to catch, in this job's own
constitution. Case C now prints its own block reading `(nothing emitted)`, and
the rubric leads with the exit code. C-10's "read the diff" named no base ref
and went empty the moment the work was committed; it now names a merge-base
diff. C-10's synthetic-case hatch asked the checker to verify nothing and
contradicted its own failing example—the archive carries all three shapes, so
a synthetic case is now a FAIL. Three preamble claims had gone stale against
the clauses they describe.

C-5's severity went back to blocker. It had been major since r0 with no
recorded reason, and it carries a required acceptance criterion.

REVISION r6, after CON-audit r5 failed with three blockers and three majors.
All three blockers were clauses that FAIL correct work rather than pass broken
work, which is now the recurring shape and worth naming: every check added to
close a hole in rounds 3 through 5 has been over-tight in its first version.

C-9's R2 wrapper stripped by DELIMITER, matching only a backticked anchor,
while C-5's rubric tells the checker punctuation does not count. An
implementation quoting with `!r`—the house style in this very file, at R3 and
R12'—passed C-5 and failed C-9 with a message asserting the opposite of the
truth. And `wrapper_is_live`, added in r5 precisely to catch a wrapper that
lands without taking effect, tested for the absence of a backtick, so it could
not tell "the anchor was stripped" from "there was never a backtick to
strip"—blind in exactly the direction it existed to watch. The wrapper now
strips by VALUE, removing its own `anchor` argument from whatever the seam
returns, which makes it indifferent to quoting style and puts C-9 back in
agreement with C-5. Verified across backticks, `!r`, and no quoting at all,
and against a decoy whose message never carried the anchor.

C-9's second blocker was a seam it never declared. It spelled out the R2
constraint and said of R10 only "reverted to its strict pre-job body," while
the spec's own "Start here" names both `_governs_plural_noun` and its caller
`find_r10_violation`. A worker putting the modifier walk in the caller passes
C-1 and C-2 and every archive sweep, then fails C-9 at blocker severity with
an empty detail string. Both seams are now stated as requirements on the
implementation, and that assertion carries a detail naming what to move where.

C-10 named a merge-base diff that reads COMMITTED history, and nothing in the
guild lifecycle commits a worker's output—a checker is dispatched against the
working tree. A conforming, uncommitted implementation read zero lines, and
the clause said nothing about what an empty read means. It now names all three
reads and rules that an empty one is a FAIL rather than a pass. That repair
had a partner: the same commit making C-10 readable empties C-7, whose
`check-diff-scope.py` unions two working-tree-only queries and reports zero
paths in scope on a committed tree. C-7 now pins the state it reads.

The majors: the preamble's r5 repair made its claim more enumerable and
therefore plainly false—"every SCRIPT-checked clause runs a probe" is wrong
for C-6, C-7 and C-8, and C-6 runs the very suite the sentence says nothing
reads. It now enumerates the sets correctly. And C-1's nonce could be drawn
ending in `s`, which IS the plural noun to `[A-Za-z][A-Za-z-]*s\b`: the phrase
fires on the untouched tree and the case reports ok against an implementation
that changed nothing, measured at 10.8% of runs. Draws ending in `s` are now
rejected, and the drawn tokens print so a failure can be replayed.

REVISION r7, made on the user's direction after r6's first dispatches were
lost to API errors, and the version CON-audit r6 actually read. C-9's mutation
machinery was CUT to a judgment instrument, and C-10 folded into it. The reason is the one `conventions.md` names: two
consecutive rounds found a blocker in the same mechanism, so it gets cut
rather than patched a third time. r4's blocker was the wrapper appended below
`sys.exit(main())`, never executing. r5's were the wrapper stripping by
delimiter instead of by value, and a seam the clause never declared. All three
were FALSE FAILS—clauses that refuse correct work—and all three lived in the
AST-mutation, splice, and injection code rather than in the standard.

That is the same cut C-5 took after four rounds, and for the same reason. The
mutations were never wrong about what to ask; they were wrong about being the
final word. As a script check, a bug in the splice logic fails a correct
worker outright. As evidence a checker reads, a `FAIL: revert changed nothing`
becomes a thing a person looks at and rules on—and the legitimate
implementation that put the relaxation in the caller, which r5 built and which
C-9 refused at blocker severity, is now something the rubric names and tells
the checker how to handle.

Folding C-10 in removes a duplication r4 asked about: both clauses were about
the suite, one about whether its cases discriminate and one about where their
inputs come from. One rubric carries both questions, and the archive-drawn
half keeps the FAIL-on-empty rule and the no-synthetic-cases ruling that r5
established. Nine clauses now, seven script-checked and two rubrics.

-->

## Clauses

### C-1: R10 fires through an intervening adjective
- **text**: R10 reports a count-versus-list mismatch when adjectives separate the number from the plural noun it governs, so `Four further rules constrain how:` above three bullets is caught exactly as `Four rules constrain how:` already is.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r10-adjective'
- **baseline**: red
- **severity**: blocker
- **failing example**: `_governs_plural_noun` still matches only the token immediately after the number, so a clause block reading `Four further rules constrain how:` above a three-item list exits 0 and the linter reports nothing.

### C-2: relaxing R10 adds no false positive to any archived job
- **text**: R10 stays silent on every archived job under `.agent-guild/state/archive/` — every directory carrying a constitution, whether or not it also carries tasks — so the relaxed adjacency introduces no new firing on work that already shipped.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r10-corpus'
- **baseline**: green
- **severity**: blocker
- **failing example**: the relaxation matches a number against any plural noun later on the line, so `2026-08-11-issue-100`'s constitution reports a mismatch between an issue id and an unrelated list beneath it.

### C-3: R21 fails a deterministic checker holding a judgment clause
- **text**: A task declaring `checker: checker-deterministic` while citing a clause whose check begins `checker-judgment:` is a proof-class violation naming the task id and the offending clause id, and no other clause the task cites. The clause kind is read from the constitution, not from the task's `check_method` paraphrase of it, because that agent runs scripts and exercises no judgment and the rubric cannot be applied at all. The rule runs ahead of the heuristics, so paperwork carrying both a routing defect and an inferred one reports the unwaivable proof rather than the waivable guess, and it carries an explicit `PROOF` entry in `RULE_CLASS` rather than relying on the unrecognized-rule fallback.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r21-unsafe'
- **baseline**: red
- **severity**: blocker
- **failing example**: a task carrying `checker: checker-deterministic` and `clauses: [C-1, C-2]`, where C-1 is script-checked and C-2 carries the rubric, is reported against C-1 — the clause its own `check_method` happens to name — while C-2, the clause that actually cannot be checked, goes unmentioned.

### C-4: R21 stays silent on the safe direction
- **text**: Both legal routings exit 0 — a `checker-judgment` task citing only script-checked clauses, and a `checker-deterministic` task citing only script-checked clauses whose command contains the literal `checker-judgment:` as an argument. R21 fires on the clause's kind, never on a string appearing in a task's own check command.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r21-safe'
- **baseline**: green
- **severity**: blocker
- **failing example**: R21 compares the two fields for equality rather than for the one harmful direction, so a `checker-judgment` task citing a `check-build.sh` clause is refused and a routing that has always been legal starts blocking dispatches.

### C-5: R2 names the anchor it matched and where it sits
- **text**: An R2 diagnostic quotes the anchor text the rule matched and states where that anchor sits in the citing document, so an author can tell a wrong citation from a wrongly-chosen anchor in one pass. Both positions read correctly: an anchor on a line of its own, and an anchor sharing the citation's line. R2 stays silent exactly where it is silent today — a quoted span absent from the whole cited file is evidence the span was never that citation's anchor, not evidence the citation is wrong.
- **check**: checker-judgment: run `python3 .agent-guild/state/checks/probe.py r2-anchor`. It must exit 0 — a nonzero exit is a FAIL on its own and settles the clause before you read anything, because its assertions are the mechanical half (R2 fires on A and B, stays silent on C). Then read the three blocks it prints, `[A]`, `[B]`, and `[C]`, and rule on the two that carry a diagnostic: is the anchor quoted, and can a reader tell where that anchor sits without opening the file? `[C]` must read `(nothing emitted)`. Judge the sentences, not their punctuation; a message saying the anchor is on the citing line satisfies this as fully as one repeating the number.
- **severity**: blocker
- **failing example**: the message still names the citing document's line, the line cited, and the line the target's matching code was found on, and stops there — three numbers, none of which is where the quoted anchor sits in the document, and no quotation of the anchor text at all, leaving an author to permute prose until the rule goes quiet.

### C-6: every consumer suite stays green
- **text**: All four of these commands exit 0 against the delivered tree, because `dispatch-guard` runs `check-job-spec.py` as a gate and the builder rebuilds it into both published plugin trees, so a change to it has consumers beyond its own suite.
  - `python3 .agent-guild/scripts/test_check_job_spec.py`
  - `python3 .agent-guild/scripts/check-job-spec.py --self-test`
  - `python3 .agent-guild/hooks/test_hooks.py`
  - `python3 scripts/build-plugin.py --check`
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/scripts/test_check_job_spec.py && python3 .agent-guild/scripts/check-job-spec.py --self-test && python3 .agent-guild/hooks/test_hooks.py && python3 scripts/build-plugin.py --check'
- **baseline**: green
- **severity**: blocker
- **failing example**: R21 is added to the source tree and `build-plugin.py` is never re-run, so `--check` reports the published trees no longer match a fresh build.

### C-7: the diff touches only the source tree and its generated views
- **text**: The working tree's diff stays inside the authored linter, its suite, and the generated trees `build-plugin.py` rewrites, so no unrelated file rides along. This clause reads the **uncommitted** working tree and is checked before anything is committed: `check-diff-scope.py` unions `git status --porcelain` with `git diff --name-only`, both working-tree only, so against a committed implementation it sees zero paths and passes without checking anything. Whether a generated tree was rebuilt or hand-edited is C-6's question, not this one — an allowlist sees paths, not provenance.
- **check**: .agent-guild/scripts/check-diff-scope.py .agent-guild/scripts/check-job-spec.py .agent-guild/scripts/test_check_job_spec.py plugin/ plugins/ --ignore .agent-guild/state/
- **baseline**: green
- **severity**: major
- **failing example**: a worker fixes R2's diagnostic and also edits `.agent-guild/hooks/dispatch-guard.py` to match, which this job never authorized and `conventions.md` forbids routing through the guild at all.

### C-8: the linter stays stdlib-only
- **text**: `check-job-spec.py` imports nothing outside the Python standard library, because hooks run it as a bare `python3` call with no venv, so a third-party import becomes `HOOK ERROR` and exit 2 for every dispatch in every project running the kit.
- **check**: .agent-guild/scripts/check-build.sh 'python3 -X importtime -c "import importlib.util,sys; s=importlib.util.spec_from_file_location(\"m\",\".agent-guild/scripts/check-job-spec.py\"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)" >/dev/null 2>&1 && python3 -c "import ast,sys; t=ast.parse(open(\".agent-guild/scripts/check-job-spec.py\").read()); mods={(n.module or \"\").split(\".\")[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom)} | {a.name.split(\".\")[0] for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names}; bad=sorted(m for m in mods if m and m not in sys.stdlib_module_names); sys.exit(1 if bad else 0)"'
- **baseline**: green
- **severity**: blocker
- **failing example**: the R2 diagnostic work reaches for `regex` instead of `re` for a lookbehind, and every guild dispatch in every consuming project starts failing its gate.

### C-9: every change has a discriminating case in the shipped suite
- **text**: Each of the three changes has a case in `test_check_job_spec.py` that goes red when that change is reverted, and each of those cases is built from the archived corpus under `.agent-guild/state/archive/` in the mutation style the suite already uses — take real shipped paperwork, change one line, assert the rule fires. Both halves matter and neither substitutes for the other. A case that cannot fail proves nothing, and a case built from invented paperwork cannot show that real paperwork would have been caught. One seam is required of the implementation: **the R2 diagnostic is built by a function named `r2_anchor_message`, taking the matched text as a parameter named `anchor`.** Without a named seam there is no way to remove the anchor while leaving R2's older cases standing, and a blunt stub takes those down too. R10 gets no such requirement — the relaxation may live in `_governs_plural_noun` or in `find_r10_violation`, both of which the spec's "Start here" names, and the rubric says how to check the second.

This is the job's only lasting regression net. `.gitignore:5-6` ignores `.agent-guild/state/*` and then un-ignores `archive/`, so the corpus these cases draw from is tracked and travels while the probe harness every other clause runs is not, and is deleted at teardown. The suite is what remains.
- **check**: checker-judgment: run `python3 .agent-guild/state/checks/probe.py suite-coverage` and treat its output as evidence rather than as a verdict. It stubs `rule_R10` and `rule_R21`, reverts `_governs_plural_noun` to its strict pre-job body, and wraps `r2_anchor_message` to strip the anchor's own text — each mutation should turn the suite red. Where one does not, decide whether the suite is genuinely missing a case or the probe's seam simply does not match how this worker factored the code: a relaxation living in `find_r10_violation` rather than the predicate is a legitimate implementation the revert cannot reach, and there the question is whether some case still fails when you undo the relaxation by hand. If the probe reports no `r2_anchor_message` seam, that IS a finding — the clause's text requires it — but rule it against the seam requirement rather than against test coverage, and check the R2 case by hand before deciding whether coverage is also missing. The same goes for a seam the probe finds but cannot strip through: the wrapper binds the matched text by the parameter name `anchor`, so a seam naming that parameter something else fails liveness while behaving correctly. The probe skips its coverage mutation in that case rather than reporting a coverage failure it did not measure. Rule it against the seam requirement, check the R2 case by hand, and do not spend a worker's retry on a test that already exists. Then read the added cases — `git diff HEAD -- .agent-guild/scripts/test_check_job_spec.py`, which covers staged and unstaged work alike, falling back to `git diff $(git merge-base main HEAD)..HEAD -- .agent-guild/scripts/test_check_job_spec.py` for already-committed work and `git status --porcelain -- .agent-guild/scripts/test_check_job_spec.py` for an untracked file if that is empty — scoped to the path, because a bare `git status --porcelain` reports every other file the job touched and so is never empty, which would keep the FAIL-on-empty rule from ever firing — and rule on where each case's input comes from. If every read is empty, no cases were added and this clause FAILS; an empty read is never a pass. The archive carries an instance of all three shapes, so a synthetic case is a FAIL rather than a judgment call.
- **severity**: blocker
- **failing example**: two of them. All three fixes land, every script-checked clause passes, and `test_check_job_spec.py` is untouched — so the repo ships three linter behaviors whose only regression net was the probe harness, and teardown deletes it. Or the suite gains three cases that do discriminate, each built on a hand-written constitution rather than the corpus, so it proves the rules fire on paperwork nobody ever filed while `dotfiles#22`'s actual `Three further rules constrain how:` line goes untested.

## Protected content

- none. This job ships no author copy that must survive verbatim.

## Non-goals

- **The `owns` overlap between a task and its own dependency during rework.** #193 raises it as an open question rather than a criterion, and it stays unruled here. When an invalidated dep is re-dispatched while its dependent is mid-flight both run, and overlapping `owns` means two writers on one path with nothing detecting it — but R13 and `ready-set.py` each have a defensible reason for passing it today, so ruling on it is its own job.
- **Anything `#22`'s auditors caught by execution.** Those were reference-implementation and discrimination defects, which belong to #119 and #191, and no linter reaches them.
- **Validating `executor_model` against `executor`'s tier.** `dispatch-guard` already refuses a dispatch whose model disagrees with the recorded `executor_model`.
- **R2's anchor-selection algorithm.** The #132 heuristic and its sentence scoping stay exactly as they are; only the diagnostic changes, so an author can tell a wrong citation from a wrongly-chosen anchor in one pass.
