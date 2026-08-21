---
audit: CON-audit
round: 2
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: b879a6e8237fab9f5d3b0a99778cf82c7337400a4497bfe8b88baecc147d936b
verdict: FAIL
checked_at: 2026-08-20T23:53:39Z
---

# CON-audit r2 — payload provenance for the installer (#183)

## Scope of this round

- **Baseline sweep.** `python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .` → exit 0: `ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)`, both at the start of the round and at filing. Every declared baseline holds against the tree as I found it. The two skips are C-7 and C-9, both rubrics — so the sweep covered seven of nine clauses. `check-job-spec.py .agent-guild/state --audit-id CON-audit` also exits 0, so R17/R18 are satisfied by the weight line and the recorded overrun.
- **Executed.** C-1 through C-6 and C-8, each run three ways: against the untouched tree, against a reference implementation built from the clause texts, and against variants built to violate each clause's own property. Fifteen variant venues plus four hand-driven demonstration venues.
- **Read, not run.** C-7 and C-9 (`checker-judgment:` rubrics). Nothing was left `blocked`.
- **Reference implementation.** `.agent-guild/state/apparatus/CON-audit-r2/` holds `apply-reference.py` (the patch that produces the deliverable and every variant from the two shared sources the build generates from — `scripts/plugin-src/install-project.py` and `.agent-guild/hooks/session-nudge.py`), `run-variant.sh`, and `SOURCE.sha256` over `constitution.md`, `spec.md`, and `checks/probe-183.py`. Nothing was applied inside the repo: every venue is a whole-tree copy under its own `mktemp -d`, because `build-plugin.py --check` walks the tree and would read a reference installer left under `apparatus/` as a real artifact.
- **Independence caveat, stated plainly.** The dispatch directed me to r0's and r1's verdicts and to the four repairs r1 prompted, and I read r1's verdict in full before building. The reference was derived from the clause texts and the preamble's pinned contract; the *selection* of the regression variants (`claude-only`, `run-scoped`, `stamp-only`, `count-examined`, `abort-on-edit`, `restamp-preserved`, `adopt-wholesale`, `adopt-source-hash`, `nudge-writes`, `gitignore-record`, `readingA`, `stale-build`) was informed by r1, since verifying those repairs is what this round was dispatched for. The five findings below came out of building and out of the requirement sweep, not out of r1.
- **Comparand.** None matches. My `SOURCE.sha256` reads `constitution.md` at `b879a6e8…` and `checks/probe-183.py` at `11f23df0…`; `CON-audit-r1/` records `b0408bf8…` and `de5d9807…`, and `CON-audit-r0/` records `bf8f5970…` with no probe entry. Both documents an apparatus of this kind transcribes have moved, so the diff would be noise and this step is a no-op that files nothing on that axis. `spec.md` matches both predecessors at `934eba61…`, but nothing in either apparatus transcribes the spec alone. My build was whole — reference, both C-5 readings, and all fifteen variants built and run — before I touched either predecessor directory, and I never opened the contents of `CON-audit-r0/` or `CON-audit-r1/` at all. I did list their filenames and read their `SOURCE.sha256` at the start of the round, which is what the comparand rule requires and is the whole of my contact with them.
- **Venues acted on** (all outside the repo, each its own `mktemp -d`, each a whole-tree copy patched and rebuilt): `/private/tmp/con-r2-ref.9jdsCJ` (reference), `/private/tmp/con-r2-readingA.DfoWvA`, `/private/tmp/con-r2-claude-only.Ddbr24`, `/private/tmp/con-r2-run-scoped.IWneew`, `/private/tmp/con-r2-stamp-only.O3eyI8`, `/private/tmp/con-r2-count-examined.zi8xy8`, `/private/tmp/con-r2-abort-on-edit.J3huum`, `/private/tmp/con-r2-restamp-preserved.xPunMu`, `/private/tmp/con-r2-adopt-wholesale.LJW8VZ`, `/private/tmp/con-r2-adopt-source-hash.J0nBy2`, `/private/tmp/con-r2-nudge-writes.UxxoLc`, `/private/tmp/con-r2-nudge-always.a7WkoG`, `/private/tmp/con-r2-claude-manifest-nudge.p829XZ`, `/private/tmp/con-r2-gitignore-record.o6Z2qm`, `/private/tmp/con-r2-record-hooks.atxNsk`, `/private/tmp/con-r2-noisy-preserved.AECiQa`, `/private/tmp/con-r2-stale-build.kwvyQJ`; plus four demonstration projects installed into from those venues, `/private/tmp/con-r2-ideprobe.UUUpnv`, `/private/tmp/con-r2-noisyshow.iG5hTI`, `/private/tmp/con-r2-codexnudge.xfc7p3`, `/private/tmp/con-r2-codexsilent.CxZ6lH`, `/private/tmp/con-r2-alwaysshow.rEFEKh`, and the throwaway install targets each probe makes for itself under the system tmpdir.
- **Working tree.** `git status --porcelain` was empty at the start of the round and empty at filing. No `__pycache__` remains under `plugin/`, `plugins/`, or `.agent-guild/hooks/`; every venue run set `PYTHONDONTWRITEBYTECODE=1`, and C-8's own check deletes those trees before it starts.
- **Protected content.** `manifest: none`. Nothing to parse, nothing to check.
- **Lint exception.** None declared.
- **Ceiling overrun.** The recorded reason is true, not merely present, and I re-derived the underlying fact rather than taking r0's word: my reference implementation satisfies C-1 through C-6 and adds no case to either suite, and C-8's check exits 0 against it (`371 passed, 0 failed` / `50 passed, 0 failed` / `--check` OK). So regression coverage genuinely cannot ride C-8, the spec's eighth acceptance criterion still demands it, and a ninth clause carrying it as a rubric is the right call.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | The Codex repair holds — but the whole-payload sentence is unreachable on the one shipped install shape it now has to describe. **Untouched:** red — `AssertionError: provenance record missing`. **Reference:** green on the fresh install, the idempotent re-run, and the codex arm. **Variant `claude-only`** (record written only when `host == "claude"` — r1's finding, verbatim): now **red** at the codex arm, where in r1 it was green on all six probes and both suites. **Variant `run-scoped`** (record holds only the files this run copied): red — `entry set diverges from installed payload: missing=[38 paths]`. **Variant `record-hooks`** (the second reading: the Codex IDE bootstrap's nine repo-local hooks earn entries too): green on c1–c6 and both suites, i.e. the check accepts both readings. A `--project-skills` codex install lands 47 payload files under `.agent-guild/` and the reference records 38. | `/private/tmp/con-r2-claude-only.Ddbr24`; `/private/tmp/con-r2-run-scoped.IWneew`; `/private/tmp/con-r2-record-hooks.atxNsk`; `/private/tmp/con-r2-ideprobe.UUUpnv` |
| C-2 | minor | The `updated` term discriminates; the `unchanged` term is read by nothing. **Untouched:** red. **Reference:** green — `payload=1 updated/37 unchanged/0 preserved`. **Variant `stamp-only`** (advance the stamp, leave the stale bytes — the failing example): red — `stale-but-clean file was not upgraded`. **Variant `count-examined`** (every stale-stamped file counted updated): red — `summary counts files that did not move: 'payload=38 updated/0 unchanged/0 preserved'`. **Variant `noisy-preserved`** (a file matching source under a stale record counted `preserved`, not `unchanged`): green on c1–c6 and both suites, reporting `payload=1 updated/0 unchanged/37 preserved`. | `probe-183.py:209-211`; `/private/tmp/con-r2-stamp-only.O3eyI8`; `/private/tmp/con-r2-count-examined.zi8xy8`; `/private/tmp/con-r2-noisy-preserved.AECiQa` |
| C-3 | major | Every property but one discriminates. **Untouched:** red. **Reference:** green. **Variant `abort-on-edit`** (one edit withholds the release, pre-#211): red — `mixed run failed: 'install.py: local Agent Guild payload differs…'`. **Variant `restamp-preserved`** (a preserved file's entry refreshed from its on-disk bytes): red — `a preserved file's recorded hash was refreshed from its on-disk bytes`. **Variant `noisy-preserved`**: green on c1–c6 and both suites while naming 37 untouched files in the `preserved without writes` warning — the "only payload path the diagnostic names" sentence is enforced by two negative substring assertions on two specific paths. | `probe-183.py:242-244`; `/private/tmp/con-r2-abort-on-edit.J3huum`; `/private/tmp/con-r2-restamp-preserved.xPunMu`; `/private/tmp/con-r2-noisyshow.iG5hTI` |
| C-4 | pass | The fixture is real and both wrong-adoption readings are caught. **Untouched:** red — `FileNotFoundError` removing a record that was never written. **Reference:** green. **Variant `adopt-wholesale`** (stamp the edit's own bytes): red — `adoption recorded an entry for a file it refused`. **Variant `adopt-source-hash`** (stamp the current source hash): red on the same assertion. **Variant `run-scoped`**: red — `KeyError: '.agent-guild/scripts/ready-set.py'`. | `probe-183.py:284-296`; `/private/tmp/con-r2-adopt-wholesale.LJW8VZ`; `/private/tmp/con-r2-adopt-source-hash.J0nBy2` |
| C-5 | major | Both r1 findings are repaired and two new ones sit behind them. **Untouched:** red. **Reference:** green. **Variant `nudge-writes`** (breadcrumb file on every session start — r1's finding, verbatim): now **red** — `the nudge wrote to the project: added=['.agent-guild/nudged.txt']`. **Reading A vs. reading B** (version gap evaluated before vs. after the partial-init report — r1's fork): both green on all six probes, so the fixture repair closed the fork and the axis is genuinely free. **Variant `nudge-always`** (fires whenever a record exists, gap or no gap): green on c1–c6 and both suites, printing `installed by Agent Guild 0.7.1; the running plugin is 0.7.1. Run /agent-guild:init to bring it up to date—run it now?` on an up-to-date project. **Variant `claude-manifest-nudge`** (nudge knows only `.claude-plugin/plugin.json`): green everywhere, and silent forever on the Codex package. | `/private/tmp/con-r2-nudge-writes.UxxoLc`; `/private/tmp/con-r2-readingA.DfoWvA`; `/private/tmp/con-r2-nudge-always.a7WkoG` and `/private/tmp/con-r2-alwaysshow.rEFEKh`; `/private/tmp/con-r2-claude-manifest-nudge.p829XZ` and `/private/tmp/con-r2-codexsilent.CxZ6lH` |
| C-6 | pass | **Untouched:** red — `AssertionError: provenance record missing`. **Reference:** green. **Variant `gitignore-record`** (installer appends `provenance.json` to the gitignore block it writes — the failing example verbatim): red — `provenance.json is gitignored; a tracked record must be addable`. Both halves of the text are asserted, including `state/` staying ignored. | `probe-183.py:357-369`; `/private/tmp/con-r2-gitignore-record.o6Z2qm` |
| C-7 | pass | Rubric, judged by reading. Its target exists, its four behaviors each map onto a behavior clause (C-6, C-2, C-3, C-4) with no contradiction, and its failing example is live on the current tree: `docs/installing.md:135` still says the payload class is one where init "lands each missing file and preserves each differing one," and `:137` still says "A drifted payload file never upgrades in place." C-2 makes both false for files clean against their recorded hashes. Applicable by a checker who cannot edit: everything it asks is a read of one file against shipped behavior. | `docs/installing.md:130-137` |
| C-8 | pass | Single falsifiable property, and it discriminates. **Untouched:** green, exit 0 (371 + 50 passed, `--check` OK). **Reference:** green, same counts. **Variant `stale-build`** (`install-project.py` edited, mirrors not regenerated — the failing example): red, exit 1 — `FAIL the explicit Claude build reproduces the published plugin exactly rc=0 diffs=['content differs: hooks/session-nudge.py', 'content differs: project-template/install.py']`. The `rm -rf` in its check is scoped to three gitignored `__pycache__` directories and left the working tree clean. | `/private/tmp/con-r2-stale-build.kwvyQJ/c8.log:414`; `.agent-guild/state/log/build-20260820T183756.log` |
| C-9 | pass | Rubric, judged by reading, and applicable by a checker who may not edit the tree — the dispatch's question, answered directly. It names the two files to search, names the artifact to read (assertions, not log lines), names two disqualifiers (a case asserting only on summary text; a case that would pass with the feature reverted), and says in its own text that reverting is reasoning rather than an edit. Establishing "the tree as this job found it" is a `git log`/`git show` read, which is also not an edit, and the constitution's own baseline declarations pin it independently ("C-1 through C-6 fail today"). Falsifiable, and I falsified it while building: my reference satisfies C-1 through C-6 and C-8 and adds no suite case at all, so C-9 fails against it — which is exactly the hole C-8 cannot see. | `scripts/test_build_plugin.py:1440-1552`; `/private/tmp/con-r2-ref.9jdsCJ` |

**Weight.** `standard` holds, and the recorded overrun is honest (see the scope note above). The weight line's own justification is the weakest part of it: `probe-183.py` is 384 purpose-built lines, so "rather than building a new instrument" is generous. It still lands on the right side of the discriminator — every probe drives an entry point that already exists (`install.py`, `session-nudge.py`) and reads what it did, and none of them measures a property nobody could check today. The unattended-blast-radius signal is present (the nudge fires on every session start in every project a user-scope plugin install touches) and read-only, which argues for standard rather than deep. Not a finding; recorded because the phrase is doing more work than it can carry.

**Axes the contract leaves free, accepted both ways and not filed.** The precedence between the version-gap nudge and the partial-init report (readings A and B, both green — r1's fork, closed by the fixture repair). Where the nudge reads the running version from (a manifest beside the hook, or a constant baked at build time). Whether a net-new file counts in the `updated` term. Version comparison by string equality versus semver ordering (no probe stamps a version *ahead* of current). The record's JSON key ordering and indentation.

**Two bounded observations, not findings.** C-1's codex arm asserts the version and the entry set but not `set(prov) == {"version", "files"}`, which the claude arm does assert; a shared writer makes the gap unreachable in practice. C-4's "covering the files whose bytes match current source" is spot-checked at one key rather than asserted as a set; I could not construct a plausible implementation that violates it while passing everything else, so it stays an observation. Separately: when the built trees are stale, c1–c6 all go red with assertions that read as "the feature is missing" rather than "the build is stale" (see the `stale-build` row) — the preamble names this and C-8 catches it, but it is worth knowing when a rework diagnosis gets written.

## Diagnosis

### C-5 (major) — the nudge is checked only in the direction where it fires

C-5's text scopes its assertion to "a fully installed project whose record's `version` trails the running plugin's." Nothing in the constitution says what the nudge does when the version does *not* trail, and `c5` never builds that project, so the silent direction is asserted by nothing. I built the violation — the gap message printed whenever a record exists, gap or no gap, one expression different (`if stamped and running and stamped != running:` → `if stamped and running:`):

```
c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c5 GREEN  c6 GREEN
test_hooks.py         371 passed, 0 failed
test_build_plugin.py   50 passed, 0 failed
build-plugin.py --check  OK
```

And on a project the installer just finished installing at the current version:

```
agent-guild: this project's payload was installed by Agent Guild 0.7.1; the
running plugin is 0.7.1. Run /agent-guild:init to bring it up to date—run it now?
```

Every session start, every guild project, forever, telling the user to upgrade to the version they are already on. The reference prints nothing on the same project. This is the pattern `session-nudge.py`'s own docstring rules out in as many words — "Nagging unrelated repos on every session start would make the plugin something people disable, not adopt" — and it ships with every clause green, because C-5 states a conditional and checks only its consequent. It is the same shape as r1's C-5(b) and r0's C-8 half: a requirement the job actually has, that no check reaches. The third instance now, and the second one inside C-5.

Neither C-9 nor C-8 covers the gap. C-9's three paths are all installer behaviors with no nudge arm, and its own "assert on the installed bytes or the record's contents, not on a log line" rule would disqualify a nudge case even if someone wrote one, since a nudge's only artifact *is* its output. So no clause in the constitution can require a regression case for the nudge at all.

Repair, one clause and four lines of probe:

- Add a sentence to C-5: in a fully installed project whose record's `version` equals the running plugin's, the nudge emits nothing about a version gap.
- Give `c5` a second arm: install fresh, leave the record alone, run the nudge, assert its stdout carries neither version string nor `/agent-guild:init`. The venue is already built by the first arm.

### C-5 (major) — the third non-goal's justification is false for the nudge, and it is r1's C-1 finding one file over

The third non-goal reads: "Codex-host coverage of the upgrade, refusal, adoption, and nudge paths (C-2 through C-5). C-1 pins that a Codex install writes the record at all, which is the host-specific branch; the rest is one shared engine below that point."

For C-2, C-3, and C-4 that is true — once the record exists, the payload sync is host-neutral. For C-5 it is false. The nudge has its own host-specific branch that C-1's codex arm never touches: reading the running plugin's version out of the package the hook file ships inside, which is `.claude-plugin/plugin.json` in one package and `.codex-plugin/plugin.json` in the other. That is the same manifest split r0 got wrong in the installer and r1 caught with the `claude-only` variant. Nothing catches it here.

I built it — the nudge's manifest lookup narrowed to the Claude package, changing nothing else:

```
c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c5 GREEN  c6 GREEN
test_hooks.py 371 passed, 0 failed   test_build_plugin.py 50 passed, 0 failed   --check OK
```

Against a Codex project installed from the Codex package and stamped down to `0.0.1`, the reference prints

```
agent-guild: this project's payload was installed by Agent Guild 0.0.1; the running plugin is 0.7.1. Run $init to bring it up to date—run it now?
```

and the variant prints nothing, exit 0. Every Codex user's stale project stays silent forever, which is the half of the issue the nudge exists to close, and the constitution certifies it green.

The non-goal is a legitimate scope decision — declining to probe the Codex nudge is defensible. Its stated reason is not, and that is what has to change, because "one shared engine below that point" is exactly the sentence r1 struck from the preamble for asserting coverage that does not exist.

Repair, either shape:

- Extend C-5 to both hosts, the way C-1 was extended, and give `c5` a codex arm that drives `plugins/agent-guild/hooks/session-nudge.py` against a codex-installed project. It costs about ten lines; the reference proves the arm runs.
- Or keep the non-goal and rewrite its reason to say what is actually true: the nudge's running-version lookup is host-specific and unchecked on Codex, accepted as a known gap.

### C-3 (major) — "the only payload path the diagnostic names" is enforced by two spot checks

C-3 requires that in a mixed run "the edited file keeps its bytes and is **the only payload path the diagnostic names**." `c3` enforces that with `assert key_b not in r.stdout` and `assert key_c not in r.stdout` — two specific paths, chosen because they are the two the fixture manipulates. Any other payload path the diagnostic names goes unseen.

I built an implementation that names 37 of them. It counts a file that already matches source as `preserved` rather than `unchanged` whenever the record's version is stale — one plausible way to write "this run didn't touch that file" — and on a routine upgrade run it prints:

```
WARNING: local Agent Guild payload differs; preserved without writes:
.agent-guild/CLAUDE.md, .agent-guild/schemas/vendor-call.schema.json, …
[37 paths] …, .agent-guild/templates/verdict.md
OK: Agent Guild project install (host=claude; payload=1 updated/0 unchanged/37 preserved; …)
```

```
c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c5 GREEN  c6 GREEN
test_hooks.py 371 passed, 0 failed   test_build_plugin.py 50 passed, 0 failed   --check OK
```

That warning is the defect the issue was filed about, reproduced verbatim: "The message is accurate about what it did and wrong about why," naming files the user never touched. An implementation that ships it passes every clause in this constitution. The existing suites do not catch it either, because they never build a project whose record is stale — that state only exists once this job ships.

Repair: assert the set, not two members. `c3` already knows the edited path, so `assert [p for p in payload_files(tmp) if p in r.stdout] == [key_a]` — or, more directly, parse the `preserved without writes:` list and assert it equals `[key_a]`, which is the shape `scripts/test_build_plugin.py:1508-1516` already uses for the pre-provenance case.

### C-2 (minor) — "is counted `unchanged`" is checked by nothing

Same variant, second sentence. C-2 says a stale stamp over a file already matching source "moves nothing and is counted `unchanged`, so the count reports files moved rather than files examined." `c2` reads only the `updated` term:

```python
m = re.search(r"payload=(\d+) updated", r.stdout)
assert int(m.group(1)) == 1
```

The variant reports `payload=1 updated/0 unchanged/37 preserved` and passes. The clause's stated purpose survives — `updated` really does report files moved — so this is minor rather than major, and the fix is one line in the same place C-3's fix lands: match the whole `payload=(\d+) updated/(\d+) unchanged/(\d+) preserved` triple and assert `preserved == 0` and `unchanged == len(payload_files) - 1`. The existing suite at `scripts/test_build_plugin.py:1525-1541` already parses all three terms, so the shape is in the repo.

### C-1 (major) — the whole-payload sentence has no reachable check on the `--project-skills` Codex install, and two readings both pass

C-1 now says: "On a project where the install preserved nothing, the record carries one entry per installed payload file (every file under `.agent-guild/` except `state/` and the record itself), no entry for any other path."

There are three shipped install shapes, not two. `c1` exercises a Claude install and a bare Codex install. The third is the repo-local Codex IDE bootstrap, `install.py codex PROJECT --project-skills`, which lands the guild's hook scripts under `.agent-guild/hooks/`. Against my reference:

```
payload on disk under .agent-guild/, excluding state/ and the record: 47
entries in the record:                                                38
on disk but not recorded: .agent-guild/hooks/_lib.py, …/codex-hook-adapter.py,
  …/dispatch-guard.py, …/orchestrator-write-guard.py, …/session-nudge.py,
  …/stop-gate.py, …/subagent-return.py, …/test_codex_adapter.py, …/test_hooks.py
```

Nine payload files under `.agent-guild/`, not under `state/`, not the record, with no entry — and `c1` is green, because it never runs that shape.

This is not just a coverage hole; the clause does not determine which program to write, and I built both. `install()` splits those hooks out of `payload_files` and copies them with `_copy_owned`, and the repo's own documentation calls that split out explicitly (`docs/installing.md:137`: "they sit inside `.agent-guild/` like the payload does. Even so, `install()` splits them out of the payload before the drift check runs"). So "payload file" already means something narrower in this codebase than C-1's parenthetical says. The variant that takes C-1's text at its word and records all 47:

```
c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c5 GREEN  c6 GREEN
test_hooks.py 371 passed, 0 failed   test_build_plugin.py 50 passed, 0 failed   --check OK
```

Both readings green, the records differ by nine entries, and the expression they turn on is C-1's parenthetical "every file under `.agent-guild/` except `state/` and the record itself" — which either means what it says, or means the payload set `install()` computes. The clause has to pick, since it is the sentence a checker would read when ruling on a dispute.

Repair, one sentence plus an optional probe arm:

- Say which set governs. The defensible answer is the narrow one — those hooks are `_copy_owned`, overwritten on every re-init, so provenance has nothing to decide about them — so scope the parenthetical to "every file the install copies as payload (`.agent-guild/` except `state/`, the record, and the Codex repo-local hooks, which `_copy_owned` overwrites on every run)."
- If the answer is the broad one instead, add a `--project-skills` arm to `c1`. Either way the preamble's payload-scope sentence, "every file the install wrote under `.agent-guild/`," has to move with it, since it is the wording the clause cites.

### What this round confirms about r1's repairs

All four landed, and I verified each by running rather than by reading.

- **C-1, the Codex hole.** The `claude-only` variant that was green on everything in r1 is now red at `c1`'s first arm. The preamble's false coverage claim is gone and the non-goal is rescoped — though its replacement reason carries the same defect one file over, which is the second C-5 finding above.
- **C-5, the precedence fork.** Building the fixture from a real install closed it. Readings A and B — the version gap evaluated before or after the partial-init report — are now both green on all six probes, so the axis is free rather than forced.
- **C-5, "writes nothing to the project."** The breadcrumb nudge that was green in r1 is now red: `the nudge wrote to the project: added=['.agent-guild/nudged.txt']`.
- **C-1, the entry-set contradiction.** Scoping the whole-payload claim to a preserved-nothing project and deferring preserved entries to C-3 and C-4 removes the contradiction. C-3's carried-forward hash and C-4's no-entry rule now read consistently with C-1.

The five findings above are new ground. Three of them — C-5's silent direction, C-3's diagnostic set, and C-2's `unchanged` term — are the same "requirement no check reaches" shape the dispatch asked me to sweep for, which has now appeared in five clauses across three rounds. The remaining two are a false justification and an undetermined contract. All five are clause revisions plus small edits to `probe-183.py`; none of them needs a different implementation.
