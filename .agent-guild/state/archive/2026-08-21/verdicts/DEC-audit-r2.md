---
audit: DEC-audit
round: 2
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/tasks/
verdict: PASS
checked_at: 2026-08-21T01:05:00Z
---

## Scope and method

Four tasks (T-001…T-004) read against `spec.md` and against `constitution.md`
at `62257a2a…`, which is the digest `CON-audit-r10.md.sha256` binds, so the
Phase 0 PASS covers exactly the text I read. `probe-183.py` reads `5c65bb9b…`,
the same instrument every round since `CON-audit-r8` recorded, so the harness
has not moved under any of this.

`check-job-spec.py` exits 0 under both audit ids; R1–R22 are proven mechanically
and none is re-litigated here.

**What this round ran, and what it did not.** The C-5 repair is the only thing
that moved since r1, so the round was spent there. Every runnable clause ran
against the tree as found (the baseline sweep) and against a reference
implementation I built this round: `c1`–`c6` and C-8, seven of seven, all green.
The break-it step was spent on C-5: four variants built to violate its own
stated properties, plus the r1 fork's reading A. I did **not** rebuild
clause-violating variants for C-1–C-4 and C-6. r1 built and ran all five
against byte-identical probe bytes and each went red at the clause's own
assertion; a probe's discriminating power is a property of the probe, and the
probe has not changed. What could have changed is the text-to-probe fit, and
that I did re-measure rather than assume: my transcription was built this round
from the current clause text alone and passes all six probes, so text and check
still name the same artifact. C-7 and C-9 carry `checker-judgment:` rubrics,
have nothing to execute, and were judged by reading. Nothing is `blocked`.
This is a Claude host, so the Codex lane's read-only scope note does not apply.

**Which tree.** Still the first pass through Phase 1 for this cut: no DEC PASS
has ever opened `dispatch-guard`, so no worker has built and the baseline
sweep's report is read straight rather than as the post-Phase-2 scope note.

```
python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .
check-baselines: ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)
exit 0
```

Every declared baseline held. Scope: 7 of 9 clauses swept; the 2 skipped are
C-7 and C-9, the two with nothing to run; 0 skipped for having no baseline, 0
unclassifiable.

**The venue.** One whole-tree copy at `/private/tmp/decr2.AgCF5q`, made with
`git archive HEAD | tar -x` plus the gitignored `probe-183.py` copied in, then
`git init`-ed there and nowhere else. Probe venues were confined to
`TMPDIR=/private/tmp/decr2.AgCF5q.tmp`. Each variant was applied by restoring
the nudge from that venue's own base commit and re-patching, never by cloning
again, so exactly one whole-tree copy existed at any moment. Both paths were
removed by those exact printed names, along with the six `probe183-*`
directories the baseline sweep left in the system tmpdir. `PYTHONDONTWRITEBYTECODE=1`
on every run; C-8's own check clears the three `__pycache__` paths and I read
that `rm -rf` before running it — all three targets are untracked byproducts.

`git status --porcelain` was empty when I started and is empty now.

**Apparatus.** `.agent-guild/state/apparatus/DEC-audit-r2/`, carrying
`SOURCE.sha256` over the constitution, the spec, all four task files,
`probe-183.py`, `docs/installing.md`, and the two files the reference patches;
`apply-ref.py` (the reference implementation of the installer and the nudge),
`apply-nudge.py` and `break-it.sh` (the variant driver), `fork-probe.py` (the
combined state), and `ref-src/`.

## Per-task results

| task | executor / checker | clauses | routing | deps | finding |
| ---- | ------------------ | ------- | ------- | ---- | ------- |
| T-001 | worker-standard (sonnet) / checker-deterministic | C-1, C-2, C-3, C-4, C-6, C-8 | correct: every cited clause is script-checked → checker-deterministic; clear-spec implementation judged on correctness → worker-standard | none | none |
| T-002 | worker-standard (sonnet) / checker-judgment | C-9, C-8 | correct: one rubric clause and one script clause route to the checker that can do both; checker-deterministic (haiku) cannot do C-9's "would it fail against pre-job behavior" reasoning | T-001, T-004 (both rationales hold) | none |
| T-003 | worker-craft (opus) / checker-judgment | C-7 | correct: user-facing prose → worker-craft; C-7 is a rubric clause → checker-judgment | T-001 (rationale holds) | none |
| T-004 | worker-standard (sonnet) / checker-deterministic | C-5, C-8 | correct: both cited clauses are script-checked → checker-deterministic; C-5 is unusually specific, so clear-spec → worker-standard | T-001 (rationale holds) | none (the r1 finding is closed; see below) |

**Coverage.** Every spec section maps, re-derived rather than carried over:
acceptance criteria 1→C-1, 2→C-2, 3→C-3, 4→C-3, 5→C-4 plus C-7, 6→C-5, 7→C-6,
8→C-8 plus C-9. The three open questions are answered by the intake rulings
bound into C-1/C-4/C-5 and restated in the T-001 and T-004 excerpts. The spec's
non-goals appear in the constitution's. No spec requirement is uncovered.

**DAG, run rather than read.** `ready-set.py` against the tasks as they stand
returns `wave: [T-001]` with T-002, T-003 and T-004 deferred on unmet deps. No
cycles; every referenced task exists. T-001 → {T-003, T-004}; {T-001, T-004} →
T-002, so T-002 is last and its C-8 run is the one that reads the shipped tree.

**dep_rationale.** All four edges held in r1 against what each dep actually
produces, and none of the four tasks' `deps` or `dep_rationale` bytes changed:
T-001, T-002 and T-003 are byte-identical to what r1 read, and T-004's only
edit is inside its `## Spec excerpt`. Re-verified this round rather than taken
on trust, because it was cheap: T-004 → T-001 still holds by construction —
probe `c5`'s first act on every arm is a real install followed by `load_prov()`,
so with no record the arm dies before reaching any assertion about the notice,
which is why every variant run below kept the installer half at the reference.
T-002 → T-004 still holds: `session-nudge.py` is a build input that
`build-plugin.py` mirrors into both packages and `test_hooks.py` execs, so
T-004's artifact is read by two of C-8's three commands, and without the edge
the two would ride one wave and race.

## Per-clause results

Each executed clause carries both runs: the tree as found, and a reference
implementation built this round. C-5 additionally carries the round's variants.

| clause | severity | tree as found (baseline) | reference impl | variant built to violate it | finding |
| ------ | -------- | ------------------------ | -------------- | --------------------------- | ------- |
| C-1 | blocker | red as declared (sweep) | **green** — `probe c1: ok` | not rebuilt this round; r1's red stands against byte-identical probe bytes (scope note above) | none |
| C-2 | blocker | red as declared (sweep) | **green** — `probe c2: ok` | not rebuilt this round (as above) | none |
| C-3 | blocker | red as declared (sweep) | **green** — `probe c3: ok` | not rebuilt this round (as above) | none |
| C-4 | blocker | red as declared (sweep) | **green** — `probe c4: ok` | not rebuilt this round (as above) | none |
| C-5 | major | red as declared (sweep) | **green** — `probe c5: ok` | four built, three red at the clause's own logic, one caught by C-8 in the same dispatch — see the table below | **A1** (advisory, not blocking) |
| C-6 | major | red as declared (sweep) | **green** — `probe c6: ok` | not rebuilt this round (as above) | none |
| C-7 | major | judgment rubric, nothing to execute; judged by reading | — | — | none |
| C-8 | blocker | green as declared: `371 passed, 0 failed`; `50 passed, 0 failed`; `--check OK` | **green** on the reference tree (`371` / `50` / `--check OK`, rc=0) | marker gate hoisted above the double-registration block → **red**, `366 passed, 5 failed`, first failure `plugin-rooted + copy-in settings.json → one double-registration warning  rc=0 out=''` | none |
| C-9 | major | judgment rubric, nothing to execute; judged by reading | — | — | none |

Nothing is `blocked`. Every clause carrying a runnable check ran.

### C-5's variants, in detail

| variant | what it violates | result |
| ------- | ---------------- | ------ |
| `gap-on-record-exists` | C-5's own failing example: keyed on "a record exists" rather than the versions differing | **red** — `nudge reports a version gap on an up-to-date project: "…installed by version 0.7.1; the running plugin is 0.7.1…"` |
| `notice-below-dblreg` | "the notice sits above both early returns … so it prints before either can return" | **red** — `the version gap is lost when the plugin is registered twice` |
| `compiled-in-version` | "read at run time … provably, since a copy of the package whose manifest reads a version nothing else carries is reported as that version" | **red** — `the codex nudge does not read its own package's manifest` |
| `hoist-marker-gate` | "moving it below is a regression this clause does not license" — the delegating note | c5 **green**, C-8 **red** (`366 passed, 5 failed`). The note is true and true at the right time: T-004 cites C-8, so `test_hooks.py` fires in the same dispatch. |
| reading A (r1's fork) | "This job moves the notice above them and **removes neither**" | c5 **green**, C-8 **green** — see **A1** |

## The C-5 settlement, checked at the schedule level

**The fork is closed in the text, in both documents.** C-5 now says the notice
sits above both early returns, that "those returns keep their current behavior,"
that this job "removes neither," and that a project both double-registered and
partially initialized "prints the notice and the double-registration warning and
not the partial-init report." T-004's excerpt item 4 says the same thing in its
own words — "Move the notice above them; do not remove either return" and the
same three-message sentence. A worker reading only the excerpt and the
constitution has no route to reading A: it is named and forbidden twice, and
neither document leaves the question open.

**Two independent transcriptions now agree, which is the strongest evidence the
repair worked.** My reference and `CON-audit-r10`'s, built from the same amended
bytes by different rounds, produce the same behavior in the state r1's fork
turned on:

```
                       DEC-r2 (mine)   CON-r10 (comparand)   reading A
registered twice     : True            True                  True
version gap          : True            True                  True
partial-init report  : False           False                 True
```

r1's divergence was exactly the third row, and it is gone.

**What remains is an unchecked assertion rather than a fork — filed as A1.**
Under the settled reading, C-5's combined-state sentence is a no-regression
claim, and nothing in the job exercises it. Probe `c5`'s F5 arm drives a
double-registered project that is fully installed; its arm 5 drives a partially
initialized project that is not double-registered; the combined state appears in
no arm, and `test_hooks.py`'s double-registration cases all run against projects
with no marker, where the version notice is silent by jurisdiction anyway. I
measured it rather than reasoned it: reading A — the double-registration
`return 0` deleted — passes `probe c5`, `test_hooks.py` (371/0),
`test_build_plugin.py` (50/0) and `build-plugin.py --check`. Every check in the
job is green against an implementation C-5's amended text forbids.

That is a real gap and it is a small one, which is why it is advisory rather
than a finding that fails the round. Reaching it takes deliberately deleting a
return that both documents say to keep; the three plausible ways a conforming
worker could get the placement wrong all go red (two on `c5`, one on C-8); and
the behavior it lets through is one extra accurate message in a rare state,
which C-5 itself puts out of scope to rewrite. What it costs if left standing is
smaller than what r1's fork cost, because no correct reading now leads there.

## Reading the constitution against the schedule

Three passes, by enumeration across the whole document, re-derived this round
rather than inherited.

**Delegating notes — every one, listed and placed against the schedule.**

- C-1: "entries for files a run preserved are governed by C-3 and C-4 instead."
  Both sit in T-001 alongside C-1, checked in the same dispatch, and their
  probes build their own fixtures. Holds.
- C-3: "leaves C-5's nudge firing every session with nothing that clears it."
  Nothing is delegated — C-3's own probe asserts the stamp advances
  (`a run that preserved a file left the stamp at …`). Motivation, not coverage.
  Holds.
- C-5: "the double-registration warning … already fires above the marker gate,
  which `test_hooks.py` pins, so moving it below is a regression this clause
  does not license." `test_hooks.py` runs under C-8 and **T-004 cites C-8**, so
  the pin fires in the same dispatch. Verified by running rather than reading:
  the `hoist-marker-gate` variant leaves `c5` green and turns five `test_hooks`
  cases red. Holds, at the right time.
- C-5, new this round: "Those returns keep their current behavior … exactly as
  it does today minus the notice." "Today" is stable when T-004 runs — T-004 is
  the only task that owns `session-nudge.py`, and none of T-001, T-002 or T-003
  writes it, so the baseline the sentence points at cannot move underneath the
  task. No schedule hazard.
- C-7 and the preamble both point at `docs/installing.md`'s split sentence
  rather than restating it. T-003 owns that file and rewrites the paragraph
  around it, and by then C-1's check has already run in T-001 — so C-7 is the
  only thing standing between that sentence and deletion. C-7's text requires
  it and T-003's `check_method` carries it verbatim. Holds. The artifact is
  real: `docs/installing.md:137`.
- C-8: "Every task that writes an input to any of those three commands cites
  this clause, so the last such task in the schedule is the one whose check
  reads the tree the job actually ships." Re-enumerated and re-measured, not
  carried over: three of four tasks write into that input set (T-001's
  `scripts/plugin-src/install-project.py` plus both built trees, T-004's
  `.agent-guild/hooks/session-nudge.py` plus both built trees, T-002's
  `scripts/test_build_plugin.py`) and all three cite C-8. T-003 owns
  `docs/installing.md`, and `docs/` appears in `build-plugin.py` at exactly one
  path — `docs/plugin-readme.md` — while neither suite references `docs/` at
  all, so T-003 correctly does not cite C-8. T-002 is last by the DAG.
- Non-goals: "C-1 drives all three install shapes, and C-5 drives all three
  nudge deployments." C-1 is in T-001, C-5 in T-004, and each probe drives what
  its clause claims — my reference routes all three install shapes through one
  host-agnostic `_sync_payload` and all three nudge deployments through one
  manifest lookup, and every arm went green off it. Holds.
- Preamble, the r1 advisory: the build-input sentence now names both writers,
  `scripts/plugin-src/` for the installer and `.agent-guild/hooks/` for the
  nudge. Repaired; both writers cite C-8.

**Fixture constructibility — every check's precondition built, not eyeballed.**
All six probes built their own venues off my reference and all six went green,
so no clause makes another's fixture unreachable. The one state the constitution
asserts about and no probe builds is the combined double-registered plus
partially initialized project, and I constructed it (`fork-probe.py`) to confirm
it is reachable — it is, which is what makes A1 worth writing down and also what
bounds it. C-7's rubric names the #214 re-init table, which exists at
`docs/installing.md:132-135`. C-9's rubric names cases asserting on the record's
contents, and T-002's excerpt pins the project-root-relative key format they
need.

**Task order.** Nothing else in the document turns on when a task runs. No
clause needs an artifact before its producer has run, and the preamble fixes no
cadence the DAG puts out of reach. One state worth naming and dismissing again:
`ready-set.py` will dispatch T-002 speculatively while T-004 sits at
`needs-check`, so T-002's C-8 can run against an unverified nudge. That is the
contract's one-level speculation working as documented — T-004's artifact
exists, and a later T-004 FAIL invalidates T-002 and re-runs its C-8.

Nothing new surfaced in these three passes. Said plainly: after the C-5 repair,
this constitution reads clean against this schedule.

## Fork check, and what the comparand diff yielded

**Comparand: `CON-audit-r10`.** Its `SOURCE.sha256` records `62257a2a…` for the
constitution and `9c549764…` for T-004 — both matching what my build read — and
it is the most recent earlier round of either audit id that matches. `DEC-audit-r1`
records the pre-amendment constitution (`229ac266…`) and the superseded T-004,
so it matches on nothing the nudge transcribes and is not a comparand for it.

**My own build was whole before I opened it.** Reference installer and nudge
written, regenerated, all seven runnable checks green, all four C-5 variants
run, reading A built and measured, and `SOURCE.sha256` written — then and only
then did I list `CON-audit-r10/ref-src/`. That order held.

**What the diff yielded: agreement on the settled behavior, on three free axes.**
The two transcriptions of the amended C-5 differ in shape and not in what any
harness accepts. Both were run, not eyeballed: `CON-audit-r10`'s nudge dropped
into my venue passes `probe c5`, passes `test_hooks.py` (371/0), and produces
the same three-message result as mine in the combined state. The axes it leaves
free:

- **Message order.** Mine prints the notice first, r10's prints the
  double-registration warning first. C-5 requires the notice to print "before
  either can return," not before either prints, so both conform.
- **How the return is expressed.** Mine keeps the double-registration `return 0`
  where it is and puts the notice above it; r10 converts it to a flag and returns
  below the notice. Identical behavior.
- **Where the marker gate binds the notice.** Mine calls
  `_lib.guild_initialized()` inline above the double-registration block and
  leaves the existing gate alone; r10 lets the existing gate cover the notice by
  placing the notice below it. Both keep the double-registration warning above
  the gate, which is what C-5 requires and C-8 pins.

No material divergence, so nothing is filed from the diff. Recording the
agreement is the point: this is the first round in which two independent
transcriptions of C-5 landed on the same program, and it is the direct measure
of the r1 repair.

**Scope limit on the diff.** `CON-audit-r10`'s installer implements the record
write only (`_write_provenance`, `_package_version`) and leaves
`_preflight_payload`/`_copy_missing` at pre-job behavior — enough to build
`c5`'s fixtures, not a transcription of C-2, C-3 or C-4. So the installer's
decision logic has no digest-matching comparand this round. r1's build had one
and converged with `CON-audit-r9`, but r1's recorded constitution digest does
not match mine, and the rule is digest-based, so that convergence is not counted
here.

## Advisory

- **A1, C-5** (advisory; no CON round owed, and not blocking): C-5's
  combined-state sentence — a double-registered and partially initialized
  project "prints the notice and the double-registration warning and not the
  partial-init report" — is asserted by the clause and exercised by no check in
  the job. Measured: an implementation that deletes the double-registration
  `return 0` passes `probe c5`, `test_hooks.py`, `test_build_plugin.py` and
  `build-plugin.py --check`, while violating the clause's "removes neither."
  The r1 fork is genuinely closed — this is not that finding returning, since no
  correct reading of either document now leads to reading A — and the exposure
  is a worker who deliberately contradicts two explicit sentences, checked by a
  deterministic checker that only runs scripts. If it is ever worth closing, the
  cheapest close is one arm in `probe-183.py`'s `c5`: the `both` fixture with
  `state/tasks` removed, asserting `"partially initialized" not in stdout`.
  Changing the instrument mid-job costs more than the defect does, so this
  round recommends leaving it and recording the gap.

## What this round did not run

Said plainly. I did not rebuild clause-violating variants for C-1 through C-4
and C-6; the reasoning and its limits are in the scope note above. I did not
build a second full transcription of the installer clauses, and the comparand
does not supply one either, so those five clauses ran two ways this round
(tree as found, reference) rather than three. Everything about C-5 ran three
ways plus the fork measurement. Nothing was blocked, and no check in the job
went unexecuted.
