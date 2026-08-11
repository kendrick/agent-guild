# Courier Comparison

Every courier crossing gets a `## Courier comparison` block in its task file, filled in once the second opinion lands. The block is the unit of evidence #34 rules on: whether a checker from another model family catches what same-family checking misses. Prose alone cannot be counted across repos, and a bare count cannot be audited, so each block leads with structured YAML and follows it with prose that names the clauses behind every number.

This file is the schema of record. It exists because the schema drifted for months inside dispatch prompts and session-standing instructions, and the newest crossings ended up conforming to the oldest shape.

## The Block

````markdown
## Courier comparison

```yaml
clause_types_sampled: judgment | deterministic | mixed
brief_framing: confirm | attack | open | unknown
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

**`clause_types_sampled`** is what the crossing's findings actually cite, not what the task's `clauses` field declares. Those diverge more often than you'd expect: a task citing two rubric clauses and two script clauses reads `mixed` by declaration while the crossing itself only ever engaged the rubrics. Record what happened.

**`brief_framing`** records what the brief asked the far side to do. `confirm` asks it to agree with the checker of record, `attack` asks it to find fault with that reasoning or argue the opposite case, `open` asks for a judgment with no thumb on the scale. Vary this deliberately and record it, because a difference in outcome cannot be attributed to the lane if the framing drifted underneath it. Prefer `attack` for judgment clauses; reserve `confirm` for when you specifically want an agreement rate and expect it to be high. `unknown` is for reading a crossing back from an archive where the brief did not survive.

**`courier_outcome`** is the second opinion's own verdict. `denied` covers a lane refused before it ran, quota or otherwise.

**`agreement_on_outcome`** takes `null` when there is nothing to agree with, which is every `blocked` and `denied` crossing.

**`disagreement_kind`** is only meaningful when `agreement_on_outcome: disagree`, `null` otherwise. `substantive` is a real split on the merits. `evidence_packet` is the courier declining to certify something it was never shown, which looks identical in a count and means the opposite. Across the corpus so far, 11 of 12 disagreements were substantive and one was a packet artifact.

**`unique_courier`** counts findings only the courier raised, split four ways rather than counted once. A `defect` is a real problem in the artifact. An `inference` is a conclusion drawn from what was shown. `evidence_quality` names something missing or unverifiable in the packet. `coverage` is a clause or case nobody looked at. A lane that finds zero defects but keeps naming missing evidence is a different proposition from a lane that finds nothing, and one number erases that difference.

**`unique_checker`** and **`unique_checker_access_derived`** cover findings only the in-family checker raised, and how many of those came from *executing* something or reading across the repo rather than from being a different model. This split is the one that could invalidate #34's headline measure. Of 34 unique in-family findings classified so far, every classifiable one came from execution or repo-wide reading: planting fixtures and counting what fired, sweeping 47 comment blocks, reading past the diff. Not one came from model family. A courier is blind by design, so a unique-finding rate that does not separate these two is measuring tool access and calling it vendor diversity.

**`overlap`** counts findings both sides raised.

**`changed_verdict`** records whether the second opinion changed what happened to the task. It should almost always be `no`; the courier is comparison data, not a second gate.

**`cost`** is the price of the opinion, since #34 is a cost/benefit ruling and an opinion with no price attached cannot be weighed. `tokens_cached` comes from `cached_input_tokens` on the codex lane's `turn.completed` event and is deliberately not folded into `tokens_in`. Null means the vendor did not report it, never zero.

## Filling It In

Read the two verdicts directly. Do not take either agent's summary of its own findings, and do not read the worker's notes—the whole point is that the comparison is derived from artifacts rather than self-reports.

Name the clause behind each unique finding in the prose, and say which cited clauses were deterministic. Deterministic clauses agree by construction: the courier is handed pre-run output and has no way to build the fixture that would falsify it, so a unique-finding rate measured over them is near zero by method rather than by evidence. That reaches #34's "close the multi-provider line" condition without testing the claim.

A `blocked` or `denied` crossing still gets a block, with its reason. Those are data too: a lane that cannot produce a verified crossing is itself an answer about the lane.

## Don't Write the Ledger by Hand

Do not append to `vendor-calls.jsonl` by hand. Both lanes run through a script that appends exactly one row per crossing—`codex-courier.py` from a Claude host, `claude-courier.py` plus its parent from a Codex host—and a second manual append produces a duplicate row that inflates the cost side of the ruling. Read the row back to fill in `cost`; do not write it.

The same goes for the isolation and salvage rules that used to live in dispatch prompts. The runner runs the vendor from an isolated empty directory, and it refuses to read a verdict left behind by a process it killed. Neither is something a courier has to remember any more.

## What Changed, and When

The two access fields arrived on 2026-08-10, after a re-read of every archived comparison across agent-guild, skills, and dotfiles. Eleven tasks could not be classified at all, because nobody was tracking the distinction when those notes were written.

The `unknown` and `null` values were forced by the #100 archive: no brief survived those crossings, and a blocked crossing has no outcome to agree with. They were being improvised in place before they were written down here.

`tokens_cached` was recorded as unfillable, on the belief that the lane reported no cached-token figure. It does, on `turn.completed`. That note was stale rather than wrong at the time.
