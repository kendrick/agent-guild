---
task: T-005
checker: checker-judgment
vendor: anthropic
model: claude-opus-5[1m]
verdict: PASS
checked_at: 2026-08-11T01:08:37Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-6 | info | Step 3 enumerates what moves as a three-bullet list under the instruction "Everything the run wrote goes:", and `log/` is its own bullet naming its contents rather than a parenthetical aside. | guild-core/workflows/retrospective/SKILL.md:26-30 — "Everything the run wrote goes:" / "- `tasks/`, `briefs/`, `verdicts/`, `disputes/`, `notes/`—the message bus." / "- `log/`—dispatches, escalations, the stop gate's counter, and `vendor-calls.jsonl`." / "- `spec.md`, `constitution.md`, and the `retrospective.md` you just wrote." The six state directories the spec names (tasks/, briefs/, verdicts/, disputes/, notes/, log/) are all present, plus the three files. |
| C-6 | info | The reason given is the mechanism, not an assertion of importance: the step states that a live ledger is one the next job appends to, and names the resulting corruption (two jobs' rows in one file under the same task ids). | guild-core/workflows/retrospective/SKILL.md:32 — "Check `log/` last, since it's the one that gets left behind: it reads like plumbing rather than like part of the record. But the vendor-call ledger inside it accounts for what every crossing cost and how the second opinions landed, and a ledger left live is one the next job appends to—two jobs' rows in one file, keyed by the same task ids." |
| C-6 | info | A reader following the step would not leave the ledger behind: the enumeration is checkable item by item, and the closing paragraph directs an explicit last pass over `log/` naming it as the one that gets dropped. | guild-core/workflows/retrospective/SKILL.md:26-32. The prose is imperative ("Everything the run wrote goes:", "Check `log/` last"), replacing the prior text which git shows as the single sentence "Offer to move this run's state to `.agent-guild/state/archive/<date>/` ... so the record survives without colliding with the next constitution and task set." (git diff, guild-core/workflows/retrospective/SKILL.md, -1/+7) |
| C-6 | info | The edit landed in the authored source under `guild-core/` that C-6 names; the three generated copies are untouched and still carry the pre-change sentence, so a later regeneration task remains the thing that updates them. | `git status --porcelain` lists only .agent-guild/schemas/vendor-call.schema.json, .agent-guild/scripts/ledger-append.py, .agent-guild/scripts/test_ledger_append.py, guild-core/workflows/retrospective/SKILL.md. `git status --porcelain .claude plugin plugins` returns empty. Grep of .claude/skills/retrospective/SKILL.md, plugin/skills/retrospective/SKILL.md, plugins/agent-guild/skills/retrospective/SKILL.md all show line 31 unchanged: "The next job reuses `.agent-guild/state/`. Offer to move this run's state to `.agent-guild/state/archive/<date>/` (get the date from the environment) so the record survives without colliding with the next constitution and task set." |
