# Vendor Call Ledger

Every dispatch to an external vendor (a courier lane, once couriers exist) leaves one line in `.agent-guild/state/log/vendor-calls.jsonl`. The line records cost, latency, quota events, and artifact claims, so that data survives instead of vanishing into a courier's prose summary.

No courier hand-formats these lines. `.agent-guild/scripts/ledger-append.py` validates a line against `.agent-guild/schemas/vendor-call.schema.json` before writing it, then appends exactly one newline-terminated JSON line. This doc describes the contract on its own: a collector reading the ledger doesn't need to open the helper or any courier source to know what a line means.

## Fields

- `task_id` (string)—the guild task this vendor call served, e.g. `"T-007"`.
- `vendor` (string)—the external vendor dispatched to, e.g. `"codex"`.
- `model` (string)—the model the vendor ran, e.g. `"gpt-5.5"`.
- `started_at` (string, ISO-8601 UTC)—when the call started, e.g. `"2026-07-22T18:00:00Z"`.
- `duration_ms` (integer)—wall-clock duration of the call, in milliseconds.
- `exit_code` (integer)—the vendor process's exit code.
- `tokens_in` (number or null)—input tokens the vendor reported. Null means the vendor didn't report this figure, not that it was zero.
- `tokens_out` (number or null)—output tokens the vendor reported. Same null rule as `tokens_in`.
- `cost_usd` (number or null)—cost in US dollars the vendor reported. Same null rule.
- `brief_tokens` (number or null)—size of the brief handed to the vendor, in tokens, computed by the helper as `bytes(brief_file) // 4`. Null when no `--brief` was given.
- `tokenizer` (string or null)—`"heuristic-bytes/4"` whenever `brief_tokens` was computed; null exactly when `brief_tokens` is null. This is a byte-count heuristic from the standard library, not a real tokenizer: the field exists so a better estimator can replace it later without changing what the historical data means.
- `artifacts` (array of strings)—paths the courier verified on disk after the call. May be empty, but the field itself is always present.
- `quota_event` (boolean)—true when this call registered a vendor quota exhaustion.

The four nullable fields (`tokens_in`, `tokens_out`, `cost_usd`, `brief_tokens`) share one rule: null means unreported, never zero. A courier whose vendor reports no cost figure writes null. Writing `0.0` there would tell every downstream cost analysis that the call was free, which is worse than admitting the number is missing.

## Sample Line

```json
{"task_id": "T-007", "vendor": "codex", "model": "gpt-5.5", "started_at": "2026-07-22T18:00:00Z", "duration_ms": 41200, "exit_code": 0, "tokens_in": 18400, "tokens_out": 2100, "cost_usd": 0.31, "brief_tokens": 512, "tokenizer": "heuristic-bytes/4", "artifacts": ["scripts/foo.py"], "quota_event": false}
```

## Courier Obligations

These three rules are what make the ledger trustworthy. A collector can assume they hold; a courier that violates one has produced a ledger line that lies.

1. **Tokens and cost come from vendor-reported usage, or they're null.** Pull `tokens_in`, `tokens_out`, and `cost_usd` from the vendor's own accounting (`codex exec --json` usage events, for example), never from an estimate. When the vendor doesn't report a figure, write null. Guessing a number here is worse than admitting it's missing, because a guess looks like data.
2. **`artifacts[]` lists what the courier verified on disk, never what the vendor claimed.** A vendor's transcript saying "I wrote `foo.py`" is not evidence that `foo.py` exists. Only list a path after the courier has checked it's actually there.
3. **A quota exhaustion writes its ledger line before touching any exhaustion sentinel.** When a vendor call hits a quota limit, append the ledger line (with `quota_event: true`) first, then write the sentinel. That ordering means the sentinel is never orphaned: the ledger always has the record that explains why it exists.

## Writing a Line

```
.agent-guild/scripts/ledger-append.py \
    --task-id T-007 --vendor codex --model gpt-5.5 \
    --started-at 2026-07-22T18:00:00Z --duration-ms 41200 --exit-code 0 \
    --tokens-in 18400 --tokens-out 2100 --cost-usd 0.31 \
    --artifacts scripts/foo.py
```

Omit `--tokens-in`, `--tokens-out`, or `--cost-usd` for null. Pass `--brief PATH` to compute `brief_tokens` and record the tokenizer. Pass `--quota-event` for a quota exhaustion line. `--artifacts` is required but accepts zero paths for an empty list. `--ledger PATH` overrides the default `.agent-guild/state/log/vendor-calls.jsonl`, mainly for tests.

The helper validates before it writes, so invalid input exits nonzero with the file untouched. Appends never read, rewrite, or repair earlier lines: a malformed line from a killed courier stays exactly where it is, and the next append still lands cleanly after it.
