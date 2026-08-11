## T-001

Add the second-opinion debt predicate to `_lib.py`

The dual-check regime says every checker of record gets a courier crossing, but nothing checked that it happened: a Claude host ran a task to `complete` on 2026-08-02 with no crossing, and no gate objected. `second_opinion_debts()` is the predicate two gates (T-002) will read to close that hole. It reports which verdicts of record still owe a courier opinion, discharging on a lane sibling from either lane, the quota sentinel, an orchestrator waiver, or a blocked in-family verdict. A record it can't parse only rules out that last route—the lane-sibling, sentinel, and waiver routes still discharge it, because a lane sibling is exactly the file a courier writes, and refusing to check for one before declaring a record corrupt would leave a debt no future dispatch could ever clear.

This task only adds the function and the `COURIER_LANES` constant it shares with future callers. Nothing calls it yet: wiring it into `stop-gate.py` and `dispatch-guard.py` is T-002, so this change can't alter any gate's behavior on its own.

Regenerated `plugin/` and `plugins/agent-guild/` from the edited hooks so the shipped trees don't drift from `.agent-guild/hooks/`.

## T-002

Wire the second-opinion debt into the stop gate and dispatch guard

T-001 added `second_opinion_debts()` to `_lib.py`, but nothing called it, so the dual-check regime stayed contract, not code: a Claude host reached `complete` on 2026-08-02 with no courier crossing, and no gate said anything. This task wires the predicate into the two gates that can actually catch that gap.

`stop-gate.py` now computes debts before its "no open tasks" early exit. That exit drops terminal tasks, so without this change a completed task's outstanding debt stays invisible—exactly the 2026-08-02 failure. The block message names the missing lane-suffixed verdict file and points at `checker-courier` as the dispatch that writes it. The checking-status next-move line switches from the generic "act on the verdict" to "dispatch the courier" once a task's checker of record has landed but its lane sibling hasn't. Debts are folded into the livelock digest too, so an `exhausted/<lane>` sentinel appearing between two otherwise-identical blocks reads as progress instead of a third identical strike.

`dispatch-guard.py` lets a courier dispatch through on a debt-bearing task whatever its status, including rework, which is where a FAIL verdict leaves a task with its debt still standing. The widening only touches `checker-courier` and only fires when a debt is actually outstanding; every other courier condition—no model override, no workspace-write or danger-full-access, no exhausted lane—still applies exactly as before.

Both gates land together in this one change on purpose: a stop gate demanding a courier while the dispatch guard still refuses one on status is a deadlock nothing recovers from.

## T-003

Add fixtures for the debt gate, so it can't regress silently again

T-001 added `second_opinion_debts()` and T-002 wired it into `stop-gate.py` and `dispatch-guard.py`, but nothing exercised any of it. The dual-check regime was enforced in code by then but not proven in tests, the same gap that let a Claude host reach `complete` on 2026-08-02 with no courier crossing and nothing objecting. This task adds seventeen labelled cases to `test_hooks.py`: the fifteen the constitution names, plus two beyond that, covering a debt-bearing courier dispatch still refused for a model override and for workspace-write, since every courier fixture already in the suite ran against a debt-free task and nothing touched that path.

Most cases pair a positive control with their fixture in the same scratch project: build the discharge condition, confirm a clean exit, then remove it and confirm the identical fixture now blocks. A clean exit on its own can't tell "correctly discharged" from "the predicate saw nothing," which is exactly the gap the auditor-stem case is built to expose. `CON-audit-r0.json` alone passing proves nothing, since the regex already ignores non-`T-NNN` stems; only adding a real owing stem beside it and confirming that one flips the exit code shows the scan itself still works.

The host-lane case is the one this whole task exists for. CON-audit's first round caught a predicate that could ignore its `data` argument and hardcode one lane, and nothing in the suite drove a hook with `hook_host: codex` at all, so that predicate would have shipped invisible on every Claude-host run. This case drives `stop-gate.py` with that payload and checks `exhausted/claude` and `exhausted/codex` separately, so a hardcoded lane fails here even while it passes every other case.

Ran `scripts/build-plugin.py` to regenerate `plugin/` and `plugins/agent-guild/` from the edited suite.

## T-004

docs(contract): the dual-check regime is enforced now, so stop saying it isn't

The contract has said all along that every checker of record gets a courier crossing. `conventions.md` said in the next breath that nothing enforced it and to dispatch one by hand on every task. Both were true, which is the gap this closes: #100 put two gates behind the regime, and a hand-dispatch instruction left standing would send the next orchestrator off doing work the stop gate now does, then leave them hunting a bug when a turn blocks on a debt they thought they had settled.

The dual-check section now describes what the gates do and names the three files that discharge a debt, because "is this task settled" is a question you answer by going and looking for a path. One is the courier's own `…-r<N>-<lane>.json`, where a timeout, an auth failure, a missing CLI, and vendor output malformed twice running all land as a `blocked` verdict, so a courier that ran at all leaves something behind. Another is the `exhausted/<lane>` sentinel, written instead of a verdict rather than alongside one. The third is the `.denied` waiver, for a host that refused the dispatch outright. The section also names the one verdict of record that owes nothing: one that itself reads `blocked`, since the in-family check never ran and a crossing would compare against nothing.

The state map documents the waiver beside the sentinel—who writes it, the one line that goes in it, and the lane trap. The waiver takes this host's lane suffix, the same lane `exhausted/<lane>` uses, because the predicate pins it. File one under the other lane and it discharges nothing while no gate explains the silence.

Working memory follows. `conventions.md` says what the gates do instead of telling anyone to remember. `decisionLog.md` gains the predicate, its five discharge routes, and why `blocked` is exempt for a reason that isn't cost. `openQuestions.md` drops the #100 caveat from the #34 entry and gains what this job learned about crossings: T-002's agreed with an in-family checker that had reached its verdict on 26 subprocess confirmations the courier structurally could not run, so a judgment clause about process behavior under constructed state crosses no better than a deterministic one. `activeContext.md` comes back under its 20-line ceiling by evicting three risks already written down in `dataContracts.md`, `openQuestions.md`, and `decisionLog.md`, and adding the one this change introduces.

Regenerated `plugin/` and `plugins/agent-guild/`, since `.agent-guild/CLAUDE.md` ships inside the project template.

## T-005

style(hooks): read the shipped prose as one piece, the way nobody had

Everything #100 ships is written, and each of the four building tasks ran a humanizer pass over its own commit message before it landed. Nobody read the comments, the contract section, and the decision log entry as a set. That gap has a characteristic shape: prose written next to the code it explains restates its own argument at every adjacent location, and a per-task pass never catches it because each location reads fine alone.

`second_opinion_debts()` made the unreadable-record argument three times over—twice inside one docstring paragraph, then again in the comment above the `json.load`. The docstring now makes it once, and the comment carries the point that belongs next to the code: routes 1-4 settle before the file is ever opened. In `stop-gate.py`, the `_next_move` comment had a sentence that doesn't parse ("Naming the courier here ... is what the debt list below only ever catches after the fact") and pointed at "today's" generic move line, which stops being today the moment this ships.

`dispatch-guard.py`, the dual-check section of `.agent-guild/CLAUDE.md`, and the `decisionLog.md` entry are untouched. They were already clean, and editing them to show the pass ran would have been the worse call.

Voice only—no comment asserts anything it didn't assert before. The `blocked` exemption still reads as being about there being nothing for a crossing to compare against, not about saving a vendor call.

Ran `scripts/build-plugin.py` to regenerate `plugin/` and `plugins/agent-guild/` from the edited hooks.
