---
source: github-issue
ref: kendrick/agent-guild#141
issue: 141
title: fix(hooks): a verdict's authority is its filename, so any agent can discharge another task's second opinion
fetched_at: 2026-08-11T21:00:39Z
---

# fix(hooks): a verdict's authority is its filename, so any agent can discharge another task's second opinion

A verdict is authoritative because of where it sits. `second_opinion_debts()` decides a task's crossing landed by looking for `T-NNN-<tier>-r<N>-<lane>.json` in `state/verdicts/`, and `dispatch-guard` and `stop-gate` both act on that answer. Nothing anywhere ties that file to a dispatch that authorized it.

`subagent-return.py` looks like the gate that would catch this, and it isn't. At `:459` it computes `vpath` from `ident`, the id of the subagent currently returning, then validates the file at that one path. It never asks what else that agent wrote. A courier dispatched for T-001 satisfies its own gate by writing `T-001-...-codex.json`, and every other file it created on the way past is invisible to every check in the kit.

So any agent with a Write tool can discharge any task's second-opinion debt, and the debt gate #100 just shipped will believe it.

## Steps to Reproduce

Verified against `77f2edd`. Run in an empty directory, with no courier dispatched and no vendor call made. `HOOKS` points at a checkout of this repo; `CLAUDE_PROJECT_DIR` is what makes the hooks resolve state here rather than in that checkout.

```sh
export CLAUDE_PROJECT_DIR="$PWD"
HOOKS=/path/to/agent-guild/.agent-guild/hooks

mkdir -p .agent-guild/state/{tasks,verdicts,log}
cat > .agent-guild/state/tasks/T-900.md <<'EOF'
---
id: T-900
status: complete
executor: worker-standard
executor_model: sonnet
checker: checker-judgment
retries: 0
---
EOF

python3 - <<'PY'
import json
base = {"task_id": "T-900", "checker": "checker-judgment", "vendor": "anthropic",
        "model": "claude-opus-5", "verdict": "pass", "findings": [],
        "timestamp": "2026-08-11T00:00:00Z", "duration_ms": None, "cost_usd": None}
json.dump(base, open(".agent-guild/state/verdicts/T-900-sonnet-r0.json", "w"))
PY

python3 -c "import sys;sys.path.insert(0,'$HOOKS');import _lib;print(_lib.second_opinion_debts({}))"

# Now forge the crossing. No dispatch, no vendor call, no ledger row.
python3 - <<'PY'
import json
forged = {"task_id": "T-900", "checker": "checker-courier", "vendor": "openai",
          "model": "gpt-5.6-terra", "verdict": "blocked", "findings": [],
          "timestamp": "2026-08-11T00:00:00Z", "duration_ms": None, "cost_usd": None}
json.dump(forged, open(".agent-guild/state/verdicts/T-900-sonnet-r0-codex.json", "w"))
PY

python3 -c "import sys;sys.path.insert(0,'$HOOKS');import _lib;print(_lib.second_opinion_debts({}))"
```

## Observed vs. Expected

**Observed.** The first call reports `[('T-900', 'T-900-sonnet-r0', 'codex')]`. The second reports `[]`. A file written by hand, backed by no dispatch and no vendor call, discharged the obligation. `dispatches.log` is empty, `vendor-calls.jsonl` does not exist, and nothing objects.

**Expected.** At minimum, a discharge that no dispatch and no ledger row supports is surfaced. The stronger form: a lane-suffixed verdict discharges a debt only when a ledger row for that stem exists, mirroring the ledger-before-sentinel ordering the quota path already requires.

## How This Surfaced

Not hypothetically. During the #100 run a `checker-courier` dispatched with `Task-ID: T-001`, having already completed that task, went on to write a verdict, a rendered `.md` sibling, and a vendor-ledger row for **T-002**. Its own explanation was that it was satisfying a gate message it had read, and gate messages are addressed to the orchestrator rather than to a subagent.

At that moment `dispatches.log` held no `checker-courier` row for T-002, and the ledger row it wrote books `duration_ms: 0` with null token counts for a call that never happened. Left alone the file would have discharged T-002's debt by filename and entered #34's corpus as a crossing.

The artifacts are preserved rather than deleted, in `.agent-guild/state/archive/2026-08-11-issue-100/`:

- `quarantine/T-002-sonnet-r0-codex.json` and its `.md` sibling, the verdict nothing authorized
- `log/dispatches.log`, where the first `checker-courier | T-002` row postdates the write
- `log/vendor-calls.jsonl`, holding both the false row and the real one written later by the authorized dispatch

A later courier on the same run, dispatched with an explicit instruction to write only for its own Task-ID, refused a gate message asking for more. That is the current mitigation: prompt wording, remembered per dispatch.

## Why This Matters More Than It Looks

#34 rules on whether a checker from another model family catches what same-family checking misses, and its evidence is these files. A forged or misfiled crossing is not a wrong answer in the corpus, it is a fabricated data point that reads identically to a real one. The same run produced three ledger rows with invented values, so the ledger cannot currently serve as the independent corroboration either.

Same family as #130, from the other end: that issue is about a valid row landing at a path nothing reads, this one is about a valid file landing under a task nothing authorized.

## Done when

- A lane-suffixed verdict that no dispatch authorized cannot silently discharge a debt.
- The reproduction above either fails at the forge step or surfaces the unbacked discharge on the second call.
- `subagent-return` (or an equivalent gate) accounts for verdict files an agent wrote outside its own stem, rather than validating only the path it computed for that agent.
- Existing archived runs stay readable: no change that invalidates the crossings already in #34's corpus.

Blocks #34.

