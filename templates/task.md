---
id: T-000
title: One-line task title
spec: state/spec.md#section-anchor
clauses: [C-1]
executor: worker-standard
executor_model: sonnet
checker: checker-deterministic
check_method: >-
  How this task is verified. Name each clause's check: a script invocation
  (scripts/check-foo.sh <args>) or "checker-judgment: <one-line rubric>".
  Every clause in `clauses` must appear here.
status: pending
retries: 0
max_retries: 2
deps: []
escalations: []
artifacts: []
---

## Spec excerpt

<!-- ORCHESTRATOR writes this: the self-contained slice of the spec this task
covers. A worker sees only this section and the constitution, not the whole
spec. Include everything needed to do the work without guessing. -->

## Rework diagnosis

<!-- ORCHESTRATOR appends here on each FAIL, copied verbatim from the checker's
verdict Diagnosis. Newest at the bottom, headed with the attempt it addresses
(e.g. "### sonnet r1"). Empty until the first failure. -->
