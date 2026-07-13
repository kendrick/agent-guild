# Data Contracts

The kit has no application data. Its "contracts" are the shapes of the file-based message bus under `.agent-guild/state/`, and the source of truth for each is a template in `.agent-guild/templates/`. Consume these shapes through the templates; don't restate them here (that just drifts).

## The Bus

`.agent-guild/state/` holds the running job. Everything is Markdown, with the schema-bearing files carrying YAML frontmatter:

- `spec.md`, `constitution.md` — the job's inputs, written by the orchestrator.
- `tasks/T-NNN.md` — one file per unit of work. Schema: `.agent-guild/templates/task.md`.
- `verdicts/T-NNN-<tier>-r<retries>.md` — one checker verdict per attempt. Schema: `.agent-guild/templates/verdict.md`.
- `disputes/T-NNN-<tier>-r<retries>.md` — a worker's case that a check was wrong. Schema: `.agent-guild/templates/dispute.md`.
- `notes/T-NNN.md` — the worker's self-report. Off-limits to checkers and the orchestrator by design; it exists so verification never leans on "I did it."
- `log/` — dispatches, escalations, and the stop-gate's livelock counter.

## Task Frontmatter

Source: `.agent-guild/templates/task.md`. Fields: `id`, `title`, `spec` (anchor into `spec.md`), `clauses[]`, `executor`, `executor_model`, `checker`, `check_method`, `status`, `retries`, `max_retries`, `deps[]`, `escalations[]`, `artifacts[]`. Every clause in `clauses` must appear in `check_method`, named to a script invocation or a `checker-judgment` rubric.

## Status Enum

`pending` → `assigned` → `needs-check` → `checking` → then `rework` (loops back to `assigned`) or `disputed` or `complete`; `abandoned` is the cancelled terminal. Who moves each status is the table in `.agent-guild/CLAUDE.md`—workers set only `needs-check` and `disputed`; the orchestrator owns the rest.

## Verdict Result

Source: `.agent-guild/templates/verdict.md`. `verdict` is one of:

- `PASS` — every clause satisfied, each backed by evidence the checker re-derived.
- `FAIL` — one or more clauses violated. A `## Diagnosis` section is required (file, line, clause id + quoted text, expected vs actual).
- `ERROR` — the check itself couldn't run. Not a retry; the orchestrator fixes the check and it doesn't count against the worker's tier budget.
