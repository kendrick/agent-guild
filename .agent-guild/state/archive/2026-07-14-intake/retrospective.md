# Retrospective: GitHub-Issue Intake (Job 1)

Second dogfood run, first of the two-job intake-then-publish sequence. Four tasks, all passing on first attempt. One catch, again by the auditor, again before any worker ran. No disputes, no escalations, no ERROR verdicts.

## Catches

The single FAIL was CON-audit r0, and it bundled two coverage gaps in my clause-writing:

- C-3 required the validator's self-test to check exit codes but never demanded the diagnostic line the spec promised. A validator that failed with a silent `sys.exit(1)` would have passed every clause while breaking the spec's contract that failures name the violated rule.
- C-1 checked argument forms and the no-fabrication rule but not the output content contract. A skill that wrote the issue title and dropped the body, or stripped its markdown, would have sailed through.

Both were closed in one amendment round; r1 passed. The pattern from the first dogfood repeats: the verification system's real catches concentrate at Phase 0, on the orchestrator's own work. By the time workers run, the standard has been debugged.

## Strain

None. No retries, no tier escalations, no disputes. CON-audit took two rounds, which is where the design wants the friction to live.

## Why Workers Keep Passing First Try

Two consecutive jobs at 100% first-attempt worker PASS deserves suspicion, so here is the honest reading. Workers run their tasks' own check commands before returning, so the deterministic checks act as a pre-flight rather than a trap; the checker then re-derives the result independently. That is the intended shift-left, not a rubber stamp—the T-002 checker, for instance, re-verified the header contract in both directions and confirmed the load-bearing detail that `ref` always carries a `#N` consistent with `issue`. But it does mean the FAIL/rework/escalate/dispute machinery has now gone two jobs without a live rehearsal. If a third job repeats this, consider a deliberately adversarial task (ambiguous spec, taste-heavy artifact) to exercise those paths on purpose.

## Check-Infra Debt

None. The auditor pre-verified the deterministic checks empirically at CON-audit: it confirmed the C-6 regex rejects the pre-change 49 count, accepts 50+ only with zero failures, and refuses every nonzero-failed string it could construct; it confirmed check-build.sh surfaces the then-missing validator as a hard failure rather than a silent pass; it confirmed the C-7 path list on the clean tree.

## Deliverables

- `.agent-guild/scripts/check-provenance.py`—provenance validator with `--issue` cross-check and an embedded `--self-test` (5 fixtures, message-asserting).
- `.claude/skills/job/SKILL.md`—the `/job` intake skill: six argument situations, header-then-content output, verbatim issue bodies, fail-honest `gh` handling, validator self-check.
- `.claude/skills/constitution/SKILL.md`—collapsed-interview branch when `spec.md` exists; full interview preserved otherwise.
- `.agent-guild/hooks/_lib.py` + `test_hooks.py`—`project_dir()` fallback now validates its candidate or raises; suite at 51 passed, 0 failed. Job 2's build script can copy `_lib.py` verbatim.

## What Feeds Job 2

The intake path is built and offline-verified; the live proof (`/job <issue#>` into a collapsed constitution) is the orchestrator demonstration that follows this report. Job 2's scope gets filed as GitHub issues and consumed through `/job`, so every Job 2 kickoff doubles as another live test of today's deliverables. Carry forward the standing lesson, now twice-confirmed: write the constitution's checks to assert the source of a property, and expect the auditor to earn its keep before the first worker moves.
