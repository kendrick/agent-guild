# Constitution: Courier-lane cleanup (#106, #128, #47 + #116)

<!--
Phase 0 artifact for the job at .agent-guild/state/spec.md. Every clause names
a check a checker can run and a failure it could actually catch.

Round 3, revised against CON-audit-r2's FAIL:
  - C-9 and C-2 deadlocked on Step 1's own deliverable. `build-plugin.py`
    overlays `.claude/agents/` and `.claude/skills/` via `sync_dogfood()`, and
    `--check` verifies them, so a worker editing `guild-core/roles/` failed
    C-9 by rebuilding and C-2 by not. Both `.claude/` paths are build outputs
    now, named in C-2's text and allowed by C-9.
  - C-11's commit-count arm was branch-level in a per-task blocker, so a task
    whose only deliverable is a posted comment could not pass it. The arm is
    gone: the clean-tree arm already catches the case it was added for, since
    an uncommitted diff is a dirty tree.
  - C-7's count, C-10's two typographic rules, C-14's check on the courier
    pre-pass surviving, and C-4's fabricated-zero rule now read on C-15.

Round 2, revised against CON-audit-r1's FAIL, which found the r0 fixes mostly
holding and two things still open:
  - C-5's venue moved from forbidden to empty. `git clone --local` carries
    committed state only, and the clause's own enumeration rule assumes an
    uncommitted tree, so the copy held neither the new tests nor the change
    they cover. It is a `cp -a` of the working tree now.
  - The tests #128 requires were the one deliverable class nobody was required
    to write. C-5's existence backstop named only C-13/C-14/C-15; C-6 and C-7
    are on that list now, C-7's check reads `test_hooks.py` for its three
    cases, and C-13's reads `test_compose_brief.py` for its three shapes.
  - C-7's four operations covered three sites — the discharge and its
    far-lane trap are one site counted twice — so `test_hooks.py` went
    unchecked. The accounting is five operations across four sites now.
  - Nothing required a commit to exist, so C-10 and C-2's walk both went
    vacuous on an uncommitted tree. C-11 now requires commits past the merge
    base and a clean tree outside `state/`.
  - "No brief written" on the all-script path, the fixture venues for C-7 and
    C-13, the pre-change composer's source, `attempts`/`discarded`'s own
    types, C-11's diagnostics, C-2's leaked clone, C-12's tolerance for a
    commented-out line, and the courier pre-pass staying: all folded in.

Round 1, revised against CON-audit-r0's FAIL. Six defects and four coverage
gaps, all addressed there:
  - C-2/C-3/C-9 rested on `git diff main...HEAD`, which is empty whenever the
    work is uncommitted or HEAD is main. Every path guard now pins the branch
    as a precondition and diffs against the merge base including the worktree
    and untracked files.
  - C-5 told checker-judgment to edit the tree its own role forbids it to
    touch. The mutation now happens in a disposable clone.
  - C-7 was a reading rubric on the job's central mechanism. Three of its four
    sites now name an operation the checker performs.
  - C-4's nullable convention was ambiguous; the types are written out field
    by field.
  - C-10 required a process no artifact evidences. It states the output
    standard instead, and the facts a script can settle moved to C-11.
  - C-12 through C-15 are the four missing deliverables, shaped like C-6:
    state the behavior, run the repro the spec already wrote.

One deviation from spec.md worth recording, since C-11 pins the choice without
giving its reason. The spec says one branch per step; this job runs every task
on `chore/courier-lane-cleanup`. Per-step branches would need merges the spec
never describes, and C-2's per-commit walk, C-3, C-9, and C-11 all key off a
single branch name — four checks would have to learn which branch they were
looking at. The cost is concurrency: with one worktree and C-2's same-commit
rebuild rule, tasks that edit sources cannot run at the same time.

Routing: C-1, C-2, C-3, C-9, C-11, and C-12 are scripts and go to
checker-deterministic. C-4 through C-8, C-10, and C-13 through C-15 are
rubrics and go to checker-judgment. The split is deliberate — the last run's
constitution burned five audit rounds trying to make a script prove a test
was genuine, which no script can establish.
-->

## Clauses

### C-1: The whole verification block passes, not just the suite a task touched
- **text**: After any task's edits, all seven suites named in the spec's verification block exit 0: `.agent-guild/scripts/test_compose_brief.py`, `.agent-guild/scripts/test_ledger_append.py`, `.agent-guild/scripts/test_codex_courier.py`, `.agent-guild/scripts/test_claude_courier.py`, `.agent-guild/hooks/test_hooks.py`, `.agent-guild/hooks/test_codex_adapter.py`, and `scripts/test_build_plugin.py`. `vendor-call.schema.json` is a shared contract and `test_hooks.py` is one of its quiet consumers, so a task that edits the schema runs the hook suite too — the #43 job scoped a schema change to the schema's own tests and shipped the hook suite red for the next job to discover.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/scripts/test_compose_brief.py && python3 .agent-guild/scripts/test_ledger_append.py && python3 .agent-guild/scripts/test_codex_courier.py && python3 .agent-guild/scripts/test_claude_courier.py && python3 .agent-guild/hooks/test_hooks.py && python3 .agent-guild/hooks/test_codex_adapter.py && python3 scripts/test_build_plugin.py'
- **severity**: blocker
- **failing example**: The `attempts`/`discarded` fields land in `vendor-call.schema.json` and `test_ledger_append.py` goes green, but `test_hooks.py`'s verdict-fixture helper now builds a ledger row the amended schema rejects, and nobody ran it.

### C-2: Generated packages are regenerated at the commit that caused them
- **text**: Sources are `.agent-guild/scripts/`, `.agent-guild/hooks/`, `.agent-guild/schemas/`, `.agent-guild/templates/`, `guild-core/roles/`, `scripts/plugin-src/`, `docs/plugin-readme.md`, and `.agent-guild/CLAUDE.md`. The outputs of `python3 scripts/build-plugin.py` are `plugin/`, `plugins/agent-guild/`, and the dogfooded wrappers this repo runs on itself — `.claude/agents/` and `.claude/skills/`, overlaid by `sync_dogfood()` and verified by `--check`. That last pair is easy to miss and it is not optional: editing a file under `guild-core/roles/` and rebuilding changes `.claude/agents/` too, and skipping the rebuild leaves `--check` red. A task that edits a source runs the build and commits the refreshed packages in the same commit, so `build-plugin.py --check` is clean at every commit on the branch and not merely at its tip. Editing a generated copy by hand reaches the same end state today and drifts the next time anyone runs the build, so it fails this clause even when `--check` is momentarily quiet.
- **check**: .agent-guild/scripts/check-build.sh 'git rev-parse --abbrev-ref HEAD | grep -qx chore/courier-lane-cleanup || { echo "not on chore/courier-lane-cleanup; this guard cannot see the job commits from here" >&2; exit 1; }; python3 scripts/build-plugin.py --check || exit 1; d=$(mktemp -d) && trap "rm -rf \"$d\"" EXIT && git clone -q --local --no-hardlinks . "$d" && cd "$d" && for c in $(git rev-list origin/main..HEAD); do git checkout -q "$c" && python3 scripts/build-plugin.py --check || { echo "stale generated packages at commit $c" >&2; exit 1; }; done'
- **severity**: blocker
- **failing example**: Commit 1 adds the exit-3 branch to `.agent-guild/scripts/compose-brief.py`; commit 3 regenerates `plugin/`. The tip is clean and `--check` exits 0, while commits 1 and 2 ship a package whose `compose-brief.py` is a different program from the source beside it.

### C-3: Archived job state is never rewritten
- **text**: Nothing under `.agent-guild/state/archive/` changes on this branch, committed or uncommitted. Those are three closed runs' briefs, verdicts, and ledgers, and every issue in the spec forbids rewriting them; a schema that gains fields does so without touching a row already written.
- **check**: .agent-guild/scripts/check-build.sh 'git rev-parse --abbrev-ref HEAD | grep -qx chore/courier-lane-cleanup || { echo "not on chore/courier-lane-cleanup; this guard cannot see the job diff from here" >&2; exit 1; }; test -z "$(git diff --name-only "$(git merge-base main HEAD)" -- .agent-guild/state/archive; git status --porcelain -- .agent-guild/state/archive)"'
- **severity**: blocker
- **failing example**: A worker "fixes" the absolute `artifacts` paths in `.agent-guild/state/archive/2026-08-11-issue-141/log/vendor-calls.jsonl` so they match #47's new relative form, and has not committed yet when the checker arrives.

### C-4: The ledger's new fields are optional, typed to match the top level, and break no archived row
- **text**: In `vendor-call.schema.json`, neither `attempts` nor `discarded` appears in `required`, and `additionalProperties` stays `false`. `attempts` is an `integer` and `discarded` is an `array` whose `items` are objects. Inside a `discarded` entry the types mirror the top-level fields of the same name exactly: `reason` is `string`, `duration_ms` is `integer`, `exit_code` is `integer`, and `tokens_in` and `tokens_out` are each `["number", "null"]`. A vendor that reported no token figure for a discarded attempt gets `null`, never a fabricated `0`, which is the whole reason the top level spells them that way. The consequence is the real bar: every line of all three archived ledgers — `.agent-guild/state/archive/2026-08-10-issue-117/log/vendor-calls.jsonl`, `.agent-guild/state/archive/2026-08-11-issue-100/log/vendor-calls.jsonl`, and `.agent-guild/state/archive/2026-08-11-issue-141/log/vendor-calls.jsonl`, 21 rows between them — still conforms after the change.
- **check**: checker-judgment: read the amended schema and confirm, field by field, that the two new keys are absent from `required`, that `additionalProperties` is still `false`, that `attempts` is `integer` and `discarded` is an `array` of objects, and that the five `discarded` members carry exactly the types named above; then load the schema through `ledger-append.py`'s own `load_schema` and run its `schema_violation` over all 21 lines of the three archived ledgers, naming file and line number for any row that fails. FAIL on any type that differs from the list, not only on a row that breaks.
- **severity**: blocker
- **failing example**: `discarded[].tokens_in` is declared `{"type": "integer"}`. No archived row carries a `discarded` key, so every archived row still validates and the schema half of the check is quiet — while the first courier whose discarded attempt reported no usage has to write a `0` it invented.

### C-5: A new test fails when the change it covers is reverted
- **text**: Each test added or amended by this job is genuine: it goes red when the production change it exercises is backed out, and green again when restored. A test that passes against both states covers nothing, and no script can tell the difference — this has to be re-derived by running it. The mutation is a check instrument, not a repair, and it happens in a disposable copy of the working tree; the job branch is never edited by a checker.
- **check**: checker-judgment: copy the whole working tree to a throwaway directory under the session scratchpad with `cp -a` or `rsync -a`, and work only there. The copy has to carry uncommitted and untracked files, which is why it is a filesystem copy and not `git clone` — a clone takes committed state only, so it is the wrong instrument whenever anything under review has not landed in a commit yet. C-11 requires the tree to be clean outside `state/`, so in the ordinary case the copy and a clone would agree; the copy is specified because it is correct in both states and a clone is correct in only one. Enumerate the new or changed test cases from the task's own artifact list, not from a diff. For each case, back out the corresponding production edit in the copy, run that suite, and confirm the case fails; restore and confirm it passes. Report the copy's path, the mutation applied, and the observed failure text for each case. FAIL if any new case survives its own mutation. FAIL also if the task's artifact list names no test for a behavior C-6, C-7, C-13, C-14, or C-15 requires — this clause bites only tests that exist, so it cannot be the coverage argument for a test nobody wrote.
- **severity**: blocker
- **failing example**: `test_compose_brief.py` gains an all-script case asserting a non-zero exit, which passes identically against the old code because the old code already exits 1 on that input — the case never distinguished exit 3 from exit 1 at all.

### C-6: #106 closes on a replay, not on a reading
- **text**: The evidence attached to #106 comes from actually driving a vendor response with unescaped double quotes inside a JSON string through `codex-courier.py`'s path and observing what the harness did. Quoting the source to argue the guarantee holds is not evidence. The evidence has to show all four live acceptance criteria: nothing reached the lane-suffixed stem unvalidated, one retry happened on the fixed lane, the second failure produced a schema-conforming `blocked` verdict, and the raw attempts were retained under `state/log/courier-raw/`. The amended criterion — vendor JSON is re-serialized because #142/#144 stamps `model` locally — is recorded as a deliberate amendment with its `info` finding, not quietly passed over.
- **check**: checker-judgment: re-run the replay yourself from the artifacts the task names and compare what you observe against the posted comment claim by claim; FAIL if any of the four criteria is asserted rather than demonstrated, if the amendment note is missing, or if the posted evidence describes a run you cannot reproduce.
- **severity**: blocker
- **failing example**: The comment on #106 says "verified against `_validate_structured_output`; the retry-once-then-blocked path is covered by the existing malformed fixture" and cites line numbers, with no run output and no case using #106's own embedded-quote payload.

### C-7: The `.skipped` discharge route is exercised at all four sites
- **text**: A recorded skip is a complete discharge route or it is a livelock. Four sites carry it. `compose-brief.py` exits 3 with the exact stderr line `compose-brief: nothing to cross: <task-id> cites only script-checked clauses`, distinct from the existing exit-1 error, and writes no brief file at all on that path — a brief sitting at a stem no courier may legally cross is an artifact nothing will ever collect. `second_opinion_debts` in `.agent-guild/hooks/_lib.py` discharges a debt on a `.skipped` marker the same way it does on `.denied`. `dispatch-guard.py` denies a `checker-courier` dispatch on a stem carrying one. And `test_hooks.py` carries all three of the cases the spec names: a debt discharged by `.skipped`, a courier dispatch denied on a skipped stem, and the wrong-lane trap where a marker filed under the other host's lane discharges nothing.
- **check**: checker-judgment: six operations across the four sites. Site 1, twice: compose a fixture task citing only script-checked clauses, invoke `compose-brief.py` against it, compare stderr byte for byte with the string this clause states in full, and confirm no file exists at the brief's output path afterward. Site 2, twice: build a fixture project holding a verdict of record plus a `T-NNN-<tier>-r0-<lane>.skipped` marker, confirm `second_opinion_debts` returns no debt for that stem, then refile the same marker under the far host's lane suffix and confirm the debt stands. Site 3: read `dispatch-guard.py` and say where its `stem` is computed relative to the denial. Site 4: read `test_hooks.py` and name the three cases above by their `check(...)` label, failing if any is absent. Stage every fixture outside the live `.agent-guild/state/` — `compose-brief.py` takes its state dir from `os.getcwd()`, so run it by absolute path from a fixture directory, and `second_opinion_debts` reads `project_dir()`, which honors `CLAUDE_PROJECT_DIR`. A fixture staged in the live state directory becomes an open task the stop gate acts on. FAIL if any observed behavior differs from the text, including a stderr string differing by one character.
- **severity**: blocker
- **failing example**: `second_opinion_debts` learns about `.skipped` but the lane comparison is dropped, so a `T-001-sonnet-r0-claude.skipped` file discharges a debt on a Claude host whose own lane is `codex` — the same trap `.denied` already carries, reintroduced.

### C-8: The docs describe the code an agent will actually meet
- **text**: Three source documents change with the behavior and end up consistent with it. `guild-core/roles/checker-courier.md` says a crossing happens only when the brief carries at least one judgment clause, tells the courier what to do on exit 3, no longer carries the "if evidence a clause requires was not supplied" fallback that now has nothing behind it, and its "a retried call sums its attempts into a single row" line gains the `discarded[]` detail. `.agent-guild/CLAUDE.md`'s dual-check regime reads "after every checker of record whose task cites a judgment clause", and its state map lists the `.skipped` marker with its lane trap and names the orchestrator as the agent that writes it, on compose-brief's exit 3 — the route's only trigger is a human-readable instruction, so a state map that lists the marker without saying who files it leaves the route unreachable. `.agent-guild/templates/task.md` makes the skip case explicit in the Courier comparison section.
- **check**: checker-judgment: read each of the three documents against the code it describes and name any instruction that would lead an agent to a state the code refuses, any behavior the code has that the document still contradicts, and any of the requirements listed above that is absent. A contradiction is a blocker; so is an absent requirement from this clause's own list. An omission this clause does not name is a minor finding.
- **severity**: blocker
- **failing example**: `checker-courier.md` still instructs the courier to dispatch the lane unconditionally while `compose-brief.py` now exits 3 without writing a brief, so the courier shells out with no brief file and the crossing dies at the vendor.

### C-9: The diff stays inside the paths this job names
- **text**: Every file the branch changes relative to its merge base with `main` — committed, staged, unstaged, or untracked — sits under `.agent-guild/scripts/`, `.agent-guild/hooks/`, `.agent-guild/schemas/`, `.agent-guild/templates/`, `.agent-guild/state/`, `guild-core/roles/`, `scripts/plugin-src/`, `plugin/`, `plugins/agent-guild/`, `.claude/agents/`, or `.claude/skills/`, or is `.agent-guild/CLAUDE.md`, `docs/plugin-readme.md`, or `.github/workflows/plugin-build.yml`. The two `.claude/` entries are there because they are build outputs, not because this job edits them by hand: `build-plugin.py` overlays them from `guild-core/`, so a role edit that is correctly rebuilt lands there whether the worker meant it to or not.
- **check**: .agent-guild/scripts/check-build.sh 'git rev-parse --abbrev-ref HEAD | grep -qx chore/courier-lane-cleanup || { echo "not on chore/courier-lane-cleanup; this guard cannot see the job diff from here" >&2; exit 1; }; out=$( { git diff --name-only "$(git merge-base main HEAD)"; git status --porcelain | cut -c4-; } | sort -u | grep -vE "^(\.agent-guild/(scripts|hooks|schemas|templates|state)/|\.agent-guild/CLAUDE\.md|guild-core/roles/|scripts/plugin-src/|docs/plugin-readme\.md|\.github/workflows/plugin-build\.yml|plugin/|plugins/agent-guild/|\.claude/(agents|skills)/)" ); test -z "$out" || { echo "$out" >&2; exit 1; }'
- **severity**: major
- **failing example**: A worker notices `docs/courier-comparison.md` describes the old unconditional dual-check rule and rewrites it on this branch, adding a file no step in the spec claims.

### C-10: Human-facing prose earns its reading
- **text**: Every commit message says why the change exists, not only what moved, and every human-facing prose edit — commit messages, the #106 comment, and the doc and role text C-8 covers — is free of the AI-writing tells the `humanizer` skill enumerates. Headings stay title-cased and em dashes appear unspaced and used sparingly, per the standing user preference. The bar is the prose on the page: this clause judges what shipped, not how it was produced.
- **check**: checker-judgment: read `git log main..HEAD` and the prose diffs for inflated symbolism, tripartite lists that pad or drop an item to reach three, vague attribution, negative parallelism, "-ing" clauses tacked onto a sentence end to editorialize, and commit subjects that describe the edit without its cause. Check the two typographic rules directly: every heading added or changed in a doc keeps its main words capitalized, and every em dash sits flush against the words on both sides with no surrounding spaces. Also judge commit granularity: one logical change per commit, and a commit mixing two unrelated changes is a finding. FAIL naming the commit or file and quoting the specific tell.
- **severity**: major
- **failing example**: A commit reads `feat(brief): add exit 3 to compose-brief.py` — accurate, and it says nothing about the all-script task that would otherwise hang the stop gate forever, which is the only reason the exit code exists.

### C-11: The branch is the one this job agreed to, it stays local, and nothing is left uncommitted
- **text**: Work happens on `chore/courier-lane-cleanup`, branched from `main`, and nothing is pushed: the branch has no upstream tracking ref for the whole life of the job. At check time nothing outside `.agent-guild/state/` is left uncommitted — job bookkeeping under `state/` is the kit's own churn and is exempt. Without that last part the rest of the document goes quiet: C-10 reads `git log main..HEAD` and C-2 walks the branch's commits, so a job that ends as one uncommitted diff on the right branch would satisfy both by giving them nothing to read. The requirement is that work on disk has landed in a commit, not that any particular task produced one — a task whose whole deliverable is a posted GitHub comment changes no file, leaves the tree clean, and passes.
- **check**: .agent-guild/scripts/check-build.sh 'git rev-parse --abbrev-ref HEAD | grep -qx chore/courier-lane-cleanup || { echo "not on chore/courier-lane-cleanup (on $(git rev-parse --abbrev-ref HEAD))" >&2; exit 1; }; git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1 && { echo "the branch has an upstream tracking ref; nothing on this job is pushed" >&2; exit 1; }; d=$(git status --porcelain | cut -c4- | grep -v "^\.agent-guild/state/"); test -z "$d" || { echo "uncommitted work outside .agent-guild/state/:" >&2; echo "$d" >&2; exit 1; }'
- **severity**: blocker
- **failing example**: A worker commits the CI fix straight to `main` because the branch did not exist yet. C-3 and C-9 both report clean from there, having nothing to diff.

### C-12: CI runs the suite the guarantee lives in
- **text**: `.github/workflows/plugin-build.yml` runs `python3 .agent-guild/scripts/test_codex_courier.py` as a live line in its suite list — indented into the `run:` block like its neighbours, not commented out and not trailing other text. That file is the only test of the script #106's whole guarantee lives in, and it appears in no workflow in the repo today, so every assertion this job adds to it would run locally and nowhere else.
- **check**: .agent-guild/scripts/check-build.sh 'grep -qE "^[[:space:]]+python3 \.agent-guild/scripts/test_codex_courier\.py[[:space:]]*$" .github/workflows/plugin-build.yml'
- **severity**: blocker
- **failing example**: The job ships #116's retried-crossing assertions into `test_codex_courier.py`, every clause passes, and the file remains unreferenced by any `.yml` — a green CI badge over a suite CI never runs.

### C-13: The composer partitions on the check prefix, and drops rather than demotes
- **text**: `compose-brief.py` keeps a cited clause only when the value of its `- **check**:` line starts with `checker-judgment:`. A script-checked clause is dropped from the brief entirely — not moved to a context section, not summarized, not mentioned; the issue settled that. A mixed-clause task produces a brief in which the script-checked clause's text and check line are both absent, and an all-judgment task produces a brief byte-identical to the one today's composer produces. The prefix is anchored: a clause whose check merely contains the string `checker-judgment` somewhere in it is not a judgment clause.
- **check**: checker-judgment: run the spec's own repro, staging every fixture in its own directory outside the live `.agent-guild/state/` and invoking `compose-brief.py` by absolute path from there, since the script takes its state dir from `os.getcwd()`. Stage a fixture constitution holding one script-checked clause and one judgment clause plus a task citing both, run the composer, and grep the written brief for the script clause's id and its check line — both must be absent while the judgment clause survives verbatim. Run it again against an all-judgment task and diff the brief against one produced by the pre-change composer, recovered with `git show $(git merge-base main HEAD):.agent-guild/scripts/compose-brief.py`; they must be byte-identical. Construct a clause whose check reads `.agent-guild/scripts/check-foo.sh --mode checker-judgment:x` and confirm it is dropped. Then read `test_compose_brief.py` and confirm it carries all three shapes the spec names — mixed, all-judgment, all-script — failing if any is absent. FAIL if any of the observations differs.
- **severity**: blocker
- **failing example**: The filter tests `"checker-judgment" in check_value` rather than the prefix, so a deterministic clause whose script takes a flag containing that word crosses the lane anyway — the exact class of clause #128 exists to stop sending.

### C-14: Ledger artifact paths go relative under the root and are left alone outside it
- **text**: `ledger-append.py` rewrites each `--artifacts` value that resolves under the repo root to a repo-relative path before the assembled line is validated, using the same `os.getcwd()` base the script already uses for `DEFAULT_LEDGER` and for reading `spec.md`'s provenance ref. A value already relative is unchanged. A value that resolves outside the root is written as given, and no rewritten path is ever a `../` chain. The rewrite is not existence-gated: a path resolving under the root is relativized whether or not a file sits there. That is a deliberate divergence from `_courier_lib.repo_relative`, which drops a path whose file is missing — the helper is the couriers' own pre-pass and it stays exactly as it is, since deleting it as newly redundant would silently change what a courier logs for a missing artifact. No archived ledger is rewritten by this change (C-3 covers the file; this covers the intent).
- **check**: checker-judgment: run the spec's two-row repro against a temp ledger. Append one row whose `--artifacts` value is an absolute path under the repo root and one whose value is an absolute path outside it; read both rows back and confirm the first is repo-relative, the second is byte-identical to what was passed, and neither contains `../`. Append a third row with an already-relative value and confirm it is unchanged. Then confirm the courier pre-pass survived: call `_courier_lib.repo_relative` with an under-root path whose file does not exist and confirm it still returns `None`, so a stub that quietly became a pass-through is caught — both courier suites stay green against such a stub, so C-1 is no backstop here. FAIL if any row differs, and FAIL if the rewrite runs after `schema_violation` rather than before it, since a path the schema has already accepted is a path the ledger has already committed to.
- **severity**: major
- **failing example**: The rewrite calls `os.path.relpath` unconditionally, so a courier logging an artifact under `/var/folders/.../scratchpad` gets `../../../var/folders/...` in the ledger — a path that resolves nowhere once the row is read from anywhere but that one working directory.

### C-15: A retried crossing is visible in its ledger row
- **text**: `ledger-append.py` accepts `--attempts N` and a repeatable `--discarded` taking one JSON object per discarded call. `codex-courier.py` times each `_run_once` individually and captures that call's own token usage before folding it into `usage_totals`, then passes `--attempts` and one `--discarded` entry per non-final attempt, with `reason` set to that attempt's validation failure. The row's top-level `tokens_in` and `tokens_out` stay the cumulative sums across attempts, so a cost total means what it meant before this change. `quota_event` is untouched, so a quota abandonment stays distinguishable from a retried crossing. `claude-courier.py` captures the same per-attempt figures into the `ledger` payload it returns; it never calls `ledger-append.py` itself, and threading the flags through the Codex-host parent that does is out of scope.
- **check**: checker-judgment: drive a retried crossing through `test_codex_courier.py`'s fake-CLI harness in `malformed_once` mode and read the ledger row it writes. Confirm `attempts` is 2, that `discarded` holds exactly one entry whose `reason` names the first attempt's validation failure and whose `duration_ms` is that attempt's own elapsed time rather than the cumulative figure, and that top-level `tokens_in`/`tokens_out` still equal the sum across both attempts — `test_codex_courier.py` already pins that sum at 108 and 26, so a change to those numbers is the tell that the totals stopped being cumulative. Drive a quota abandonment and confirm `quota_event` is still true with no `discarded` entry invented for it. Read the code that builds a discarded entry and confirm an attempt whose usage the vendor never reported writes `null` for `tokens_in`/`tokens_out` rather than `0` — the fabricated zero is the failure the top-level fields were spelled nullable to prevent, and no fixture in the suite happens to exercise it. Read `claude-courier.py`'s returned `ledger` payload and confirm the per-attempt figures are present in it. FAIL if `duration_ms` inside a discarded entry equals the row's own `duration_ms`, which is the tell that the cumulative clock was reused.
- **severity**: blocker
- **failing example**: `codex-courier.py` passes `--attempts 2` and a `--discarded` entry whose `duration_ms` is read from the same `started_clock` the row uses, so the discarded attempt appears to have taken as long as the whole crossing and the retry costs nothing measurable.

## Protected content

No protected passages. This job ships no verbatim author copy — every string it writes is either code, a stderr message the constitution specifies in full (C-7), or prose written fresh for it.

## Non-goals

- #34 itself. These steps clean its evidence stream; the ruling stays open and no clause here decides it.
- Rewriting any archived brief, verdict, or ledger (C-3 forbids it outright).
- Threading `--discarded` flags through the Codex-host parent that calls `ledger-append.py` on `claude-courier.py`'s behalf. That code is outside the courier and outside what #116 names; C-15 stops at the payload the courier returns.
- Closing #106 on GitHub. A worker posts the evidence comment; the close is the user's, so no clause requires the issue to end in a closed state.
- Persisting `tokens_cached` in the ledger. #150 documented that gap deliberately and it is a separate contract change with its own consumer pass.
