---
audit: CON-audit
round: 4
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: a3b71b7f2132b13eb4b74a4899aed3f160ef1e36d3ae8855fe7c3313c6a1df14
verdict: FAIL
checked_at: 2026-08-21T00:44:09Z
---

## Scope and method

Every clause carrying a runnable check was executed three ways: against the tree
as found, against a reference implementation built from the clause texts and the
preamble's pinned contract alone, and against variants built to violate each
clause's own stated property. C-7 and C-9 carry `checker-judgment:` rubrics,
have nothing to execute, and were judged by reading. Nothing was `blocked`.

Preflight, on the tree as found:

- `check-job-spec.py .agent-guild/state --audit-id CON-audit --repo-root .` — exit 0.
  R17/R18 clear; the preamble carries no `**Lint exception**:` line, so R20 does not apply.
- `check-baselines.py .agent-guild/state --repo-root .` — exit 0,
  `ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)`. Every declared
  baseline held. The sweep filed nothing; the two skips are C-7 and C-9.

The reference implementation lives at
`.agent-guild/state/apparatus/CON-audit-r4/refA/` (`apply.py` plus the two files
it produces). It touches `scripts/plugin-src/install-project.py` and
`.agent-guild/hooks/session-nudge.py` and nothing else, and it went green on all
six behavior probes plus C-8 on the first run — the clause texts do determine an
implementation. 35 variants ran; `variants.py` and `variant.py` beside it carry
every one.

**Venue.** All building and breaking happened in a whole-tree copy at
`/private/tmp/con-r4-hhbPEf`, removed after the last run. The probes' own
fixtures land under `$TMPDIR` as `probe183-*`; 531 of them were removed from
`/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T` by name. `git status
--porcelain` was clean when this round opened and is clean as it files. The only
writes into the repo are under `.agent-guild/state/apparatus/CON-audit-r4/` and
the gitignored `state/log/build-*.log` that `check-build.sh` tees.

**Comparand.** None. This round's build read
`constitution.md` at `a3b71b7f…`; the predecessors' `SOURCE.sha256` record
`bf8f5970…` (r0), `b0408bf8…` (r1), `b879a6e8…` (r2) and `734658e2…` (r3), so no
earlier round transcribed this text and the diff step is a no-op that files
nothing. My own build was whole — applied, green, and variant-tested — before any
predecessor directory was opened; the only thing read out of them was
`SOURCE.sha256`, after that point.

**r3's repairs, re-derived.** All seven land and all seven discriminate. F1 →
V20 red (a Codex session handed `/agent-guild:init` fails arm 3). F2 → V18 red (a
repo-local nudge that raises exits 2 and fails arm 4). F3 → V19 red (a write on
the Codex branch alone is caught, because every arm snapshots its own project).
F4 → V10 and V15 red. F5 → V6 red, and the per-file settlement is implementable:
the reference reads the record, never the stamp. F6 → V14 red, likewise
implementable. F7 → the citation by content resolves to `docs/installing.md`'s
"`install()` splits them out of the payload before the drift check runs", which
is on the page.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | Text says the record contract holds "across all three shipped install shapes"; the check asserts the whole contract on one of them. As found: red (`provenance record missing`). Reference: green. Variants: V1/V2/V3/V4/V5 red — but V22, V29, V30 and V31 all green. | `probe-183.py:163-227`; the `codex --project-skills` arm asserts only the entry-path set and `recorded_hooks == []`, and the bare-`codex` arm never asserts the two-key shape |
| C-2 | blocker | The per-file settlement and the summary accounting hold up, but two of the clause's own sentences are unreachable: "every payload file whose bytes match its recorded hash" is exercised on a one-element set, and "advances the record's version" is never checked in a run that preserved anything. As found: red. Reference: green. Variants: V6/V7/V8/V9/V23 red; V26 and V32b green. | `probe-183.py:230-287`; both arms drift exactly one file, and `prov2["version"]` is asserted only in the arm with zero conflicts |
| C-3 | blocker | The refusal set, the carried-forward hash, the upgrade and the net-new landing all discriminate. "The version bump that same run performs" does not: nothing asserts it, in this clause or any other. As found: red. Reference: green. Variants: V10/V11/V12/V12b red; V32 green. | `probe-183.py:290-359`; `prov_after` is read for `files[key_a]` and then overwritten with `"0.0.2"` without its `version` ever being asserted |
| C-4 | major | Adoption, non-adoption of a differing file, the second run's refusal and the revert escape hatch all discriminate. "Covering the files whose bytes match current source" and "still preserves and reports those same files" are one-file spot checks. As found: red. Reference: green. Variants: V13/V14/V15/V27 red; V27b and V33 green. | `probe-183.py:362-429`; the adoption record is asserted at `key_b` alone, and the re-run's report at `key_a` alone |
| C-5 | major | Four arms, three of the four required output elements checked on the Codex arm, and the clause's one mechanism claim unfalsifiable. As found: red. Reference: green. Variants: V17/V18/V19/V20 red; V16 and V28 green. | `probe-183.py:475-556`; arm 3 asserts `"/agent-guild:init" not in out_c` and never asserts what *is* there; both packages' manifests are generated from one `scripts/plugin-src/plugin.json` version |
| C-6 | — | Sound. Text, check and failing example agree on one artifact. As found: red (`provenance record missing`). Reference: green. Variant V21 red (`provenance.json is gitignored; a tracked record must be addable`). | `probe-183.py:559-571` |
| C-7 | — | Sound rubric. Applicable, and its failing example is on the page today: `docs/installing.md` line 137 still says "A drifted payload file never upgrades in place… That record is #183", which C-2 makes false. Judged by reading; nothing to execute. | `docs/installing.md:130-137` |
| C-8 | — | Sound. As found: green (declared green, `50 passed, 0 failed` plus a clean `--check`). Reference: green, with zero regression cases added — which is the overrun line's own claim, independently confirmed. Variant: source edited without regenerating → `--check` exit 1, `content differs: project-template/install.py` on both targets. | the clause's own command |
| C-9 | — | Sound rubric. Falsifiable, and the "would fail against the tree as this job found it" qualifier is what keeps the refusal path honest — today's installer already preserves a drifted file, so only a case keyed to the *recorded* hash can satisfy it. Judged by reading; nothing to execute. | clause text and check |
| preamble | minor | The `**Ceiling overrun**` line is true and I re-derived it. The `**Job weight**` line's stated reason is contradicted by the preamble two paragraphs below it. | see F8 |

## Diagnosis

### F1 — blocker (C-3, requirement in C-2)

**Nothing checks that a run which preserves anything still advances the record's
version.** C-2 requires it ("advances the record's version"); C-3 states it as a
premise ("the refusal survives the version bump that same run performs"). No
probe reaches it.

Variant V32: `_write_record` keeps the recorded version whenever
`payload_conflicts` is non-empty, and advances it otherwise.

- `probe c3` — green. c3's mixed run reads `prov_after` only for
  `files[key_a]`, then overwrites `version` with `"0.0.2"` itself.
- `probe c2` — green. Both c2 arms are conflict-free, so the mutation never fires.
- `probe c4` — green. The adoption run has no prior record, so the
  `recorded is None` branch stamps the current version and satisfies
  `prov["version"] == current_version()`; the re-runs assert no version at all.

What this passes through is the issue's own headline symptom, relocated. The user
in `spec.md:43-53` holds a stale project with two local edits. They re-run init,
their clean files upgrade, their edits are refused correctly — and the record
stays pinned at the old release forever, because every subsequent run also has a
conflict. C-5's nudge then reports a version gap at every session start, and no
action the user can take clears it. Nine clauses green.

The failure is reachable by a defensible design decision, not just a slip: C-3's
text puts all its weight on the refusal *surviving* the bump, so a worker who
decides the safest way to make a refusal survive is not to bump has read the
clause and found nothing that says otherwise.

Repair, both halves:

1. C-3's text has to require the bump rather than presuppose it — something like
   "the same run advances the record's version to the running plugin's, whatever
   it preserved" — so the sentence is a requirement a check can be written
   against.
2. c3 asserts `load_prov(tmp)["version"] == current_version()` immediately after
   the mixed run, *before* the probe writes `"0.0.2"` into it, and c4 asserts the
   same after `r2`.

### F2 — major (C-1)

**"This holds across all three shipped install shapes" is checked on one shape.**
C-1's text names the whole contract — exactly the keys `version` and `files`,
`version` equal to that host package's own manifest, one entry per installed
payload file, each hash matching the bytes on disk, and again after an idempotent
re-run — and then says it holds across `claude`, bare `codex`, and
`codex --project-skills`.

What the arms actually assert:

| arm | two keys | version | entry set | hashes | idempotent re-run |
| --- | --- | --- | --- | --- | --- |
| `claude` (`_assert_record_covers`) | yes | yes | yes | yes | yes |
| bare `codex` | **no** | yes | yes | yes | **no** |
| `codex --project-skills` | **no** | **no** | yes | **no** | **no** |

Four variants green:

- V22 — the `--project-skills` path stamps `"0.0.0"`. `probe c1` green.
- V29 — the `--project-skills` path records `"0"*64` for every hash. `probe c1` green.
- V30 — the `--project-skills` record carries a third key. `probe c1` green.
- V31 — the bare-`codex` record carries a third key. `probe c1` green.

This also weakens the third non-goal, which waives Codex coverage of C-2 through
C-4 on the ground that "the host-specific lookups are covered rather than waived:
C-1 drives all three install shapes." C-1 drives them; it does not check them.
`--project-skills` is the direct Codex IDE bootstrap and the one route where the
owned hooks and the governed payload share a directory, which makes it the shape
most likely to attract bespoke record-writing code.

Repair: give `_assert_record_covers` a manifest parameter and run it over all
three arms plus a codex idempotent re-run, replacing the three hand-rolled
per-arm subsets. That closes all four variants at once.

### F3 — major (C-2)

**"Every payload file whose bytes match its recorded hash" is exercised on a
one-element set.** Both c2 arms drift exactly one file.

Variant V26: upgrade only the first clean-but-stale file encountered
(`if target_hash != source_hash and not updated:`). `probe c2` green — one stale
file means "the first" and "every" are the same thing, and `updated == 1`,
`preserved == 0`, `unchanged == total - 1` all still hold.

This is r3's F4 shape, in a clause the same round did not touch. The probe's own
comment at `probe-183.py:296-298` states the principle — "a one-element set
assertion proves only that a set has one element… and the spec's own repro
(spec.md:43-46) edits two" — and c2's upgrade set was left at one.

Repair: c2's first arm drifts two files clean against their recorded hashes,
asserts both reach source bytes and both are restamped, and asserts
`updated == 2` with `unchanged == total - 2`.

### F4 — major (C-4)

**Two of C-4's plural requirements are one-file spot checks.**

- "writes a record at the current version covering the files whose bytes match
  current source" — asserted at `key_b` alone. Variant V27b drops
  `.agent-guild/templates/task.md` from the adoption record while recording
  everything else. `probe c4` green.
- "on a further re-run still preserves and reports those same files" — `r2`
  asserts `key_a in r2.stdout` and nothing about `key_d`. Variant V33 makes the
  re-run stop reporting `key_d`. `probe c4` green.

r3's F4 gave the adoption run's *report* a whole-set assertion
(`named_adopt == sorted([key_a, key_d])`). Its record and its re-run report never
got one.

Repair: assert the adoption record's key set equals
`set(payload_files(tmp)) - {key_a, key_d}`, and give `r2` the same whole-set
`named` assertion the adoption run already has.

### F5 — major (C-5)

**The Codex arm checks that the wrong command is absent and never checks that the
right one is present.** C-5's text requires four things in the output — the
stamped version, the running plugin version, "the command that fixes it", and a
question — and says the Codex copy carries "that host's own command, not the
Claude one". Arm 3 asserts the first, second and fourth, plus
`"/agent-guild:init" not in out_c`. Nothing asserts a Codex command is there.

Variant V16: the Codex branch computes `init_invocation = ""`, so a stale Codex
project is told `"…Run  now to bring it up to date?"` — both versions, a question
mark, no command. `probe c5` green on all four arms.

r3's F1 closed "a Codex session is handed the Claude command string". Its mirror
image — a Codex session handed no command at all — is still open, and it is the
worse of the two for a user: the wrong command fails visibly, the missing one
leaves a prompt with nothing to act on.

Repair: C-5's text should name what the Codex command is (the existing
partial-init branch already computes `f"${prefix}init"`), and arm 3 should assert
it appears in `out_c`.

### F6 — minor (C-5)

**"It reads the running version from the manifest of the package its own hook
file ships inside" cannot be falsified by any arm.** Both packages' manifests are
generated from a single `scripts/plugin-src/plugin.json` version, so
`.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` carry the same
string at every release — `0.7.1` today, and by construction, not by
coincidence.

Variant V28: `_package_version` returns the literal `"0.7.1"` whenever a manifest
directory merely exists, reading nothing. `probe c5` green on all four arms,
including arm 3's `codex_ver in out_c`.

So arm 3 proves the reported version equals a value that is identical on both
hosts. It cannot separate "read this package's manifest" from "read the other
one" from "hardcode today's release" — which is the one mechanism claim C-5
makes, and the mechanism whose failure is precisely the bug class this job
exists to fix.

Minor rather than major because the wrong manifest path does not exist inside
either package, so the realistic wrong implementations mostly crash instead of
lying. Repair, if it is worth the arm: copy the package into a venue, bump that
copy's `plugin.json`, drive the nudge from the copy, and assert the reported
running version follows the copy.

### F7 — minor (C-5)

**C-5 leaves the ordering against the double-registration early return unpinned,
and no arm reaches it.** `session-nudge.py:144-156` returns 0 before anything
else when a plugin-rooted instance finds the guild's gates also wired into the
project's own hook config. C-5 says nothing about a project that is both
double-registered and stale, and no arm builds one: arms 1–3 have no guild gates
in `.claude/settings.json` or `.codex/hooks.json`, and arm 4's repo-local
instance skips the check by design.

Two faithful transcriptions — the version check before the early return, or after
it — produce materially different output on a real project state, and both pass
c5. The reference implementation had to pick (it put the version check after,
preserving the existing early return) and nothing in the constitution records the
pick.

Repair: one sentence in C-5 saying which warning wins when both apply, and an arm
that builds the combination.

### F8 — minor (preamble, `**Job weight**`)

**The weight's recorded reason is contradicted by the preamble two paragraphs
below it.** The weight line reads "standard, every acceptance check runs through
suites that already exist (test_hooks.py, test_build_plugin.py, build-plugin.py
--check) or through probes that drive the packaged installer rather than building
a new instrument". The preamble says the opposite about the suites: "nothing in
the suites asserts anything about provenance, so 'the Codex paths ride the
existing suites' is false for this job and is not claimed here."

Six of nine clauses check through `.agent-guild/state/checks/probe-183.py`, 585
lines written for this job, against which four audit rounds have now failed on
defects in the instrument rather than in the deliverable. `CLAUDE.md`'s own
discriminator — "does verification require building an instrument, or invoking
one that already exists?" — reads deep here, and "uncertainty fails toward deep"
points the same way. Deep carries no ceiling, so the overrun would not have
needed recording at all.

Nothing downstream is harmed: the ninth clause exists, and the
`**Ceiling overrun**` line is honest. I re-derived its claim independently — the
reference implementation added zero regression cases and C-8 ran green against
it, which is exactly the unfalsifiable half r0 found. The finding is only that
the record this job leaves for the next weight derivation says the harness
existed when it did not, and that record is the whole point of the overrun line.

Repair: correct the weight line's reason, or restate the weight as deep and drop
the overrun line. Either way the clause set stays as it is.

## What is not wrong

Worth saying, because four rounds of findings can make a document look worse than
it is. No clause contradicts another. Every clause names a concrete check and a
failing example its check actually catches (V1, V9, V12b, V13, V17, V21 and the
C-8 stale-build variant are each that clause's own failing example, run and red).
The protected-content manifest is `none`, which needs no parse. The record
contract in the preamble is complete enough that a reference implementation built
from it alone went green on every probe on the first attempt, with no axis I had
to guess at except the one in F7. The spec's eight acceptance criteria all map
onto clauses. The three intake rulings are all carried by clause text and all
checked.
