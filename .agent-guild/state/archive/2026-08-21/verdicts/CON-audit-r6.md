---
audit: CON-audit
round: 6
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: b272140fba379f264b09eb21d8427448ebace79bac97d30930976025cb45967f
verdict: FAIL
checked_at: 2026-08-21T03:00:30Z
---

## Scope and method

Every clause carrying a runnable check ran three ways: against the tree as
found, against a reference implementation built from the clause texts and the
preamble's pinned record contract alone, and against variants built to violate
each clause's own stated property. C-7 and C-9 carry `checker-judgment:`
rubrics, have nothing to execute, and were judged by reading. Nothing was
`blocked`, and nothing went unexecuted.

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
  on the property rather than a precondition: five at
  `provenance record missing: …/provenance.json`, C-4 at the `os.remove` of a
  record that does not exist. C-8 ran green (`50 passed, 0 failed`, clean
  `--check`).

The reference implementation lives at
`.agent-guild/state/apparatus/CON-audit-r6/`: `apply.py`, which patches the two
sources the clauses reach — `scripts/plugin-src/install-project.py` and
`.agent-guild/hooks/session-nudge.py` — then regenerates both packages with
`build-plugin.py`, plus `variants.py`, the driver that applies one mutation at a
time and runs the probes it should falsify. It went green on all six behavior
probes and on C-8 on the first run, with no axis I had to guess at. Thirty-six
variants ran; `apply.py` carries every one by name.

**Venue.** All building and breaking happened in one whole-tree copy at
`/private/tmp/con-r6-ref-kC27tK`, removed by name after the last run. Probe
fixtures land under `/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T` as
`probe183-*` (including the `probe183-pkg-*` package copies); `variants.py`
sweeps them after every single probe run rather than at the end, and the count
was confirmed at zero before filing. Exactly one whole-tree copy existed at any
point, and it was patched in place from `git show HEAD:` for each variant rather
than re-cloned. `git status --porcelain` was clean when this round opened and is
clean as it files. The only writes into the repo are under
`.agent-guild/state/apparatus/CON-audit-r6/` and the gitignored
`state/log/build-*.log` that `check-build.sh` tees. The `__pycache__` my runs
left under `.agent-guild/hooks/` was removed; the two that remain, under
`scripts/` and `.agent-guild/scripts/`, predate this session (Aug 13 and 17:49
today) and were left alone.

**Comparand.** None. This round's build read `constitution.md` at `b272140f…`;
the predecessors' `SOURCE.sha256` record `bf8f5970…` (r0), `b0408bf8…` (r1),
`b879a6e8…` (r2), `734658e2…` (r3), `a3b71b7f…` (r4) and `2737e51e…` (r5), so
no earlier round transcribed this text and the diff step is a no-op that files
nothing. My build was whole — applied, green on all seven runnable clauses, and
variant-tested — before any predecessor apparatus directory was opened; the only
thing read out of them was `SOURCE.sha256`, after that point. The dispatch did
brief me on r5's finding ids, and I read `verdicts/CON-audit-r5.md`; neither is
a predecessor's build, and no earlier round's implementation was read at all.

**r5's repairs, re-derived. All five land.**

- F1 (blocker, C-4) → `c4-rerun-overwrites-second` and
  `c4-rerun-reports-first-only` were both green in r5 and are both red now, at
  `post-adoption run overwrote the second edit: wholesale trust, delayed by one
  re-init` and `post-adoption run names ['.agent-guild/CLAUDE.md'], not both
  refused files`. Both still leave `c3` green, so `c4` is the arm that closed
  it.
- F2 (major, C-1) → `c1-version-hardcoded` red at `the stamp does not come from
  the installing package's manifest: '0.7.1' != '9.9.9'`.
- F3 (major, C-1) → `c1-codex-run-scoped` red at `codex record shrank to the
  files the re-run copied`, and it is the first arm to fire, ahead of the Claude
  re-run.
- F4 (minor, C-5) → `c5-claude-version-compiled-in` and
  `c5-codex-version-compiled-in` both red at `the <kind> nudge does not read its
  own package's manifest`.
- F5 (minor, C-5) → `c5-below-double-reg` red at `the version gap is lost when
  the plugin is registered twice`, and the reference satisfies the
  double-registration and jurisdiction sentences at once, so the fork r5 found
  is settled rather than traded for a new one.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | The record contract, the payload scope and the Claude arm's run-time lookup and re-run all discriminate. Below the Codex branch the arms assert a strict subset of what the Claude arm asserts, and the clause's text draws no such line. As found: red (`provenance record missing`). Reference: green. Variants: `c1-claude-only`, `c1-third-key`, `c1-wrong-hash` class (`c1-records-owned-hooks`), `c1-version-hardcoded`, `c1-run-scoped`, `c1-codex-run-scoped` all red; `c1-codex-version-hardcoded`, `c1-codex-rerun-no-advance` and `c1-skills-rerun-records-hooks` green. | `probe-183.py:193-234` (Codex arm), `:274-292` (pinned Claude package only), `:239-272` (repo-local shape, fresh install only) — see F1, F4 |
| C-2 | — | Sound. Every sentence is reached and every one discriminates: the per-file decision, the stamp not gating it, the restamp, the version advance and all three summary terms. As found: red. Reference: green. Variants: `c2-first-clean-only`, `c2-stamp-gates`, `c2-count-examined`, `c2-no-restamp`, `c2-no-version-advance` — all five red, each at the assertion naming its own property. | `probe-183.py:306-373` |
| C-3 | — | Sound. Refusal set, carried-forward hash, upgrade, net-new landing, exit code and the version bump all reached and all discriminating. As found: red. Reference: green. Variants: `c3-abort-on-conflict`, `c3-restamp-preserved`, `c3-hold-version-on-conflict`, `c3-first-conflict-only` — all four red. | `probe-183.py:376-452` |
| C-4 | — | Sound, and r5's blocker is closed. Adoption, non-adoption, the record's key set, the post-adoption re-run's whole refused set, that run's preserved bytes, and the revert escape hatch all discriminate. As found: red. Reference: green. Variants: `c4-adopt-wholesale`, `c4-record-entry-for-refused`, `c4-no-revert-escape`, `c4-rerun-reports-first-only`, `c4-rerun-overwrites-second` — all five red. | `probe-183.py:510-522` is the repaired re-run assertion; it fires on both files |
| C-5 | major | Seven arms. The stamped version, the running version, both hosts' commands, the question, both packages' run-time lookups, the repo-local silence and exit code, the write-nothing property, the fully-installed independence and the double-registration co-presence all discriminate. Two sentences do not: jurisdiction, and the partial-init half of "every applicable message appears in the same run". As found: red. Reference: green. Variants: `c5-keyed-on-record-exists`, `c5-no-command`, `c5-claude-command-everywhere`, `c5-claude-version-compiled-in`, `c5-codex-version-compiled-in`, `c5-below-partial-return`, `c5-below-double-reg`, `c5-repo-local-raises`, `c5-nudge-writes` red; `c5-ignores-jurisdiction` and `c5-suppresses-partial` green. | `probe-183.py:706-724` asserts only the gap strings; no arm builds a project holding a record and no marker — see F2, F3 |
| C-6 | — | Sound. Text, check and failing example agree on one artifact. As found: red. Reference: green. Variant `c6-record-gitignored` red (`provenance.json is gitignored; a tracked record must be addable`). | `probe-183.py:752-764` |
| C-7 | — | Sound rubric. Applicable, and its failing example is still on the page: `docs/installing.md:137` says "A drifted payload file never upgrades in place, because the installer keeps no record of what it shipped", which C-2 makes false, and the #214 table at `:135` says the payload class "preserves each differing one". Judged by reading; nothing to execute. | `docs/installing.md:118, 130-137` |
| C-8 | — | Sound. As found: green (declared green; `50 passed, 0 failed` plus a clean `--check`). Reference: green — and the suites' own double-registration cases survive C-5's removal of that early return, so C-5 and C-8 do not collide. Variant: source edited without regenerating → `--check` exit 1, `content differs: project-template/install.py` on both targets. | the clause's own command |
| C-9 | — | Sound rubric, and independently load-bearing: my reference added zero test cases and C-8 stayed green, so C-8 cannot stand in for it. Confirmed twice more — `test_hooks.py` stayed at `371 passed, 0 failed` against both of the implementations F2 and F3 say the probes accept, so the existing suites do not backstop C-5 either. | clause text and check |
| preamble | — | Sound. The weight (`deep`) matches the spec's signals — verification did require building an instrument, and this round rebuilt it — and its stated reason agrees with the paragraph below it. Protected content is `none`, which needs no parse. The record contract determined an implementation on the first attempt. The content citation resolves: `docs/installing.md:137` carries "install() splits them out of the payload before the drift check runs". | `constitution.md:3, 24-38, 129` |

**Free axes.** Three places where the contract leaves an implementer a choice
and the harness accepts either, recorded rather than filed: where the record is
stamped relative to `_copy_owned` of the Codex project hooks (either order
yields the same record, since those hooks carry no entry); whether a net-new
file counts toward the summary's `updated` term (C-2's fixture has no net-new
file, C-3's asserts no counts); and the record's JSON formatting. None changes
what any check accepts.

## Diagnosis

Four findings: two major, two minor. **None is a blocker, and I want to be
unambiguous about that**, because the user's rule for this round turns on it. I
built the whole deliverable from these clause texts alone and it went green on
every probe and on C-8 on the first attempt, with no ambiguity I had to settle
by guessing and no second reading of any clause that would produce a materially
different program. Nothing here would mislead a worker into building the wrong
thing. Every finding runs the other direction: a sentence the clause states
plainly and its check cannot falsify, so a worker who gets that sentence wrong
is not caught. Nor is any of it Phase 1's to catch — each is a property of one
clause read against its own check, which is what a CON round is chartered for.

Both majors are the same shape as r5's F2 and F4, one host over. That shape has
now recurred in four consecutive rounds, which is itself worth saying out loud:
the pattern is a clause whose text names two things and whose probe pins one of
them.

### F1 — major (C-1)

**Below the Codex branch, C-1's arms assert a strict subset of what the Claude
arm asserts, and the clause's text draws no such line.** Two sentences are
affected, both about the stamp:

- "`version` equal to that host package's own manifest, read at run time rather
  than compiled in — provably, since a copy of the package whose manifest
  carries a version nothing else does stamps that version." The clause opens by
  naming both hosts — "`claude` from the Claude package, `codex` from the Codex
  one" — and states the proof method itself. `pinned_package` at
  `probe-183.py:164-190` takes a `kind` and does exactly that, and C-5's arm 3b
  now loops it over both packages. C-1 calls it once, for `claude`
  (`:274-292`).

  Variant `c1-codex-version-hardcoded`: the Claude branch reads its manifest,
  the Codex branch returns the literal `"0.7.1"`. `probe c1` green. The Codex
  arm at `:206-210` compares the stamp against the real manifest, and both
  manifests carry `0.7.1` by construction — they are generated from one
  `scripts/plugin-src/plugin.json` — so it cannot tell a lookup from a constant.

- "again after an idempotent re-run that copies nothing." r5's F3 repair added a
  Codex re-run, and it works: `c1-codex-run-scoped` is red. But the re-run
  assertion at `:230-234` checks the entry *set* alone, where the Claude re-run
  hands the whole contract to `_assert_record_covers` (`:303`) — keys, version,
  entry set and every hash.

  Variant `c1-codex-rerun-no-advance`: below the Codex branch, a run that finds
  an existing record leaves the stamp where it was. `probe c1`, `c2`, `c3` and
  `c4` are all green. Nine clauses green on an implementation where a Codex
  project's stamp freezes on the first install.

Both variants ship the same outcome: on Codex the stamp is a constant, so the
project drifts and nothing notices — the issue's headline defect, unfixed on one
of two supported hosts. It is also C-3's own stated failure mode ("a stamp held
back … pins the project forever and leaves C-5's nudge firing every session with
nothing that clears it") reached by a route C-3 does not cover, since C-3 is
Claude-only by the third non-goal. And that non-goal rests on this clause: it
waives Codex coverage of C-2 through C-4 on the ground that "the host-specific
lookups are covered rather than waived: C-1 drives all three install shapes."
The stamp lookup is the host-specific one, and it is the one C-1 pins on a
single host.

Repair, both halves in `c1`, and both are probe work rather than clause text —
C-1's text is already right:

1. Call `pinned_package("codex")` the way `c5` already does, install from the
   copy with `CODEX_INSTALLER`'s equivalent inside it, and assert the record
   carries `9.9.9`.
2. Give `_assert_record_covers` a manifest parameter and run the Codex re-run
   through it, instead of the bare set comparison at `:230-234`.

### F2 — major (C-5)

**"It stays subject to jurisdiction: no marker, no output of any kind" is
unreachable, and the clause's own double-registration requirement pressures a
worker toward violating it.**

Variant `c5-ignores-jurisdiction`: the gap notice prints from inside the
`if not _lib.guild_initialized():` branch, above the marker gate rather than
below it. `probe c5` green on all seven arms. `test_hooks.py` also green,
`371 passed, 0 failed` — the suite's `bare_no_marker` and `zero_evidence`
jurisdiction fixtures hold no provenance record, so no gap exists in them and
the notice stays silent for the wrong reason. C-8 does not backstop this.

What makes it worth a major rather than a note is that the clause pushes both
ways at once and only checks one. The notice has to appear in a
double-registered project, and the double-registration branch sits *above* the
marker gate at `session-nudge.py:144-156`. There are two ways to satisfy that:
drop the early return and leave the notice below the marker gate (what I built),
or hoist the notice above both. The second passes every arm in `c5` and violates
the jurisdiction sentence in the same clause. A worker reaching for the shorter
edit lands on it.

The state is reachable and the repo already treats it as important. The record
is tracked and sits beside the marker, so a `git rm` that takes the marker and
leaves the record — #212's scenario, the reason `guild_initialized()` keys on
the marker rather than the directory — produces a project the nudge would now
speak in after the user removed the guild from it.

Repair: an arm that fresh-installs, stamps the record down, removes
`.agent-guild/CLAUDE.md`, and asserts the nudge prints nothing at all. Three
lines, and `run_nudge` already gives you the write-nothing half.

### F3 — minor (C-5)

**"So every applicable message appears in the same run" is checked for the
double-registration pairing and not for the partial-init one.**

Arm 5 at `probe-183.py:706-724` builds a project that is both stale and
partially initialized and asserts only `"0.0.1" in stdout and ver in stdout`.
Its own comment says the other half — "one written above it must not suppress
the partial-init report either. Both messages belong to the same run" — and
nothing asserts it. The double-registration arm directly above it does assert
both messages (`:699-704`), which is what makes this read like an oversight
rather than a decision.

Variant `c5-suppresses-partial`: the gap notice prints and then returns 0,
swallowing the partial-init report. `probe c5` green; `test_hooks.py` green at
`371 passed, 0 failed`, since its partial-init fixtures carry no record.

Minor rather than major because the double-registration arm rules out the
crudest version of this (a notice that returns 0 before everything). What
survives is a notice placed between the two, which suppresses the #212 nudge for
exactly the projects that are both stale and half-installed.

Repair: one clause in arm 5's assertion —
`assert "partially initialized" in r_partial.stdout`.

### F4 — minor (C-1)

**The `codex --project-skills` shape gets a fresh install and no idempotent
re-run, though the clause says "on each of those shapes … and again after an
idempotent re-run".**

The repo-local arm at `:239-272` installs once and stops. It is the shape whose
whole reason for existing is the owned-hooks exclusion, and the exclusion is
only ever observed on a fresh install.

Variant `c1-skills-rerun-records-hooks`: the record is built from a walk of
`.agent-guild/` stamped after `_copy_owned` lands the hooks, but only when a
record already exists. `probe c1` green. The unconditional version of the same
mutation, `c1-records-owned-hooks`, is red at `record carries owned hook files it
does not govern`, which is what shows the gap is the missing re-run rather than a
missing assertion.

Minor because the defect it admits is narrow — a run-scoping error is caught on
the bare Codex arm, and a tree-walk error is caught on this shape's fresh
install, so what is left is a defect confined to this shape's second run.

Repair: re-run `CODEX_INSTALLER … --project-skills` against `skills_tmp` and
repeat the `recorded_hooks == []` and entry-set assertions.

## What is not wrong

Worth stating plainly, since this is the sixth round and the document is close.

No clause contradicts another, and I tested the one pairing that looked like it
might: C-5's demand that the notice survive the double-registration early return
against C-8's existing case asserting that a double-registered project prints
`exactly one stdout line`. My reference satisfies both, because that fixture
holds no marker. C-2, C-3, C-4 and C-6 are complete — I could not find a sentence
in any of them a variant could violate while the probe stayed green, and
nineteen variants tried. C-4 in particular now discriminates on the assertion
r5's blocker was about, on both files and on both their bytes and their names.
Every clause names a concrete check and a failing example its check actually
catches: `c1-claude-only`, `c2-first-clean-only`, `c3-abort-on-conflict`,
`c4-adopt-wholesale`, `c5-keyed-on-record-exists`, `c6-record-gitignored` and the
C-8 stale-build variant are each that clause's own failing example, run and red.
The preamble's record contract determined an implementation on the first
attempt, on both hosts and all three install shapes. The spec's eight acceptance
criteria all map onto clauses; the three intake rulings are all carried by clause
text and all checked. The weight is `deep` and the reason recorded on that line
is true — I rebuilt the instrument this round, which is the evidence for it.

All four findings are probe repairs. No clause text changes are owed by this
round.
