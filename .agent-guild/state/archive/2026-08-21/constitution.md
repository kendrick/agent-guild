# Constitution: payload provenance — a version stamp plus per-file hashes so re-init can upgrade (#183)

**Job weight**: deep, corrected from standard by the user on CON-audit r4's finding, because verification did require building an instrument rather than invoking one: a ~600-line probe harness covering three install shapes and four nudge deployments, and a reference implementation each audit round rebuilds and mutates. The original derivation read "the suites already exist" off the spec and missed that none of those suites asserts anything about provenance, which the preamble had already noticed and the weight line had not.

<!--
Job source: kendrick/agent-guild#183, intaken to spec.md with provenance header.

CONTEXT THE SPEC PREDATES. The issue was filed against v0.6.0. Since then #211
shipped the narrow cut (a drifted payload file preserves and continues, net-new
files land), and #213 gave the payload a tracked marker, .agent-guild/CLAUDE.md.
This job builds the remainder: the provenance record, the upgrade-in-place path
for files clean against their RECORDED hashes, refusal keyed to the record
rather than to current source, pre-provenance adoption, and the session nudge.

THREE RULINGS FROM THE USER, made at intake and binding on every clause:
1. The record is TRACKED: .agent-guild/provenance.json, beside the marker,
   committed with the payload. Not gitignored, not under state/.
2. The nudge PROMPTS: it names both versions and /agent-guild:init and asks
   whether to run it now. It never runs init itself and never writes.
3. Pre-provenance kits ADOPT WHAT MATCHES: a file matching current source is
   stamped at the current version; a differing file is preserved and reported.
   No edit is ever silently overwritten.

THE RECORD'S CONTRACT, pinned here so no worker or checker re-derives it:
.agent-guild/provenance.json is a JSON object with exactly two keys —
"version" (string, the plugin version that wrote the payload, equal to the
"version" field of the host package's own manifest beside the installer's
             project-template/ root: .claude-plugin/plugin.json for the Claude
             package, .codex-plugin/plugin.json for the Codex one — naming only
             the Claude path would fail every Codex install) and
"files" (object mapping project-root-relative payload paths, "/"-separated,
to lowercase hex sha256 of the bytes as shipped). Payload scope: the payload
set install() computes — under .agent-guild/, excluding state/, the record
itself, and the Codex repo-local hooks/, which install() splits out of the
payload and copies with _copy_owned so they upgrade on every re-init.
Provenance governs only what _copy_missing can preserve, which is the line
docs/installing.md already draws where it says install() splits the Codex
project hooks out of the payload before the drift check runs.

WHY THE CHECKS LOOK LIKE THIS. C-1 through C-6 check BEHAVIOR of the packaged
installer and the session nudge, so each runs a probe subcommand in
.agent-guild/state/checks/probe-183.py rather than reading a test suite — a
check that greps test source is satisfied by comment lines (#141). Each probe
builds a throwaway project under the system tmpdir, runs
plugin/project-template/install.py (or plugin/hooks/session-nudge.py) against
it, and reads what actually happened. Every probe that mutates its venue
asserts the mutation landed before re-running the installer. C-1 drives all
three install shapes and C-5 all three nudge deployments, because each of
those resolves a version from a different place: r1 built a reference writing
the record only on the claude branch, and r3 built one whose nudge ran the
claude branch in every Codex session, both green everywhere. The engine is
shared, but nothing in the suites asserts anything about provenance, so "the
Codex paths ride the existing suites" is false for this job and is not
claimed here. C-2 through C-4 drive the Claude package alone, below the host
branch, where the payload sync is one code path. The probes read the BUILT
plugin/ and plugins/ trees, while the sources a worker edits are build inputs
— scripts/plugin-src/ for the installer, .agent-guild/hooks/ for the nudge —
so a task writing either is not done until the build is regenerated. C-8's
--check holds that.

Baselines were run against the tree as the job finds it: C-1 through C-6 fail
today (no provenance exists anywhere), so all six declare red. C-8 passes
today and declares green.
-->

## Clauses

### C-1: install writes the provenance record
- **text**: An install on either host — `claude` from the Claude package, `codex` from the Codex one — writes `.agent-guild/provenance.json` matching the contract in the preamble: exactly the keys `version` and `files`, and `version` equal to that host package's own manifest, read at run time rather than compiled in — provably, since a copy of the package whose manifest carries a version nothing else does stamps that version. On a project where the install preserved nothing, the record carries one entry per installed payload file — the payload set `install()` computes, which is `.agent-guild/` minus `state/`, minus the record itself, and minus the Codex repo-local `hooks/`, since those are `_copy_owned` and overwritten on every re-init, exactly the line `docs/installing.md` already draws where it says `install()` splits the Codex project hooks out of the payload before the drift check — no entry for any other path, and each hash matches the bytes on disk; entries for files a run preserved are governed by C-3 and C-4 instead. This holds across all three shipped install shapes: `claude`, bare `codex`, and `codex --project-skills`. That holds on each of those shapes after a fresh install and again after an idempotent re-run that copies nothing, since a record scoped to the files one run wrote is indistinguishable from a whole-payload record on a fresh install, and a re-run checked on one host proves nothing about the other.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe-183.py c1'
- **baseline**: red
- **severity**: blocker
- **failing example**: An install that writes the record only on the `claude` branch, leaving every Codex project pre-provenance forever while the suites stay green.

### C-2: clean-but-stale files upgrade in place
- **text**: Re-running init brings every payload file whose bytes match its recorded hash to current source, restamps that file's hash, advances the record's version, and reports a summary whose three terms account for the whole payload. The decision is per file and the stamp never gates it: a file clean against its record is upgraded whether the recorded version trails the plugin's or equals it, since the record — not the stamp — is what says the bytes are the guild's rather than the user's. Terms: `updated` counts exactly the files whose bytes changed, `preserved` is zero when nothing was edited locally, and `unchanged` carries the rest. A stale stamp over a file already matching source moves nothing, so the count reports files moved rather than files examined.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe-183.py c2'
- **baseline**: red
- **severity**: blocker
- **failing example**: A run that reports every file it did not write as `preserved` whenever the stamp is stale, so a routine upgrade prints the issue's own headline warning over 37 paths the user never touched.

### C-3: a mixed run refuses only real edits
- **text**: In one invocation against a project holding a locally edited file (bytes differ from its recorded hash), a clean-but-stale file, and a missing net-new file: the edited file keeps its bytes and is the only payload path the diagnostic names — checked as the whole set of payload paths appearing in the output, not as spot checks on the fixture's own two — the clean file upgrades to current source, and the missing file lands matching source, with exit 0. The run advances the record's version to the running plugin's even though it preserved a file, since a stamp held back by any conflict pins the project forever and leaves C-5's nudge firing every session with nothing that clears it. A preserved file's recorded hash is carried forward untouched — never refreshed from the bytes on disk — so the refusal survives that bump and the next release refuses the edit again.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe-183.py c3'
- **baseline**: red
- **severity**: blocker
- **failing example**: A run that refuses the edited file and also skips the clean-but-stale one, reproducing the pre-#211 behavior where one edit withholds the rest of the release.

### C-4: a pre-provenance kit adopts what matches
- **text**: Re-running init on a project with payload but no `provenance.json` writes a record at the current version covering exactly the files whose bytes match current source, each at its on-disk hash, preserves and reports every file that differs — all of them, not the first — and records no entry at all for those, and on a further re-run still preserves and reports every one of those same files — all of them, since preserving the first and taking the rest from source is wholesale trust delayed by one re-init, which the spec rules out — rather than treating the adopted stamp as proof they shipped that way. A file carrying no entry whose bytes match current source is recorded at that hash by the next run and stops being reported, since restoring the shipped bytes is the remedy the warning implies and a warning nothing can clear is a defect.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe-183.py c4'
- **baseline**: red
- **severity**: blocker
- **failing example**: An adoption pass that stamps every existing file's current bytes as shipped, so the next upgrade sees the user's edited file as clean and overwrites it — the wholesale-trust failure the spec rules out.

### C-5: the session nudge names the gap and asks
- **text**: `session-nudge.py`, run at session start in a fully installed project whose record's `version` trails the running plugin's — the project resolved the way every Claude-lane hook resolves it, through `_lib.project_dir()` — emits output containing the stamped version, the running plugin version, the host's own runnable init command — named, not merely not-the-other-host's — and a question offering to run it now. The running version is read at run time from that package's manifest rather than compiled in, provably: a copy of the package whose manifest reads a version nothing else carries is reported as that version. The notice sits above both early returns in the file, so it prints before either can return: in a fully installed project, where the partial-init report returns early, and in a project where the plugin is registered twice — #104 says this repo is in that state — where that warning prints and then returns. Those returns keep their current behavior. This job moves the notice above them and removes neither, so a project that is both double-registered and partially initialized prints the notice and the double-registration warning and not the partial-init report, exactly as it does today minus the notice. Rewriting that message policy is out of scope here. It stays subject to jurisdiction: no marker, no version notice. That binds this notice and nothing else — the double-registration warning reads the project's own settings rather than the payload and already fires above the marker gate, which `test_hooks.py` pins, so moving it below is a regression this clause does not license. It reads the running version from the manifest of the package its own hook file ships inside, so the Codex package's copy reports the gap in a Codex project — carrying that host's own command, not the Claude one — rather than staying silent. There are three deployments and the third is the repo-local copy at `<project>/.agent-guild/hooks/session-nudge.py`, which ships inside no package: with no manifest to read it makes no version claim, and it exits 0 rather than raising, since the Codex adapter turns a raise into a blocked session start. In a project whose stamp equals the running version it says nothing about a version gap. The project's files are byte-identical before and after every one of these runs — each arm snapshots its own project, since "wrote nothing" is a property of a run and not of the one run a probe happens to watch: the nudge asks, and never writes.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe-183.py c5'
- **baseline**: red
- **severity**: major
- **failing example**: A nudge keyed on "a record exists" rather than on the versions differing, which tells every user of an up-to-date project to upgrade to the version they are already on, every session start.

### C-6: the record is trackable in git
- **text**: After a fresh install into a git repository, `.agent-guild/provenance.json` exists and is not matched by any gitignore rule (`git check-ignore` exits 1 for it), while `.agent-guild/state/` remains ignored — the record commits with the payload it describes.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe-183.py c6'
- **baseline**: red
- **severity**: major
- **failing example**: An installer that appends `provenance.json` to the gitignore block it writes, so every fresh clone of the project arrives pre-provenance and the record never travels with the repo.

### C-7: the docs state the new semantics
- **text**: `docs/installing.md` documents the provenance record and each behavior a user meets: that the record is committed with the payload, that re-running init upgrades files clean against their recorded hashes, that files differing from their recorded hashes are preserved and named, and how a pre-provenance project is adopted. It also keeps drawing the line the rest of this constitution cites it for — that `install()` splits the Codex repo-local hooks out of the payload before the drift check, so they upgrade on every re-init while payload files do not — since this constitution's payload-scope definition and the probes both point at that sentence rather than restating it.
- **check**: checker-judgment: read docs/installing.md as a user holding a pre-provenance project and one with a stale kit; confirm each of the four behaviors in the clause text is stated accurately against the shipped implementation, and that the re-init table from #214 still tells the truth about which files upgrade
- **severity**: major
- **failing example**: The #214 table still saying payload files are never overwritten, which C-2 makes false for files clean against their recorded hashes.

### C-8: the suites and the build stay green
- **text**: `python3 .agent-guild/hooks/test_hooks.py`, `python3 scripts/test_build_plugin.py`, and `python3 scripts/build-plugin.py --check` all pass. Every task that writes an input to any of those three commands cites this clause, so the last such task in the schedule is the one whose check reads the tree the job actually ships. Naming a "finished tree" instead would oblige nobody to produce one: a clause checked only at the first writer certifies a tree a later task then changes, and every verdict in the job stays green while it happens.
- **check**: .agent-guild/scripts/check-build.sh 'rm -rf plugins/agent-guild/hooks/__pycache__ plugin/hooks/__pycache__ .agent-guild/hooks/__pycache__ && python3 .agent-guild/hooks/test_hooks.py && python3 scripts/test_build_plugin.py && python3 scripts/build-plugin.py --check'
- **baseline**: green
- **severity**: blocker
- **failing example**: A worker who edits `scripts/plugin-src/install-project.py` without regenerating the mirrored trees, leaving `--check` red because the shipped plugin no longer matches a fresh build.

### C-9: the suites carry the regression cases
- **text**: The repo's own suites gain cases that would fail against the tree as this job found it, covering three paths: a clean-but-stale file upgrading, an edited file being refused, and a mixed run where both happen alongside a net-new file landing. Each case asserts on the installed bytes or the record's contents, not on a log line, and each would go red if its behavior regressed.
- **check**: checker-judgment: for each of the three paths, find the case in `scripts/test_build_plugin.py` or `.agent-guild/hooks/test_hooks.py`, read what it asserts, and confirm it would fail against the pre-job behavior; a case that asserts only on summary text, or that passes with the feature reverted, does not count. Reverting is reasoning, not an edit — do not modify the tree.
- **severity**: major
- **failing example**: A test that installs twice and asserts `"preserved" in stdout`, which passes against today's installer and so proves nothing about the upgrade path.

## Protected content

- manifest: none — no words in this job must ship verbatim.

## Non-goals

- Version-pinning a project to an older guild on purpose, or supporting more than one payload version per repo (spec's own non-goals).
- The nudge running init itself, or any write to a project at session start — it prompts and stops.
- Codex-host coverage of the upgrade, refusal, and adoption paths (C-2 through C-4). Those three run below the host branch, on the shared payload-sync engine. The host-specific lookups are covered rather than waived: C-1 drives all three install shapes, and C-5 drives all three nudge deployments — the Claude package's, the Codex package's, and the repo-local copy that has no manifest at all — because each resolves a running version differently.
- The installer's gitignore covered-set gap (a `state/*` line is judged uncovered and gets a duplicate `state/` appended) — adjacent, observed during intake, and filed separately rather than folded in here.
