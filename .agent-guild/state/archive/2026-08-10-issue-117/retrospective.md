# Retrospective: #117 — a ledger row names the job it came from

7 tasks, 24 verdicts, 0 disputes, 0 escalations, 1 retry. 7 courier crossings, all 7 carrying the field this job added.

## Catches

Nine FAILs. Seven of them landed on the orchestrator's own work before a single worker ran, which is the number that says the most about this run.

**The auditor caught seven, across four CON rounds and five DEC rounds.** Three were factual errors in my own analysis, each verified before I accepted it:

- The attribution table in the spec claimed a row's artifact tier identifies its job. It does not: `T-001-judgment-r0-codex.json` through `T-004-judgment-r0-codex.json` exist in both the #17 and #32 archives, leaving 8 of 18 rows ambiguous — precisely the ones the backfill exists to separate.
- "Eleven rows carry `/Users/karnett/` paths." Ten. The wrong number had already propagated into the spec, the constitution, and a task file.
- A `check_method` instructing a checker to pass a task while reporting a `major` finding. `validate-verdict.py` refuses that verdict, and the rule refusing it is one I added to this repo three hours earlier closing #115. The decomposition would have shipped a task no checker could clear.

The other four were structural: a terminal task that wasn't terminal, so nothing regenerated after two later tasks edited build inputs; a voice-pass task that could break two clauses with every verdict green; a worker and its checker handed contradictory prose rubrics; and a `git diff` instruction that cannot distinguish "never written" from "written then deleted", because no worker commits and the whole job is one cumulative diff.

**A checker caught one, and the courier caught the same one.** T-006 wrote that the backfill "attributes both copies to `kendrick/skills#32`", when only the #27 archive's copies carry the key. Both readers found the same sentence at the same severity, the far side from inlined rows with no access to either repository.

**A checker caught one more that no clause asked for.** T-004's checker re-derived all 18 attributions, agreed with every one, then filed a `minor` against the rubric it had been given: the third discriminator, "sonnet and opus stems exist only in the #27 archive", is false — those stems also sit under `2026-08-07/`, whose own ledger books them. The attribution held on other evidence; its stated justification did not. That is a checker correcting the standard rather than the artifact, which is the behavior the org chart is supposed to produce and rarely does.

## Strain

One retry, on T-006, cleared in a single round on a one-sentence fix. No escalations. No disputes filed.

The strain in this job was not in the building. It was in Phase 0 and Phase 1: nine audit rounds against seven tasks. Every round found something real, and the last two DEC rounds each found defects that would have wedged a task mid-run. But the shape is worth naming honestly — the orchestrator wrote a plan, the auditor found it wrong four times in a row, and each correction cost a full opus round. #120 (no CON-audit round budget) and #122 (audits rebuild the reference implementation every round) are both open, and this run is evidence for both.

## Disputes

None filed. One disagreement, ruled directly per the dual-check contract.

T-003's courier returned FAIL where the in-family checker passed, on C-5's scope check. It had been handed `OK: 17 path(s) in scope` and refused to certify a list it could not see. I listed all 17 myself; every one is inside the allowlist, so the standard-stem PASS stands.

The courier was right about its own position and wrong to convert "I cannot verify this" into "this is false". Underneath the false disagreement sits a true defect that belongs to the tooling: **`check-diff-scope.py` reports a count, not the paths it approved**, so nothing downstream can audit its judgment — not a courier, not a verdict reader, not a person reading the log next week. The script knows every path it cleared and throws them away. Worth its own issue.

## Check-infra debt

No ERROR verdicts. Every check ran.

Two defects surfaced in the courier's own ledger writes during this run, neither in the ledger format this job repaired:

- One crossing appended its row to `.agent-guild/state/log/calls.jsonl` instead of `vendor-calls.jsonl`, orphaning a schema-valid row in a file nothing reads. Rescued by hand. `ledger-append.py` validates the line exhaustively and the destination not at all: `--ledger` takes any path and creates it on demand, so a path one character wrong produces a perfect line nobody will find.
- One row carries a `started_at` about 25 hours off from the crossing it stamps. #117 listed that as a non-goal, being a defect in the writing agent, but it is the same reason the archived rows were hard to attribute in the first place. The backfill had to place one row by append position for exactly this reason.

Both are recorded in `_working-memory/openQuestions.md` alongside the three archived-data findings.

## What the constitution missed

**The severity vocabulary held.** Every verdict in this run used `info` for a satisfied clause, and no pass carried a `blocker`. That contract is a day old (#115) and this is its first full exercise.

**C-5's failing example described something C-5 cannot report.** The clause names a hand-edited file under `plugin/` as a violation, but `plugin/` is on its own allowlist, so the scope check would pass it. The bar survives through C-3's drift check; the prose misleads a reader rather than a run. Flagged by the auditor at DEC r4 and left standing.

**Nothing enforced "no worker commits."** It is load-bearing for two clauses, and the protection is a HEAD-equality guard I added to a task's `check_method` after the auditor pointed out that a commit empties the working tree the scope check reads. It held, but only because every worker complied with prose. A hook could enforce it; none does.

**A task edited another task's deliverable and no clause noticed.** T-007 ran `build-plugin.py`, which is T-003's work. Its own task file forbade committing but never forbade regenerating, and the paths are inside C-5's allowlist, so no clause was violated. T-003 then found the tree already in sync and reported that honestly. Harmless here; a decomposition that leaves two tasks able to produce the same artifact is not harmless in general.

## For #34

Seven crossings, all judged and all recorded. Counting them honestly:

- **Two deterministic** (T-002, T-003) where the far side judged pre-collected exit codes. Agreement by construction, worth nothing as evidence, and the working memory already says so.
- **Five judgment** (T-001, T-004, T-005, T-006, T-007). Four agreed with zero unique findings. One — T-006 — is the first crossing in this evaluation where a real defect existed to be caught, and the far side caught it independently from inlined data.
- **Two unique findings, both in-family**, and both required something a courier structurally cannot have: T-004's rubric correction needed the archive tree, and T-007's em-dash finding needed `git diff` plus the house conventions file.

That last line is the one #34 should carry forward. On the unique-finding measure the evaluation actually rules on, this run reads 2–0 in favor of the in-family checker. But both unique findings came from repository access rather than model family, and a courier is blind by design. The measure may be reporting the evidence packet rather than the vendor.

171,118 input tokens and 3,581 output across the seven crossings.
