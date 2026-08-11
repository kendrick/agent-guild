---
source: file
ref: /Users/k.arnett/.claude/plans/lets-fix-gh-issue-tidy-cook.md
fetched_at: 2026-08-10T23:21:08Z
---

# Fix #117 — a ledger row names the job it came from

## Context

Every guild job numbers tasks from `T-001` and `.agent-guild/state/` is wiped between runs, so a task id is unique inside a job and meaningless across jobs. The vendor-call ledger keys on `task_id` and records nothing about which job produced the row. Artifact paths don't disambiguate either, since both runs point at the byte-identical `verdicts/T-001-judgment-r0-codex.json`.

#34 is a cost/benefit ruling on the courier lane and this ledger is the evidence it rules on, so unattributable rows are the evaluation losing its data.

**What changed since the issue was filed.** The seven `#17` rows are no longer in a live ledger. A later archive step swept them into `~/repos/skills/.agent-guild/state/archive/2026-08-08-issue-27/log/vendor-calls.jsonl`, which now holds 18 rows from three jobs: 7 from #17, 4 from #32 that are byte-identical to the ones in the #32 archive, and 7 of #27's own. This repo has no ledger rows at all, live or archived. So the backfill target is one file in the skills repo, not the live log the issue describes.

## The job field

`job` holds the spec's provenance `ref`, e.g. `kendrick/skills#17`. All three archived specs carry one, so the value already exists for every job that came through intake.

`ledger-append.py` derives it rather than taking it on trust:

1. `--job VALUE` if given. Exists for backfill and tests, not for routine use.
2. Otherwise read `.agent-guild/state/spec.md`'s provenance header and take `ref`. Same cwd assumption `DEFAULT_LEDGER` already makes, so no new fragility.
3. Otherwise omit the key.

Deriving beats a flag the courier has to remember, which is the lesson #113 just charged us for: a required fact that lives in prose works until someone else runs the crossing. A job authored through the constitution interview alone has no provenance header and writes no `job`, which is the honest answer and a detectable gap rather than a fabricated one.

Schema: `job` is `{"type": "string"}` under `properties`, deliberately **not** in `required`. That is what keeps every row already written legal (AC2). Absence means unattributed; there is no null spelling, so one state has one encoding. `vendor-call.schema.json` is never passed to a vendor as a structured-output schema, unlike `verdict.schema.json`, so the all-keys-required constraint that forced nullable typing there doesn't apply.

While stripping the `ref:` value, strip one matching quote pair rather than calling `str.strip("'\"")` — the greedy form is #127, and this script shouldn't add a fourth instance of it.

## Files

- [.agent-guild/schemas/vendor-call.schema.json](.agent-guild/schemas/vendor-call.schema.json) — the new property, plus a description saying what absence means
- [.agent-guild/scripts/ledger-append.py](.agent-guild/scripts/ledger-append.py) — `--job`, a small `derive_job()` reading the provenance header, docstring
- [.agent-guild/scripts/test_ledger_append.py](.agent-guild/scripts/test_ledger_append.py) — new cases (below)
- [guild-core/workflows/retrospective/SKILL.md](guild-core/workflows/retrospective/SKILL.md) — step 3 names `log/` explicitly
- [docs/vendor-ledger.md](docs/vendor-ledger.md) — the field and how it's derived
- Generated mirrors under `plugin/`, `plugins/`, `.claude/` — `scripts/build-plugin.py` regenerates all of them; the issue is right that the script lives in three trees and the skill in four, and right that editing one ships broken

## The archive step

Step 3 currently says to "move this run's state to `.agent-guild/state/archive/<date>/`" and never enumerates what that includes, which is how `log/` got left behind for the #17 run and how the next job appended on top of its rows. It will name the directories that move, `log/` among them, and say why: the ledger is part of a run's record, not machine plumbing that lives outside it.

## Backfill

One file: `~/repos/skills/.agent-guild/state/archive/2026-08-08-issue-27/log/vendor-calls.jsonl`. Each of the 18 rows gets `job` added in place, nothing else touched, row order preserved.

Attribution comes from evidence, not from the clock, because two rows carry timestamps that contradict their own job. Each row's artifact path names a verdict stem whose **tier** segment appears in exactly one archive:

| rows | artifact tier | archive holding those verdicts | job |
| --- | --- | --- | --- |
| 0–6 | `judgment`, T-001…T-007 | `2026-08-08-issue-17` (holds all seven) | `kendrick/skills#17` |
| 7–10 | `judgment`, T-001…T-004 | `2026-08-08-issue-32`, whose own ledger holds these four byte-identically | `kendrick/skills#32` |
| 11–16 | `sonnet` / `opus` | `2026-08-08-issue-27`, the only archive with those tiers | `kendrick/skills#27` |

Row 17 has an empty `artifacts` array (a timeout, `exit_code: 143`) and a timestamp of `2026-08-08T02:59:53Z` that would place it in #17's window. It gets `kendrick/skills#27` on append order: a JSONL append log is chronological in *write* time even when a stamped timestamp is wrong, and it sits among #27's rows. Row 15 is the same story with evidence to spare — stamped `2026-08-08T00:00:00Z`, but its artifact is `T-006-sonnet-r0-codex.json`, a stem only #27's archive holds.

The four duplicated #32 rows stay where they are, per the issue's instruction to backfill in place. I'll note the duplication in the close comment as worth its own issue rather than quietly deleting a run's record.

Two things I found while attributing, both out of scope and both worth reporting rather than fixing here: ten of the 18 rows record absolute artifact paths under `/Users/karnett/`, a username that doesn't exist on this machine, so paths the courier "verified on disk" don't resolve. And row 2's `started_at` carries fractional seconds while every other row doesn't.

The skills repo's `.agent-guild/` payload is frozen at install, so its own copy of the schema won't know `job` until that project's payload is refreshed. I'll validate the backfilled rows against this repo's amended schema and say so plainly rather than implying they pass over there.

## Verification

```sh
python3 .agent-guild/scripts/test_ledger_append.py
python3 .agent-guild/hooks/test_hooks.py
python3 scripts/build-plugin.py && python3 scripts/build-plugin.py --check
```

New coverage in `test_ledger_append.py`: `job` derived from a fixture `spec.md`; `--job` overriding derivation; the key absent when no spec exists; a row written before this change (no `job`) still validating; and the issue's own scenario, two rows sharing `task_id: T-001` from different jobs, distinguishable without reading timestamps.

Then the issue's reproduction verbatim, which should now yield two rows a reader can attribute, and a validation pass over all 18 backfilled rows.

## Wrap-up

- Branch `fix/117-ledger-job-identity` here; one commit. The skills-repo backfill is a separate commit in that repo. Neither pushed unless you say so.
- Humanizer pass on the commit messages, the schema description, and the retrospective step's new prose.
- Working memory: `dataContracts.md` describes the ledger and needs the field; `conventions.md` gets the archive-includes-`log/` rule, since leaving it behind is what let the collision happen.
- Close #117 with the attribution table and the two out-of-scope findings named.
