---
name: decompose
description: Phase 1 of a guild job. Turn .agent-guild/state/spec.md plus the constitution into task files under .agent-guild/state/tasks/, each with an executor, a checker, and a check method. Use after the constitution passes audit, when breaking a job into dispatchable work.
---

# Decompose the spec into tasks

A job is built one task at a time, so the unit that matters is the **one-dispatch task**: small enough that a single worker finishes it in one dispatch, self-contained enough that the worker needs only its own task file and the constitution. Too big and the worker loses the thread; too small and the overhead of a paired check outweighs the work.

Run this after a CON-audit PASS exists. Each task is created from `.agent-guild/templates/task.md` and lands in `.agent-guild/state/tasks/`.

## 1. Cut the spec into one-dispatch tasks

Read `.agent-guild/state/spec.md` and the constitution together. Break the spec into tasks, each producing a coherent artifact or a coherent slice of one. Every task must trace to at least one constitution clause; if a piece of spec maps to no clause, that's a gap to resolve now (add a clause, or confirm it's a non-goal), not to paper over.

Done when every section of the spec belongs to a task and every task cites at least one clause.

## 2. Allocate an id per task

For each task, run `.agent-guild/scripts/new-task.py "<title>"` to claim the next `T-NNN` and stamp the template. This is collision-safe, so you can create tasks in any order.

## 3. Fill each task file

Set the frontmatter per the routing table in `CLAUDE.md`:
- `executor` and `executor_model`: mechanical work to worker-bulk (haiku), clear-spec work to worker-standard (sonnet), taste work to worker-craft (opus).
- `checker`: a clause checked by a script routes to checker-deterministic; a clause checked by a rubric routes to checker-judgment.
- `check_method`: name the check for every clause the task cites—a `.agent-guild/scripts/` invocation, or `checker-judgment: <rubric>`. A cited clause with no check is a task that can't be verified.
- `clauses`: the clause ids this task must satisfy.
- `deps`: task ids that must complete first.
- `owns`: every path this task writes, so concurrent dispatch can't lose an update. Each entry is one of two shapes: an exact file path, or a directory prefix ending in `/` (covers everything under it). If two tasks' `owns` overlap, one has to transitively depend on the other—the dep path is what keeps them from running at the same time. Fill it in for every task that writes files; a task that writes nothing (pure verification, say) leaves it empty. `owns` tracks whole files and whole directories only—two tasks each owning a different region of one file is out of scope, and has to be split into separate files or handled by hand.
- `## Spec excerpt`: the self-contained slice of spec the worker needs. Write it so the worker never has to open the full spec.

Optional: a constitution may designate select high-severity clauses cross-vendor—checker must run on a different vendor than the executor. Honor that designation when assigning `checker`, once a courier lane is eligible as checker of record; today `checker-courier` only produces second opinions, so no clause can be assigned to it yet.

A task that changes a shared contract—a schema, a template shape, a hook-visible format—cites the constitution's consumer-suite clause in its `check_method`, so the checker runs every suite that consumes the contract, not just the contract's own tests. Tasks that don't touch a shared contract carry no such citation.

`check-job-spec.py --audit-id DEC-audit` proves the mechanical half of a decomposition before an auditor reads it: every cited clause exists and is keyed in the task's `check_method`, every `deps` id resolves and the graph is acyclic, whichever task regenerates the shipped trees sits downstream of every task that edits a build input, and any two tasks whose `owns` overlap are connected by a dep path. Run it before you dispatch the auditor, since `dispatch-guard` refuses that dispatch until it passes. #117 lost a round to a terminal task that wasn't terminal, so a regeneration could pass while a later edit was still coming and every verdict stayed green.

Done when every task names an executor, a checker, a check method covering each cited clause, an `owns` list for every task that writes files, and a spec excerpt a worker could act on cold.

## 4. Send it to audit

Tell the orchestrator to dispatch the **auditor** with `Audit-ID: DEC-audit`. The auditor confirms the tasks cover the spec, the assignments follow the routing table, and `deps` form a DAG. Fix what it flags and re-submit before dispatching workers.
