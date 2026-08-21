---
audit: DEC-audit
round: 0
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/tasks/
verdict: FAIL
checked_at: 2026-08-20T23:20:00Z
---

## Scope and method

Three tasks (T-001, T-002, T-003) read against `spec.md` and against
`constitution.md` at `ba971fec…`, the same bytes `CON-audit-r8.md.sha256`
binds and the same bytes r8's own apparatus recorded. `probe-183.py` reads
`5c65bb9b…`, matching what r8 recorded too, so the whole instrument stack sat
still between that PASS and this round.

`check-job-spec.py --audit-id DEC-audit` exits 0, so R1–R22 are already
proven and none of them is re-litigated here.

**Runs.** Every clause carrying a runnable check ran three ways: against the
tree as found, against a reference implementation built this round, and
against a variant built to violate that clause's own stated property. C-7 and
C-9 carry `checker-judgment:` rubrics, have nothing to execute, and were
judged by reading. Nothing was `blocked` and nothing went unexecuted — this is
a Claude host, so the Codex lane's scope note does not apply.

**Which tree.** This is a first pass through Phase 1: `dispatch-guard` has held
every worker behind this verdict, so no worker has built. The baseline sweep's
report is therefore read straight, not as the post-Phase-2 scope note.

```
python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .
check-baselines: ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)
exit 0
```

Every declared baseline held. Scope note on what the sweep did not cover: 2
clauses skipped as judgment (C-7, C-9), 0 for no baseline, 0 unclassifiable.
So the sweep reached 7 of 9 clauses, and the two it skipped are the two with
nothing to run.

**Apparatus.** `.agent-guild/state/apparatus/DEC-audit-r0/`, carrying
`SOURCE.sha256` over `constitution.md`, `spec.md`, all three task files, and
`probe-183.py`; `readingA/` and `readingB/` (two transcriptions of the same
clause texts); `variants/`. The venue I acted on was a whole-tree copy at
`/tmp/decr0-A-VkczyJ`, made with `git archive HEAD | tar -x` plus the
gitignored probe copied in, `git init`-ed there and never anywhere else. It
was removed by that exact printed path before filing, along with the 89
`probe183-*` directories the probes leave under `$TMPDIR`. One whole-tree copy
was alive at a time, never two.

`git status --porcelain` was empty when I started and is empty now. The
`__pycache__` the suites leave under `.agent-guild/hooks/` was removed and
`build-plugin.py --check` re-run green afterward.

**Comparand.** `CON-audit-r8`'s apparatus records the identical constitution
digest, so it is the comparand for the reference implementation. My own build
was whole first — readings A and B written, built, all seven runnable checks
run against both, and all six clause-violating variants run — before r8's
directory was opened. The diff is reported below.

## Per-task results

| task | executor / checker | clauses | routing | deps | finding |
| ---- | ------------------ | ------- | ------- | ---- | ------- |
| T-001 | worker-standard (sonnet) / checker-deterministic | C-1…C-6, C-8 | correct: every cited clause is script-checked, so checker-deterministic; clear-spec implementation, so worker-standard | none | none |
| T-002 | worker-standard (sonnet) / checker-judgment | C-9 | correct: C-9 is a rubric clause, so checker-judgment; the "would fail against pre-job behavior" property needs judgment, so not worker-bulk | T-001 (rationale holds) | **F1** (blocker), **F2** (major) |
| T-003 | worker-craft (opus) / checker-judgment | C-7 | correct: user-facing prose, so worker-craft; C-7 is a rubric clause, so checker-judgment | T-001 (rationale holds) | **F3** (minor) |

**Coverage.** Every spec section maps. Acceptance criteria 1→C-1, 2→C-2,
3→C-3, 4→C-3, 5→C-4 plus C-7, 6→C-5, 7→C-6, 8→C-8 plus C-9. The three open
questions are answered by the intake rulings bound into C-1/C-4/C-5 and
restated in T-001's excerpt; the spec's non-goals appear verbatim in the
constitution's. No spec requirement is uncovered. Criterion 8 is *mapped* but
not *verified* — see F1.

**DAG.** T-001 → {T-002, T-003}. No cycles, every referenced task exists.
T-002 and T-003 declare disjoint, well-formed `owns`
(`scripts/test_build_plugin.py`, `docs/installing.md`), so they ride one wave
after T-001, which is the right shape.

**dep_rationale, read against what the dep actually produces.** T-002's
("supplies the installer behavior these cases assert against; there is nothing
to regress before it lands") holds: T-001's artifacts are the installer and
the built trees, and I measured that against the pre-job installer there is no
record at all to assert on — C-1 through C-4 die at `provenance record
missing`. T-003's ("documenting it before it exists would describe an
intention") holds and is reinforced by C-7's own rubric, which says "against
the shipped implementation." Neither task could start earlier.

**T-001's `owns` is sufficient for its own regeneration.** I hashed every file
outside `plugin/` and `plugins/` before and after a `build-plugin.py` run in
the venue: no writes land anywhere else. The four entries cover the whole
task.

## Per-clause results

Each executed clause carries both runs the charter requires: green against a
faithful reference implementation, red against a variant violating the
clause's own text, with the assertion that decided it.

| clause | severity | tree as found (baseline) | reference impl | variant built to violate it | finding |
| ------ | -------- | ------------------------ | -------------- | --------------------------- | ------- |
| C-1 | blocker | red as declared: `provenance record missing: …/.agent-guild/provenance.json` | **green** | record written only on the `claude` branch (the clause's own failing example) → **red**, codex install rc=0 then `provenance record missing` | none |
| C-2 | blocker | red as declared, same assertion | **green** | per-file upgrade gated on the stamp trailing the plugin version → **red**, `a file clean against its record was skipped because the stamp matched` | none |
| C-3 | blocker | red as declared, same assertion | **green** | preserved file's entry refreshed from its on-disk bytes → **red**, `a preserved file's recorded hash was refreshed from its on-disk bytes` | none |
| C-4 | blocker | red as declared: `FileNotFoundError` removing a record that never existed | **green** | wholesale adoption, every existing file stamped at current bytes → **red**, `adoption recorded an entry for a file it refused` | none |
| C-5 | major | red as declared, same assertion | **green** | notice keyed on "a record exists" rather than the versions differing (the clause's own failing example) → **red**, `nudge reports a version gap on an up-to-date project` | none |
| C-6 | major | red as declared: `provenance record missing` | **green** | `provenance.json` appended to the gitignore block the installer writes → **red**, `provenance.json is gitignored; a tracked record must be addable` | none |
| C-7 | major | judgment rubric, nothing to execute; judged by reading | — | — | **F3** |
| C-8 | blocker | green as declared: 371 + 50 tests pass, `--check` OK | **green** on the reference impl (371 + 50 + `--check`) | a C-9-shaped case appended to `scripts/test_build_plugin.py` with a wrong record key → **red**, `50 passed, 1 failed`, rc=1 | **F1** |
| C-9 | major | judgment rubric, nothing to execute; judged by reading | — | — | **F1**, **F2** |

Nothing is `blocked`. Every runnable clause ran.

### Reading the constitution against the schedule

Three passes, run by enumeration across the whole document rather than stopped
at the first defect.

**Delegating notes — every one, listed and placed against the schedule.** Five
notes hand part of a clause's weight to something else. Four hold:

- C-1: "entries for files a run preserved are governed by C-3 and C-4
  instead." C-3 and C-4 sit in T-001 alongside C-1, checked in the same
  dispatch, and their probes build their own fixtures at check time. Holds.
- C-3: "leaves C-5's nudge firing every session with nothing that clears it."
  C-5 is in T-001. Holds.
- C-5: "the double-registration warning … already fires above the marker gate,
  which `test_hooks.py` pins, so moving it below is a regression this clause
  does not license." `test_hooks.py` runs under C-8, and C-8 is in T-001, the
  same dispatch as C-5. I did not take the pin on trust: I moved the whole
  double-registration block below the marker gate in the reference
  implementation and ran the suite. Four cases went red, starting with
  `plugin-rooted + copy-in settings.json → one double-registration warning
  rc=0 out=''`. The note is true, and it is true *at the right time*.
- Non-goals: "C-1 drives all three install shapes, and C-5 drives all three
  nudge deployments." All five clauses live in T-001. Holds, and the premise
  under it holds too — my reference implementation touched one shared
  `_sync_payload`, and c1's Codex and `--project-skills` arms went green off
  it.
- Preamble: "a task is not done until the build is regenerated — C-8's
  `--check` holds that." **This is the one that does not hold**, and it is F1.
  It holds for T-001, the only task that edits a build input. It does not hold
  for T-002, which edits `scripts/test_build_plugin.py` — not a build input,
  but one of the three commands C-8 *runs* — after C-8's only scheduled
  execution has already happened.

**Fixture constructibility — every check's precondition, built rather than
eyeballed.** Every probe builds its own venue and I ran all six; nothing in
the constitution makes any of those states unreachable. C-7's rubric names the
"#214 re-init table", which exists at `docs/installing.md:132-135` — the
fixture is real. C-9's rubric names a case in `scripts/test_build_plugin.py`
asserting on "the record's contents"; I constructed one, and constructing it
is where F2 surfaced.

**Task order.** F1 is the whole of it. Nothing else in the document turns on
when a task runs: no clause needs an artifact before its producer has run, and
the preamble fixes no cadence the DAG puts out of reach.

### The structural question: is T-001's cut right?

**The cut is acceptable. The reason recorded in the task file is not true, and
a better cut exists.**

T-001's excerpt says: "Splitting this across tasks would leave the earlier one
unverifiable, and only one task may regenerate." Both halves fail on
inspection.

Nothing in the constitution, in `CLAUDE.md`, or in `ready-set.py` restricts
regeneration to one task. What C-8's `--check` actually demands is that the
shipped trees match a fresh build *at the moment the check runs*, which any
task that regenerates what it changed satisfies. Two tasks both declaring
`owns: [plugin/, plugins/]` simply cannot ride one wave — they serialize,
which is what a dependency edge would do anyway.

And the earlier task is verifiable. I measured it: reading A's installer with
the **pre-job nudge left untouched**, rebuilt, gives

```
c1 PASS  c2 PASS  c3 PASS  c4 PASS  c5 FAIL  c6 PASS  C-8 PASS
```

So an installer-only task carrying C-1, C-2, C-3, C-4, C-6 and C-8 is fully
green at its own check time with no nudge work in the tree at all. C-5 is the
only clause that needs the nudge, and a second task carrying C-5 and C-8,
depending on the first and regenerating after its own edit, is verifiable in
turn.

The concrete alternative, if T-001 proves too large for one sonnet dispatch:

- **T-001a** — `scripts/plugin-src/install-project.py` + regenerate.
  `owns: [scripts/plugin-src/install-project.py, plugin/, plugins/]`,
  clauses `[C-1, C-2, C-3, C-4, C-6, C-8]`.
- **T-001b** — `.agent-guild/hooks/session-nudge.py` + regenerate.
  `deps: [T-001a]`, `owns: [.agent-guild/hooks/session-nudge.py, plugin/,
  plugins/]`, clauses `[C-5, C-8]`.

That split also happens to fix F1 for free, because C-8 lands on more than one
task and the last writer carries it.

I am **not** failing the round on the cut. One task for ~190 lines across two
files, with the probes as acceptance criteria, is a defensible dispatch — my
own reference implementation of the same contract went green first try. What I
am filing is that the justification in the task file is false, and a reader
who trusts it will not reach for the split when the retries start burning.

### Fork check, and what the comparand diff yielded

I enumerated every expression in the runnable clauses that admits a second
reading, built the second reading where one existed (`readingB/`), and ran the
full check set against it. **All seven runnable clauses are green against
reading B as well.** Four axes turned out to be genuinely free — the harness
accepts both ways, so they belong here rather than in the findings:

1. C-1's "that host package's own manifest": resolved by the `host` argument
   (A) or by probing the package root for whichever manifest dir exists (B).
2. C-5's same phrase for the nudge: same two readings.
3. C-5's "trails the running plugin's": read as "the versions differ" (A) or
   strictly older via parsed dotted integers (B). C-5's text says "trails" and
   its failing example says "the versions differing"; no probe separates them,
   because every fixture stamps `0.0.1` against a current release.
4. The record's serialization — indented and sorted (A) versus compact and in
   payload order (B).

None of these changes what the harness accepts, so none is a fork finding.

**The comparand.** `CON-audit-r8`'s `SOURCE.sha256` records
`ba971fec…` for the constitution — identical to mine — so its reference
implementation is a transcription of the same document and the diff is signal
rather than noise. It was opened only after my own build was whole; readings A
and B were both written, built and run, and all six variants had gone red,
before I read a byte of `CON-audit-r8/apply.py`.

**The diff yielded agreement.** r8's reference and mine diverge on exactly
three points, and all three are on the free axes above: r8 probes the
filesystem for the manifest on both the installer and the nudge (my reading
B's choice, not my reading A's), and r8 prints the version-gap notice above
the partial-init report where I print it below. Both readings run green under
every clause. Everywhere the clauses actually bind — per-file decision keyed
to the record and not the stamp, a preserved entry carried forward untouched,
adoption recording no entry for a refused file, the stamp advancing through a
refusal, the double-registration early return removed, the repo-local copy
returning `None` rather than raising — two independent transcriptions of the
same bytes landed on the same program. That is the strongest evidence this
round produces that C-1 through C-6 are well specified, and it is worth
recording as much as a divergence would have been. No findings keyed to any
clause come out of this step.

## Diagnosis

### Constitution defects (clause revision + a fresh CON round)

- **C-8** (blocker): the clause's own account of itself is "all pass **on the
  finished tree**." The schedule falsifies that. C-8 is cited by T-001 alone,
  so its only execution happens when T-001's checker runs — and T-002 writes
  `scripts/test_build_plugin.py` afterward, which is one of the three commands
  C-8 runs. The tree C-8 certifies is not the finished tree, and nothing
  re-runs it on the one that is.

  I measured the consequence rather than inferring it. Against a finished tree
  carrying a red `scripts/test_build_plugin.py` (`50 passed, 1 failed`, rc=1),
  every runnable `check_method` in the decomposition comes back green:

  ```
  T-001: C-1 PASS  C-2 PASS  C-3 PASS  C-4 PASS  C-5 PASS  C-6 PASS  C-8 FAIL*
  T-002: C-9  — rubric, nothing to run
  T-003: C-7  — rubric, nothing to run
  ```

  \* C-8 is red only because I ran it by hand. Under the schedule nobody does:
  T-001's checker has already finished, and neither T-002 nor T-003 cites it.

  That takes spec acceptance criterion 8 — "`python3
  scripts/test_build_plugin.py` … all pass, **with** coverage for the upgrade
  path, the refusal path, and a mixed run" — out of reach of the whole job.
  C-9 covers the "with coverage" half; C-8 covers the "all pass" half; and the
  conjunction is exactly what no dispatch ever evaluates. C-9's rubric will
  not catch it either: it asks a checker to read what a case asserts and
  reason about whether it would fail against pre-job behavior, and never asks
  whether the case passes now.

  **The clause repair**: C-8's text should say which tree it means in terms a
  decomposer can schedule against — that every task writing an input to any of
  those three commands carries C-8 — rather than naming a "finished tree" that
  no clause obliges anyone to produce. That is a clause revision and another
  CON round; the amended bytes re-close the Phase 0 gate on their own.

  **The task repair, which keeps the job moving** (file it too, and file it as
  T-002 below): add C-8 to T-002's `clauses` and its `check_method`. I verified
  this is sufficient rather than assuming it: none of C-8's three commands
  reads `docs/installing.md`, so T-003 cannot break C-8, and T-002 is the last
  task that touches anything C-8 runs.

- **C-7** (minor): C-7's text enumerates four behaviors plus the #214 re-init
  table, and that enumeration is what the checker holds T-003 to. It omits the
  one sentence in `docs/installing.md` that the rest of this constitution
  depends on. `docs/installing.md:137` — "`install()` splits them out of the
  payload before the drift check runs" — is the definitional anchor for the
  payload scope, cited by name in the preamble's record contract, in C-1's own
  text, and in `probe-183.py`'s docstring and `payload_files()` comment. T-003
  owns that file and its excerpt tells the worker to rewrite the paragraph
  around that sentence. If the sentence goes, C-1's text becomes a dangling
  reference on the finished tree and nothing catches it: C-1 has already been
  checked, and C-7 does not ask.

  T-003's excerpt does tell the worker to keep the distinction, which is why
  this is minor rather than major. But the excerpt is not what the checker
  checks against.

  **Repair**: name the payload/`_copy_owned` split among the things C-7
  requires `docs/installing.md` to state — clause revision, fresh CON round —
  and, in the meantime, add it to T-003's `check_method`.

### Task defects (re-cut; no CON round needed for these)

- **T-002** (blocker, the task half of C-8 above): cite C-8 in `clauses` and
  add its invocation to `check_method`:

  ```
  C-8: .agent-guild/scripts/check-build.sh 'rm -rf plugins/agent-guild/hooks/__pycache__ plugin/hooks/__pycache__ .agent-guild/hooks/__pycache__ && python3 .agent-guild/hooks/test_hooks.py && python3 scripts/test_build_plugin.py && python3 scripts/build-plugin.py --check'
  ```

  This is what makes T-002's own edits answerable to the blocker that says the
  suites are green, and it is the only place in the schedule where a run of
  C-8 sees the finished tree.

- **T-002** (major): the task asks for cases asserting on "the record's
  contents" and points the worker at nothing that says what the record looks
  like. T-002 cites C-9 alone. C-9's text says "asserts on the installed bytes
  or the record's contents" without describing either. The record's shape is
  pinned in the constitution's preamble and restated in C-1 — neither of which
  T-002 cites — and the key format is the trap: project-root-relative and
  `/`-separated, `.agent-guild/scripts/ready-set.py`, **not** the
  payload-relative `scripts/ready-set.py` that `_copy_missing`, `_copy_owned`
  and the existing suite all use.

  I did not reason this into existence. Building the T-002 stand-in for F1, I
  reached for the idiom the surrounding suite uses and wrote
  `_after["files"]["scripts/ready-set.py"]`. It raised `KeyError`. That is
  precisely the mistake a worker following T-002's own advice — "the existing
  suite already holds the shapes you need … follow those rather than inventing
  a new idiom" — is being steered into.

  This compounds with the finding above rather than sitting beside it. T-002's
  excerpt never tells the worker to run the suite before reporting done, where
  T-001's excerpt does ("Run the probes yourself before you report done"). So
  a worker can write a red case, not run it, and no check in the job will run
  it either.

  **Repair**: quote the preamble's record contract in T-002's excerpt (or cite
  C-1 alongside C-9), and add one line telling the worker to run `python3
  scripts/test_build_plugin.py` before reporting done.

- **T-003** (minor, the task half of C-7 above): add to `check_method` that
  `docs/installing.md` must still draw the payload versus `_copy_owned` line
  that C-1's text and `probe-183.py` both cite by reference.

- **T-001** (advisory, not blocking): the excerpt's justification for the cut
  is false — "Splitting this across tasks would leave the earlier one
  unverifiable, and only one task may regenerate." Measured above: an
  installer-only task is green on six of the seven runnable clauses with the
  nudge untouched, and nothing restricts regeneration to one task. Either
  strike the claim or replace it with the true reason, which is that one
  dispatch is cheaper than two when the contract is this well specified. The
  cut itself stands.

### What clears this

F1 is the one that fails the round. Two of the four repairs are task re-cuts
the orchestrator can make now (T-002's C-8 citation, T-002's record-contract
pointer and run-it instruction). Two are clause revisions that send the job
back to Phase 0 for a CON round on the amended bytes (C-8's schedule
obligation, C-7's split-line requirement). Since C-8's task-level repair and
its clause-level repair are the same defect seen from two ends, doing only the
re-cut would leave the next decomposition to trip over the clause again — do
both.

Nothing here touches the constitution's substance. C-1 through C-6 came
through this round intact: every one discriminates in both directions, and two
independent transcriptions of their text produced the same program.
