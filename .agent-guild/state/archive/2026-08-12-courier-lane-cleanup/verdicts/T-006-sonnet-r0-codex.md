---
task: T-006
checker: checker-courier
vendor: openai
model: gpt-5.6-terra
verdict: BLOCKED
checked_at: 2026-08-12T07:14:32Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| external-lane | blocker | codex exec exited 1 before producing a verdict | stdout: {"type":"thread.started","thread_id":"019ff4d2-64b2-70d2-8538-a369ffeeb735"} {"type":"turn.started"} {"type":"error","message":"Selected model is at capacity. Please try a different model."} {"type":"turn.failed","error":{"message":"Selected model is at capacity. Please try a different model."}} stderr: Reading additional input from stdin... 2026-08-12T07:14:16.587337Z ERROR codex_models_manager::cache: failed to load models cache: missing field `base_instructions` at line 94 column 5 |
