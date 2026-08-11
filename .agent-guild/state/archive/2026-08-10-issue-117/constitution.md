# Constitution: #117 — a ledger row names the job it came from

Source spec: `.agent-guild/state/spec.md` (`source: file`, the plan for issue #117).

Round 3. Prior verdicts: `verdicts/CON-audit-r0.md`, `CON-audit-r1.md`, `CON-audit-r2.md`.

The audit history is the short version of what this document had to learn. r0: four clauses whose checks could not fail their own failing example. r1: the repair moved the problem, since checks that stopped depending on this job's tests also stopped requiring those tests to exist. r2: consolidating the two into one counted check inverted the trade again, because counting lines that start `ok   job:` binds a prefix rather than an assertion, and six vacuous cases would pass it. Behavior and coverage are two bars and get two clauses, each checked the way it can actually fail.

Two rules that apply to every clause, stated once:

**Every check runs from the repo root**, `/Users/k.arnett/repos/agent-guild`. The kit's scripts resolve `.agent-guild/state/` relative to cwd, and `check-diff-scope.py` compares git's relative paths against its allowlist.

**No worker commits anything.** Committing is orchestrator wrap-up after the job ends, listed under non-goals. That is what lets C-4 and C-5 read the working tree, and it removes the contradiction r2 found in the previous draft, where a rule deferring commits until after every verdict made the commit-message half of C-8 impossible to check. The commit messages are drafted into a file instead, so a checker can read them before they exist as commits.

## Clauses

### C-1: The suite carries a passing case for each behavior
- **text**: `test_ledger_append.py` gains six cases, labelled verbatim as below, and every one passes:
  - `job: derived from provenance ref`
  - `job: flag overrides provenance`
  - `job: absent when no spec exists`
  - `job: legacy row without the key still validates`
  - `job: two jobs are distinguishable`
  - `job: schema keeps the field optional`
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/scripts/test_ledger_append.py | tee .agent-guild/state/log/ledger-suite.out > /dev/null; for L in "derived from provenance ref" "flag overrides provenance" "absent when no spec exists" "legacy row without the key still validates" "two jobs are distinguishable" "schema keeps the field optional"; do grep -qF "ok   job: $L" .agent-guild/state/log/ledger-suite.out || { echo "missing or failing case: job: $L" >&2; exit 1; }; done; echo "all six cases present and passing"'
- **severity**: major
- **failing example**: the behavior ships correct with no tests, so the next edit removes derivation and every suite stays green. The check names the first missing label on stderr, so the diagnosis says which case is absent rather than only that something is. A seventh `job:`-labelled case is fine and does not fail this clause; only a missing or failing one of these six does.
- **note**: this clause binds coverage, not correctness. Six cases that assert nothing would satisfy it, which is exactly why C-2 exists and is checked by a different agent reading different evidence.

### C-2: The field derives from the spec, and old rows stay legal
- **text**: `ledger-append.py` resolves `job` in this precedence and no other: `--job VALUE` when passed; otherwise the `ref` from `.agent-guild/state/spec.md`'s provenance header, resolved against the same cwd `DEFAULT_LEDGER` already assumes; otherwise the key is omitted entirely. `job` sits under `properties` in `.agent-guild/schemas/vendor-call.schema.json` typed `string` and NOT in `required`, so a row written before this change still validates (the issue's AC2). Absence is the only spelling of "unattributed"; the field is never written as `null`.
- **check**: checker-judgment: exercise the three precedence cases yourself in a scratch directory, reading the written line each time, rather than reading C-1's test assertions — a fixture `spec.md` with a known `ref` and no flag, the same fixture with the flag, and no `spec.md` at all. Then open the schema and confirm the three properties directly, and confirm no code path in `ledger-append.py` can emit `"job": null`.
- **severity**: major
- **failing example**: `--job` is the only source, so a crossing dispatched without that flag writes a row with no `job`, putting the requirement back in prose a courier has to remember — the #113 failure, in the file that fixes its sibling. Also failing: `job` added to `required`, invalidating all 22 rows in the skills repo's three archived ledgers; or derivation resolving the spec path relative to the script's own location, so it finds this repo's spec while appending to another project's ledger.

### C-3: A shared-contract change runs every suite that consumes it
- **text**: The schema is a shared contract, so verification runs the full consumer set green: `test_ledger_append.py`, `test_hooks.py`, and `scripts/build-plugin.py --check`. All three run every time and their statuses combine, so one red suite never hides the state of the other two. The generated trees under `plugin/`, `plugins/`, and `.claude/` are regenerated by `build-plugin.py`, never hand-edited, and `--check` reports no drift.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/scripts/test_ledger_append.py; a=$?; python3 .agent-guild/hooks/test_hooks.py; b=$?; python3 scripts/build-plugin.py --check; c=$?; exit $((a|b|c))'
- **severity**: blocker
- **failing example**: the schema and script are edited under `.agent-guild/` only, so `plugin/project-template/.agent-guild/scripts/ledger-append.py` still ships the old version and `--check` reports drift. This is the #43 failure repeating. Chaining the three with `&&` would also fail this clause: it hides `--check` behind any red suite, which is exactly the rework state where a checker needs all three.

### C-4: The backfill is attributed from evidence, validated, and changes nothing else
- **text**: Every one of the 18 rows in `~/repos/skills/.agent-guild/state/archive/2026-08-08-issue-27/log/vendor-calls.jsonl` carries the right `job`: rows 0-6 `kendrick/skills#17`, rows 7-10 `kendrick/skills#32`, rows 11-17 `kendrick/skills#27`. Row order is preserved, no other field on any row is altered, and every row validates against the amended schema in THIS repo.
- **check**: checker-judgment: re-derive the attribution before trusting the table, using the three discriminators that actually separate these rows — rows byte-identical (but for the added key) to the #32 archive's own `log/vendor-calls.jsonl` are #32's; `judgment`-tier stems for T-005 through T-007 exist only in the #17 archive, and the contiguous ascending run around them predates #32's intake at `2026-08-08T14:47:08Z`; and the remaining rows postdate #27's intake at `2026-08-08T19:28:16Z` while every earlier archive's own ledger already books its own crossings, so a row not booked elsewhere and stamped after that intake is #27's. (An earlier draft of this clause said `sonnet` and `opus` stems exist only in the #27 archive. T-004's checker showed that is false — `T-001-sonnet-r0-codex.json` and `T-002-opus-r0-codex.json` also sit under `2026-08-07/`, whose ledger books them at `04:18:46Z` and `04:33:26Z` — which is the same defect this clause's own failing example calls out for the tier segment.) Attribute the single row with an empty `artifacts` array by append position, a JSONL log being chronological in write time even where a stamped timestamp is wrong. Then diff the file against its git baseline and confirm the only per-line change is an added `job` key. Validate by importing `load_schema()` and `schema_violation()` from THIS repo's `.agent-guild/scripts/ledger-append.py` and walking every row — never the skills repo's frozen copy, whose schema has no `job` and would fail all 18.
- **severity**: blocker
- **failing example**: rows attributed by tier segment alone, which cannot separate rows 0-6 from rows 7-10 because `T-001-judgment-r0-codex.json` through `T-004-judgment-r0-codex.json` exist in both the #17 and #32 archives — 8 of 18 ambiguous, and exactly the ones the backfill exists to distinguish. Also failing: the artifacts-less row left unattributed, the four duplicated #32 rows deleted, or a wrong `started_at` "corrected" while adding `job`.

### C-5: The diff stays inside the job
- **text**: This repo's working tree changes only the paths this job owns: the schema, `ledger-append.py` and its test, the retrospective skill body under `guild-core/`, `docs/vendor-ledger.md`, the working-memory files, and the regenerated `plugin/`, `plugins/`, and `.claude/` trees. Everything the job writes under `.agent-guild/state/` is job bookkeeping the check already permits.
- **check**: .agent-guild/scripts/check-diff-scope.py .agent-guild/schemas/vendor-call.schema.json .agent-guild/scripts/ledger-append.py .agent-guild/scripts/test_ledger_append.py guild-core/workflows/retrospective/ docs/vendor-ledger.md _working-memory/ plugin/ plugins/ .claude/
- **severity**: major
- **failing example**: a worker fixes an unrelated lint complaint in `compose-brief.py` while it has the file open, or hand-edits `plugin/project-template/.agent-guild/scripts/ledger-append.py` rather than regenerating it. The check reads `git status --porcelain` and `git diff --name-only`, so a worker who committed would empty the set and pass having judged nothing — which is why no worker commits.

### C-6: The archive step says what moves
- **text**: Step 3 of `guild-core/workflows/retrospective/SKILL.md` enumerates the state directories that move into `archive/<date>/`, names `log/` among them, and says why the ledger belongs to the run's record rather than sitting outside it. The prose is instruction, not a passing mention.
- **check**: checker-judgment: read step 3; confirm it names `log/` in an enumeration of what moves and gives the reason, and that a reader following it would not leave the ledger behind.
- **severity**: minor
- **failing example**: the step still says "move this run's state" with no enumeration, or adds "(including logs)" as a parenthetical a reader skims past — which is how the #17 run's seven rows stayed live for the next job to append onto.

### C-7: The ref reader strips one matching pair
- **text**: The code that reads `ref:` out of the provenance header strips at most one matching quote pair (`val[0] == val[-1]`), the way `compose-brief.py` and `check-provenance.py` already do. It does not call `str.strip("'\"")`, which removes any number of quote characters from either end regardless of balance.
- **check**: checker-judgment: read the new reader; confirm the matched-pair form and the absence of a character-set strip.
- **severity**: minor
- **failing example**: `val.strip("'\"")`, adding a fourth instance of the defect already filed as #127 in the one file this job is touching for exactly this reason.

### C-8: The prose reads as written, not generated
- **text**: The new `job` description in the schema, `ledger-append.py`'s updated docstring, the rewritten retrospective step, the `docs/vendor-ledger.md` addition, and both commit messages pass a humanizer audit, with three house overrides that win wherever the audit conflicts with them: em dashes stay where they earn their place and chain directly to the text on both sides with no surrounding spaces; headings stay Title Case; and a list of exactly three is fine when three is the true count, the rule being against padding to three rather than against three. The first two are the project's standard at `_working-memory/conventions.md:65`. The commit messages are drafted into `.agent-guild/state/commit-message.md` — one for this repo, one for the skills repo, clearly separated — so they exist as an artifact before either commit does. Neither is hard-wrapped, and neither carries a `Co-Authored-By` trailer or any other coauthored attribution.
- **check**: checker-judgment: run the humanizer audit, with the three overrides above, over the five pieces this clause names — the schema's `job` description, `ledger-append.py`'s docstring, step 3 of the retrospective skill, the `docs/vendor-ledger.md` addition, and both messages in `commit-message.md`. Only `commit-message.md` is authored by the task that carries this clause; the other four it audits and may reword but never authors. Confirm no hard wraps in either message body and no attribution trailers.
- **severity**: minor
- **failing example**: a schema description reading "This field enhances the ledger's ability to facilitate robust attribution across job boundaries", or a commit body hard-wrapped at 72 columns. Also failing: no `commit-message.md`, which leaves the standing no-attribution rule with nothing checking it.

### C-9: The field is documented and the side findings are recorded
- **text**: Six files carry the change in prose. The schema's `job` description says what the field holds and that an absent key means unattributed. `ledger-append.py`'s docstring documents the three-step precedence. `docs/vendor-ledger.md` documents the field and its derivation. `_working-memory/dataContracts.md` carries the field in its ledger description, and `_working-memory/conventions.md` carries the rule that a run's archive includes `log/`. Three findings this job deliberately does not fix are written into `_working-memory/openQuestions.md`, so "reported" is an artifact rather than something someone remembers to mention: ten rows recording absolute artifact paths under a `/Users/karnett/` home that does not exist on this machine, one row's fractional-seconds `started_at`, and the four #32 rows that exist byte-identically in two archives.
- **check**: checker-judgment: read all six files, `_working-memory/openQuestions.md` included, and confirm each named fact is present and accurate.
- **severity**: major
- **failing example**: the field ships working and undocumented, so the next courier author learns about `job` by reading the script. Or a finding survives only in a GitHub comment, which is the same prose dependency C-2 exists to remove.

## Protected content

- none. This job ships no taglines, quotes, or legal copy; the one verbatim-fidelity requirement it does have (the 18 backfilled rows changing in exactly one way) is C-4's job, not a passages manifest's.

## Non-goals

- Committing, branching, and pushing. No worker commits; the orchestrator makes both commits after the job ends, on `fix/117-ledger-job-identity` here and on whatever branch the skills repo is on, using the messages C-8 requires. Nothing is pushed until the user asks.
- The GitHub close comment and its attribution table. Orchestrator wrap-up after the job, by a non-worker, on a repo nothing here may push to. Every fact it needs survives as a checked artifact: C-4's file, C-9's `openQuestions.md`.
- A `--validate PATH` mode on `ledger-append.py`. r1 ruled it over-reach and it is: the module already exposes what a validation pass needs, and a new flag with no test could satisfy its clause by exiting 0 unconditionally.
- The courier's local-time stamp, a defect in the writing agent rather than in the ledger format.
- Retries recording a single row (#116) and missing rows on the Claude lane (#99), both already filed.
- Moving the seven #17 rows into the #17 archive. They are backfilled where they sit.
- De-duplicating the four #32 rows that appear in two archives. C-9 records the finding; deleting a run's record is not this job's call.
- Fixing the absolute artifact paths or the fractional-seconds `started_at`. C-9 records both; neither gets repaired here.
- Refreshing the skills repo's frozen `.agent-guild/` payload so its own schema copy knows `job`.
