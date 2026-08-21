---
audit: CON-audit
round: 7
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: b272140fba379f264b09eb21d8427448ebace79bac97d30930976025cb45967f
verdict: FAIL
checked_at: 2026-08-21T03:21:40Z
---

## Scope and method

The constitution's bytes are unchanged since r6 (`b272140f…`, matching the
`CON-audit-r7.md.sha256` the dispatch wrote). What changed is
`.agent-guild/state/checks/probe-183.py`, which r6 recorded at `9788a033…` and
which now reads `bf52ca8f…` — the four probe repairs r6's diagnosis asked for.
This round was dispatched to confirm those repairs discriminate and that a
conforming implementation still passes. Two of the four do not, and one of them
makes C-5 unsatisfiable.

Every clause carrying a runnable check ran three ways: against the tree as
found, against a reference implementation built this round from the clause
texts and the preamble's pinned record contract, and against variants built to
violate each clause's own stated property. C-7 and C-9 carry
`checker-judgment:` rubrics, have nothing to execute, and were judged by
reading. Nothing was `blocked`, and nothing went unexecuted.

Preflight, on the tree as found:

- `check-job-spec.py .agent-guild/state --audit-id CON-audit --repo-root .` —
  exit 0. Weight is `deep`, which carries no ceiling, so R18 owes no
  `**Ceiling overrun**:` line and none is present. No `**Lint exception**:`
  line, so R20 does not apply.
- `check-baselines.py .agent-guild/state --repo-root .` — exit 0,
  `ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)`. Every
  declared baseline held and the sweep filed nothing. The two skips are C-7 and
  C-9, which is the whole of the constitution the sweep did not cover.
- Each of C-1 through C-6 also ran by hand on the untouched tree. All six died
  on the property, not a precondition: five at
  `provenance record missing: …/provenance.json`, C-4 at the `os.remove` of a
  record that does not exist. C-8 ran green (`50 passed, 0 failed`, clean
  `--check`).

The reference implementation lives at
`.agent-guild/state/apparatus/CON-audit-r7/`: `apply.py` patches the two
sources the clauses reach — `scripts/plugin-src/install-project.py` and
`.agent-guild/hooks/session-nudge.py` — then regenerates both packages with
`build-plugin.py`; `variants.py` applies one mutation at a time and runs the
probes it should falsify. It went green on c1, c2, c3, c4, c6 and C-8 on the
first run. It cannot go green on c5, and that is finding F1 rather than a
defect in the build: with arm 5's one unreachable assertion neutralized
(`probe-c5-past-arm5.py`) the same reference reports `probe c5: ok` on every
other arm, including arm 4 and the new jurisdiction arm.

Two standalone probes sit beside it, each built to reach a state
`probe-183.py` never constructs: `probe-codex-stamp.py` (a Codex re-run over a
stale stamp) and `probe-arm5-fixed.py` (arm 5 against a project that is
actually half-installed).

**Venue.** All building and breaking happened in one whole-tree copy at
`/private/tmp/con-r7-work-wYeJVB`, extracted with `git archive HEAD` and
patched in place from pristine sources for each variant rather than re-cloned;
never more than one copy existed at a time. Probe fixtures were redirected to
`/private/tmp/con-r7-fixtures-xRIBbZ` by `TMPDIR` and swept after every single
probe run. Both directories were removed by name before filing, and both are
gone. Twelve `probe183-*` fixtures that the `check-baselines.py` sweep left in
the per-user `$TMPDIR` (`/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T`,
which was not removed — only its `probe183-*` entries were) are also gone.
`git status --porcelain` was clean when this round opened and is clean as it
files. The only writes into the repo are under
`.agent-guild/state/apparatus/CON-audit-r7/` and the gitignored
`state/log/build-*.log` that `check-build.sh` tees. The `__pycache__` the
baseline sweep left under `.agent-guild/hooks/` was removed; the two under
`scripts/` and `.agent-guild/scripts/` predate this session and were left
alone.

**Comparand: CON-audit-r6.** Its `SOURCE.sha256` records `constitution.md` at
`b272140f…` and `spec.md` at `934eba61…`, both matching what this round's build
read, so it is the comparand for the reference implementation. My build was
whole — applied, run against every probe and C-8, and variant-tested through
all thirteen mutations — before `apparatus/CON-audit-r6/` was opened for
anything but its `SOURCE.sha256`. **The diff yields agreement, and no
findings.** Three axes r6 recorded as free were re-derived independently and
came out the same way, and one of them turns out not to be free at all:

- The nudge's manifest lookup. r6 probes `.claude-plugin` then `.codex-plugin`
  and takes whichever exists; mine keys on `host`. No shipped package carries
  both manifests, so the harness accepts either — free.
- Where the record is stamped relative to `_copy_owned` of the Codex project
  hooks. r6 stamps before, mine after. Those hooks carry no entry either way —
  free.
- Whether a net-new file counts toward the summary's `updated` term. Both
  builds count it, and this one is **not** free: `test_build_plugin.py:1524-1540`
  requires `updated == 1` on a re-run whose only movement is a net-new file
  landing, so C-8 pins it.

The one axis worth its own line is the jurisdiction sentence in F3 below: r6's
transcription and mine independently settled it the same way, which is why that
finding is minor rather than major.

**r6's four repairs, re-derived. Two land, two do not.**

| r6 finding | repair | verdict |
| --- | --- | --- |
| F1 first half (C-1, Codex stamp lookup) | `pinned_package("codex")` at `:235-253` | **lands.** `c1-codex-version-hardcoded` red at `the codex stamp does not come from the installing package's manifest: '0.7.1' != '9.9.9'` |
| F1 second half (C-1, Codex re-run) | `_assert_record_covers(codex_tmp, …, version=codex_ver)` at `:230` | **does not land.** `c1-codex-rerun-no-advance` still green — see F2 |
| F2 (C-5, jurisdiction) | the unmarked arm at `:740-758` | **lands.** `c5-ignores-jurisdiction` red at `the nudge speaks in a project carrying no marker` |
| F3 (C-5, partial-init) | `assert "partially initialized" in r_partial.stdout` at `:779` | **does not land, and blocks the job.** Red against the reference too — see F1 |
| F4 (C-1, `--project-skills` re-run) | the re-run at `:292-306` | **lands.** `c1-skills-rerun-records-hooks` red at `the re-run recorded owned hook files: [...]` |

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | Text and check agree on one artifact, and the record contract, the payload scope, both hosts' run-time lookups and the `--project-skills` re-run all discriminate now. What does not is the Codex idempotent re-run: it re-reads a record its own first install wrote at the current manifest version, so it cannot see a stamp that never advances. As found: red (`provenance record missing`). Reference: green. Variants: `c1-claude-only`, `c1-codex-version-hardcoded`, `c1-skills-rerun-records-hooks` red; `c1-codex-rerun-no-advance` green on c1, c2, c3 and c4 alike. | `probe-183.py:223-230`; `apparatus/CON-audit-r7/probe-codex-stamp.py` — see F2 |
| C-2 | — | Sound. Per-file decision, the stamp not gating it, the restamp, the version advance and all three summary terms are reached and discriminate. As found: red. Reference: green. Variant `c2-first-clean-only` red at `stale-but-clean .agent-guild/templates/task.md was not upgraded` — the second of two files, which is what a one-element fixture would have missed. | `probe-183.py:340-407` |
| C-3 | — | Sound. Refusal set, carried-forward hash, upgrade, net-new landing, exit code and the version bump all reached. As found: red. Reference: green. Variant `c3-abort-on-conflict` red at `mixed run failed: 'install.py: local Agent Guild payload differs…'`, naming both edits. | `probe-183.py:410-486` |
| C-4 | — | Sound. Adoption, non-adoption, the record's key set, the post-adoption re-run's whole refused set and the revert escape hatch all discriminate. As found: red. Reference: green. Variant `c4-adopt-wholesale` red at `adoption recorded an entry for a file it refused`. | `probe-183.py:489-574` |
| C-5 | **blocker** | The check cannot go green against any conforming implementation. Arm 5 requires `"partially initialized"` from a fixture whose only mutation is a removed payload file, which `_missing_pieces()` does not look at, so the string is unreachable. As found: red. Reference: **red, at that assertion** — green on every other arm once it is neutralized. Variants: `c5-keyed-on-record-exists` and `c5-ignores-jurisdiction` red at their own assertions; `c5-suppresses-partial` red at the same assertion the reference dies on, so that arm is red in both directions and separates nothing. The jurisdiction sentence also admits a second reading the harness cannot see. | `probe-183.py:760-781` against `session-nudge.py:110-128` — see F1, F3 |
| C-6 | — | Sound. Text, check and failing example agree on one artifact. As found: red. Reference: green. Variant `c6-record-gitignored` red at `provenance.json is gitignored; a tracked record must be addable`. | `probe-183.py:809-821` |
| C-7 | — | Sound rubric. Applicable, and its failing example is still on the page: `docs/installing.md:137` says "A drifted payload file never upgrades in place, because the installer keeps no record of what it shipped", which C-2 makes false, and the #214 table at `:135` says the payload class "preserves each differing one". Judged by reading; nothing to execute. | `docs/installing.md:118, 130-137` |
| C-8 | — | Sound, and load-bearing beyond its own text this round: it is what settles both the net-new counting axis and F3's fork. As found: green (declared green). Reference: green (`371 passed, 0 failed`; `50 passed, 0 failed`; clean `--check`). Variant `c8-stale-build` red at `content differs: hooks/session-nudge.py`, `content differs: project-template/install.py`. | the clause's own command |
| C-9 | — | Sound rubric, and independently load-bearing: my reference added zero test cases and C-8 stayed green, so C-8 cannot stand in for it. | clause text and check |
| preamble | — | Sound. The weight (`deep`) matches the spec's signals — verification did require building an instrument, and this round rebuilt it from scratch — and its stated reason agrees with the paragraph below it. Protected content is `none`, which needs no parse. The record contract determined an implementation on the first attempt, on both hosts and all three install shapes. The content citation resolves: `docs/installing.md:137` carries "install() splits them out of the payload before the drift check runs". | `constitution.md:3, 24-38, 129` |

## Diagnosis

Three findings: one blocker, one major, one minor. The blocker is new this
round and was introduced by r6's F3 repair. **Both remaining defects are probe
work; only F3 asks for a clause revision, and only of one sentence.**

### F1 — blocker (C-5)

**`probe c5` cannot go green against a conforming implementation, because arm
5 asserts a string its own fixture makes unreachable.**

Arm 5 (`probe-183.py:766-781`) fresh-installs, writes the stamp down to
`0.0.1`, removes `.agent-guild/templates/task.md`, and then requires both the
version gap and `"partially initialized"` in one run. Only `_missing_pieces()`
(`session-nudge.py:110-128`) produces that second string, and it examines two
things: the five `state/` subdirs, and the root guidance file's Agent Guild
import line. It never looks at payload files. A fresh install creates all five
state dirs and writes the import line, so removing a payload file leaves
`missing == []`, the partial-init branch returns early at `:166`, and the
report never fires.

Measured directly against the reference, on that exact fixture:

```
missing pieces: []
state dirs: ['disputes', 'log', 'notes', 'tasks', 'verdicts']
root CLAUDE.md exists: True
STDOUT: "agent-guild: this project's payload was installed by agent-guild 0.0.1; the running plugin is 0.7.1. Run /agent-guild:init to bring it up to date?\n"
```

So the arm is red in both directions, which is the defect the "break it" step
exists to catch from the opposite side: `c5-suppresses-partial`, the variant
this assertion was added to catch, dies at the same line and with the same
message as the conforming reference. The arm separates nothing.

The trap underneath it is worth naming, because it is where a worker will go
first. The only implementation that satisfies arm 5 as written is one that
teaches `_missing_pieces()` to report missing payload files — and that fails
C-8: `test_hooks.py`'s `fully_init` fixture is `fresh_proj()` plus a root
`CLAUDE.md`, and `fresh_proj()` creates no payload files at all, so a
payload-aware `_missing_pieces` makes it print where the suite asserts silence.
A worker chasing arm 5 green therefore trades a blocker clause for a blocker
clause, with nothing in either clause's text to tell them which way to go.

Repair, one line in the probe, no clause text: make the fixture actually
half-installed. Replace the `os.remove` of `templates/task.md` at `:770-773`
with a removal of a `state/` subdir and keep the mutation-landed assert —

```python
    half = os.path.join(partial, ".agent-guild", "state", "tasks")
    shutil.rmtree(half)
    assert not os.path.isdir(half), "removal did not land"
```

Demonstrated in `apparatus/CON-audit-r7/probe-arm5-fixed.py`: with that
fixture the reference prints both messages (`…up to date?` followed by
`…partially initialized (missing state/tasks)…`) and `c5-suppresses-partial`
goes red at exactly the intended assertion. The assertion r6 asked for is the
right assertion; it is pointed at the wrong fixture.

### F2 — major (C-1)

**r6's F1 second half did not close the gap. A Codex install that freezes an
existing record's stamp is still green on `probe c1`.**

The repair gave `_assert_record_covers` a `version` argument and routed the
Codex re-run through it (`:230`). But the record that re-run re-reads was
written by the first install four lines up, into a venue that did not exist
before, so it already carries `codex_ver`. `version=codex_ver` is therefore
trivially true whether the second run recomputed the stamp or copied it
forward. The Claude re-run at `:335-337` has the same shape and the same blind
spot; nothing in the probe ever presents either host with a record whose stamp
is stale.

Variant `c1-codex-rerun-no-advance` (below the Codex branch, a run that finds
an existing record keeps its version): `probe c1`, `c2`, `c3` and `c4` all
green. `apparatus/CON-audit-r7/probe-codex-stamp.py` walks the state the probe
never builds — install, write the stamp to `0.0.1`, re-run — against the same
two trees:

```
reference:                  running manifest='0.7.1'  stamp after re-run='0.7.1'  → ok
c1-codex-rerun-no-advance:  running manifest='0.7.1'  stamp after re-run='0.0.1'  → VIOLATION
```

That violates C-1's own text — "`version` equal to that host package's own
manifest" — and it ships the issue's headline defect on one of two supported
hosts: a Codex project pins forever, and C-5's nudge fires every session with
nothing that clears it, which is C-3's stated failure mode reached by a route
C-3 does not cover (C-2 through C-4 are Claude-only by the third non-goal).
That non-goal rests on this clause: it waives Codex coverage on the ground that
"the host-specific lookups are covered rather than waived: C-1 drives all three
install shapes." The stamp is a host-specific lookup and C-1 still does not
reach it.

Repair, probe work again, and c2 already shows the shape: before the Codex
re-run at `:223`, write the record's `version` down to a string no manifest
carries, assert the rewrite landed (`write_prov` does this), re-run, and let
`_assert_record_covers(codex_tmp, "codex re-run", version=codex_ver)` do the
rest. The same three lines are worth adding to the Claude re-run at `:335`,
where the blind spot is identical and only C-2's Claude-only fixture happens
to cover it.

### F3 — minor (C-5)

**"It stays subject to jurisdiction: no marker, no output of any kind" admits
a second reading, and C-5's own harness cannot separate the two.**

Reading (a): the version notice is what the marker gate governs, and the
double-registration warning keeps its existing placement above that gate.
Reading (b): the hook emits nothing at all without a marker, which puts the
double-registration warning below the gate too. The sentence's "it" points back
at "The notice", but "no output of any kind" is a claim about the run.

Variant `c5-jurisdiction-strict` builds reading (b). `probe c5` cannot tell it
from the reference: the unmarked arm's fixture registers no copy-in gates, so
the moved warning is silent there for an unrelated reason. C-8 can, loudly —
`test_hooks.py` fails five assertions in the `plugin_rooted_hit` block, which
is a bare tmpdir holding only `.claude/settings.json` and no marker:

```
FAIL plugin-rooted + copy-in settings.json → one double-registration warning  rc=0 out=''
FAIL plugin-rooted + copy-in settings.json → exactly one stdout line  out=''
FAIL double-registration warning cites the verified stall-counter consequence
FAIL double-registration warning names --scope local, not --scope project, as the resolution
FAIL double-registration warning names the kendrick-qualified plugin id
```

So the sentence as written is false of the artifact the constitution requires:
a conforming build does produce output in a markerless double-registered
project, because C-8 insists on it. Minor rather than major on two grounds —
C-8 settles the fork immediately and by name, so the cost is one debugging
cycle rather than a shipped defect; and r6's independent transcription settled
it the same way mine did, which is the strongest evidence available that a
worker lands on reading (a).

Repair, one clause sentence: say what is actually meant — "the version notice
stays subject to jurisdiction: with no marker it prints nothing" — leaving the
double-registration warning's placement, which this job does not touch, out of
it.

## What is not wrong

Worth stating plainly, since two of r6's four repairs did land and the rest of
the document held up under a second independent build.

The reference implementation went up from the clause texts and the preamble's
record contract alone, on the first attempt, on both hosts and all three
install shapes, with no ambiguity I had to settle by guessing except the one
filed as F3. C-2, C-3, C-4 and C-6 are complete: every sentence is reached and
every one discriminates, and the failing examples C-1, C-2, C-3, C-4, C-5, C-6
and C-8 each state were run as variants and each went red at its own clause's
own assertion. No clause contradicts another under reading (a) of C-5's
jurisdiction sentence. The weight is `deep` and the reason recorded on that
line is true — I rebuilt the instrument this round, which is the evidence for
it. C-7's and C-9's rubrics both remain applicable and both remain independent
of C-8.

No clause text changes are owed by F1 or F2; both are repairs to
`.agent-guild/state/checks/probe-183.py`. F3 is one sentence in C-5. All three
land in Phase 0, and the amended bytes will re-close the gate on their own, so
one more CON round is owed after them.
