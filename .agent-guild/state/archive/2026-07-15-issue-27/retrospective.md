# Retrospective: Namespaced Dispatch Recognition (Issue #27)

Fifth guild run. One task, one worker attempt, PASS on all five clauses — but the interesting failure happened before any worker existed, and it was a new species: the auditor killed the orchestrator's *implementation plan*, not just a clause.

## The Catch: DEC-Audit Falsified A Seam

CON-audit r0 passed. DEC-audit r0 then FAILed the decomposition by doing something no prior audit had done — it *installed* the task's proposed implementation (wrapper objects in `_lib.py` normalizing `__contains__`/`__getitem__` so `dispatch-guard.py` could stay untouched) against the real code and proved it dead: two raw string comparisons in dispatch-guard (`agent == "auditor"`, `agent != executor`) consume the agent name through operators no wrapper intercepts. The task as written sent the worker toward either a footprint violation or an unbuildable fixture, with a STOP instruction guarding the only workable path. The reconciliation amended C-1 (normalize once at dispatch-guard's entry seam, raw string kept for the log), widened C-4's footprint to three files, rewrote the task's seam guidance, and re-ran both audits to PASS.

The lesson is sharper than "the auditor caught a bad clause": when a task excerpt prescribes an implementation approach, that approach is itself an auditable claim, and the audit should try to build it. This one did, and saved a guaranteed mid-build dead end plus at least one wasted worker dispatch.

## A Worker Improving The Spec

Fixture 2's description said "model override matching the tier." The worker omitted the override deliberately — with one present, `override or DEFAULT_MODEL[agent]` short-circuits and the namespaced-KeyError trap the clause exists to catch goes unexercised — and flagged the call. The checker ruled the omission serves the clause: the fixture as built is the stronger test. Second job running where the flag-and-rule path resolved a spec deviation without a dispute or a rework cycle, and the first where the worker's reading beat the orchestrator's.

## Strain

None at the worker tier: first-attempt PASS, suite at 55 passed 0 failed (from 51), live gates edited without a wobble (each edit py_compile-checked immediately, since the files being fixed were the session's own running hooks).

## What Feeds The Epic

The gate bypass is closed rename-robustly (any `<ns>:` prefix normalizes), the audit trail keeps raw dispatch strings, and #21 is unblocked from this side — the committed plugin's gates will actually gate. Remaining before #21: the nudge (#23). The standing lessons gain one: an implementation seam prescribed in a task is a falsifiable claim — audit it like one.
