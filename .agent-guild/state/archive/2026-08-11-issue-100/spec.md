---
source: file
ref: /Users/k.arnett/.claude/plans/check-out-working-memory-then-ticklish-beaver.md
fetched_at: 2026-08-11T06:31:10Z
---

# Make the Mandatory Second Opinion Actually Dispatch (#100)

## Context

`.agent-guild/CLAUDE.md` declares the dual-check regime mandatory until #34 closes: once a task's checker of record returns, the orchestrator dispatches `checker-courier` on the same Task-ID, and the second opinion lands at a lane-suffixed verdict stem. Nothing in the kit checks that it happens.

The two live smoke runs on 2026-08-02 disagreed about whether it happens at all. The Codex host dispatched a courier after every checker unprompted; the Claude host ran C1 end to end, marked T-001 `complete`, and never dispatched one. No `vendor-calls.jsonl` row, no suffixed verdict, no complaint from any gate. `_working-memory/conventions.md:15` currently instructs humans to dispatch it by hand.

That lands on #34, which needs 10 dual-checked tasks to rule on the multi-provider bet and has 7 crossings, only because someone remembered. The intended outcome: the guild's own gates make the second opinion unskippable, so the sample grows from ordinary work instead of from vigilance.

## Design

One derived predicate — a **second-opinion debt** — read by two gates.

A debt exists for each verdict-of-record stem `T-NNN-<tier>-r<N>` when all of these hold:

- `state/verdicts/T-NNN-<tier>-r<N>.json` exists (task-shaped id, no lane suffix — auditor stems like `CON-audit-r0.md` never qualify)
- its `verdict` is not `blocked` (a record check that couldn't run has nothing to compare against, so a crossing would burn a vendor call producing nothing #34 can use; an unreadable verdict counts as owing, so the failure is loud)
- no lane sibling `…-r<N>-codex.json` or `…-r<N>-claude.json` exists
- no `state/exhausted/<lane>` sentinel for this host's lane
- no `state/verdicts/T-NNN-<tier>-r<N>-<lane>.denied` waiver

The three discharge routes cover every way a courier can end. Quota bails out to the sentinel with no verdict by contract. Auth failure, timeout, missing CLI, and twice-malformed output all become a schema-conforming `blocked` verdict at the lane stem (`guild-core/roles/checker-courier.md:35`), so the file exists either way. The `.denied` waiver covers the one remaining case — the host refuses the dispatch outright, as when the Claude package shipped without `checker-courier` registered (#94) — where no hook ever fires and nothing would otherwise be on the record.

## Changes

### 1. `.agent-guild/hooks/_lib.py` — the predicate

- `COURIER_LANES = ("codex", "claude")`, a named constant for the suffix set `scripts/classify-crossings.py:122` currently hardcodes.
- `second_opinion_debts(data=None)` → list of `(task_id, stem, lane)`. Lists `state/verdicts/` once, matches `^(T-\d+)-([a-z]+)-r(\d+)\.json$`, applies the discharge tests above. Uses the existing `courier_lane(data)` and `lane_exhausted(lane)`. Must never raise — same contract as `paused()`.

### 2. `.agent-guild/hooks/stop-gate.py` — the enforcement

This is the issue's own proposed home: a task whose checker of record returned with no second opinion landed and no denial on record is exactly the shape of unfinished the gate already refuses to end a turn on.

- Compute debts before the `if not tasks: return 0` early exit, so a task the orchestrator already marked `complete` still holds the turn open. This is what would have caught the Claude host's C1 run.
- Fold debts into the message body, naming the missing stem and the dispatch that settles it.
- Sharpen `_next_move`'s `checking` line: when that task's record verdict has landed but its lane sibling hasn't, say "dispatch checker-courier before completing" rather than the generic "act on the verdict". A well-behaved orchestrator then never reaches `complete` prematurely, and the debt list is the backstop for one that does.
- Extend the livelock digest to include the debt list. `_verdicts_landed()` already changes when a lane verdict or a `.denied` file appears, but the `exhausted/<lane>` sentinel lives outside `verdicts/` and would otherwise read as no progress.

### 3. `.agent-guild/hooks/dispatch-guard.py` — don't deadlock the fix

The checker branch at line 281 refuses any checker dispatch on a task that isn't `checking`. Without a change here, the stop gate demands a courier for a `complete` task and this gate refuses it — every run ends at STALLED.md.

Move the `checker-courier` branch ahead of the generic status check and let it run on any task carrying an outstanding debt, whatever its status. Defensible on the contract's own terms: the courier is explicitly not a second gate, so its dispatch legality needn't track the task's gate status. Every other courier condition (no model override, no `workspace-write`, lane not exhausted) stays exactly as it is.

### 4. The waiver

No new script. The orchestrator writes `state/verdicts/T-NNN-<tier>-rN-<lane>.denied` holding one line of reason. It sits where the verdict would have been, so the hole and its cause turn up in the same listing anyone auditing #34's corpus reads. Verified safe against the existing verdict-dir consumers: `retrospective/summarize.py:36` reads `.md` only, `classify-crossings.py:121` globs `*.json`.

### 5. Docs

- `.agent-guild/CLAUDE.md`, dual-check regime section: the second opinion is now gate-enforced, the three discharge routes, and what the `.denied` waiver is for. Add the waiver to the state map beside `exhausted/<lane>`.
- `_working-memory/conventions.md:15` — replace "Nothing enforces that regime yet (#100)" and its dispatch-by-hand instruction with what the gate now does.
- `_working-memory/openQuestions.md:19` — strike the #100 caveat from the #34 entry.
- `_working-memory/decisionLog.md` — append the decision (append-only; never edit past entries).
- `_working-memory/activeContext.md` — current focus and the retired risk.

### 6. Regenerate the published views

`.agent-guild/hooks/` and `guild-core/` are the sources; `plugin/`, `plugins/agent-guild/`, and `.claude/agents/` are generated. Run `python3 scripts/build-plugin.py`, then `--check` to confirm the trees match a fresh build.

## Tests

`.agent-guild/hooks/test_hooks.py` is a flat script of `check(label, cond, detail)` assertions grouped by hook. Add to the existing `stop-gate.py` and `dispatch-guard.py` sections, reusing `fresh_proj()`, `write_task()`, `write_verdict_json()`, and `run_hook()`.

Cases:

- record verdict, no lane sibling, task `checking` → blocks, message names the courier
- record verdict, no lane sibling, task **`complete`** → still blocks (the #100 regression itself)
- `-codex.json` sibling present → clean exit
- `-claude.json` sibling present → clean exit (host symmetry, done-when #3)
- `exhausted/codex` set → clean exit
- `.denied` waiver present → clean exit
- record verdict is `blocked` → clean exit, no debt
- `CON-audit-r0.json` alone → no debt (auditor stems are not checker stems)
- two retry rounds, r0 crossed and r1 not → debt on r1 only
- unreadable record verdict JSON → debt (fails loud)
- `PAUSED` set → clean exit, same as every other gate
- courier dispatch on a `complete` task with a debt → allowed
- courier dispatch on a `complete` task with no debt → still blocked on status
- `checker-judgment` on a `complete` task → still blocked (the widening is courier-only)

## Verification

```sh
python3 .agent-guild/hooks/test_hooks.py          # full hook suite, not just the new cases
python3 .agent-guild/hooks/test_codex_adapter.py  # Codex payloads reach the same predicate
python3 scripts/build-plugin.py --check           # generated trees match source
```

Then an end-to-end pass against the real gate, since the archived #117 run is a Codex-host corpus and the bug is Claude-host:

1. Seed a scratch project with one task at `checking` and a passing verdict of record.
2. Fire `stop-gate.py` with an empty payload — confirm exit 2 and the message names the missing `-codex` stem.
3. Flip the task to `complete`, fire again — confirm it still blocks. This is the exact state the 2026-08-02 Claude run ended in silently.
4. Fire `dispatch-guard.py` with a `checker-courier` Task dispatch against that `complete` task — confirm exit 0.
5. Drop in a `-codex.json` sibling, fire the stop gate — confirm exit 0.

## Notes

Prose bound for the commit message, the docs, and the working-memory entries goes through the `humanizer` skill before merge, per the user-level preference. Hook docstrings and code comments too, since they carry the reasoning a reader needs.

Not running this as a guild job (`/job 100`): the dual-check regime is what's being repaired, so driving the repair through it would both fight the broken machinery and put self-referential crossings into #34's sample.
