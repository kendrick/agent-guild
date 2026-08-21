---
audit: CON-audit
round: 1
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: b0408bf8c5fc7e3b9bcf81a0f92f55e3a97e83ddbceccca7956d72d067ab5385
verdict: FAIL
checked_at: 2026-08-20T23:28:17Z
---

# CON-audit r1 — payload provenance for the installer (#183)

## Scope of this round

- **Baseline sweep.** `python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .` → exit 0: `ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)`. Every declared baseline holds against the tree as I found it. The two skips are C-7 and C-9, both rubrics. `check-job-spec.py .agent-guild/state --audit-id CON-audit` also exits 0, so R17/R18 are satisfied by the weight line and the recorded overrun.
- **Executed.** C-1 through C-6 and C-8, each run three ways: against the untouched tree, against a reference implementation built from the clause texts, and against variants built to violate each clause's own property. Twelve variant venues in all.
- **Read, not run.** C-7 and C-9 (`checker-judgment:` rubrics). Nothing was left `blocked`.
- **Reference implementation.** `.agent-guild/state/apparatus/CON-audit-r1/` holds `apply-reference.py` (the patch that produces the deliverable and its variants from the two shared sources the build generates from), `run-variant.sh`, and `SOURCE.sha256` over `constitution.md`, `spec.md`, and `checks/probe-183.py`. The implementation itself was applied into venues outside the repo, because the project's own build (`build-plugin.py --check`) walks the tree and would read a reference installer left under `apparatus/` as a real artifact.
- **Independence caveat, stated plainly.** The dispatch directed me to the r0 verdict and to the seven repairs it prompted, and I read both before building. The reference implementation was derived from the clause texts and the preamble's pinned contract; the *selection* of variants (v1, v3, v4, v5, v7, v9, and the `updated`-term fork) was informed by r0's verdict, since verifying those repairs is what this round was dispatched for. The three findings below that r0 did not raise — C-5's precedence fork, C-5's unchecked "writes nothing", and the Codex hole — came out of building, not out of reading r0.
- **Comparand.** `.agent-guild/state/apparatus/CON-audit-r0/` exists and records `constitution.md` at `bf8f5970…`; mine reads `b0408bf8…`. The document an artifact of this kind transcribes has moved, so the diff would be noise and this step is a no-op that files nothing. `spec.md` matches at `934eba61…`, but nothing in either apparatus transcribes the spec alone. My build was whole — reference, both nudge readings, and all twelve variants built and run — before I listed that directory, and I have not opened the contents of `CON-audit-r0/reference/` at all.
- **Venues acted on** (all outside the repo, each its own `mktemp -d`, each a whole-tree copy patched and rebuilt):
  `/private/tmp/con-r1-ref.lQ9pQ0` (reference, nudge reading A), `/private/tmp/con-r1-readB.icgy75` (nudge reading B), `/private/tmp/con-r1-v1.BMlYK4`, `/private/tmp/con-r1-v2.T9iKv3`, `/private/tmp/con-r1-v3.SHwKNv`, `/private/tmp/con-r1-v4.9RCf5Y`, `/private/tmp/con-r1-v5.WJqlKn`, `/private/tmp/con-r1-v7.VtQYvl`, `/private/tmp/con-r1-v8.rqJi82`, `/private/tmp/con-r1-v9.PgZWI4`, `/private/tmp/con-r1-vupd.XJKJeG`, `/private/tmp/con-r1-codexskip.LjqiRF`, `/private/tmp/con-r1-v10write.l0tOh4`, plus the throwaway install targets each probe makes for itself under the system tmpdir.
- **Working tree.** `git status --porcelain` was empty at the start of the round and empty at filing. One gitignored artifact moved: `.agent-guild/hooks/__pycache__` existed when I started and does not now, because C-8's own check begins by deleting it. No `__pycache__` remains under `plugin/`, `plugins/`, or `.agent-guild/hooks/`.
- **Protected content.** `manifest: none`. Nothing to parse, nothing to check.
- **Lint exception.** None declared.
- **Ceiling overrun.** The recorded reason is true, not merely present. r0 did find C-8's second half unfalsifiable, and I reproduced the underlying fact this round: C-8's check is green against a complete reference implementation of #183 that adds no suite cases at all. The spec's eighth acceptance criterion demands that coverage, so the requirement cannot simply be dropped, and #141's finding about greping test source rules out a script check. A ninth clause carrying it as a rubric is the right call, and the overrun line says so honestly.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | Discriminates its own failing example now — r0's repair holds — but the record is scoped to one host, and the preamble's reason for that is false. **Untouched:** red — `AssertionError: provenance record missing`. **Reference:** green. **Variant v1** (record holds only the files this run copied): now **red** on the idempotent second install — `entry set diverges from installed payload: missing=[38 paths]`. **Codex variant** (record written only when `host == "claude"`): green on `c1`–`c6` and green on all of C-8. Separately, C-1's unscoped entry-set sentence contradicts C-3 and C-4. | `/private/tmp/con-r1-v1.BMlYK4`; `/private/tmp/con-r1-codexskip.LjqiRF` |
| C-2 | pass | Fork settled and the check can now see it. **Untouched:** red. **Reference:** green — `payload=1 updated/37 unchanged/0 preserved`. **Variant v2** (advance the stamp, leave the stale bytes — the failing example): red — `AssertionError: stale-but-clean file was not upgraded`. **Variant vupd** (r0's reading A, every stale-stamped file counted updated): red — `summary counts files that did not move: 'payload=38 updated/0 unchanged/0 preserved'`. | `probe-183.py:176-178`; `/private/tmp/con-r1-v2.T9iKv3`; `/private/tmp/con-r1-vupd.XJKJeG` |
| C-3 | pass | r0's blocker is closed and the invariant is now falsified by an assertion that names it. **Untouched:** red. **Reference:** green. **Variant v3** (one edit withholds the release, pre-#211): red — `mixed run failed: 'install.py: local Agent Guild payload differs…'`. **Variant v9** (a preserved file's entry restamped from its bytes on disk): now **red** — `AssertionError: a preserved file's recorded hash was refreshed from its on-disk bytes`, where in r0 the same variant was green on every clause. | `probe-183.py:221-231`; `/private/tmp/con-r1-v9.PgZWI4`; `/private/tmp/con-r1-v3.SHwKNv` |
| C-4 | pass | The open axis is pinned and both readings of it are now caught. **Untouched:** red. **Reference:** green. **Variant v4** (adoption stamps the edit's own bytes): red — `adoption recorded an entry for a file it refused`. **Variant v7** (adoption stamps the current source hash — the axis r0 found free): now red on the same assertion. | `probe-183.py:258-260`; `/private/tmp/con-r1-v4.9RCf5Y`; `/private/tmp/con-r1-v7.VtQYvl` |
| C-5 | major | r0's blocker is fixed — `CLAUDE_PROJECT_DIR` is set and the clause names `_lib.project_dir()`, and the reference goes green. Two defects remain. **(a) Fork:** the check's fixture is a project that is stale *and* partially initialized, forcing a precedence the clause never states. **Reference reading A** (version gap checked before the partial-init report): green. **Reading B** (checked after): red — `stamped version missing from nudge output: 'agent-guild: this project looks partially initialized (missing state/tasks, …, CLAUDE.md)—run /agent-guild:init to finish the install.'` **(b) Unchecked half:** "It writes nothing to the project" is falsified by nothing. A nudge that appends `.agent-guild/nudged.txt` to the project on every session start is **green** on `c5`. | `probe-183.py:271-299`; `/private/tmp/con-r1-readB.icgy75`; `/private/tmp/con-r1-v10write.l0tOh4` |
| C-6 | pass | **Untouched:** red — `AssertionError: provenance record missing`. **Reference:** green. **Variant v5** (installer appends `provenance.json` to the gitignore block it writes — the failing example verbatim): red — `provenance.json is gitignored; a tracked record must be addable`. | `probe-183.py:302-314`; `/private/tmp/con-r1-v5.WJqlKn` |
| C-7 | pass | Rubric, judged by reading. Its target exists, its four behaviors each map onto a behavior clause (C-6, C-2, C-3, C-4) with no contradiction, and its failing example is live: `docs/installing.md:135` still says the payload class is one where "init lands each missing file and preserves each differing one," and `:137` still says "A drifted payload file never upgrades in place." C-2 makes both false for files clean against their recorded hashes. | `docs/installing.md:130-137` |
| C-8 | pass | Now a single-property clause, and it discriminates. **Untouched:** green, exit 0 (371 + 50 passed, `--check` OK). **Reference:** green, same counts. **Variant v8** (`scripts/plugin-src/install-project.py` edited, mirrors not regenerated — the failing example): red, exit 1 — `FAIL the explicit Claude build reproduces the published plugin exactly  rc=0 diffs=['content differs: project-template/install.py']`. r0's unfalsifiable second half is gone from this clause. | `/private/tmp/con-r1-v8.rqJi82`; `.agent-guild/state/log/build-20260820T182240.log` |
| C-9 | pass | Rubric, judged by reading. Falsifiable, and I falsified it while building: my reference implementation satisfies C-1 through C-6 and C-8 and adds no suite cases at all, so C-9 fails against it — which is exactly the hole C-8 could not see. The rubric is applicable as written: `scripts/test_build_plugin.py:1441-1542` shows the shape a checker would be reading, and its "would this go red against pre-job behavior" question is answerable by reading assertions rather than by editing the tree. | `scripts/test_build_plugin.py:1441-1542`; `/private/tmp/con-r1-ref.lQ9pQ0` |

**Weight.** `standard` holds. Its stated signals check out — the acceptance checks route through existing suites plus probes that drive the packaged installer, and the session nudge, while genuinely unattended (it fires on every session start in every project a user-scope plugin install touches), is read-only, which is the "unattended blast radius" signal that argues for standard rather than deep. The overrun is a clause-count fact about C-8's split, not evidence the weight was wrong.

**Axes the contract leaves free, all accepted both ways and none worth a finding.** Version comparison by string equality versus semver ordering (no probe stamps a version *ahead* of current, so both are green). Whether a net-new file counts in the `updated` term (nothing asserts it). The record's JSON key ordering and indentation. Which manifest the installer reads when both are present (they never are). Recorded here rather than guessed at, because two of them are one clause sentence away from mattering.

**One observation, not a finding.** C-1 through C-6 read the built `plugin/` tree while workers edit `scripts/plugin-src/`, so a worker who forgets to rebuild gets six red probes whose assertions read as "the feature is missing" rather than "the build is stale". The preamble names this and C-8's `--check` catches it, so the cost is bounded, but the ordering is worth knowing when a rework diagnosis is written.

## Diagnosis

### C-5 (major, a) — the check settles a precedence the clause never states

C-5's text asserts a property of "a project whose record's `version` trails the running plugin's." It says nothing about a project that is *also* missing its entire state tree and its root `CLAUDE.md` import line — which is the only kind of project its check ever builds. `c5` writes just two files into its venue, `.agent-guild/CLAUDE.md` and `provenance.json`, so `_missing_pieces()` returns five state directories plus `CLAUDE.md`, and the existing partial-init nudge fires on exactly this input. That is what the untouched-tree baseline records:

```
AssertionError: stamped version missing from nudge output:
'agent-guild: this project looks partially initialized (missing state/tasks,
 state/verdicts, state/disputes, state/notes, state/log, CLAUDE.md)—run
 /agent-guild:init to finish the install.\n'
```

So a conforming implementation has to decide which of two messages a stale-*and*-incomplete project sees, and the clause does not decide it. I built both readings, one expression apart — whether `_version_gap_nudge(root, init_invocation)` is evaluated before or after `_missing_pieces()`'s early return in `session-nudge.py`'s `main()`:

```
reading A  (gap checked first):  c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c5 GREEN  c6 GREEN
reading B  (gap checked after):  c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c5 RED    c6 GREEN
```

Reading B is not a strawman. Both messages end in "run init," so reporting the more urgent problem first — the install is incomplete — is the reading a careful implementer is likely to reach, and it satisfies every sentence C-5 writes about the state the spec actually contemplates ("A session in a project stamped older than the running plugin surfaces it once"). The diagnosis reading B earns points at the version-reading code, which is correct in both readings, so the retry it costs is spent looking in the wrong place.

Repair, and the cheaper option is the first:

- Build `c5`'s fixture by running the installer and then editing the record's `version` down, so the venue is a complete install with a stale stamp — the state a real project is actually in. That removes the fork from the check without needing the clause to arbitrate anything.
- Or add one sentence to C-5 saying the version-gap nudge takes precedence over the partial-init report, and keep the fixture as it is.

### C-5 (major, b) — "It writes nothing to the project" is checked by nothing

C-5's last sentence carries ruling 2, the binding user ruling that the nudge prompts and never writes, restated again in the non-goals ("The nudge running init itself, or any write to a project at session start — it prompts and stops"). `c5` asserts an exit code and four output substrings. It never looks at the venue afterward.

I built the violation: a nudge that emits exactly the required line and also appends `.agent-guild/nudged.txt` to the project on every session start.

```
c5: GREEN
```

This is the same defect r0 found in C-8's second half, relocated. A clause half that no check can see is a clause half the job will not get, and this one is the ruling the user made at intake.

Repair: snapshot the venue before the nudge runs — relative paths plus content hashes — and assert the snapshot is identical afterward. Four lines in `c5`, and it makes the sentence falsifiable for the first time.

### C-1 (major) — a Codex install can skip provenance entirely and the whole job stays green

C-1's text is scoped to "A `claude` install." Nothing else in the constitution requires a record on the Codex host. The preamble justifies the gap: "Probes exercise the claude host; the engine is shared, and Codex-host coverage rides the suites C-8 runs," and the third non-goal repeats it.

That note is false for the behavior this job adds. I took the reference implementation and wrapped its record write in `if host == "claude":`, changing nothing else:

```
c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c5 GREEN  c6 GREEN
test_hooks.py     371 passed, 0 failed
test_build_plugin.py  50 passed, 0 failed
build-plugin.py --check  OK
```

Everything green. The suites C-8 runs do exercise Codex installs — that is why r0's manifest-path error was caught by them — but they carry no provenance assertions at all, so they cannot notice a Codex install that never writes the record. Neither can C-9's rubric, whose three paths are installer behaviors with no host arm.

What ships if that implementation ships: every Codex project stays pre-provenance forever. Its re-inits never upgrade in place, its session nudge never fires because there is no stamp to read, and the defect the issue was filed for survives untouched for one of the two hosts the engine serves — with every verdict in the job green, which is the failure mode a decomposition audit cannot recover either.

Repair, either shape:

- Extend C-1's text to both hosts and give `c1` a `codex` arm asserting the record exists and covers what that host installed. The preamble already names both manifests, so the contract is ready for it.
- Or add the Codex path to C-9's rubric as a fourth case, and rewrite the preamble note and the third non-goal to say what C-8's suites actually cover today rather than what the shared engine makes plausible.

Either way the preamble sentence and the non-goal have to change, because as written they assert coverage that does not exist.

### C-1 (minor) — the entry-set sentence contradicts C-3 and C-4

C-1's first sentence is unscoped: "A `claude` install writes `.agent-guild/provenance.json` … one entry per installed payload file (every file under `.agent-guild/` except `state/` and the record itself), no entry for any other path, each hash matching the bytes on disk."

Two clauses contradict it directly, and each contradiction is reachable:

- After C-4's adoption run, `.agent-guild/CLAUDE.md` is a file under `.agent-guild/`, not under `state/`, not the record. C-1 requires an entry for it. C-4 requires that adoption "records no entry at all for it." No implementation satisfies both.
- After C-3's mixed run, the preserved file's entry holds the hash "carried forward untouched — never refreshed from the bytes on disk," which by construction does not match the bytes on disk. C-1 requires that it does.

C-1's own closing sentence half-resolves this by scoping the *coverage* claim to a fresh install and an idempotent re-run, and `c1` only ever exercises those two, so no worker is failed by it and no check disagrees. It is minor for that reason and not less: a checker ruling on a dispute reads clause text, not probe source, and this text says the opposite of what C-3 and C-4 say.

Repair: one clause. Scope C-1's parenthetical to the files a run actually wrote or already owned — "every file under `.agent-guild/` except `state/`, the record itself, and any file this run preserved rather than wrote" — and say the hash is the bytes as shipped rather than the bytes on disk, which is the preamble's own wording.

### What this round confirms about r0's repairs

All seven landed and I verified each by running rather than by reading. C-5's `CLAUDE_PROJECT_DIR` fix makes the clause satisfiable (the reference goes green where r0's could not). C-3's carried-forward-hash requirement catches variant v9, which passed everything in r0. C-1's idempotent second install catches variant v1 by assertion rather than by an incidental `KeyError`. C-2's settled `updated` term now reads `payload=1` and rejects `payload=38`. C-4's no-entry rule catches both v4 and v7. C-8 is a single falsifiable property. The host-aware version source is correct — the reference reads `.claude-plugin/plugin.json` and the Codex package's own manifest without the failure r0 reproduced.

The three findings above are new ground rather than regressions, which is what the round was for.
