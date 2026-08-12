---
task: T-003
checker: checker-courier
vendor: openai
model: gpt-5.6-terra
verdict: BLOCKED
checked_at: 2026-08-12T00:04:06Z
duration_ms: None
cost_usd: None
---

<!-- GENERATED FILE—do not hand-edit. Rendered by render-verdict.py
from the verdict JSON, the record of record. Edit the JSON and
re-render instead. -->

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| external-lane | blocker | codex structured output remained invalid after one retry: codex output checker was 'codex', expected 'checker-courier' | stdout: {"type":"thread.started","thread_id":"019ff348-5699-7540-be4d-2c139d2780b6"} {"type":"turn.started"} {"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"{\\"task_id\\":\\"T-003\\",\\"checker\\":\\"codex\\",\\"vendor\\":\\"openai\\",\\"model\\":\\"gpt-5\\",\\"verdict\\":\\"fail\\",\\"findings\\":[{\\"clause_id\\":\\"T-003\\",\\"severity\\":\\"major\\",\\"description\\":\\"Both passages overstate the effect of a re-dispatch because promote_crossing can promote an earlier matching unpromoted record even when the re-dispatch creates no new reservation.\\",\\"evidence\\":\\"reserve_crossing: returns False when verdict exists; promote_crossing: accepts any existing record whose task_id equals tid and sets promoted=True.\\"},{\\"clause_id\\":\\"T-003\\",\\"severity\\":\\"major\\",\\"description\\":\\"The wording “a stem that already carries a file is never reserved” is inaccurate without qualifying it as “no new reservation is created by that reserve_crossing call.”\\",\\"evidence\\":\\"Scenario steps 2 and 8: the stem already has an authorization record from the first dispatch, which the second return promotes.\\"}],\\"timestamp\\":\\"2026-08-11T00:00:00Z\\",\\"duration_ms\\":null,\\"cost_usd\\":null}"}} {"type":"turn.completed","usage":{"input_tokens":19123,"cached_input_tokens":15104,"cache_write_input_tokens":0,"output_tokens":416,"reasoning_output_tokens":183}} stderr: Reading additional input from stdin... output file: {"task_id":"T-003","checker":"codex","vendor":"openai","model":"gpt-5","verdict":"fail","findings":[{"clause_id":"T-003","severity":"major","description":"Both passages overstate the effect of a re-dispatch because promote_crossing can promote an earlier matching unpromoted record even when the re-dispatch creates no new reservation.","evidence":"reserve_crossing: returns False when verdict exists; promote_crossing: accepts any existing record whose task_id equals tid and sets promoted=True."},{"clause_id":"T-003","severity":"major","description":"The wording “a stem that already carries a file is never reserved” is inaccurate without qualifying it as “no new reservation is created by that reserve_crossing call.”","evidence":"Scenario steps 2 and 8: the stem already has an authorization record from the first dispatch, which the second return promotes."}],"timestamp":"2026-08-11T00:00:00Z","duration_ms":null,"cost_usd":null} |
| external-lane | info | courier runner: the far side echoed model='gpt-5'; the lane ran 'gpt-5.6-terra' (source: requested). The judgment below is the vendor's, unchanged. | raw response: .agent-guild/state/log/courier-raw/T-003-opus-r0-codex.jsonl |
