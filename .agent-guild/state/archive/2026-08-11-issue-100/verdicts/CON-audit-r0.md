---
task: CON-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-11T06:46:18Z
---

Audit of `.agent-guild/state/constitution.md` (round 0) against `.agent-guild/state/spec.md`, issue #100.

## Per-clause results

| clause | severity | description | evidence |
| ------ | -------- | ------------ | -------- |
| C-1 | major | PASS. The fourteen labels in the check body match the fourteen in the clause text character for character (compared programmatically, zero diffs). Run as written against the baseline, the check exits 1 and names the first absent label on stderr. `check()` prints `  ok   <label>`, which the `grep -qF "ok   so: $L"` fixed string matches as a substring. | check body vs. text: 14/14 exact; baseline run: `missing or failing case: so: debt with the task at checking blocks the turn`, exit 1; `test_hooks.py:63-70` |
| C-2 | blocker | FAIL. Two defects. (a) The clause is titled "exactly five conditions" but its text enumerates four semicolon-separated discharges, and the rubric forbids the checker from reading C-1 — the only place five are enumerated. (b) Nothing requires exercising the Codex-host branch, so a predicate that ignores `data` and hardcodes the `codex` lane passes every check in this constitution while deadlocking a Codex host. | constitution.md:38-40; `_lib.py:165-174` (`courier_lane`), `_lib.py:153-162` (`lane_exhausted`); spec.md:36, spec.md:78 |
| C-3 | blocker | FAIL. The clause text states five requirements; the check says "Confirm all four" and omits the `_next_move` `checking`-line sharpening entirely, and confirms only half of the block-message requirement. A worker can ship without the sharpened line and pass both C-3 and C-1. | constitution.md:45-46 vs. spec.md:44; `stop-gate.py:27-41` |
| C-4 | blocker | PASS. All four confirmations name process-level observables (exit code plus stderr content) a checker can construct from outside. The "unchanged" courier conditions the check does not re-test — model override, `workspace-write`, `danger-full-access` — are already asserted by existing suite cases that C-5 holds green. | constitution.md:51-52; `dispatch-guard.py:280-317`; existing assertions at `test_hooks.py:830-864`; `_lib.block` returns 2 (`_lib.py:555-557`) |
| C-5 | blocker | PASS. Run as written against the untouched baseline: exit 0. All three suites green, `build-plugin.py --check` reports no drift. The `a\|b\|c` combination does what the text claims — one red suite cannot hide the other two, which `&&` would. | `check-build.sh: exit 0 (log: .agent-guild/state/log/build-20260811T014002.log)`; 27 codex-adapter tests OK; `OK: shared-core wrappers, both published packages, and both marketplaces match fresh builds` |
| C-6 | major | PASS. Run as written against the untouched baseline: `OK: 0 path(s) in scope`, exit 0. The allowlist covers every path this job's changes plus `build-plugin.py` will touch. The two generated files outside it are rendered from release metadata this job does not alter. | `check-diff-scope.py` exit 0; output roots at `build-plugin.py:37,55,56,58,61`; `.agent-guild/state/` carve-out at `check-diff-scope.py:112` |
| C-7 | major | FAIL. "names all five discharge routes" contradicts the spec's "the three discharge routes" and matches neither C-2's four-item enumeration nor C-1's five labels. Three different counts for one concept across three documents. Separately, the twenty-line ceiling is stated two different ways and neither matches the project rule as written. | constitution.md:69-70 vs. spec.md:29 and spec.md:59; `AGENTS.md:42`; `_working-memory/activeContext.md` is 22 lines today |
| C-8 | minor | FAIL. The clause cites `_working-memory/conventions.md:65` as the source of the em-dash and Title Case standard. Line 65 is the `/agent-guild:init` / `settings.json` convention. The standard the clause means is at line 72. | `conventions.md:65` vs. `conventions.md:72` |

## Coverage

Spec Changes 1 through 6, each bound:

1. `_lib.py` predicate and `COURIER_LANES` — C-2 (with the defects above).
2. `stop-gate.py` — C-3 (with the defect above).
3. `dispatch-guard.py` — C-4.
4. The waiver — C-2 recognizes `.denied`; C-7 requires the state map to document who writes it and what goes in it; the non-goals record the deliberate absence of a writer script. The spec's compatibility survey holds: I re-derived it, and `con_audit_passed()` (`_lib.py:401-402`) and `_latest_audit_verdict()` (`subagent-return.py:346-349`) both filter to `.md`, so a `.denied` sibling is inert to them as well as to the two consumers the spec names.
5. Docs, all five files — C-7. Nothing outside those five is left stale: the only mentions of #100 anywhere in the tree outside `state/` are `conventions.md:15` and `openQuestions.md:19`, both named by the clause, and both line numbers are correct.
6. Regenerate the published views — C-5 (`--check`, no hand-edits) and C-6 (`plugin/`, `plugins/`, `.claude/` allowlisted).

Spec Tests: all fourteen map one-to-one onto C-1's fourteen labels, in order, with nothing added or dropped.

Spec Verification: the three commands are C-5 verbatim. The five-step end-to-end pass is carried by C-3's rubric (steps 1, 2, 3, 5) and C-4's (step 4), both of which drive the hooks as processes rather than reading them.

Done-when criteria, as the spec restates them (the spec carries no verbatim Done-when block, so these are mapped from its Context and Tests):

- The gates make the second opinion unskippable, so the sample grows from ordinary work rather than vigilance (spec.md:15) — C-3, with C-1 case 2 as the regression fixture for the exact 2026-08-02 state.
- The fix does not deadlock its own enforcement — C-4, with C-1 cases 12 through 14.
- Both hosts produce the same artifacts for the same task (spec.md:78, "host symmetry, done-when #3") — **weakly carried**. C-1 case 4 and C-2 cover a `-claude.json` sibling discharging a debt, but that path is host-agnostic: the sibling test accepts either suffix regardless of which host is running. The host-dependent path is the exhausted-lane discharge, which must resolve through `courier_lane(data)`, and no clause requires it to be exercised. See C-2 (b) in the diagnosis.

## Non-goals

All five are genuinely out of scope, not requirements quietly dropped.

- `scripts/classify-crossings.py`: settled by the user. The spec cites `:122` only as motivation for naming the constant, never as an edit target.
- No validated writer for `.denied`: matches spec Changes 4 ("No new script") exactly, and the stated reason — the orchestrator is cooperative where a courier is not — is the same reason `ledger-append.py` exists.
- Archived runs: the archive lives at `.agent-guild/state/archive/`, a sibling of `verdicts/`, so C-2's predicate cannot reach it. Nothing to drop.
- `docs/roles.md`: verified. It carries no claim this change falsifies, and no mention of #100 or of the regime being unenforced.
- Closing #34: correct. This job grows the mechanism, not the sample.

## Diagnosis

- **C-2** (blocker): the clause is titled "The debt predicate discharges on exactly five conditions" but its text enumerates four discharges, because the lane-sibling item bundles `codex` and `claude` into one clause: "a lane sibling `…-r<N>-codex.json` or `…-r<N>-claude.json` exists". The rubric then instructs the checker to "Construct each of the five discharge conditions" while explicitly forbidding it from reading C-1's assertions — and C-1's label list is the only place in the constitution where five are enumerated as five. A checker that counts four in the text and is told to construct five has to guess which one it is missing. Fix: split the enumeration into five separately-numbered items in the text, so the count and the list agree without reference to C-1 — (1) a `…-r<N>-codex.json` sibling exists, (2) a `…-r<N>-claude.json` sibling exists, (3) `state/exhausted/<lane>` exists for the lane `courier_lane(data)` returns, (4) a `…-r<N>-<lane>.denied` waiver exists, (5) the record verdict's own `verdict` field reads `blocked`.

  evidence: constitution.md:38-40

- **C-2** (blocker): the check has no way to fail its own most likely failing example. `second_opinion_debts(data=None)` must resolve the exhausted-lane discharge through `courier_lane(data)`, which returns `claude` only when `data` carries `hook_host: codex` (`_lib.py:172-174`). An implementation that ignores `data` entirely and hardcodes the `codex` lane passes every check in this constitution: C-1's fourteen labels all pass on a Claude host, C-2's rubric run by a checker on a Claude host constructs `exhausted/codex` and sees it discharge, C-5's `test_codex_adapter.py` gains no new case so it cannot fail, and C-3 and C-4 never touch the predicate's lane resolution. The consequence on a Codex host is the exact deadlock C-4 exists to prevent, in the other direction: `exhausted/claude` never discharges the debt, so `stop-gate.py` demands a courier forever while `dispatch-guard.py` — which does resolve the lane correctly (`dispatch-guard.py:305-315`) — refuses it on the sentinel, and every Codex run ends at `STALLED.md`. This is done-when #3, "both hosts produce the same artifacts for the same task". Fix: append to C-2's check, "Then call the predicate twice against the same fixture with `data={'hook_host': 'codex'}`: confirm `state/exhausted/claude` discharges the debt and `state/exhausted/codex` does not, and confirm the reverse with `data={}`." Consider also adding a fifteenth case to C-1 — its failing example already permits one — labelled `so: the exhausted-lane discharge follows the host lane`, which would put the regression in the suite rather than only in a rubric. If instead you bind that case in `.agent-guild/hooks/test_codex_adapter.py`, that path must be added to C-6's allowlist, which does not currently list it.

  evidence: constitution.md:39-40; `_lib.py:165-174`; `dispatch-guard.py:305-315`; spec.md:78, spec.md:94

- **C-3** (blocker): the clause text states five requirements and the check confirms four, and the omitted one is a spec requirement in its own right. The text requires that "`_next_move`'s `checking` line, when that task's verdict of record has landed but its lane sibling has not, says to dispatch `checker-courier` before completing, rather than the generic 'act on the verdict'" — spec Changes 2, third bullet. The check's "Confirm all four" list does not include it, and its exhaustive phrasing tells a checker that four is the whole obligation. C-1 cannot backstop this: its case-2 label binds a test's existence, and its own note says the clause "binds coverage, not correctness". So a worker ships `_next_move` untouched, C-3 passes on its four, C-1 passes on its fourteen, and the sharpened line the spec asked for never lands. Fix: change "Confirm all four" to "Confirm all five" and add the fifth as an observable — "with an open task at `status: checking` whose verdict of record has landed and whose lane sibling has not, the block message's line for that task names `checker-courier` and says to dispatch it before completing; with the lane sibling present, that same line reverts to the generic 'act on the verdict' wording." While editing the check, also close the half-covered second requirement: the text requires the block message to name "the missing lane-suffixed stem **and the dispatch that settles it**", but the check confirms only "the message names the absent stem". Extend that confirmation to both halves.

  evidence: constitution.md:45-46; spec.md:44; `stop-gate.py:27-41`

- **C-7** (major): the clause requires `.agent-guild/CLAUDE.md`'s dual-check section to name "all five discharge routes", but the spec calls them "The three discharge routes" (spec.md:29) and asks the doc for exactly that (spec.md:59), while C-2's text enumerates four. Three documents, three counts, one concept. A worker who writes the spec's three fails C-7's five; a worker who writes C-2's four also fails C-7's five; and a checker reading C-7 alone cannot tell which five are meant. Fix: replace the count with the list, so no clause has to agree with another clause's arithmetic. Require that the section name each route by what the reader would look for on disk: a lane-suffixed verdict at `…-r<N>-<lane>.json` (which is where auth failure, timeout, missing CLI, and twice-malformed vendor output all land as `blocked`), the `state/exhausted/<lane>` quota sentinel, and the `…-r<N>-<lane>.denied` waiver for a host that refuses the dispatch outright — plus the note that a verdict of record reading `blocked` owes no crossing at all. If you keep a number anywhere in the clause, make it the same number in C-2's title, C-7's text, and the spec.

  evidence: constitution.md:69 vs. spec.md:29 and spec.md:59; constitution.md:39

- **C-7** (major): the `activeContext.md` ceiling is stated two ways and neither matches the rule as the project writes it. The text says "staying inside its twenty-line ceiling"; the check says "at most twenty lines of content"; `AGENTS.md:42` says "Never let `activeContext.md` exceed 20 lines" with no qualifier, and `AGENTS.md:24` says "≤20 lines". "Of content" invites the argument that blank lines and the heading are exempt, which matters right now — the file is 22 lines today, so the worker has to trim, and the checker has to rule on how much. Fix: make the check mechanical — "confirm `wc -l _working-memory/activeContext.md` reports 20 or fewer, the flat ceiling `AGENTS.md:42` states" — and drop "of content" from both the text and the check.

  evidence: constitution.md:69-70; `AGENTS.md:24`, `AGENTS.md:42`; `wc -l _working-memory/activeContext.md` = 22

- **C-8** (minor): the clause cites the wrong line. It says the em-dash and Title Case overrides are "the project's standard at `_working-memory/conventions.md:65`". Line 65 is "`/agent-guild:init` never touches `.claude/settings.json`", an unrelated convention about plugin hook registration. The standard the clause means is line 72: "Em dashes chain directly to the text on both sides—like this—never wrapped in spaces. Don't hard-wrap prose lines; let the display wrap. Headings are Title Case." A checker following the citation reads a rule about `settings.json` and has to go hunting. Fix: change `_working-memory/conventions.md:65` to `_working-memory/conventions.md:72`. Nothing else in C-8 needs to change; the rest of the clause is falsifiable as written, and line 72 happens to carry the no-hard-wrap rule the clause also asserts, which makes the corrected citation cover more of the clause than the broken one claimed to.

  evidence: constitution.md:75; `conventions.md:65` vs. `conventions.md:72`

- **Cross-cutting, not a clause defect but needing a decision before Phase 1**: the spec's own Notes say this work is "Not running this as a guild job (`/job 100`): the dual-check regime is what's being repaired, so driving the repair through it would both fight the broken machinery and put self-referential crossings into #34's sample" (spec.md:110). It is being run as a guild job — there is a constitution, `check-job-spec.py --audit-id CON-audit` passes, and I was dispatched as `CON-audit`. The constitution half-acknowledges this in its third preamble rule ("This job edits the very gates that run it") and points at `PAUSED`, but it does not address the consequence the spec was actually worried about, which is live rather than hypothetical: the moment a worker lands `second_opinion_debts()` in `_lib.py` and wires it into `stop-gate.py`, this job's own remaining tasks start accruing debts, and the orchestrator's turn is held open demanding couriers on the tasks that are building the courier enforcement. Those crossings then land in #34's sample as self-referential data. Two clean resolutions, either acceptable: amend spec.md:110 to record that the decision changed and say how the self-referential crossings will be excluded from #34's corpus, or extend the constitution's third preamble rule to name this specific failure mode alongside the existing gates-under-construction warning. What should not happen is the two documents continuing to disagree about whether this is a guild job at all, because the retrospective in Phase 3 will read both.

  evidence: spec.md:110 vs. constitution.md:13; `.agent-guild/state/` currently holds a constitution and an audit dispatch
