---
audit: CON-audit
round: 10
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
verdict: PASS
checked_at: 2026-08-21T05:34:55Z
---

## Scope and method

This round is scoped, deliberately and on the orchestrator's instruction, to
C-5 and to the amendment that closed `DEC-audit-r1`'s F1. I read all nine
clauses whole; I executed one.

`constitution.md` reads `62257a2ac5d3699f59048c852bdf2fcf7730747e1b67a3b32c55c408e60c6efe`,
which is what `CON-audit-r10.md.sha256` binds, so this verdict covers the text
I read. `spec.md` (`934eba61…`), `probe-183.py` (`5c65bb9b…`) and
`docs/installing.md` (`011551…`) are byte-identical to what `CON-audit-r9` and
`DEC-audit-r1` recorded, so the instrument and the artifacts around it have not
moved since those rounds ran.

**What I ran, and what I did not.** C-5 ran six ways: against the tree as
found, against a reference implementation of the settled reading built this
round, and against four variants built to violate four distinguishable
properties of its text. C-1 through C-4, C-6 and C-8 ran once each, through the
baseline sweep, against the tree as found; I did not rebuild reference
implementations for them this round. That is a deliberate narrowing, not an
oversight: those six clauses' bytes have not moved since `CON-audit-r9` passed
them, and `DEC-audit-r1` ran every one of them three ways — green against a
reference, red against a violating variant — against these same probe bytes ten
hours ago. C-7 and C-9 carry `checker-judgment:` rubrics, have nothing to
execute, and were judged by reading. Nothing is `blocked`.

**One limit on that narrowing, said plainly.** `.agent-guild/state/` is
gitignored (`.gitignore:5`) and no round archives the constitution's bytes,
only its digest. So I cannot mechanically diff this text against the
`229ac266…` that r9 and DEC-r1 read, and "nothing else moved" rests on my own
read-through of all nine clauses plus the sweep confirming every declared
baseline still holds — not on a byte diff. If a clause other than C-5 changed
in a way that reads correctly on its own, this round would not catch it.

**Baseline sweep**, against the tree exactly as found:

```
python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .
check-baselines: ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)
exit 0
```

Every declared baseline held. Scope note on coverage: 7 of 9 clauses ran; the
2 skipped are C-7 and C-9, the two with nothing to run; 0 skipped for having no
baseline, 0 unclassifiable.

**The venue.** One whole-tree copy at `/tmp/conr10.Xkv0bZ`, built with
`git archive HEAD | tar -x` plus the gitignored `probe-183.py` copied in, and
patched in place from saved `.orig-*` copies between variants rather than
re-cloned — so exactly one whole-tree copy existed at any moment. Probe venues
were confined to `TMPDIR=/tmp/conr10.Xkv0bZ.tmp`, including the baseline
sweep's. Both paths were removed by those exact printed names before filing;
neither `/tmp/probe183-*` nor `/tmp/conr10-fork-*` survives. `PYTHONDONTWRITEBYTECODE=1`
was set on every run. I read C-8's `rm -rf` before running it: all three
`__pycache__` targets are untracked bytecode, and `.agent-guild/hooks/__pycache__`
did exist beforehand and was removed by that check.

`git status --porcelain` was empty when I started and is empty now. Peak load
during the round was under the r1 standard.

**Apparatus.** `.agent-guild/state/apparatus/CON-audit-r10/`, carrying
`SOURCE.sha256` (constitution, spec, probe, `session-nudge.py`,
`install-project.py`, `docs/installing.md`, `T-004.md`), `VENUE.txt`,
`apply-ref.py` (the reference implementation, with both readings behind a flag
and C-5's own failing example behind another), `late-notice.py` and
`variants.py` (three more clause-violating mutations), `fork-probe.py` (the
combined-state measurement), and `ref-src/` holding the two patched sources.

**Comparand.** No predecessor matches. `CON-audit-r9` and `DEC-audit-r1` both
record `229ac266…` for `constitution.md`; my build transcribes `62257a2a…`, so
the source moved and a diff of the artifacts would be noise. The comparand step
is a no-op and files nothing. **My own build was whole before I opened either
predecessor's `ref-src/`** — reference written, regenerated, `probe c5` green,
`test_hooks.py` at `371 passed`, `--check OK`, and all four variants run red or
green as recorded below — and I opened them afterward only to confirm my two
reconstructions correspond to the two readings DEC-r1's fork finding names.
They do, exactly: `CON-audit-r9/ref-src/session-nudge.py` carries
`double_registered = True` with `if double_registered: return 0` below the
notice (my reading B), and `DEC-audit-r1/ref-src/session-nudge.py` carries the
same restructure with the return deleted (my reading A). Recording the
agreement, since it is the round's strongest evidence that the settled text
determines a program: three independent transcriptions of the deciding
expression, and the two built from the amended bytes landed on the same one.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ----------- | -------- |
| C-1 | blocker | text and check agree, falsifiable, concrete check. Tree as found: **red as declared** (`provenance record missing`). No reference or variant built this round — carried on `DEC-audit-r1`'s two runs against these same probe bytes, which its own table records. | baseline sweep; `DEC-audit-r1.md` per-clause table |
| C-2 | blocker | sound on its own text; tree as found **red as declared**. Not rebuilt this round; carried on DEC-r1. | same |
| C-3 | blocker | sound on its own text; tree as found **red as declared**. Not rebuilt this round; carried on DEC-r1. | same |
| C-4 | blocker | sound on its own text; tree as found **red as declared**. Not rebuilt this round; carried on DEC-r1. | same |
| C-5 | major | **The fork is closed.** The amended text admits exactly one reading, measured against both implementations rather than argued. Tree as found: **red as declared**. Reference implementation of reading B: **green** (`probe c5: ok`; `371 passed, 0 failed`; `--check OK`). Four violating variants, all **red at the clause's own assertions**, none at a precondition. One residual, filed as **M1**: the newly-settled combined-state sentence is the one assertion no arm exercises. | see the C-5 section below |
| C-6 | major | sound on its own text; tree as found **red as declared**. Not rebuilt this round; carried on DEC-r1. | baseline sweep; `DEC-audit-r1.md` |
| C-7 | major | `checker-judgment:` rubric, nothing to execute; judged by reading. Names four behaviors and the `install()` split sentence a checker can find and test against the shipped implementation. `docs/installing.md` is byte-identical to what DEC-r1 verified. | read only |
| C-8 | blocker | tree as found: **green as declared**, rc=0 across all three commands. Not re-broken this round; DEC-r1 records the red run. | baseline sweep |
| C-9 | major | `checker-judgment:` rubric, nothing to execute; judged by reading. Its "would it fail against pre-job behavior" test is applicable as written, and DEC-r1 measured the premise it rests on — the existing suites pass unchanged against a full reference implementation, so nothing existing covers these paths. | read only |

Nothing is `blocked`.

### C-5: the fork, tested against both implementations

**Question 1 — does the text now admit one reading?** Yes. The clause's
operative sentences are:

> Those returns keep their current behavior. This job moves the notice above
> them and removes neither, so a project that is both double-registered and
> partially initialized prints the notice and the double-registration warning
> and not the partial-init report, exactly as it does today minus the notice.

Reading A removes the double-registration early return, so the combined state
also reaches the partial-init report. That is now excluded twice over — by
"removes neither" and by the named output. Reading B is what remains, and it is
reachable: the double-registration *warning* stays above the marker gate, where
`test_hooks.py` pins it and where the clause forbids moving it; only its
`return 0` relocates to below the notice. That is the one arrangement satisfying
every sentence at once, and I built it without difficulty from the clause text
alone, first try.

**The measurement.** I built both readings from the amended bytes and drove the
combined state — fully installed, stale-stamped, double-registered *and*
partially initialized — through each, alongside HEAD:

```
                              reading A     reading B     HEAD today
double-registration warning   True          True          True
version notice                True          True          False
partial-init report           True          False         False
```

Reading B is HEAD's behavior plus the notice, which is exactly what the clause
now demands. Reading A prints a third message the clause forbids. The text
separates them.

**Question 2 — did the settlement break anything?** No. The reference
implementation of reading B is green on every existing C-5 arm and on all three
of C-8's commands:

```
probe c5: ok
test_hooks.py         371 passed, 0 failed
test_build_plugin.py  (via --check)  ✔ Validation passed
build-plugin.py --check  OK
```

**Discrimination.** Four variants, each violating a distinct sentence of C-5,
each red at that sentence's own assertion:

| variant | property violated | assertion that failed |
| ------- | ----------------- | --------------------- |
| notice keyed on "a record exists" | the clause's own failing example | `nudge reports a version gap on an up-to-date project: "…installed by version 0.7.1; the running plugin is 0.7.1…"` (arm 2) |
| notice below the double-registration return | "prints before either can return" | `the version gap is lost when the plugin is registered twice` (the F5 arm) |
| notice below the partial-init return | "prints before either can return" | `stamped version missing from nudge output: ''` (arm 1) |
| notice hoisted above the marker gate | "no marker, no version notice" | `the nudge speaks in a project carrying no marker` (the jurisdiction arm) |

None died at a precondition; every one reached the clause's own logic.

## Findings

### M1 — C-5 (minor): the combined-state sentence is the one assertion no arm exercises

The dispatch says "No probe arm is owed under B — the existing arms already
cover it." Measured, that is false. I ran a reading-A implementation — the one
the amended clause now forbids — against C-5's own check:

```
probe c5: ok                      (reading A)
test_hooks.py  371 passed, 0 failed
```

Green, on the reading the clause excludes. The reason is structural rather than
incidental: the F5 arm builds a double-registered project that is *fully*
installed, so nothing is missing and reading A's extra path prints nothing;
arm 5 builds a partially initialized project that is *not* double-registered,
so the return never fires. The combined state appears in no arm, and it is the
only state where the two readings differ.

T-004's checker is `checker-deterministic`, which runs the probe and reads no
clause text, so in this decomposition the sentence has no enforcement path at
all.

**Why minor rather than blocking.** What the gap admits is narrow and it is not
a regression. Reading B is the status quo plus the notice, and it is the
smaller change; reading A is extra unmotivated work that *adds* a message
rather than losing one. Both the clause and T-004's excerpt item 4 now state
the decision in plain words, so a worker following either lands on B — the fork
that could have cost a retry budget through a checker/worker disagreement is
genuinely closed, and what is left is an unlikely over-implementation nobody
would notice. I would not hold the workers behind it.

**The repair, and it costs no round.** Add one arm to `probe-183.py`'s `c5`
driving the combined state and asserting `"partially initialized" not in
stdout` alongside the warning and the notice.
`.agent-guild/state/apparatus/CON-audit-r10/fork-probe.py` is that fixture
already, built and run. The check line in C-5 does not change and neither does
`constitution.md`, so the Phase 0 digest does not re-close: the arm can go in
without another CON-audit round.

### M2 — C-5 (minor, wording): "moves the notice above them" describes the wrong motion

Read strictly, "the notice sits above both early returns in the file" and "It
stays subject to jurisdiction: no marker, no version notice" cannot both hold
of a notice that only moves, because today's double-registration return sits
*above* the marker gate. What actually has to move is that `return 0`, down to
below the notice, while the warning it follows stays put — which is what the
next sentence forbids changing ("moving it below is a regression this clause
does not license"). The requirement is recoverable and I recovered it, and so
did r9's independent transcription, because the combined-state sentence names
the required output exactly and `test_hooks.py` closes the alternative. Worth a
word whenever C-5 is next touched; not worth a round on its own.

## Notes on the rest of the document

- **The preamble advisory from DEC-r1 is repaired.** The build-input sentence
  now names both writers — "`scripts/plugin-src/` for the installer,
  `.agent-guild/hooks/` for the nudge" — which is the whole of the schedule's
  build-input surface.
- **The weight line still reads right.** `deep`, corrected by the user on r4,
  with a reason that survives this round's own experience: I had to build an
  instrument to verify anything here, and the reference implementation plus
  five mutations is the fourth such build this job has paid for. No
  `**Ceiling overrun**:` line is owed at `deep`, and none is present.
- No `**Lint exception**:` line is present, so R20 has nothing to judge and
  neither do I.
- Protected content declares `manifest: none`, which needs no manifest to
  parse.
- No two clauses contradict each other on this read. The one place the document
  strains against itself is M2, and it resolves.
