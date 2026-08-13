# Courier Comparison

Every courier crossing gets a `## Courier comparison` block in its task file, filled in once the second opinion lands. Prose alone cannot be counted across repos, and a bare count cannot be audited, so each block leads with structured YAML and follows it with prose that names the clauses behind every number.

The schema was built for #34, which asked whether a checker from another model family catches what same-family checking misses. #34 closed on 2026-08-13 against `gpt-5.6-terra`: it does not, and the second opinion is opt-in from #167 on. The block stays because a crossing you do dispatch still has to be recorded somewhere the retrospective can read it, and because a future experiment on a different vendor should not have to invent this shape again.

This file is the schema of record. It exists because the schema drifted for months inside dispatch prompts and session-standing instructions, and the newest crossings ended up conforming to the oldest shape.

## The Block

````markdown
## Courier comparison

```yaml
repo: agent-guild | skills | dotfiles | …
job: 2026-08-12-courier-lane-cleanup
task: T-003
verdict_pair: [{of_record: T-003-sonnet-r0.json, lane: T-003-sonnet-r0-codex.json}]
clause_types_sampled: judgment | deterministic | mixed
brief_framing: confirm | attack | open | unknown | null
courier_outcome: pass | fail | blocked | denied
agreement_on_outcome: agree | disagree | null
disagreement_kind: substantive | evidence_packet | null
unique_courier: {defect: N, inference: N, evidence_quality: N, coverage: N}
unique_checker: N
unique_checker_access_derived: N
overlap: N
changed_verdict: yes | no
cost: {wall_s, tokens_in, tokens_cached, tokens_out, brief_tokens, vendor_calls}
```

Prose follows: which clause each unique finding came from, which cited clauses
were deterministic, and anything the numbers flatten.
````

## The Fields

**`repo`, `job`, `task`, and `verdict_pair`** identify the row. Inside one repo the file path already says all four, which is why the block went without them for months. That stops working the moment the corpus is pooled: #34 ruled across three repos at once, and its closure criteria asked for links to the verdict pairs, which no amount of prose supplies. `verdict_pair` is a list because a task that was crossed on two retry rounds carries two pairs, and `lane: null` records a crossing that never produced a far-side file. Take the filenames from the ledger's `artifacts` field rather than guessing at the stem.

**`clause_types_sampled`** is what the crossing's findings actually cite, not what the task's `clauses` field declares. Those diverge more often than you'd expect: a task citing two rubric clauses and two script clauses reads `mixed` by declaration while the crossing itself only ever engaged the rubrics. Record what happened.

**`brief_framing`** records what the brief asked the far side to do. `confirm` asks it to agree with the checker of record, `attack` asks it to find fault with that reasoning or argue the opposite case, `open` asks for a judgment with no thumb on the scale. Vary this deliberately and record it, because a difference in outcome cannot be attributed to the lane if the framing drifted underneath it. Prefer `attack` for judgment clauses; reserve `confirm` for when you specifically want an agreement rate and expect it to be high. `null` is for a crossing that was denied or died before any brief existed.

Record it live, from the dispatch you are about to send. It cannot be recovered afterward, and the sentence above about reading it back from a surviving brief was wrong: `compose-brief.py` emits a title, `## Constitution clauses`, and `## Spec excerpt`, and there is no framing anywhere in it. There never was. Framing reaches the vendor through the dispatch prompt, which nothing persists. So a brief sitting in the archive tells you nothing about how its crossing was framed, and `unknown` is the honest value for every crossing whose framing was not written down at the time—whether or not the brief survived. The seven `open` values in the #117 archive were read off surviving briefs on exactly that mistaken basis and have been corrected to `unknown`; their own inline comment already conceded the dispatch prompt was unrecoverable.

**`courier_outcome`** is the second opinion's own verdict. `denied` covers a lane refused before it ran, quota or otherwise.

**`agreement_on_outcome`** takes `null` when there is nothing to agree with, which is every `blocked` and `denied` crossing.

**`disagreement_kind`** is only meaningful when `agreement_on_outcome: disagree`, `null` otherwise. `substantive` is a real split on the merits. `evidence_packet` is the courier declining to certify something it was never shown, which looks identical in a count and means the opposite. Across the finished corpus, 13 of 16 disagreements were substantive and 3 were packet artifacts.

**`unique_courier`** counts findings only the courier raised, split four ways rather than counted once. A `defect` is a real problem in the artifact. An `inference` is a conclusion drawn from what was shown. `evidence_quality` names something missing or unverifiable in the packet. `coverage` is a clause or case nobody looked at. A lane that finds zero defects but keeps naming missing evidence is a different proposition from a lane that finds nothing, and one number erases that difference.

**`unique_checker`** and **`unique_checker_access_derived`** cover findings only the in-family checker raised, and how many of those came from *executing* something or reading across the repo rather than from being a different model. This split is the one that could invalidate #34's headline measure. The corpus is now fully classified: of 46 unique in-family findings across the 50 crossings that produced a judgment, 45 came from execution or repo-wide reading—planting fixtures and counting what fired, sweeping 47 comment blocks, rebuilding a scratch repo per case, reading past the diff. Exactly one did not. A courier is blind by design, so a unique-finding rate that does not separate these two is measuring tool access and calling it vendor diversity.

The predicate is mechanical enough to apply to an archive: a finding is access-derived when its evidence cites a repo path, a line number, or the output of something the checker ran, because the brief carries none of those. The last seventeen were classified that way in the #34 closeout sweep, on the observation that in each of those eight tasks *every* finding in the verdict of record rested on execution or a path the brief never inlined—so whichever subset was counted unique is wholly access-derived, without needing to identify which findings those were.

On a `blocked` or `denied` crossing the field is `null`, and that null means not applicable rather than not known. No far-side judgment exists, so every in-family finding is unique by default and the split says nothing about the lane. Exclude those crossings from any unique-finding rate for the same reason; their `unique_checker` is a count of the checker's whole output, not of anything the courier missed.

**`overlap`** counts findings both sides raised.

**`changed_verdict`** records whether the second opinion changed what happened to the task. It should almost always be `no`; the courier is comparison data, not a second gate.

**`cost`** is the price of the opinion, since #34 is a cost/benefit ruling and an opinion with no price attached cannot be weighed. `tokens_cached` comes from `cached_input_tokens` on the codex lane's `turn.completed` event and is deliberately not folded into `tokens_in`. Null means the vendor did not report it, never zero.

`vendor_calls` is the one field in the mapping that takes a real zero, and only on a denied crossing, where no call happened and the zero is a fact. Everything beside it stays null there—nothing ran, so nothing was measured, and a row of zeros drags the mean wall time and token cost of the lane down toward a crossing that never occurred. Where a ledger survives, `vendor_calls` is not a judgment call at all: count the rows carrying that `task_id`.

Expect that null most of the time, and know why before you read a run's costs as complete. Nothing on the path persists the figure: `_usage()` in `codex-courier.py` reads `input_tokens` and `output_tokens` and drops the rest, and `vendor-call.schema.json` has no `tokens_cached` field for the ledger to carry. The number survives only inside a retained raw stream, and retention defaults to `onissue`, so a crossing that goes cleanly leaves nothing behind. In the #141 run three of six crossings retained raw; the one that recorded `cached_input_tokens: 15104` is a crossing that blocked. So the field is reliably fillable for the crossings that went wrong and reliably empty for the ones that went right, which is backwards for costing a lane. Fill it when the raw is there and leave it null otherwise, but do not read a corpus of nulls as a lane that reports no cache.

## Filling It In

Read the two verdicts directly. Do not take either agent's summary of its own findings, and do not read the worker's notes—the whole point is that the comparison is derived from artifacts rather than self-reports.

Name the clause behind each unique finding in the prose, and say which cited clauses were deterministic. Deterministic clauses agree by construction: the courier is handed pre-run output and has no way to build the fixture that would falsify it, so a unique-finding rate measured over them is near zero by method rather than by evidence. That reaches #34's "close the multi-provider line" condition without testing the claim.

A `blocked` or `denied` crossing still gets a block, with its reason. Those are data too: a lane that cannot produce a verified crossing is itself an answer about the lane.

## One Vendor Model, All the Way Down

Every one of the 85 ledger rows in the three archived corpora records `model: gpt-5.6-terra`. Whatever #34 concludes, it concludes about one non-Claude model, not about cross-family checking in general. That belongs in the ruling as a stated limit on scope. It does not belong in the block—a field that holds the same value 69 times is noise, and the ledger already carries it per crossing for the day a second model appears.

## Don't Write the Ledger by Hand

Do not append to `vendor-calls.jsonl` by hand. Both lanes run through a script that appends exactly one row per crossing—`codex-courier.py` from a Claude host, `claude-courier.py` plus its parent from a Codex host—and a second manual append produces a duplicate row that inflates the cost side of the ruling. Read the row back to fill in `cost`; do not write it.

The same goes for the isolation and salvage rules that used to live in dispatch prompts. The runner runs the vendor from an isolated empty directory, and it refuses to read a verdict left behind by a process it killed. Neither is something a courier has to remember any more.

## What Changed, and When

The two access fields arrived on 2026-08-10, after a re-read of every archived comparison across agent-guild, skills, and dotfiles. Eleven tasks could not be classified at all, because nobody was tracking the distinction when those notes were written.

The `unknown` and `null` values were forced by the #100 archive: no brief survived those crossings, and a blocked crossing has no outcome to agree with. They were being improvised in place before they were written down here.

`tokens_cached` was recorded as unfillable, on the belief that the lane reported no cached-token figure. It does, on `turn.completed`. That note was stale rather than wrong at the time.

The provenance fields and the #34 closeout sweep landed on 2026-08-12, across all 69 blocks in the three repos. The sweep filled `vendor_calls` from the ledgers wherever one survived, classified the last seventeen unique in-family findings, normalized dotfiles' `n/a` spellings to `null`, and corrected the #117 framing values. Six blocks in the skills `2026-08-08-issue-17` archive still carry `unknown` costs and always will: that job kept no ledger, so there is nothing to read them out of.

Correcting that correction, from the #141 run: the lane reports the figure, and nothing keeps it. Both earlier notes were half right, and the half each one missed is the half that decides whether you can actually fill the field. Persisting it needs a `tokens_cached` in `vendor-call.schema.json` and a `_usage()` that reads it, neither of which exists yet.
