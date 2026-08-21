---
audit: CON-audit
round: 3
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: 734658e2b66fe7cb73b3418f537882caca5c5af173ea695860f709bb5723cece
verdict: FAIL
checked_at: 2026-08-20T19:20:00Z
---

## Scope and method

Every clause with a runnable check was executed three ways: against the tree as
found, against a reference implementation built from the clause texts and the
preamble's pinned contract alone, and against variants built to violate each
clause's stated property. C-7 and C-9 carry `checker-judgment:` rubrics and were
judged by reading.

The reference implementation lives at
`/Users/k.arnett/repos/agent-guild/.agent-guild/state/apparatus/CON-audit-r3/`
(`ref_install_patch.py`, `ref_nudge_patch.py`, `run.sh`, `VARIANTS.md`). It was
derived only from C-1..C-6, the preamble's record contract, and
`docs/installing.md:137` (the one document a clause explicitly names). The venue
it is applied in is `/tmp/conr3ref.Ya6GyQ`, outside the repo: each run rsyncs a
full repo copy, patches `scripts/plugin-src/install-project.py` and
`.agent-guild/hooks/session-nudge.py`, regenerates both packages with
`build-plugin.py`, and runs the probes from inside that copy so
`probe-183.py`'s `REPO` resolves to the build under test. Two throwaway git
repos were created under the system tmpdir and removed; both absolute paths are
printed in the evidence column below.

Baseline sweep, run against the tree as found:
`check-baselines: ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)`,
exit 0. The two skips are C-7 and C-9, correctly declared judgment. Every red
clause failed on its own logic (`provenance record missing`), not at a
precondition, so the sweep covers 7 of 9 clauses mechanically and the two it
skips are the two this round read.

`git status --porcelain` was empty at start and is empty at close. No
`__pycache__` remains under `plugin/`, `plugins/`, or `.agent-guild/hooks/`.

**Predecessor diff: no-op, filed nothing.** My own build was whole and every
variant had run before any predecessor directory was opened; only the
`SOURCE.sha256` files were then read. My constitution digest is
`734658e2…`; r0 recorded `bf8f5970…`, r1 `b0408bf8…`, r2 `b879a6e8…`. My
`probe-183.py` digest is `528a7b65…`; r1 recorded `de5d9807…`, r2
`11f23df0…`. No predecessor matches on either document my build transcribes,
so there is no comparand and this axis files nothing. (All four rounds match on
`spec.md`, but no artifact transcribes the spec.)

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | pass | Sound and discriminating. As-found RED (`provenance record missing`, codex arm). Reference RED→GREEN. `v_claude_only_record` (the clause's own failing example) RED on the codex arm; `v_true_run_scoped` RED on `re-run on an already-initialized project: entry set diverges … missing=[38 paths]`, so the idempotent-re-run sentence really does separate a whole-payload record from a run-scoped one. All three install shapes are driven. The `docs/installing.md:137` citation resolves and says what C-1 claims — but see F7. | apparatus `VARIANTS.md`; probe-183.py:161-225 |
| C-2 | **fail** | Fork, unsettled by the harness. "the recorded version trails the plugin's" reads either as a precondition on the in-place upgrade or as a description of when it is noticed, and the two are materially different programs. `v_version_gated` builds the first reading; c1-c4 and c6 all GREEN, identical to the second reading's run. c2's fixture pins the stamp to `"0.0.1"`, so the gate is always true and the expression is never exercised. The rest of C-2 is sound: `v_count_examined` RED (`summary counts files that did not move: payload=38 updated`), `v_preserve_all` RED (`summary preserves a file nobody edited`, 37 paths). Prior round's `unchanged`-term finding is verified repaired. | F5 below; apparatus `VARIANTS.md`; probe-183.py:253-263 |
| C-3 | **fail** | The diagnostic-set repair works — `v_preserve_all` is RED naming 36 paths, `v_restamp_preserved` is RED on `a preserved file's recorded hash was refreshed from its on-disk bytes` — but the set it proves is a one-element set. c3's fixture holds exactly one edited file, so "the only payload path the diagnostic names" is never tested against a run with two conflicts. `v_report_first_conflict_only` truncates the warning to `payload_conflicts[0]`; c1-c4 and c6 all GREEN. | F4 below; probe-183.py:266-319 |
| C-4 | **fail** | Two defects. (a) Fork: what a run does with "file exists, no recorded entry, bytes match current source" is undetermined between "always stamp it" and "only a run that wrote it stamps it"; `v_adopt_reading_b` builds the second and c1-c6 are all GREEN. (b) "reports each file that differs" is proven against one differing file — `v_report_first_conflict_only` GREEN. Sound otherwise: `v_adopt_wholesale` RED on `adoption recorded an entry for a file it refused`, and the second re-run arm holds. | F4, F6 below; probe-183.py:322-356 |
| C-5 | **fail** | Three defects, all in the half added since r2. The Codex arm never sets `hook_host`, so it runs the Claude host branch (`v_claude_host_only` GREEN); the repo-local third deployment is reached by nothing (`v_raise_no_manifest` GREEN, and the installed adapter then exits 2 on SessionStart); "byte-identical … after every one of those runs" is snapshotted for one of three runs (`v_writes_on_quiet` GREEN). What r2 repaired does hold: `v_keyed_on_existence` RED (`nudge reports a version gap on an up-to-date project`), `v_claude_manifest_only` RED, `v_no_question` RED, `v_writes_breadcrumb` RED (`added=['.agent-guild/.nudged']`). | F1, F2, F3 below; probe-183.py:368-461; codex-hook-adapter.py:230,254; session-nudge.py:141 |
| C-6 | pass | As-found RED (`provenance record missing`). Reference GREEN. `v_gitignore_record` (the clause's own failing example) RED on `provenance.json is gitignored; a tracked record must be addable`. Both halves of the text are asserted, including that `state/` stays ignored. Claude-only, which the preamble's "the remaining probes drive the Claude package" covers; `_gitignore_update` carries no host branch at all, so the exposure is nil. | probe-183.py:464-476 |
| C-7 | pass | Rubric, judged by reading — nothing to execute. Applicable and falsifiable against the live tree: the #214 re-init table at `docs/installing.md:132-135` says the payload class is one where "init lands each missing file and preserves each differing one", which C-2 makes false, and that is the clause's own failing example sitting in the repo today. The four behaviors it enumerates each have a checkable statement in the doc. | docs/installing.md:132-137 |
| C-8 | pass | As-found GREEN (baseline green, matching): 371 + 50 tests pass and `--check` validates. GREEN against the reference implementation too, which is the run that matters for a no-regression clause — a conforming build regenerates cleanly. Discriminating: appending one comment line to `scripts/plugin-src/install-project.py` without rebuilding gives `--check` exit 1, `claude: content differs: project-template/install.py`, which is the clause's own failing example. | /tmp/conr3ref.Ya6GyQ/c8v.log |
| C-9 | pass | Rubric, judged by reading. Applicable as written, and r2's worry does not bite: the "assert on the installed bytes or the record's contents, not on a log line" rule disqualifies nothing C-9 actually requires, because all three paths it names (upgrade, refusal, mixed-with-net-new) produce installed bytes and record entries. C-9 never asks for a nudge regression case, so the artifact that has only output is out of its scope by construction. It also tracks the spec's own acceptance line exactly. | spec.md:83; constitution C-9 |

## Diagnosis

Seven findings: two blockers, four majors, one minor. Six of the seven were
found by building a variant rather than by reading, per the standing
instruction; the seventh (F7) was found by resolving a citation.

The concentration is where the document changed since r2. C-5 was extended in
two directions this round and both extensions carry the same defect the round
before them carried: the text grew, the check did not follow it all the way.

---

### F1 — C-5, blocker: the Codex arm is a Claude-host invocation, so the Codex host branch is checked by nothing

`probe-183.py:446-454` drives `plugins/agent-guild/hooks/session-nudge.py` with
an input object carrying `cwd`, `hook_event_name`, and `session_id` — and no
`hook_host`. `session-nudge.py:141` reads
`host = data.get("hook_host", "claude")`. Every real Codex session sets it:
`codex-hook-adapter.py:230` does `data = {**data, "hook_host": "codex"}`
unconditionally, and `:251-256` sets it again for this exact gate along with
`agent_guild_skill_prefix`. So the arm runs the Claude host branch of a file
that happens to live in the Codex package directory.

Demonstrated: variant `v_claude_host_only` gates the version-gap check on
`host == "claude"`. **c5 PASSES.** That implementation is silent in every real
Codex session — the precise failure the Codex extension was written to close,
displaced from the manifest path to the host field.

Corroborating, from the reference implementation's own Codex arm, driving the
same file with the two inputs side by side:

```
--- probe's input (no hook_host)
"agent-guild: this project's payload was installed by version 0.0.1; the running plugin is 0.7.1. Run /agent-guild:init now to catch it up?\nagent-guild: this project looks partially initialized (missing CLAUDE.md)—run /agent-guild:init to finish the install.\n"
--- real Codex adapter input
"agent-guild: this project's payload was installed by version 0.0.1; the running plugin is 0.7.1. Run $init now to catch it up?\n"
```

The arm's own fixture is not the thing C-5 describes. C-5 requires "a fully
installed project"; under the probe's input the nudge diagnoses this Codex
project as partially initialized and missing `CLAUDE.md`, because
`_missing_pieces(root, "claude")` looks for the Claude marker in a project that
has `AGENTS.md`. The fix command it prints is `/agent-guild:init`, which is not
the invocation a Codex user can run.

Text and check disagree about the artifact: the text says "the Codex package's
copy reports the gap in a Codex project", the check reports the gap in a Codex
*directory* under a Claude-host invocation.

**Fix (clause revision plus another CON round).** The Codex arm's input must
carry `"hook_host": "codex"` and an `agent_guild_skill_prefix`, and must assert
what only that branch can show: that the gap line names the Codex fix command
(the `$…init` form, which C-5's text already requires as "the command that
fixes it" with no host qualifier), and that no partial-init line fires on a
fully installed Codex project. Note that the fix-command element is currently
unasserted on the Codex arm entirely — `v_no_fix_command_on_codex` also passes,
for the same root cause.

### F2 — C-5, blocker: the third nudge deployment is reached by no clause and waived by no non-goal

There are three places `session-nudge.py` runs, not two:

1. the Claude package, `plugin/hooks/session-nudge.py` — C-5's first arm;
2. the Codex package, `plugins/agent-guild/hooks/session-nudge.py`, wired by
   `${PLUGIN_ROOT}/hooks/codex-hook-adapter.py session-nudge` — C-5's Codex arm;
3. the repo-local copy, `<project>/.agent-guild/hooks/session-nudge.py`,
   installed by `codex --project-skills` and wired by that route's
   `.codex/hooks.json` SessionStart entry
   (`python3 "$(git rev-parse --show-toplevel)/.agent-guild/hooks/codex-hook-adapter.py" session-nudge`).

C-1's own `--project-skills` arm proves route 3 is live and installs those
hooks — `probe-183.py:200-203` asserts the hooks directory landed and is
non-empty. C-5 never drives it.

That copy ships inside no package, so C-5's rule "reads the running version from
the manifest of the package its own hook file ships inside" has no manifest to
name there. Whatever the implementation does in that case is unconstrained by
every clause in the document.

Demonstrated: `v_raise_no_manifest` raises when no manifest is found beside the
hook. **c1 through c6 all PASS.** Driving the installed repo-local adapter under
that build then gives:

```
SessionStart exit: 2
stderr: RuntimeError: no package manifest beside <project>/.agent-guild
        The verification gate did NOT run. Fix .agent-guild/hooks/ before proceeding
```

Exit 2 is a block. Every repo-local Codex project's session start is broken, and
the constitution is green end to end.

The non-goals section makes an affirmative claim this falsifies: "The two
host-specific lookups are both covered rather than waived." There are three
deployments and this one is neither covered nor waived.

**Fix (clause revision plus another CON round).** C-5 must say what the
repo-local copy does. Silence is the defensible answer and is worth stating
outright — `_copy_owned` keeps that copy in lockstep with the record on every
re-init, so there is no gap it could report — but it has to be stated, because
the alternative is a crash nobody would notice. c5 then needs an arm that
installs `codex --project-skills` and drives
`<project>/.agent-guild/hooks/session-nudge.py`, asserting exit 0 and no gap
line. Amend the non-goal to name three deployments and say which is waived.

### F3 — C-5, major: "byte-identical … after every one of those runs" is checked for one of the three runs

`tree_state` is captured at `probe-183.py:378` and compared at `:403-409`,
around the gap run only. The quiet arm (`:415-429`) and the Codex arm
(`:435-461`) take no snapshot.

Demonstrated: `v_writes_on_quiet` writes `.agent-guild/.checked` on every
session start where the versions match. **c5 PASSES.** The versions matching is
the common case — every session in an up-to-date project — so the variant is a
write to the project on essentially every session start, which is ruling 2's
own forbidden pattern (#98) on the path that will actually run.

This is the same shape r2 already repaired once in this clause. The repair added
the snapshot to the arm r2 was looking at; the text then grew to "every one of
those runs" while the other two arms stayed unsnapshotted.

**Fix.** Snapshot and compare around all three runs, or hoist the comparison
into a helper the arms share.

### F4 — C-3 and C-4, major: the plural conflict case is proven against fixtures holding exactly one differing file

c3 edits one payload file (`key_a`, `probe-183.py:275-277`). c4 edits one
(`key_a`, `:328-330`). Neither fixture ever puts two conflicts in one run, so
C-3's "the whole set of payload paths appearing in the output" is proven against
a one-element set, and C-4's "preserves and reports **each** file that differs"
is proven against one file.

Demonstrated: `v_report_first_conflict_only` truncates the warning to
`payload_conflicts[0]`. **c1-c4 and c6 all PASS.** Driving the spec's own
reproduction under that build — `spec.md:43-46`, which edits
`.agent-guild/scripts/ready-set.py` and `.agent-guild/CLAUDE.md` together and
whose reported output names both — gives:

```
WARNING: local Agent Guild payload differs; preserved without writes: .agent-guild/CLAUDE.md
```

The second preserved file is silently dropped. The user is told nothing about a
file the installer refused to write, which is a regression against the behavior
the issue reports as already working.

Keyed to C-3 primarily, since its text is the one that asserts a *set*; C-4
carries the same hole in "each file that differs".

**Fix.** Give c3 a second edited payload file and assert the named set equals
both. Give c4 a second differing file and assert both are reported and neither
is recorded.

### F5 — C-2, major: "the recorded version trails the plugin's" admits two readings, and the harness accepts both

The expression the two readings turn on is C-2's clause **"but the recorded
version trails the plugin's"**.

- Reading A, precondition: the in-place upgrade fires only when the record's
  `version` differs from the running package's.
- Reading B, description: any file clean against its recorded hash but stale
  against current source upgrades, whatever the record's `version` says.

Demonstrated: `v_version_gated` builds reading A. **c1-c4 and c6 all PASS**,
identically to reading B's run. c2 pins the stamp to `"0.0.1"`
(`probe-183.py:240`), so the gate is always true and the expression is never
exercised in either direction.

Materially different programs: under reading A a payload whose bytes changed
without a version bump — a re-cut release, a hotfix, any local dev build — never
upgrades in place and stays stale indefinitely, because the whole-record gate is
false. Under reading B it upgrades on the next init. Which one ships is
currently decided by whichever worker transcribes the clause.

**Fix.** State which. If it is a precondition, c2 needs a second arm with the
stamp left current and a payload file clean-against-record but
stale-against-source, asserting the settled behavior.

### F6 — C-4, major: what a run does with "file exists, no recorded entry, bytes match current source" is undetermined

The two readings turn on C-4's **"records no entry at all for it"** read against
the same clause's **"covering the files whose bytes match current source"** —
the first is a rule about the adoption run's output, the second is scoped to the
adoption run, and neither says which governs a later run that meets a file with
no entry.

- Reading A: a file matching current source is always stamped, entry or not,
  because a file identical to what ships is not an edit.
- Reading B: only a run that legitimately writes a file stamps it; a file with
  no entry is preserved and reported — which is exactly what C-4's own re-run
  sentence demands for `key_a`.

Demonstrated: `v_adopt_reading_b` builds reading B. **c1-c6 all PASS.**

Reachable and user-visible. Adoption refuses `key_a` and records no entry for it
— C-4 requires this. The user then reverts `key_a` to the shipped bytes. Under
reading A the next init stamps it and the warning stops. Under reading B the
file is reported as a local edit on every init forever, and there is no action
the user can take to clear it, since restoring the shipped bytes is exactly what
they already did.

**Fix.** Settle it in C-4's text and add the arm: adopt, revert the refused file
to source bytes, re-run, assert the settled outcome.

### F7 — C-1 and the preamble, minor: `docs/installing.md:137` is a line-number citation into a file this constitution requires rewriting

The line number is cited four times as the authority for excluding the Codex
repo-local `hooks/` from the payload scope: twice in the preamble (the record
contract block and the `WHY THE CHECKS LOOK LIKE THIS` block), once in C-1's
text, and once in `probe-183.py`'s docstring.

Line 137 today is the paragraph ending "A drifted payload file never upgrades in
place, because the installer keeps no record of what it shipped and cannot tell
a local edit from a version gap. That record is #183." C-7 requires
`docs/installing.md` to document the new semantics, and that paragraph and the
re-init table immediately above it (lines 132-135) are precisely what has to
change — C-7's own failing example names the table. Once C-7's work lands, `:137`
points somewhere else, and any checker following the citation reads the wrong
line while the clause it is verifying still reads as authoritative.

**Fix.** Cite by content rather than line number — "the re-init table's
`_copy_owned` row", or the sentence itself.

---

## Judged sound, recorded so the next round need not re-derive it

- **Job weight `standard` is correct.** C-9 extends suites that already exist
  (`the harness exists but needs extending`), and the nudge's unattended
  session-start firing is the upward signal `standard` already absorbs. `deep`'s
  trigger does not hold: the acceptance checks land in `test_build_plugin.py`
  and `test_hooks.py`, and the spec's "done" is checkable today.
  `probe-183.py` is audit scaffolding rather than the deliverable's harness, so
  it does not make this an instrument-building job.
- **The `**Ceiling overrun**:` reason is true, not merely present.** C-8 is a
  script clause and C-9 is a rubric; the split it describes is visible in the
  document, and 9 against standard's 8 is the arithmetic it claims.
- **No `**Lint exception**:` line, so nothing to audit there.**
- **Protected content resolves**: `manifest: none`, and no clause requires
  verbatim text.
- **Every prior-round repair verified by variant, not by reading**: C-5's silent
  direction (`v_keyed_on_existence` RED), C-5's Codex manifest lookup
  (`v_claude_manifest_only` RED), C-3's diagnostic set (`v_preserve_all` RED with
  the 37-path list), C-2's `unchanged` term (`v_count_examined` RED), C-1's
  `--project-skills` shape (third arm present and asserting no `hooks/` entries).

## Narrower than the text, noted rather than filed

Shared code makes these low-exposure, but they are the same shape as F3 and are
worth closing while C-5 is open anyway:

- C-1's `--project-skills` arm (`probe-183.py:192-214`) checks the record's file
  set and the absence of `hooks/` entries, but not the record's `version` and
  not its hashes. C-1's text asks for all three on all three shapes.
- C-1's Codex arm checks version, file set, and hashes but never
  `set(prov) == {"version", "files"}`; only the Claude arm's
  `_assert_record_covers` does.
- The non-goal enumerates C-2..C-4 as the waived Codex coverage. C-6 is
  Claude-only too and appears in neither the waiver nor the covered list.
  `_gitignore_update` has no host branch, so the exposure is nil, but the
  enumeration is incomplete and the preamble's blanket "the remaining probes
  drive the Claude package" is what actually covers it.

## Venues

- Reference and variant builds: `/tmp/conr3ref.Ya6GyQ` (retained; outside the
  repo, holds ~20 full repo copies).
- Codex-input comparison venue: `/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T/c5mech-e1n3yiei` (removed).
- Repo-local `--project-skills` git venue: `/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T/repolocal-ye96xfuj` (removed).
- Two-conflict reproduction venue: `/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T/tworepro-zj060zoy` (removed).
- C-6's own probe and `v_gitignore_record` each `git init` a fresh
  `tempfile.mkdtemp()` under the system tmpdir; those are the probe's own and
  were left as the probe leaves them.
