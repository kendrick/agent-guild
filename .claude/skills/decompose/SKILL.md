---
name: decompose
description: Phase 1 of a guild job. Turn state/spec.md plus the constitution into task files under state/tasks/, each with an executor, a checker, and a check method. Use after the constitution passes audit, when breaking a job into dispatchable work.
---

# Decompose the spec into tasks

A job is built one task at a time, so the unit that matters is the **one-dispatch task**: small enough that a single worker finishes it in one dispatch, self-contained enough that the worker needs only its own task file and the constitution. Too big and the worker loses the thread; too small and the overhead of a paired check outweighs the work.

Run this after a CON-audit PASS exists. Each task is created from `templates/task.md` and lands in `state/tasks/`.

## 1. Cut the spec into one-dispatch tasks

Read `state/spec.md` and the constitution together. Break the spec into tasks, each producing a coherent artifact or a coherent slice of one. Every task must trace to at least one constitution clause; if a piece of spec maps to no clause, that's a gap to resolve now (add a clause, or confirm it's a non-goal), not to paper over.

Done when every section of the spec belongs to a task and every task cites at least one clause.

## 2. Allocate an id per task

For each task, run `scripts/new-task.py "<title>"` to claim the next `T-NNN` and stamp the template. This is collision-safe, so you can create tasks in any order.

## 3. Fill each task file

Set the frontmatter per the routing table in `CLAUDE.md`:
- `executor` and `executor_model`: mechanical work to worker-bulk (haiku), clear-spec work to worker-standard (sonnet), taste work to worker-craft (opus).
- `checker`: a clause checked by a script routes to checker-deterministic; a clause checked by a rubric routes to checker-judgment.
- `check_method`: name the check for every clause the task cites—a `scripts/` invocation, or `checker-judgment: <rubric>`. A cited clause with no check is a task that can't be verified.
- `clauses`: the clause ids this task must satisfy.
- `deps`: task ids that must complete first.
- `## Spec excerpt`: the self-contained slice of spec the worker needs. Write it so the worker never has to open the full spec.

Done when every task names an executor, a checker, a check method covering each cited clause, and a spec excerpt a worker could act on cold.

## 4. Send it to audit

Tell the orchestrator to dispatch the **auditor** with `Audit-ID: DEC-audit`. The auditor confirms the tasks cover the spec, the assignments follow the routing table, and `deps` form a DAG. Fix what it flags and re-submit before dispatching workers.
