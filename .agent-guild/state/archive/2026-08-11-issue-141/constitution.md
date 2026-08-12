# Constitution: a verdict's authority is not its filename (#141)

<!--
Job source: kendrick/agent-guild#141. `second_opinion_debts()` decides a crossing
landed by looking for a filename in `state/verdicts/`, and nothing ties that file
to a dispatch that authorized it.

Revision r4, after CON-audit r0, r1, r2, and r3 all failed. The three failures were
one mistake repeated: asking a deterministic check to prove something
deterministic checks cannot prove, then validating it against a correct tree
instead of an adversarial one.

- r0: five clauses shared one check that exits 0 on the unmodified tree.
- r1: replaced it with a grep of test SOURCE. Seven appended comment lines
  turned four blocker clauses green.
- r2: replaced that with a grep of test RUNTIME OUTPUT. Comments died, but
  `check("<label>", True, "")` — a test asserting nothing — still passed, and
  the tamper guard on the orchestrator-owned check script was vacuous, because
  `.agent-guild/state/*` is gitignored (`.gitignore:5`; `!archive/` is the sole
  exception, which is the only reason C-6's identical guard works).

So r3 stops trying. A check that reads a test file cannot tell a real test from
a written one, and no amount of pattern-hardening changes that. The deterministic
clauses now exercise behavior through an orchestrator-owned script pinned by
digest, and the behavioral claims move to judgment rubrics, where a checker who
re-derives is the right instrument. C-8 exists to catch the vacuous test, and it
fails on a diff that changes no gate code, so it cannot pass the way it did in
r2's demonstration.

Revision r4 applies CON-audit r3's named edits. r3 failed with no blockers and
the ruling that the architecture was right and the remaining defects were clause
surgery. Four things changed:

- C-8 asked a checker to revert to pre-change code and re-run. Uninterpretable:
  `test_hooks.py` imports `_lib` at module scope, so any case touching a symbol
  new in this job aborts the whole suite with `AttributeError`, which reads like
  a failing test. It now asks the checker to neutralize the targeted branch in a
  copy of the DELIVERED code, where every symbol still exists.
- C-3 only ever proved refusal. Breaking the predicate outright (`if False:` at
  `_lib.py:271`) makes the forge subcommand print PASS on a tree where no
  crossing can discharge at all. The positive property is now stated in C-1.
- C-5 listed `state/PAUSED` among the predicate's discharge routes. It is not
  one: `_lib.run()` handles it at `_lib.py:697`, and the predicate body never
  calls `paused()`. r0 found this, r1 fixed it, and merging C-5 with C-7 folded
  it back in.
- C-1 assigned a courier that died mid-flight to the `.denied` waiver, a use the
  contract does not describe and which collided with C-5. It now states the
  requirement directly and makes widening `.agent-guild/CLAUDE.md` part of the
  job, rather than quietly extending the kit's contract from inside a job spec.

Clause ids were renumbered when the old C-5 and C-7 merged. Prior audits cite the
old numbering; the mapping is old C-8 to C-7, old C-9 to C-8, old C-10 to C-9.

Two approaches the issue itself proposes stay ruled out, both re-derived
independently by every audit round:

1. Ledger-backing. The forging agent wrote a conforming ledger row naming its own
   verdict in `artifacts` (`archive/2026-08-11-issue-100/log/vendor-calls.jsonl`,
   the row with `duration_ms: 0`), so this passes the forgery.
2. Dispatch-ordering. `dispatches.log` stamps local time; verdicts stamp UTC, an
   offset of exactly five hours here with nothing recording it. Read as one clock
   the forgery looks authorized.

The seam is settled and confirmed buildable on both hosts: `dispatch-guard.py`
has `tid`, `executor_model`, `retries`, and `courier_lane(data)`, so it can
compute a crossing's exact stem and record what it finds at dispatch;
`subagent-return.py` recomputes the same stem at return. Nothing may depend on
observing the write itself, because a courier's verdict is written by
`codex-courier.py` through Bash and the kit registers write hooks only on
Write|Edit|MultiEdit.
-->

## Clauses

### C-1: A crossing discharges a debt only if the gate recorded it as authorized
- **text**: A lane-suffixed verdict discharges a second-opinion debt only when the gate recorded that crossing as authorized. That record is made by `dispatch-guard.py` and `subagent-return.py` from the stem they compute themselves, never by trusting a file's presence, and it works on both hosts: on a Claude host where the courier's file is already on disk, and on a Codex host where the read-only courier returns its outcome for the parent to persist. A stem already present when its courier was dispatched is not recorded as authorized, so a forged file is not laundered by the next legitimate dispatch. An authorized crossing does discharge its debt: a predicate that discharges nothing satisfies this clause no better than one that discharges everything, and `check-141-conformance.py forge` cannot tell those apart. A stem left unauthorized, including one poisoned by a courier that died after writing, stays clearable by a `…-<lane>.denied` waiver at that stem; `.agent-guild/CLAUDE.md` currently describes that waiver as being for a lane that never reached a courier at all, so the job widens that description to cover this case rather than leaving the contract and the code disagreeing.
- **check**: checker-judgment: read `_lib.second_opinion_debts()`, `dispatch-guard.py`, and `subagent-return.py` on the delivered tree; confirm a lane-suffixed verdict discharges only via the gate's own record, that the record is made on a Codex read-only return, that a pre-existing stem is never recorded, that an authorized crossing does discharge, and that a `.denied` waiver still clears a stem carrying an unauthorized verdict. Confirm `.agent-guild/CLAUDE.md`'s waiver description was widened to match. Run `python3 .agent-guild/state/check-141-conformance.py forge` as supporting evidence, not as the whole check.
- **severity**: blocker
- **failing example**: A file written by hand at `state/verdicts/T-900-sonnet-r0-codex.json`, valid against `verdict.schema.json`, and `second_opinion_debts()` returns `[]` for T-900.

### C-2: A foreign-stem write does not discharge another task's debt
- **text**: A courier that writes a lane-suffixed verdict for a Task-ID other than the one it was dispatched on does not thereby discharge that other task's debt, and the anomaly is surfaced rather than passing silently. Surfaced means one of two observable channels, not a judgement call: a non-zero hook exit whose stderr names both Task-IDs, or a row appended under `.agent-guild/state/log/`. A verdict written concurrently by a different agent for its own task never blocks an unrelated return: the incident run itself overlaps `checker-courier T-001` with `worker-standard T-002`, so a time-window predicate would fire on innocent work. The implementation may use `dispatch-guard.py` and `subagent-return.py`, and may not depend on observing the write.
- **check**: checker-judgment: read the delivered gate code and its tests; confirm the #100 case (a courier dispatched for T-001 writing T-002's verdict) is refused or surfaced through one of the two named channels, that the record names both Task-IDs, that a concurrent unrelated crossing does not trigger it, and that no part of the mechanism requires a hook on the write.
- **severity**: blocker
- **failing example**: A `checker-courier` dispatched with `Task-ID: T-001` writes both `T-001-sonnet-r0-codex.json` and `T-002-sonnet-r0-codex.json`, and its return exits 0 without mentioning the T-002 file. This is the #100 incident verbatim.

### C-3: The spec's reproduction runs and the forged crossing does not discharge
- **text**: `python3 .agent-guild/state/check-141-conformance.py forge` exits 0 against the delivered tree. It replays the reproduction from `state/spec.md` and exits 0 only when the forged crossing fails to discharge the debt, printing both `second_opinion_debts()` results either way. The script is orchestrator-owned and pinned by digest in this clause's check, because `.agent-guild/state/*` is gitignored and `git status` reports a tampered copy as clean.
- **check**: .agent-guild/scripts/check-build.sh 'test "$(shasum -a 256 < .agent-guild/state/check-141-conformance.py | cut -d" " -f1)" = 5877ccc2ccde87f9e2fe8cd272b8a34c594b0e41ab4211f2cffac2f820c7df84 && python3 .agent-guild/state/check-141-conformance.py forge'
- **severity**: blocker
- **failing example**: The delivered tree prints `after forge: []`, meaning a file nobody authorized discharged the debt; or the script's digest no longer matches, meaning the check was edited rather than satisfied.

### C-4: dispatches.log stamps UTC
- **text**: `dispatch-guard.py` writes the `dispatches.log` timestamp in UTC with a trailing `Z`, matching what `utc_now()` produces for verdicts and ledger rows. `_log_gate_gap` writes a different file and is not in scope. Scoped into this job by explicit decision rather than by the issue text: the two clocks are five hours apart with nothing recording it, and the next person to write an ordering check inherits a trap that reads as working.
- **check**: .agent-guild/scripts/check-build.sh 'test "$(shasum -a 256 < .agent-guild/state/check-141-conformance.py | cut -d" " -f1)" = 5877ccc2ccde87f9e2fe8cd272b8a34c594b0e41ab4211f2cffac2f820c7df84 && python3 .agent-guild/state/check-141-conformance.py dispatch-clock'
- **severity**: major
- **failing example**: `dispatch-guard._log` writes `2026-08-11T17:09:52`, so a row cannot be compared against a verdict stamped `2026-08-11T22:09:52Z` without a silent five-hour offset.

### C-5: The escape hatches still work and the predicate stays total
- **text**: Two properties of `second_opinion_debts()` survive this job. First, the discharge routes it already has behave exactly as `.agent-guild/CLAUDE.md` documents and none acquires C-1's requirement; the four behaviors are that `state/exhausted/<lane>` discharges this host's debts, that a hand-written `…-<lane>.denied` waiver discharges its debt, that a `blocked` verdict of record owes no crossing, and that a `.denied` waiver still discharges at a stem carrying an unauthorized lane verdict. `state/PAUSED` is not among them: it is handled by the `_lib.run()` wrapper, not by this predicate, and listing it here was a regression. Second, it returns a list rather than raising on every input it can meet; the four inputs are a missing verdicts directory, a malformed verdict of record, a missing authorization record, and a truncated or non-JSON authorization record.
- **check**: checker-judgment: read the delivered predicate and its tests, then exercise each of the four discharge behaviors and each of the four malformed inputs named above against a scratch project; confirm each behaves as stated and that nothing raises.
- **severity**: blocker
- **failing example**: A hand-written `T-001-sonnet-r0-codex.denied` waiver stops discharging its debt because the authorization requirement was applied to every route; or a truncated authorization record makes `second_opinion_debts()` raise, crashing every `Stop` hook until it is deleted by hand.

### C-6: Archived crossings stay valid and untouched
- **text**: Nothing under `.agent-guild/state/archive/` is modified, and every archived verdict still passes `validate-verdict.py`. No migration, backfill, or authorization record is required for an archived crossing to remain readable as evidence for #34.
- **check**: .agent-guild/scripts/check-build.sh 'for f in .agent-guild/state/archive/*/verdicts/*.json; do python3 .agent-guild/scripts/validate-verdict.py "$f" >/dev/null || exit 1; done; test -z "$(git status --porcelain .agent-guild/state/archive/)"'
- **severity**: blocker
- **failing example**: The job adds an `authorized: true` key to archived verdict JSON so historical crossings keep discharging, leaving `git status` dirty under `state/archive/`.

### C-7: Every consumer of this shape stays green
- **text**: This job changes hook-visible state shapes, so these eleven suites pass on the delivered tree, together with `python3 scripts/build-plugin.py --check` and a run of `scripts/classify-crossings.py`, which reads the verdict-directory shape to build #34's corpus and has no suite of its own: `.agent-guild/hooks/test_hooks.py`, `.agent-guild/hooks/test_codex_adapter.py`, `.agent-guild/scripts/test_verdict_tools.py`, `.agent-guild/scripts/test_ledger_append.py`, `.agent-guild/scripts/test_compose_brief.py`, `.agent-guild/scripts/test_claude_courier.py`, `.agent-guild/scripts/test_codex_courier.py`, `.agent-guild/scripts/test_check_diff_scope.py`, `.agent-guild/scripts/test_check_job_spec.py`, `scripts/test_build_plugin.py`, and `scripts/test_codex_hooks_packaging.py`.
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/hooks/test_hooks.py && python3 .agent-guild/hooks/test_codex_adapter.py && python3 .agent-guild/scripts/test_verdict_tools.py && python3 .agent-guild/scripts/test_ledger_append.py && python3 .agent-guild/scripts/test_compose_brief.py && python3 .agent-guild/scripts/test_claude_courier.py && python3 .agent-guild/scripts/test_codex_courier.py && python3 .agent-guild/scripts/test_check_diff_scope.py && python3 .agent-guild/scripts/test_check_job_spec.py && python3 scripts/test_build_plugin.py && python3 scripts/test_codex_hooks_packaging.py && python3 scripts/build-plugin.py --check && python3 scripts/classify-crossings.py >/dev/null'
- **severity**: blocker
- **failing example**: The gate lands and `test_hooks.py` passes, but `build-plugin.py --check` reports the generated trees stale because the new hook behavior was never rebuilt into `plugin/` and `plugins/`.

### C-8: The tests are real
- **text**: A test that asserts nothing does not count as a test. Every new or changed gate branch ships a refuse-case and an allow-case; each refuse-case demonstrably fails against the pre-change code; and the diff modifies gate code rather than test files alone. A `check(label, True, "")` is absent, and so is any assertion whose truth does not depend on what the gate decided for the input being tested: `check(label, _lib.crossing_authorized.__name__ == "crossing_authorized")` names the new code, is not a literal, and still asserts nothing. The allow-cases include at minimum a legitimately authorized crossing discharging its debt, a concurrent agent's verdict not blocking an unrelated return, and each of C-5's four discharge behaviors.
- **check**: checker-judgment: read the full diff. Confirm it modifies gate code and not only test files; confirm every new branch has a paired allow-case and refuse-case; confirm each refuse-case is decisive by neutralizing the branch it targets in a scratch copy of the DELIVERED code and checking that the case flips to FAIL. Do not revert to pre-change code: `test_hooks.py` imports `_lib` at module scope, so a case touching any symbol new in this job aborts the whole suite with `AttributeError`, which reads like a failing test and is not one. Then confirm every paired case differs in exactly one input and produces opposite outcomes, and that no added assertion's truth is independent of the gate's decision for the input under test.
- **severity**: blocker
- **failing example**: The diff adds four lines reading `check("<some label>", True, "")` and changes no hook code, and every deterministic clause passes. This is CON-audit r2's demonstration verbatim.

### C-9: Comments and commit messages carry the why
- **text**: Code comments explain the constraint, incident, or invariant behind the code rather than restating what it does, and commit messages use a conventional-commit prefix with a scope and say why the change was made. The authorization mechanism in particular names the #100 incident it exists to prevent, and says why a time window was rejected for it.
- **check**: checker-judgment: read every added comment and commit message; confirm each explains a why a reader could not recover from the code, and that every commit subject carries a conventional-commit type and scope.
- **severity**: minor
- **failing example**: A comment reading `# check the record exists` above code that checks a record exists, and a commit subject reading `fix: update hooks`.

## Protected content

<!-- Nothing in this job ships verbatim author words. The issue text is
reproduced in state/spec.md by the intake skill, not by a worker, and no
deliverable quotes it. -->
- manifest: none

## Non-goals

- **Ledger-backing as the authority signal.** Ruled out on evidence: the forging agent wrote a conforming ledger row naming its own verdict, so this would have passed the incident that motivated the issue.
- **Dispatch-log ordering as the authority signal.** Ruled out. It cannot see a file forged while no agent is running. C-4 fixes the clock because the trap is real, not to enable this approach.
- **Authorization for the non-verdict discharge routes.** The quota sentinel, the `.denied` waiver, and the `blocked` verdict of record stay as they are; C-5 pins them unchanged. The spec's third Done-when says "verdict files", and the waiver in particular is documented as hand-authored, so requiring a machine record would remove an escape hatch.
- **Retroactive validation of #34's existing corpus.** Archived crossings are evidence, not live state; C-6 requires only that they stay valid and untouched.
- **#130.** The neighbouring defect, a valid row landing at a path nothing reads, is out of scope here.
