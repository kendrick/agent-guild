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
- **Outstanding crossings**: every stem whose second opinion was started and never landed, named one per line. A crossing no longer holds the turn open once a courier has been dispatched against it (#124), which is what stops one lane stalling a whole wave, and the cost of that is a crossing can now reach Phase 3 still open. Nothing else in the run will mention it. Recording the stem is what keeps the gap in #34's comparison data visible instead of reading as a crossing that agreed.
- **Weight against outcome**: the constitution's `**Job weight**:` line verbatim, since it carries the derivation and any correction the user made, plus the clause count the document actually reached and the audit rounds each id spent, counted off the `<Audit-ID>-r<N>` stems. Recorded every job, those numbers are what let the ceiling be checked against what happened instead of re-argued from memory. A user's correction matters most, since it's the derivation being wrong where somebody caught it.

## 3. Offer to archive

The next job reuses `.agent-guild/state/`, so offer to move this run's record into `.agent-guild/state/archive/<date>/` (get the date from the environment) before the next constitution and task set land on top of it. Everything the run wrote goes:

- `tasks/`, `briefs/`, `verdicts/`, `disputes/`, `notes/`—the message bus.
- `log/`—dispatches, escalations, the stop gate's counter, and `vendor-calls.jsonl`.
- `spec.md`, `constitution.md`, and the `retrospective.md` you just wrote.

`log/` is the one that gets left behind, since it reads like plumbing rather than like part of the record. Check it last. It isn't plumbing: the vendor-call ledger inside it accounts for what every crossing cost and how the second opinions landed, and a ledger left live is one the next job appends to—two jobs' rows in one file, keyed by the same task ids.
