---
id: T-000
title: One-line task title
spec: .agent-guild/state/spec.md#section-anchor
clauses: [C-1]
executor: worker-standard
executor_model: sonnet
checker: checker-deterministic
check_method: >-
  How this task is verified. Name each clause's check: a script invocation
  (.agent-guild/scripts/check-foo.sh <args>) or "checker-judgment: <one-line rubric>".
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

## Courier comparison

<!-- ORCHESTRATOR writes this once the second opinion lands, or once it is
settled that none is coming, while #34 is still open. Read both verdicts
directly and record three counts: findings only the courier raised, findings
only the checker of record raised, and the overlap.
Name the clause behind each unique finding — #34 rules on the unique-finding
rate, and a count with no clause attached can't be audited later.

Say which cited clauses were deterministic. Those never crossed at all:
compose-brief.py drops them before the brief is written, so the second opinion
covered the judgment clauses only and the counts above are read against that
shorter list.

A second opinion that never landed goes here too, with the reason: denied,
blocked, or skipped because the task cited no judgment clause at all and there
was nothing to cross. An absence recorded is data; an absence unrecorded reads
later as agreement.

This section never reaches the vendor: compose-brief.py extracts only the spec
excerpt and rework diagnosis. -->
