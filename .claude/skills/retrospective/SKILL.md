---
name: retrospective
description: Phase 3 of a guild job. Read the run state and write .agent-guild/state/retrospective.md—what the checkers caught, where retries and escalations clustered, how disputes were ruled. Use at the end of a job, or when reviewing how a build went and what the constitution missed.
---

# Write the retrospective

A finished job leaves a full record in `.agent-guild/state/`, and the point of reading it back is the **catches**: every FAIL a checker turned back is a defect that would have shipped without the paired check. The retrospective counts them, finds where the work strained, and feeds the next job a sharper constitution and routing table.

## 1. Summarize the state

Run `summarize.py` (beside this file) over the run:

```
python3 .claude/skills/retrospective/summarize.py
```

It reports verdict counts (PASS/FAIL/ERROR), FAILs grouped by checker, retries and escalations per task, dispute outcomes, and whether the stop gate ever stalled. Read its output as the raw material; you supply the reading.

## 2. Write the report

Write `.agent-guild/state/retrospective.md` covering:
- **Catches**: how many FAILs, and what they were—the defects verification stopped.
- **Strain**: which tasks needed retries or escalated, and why. A task that climbed three tiers is a routing or spec problem, not just a hard task.
- **Disputes**: each one and how it was ruled. A checker overruled more than once points at a weak clause.
- **Check-infra debt**: ERROR verdicts mean a check couldn't run. Those checks need fixing before the next job leans on them.
- **What the constitution missed**: defects that slipped through, or clauses that turned out unfalsifiable in practice. This is the most valuable output—it's next job's Phase 0 input.

## 3. Offer to archive

The next job reuses `.agent-guild/state/`. Offer to move this run's state to `.agent-guild/state/archive/<date>/` (get the date from the environment) so the record survives without colliding with the next constitution and task set.
