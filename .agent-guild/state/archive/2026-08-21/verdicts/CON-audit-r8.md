---
audit: CON-audit
round: 8
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: ba971fec3399e677ec8b8bb7b52eef603140c61e9f3a86535e9d24f014eef06e
verdict: PASS
checked_at: 2026-08-20T22:41:00Z
---

## Scope and method

The constitution reads `ba971fec…`, matching the `CON-audit-r8.md.sha256` the
dispatch wrote. It moved one sentence since r6/r7 (`b272140f…`): C-5's
jurisdiction clause, the F3 repair. `.agent-guild/state/checks/probe-183.py`
moved from `bf52ca8f…` to `5c65bb9b…`, the F1 and F2 repairs.

Every clause carrying a runnable check ran three ways: against the tree as
found, against a reference implementation built this round from the clause
texts and the preamble's pinned record contract, and against variants built to
violate each clause's stated property. C-7 and C-9 carry `checker-judgment:`
rubrics, have nothing to execute, and were judged by reading. Nothing was
`blocked` and nothing went unexecuted. Twenty variants ran; every one landed
red at its own clause's own assertion except the one that is supposed to be
caught elsewhere, which is recorded below.

Preflight, on the tree as found:

- `check-job-spec.py .agent-guild/state --audit-id CON-audit --repo-root .` —
  exit 0. Weight is `deep`, which carries no ceiling, so R18 owes no
  `**Ceiling overrun**:` line and none is present. No `**Lint exception**:`
  line, so R20 does not apply.
- `check-baselines.py .agent-guild/state --repo-root .` — exit 0,
  `ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)`. Every
  declared baseline held and the sweep filed nothing. The two skips are C-7
  and C-9, which is the whole of the constitution the sweep did not cover.
- Each of C-1 through C-6 also ran by hand on the untouched tree. All six died
  on the property, not a precondition: five at
  `provenance record missing: …/provenance.json`, C-4 at the `os.remove` of a
  record that does not exist. C-8 ran green (`50 passed, 0 failed`, clean
  `--check`).

The reference implementation lives at
`.agent-guild/state/apparatus/CON-audit-r8/`. `apply.py` patches the two
shared sources the clauses reach — `scripts/plugin-src/install-project.py` and
`.agent-guild/hooks/session-nudge.py` — then regenerates both packages with
`build-plugin.py`; `variants.py` applies one mutation at a time and runs the
probe meant to catch it; `probe-netnew-count.py` measures the one axis r7 asked
this round to re-confirm. The reference went green on c1, c2, c3, c4, c5, c6
and C-8 on the first run, arm 5 included.

**Venue.** All building and breaking happened in one whole-tree copy at
`/private/tmp/con-r8-work-8J1aw9`, extracted with `git archive HEAD` and
patched in place from pristine sources for each variant rather than re-cloned;
never more than one copy existed at a time. Probe fixtures were redirected to
`/private/tmp/con-r8-fixtures-FsxQ01` by `TMPDIR` and swept after every probe
run. Both directories were removed by name before filing, and both are gone.
Six `probe183-*` fixtures that predated this round in the per-user `$TMPDIR`
(`/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T`, which was not removed —
only its `probe183-*` entries were) are also gone. `git status --porcelain`
was clean when this round opened and is clean as it files. The only writes
into the repo are under `.agent-guild/state/apparatus/CON-audit-r8/` and the
gitignored `state/log/build-*.log` that `check-build.sh` tees. The
`__pycache__` the baseline sweep left under `.agent-guild/hooks/` was removed;
the two under `scripts/` and `.agent-guild/scripts/` predate this session and
were left alone.

**Comparand: none, and this is a genuine no-op rather than a skipped step.**
No earlier round's `SOURCE.sha256` records `constitution.md` at `ba971fec…` —
r6 and r7 both record `b272140f…`, and every round before them a different
digest again — and none records `probe-183.py` at `5c65bb9b…`. Both documents
this round's build read have moved, so there is no predecessor built from
matching source and the diff would be noise. My build was whole — applied, run
against all six probes and C-8, and variant-tested through twenty mutations —
before anything under `apparatus/CON-audit-r7/` was touched, and what was
touched there was its `SOURCE.sha256` and a filename listing. No predecessor's
`apply.py`, `variants.py`, or `orig/` was opened at any point. Nothing is filed
from this step.

**r7's three repairs, re-derived. All three land.**

| r7 finding | repair | verdict |
| --- | --- | --- |
| F1 (blocker, C-5, arm 5's unreachable assertion) | `shutil.rmtree` of `state/tasks` + landed-assert at `probe-183.py:776-778` | **lands.** Reference green on arm 5; `c5-suppresses-partial` red at `the gap notice suppressed the partial-init report` |
| F2 (major, C-1, frozen stamp invisible) | stamp-down to `0.0.1` before both re-runs, at `:223-225` and `:338-340` | **lands, on both hosts separately.** `c1-codex-rerun-no-advance` red at `codex re-run: '0.0.1' != plugin '0.7.1'`; `c1-claude-rerun-no-advance` red at `re-run on an already-initialized project: '0.0.1' != plugin '0.7.1'` |
| F3 (minor, C-5, jurisdiction sentence) | "no marker, no version notice", plus the sentence naming what it does not license | **lands.** The fork is closed by text, and the wrong reading is caught by the check the clause names — `c5-jurisdiction-strict` fails five `test_hooks.py` assertions under C-8 |

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | — | Sound, and r7's one open gap is closed. The record contract, the payload scope, both hosts' run-time manifest lookups, the `--project-skills` re-run and — new this round — both idempotent re-runs now discriminate. As found: red (`provenance record missing`). Reference: green. Variants: `c1-claude-only` red at the missing record on the Codex venue; `c1-codex-version-hardcoded` red at `the codex stamp does not come from the installing package's manifest: '0.7.1' != '9.9.9'`; `c1-claude-version-hardcoded` red at the same assertion on the Claude arm; `c1-records-owned-hooks` red naming nine `.agent-guild/hooks/` paths; `c1-rerun-no-advance`, `c1-codex-rerun-no-advance` and `c1-claude-rerun-no-advance` each red at their own host's re-run. The third non-goal's claim that "C-1 drives all three install shapes" now covers the stamp lookup it rests on. | `probe-183.py:223-233, 295-309, 338-343` |
| C-2 | — | Sound. Per-file decision, the stamp not gating it, the restamp, the version advance and all three summary terms are reached and discriminate. As found: red. Reference: green. Variants: `c2-first-clean-only` red at `stale-but-clean .agent-guild/templates/task.md was not upgraded` — the second of two files; `c2-preserve-on-stale-stamp` red at `summary preserves a file nobody edited`, naming 36 paths, which is the clause's failing example reproduced verbatim; `c2-stamp-gates-the-decision` red at `a file clean against its record was skipped because the stamp matched`. | `probe-183.py:346-413` |
| C-3 | — | Sound. Refusal set, carried-forward hash, upgrade, net-new landing, exit code and the version bump all reached. As found: red. Reference: green. Variants: `c3-abort-on-conflict` red at `mixed run failed`, naming both edits; `c3-refresh-preserved-hash` red at `a preserved file's recorded hash was refreshed from its on-disk bytes`; `c3-hold-version-on-conflict` red at `a run that preserved a file left the stamp at '0.0.1'`. | `probe-183.py:416-492` |
| C-4 | — | Sound. Adoption, non-adoption, the record's key set, the post-adoption re-run's whole refused set and the revert escape hatch all discriminate. As found: red. Reference: green. Variants: `c4-adopt-wholesale` red at `adoption recorded an entry for a file it refused`; `c4-no-entry-never-recorded` red at `a reverted file matching current source was not recorded`. | `probe-183.py:495-580` |
| C-5 | — | Sound, and satisfiable — which is what r7's blocker denied. Arm 5's fixture now removes `state/tasks`, which is what `_missing_pieces()` actually reads, so the reference prints the gap notice and `partially initialized` in one run and the arm separates a conforming build from a suppressing one. As found: red. Reference: green on every arm. Variants: `c5-keyed-on-record-exists` red at `nudge reports a version gap on an up-to-date project`; `c5-suppresses-partial` red at `the gap notice suppressed the partial-init report`; `c5-ignores-jurisdiction` red at `the nudge speaks in a project carrying no marker`; `c5-writes-to-the-project` red at `the nudge wrote to the project`. `c5-jurisdiction-strict` (the old reading (b)) stays green on `probe c5` and goes red under C-8 — see the scope note below, which is a recorded fact rather than a finding, because the clause now names that check by hand. | `probe-183.py:766-786` against `session-nudge.py:110-128, 161-166` |
| C-6 | — | Sound. Text, check and failing example agree on one artifact. As found: red. Reference: green. Variant `c6-record-gitignored` red at `provenance.json is gitignored; a tracked record must be addable`. | `probe-183.py:814-826` |
| C-7 | — | Sound rubric. Still applicable, and its failing example is still on the page: `docs/installing.md:137` says "A drifted payload file never upgrades in place, because the installer keeps no record of what it shipped", which C-2 makes false, and the #214 table at `:135` says the payload class "preserves each differing one". Judged by reading; nothing to execute. | `docs/installing.md:118, 130-137` |
| C-8 | — | Sound, and load-bearing beyond its own text: it is what pins the net-new counting axis and what catches the reading of C-5's jurisdiction sentence the clause rules out. As found: green (declared green). Reference: green (`371 passed, 0 failed`; `50 passed, 0 failed`; clean `--check`). Variant `c8-stale-build` red at `content differs: project-template/install.py`. | the clause's own command |
| C-9 | — | Sound rubric, and independently load-bearing for the third round running: my reference added zero test cases and C-8 stayed green at 371/50, so C-8 cannot stand in for it. | clause text and check |
| preamble | — | Sound. The weight (`deep`) matches the spec's signals — verification did require building an instrument, and this round rebuilt it from scratch, which is the evidence for the reason recorded on that line. Protected content is `none`, which needs no parse. The record contract determined an implementation on the first attempt, on both hosts and all three install shapes, with no axis I had to settle by guessing. The content citation resolves: `docs/installing.md:137` carries "install() splits them out of the payload before the drift check runs". | `constitution.md:3, 24-38, 129` |

## What the round confirmed, beyond the repairs

**C-2's counting sentence does not contradict C-8's net-new pin.** r7 recorded
that `test_build_plugin.py:1524-1540` requires `updated == 1` on a re-run whose
only movement is a net-new file landing, and asked this round to check C-2 for
a contradiction, since its counting sentence is where one would show up. There
is none. Read straight — "`updated` counts exactly the files whose bytes
changed" and "the count reports files moved rather than files examined" — a
net-new file is a file the run moved, and the reference built from that reading
reports `updated=1 unchanged=37 preserved=0` and passes C-8. The alternate
reading was built too, counting a net-new landing toward `unchanged`: `probe c2`
and `probe c3` both stay green against it, and C-8 goes red by name at
`re-init's counts conserve the payload without double-counting the preserved
file`. So the axis is pinned, not free, and it is pinned by a check this
constitution already runs — the same shape as C-5's jurisdiction sentence.

**Two clause properties this round found are settled only by C-8.** Neither is
a defect, because both clauses name C-8's suites in their own text, but they
are worth writing down: `probe c5` cannot separate the two readings of C-5's
jurisdiction sentence, and no probe can separate the two readings of C-2's
counting sentence. In both cases the constitution's own C-8 does it loudly and
by name, which is why neither is filed as a finding. A future round that
weakens C-8 would silently un-pin both.

## What is not wrong

The reference implementation went up from the clause texts and the preamble's
record contract alone, on the first attempt, on both hosts and all three
install shapes, with nothing I had to settle by guessing. Every failing example
C-1 through C-6 and C-8 state was run as a variant, and each went red at its
own clause's own assertion. Every clause's text, check, and failing example
name the same artifact. No clause contradicts another. The weight is `deep` and
the reason recorded on that line is true. C-7's and C-9's rubrics both remain
applicable and both remain independent of C-8. Twenty of twenty variants were
caught by the check the constitution points at for them.

This is the third consecutive round to conclude the clause texts hold under an
independent build; r6 and r7 failed on the probe harness and on one sentence,
and all three of those repairs now discriminate in both directions. The
document is sound, and Phase 1 can open.
