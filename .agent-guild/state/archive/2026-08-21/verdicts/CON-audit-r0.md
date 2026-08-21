---
audit: CON-audit
round: 0
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
artifact_sha256: bf8f59708ecb0bd2c48e0e50d28778b293f9f705f3c154e5a5aa5fdbbd502d24
verdict: FAIL
checked_at: 2026-08-20T18:10:00Z
---

# CON-audit r0 — payload provenance for the installer (#183)

## Scope of this round

- **Baseline sweep.** `python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .` → exit 0: `ran 7 (6 red, 1 green), skipped 1 (1 judgment, 0 no-baseline)`. Every declared baseline holds against the tree as I found it. The one skip is C-7, a rubric.
- **Executed.** C-1 through C-6 and C-8, each run three ways: against the untouched tree, against a reference implementation built only from the clause texts, and against variants built to violate each clause's own failing example.
- **Read, not run.** C-7 (`checker-judgment:` rubric).
- **Reference implementation.** `.agent-guild/state/apparatus/CON-audit-r0/reference/` (`apply-reference.py`, `make-variant.py`, base snapshots, `SOURCE.sha256` over `constitution.md` and `spec.md`). Built from the clause texts, the preamble's pinned record contract, and `spec.md` — `.agent-guild/state/checks/probe-183.py` was not opened until the reference was written, so nothing here was reverse-engineered from the harness.
- **Comparand.** None. `.agent-guild/state/apparatus/` did not exist when this round began, so the predecessor diff is a no-op and files nothing. My build was whole before any other directory was opened, trivially: there was none to open.
- **Venues acted on** (all outside the repo, all under `/var/folders/zz/jwg0lvm10hbfv_zq5q8cf7jw0000gn/T/`):
  `con-r0-ref.hJRgsr` (reference), `con-r0-v1.fTGnbb`, `con-r0-v2.7R0Gx6`, `con-r0-v3.jfZRgw`, `con-r0-v4.sziUAk`, `con-r0-v5.LpJ48B`, `con-r0-v6.P8V4YC`, `con-r0-v7.u3Zqos`, `con-r0-v8.xe4bfB`, `con-r0-v9.9GqTub`, `con-r0-codexonly.pJTsXn`, plus the throwaway install targets each probe makes for itself.
- **Working tree.** `git status --porcelain` was empty at the start of the round and empty at filing. The one gitignored artifact that moved is `.agent-guild/hooks/__pycache__`, which C-8's own check deletes at its start and `test_hooks.py` recreates; removed before filing.
- **Protected content.** `manifest: none`. Nothing to parse, nothing to check.
- **Lint exception.** None declared.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | Check runs and discriminates a fresh-install record, but not the clause's own failing example. **Untouched tree:** red — `AssertionError: provenance record missing`. **Reference:** green. **Variant v1** (record hashes only the files copied this run — the failing example verbatim): `c1` stays **green**, because a fresh install copies everything. Only `c4` catches v1, and by `KeyError` rather than by an assertion about the record. | `probe-183.py:118-135`; `con-r0-v1.fTGnbb` |
| C-2 | major | Discriminates its failing example, but the clause admits two readings that produce materially different output and the check accepts both. **Untouched:** red. **Reference:** green. **Variant v2** (advance the stamp, leave the stale bytes): red — `AssertionError: stale-but-clean file was not upgraded`. **Fork:** reading A (`payload=38 updated/0 unchanged`) and reading B (`payload=1 updated/37 unchanged`) both pass `re.search(r"payload=(\d+) updated")` with `>= 1`. | `probe-183.py:159-160`; `con-r0-ref.hJRgsr` vs `con-r0-v6.P8V4YC` |
| C-3 | blocker | Check is sound for the mixed run itself. **Untouched:** red. **Reference:** green. **Variant v3** (one edit withholds the release, pre-#211): red — `AssertionError: clean stale file was not upgraded`. But the refusal it proves does not survive the next release: **variant v9** (a preserved file's entry restamped from its on-disk bytes, one line) passes `c1`–`c6` **and** C-8, then overwrites the user's edit on the following version bump. | `probe-183.py:163-198`; `con-r0-v9.9GqTub` |
| C-4 | minor | Discriminates its failing example. **Untouched:** red. **Reference:** green. **Variant v4** (adoption stamps the edit's own bytes as shipped): red — `AssertionError: post-adoption run overwrote the edit`. Open axis: what the adopted record holds for a *differing* file is unspecified — omit the entry, or stamp the current-source hash. **Variant v7** (stamp source hash) is also green. | `probe-183.py:201-229`; `con-r0-v7.u3Zqos` |
| C-5 | blocker | **Unsatisfiable.** **Untouched:** red — `AssertionError: stamped version missing from nudge output: ''`. **Reference:** **still red, same assertion.** `c5` hands the probe's project to `session-nudge.py` only as `"cwd"` in the hook payload; `_lib.project_dir()` reads `CLAUDE_PROJECT_DIR` or falls back two dirs up from the hook file, and never consults `cwd`. The same reference binary, given `CLAUDE_PROJECT_DIR=<tmp>`, prints exactly what the clause requires. No variant run: a check nothing conforming can pass has no discrimination left to measure. | `probe-183.py:232-255`; `plugin/hooks/_lib.py:166-188`; `con-r0-ref.hJRgsr` |
| C-6 | pass | **Untouched:** red — `AssertionError: provenance record missing`. **Reference:** green. **Variant v5** (installer appends `provenance.json` to the gitignore block it writes — the failing example verbatim): red — `AssertionError: provenance.json is gitignored; a tracked record must be addable`. Text, check, and failing example all name the same artifact. | `probe-183.py:258-270`; `con-r0-v5.LpJ48B` |
| C-7 | pass | Rubric, judged by reading. Its target exists and its failing example is live: `docs/installing.md:132-135` currently says the payload class is one where "init lands each missing file and preserves each differing one," which C-2 makes false for files clean against their recorded hashes. The four behaviors it enumerates are each checkable against the shipped implementation. | `docs/installing.md:116-137` |
| C-8 | major | First half discriminates; second half is unfalsifiable. **Untouched:** green, exit 0 (371 + 50 passed, `--check` OK). **Reference:** green. **Variant v8** (`scripts/plugin-src/` edited, mirrors not regenerated — the failing example): red, exit 1, naming the drifted files. But "with the suites carrying cases for the upgrade path, the refusal path, and the mixed run" is checked by nothing: the check was green on a tree with none of those cases, and stayed green against a full reference implementation that adds none. | `.agent-guild/state/log/build-20260820T180410.log`; `con-r0-v8.xe4bfB` |

Two preamble claims were tested rather than taken on trust, and both hold. "Codex-host coverage rides the suites C-8 runs": a reference build that breaks Codex installs outright is caught by `test_build_plugin.py` with two named failures and exit 1. "A task is not done until the build is regenerated — C-8's `--check` holds that": variant v8 confirms it.

## Diagnosis

### C-5 (blocker) — the check cannot go green against any conforming implementation

`c5` builds its project in a `mkdtemp` venue, writes `.agent-guild/CLAUDE.md` and a `provenance.json` stamped `0.0.1` into it, and then runs `plugin/hooks/session-nudge.py` with that path passed **only** as `"cwd"` inside the hook payload JSON. The nudge resolves its project through `_lib.project_dir()`, which reads `CLAUDE_PROJECT_DIR` and otherwise falls back to two directories up from the hook file. Neither route is the venue. `data["cwd"]` is consulted nowhere in the Claude hook lane — the one file that reads it is `.agent-guild/hooks/codex-hook-adapter.py:288` — and the repo's own harness sets the environment variable instead (`plugin/hooks/test_hooks.py:30`).

I built a reference nudge that satisfies C-5's text word for word, and confirmed it:

```
probe-shaped run:                    rc=0  stdout=''
project_dir() resolved by that run:  /private/var/.../con-r0-ref.hJRgsr   <- the auditor's own repo copy, not the venue
with CLAUDE_PROJECT_DIR=<venue>:     "agent-guild: this project's payload was installed by agent-guild 0.0.1,
                                      but the running plugin is 0.7.1. Run /agent-guild:init now to upgrade it?"
```

Two things follow. The clause is unsatisfiable as checked, so a worker who implements it correctly gets a FAIL with no diagnosis that points anywhere useful, and burns the ladder proving a check wrong. And the fallback silently redirects the assertion at whatever repo the probe happens to be executing in, so `c5` is reading the agent-guild checkout's own `.agent-guild/provenance.json` — a file the job never intends to create.

The fix is one of two, and both are check-method changes that need a fresh CON round:

- Set `CLAUDE_PROJECT_DIR=<tmp>` on the nudge subprocess in `c5`, matching what `test_hooks.py` already does. Add `"cwd"` alongside it if you like; the env var is what decides.
- Or state in C-5's text that the nudge resolves the project from the hook payload's `cwd`, which makes the current probe correct and the implementation a deliberate departure from `_lib.project_dir()`. This is the worse option — it forks root resolution across hooks — but it is a real choice and the clause should say which one it means.

### C-3 (blocker) — nothing falsifies the invariant ruling 3 exists to protect

Ruling 3 says no edit is ever silently overwritten. The spec says init "still refuses a file whose bytes differ from its recorded hash." Every clause checks that refusal exactly once, in the run that first sees the edit. None of them checks that the refusal survives the version bump that same run performs.

Variant v9 is a one-line change: when a run preserves an edited file, restamp its entry from the bytes on disk instead of carrying its old recorded hash forward. That is a natural reading of C-2's "restamps its hash and the record's version," since C-2 never says the restamp is scoped to clean files. Measured:

```
c1 GREEN  c2 GREEN  c3 GREEN  c4 GREEN  c6 GREEN     (and C-8 green)
release 1 refuses it?  True   | edit intact? True
release 2 refuses it?  False  | edit intact? False
```

An implementation that passes this entire constitution destroys the user's edit on the second release after they make it, with no warning, which is the precise outcome the whole job was commissioned to prevent. The gap is structural: `c3` runs the installer once and never again; `c4`'s "further re-run" assertion is scoped to the adoption path only, so it proves the property for pre-provenance kits and for nothing else.

Repair, either shape:

- Extend C-3's text and its probe: after the mixed run, advance the record's `version` again and re-run, asserting the edited file still keeps its bytes and is still the only path named. That is four lines in `c3` and one sentence in the clause.
- Or add a ninth clause owning "a preserved file's entry is never refreshed from its on-disk bytes," with C-2's restamp language narrowed to clean files so the two stop contradicting each other. A ninth clause puts the constitution over the standard ceiling of 8; write the `**Ceiling overrun**:` line and say why.

### C-1 (major) — the check cannot reach its own failing example

C-1's failing example describes a record that "hashes only the files it copied this run, so a re-run on an already-initialized project produces a record missing most of the payload." Variant v1 implements exactly that. `c1` stays green, because `c1` only ever performs a fresh install, where every file is copied this run. The clause's text is scoped to a fresh install too, so the text and check agree — it is the failing example that names a state neither can reach.

`c4` does catch v1, by `KeyError: '.agent-guild/scripts/ready-set.py'` on a line that was checking something else. Incidental coverage that raises rather than asserts is not the clause holding; it is luck.

Repair: give `c1` a second `install()` pass on the same venue and re-assert the entry set, or re-scope the failing example to something a fresh install can exhibit.

### C-2 (major) — an unresolved fork in the summary's `updated` term

C-2's antecedent is "a payload file's bytes match its recorded hash but the recorded version trails the plugin's." A file that has not changed between releases satisfies that antecedent as fully as a file that has. Read literally, the clause then requires it to be overwritten with current source and counted in `updated`.

Two faithful transcriptions, one gate expression apart (`if stale and COUNT_CLEAN_AS_UPDATED` versus `if disk_hash != source_hash`), report the same upgrade as:

```
reading A (C-2 read literally):  payload=38 updated/0 unchanged/0 preserved
reading B (the spec's AC):       payload=1 updated/37 unchanged/0 preserved
```

The check asserts `re.search(r"payload=(\d+) updated")` and `>= 1`, so it accepts both and cannot see the fork. The spec's acceptance criterion — "upgrades those files and reports how many it moved" — argues for B, and reading A tells a user that 38 files moved when one did. Settle it in the clause text, and tighten the assertion to whichever number the settled reading produces, so the check can tell the two apart.

### C-8 (major) — half the clause is checked by nothing

C-8 asks for two things: the three commands pass, and "the suites carrying cases for the upgrade path, the refusal path, and the mixed run." The check is the three commands. It was green on the untouched tree, where none of those cases exist — that is what its `green` baseline records — and it stayed green against a complete reference implementation of #183 that adds no suite cases at all. Nothing in the clause can fail on the second half.

The preamble's reason for avoiding a grep is right (#141), and the conclusion should be to drop the requirement rather than leave it unchecked: C-1 through C-4 already prove those three behaviors against the real installer, which is strictly better evidence than a test case existing. If the suites should carry cases anyway, that is a judgment read and belongs in a rubric clause, not in a command that cannot see it.

### C-4 (minor) — what the adopted record says about a file it refused

C-4 requires adoption to write a record "covering the files whose bytes match current source" and to preserve and report the rest. It does not say what the record holds for a file it refused. Omitting the entry and stamping it with the current-source hash are both consistent with the clause, both pass `c4` (v7 green), and they produce different bytes in a file the job's first ruling says is tracked and committed. One sentence in the preamble's pinned contract closes it.

### C-1 preamble contract (minor) — the version source is named for one host only

The contract pins `version` to "the `version` field of `plugin/.claude-plugin/plugin.json`." The committed Codex package is `plugins/agent-guild/`, which ships `.codex-plugin/plugin.json` and has no `.claude-plugin/` at all. A literal transcription therefore fails every Codex install:

```
install.py: packaged plugin manifest is missing: .../plugins/agent-guild/.claude-plugin/plugin.json
```

C-8's `test_build_plugin.py` does catch this (`FAIL Codex IDE bootstrap installs the full project-local Guild surface`, `FAIL the Codex initializer preserves AGENTS.md outside one idempotent section`, exit 1), so it costs a retry rather than shipping broken — which is why this is minor and not a blocker. Still, the contract as written is wrong for one of the two hosts the engine serves. Say the version comes from the packaged plugin manifest, and name both paths.

### Weight

`standard` is defensible on its stated signals and does not need a correction on its own: the acceptance checks route through suites that already exist plus probes that drive the packaged installer, and the nudge is read-only. The reading that argues for `deep` is that `probe-183.py` is 284 lines of check logic this job authored, which is closer to building an instrument than to invoking one.

It matters here only through the ceiling, which the constitution sits exactly on at eight clauses. Two of the repairs above want clause text that does not exist yet. If the fix for C-3 lands as a ninth clause rather than as an extension of C-3, that is the right call — write it and record the `**Ceiling overrun**:` line with the reason, rather than compressing the invariant into a clause that already has a job.
