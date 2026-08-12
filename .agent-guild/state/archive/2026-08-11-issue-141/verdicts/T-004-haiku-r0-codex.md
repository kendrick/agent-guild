---
task: T-004
checker: checker-courier
vendor: openai
model: gpt-5.6-terra
verdict: PASS
checked_at: 2026-08-12T00:22:51Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-9 | info | The subject contains conventional-commit type `build` and scope `guild-plugin`. | `build(guild-plugin): regenerate trees after build-input edits` |
| C-9 | info | The body explains the synchronization constraint and why build outputs are committed with source edits. | “The generated trees stay in sync with their sources only when the build runs after each source edit; committing them together ensures later edits don't leave stale trees behind.” |
