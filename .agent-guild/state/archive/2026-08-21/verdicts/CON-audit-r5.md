---
audit: CON-audit
round: 5
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: 2737e51e6eee9de3f6fa502a7200b73c782cd276e5f6f590b4aafa0d3fe9b59c
verdict: FAIL
checked_at: 2026-08-21T02:30:38Z
---

## Scope and method

Every clause carrying a runnable check was executed three ways: against the tree
as found, against a reference implementation built from the clause texts and the
preamble's pinned record contract alone, and against variants built to violate
each clause's own stated property. C-7 and C-9 carry `checker-judgment:` rubrics,
have nothing to execute, and were judged by reading. Nothing was `blocked`, and
nothing went unexecuted.

Preflight, on the tree as found:

- `check-job-spec.py .agent-guild/state --audit-id CON-audit --repo-root .` — exit 0.
  R17/R18 clear (weight `deep`, which carries no ceiling, so no
  `**Ceiling overrun**:` line is owed and none is present). The preamble carries
  no `**Lint exception**:` line, so R20 does not apply.
- `check-baselines.py .agent-guild/state --repo-root .` — exit 0,
  `ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)`. Every declared
  baseline held; the sweep filed nothing. The two skips are C-7 and C-9, which
  is the whole of the constitution the sweep did not cover.
- Each of C-1 through C-6 was also run by hand on the untouched tree and each
  died at the same assertion, `provenance record missing` — the property, not a
  precondition. C-8 ran green in 30s (`50 passed, 0 failed`, clean `--check`).

The reference implementation lives at
`.agent-guild/state/apparatus/CON-audit-r5/` (`apply.py`, which patches the two
sources the clauses reach, plus `refA/` holding the two patched files as
built). It touches `scripts/plugin-src/install-project.py` and
`.agent-guild/hooks/session-nudge.py` and nothing else, then regenerates both
packages with `build-plugin.py`. It went green on all six behavior probes plus
C-8 on the first run, with no axis I had to guess at except the one in F5 — the
clause texts do determine an implementation. 30 variants ran; `variants.py`
carries every one, and `probe-c1-stamp.py` and `fork-c5.py` carry the two arms
the constitution does not have, written to prove that two of the findings below
are checkable rather than merely unchecked.

**Venue.** All building and breaking happened in one whole-tree copy at
`/private/tmp/con-r5-ref-cgXVnX`, removed by name after the last run. The
probes' own fixtures land under
`/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T` as `probe183-*`, and the two
extra arms as `stamp-pkg-*`, `stamp-proj-*` and `fork-c5-*`; every one was
removed by name, after each batch rather than at the end, and the venue count
was confirmed at zero before filing. Only one whole-tree copy existed at any
point. `git status --porcelain` was clean when this round opened and is clean as
it files. The only writes into the repo are under
`.agent-guild/state/apparatus/CON-audit-r5/` and the gitignored
`state/log/build-*.log` that `check-build.sh` tees; the `__pycache__` the suites
leave under `.agent-guild/hooks/` was removed.

**Comparand.** None. This round's build read `constitution.md` at `2737e51e…`;
the predecessors' `SOURCE.sha256` record `bf8f5970…` (r0), `b0408bf8…` (r1),
`b879a6e8…` (r2), `734658e2…` (r3) and `a3b71b7f…` (r4), so no earlier round
transcribed this text and the diff step is a no-op that files nothing. My own
build was whole — applied, green on all seven runnable clauses, and
variant-tested — before any predecessor directory was opened; the only thing
read out of them was `SOURCE.sha256`, after that point.

**r4's repairs, re-derived.** Six of eight land. F1 → `c3-hold-version-on-conflict`
now red at c3 (`a run that preserved a file left the stamp at '0.0.1'`), green
at c1/c2/c4, so c3 is the arm that closed it. F2 → `c1-third-key`,
`c1-wrong-hash`, `c1-drops-one-entry` and `c1-records-owned-hooks` all red on
the Codex arms, which is `_assert_record_covers`-grade coverage on all three
shapes. F3 → `c2-first-clean-only` red (`stale-but-clean .agent-guild/templates/task.md
was not upgraded`). F5 → `c5-no-command` and `c5-claude-command-everywhere` both
red on arm 3. F6 → `c5-claude-version-compiled-in` shows arm 3b closed the Codex
half only (F4 below). F8 → the weight is now `deep` and its reason no longer
contradicts the preamble; deep carries no ceiling, so the overrun line correctly
disappeared with it. **F4 landed on the adoption run and not on the re-run**, and
**F7 was not repaired at all**; both come back below, F4 harder than r4 graded it.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | The record contract now holds on all three install shapes, but two of the clause's own sentences are unreachable: `version` equal to that host package's manifest, and the idempotent re-run. As found: red (`provenance record missing`). Reference: green. Variants: `c1-claude-only`, `c1-third-key`, `c1-wrong-hash`, `c1-drops-one-entry`, `c1-records-owned-hooks` all red; `c1-version-hardcoded` and `c1-codex-run-scoped` green. | `probe-183.py:164-242`; every fixture runs at 0.7.1, and only the `claude` arm re-runs the installer — see F1, F2 |
| C-2 | — | Sound, and the strongest clause in the document. Every sentence is reached and every one discriminates. As found: red. Reference: green. Variants: `c2-first-clean-only`, `c2-stamp-gates`, `c2-preserve-everything-unwritten`, `c2-no-restamp`, `c2-count-examined`, `c2-no-version-advance` — all six red, each at the assertion naming its own property. | `probe-183.py:245-312` |
| C-3 | — | Sound. Refusal set, carried-forward hash, upgrade, net-new landing, exit code and the version bump all reached and all discriminating. As found: red. Reference: green. Variants: `c3-abort-on-conflict`, `c3-restamp-preserved`, `c3-hold-version-on-conflict`, `c3-first-conflict-only`, `c3-names-everything` — all five red. | `probe-183.py:315-391` |
| C-4 | blocker | Adoption, non-adoption, the record's key set and the revert escape hatch all discriminate. "On a further re-run still preserves and reports those same files" does not: `r2` is a one-element spot check, and a run that overwrites the second pre-provenance edit passes. As found: red. Reference: green. Variants: `c4-adopt-wholesale`, `c4-record-entry-for-refused`, `c4-adoption-drops-an-entry`, `c4-no-revert-escape` red; `c4-rerun-reports-first-only` and `c4-rerun-overwrites-second` green. | `probe-183.py:449-453`; `r2` asserts `key_a` alone and nothing about `key_d` — see F3 |
| C-5 | minor | Five arms; the stamped version, the running version, both hosts' commands, the question, the partial-init independence, the write-nothing property and the repo-local exit code all discriminate. Arm 3b closes the run-time lookup for the Codex package only, and the clause leaves the double-registration ordering unpinned. As found: red. Reference: green. Variants: `c5-keyed-on-record-exists`, `c5-no-command`, `c5-claude-command-everywhere`, `c5-below-partial-return`, `c5-repo-local-raises`, `c5-nudge-writes`, `c5-stamped-version-faked` red; `c5-claude-version-compiled-in` and `c5-above-double-reg` green. | `probe-183.py:576-598` drives the Codex package alone; no arm builds a project that is both double-registered and stale — see F4, F5 |
| C-6 | — | Sound. Text, check and failing example agree on one artifact. As found: red (`provenance record missing`). Reference: green. Variant `c6-record-gitignored` red (`provenance.json is gitignored; a tracked record must be addable`). | `probe-183.py:646-658` |
| C-7 | — | Sound rubric. Applicable, and its failing example is still on the page: `docs/installing.md:137` says "A drifted payload file never upgrades in place, because the installer keeps no record of what it shipped", which C-2 makes false, and the #214 table at `:135` says the payload class "preserves each differing one". Judged by reading; nothing to execute. | `docs/installing.md:118, 130-137` |
| C-8 | — | Sound. As found: green (declared green; `50 passed, 0 failed` plus a clean `--check`). Reference: green, with zero regression cases added. Variant: source edited without regenerating → `--check` exit 1, `content differs: project-template/install.py` on both targets. | the clause's own command |
| C-9 | — | Sound rubric, and independently load-bearing: my reference added zero test cases and C-8 stayed green, so C-8 cannot stand in for it. The "would fail against the tree as this job found it" qualifier is what keeps the refusal path honest, since today's installer already preserves a drifted file. Judged by reading; nothing to execute. | clause text and check |
| preamble | — | Sound. The weight (`deep`) matches the spec's signals and its stated reason no longer contradicts the paragraph below it. Protected content is `none`, which needs no parse. The record contract is complete enough that a reference built from it alone went green on every probe on the first attempt. The citation by content resolves: `docs/installing.md:137` carries "install() splits them out of the payload before the drift check runs". | `constitution.md:3, 24-38, 129` |

## Diagnosis

Five findings. One is a blocker, two are major, two are minor. None of them would
mislead a worker into building the wrong thing — I built the deliverable from
these clause texts alone and it went green everywhere on the first attempt, with
F5 the single exception. What fails is the other direction: three of these
checks accept implementations their clauses forbid, and one of those
implementations silently destroys a user's file. Nor is any of this Phase 1's to
catch. Every finding is a property of a clause read alone against its own check,
which is exactly what a CON round is chartered for; a DEC round would find the
schedule consistent and pass them all through.

### F1 — blocker (C-4)

**"On a further re-run still preserves and reports those same files" is checked
on one of the two files the fixture builds.** This is the half of r4's F4 repair
that did not land. The adoption run got its whole-set assertion
(`named_adopt == sorted([key_a, key_d])`, `probe-183.py:442`); `r2` at
`:449-453` still asserts `key_a in r2.stdout` and `path_a`'s bytes, and nothing
at all about `key_d`.

Two variants green:

- `c4-rerun-reports-first-only` — when a record already exists, the diagnostic
  names only the first *unrecorded* conflict. `probe c4` green; `probe c3` green
  too, because c3's conflicts are all recorded ones. A user with two
  pre-provenance edits is warned about one of them forever.
- `c4-rerun-overwrites-second` — when a record already exists, the second and
  later unrecorded-but-differing files are **overwritten from source** and
  recorded, while the first is preserved. `probe c3` green, `probe c4` green.
  Nine clauses green.

The second one is why this is a blocker rather than another one-element-fixture
note. What it ships is the outcome the spec's own open question rules out —
"Trusting it wholesale overwrites real local edits" (`spec.md:89`) — delayed by
exactly one re-init, which is the interval no probe watches. Every pre-provenance
project in existence is the population at risk, and the adoption run that the
constitution does check is the one run where the behavior is correct.

The two code paths are genuinely separable, which is what makes the variant a
design a worker could arrive at rather than a contrivance: adoption is the
`recorded is None` branch and `r2` is the steady-state branch meeting a file the
record does not cover. A worker who writes those as two functions has two places
to get the plural right, and the constitution checks one.

Repair, both halves:

1. C-4's text is already plural and already right; the check has to match it.
   `r2` asserts the whole set the way the adoption run does —
   `sorted(p for p in payload_files(tmp) if p in r2.stdout) == sorted([key_a, key_d])`
   — and asserts `path_d`'s bytes are still `edited_d`, which is the assertion
   that catches the overwrite.
2. Worth adding one sentence to C-4 making the preservation explicit on the
   re-run ("and preserves their bytes"), since the current text says "still
   preserves and reports" in a single breath and only the reporting half reads
   as something to assert on.

### F2 — major (C-1)

**"`version` equal to that host package's own manifest" cannot be falsified by
any arm.** Both manifests carry `0.7.1`, by construction rather than by
coincidence — they are generated from one `scripts/plugin-src/plugin.json` — so
every fixture the probe builds runs at the one version both packages already
claim.

Variant `c1-version-hardcoded`: `_package_version()` returns the literal
`"0.7.1"` whenever the package root exists, reading no manifest. `probe c1`,
`c2`, `c3` and `c4` are all green.

This is r4's F6, one document over. F6 was filed against C-5 and repaired there
with arm 3b, which copies the Codex package, moves the copy's manifest to a
version nothing else carries, and drives the copy. C-1 makes the same claim about
the same manifest and never got the same arm — and C-1's is the stamp that
matters more, because the nudge only ever compares against what the installer
wrote. I built the missing arm to prove the property is checkable:
`apparatus/CON-audit-r5/probe-c1-stamp.py` copies each package, sets the copy's
manifest to `9.9.9`, and installs from the copy.

```
reference:               codex -> '9.9.9' OK    claude -> '9.9.9' OK
c1-version-hardcoded:    codex -> '0.7.1' WRONG claude -> '0.7.1' WRONG
```

What the green run passes through is the issue's headline symptom made
permanent. A stamp that never advances means every project stays pinned at
whatever string was compiled in; C-5's nudge then fires at every session start
against a gap that re-running init cannot close, since the next install writes
the same constant back. That is C-3's stated failure mode ("a stamp held back …
pins the project forever and leaves C-5's nudge firing every session with
nothing that clears it") reached by a route C-3 does not cover.

Repair: fold `probe-c1-stamp.py`'s arm into `c1` — copy each package to a venue,
move the copy's `plugin.json` to a version nothing else carries, install from
the copy, and assert the record is stamped with it. Two arms, and they close the
Claude half of F4 below at the same time if the nudge is driven from the same
copies.

### F3 — major (C-1)

**"That holds … again after an idempotent re-run that copies nothing" is checked
on one of the three install shapes.** The sentence sits directly after "This
holds across all three shipped install shapes", and only the `claude` arm at
`probe-183.py:233-242` ever runs the installer twice.

Variant `c1-codex-run-scoped`: on the Codex branch, a run that finds an existing
record writes a record scoped to the files that run wrote. `probe c1` green.

The clause states its own reason for having the re-run arm — "a record scoped to
the files one run wrote is indistinguishable from a whole-payload record on a
fresh install" — and that reason applies word for word to the two Codex arms,
which do fresh installs and stop. So those arms establish the contract's shape
and nothing about its scoping.

This also thins the third non-goal, which waives Codex coverage of C-2 through
C-4 on the ground that "the host-specific lookups are covered rather than
waived: C-1 drives all three install shapes." A Codex re-init is the one shape
where a host-specific code path meets an existing record, and it is the shape no
check reaches. C-1's own failing example — an installer that branches on host
when writing the record — is exactly the implementation this variant is.

Repair: `_assert_record_covers` already takes a label; give it a manifest
parameter and run each Codex arm through install-twice the way the `claude` arm
does, then assert the record after the second run.

### F4 — minor (C-5)

**Arm 3b proves the run-time manifest lookup for the Codex package only.**

Variant `c5-claude-version-compiled-in`: `running = "0.7.1" if host == "claude"
else _running_version(__file__)`. `probe c5` green on all five arms — arm 1
asserts `ver in out` where `ver` is `0.7.1`, and arm 3b never touches the Claude
package.

Minor rather than major, for two reasons. The same file ships inside both
packages, so a single shared lookup is fully covered by arm 3b already, and the
variant has to introduce host-branching that nothing in the design asks for.
And the realistic wrong implementation on this lane — reading
`CLAUDE_PLUGIN_ROOT` — fails arm 1 outright, since the probe does not set it.
The finding is that the clause's sentence covers two packages and the check
covers one, and the repair is nearly free: arm 3b's machinery, pointed a second
time at a copy of the Claude package.

### F5 — minor (C-5)

**C-5 leaves the ordering against the double-registration early return unpinned,
and no arm reaches it.** This is r4's F7 verbatim, unrepaired. C-5 says the
notice "is independent of the partial-init report" and says nothing about the
double-registration report, which `session-nudge.py:144-156` handles with a
`return 0` before anything else. Arms 1–3 wire no guild gates into the project's
own hook config and arm 4's repo-local instance skips that check by design, so
no fixture is both double-registered and stale.

Both readings pass. `c5-above-double-reg` puts the version notice above the early
return; `probe c5` green, and my reference (notice below it) is green too. On a
project that is both — legal, reachable, and exactly what a copy-in user who also
enables the plugin has — the two produce different output, which
`apparatus/CON-audit-r5/fork-c5.py` shows directly:

```
reading A (below):  the double-registration warning alone; version notice present: False
reading B (above):  both warnings;                          version notice present: True
```

The expression the two turn on is the `return 0` at `session-nudge.py:156`. A
worker has to settle it and the constitution does not record the pick, so which
of the two ships is decided by whoever writes it first.

Repair: one sentence in C-5 saying which warning wins when both apply, and an
arm that installs, stamps down, and writes a `.claude/settings.json` carrying
`dispatch-guard.py` before running the nudge. `fork-c5.py` is that fixture,
already built.

## What is not wrong

Worth saying, because five rounds of findings can make a document look worse
than it is, and this one is close.

No clause contradicts another. Every clause names a concrete check and a failing
example its check actually catches — `c1-claude-only`, `c2-preserve-everything-unwritten`,
`c3-abort-on-conflict`, `c4-adopt-wholesale`, `c5-keyed-on-record-exists`,
`c6-record-gitignored` and the C-8 stale-build variant are each that clause's own
failing example, run and red. C-2 and C-3 are complete: I could not find a
sentence in either one that a variant could violate while the probe stayed green,
and eleven variants tried. The record contract in the preamble determined an
implementation on the first attempt. The spec's eight acceptance criteria all map
onto clauses, and the three intake rulings are all carried by clause text and all
checked. The weight is right and its reason is now true.

Three of the five findings are one property each, and three of the five are
repairs to the probe rather than to a clause — F1's second half, F2 and F3 are
arms to add, not text to rewrite. The clause text changes owed are one sentence
in C-4 and one in C-5.
