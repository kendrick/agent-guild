# Write the retrospective

A finished job leaves a full record in `.agent-guild/state/`, and the point of reading it back is the **catches**: every FAIL a checker turned back is a defect that would have shipped without the paired check. The retrospective counts them, finds where the work strained, and feeds the next job a sharper constitution and routing table.

## 1. Summarize the state

Run `summarize.py` (beside this file) over the run:

```
python3 <this-skill-directory>/summarize.py
```

It reports verdict counts (PASS/FAIL/ERROR), FAILs grouped by checker, retries and escalations per task, dispute outcomes, and whether the stop gate ever stalled. Read its output as the raw material; you supply the reading.

## 2. Write the report

Write `.agent-guild/state/retrospective.md` covering:
- **Catches**: how many FAILs, and what they were—the defects verification stopped.
- **Strain**: which tasks needed retries or escalated, and why. A task that climbed three tiers is a routing or spec problem, not just a hard task.
- **Disputes**: each one and how it was ruled. A checker overruled more than once points at a weak clause.
- **Check-infra debt**: ERROR verdicts mean a check couldn't run. Those checks need fixing before the next job leans on them.
- **What the constitution missed**: defects that slipped through, or clauses that turned out unfalsifiable in practice. This is the most valuable output—it's next job's Phase 0 input.
- **Weight against outcome**: the weight Phase 0 derived, the weight the job actually ran at if the user corrected it, the clause count the constitution reached, and the audit rounds each id spent. Recorded every job, those numbers are what let the derivation be checked against what actually happened instead of re-argued from memory next time. A correction matters most of all, since it's the derivation being wrong where someone caught it.
- **Budgets that ran out**: any audit that spent its rounds without a PASS and went to the user, what the outstanding findings were, and what the user did about it. A document that needed more rounds than its weight allowed is either a weight derived too light or a document that was too hard to specify, and the two want different fixes next time.

## 3. Offer to archive

The next job reuses `.agent-guild/state/`, so offer to move this run's record into `.agent-guild/state/archive/<date>/` (get the date from the environment) before the next constitution and task set land on top of it. Everything the run wrote goes:

- `tasks/`, `briefs/`, `verdicts/`, `disputes/`, `notes/`—the message bus.
- `log/`—dispatches, escalations, the stop gate's counter, and `vendor-calls.jsonl`.
- `spec.md`, `constitution.md`, and the `retrospective.md` you just wrote.

`log/` is the one that gets left behind, since it reads like plumbing rather than like part of the record. Check it last. It isn't plumbing: the vendor-call ledger inside it accounts for what every crossing cost and how the second opinions landed, and a ledger left live is one the next job appends to—two jobs' rows in one file, keyed by the same task ids.
