---
audit: DEC-audit
round: 1
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/tasks/
verdict: FAIL
checked_at: 2026-08-21T00:40:00Z
---

## Scope and method

Four tasks (T-001…T-004) read against `spec.md` and against `constitution.md`
at `229ac266…` — the bytes `CON-audit-r9.md.sha256` binds, so the Phase 0 PASS
covers the text I read. `probe-183.py` reads `5c65bb9b…`, the same instrument
`CON-audit-r8`, `DEC-audit-r0` and `CON-audit-r9` all recorded, so the harness
has not moved across any of those rounds.

`check-job-spec.py --audit-id DEC-audit` exits 0, so R1–R22 are already proven
and none is re-litigated here.

**Runs.** Every clause carrying a runnable check ran three ways: against the
tree as found, against a reference implementation built this round, and
against a variant built to violate that clause's own stated property. C-7 and
C-9 carry `checker-judgment:` rubrics, have nothing to execute, and were
judged by reading. Nothing was `blocked`; nothing went unexecuted. This is a
Claude host, so the Codex lane's scope note does not apply. `CON-audit-r9`
ran C-1 through C-6 against the tree as found only and said so plainly; this
round supplies the two runs it deferred.

**Which tree.** First pass through Phase 1 for this cut: `dispatch-guard` has
held every worker behind a DEC PASS, so no worker has built. The baseline
sweep's report is read straight, not as the post-Phase-2 scope note.

```
python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .
check-baselines: ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)
exit 0
```

Every declared baseline held. Scope note on what the sweep covered: 7 of 9
clauses; the 2 skipped (C-7, C-9) are the two with nothing to run, 0 skipped
for having no baseline, 0 unclassifiable.

**The venue.** One whole-tree copy at `/tmp/decr1.XO5w3s`, made with
`git archive HEAD | tar -x` plus the gitignored `probe-183.py` copied in, and
`git init`-ed there and nowhere else. Every mutation was applied in place and
reverted from saved reference copies rather than re-cloning, so exactly one
whole-tree copy existed at a time. Probe venues were confined to
`TMPDIR=/tmp/decr1.XO5w3s.tmp`. Both paths were removed by those exact printed
names before filing, and the six `probe183-*` directories the baseline sweep
left in the system tmpdir were removed by explicit path.
`PYTHONDONTWRITEBYTECODE=1` was set on every run, and C-8's own check clears
the three `__pycache__` paths — I read that `rm -rf` before running it; all
three targets are untracked build byproducts.

`git status --porcelain` was empty when I started and is empty now.

**Apparatus.** `.agent-guild/state/apparatus/DEC-audit-r1/`, carrying
`SOURCE.sha256` over `constitution.md`, `spec.md`, all four task files,
`probe-183.py` and `docs/installing.md`; `apply-ref.py` (the reference
implementation), `t002-cases.py` (the T-002 stand-in), `variants.py` and
`break-it.sh` (the six clause-violating mutations), `fork-probe.py`, `ref-src/`
and two run logs.

**Comparand: `CON-audit-r9`.** Its `SOURCE.sha256` records `229ac266…` for the
constitution and byte-identical digests for all four task files, so it is a
transcription of the same documents and the diff is signal rather than noise.
**My own build was whole first** — installer and nudge written, regenerated,
all seven runnable checks green, the T-002 stand-in written and green, and all
six clause-violating variants run red — before I listed the contents of
`CON-audit-r9/ref-src/`. The diff yielded one material divergence and is the
finding below. (`DEC-audit-r0` records `ba971fec…` and superseded task files,
so it is not a comparand for anything built from these bytes.)

## Per-task results

| task | executor / checker | clauses | routing | deps | finding |
| ---- | ------------------ | ------- | ------- | ---- | ------- |
| T-001 | worker-standard (sonnet) / checker-deterministic | C-1, C-2, C-3, C-4, C-6, C-8 | correct: every cited clause is script-checked → checker-deterministic; clear-spec implementation judged on correctness → worker-standard | none | none |
| T-002 | worker-standard (sonnet) / checker-judgment | C-9, C-8 | correct: a task citing one rubric clause and one script clause routes to the checker that can do both, and checker-deterministic (haiku) cannot do C-9's "would it fail against pre-job behavior" reasoning | T-001, T-004 (both rationales hold) | none |
| T-003 | worker-craft (opus) / checker-judgment | C-7 | correct: user-facing prose → worker-craft; C-7 is a rubric clause → checker-judgment | T-001 (rationale holds) | none |
| T-004 | worker-standard (sonnet) / checker-deterministic | C-5, C-8 | correct: both cited clauses are script-checked → checker-deterministic; C-5 is unusually specific, so clear-spec → worker-standard | T-001 (rationale holds) | **F1** surfaces here (keyed to C-5) |

**Coverage.** Every spec section maps. Acceptance criteria 1→C-1, 2→C-2,
3→C-3, 4→C-3, 5→C-4 plus C-7, 6→C-5, 7→C-6, 8→C-8 plus C-9. The three open
questions are answered by the intake rulings bound into C-1/C-4/C-5 and
restated in the T-001 and T-004 excerpts; the spec's non-goals appear in the
constitution's. No spec requirement is uncovered, and criterion 8 — the
conjunction DEC-r0 measured out of reach — is now both mapped and verified,
because T-002 carries C-8 and is the last task in the schedule to write an
input to any of its three commands.

**DAG.** T-001 → {T-003, T-004}; {T-001, T-004} → T-002. No cycles, every
referenced task exists. Run rather than read: `ready-set.py` against the tasks
as they stand returns `wave: [T-001]`; with T-001 complete it returns
`wave: [T-003, T-004]` with T-002 deferred on `unmet deps: T-004`; with T-004
at `needs-check` it returns `wave: [T-002]` carrying
`speculative_on: ["T-004"]`. Three waves, and the two regenerating tasks are
serialized by a dep edge rather than by an `owns` collision — which is the
right shape, since an `owns` collision would only defer them within a wave and
would not order their checks.

**dep_rationale, read against what the dep actually produces.**

- T-002 → T-001 ("supplies the installer behavior these cases assert against,
  and the record format they read"): holds. I built T-002's three cases from
  its excerpt and ran them against the pre-job installer; every one dies at
  `FileNotFoundError: …/.agent-guild/provenance.json`. There is nothing to
  assert on before T-001 lands.
- T-002 → T-004 ("the last task before this one to write a build input, so C-8
  here is the run that sees the tree the job ships"): **a real edge, not
  scheduling theater.** `session-nudge.py` is mirrored by `build-plugin.py`
  into `plugin/hooks/`, `plugins/agent-guild/hooks/` and the Codex
  `project-template/` payload, and `test_hooks.py` execs it directly — so
  T-004's artifact is read by two of C-8's three commands. Without the edge,
  T-002 and T-004 declare disjoint `owns` and would ride one wave, which puts
  T-002's C-8 run in a race with T-004's regeneration and defeats C-8's own
  "last such task" sentence. The edge is what makes that sentence true of this
  schedule.
- T-003 → T-001 ("documenting it earlier would describe an intention"): holds,
  and C-7's rubric reinforces it by saying "against the shipped
  implementation."
- T-004 → T-001 ("writes the provenance record this notice reads; with no
  record there is no version to compare and probe c5 cannot build its
  fixture"): holds, and it is stronger than it reads. Probe c5's first act is
  `fresh(tmp)` followed by `load_prov(tmp)`, which asserts the record exists;
  against the pre-job installer it dies there before reaching any nudge
  assertion.

**Both regenerating tasks are verifiable at their own check time.** I measured
the schedule rather than reasoning about it. With T-001's work in the tree and
the nudge left at HEAD: `c1 c2 c3 c4 c6` all pass, C-8 passes
(`371 passed, 0 failed`; `50 passed, 0 failed`; `--check OK`), and `c5` fails —
which is correct, since T-001 does not cite C-5. Adding T-004's nudge and
regenerating brings `c5` green with C-8 still green. Adding T-002's three
cases on top gives `371 passed` / `56 passed` / `--check OK`. The terminal
check of the schedule is satisfiable on the tree the job actually ships.

**`owns` is sufficient for both regenerations.** I hashed every file outside
`plugin/` and `plugins/` (excluding `.git` and `state/`) before and after a
`build-plugin.py` run in the venue: no writes land anywhere else, so
`sync_dogfood()`'s `.claude/` target stays untouched while `guild-core/` does.
T-001's and T-004's four-entry declarations cover their whole footprint.

## Per-clause results

Each executed clause carries both runs: green against a faithful reference
implementation built this round, red against a variant violating the clause's
own text, with the assertion that decided it.

| clause | severity | tree as found (baseline) | reference impl | variant built to violate it | finding |
| ------ | -------- | ------------------------ | -------------- | --------------------------- | ------- |
| C-1 | blocker | red as declared: `provenance record missing: …/.agent-guild/provenance.json` | **green** | record written only on the `claude` branch (the clause's own failing example) → **red**, codex install rc=0 then `provenance record missing` | none |
| C-2 | blocker | red as declared | **green** | per-file upgrade gated on the stamp trailing the plugin version → **red**, `a file clean against its record was skipped because the stamp matched` | none |
| C-3 | blocker | red as declared | **green** | preserved file's entry refreshed from its on-disk bytes → **red**, `a preserved file's recorded hash was refreshed from its on-disk bytes` | none |
| C-4 | blocker | red as declared | **green** | wholesale adoption, every existing file stamped at current bytes → **red**, `adoption recorded an entry for a file it refused` | none |
| C-5 | major | red as declared | **green** | notice keyed on "a record exists" rather than the versions differing (the clause's own failing example) → **red**, `nudge reports a version gap on an up-to-date project: "…installed by version 0.7.1; the running plugin is 0.7.1…"` | **F1** |
| C-6 | major | red as declared | **green** | `provenance.json` appended to the gitignore block the installer writes → **red**, `provenance.json is gitignored; a tracked record must be addable` | none |
| C-7 | major | judgment rubric, nothing to execute; judged by reading | — | — | none |
| C-8 | blocker | green as declared: `371 passed, 0 failed`; `50 passed, 0 failed`; `--check OK`, rc=0 | **green** on the finished tree (`371` / `56` / `--check OK`) | T-002's three cases present against the pre-job installer → **red** rc=1, reaching C-8's own logic (`test_hooks.py` returned `371 passed, 0 failed` first, then `test_build_plugin.py` died at `FileNotFoundError: …/provenance.json`) | none |
| C-9 | major | judgment rubric, nothing to execute; judged by reading | — | — | none |

Nothing is `blocked`. Every runnable clause ran.

One result worth recording because it is what makes C-9 non-redundant: the
existing suites pass **unchanged** against a full reference implementation of
C-1 through C-6 (`371 passed, 0 failed`; `50 passed, 0 failed`). Not one
existing case notices whether provenance exists, which is exactly the premise
the constitution's preamble states and C-9 is written to close.

### Reading the constitution against the schedule

Three passes, by enumeration across the whole document.

**Delegating notes — every one, listed and placed against the schedule.** Six
notes hand part of a clause's weight elsewhere. All six hold, and the two
DEC-r0 failed are the two the repairs targeted:

- C-1: "entries for files a run preserved are governed by C-3 and C-4
  instead." C-3 and C-4 sit in T-001 alongside C-1, checked in the same
  dispatch, and their probes build their own fixtures. Holds.
- C-3: "leaves C-5's nudge firing every session with nothing that clears it."
  C-5 now lives in T-004 rather than beside C-3 — but nothing is delegated
  here. C-3's own probe asserts the stamp advances (`a run that preserved a
  file left the stamp at …`). The sentence is motivation, not coverage. Holds.
- C-5: "the double-registration warning … already fires above the marker gate,
  which `test_hooks.py` pins, so moving it below is a regression this clause
  does not license." `test_hooks.py` runs under C-8, and **T-004 cites C-8**,
  so the pin fires in the same dispatch as C-5. I did not take the pin on
  trust: I hoisted the marker gate above the double-registration block in the
  reference implementation and ran the suite. Five cases went red, starting
  with `plugin-rooted + copy-in settings.json → one double-registration
  warning  rc=0 out=''` (`366 passed, 5 failed`). True, and true at the right
  time.
- C-7 and the preamble both point at `docs/installing.md`'s split sentence
  rather than restating it. T-003 owns that file and rewrites the paragraph
  around it, and by then C-1's own check has already run — so C-7 is the only
  thing standing between that sentence and deletion. C-7's text now requires
  it and T-003's `check_method` carries it verbatim. Holds; this is DEC-r0's
  F3, repaired at both ends. The artifact is real: `docs/installing.md:137`
  carries the sentence.
- Non-goals: "C-1 drives all three install shapes, and C-5 drives all three
  nudge deployments." C-1 in T-001, C-5 in T-004; each probe drives what its
  clause claims, and the waiver for C-2 through C-4 is about code paths rather
  than schedule — my reference implementation routes all three through one
  host-agnostic `_sync_payload`, and c1's Codex and `--project-skills` arms
  went green off it. Holds.
- Preamble: "a task is not done until the build is regenerated — C-8's
  `--check` holds that." **This was DEC-r0's F1 and it now holds.** Every
  build-input writer in the schedule cites C-8: T-001
  (`scripts/plugin-src/install-project.py`, `plugin/`, `plugins/`), T-004
  (`.agent-guild/hooks/session-nudge.py`, `plugin/`, `plugins/`), T-002
  (`scripts/test_build_plugin.py`, which is one of the three commands).

**C-8's new sentence, checked against this schedule.** "Every task that writes
an input to any of those three commands cites this clause, so the last such
task in the schedule is the one whose check reads the tree the job actually
ships." Enumerated: the three commands' inputs are `scripts/plugin-src/**`,
`guild-core/**`, `.agent-guild/**`, `docs/plugin-readme.md`, `CHANGELOG.md`,
both marketplaces, `plugin/`, `plugins/`, `.claude/`, and the two suites
themselves. Three of the four tasks write into that set and all three cite
C-8. The fourth, T-003, owns `docs/installing.md`, and I verified rather than
assumed that it is outside the set: `build-plugin.py` reads exactly one path
under `docs/` (`PLUGIN_SRC_README = docs/plugin-readme.md`, copied to
`plugin/README.md`), and neither suite references `docs/` at all. T-003
correctly does not cite C-8. T-002 is last by the DAG, so its C-8 run is the
one that reads the shipped tree — measured above at `371` / `56` /
`--check OK`.

**Fixture constructibility — every check's precondition built, not eyeballed.**
All six probes built their own venues and all six ran green against the
reference implementation, so nothing in the constitution makes any of those
states unreachable. C-7's rubric names the "#214 re-init table", which exists
at `docs/installing.md:132-135` and says what the task claims it says. C-9's
rubric names cases asserting on "the record's contents"; I constructed all
three from T-002's excerpt alone, and this time the record-contract quote in
that excerpt was sufficient — I wrote
`record["files"][".agent-guild/scripts/ready-set.py"]` straight from the
excerpt's warning and got no `KeyError`. DEC-r0's F2 is repaired, and the
repair is verified by construction rather than by reading.

**Task order.** Nothing else in the document turns on when a task runs. No
clause needs an artifact before its producer has run, and the preamble fixes
no cadence the DAG puts out of reach. One state worth naming and dismissing:
`ready-set.py` will dispatch T-002 speculatively while T-004 sits at
`needs-check`, so T-002's C-8 can run against an unverified nudge. That is the
contract's one-level speculation working as documented — T-004's artifact
exists, and a later T-004 FAIL invalidates T-002 and re-runs its C-8.

### Fork check, and what the comparand diff yielded

**The divergence.** `CON-audit-r9`'s reference nudge and mine agree everywhere
the clauses bind — manifest resolution by probing the package root, the
repo-local copy returning `None` rather than raising, the notice placed below
the marker gate and above the partial-init early return, the message carrying
both versions plus the host's own command and a question. They disagree on one
thing: r9 keeps the double-registration `return 0`, moved below the version
notice, so the warning still short-circuits the partial-init report. Mine
drops the return entirely.

**Both readings run green.** I applied r9's reading to my own nudge and ran
the clause's own harness: `probe c5: ok`, and `371 passed, 0 failed` from
`test_hooks.py`. C-5's check cannot see the difference, because its
double-registration arm uses a fully installed project and its partial-init
arm is not double-registered — the combined state appears in no arm.

**The difference is material and the state is reachable.** I built a project
that is double-registered *and* partially initialized *and* stale-stamped, and
ran both readings against it:

```
reading B (CON-audit-r9's)     reading A (mine)
registered twice : True        registered twice : True
version gap      : True        version gap      : True
partial-init     : False       partial-init     : True
```

That is a user-visible difference in exactly the shape of project C-5 names —
"#104 says this repo is in that state" — decided by an expression the clause
leaves free. Filed as **F1** against C-5.

**What the agreement is worth recording for.** Everywhere else, two
independent transcriptions of these bytes landed on the same program:
`_sync_payload`'s decision structure is line-for-line equivalent (net-new
copied and recorded; no entry → adopt only on a source match, otherwise no
entry at all; entry mismatch → preserve and carry the recorded hash forward
untouched; entry match → upgrade against source and restamp), the record is
`{"version", "files"}` sorted and indented, the stamp is read from whichever
manifest sits beside the package root, and the version advances through a
refusal. C-1 through C-4 and C-6 are well specified, and this is the strongest
evidence this round produces of it.

## Diagnosis

### Constitution defects (clause revision + a fresh CON round)

- **C-5** (major clause; the divergence itself is minor in consequence): the
  clause's account of what the notice must survive admits two readings that
  ship different behavior, and its check accepts both. The expression they
  turn on is:

  > The notice is independent of both early returns above it: … and in a
  > project where the plugin is registered twice, where the double-registration
  > warning returns early — #104 says this repo is in that state — so every
  > applicable message appears in the same run.

  **Reading A**: "every applicable message" means all of them, so the
  double-registration early return goes, and a double-registered *and*
  partially initialized project gets the partial-init report too.
  **Reading B**: the notice must merely be independent of that return, which
  stays where it is, moved below the notice — preserving today's behavior,
  where a double-registered project never hears about a half-finished install.

  I did not reason this into existence. `CON-audit-r9`'s own reference
  implementation is reading B; mine, built independently from the same bytes,
  is reading A. Both pass `probe-183.py c5` and both pass `test_hooks.py`, so
  no check in this job separates them, and the measured output difference is
  the table above.

  Neither reading regresses anything — B is the status quo and A is an
  improvement — so this is not a defect about to ship. What it costs if left
  standing is a dispute: a worker who picks B satisfies every check in the
  job, and a checker who reads C-5's sentence strictly fails the task anyway,
  on a retry budget of two, over an ambiguity in the orchestrator's own clause.

  **The clause repair**: say which one. One sentence in C-5 settling whether
  the double-registration early return survives the notice — and, if reading A
  is meant, an arm in the probe driving the combined state, since a clause
  whose text asserts a property its check never exercises is how this got
  here.

  **The task repair, which keeps the job moving** (make it too, alongside the
  clause revision): T-004's excerpt item 4 currently inherits the ambiguity
  verbatim — "It fires above both early returns in the file … so every
  applicable message appears in one run." Add one sentence naming the
  decision, e.g.: *"The double-registration warning no longer returns early:
  in a project that is both double-registered and partially initialized, all
  three messages print."* That closes it for T-004 and leaves C-5 admitting
  both readings for the next decomposition, which is why both repairs are
  owed.

### Advisory (not blocking, no round owed)

- **Preamble**: "Because workers edit `scripts/plugin-src/` and the probes read
  the built `plugin/` tree, a task is not done until the build is regenerated."
  The conclusion holds and C-8 enforces it. The premise now names one of the
  schedule's two build-input writers — T-004 edits `.agent-guild/hooks/`, not
  `scripts/plugin-src/`. T-004's excerpt covers the gap explicitly ("Run
  `python3 scripts/build-plugin.py` last — `.agent-guild/hooks/session-nudge.py`
  is a build input"), so nothing is at risk; the sentence is just narrower than
  the job it describes. Worth widening whenever C-5 is revised, at no extra
  cost.

### Task defects

None. All three of DEC-r0's task-level findings are repaired and each repair
was verified by construction rather than by reading: T-002 cites C-8 and is
demonstrably the schedule's last writer of a C-8 input; T-002's record-contract
quote was sufficient to write all three C-9 cases first try, with the
project-root-relative key format that broke DEC-r0's stand-in; T-003's
`check_method` carries the split-line requirement. T-001's false justification
is gone, and the split the advisory offered is now T-001/T-004 — measured
sound in both directions above.

### What clears this

One clause revision and one task sentence. C-5 gets a sentence naming which
side of the double-registration early return the notice lives on; the amended
bytes re-close the Phase 0 gate on their own, so a fresh CON-audit round is
owed on them. T-004's excerpt gets the matching sentence in the same pass. No
task needs re-cutting: the decomposition's shape, routing, DAG, coverage and
dependency rationales all hold, and everything that runs in it runs green on a
faithful implementation and red on a violating one.

### What this round did not run

Said plainly. I did not build a second full transcription of the installer
clauses (C-1 through C-4, C-6). `DEC-audit-r0` enumerated four free axes there
and found the harness accepts both readings on all four, and my build
converged with `CON-audit-r9`'s on every point where those clauses bind — so
the axis-hunting budget went to the one document that had changed, and to the
comparand diff, which is where F1 came from. The system tmpdir holds roughly
3,450 `ag-hooktest-*` and `ag-nudge-*` directories left by earlier rounds; the
bulk removal was denied by the sandbox classifier, so they are still there.
None is mine: my own runs were confined to `TMPDIR` under the venue, and the
six `probe183-*` directories the baseline sweep left outside it were removed
by explicit path.
