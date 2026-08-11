# Commit Messages for #117

Two commits in two repositories. Copy each body verbatim: neither is hard-wrapped, and neither ends with a coauthor or other attribution trailer.

## This Repo (`agent-guild`)

Branch `fix/117-ledger-job-identity`. Covers the schema, `ledger-append.py` and its tests, the retrospective's archive step, `docs/vendor-ledger.md`, working memory, and the regenerated package trees.

```
fix(ledger): a vendor-call row names the job it came from (#117)

Every guild job numbers its tasks from `T-001` and `.agent-guild/state/` is wiped between runs, so a task id is unique inside a job and meaningless across jobs. The ledger keyed on `task_id` and recorded nothing about origin, and artifact paths didn't separate the rows either: two different runs both point at a byte-identical `verdicts/T-001-judgment-r0-codex.json`. So when the #17 run's `log/` stayed live and a later job appended on top of it, the only thing standing between two runs' rows was a timestamp—and one of those timestamps was wrong. #34 is a cost/benefit ruling on the courier lane and this ledger is the evidence it rules on, so rows nobody can attribute are that evaluation losing its data.

`job` holds the run's provenance `ref`, `kendrick/skills#17` and the like. `ledger-append.py` derives it rather than taking it on trust: `--job VALUE` when passed, otherwise the `ref` from `.agent-guild/state/spec.md`'s provenance header, otherwise the key is left out entirely. A required fact that lives in prose for the courier to remember holds up right until someone else runs the crossing, which is the lesson #113 just charged us for. The spec path resolves against the working directory and pointedly not the script's own location, since this script gets copied into other projects and would otherwise read this repo's spec while appending to theirs.

In the schema `job` sits under `properties` and not in `required`, so every row written before today still validates. Absence is the only spelling of unattributed: the field is never written as null, so one state has one encoding.

Step 3 of the retrospective skill now enumerates what moves into `archive/<date>/` and names `log/` among them, with the reason attached—the ledger belongs to the record it documents, not to the directory the next job inherits. Leaving it behind is how the collision happened. The 18 rows already on disk are backfilled in a separate commit in the skills repo.
```

## The Skills Repo (`~/repos/skills`)

Whatever branch that repo is on. One file changes: `.agent-guild/state/archive/2026-08-08-issue-27/log/vendor-calls.jsonl`.

```
fix(ledger): attribute 18 archived rows to the jobs that made them (#117)

`.agent-guild/state/archive/2026-08-08-issue-27/log/vendor-calls.jsonl` holds 18 rows from three jobs rather than one: seven from #17, whose `log/` was never archived with the rest of that run; four from #32 that also sit in that run's own archive; and seven of #27's own. Each row now carries the `job` key that agent-guild's ledger writes going forward, so the #34 evaluation can group these crossings by the run that produced them instead of by a task id that restarts at `T-001` every job.

Attribution came from the rows, not from the clock. Two of the 18 carry a `started_at` that contradicts the job their own artifacts name: row 15 is stamped `2026-08-08T00:00:00Z` while pointing at `T-006-sonnet-r0-codex.json`, a verdict stem only #27's archive holds, and row 17 is stamped inside #17's window but has no artifacts at all. What places the rows instead is where their verdicts live. Four were byte-identical to the whole of #32's own archived ledger before this change. Seven form one ascending run around the `judgment` stems for T-005 through T-007, which exist only under #17, and that run closes before #32's intake at `2026-08-08T14:47:08Z`. The rest postdate #27's intake and are booked in no earlier archive. Row 17, with nothing to match on, takes #27 by append position: a JSONL log is chronological in write time even where a stamp is wrong.

Nothing else moved. Row order is unchanged and the only per-line difference is the added key. The four rows that exist in two archives stay in both, since recording that is #117's job and deleting a run's record isn't. This project's `.agent-guild/` payload froze at install and its schema copy has no `job` yet, so the rows were validated against the amended schema over in agent-guild rather than against the one sitting here.
```
