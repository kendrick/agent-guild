---
name: audition
description: Run a candidate model through a fixed tryout battery before trusting it in the guild—scored, timed, logged. Use when evaluating a new or swapped model for a worker or checker tier, or deciding where a model belongs in the routing table.
---

# Audition a candidate model

Before a model joins the roster it earns its seat through a **tryout**: the same fixed battery every candidate runs, scored the same way, so results compare across models and across time. A model that improvises past the spec, pads a mechanical task, or PASSes a check it couldn't run flunks here instead of on real work.

The battery is versioned. Run `battery/v1` and record the version with the result, so a score from six months ago still means something.

## 1. Read the battery

Read [battery/v1/manifest.md](battery/v1/manifest.md): four tasks, each with a candidate-facing prompt in `battery/v1/tasks/`, an output filename, and a scripted pass criterion. The tasks span the roster's real demands: a mechanical transform, a clear-spec implementation, a taste-constrained copy task, and a checker-discipline task.

## 2. Run each task as the candidate

For each task A-001 through A-004, dispatch the matching guild agent with the Agent tool's `model` override set to the candidate. Give it the task prompt plus one `Audition-ID:` line carrying the task's id (A-001 gets `Audition-ID: A-001`): the dispatch and return gates read that line to recognize a tryout and pass it through, since an audition has no task file, tier, or verdict for them to check. Save its output to the filename the manifest names, under one directory for this run (for example `.agent-guild/state/audition/<model>/`). Record the wall-clock time each task takes.

Done when all four outputs exist in the run directory.

## 3. Score

Run `battery/v1/score.py <run-directory>`. It applies each task's scripted criterion and prints per-task pass/fail with reasons. The scripted checks are a floor—the taste task also deserves a checker-judgment read for quality, which the score can't capture. Note both.

## 4. Log and recommend

Append one line to [results/results.jsonl](results/results.jsonl): the model, the battery version, per-task pass/fail, the timings, and the date (get it from the environment; don't invent one). Then recommend where the candidate belongs in the routing table, or that it doesn't make the roster. A model that fails A-004 has no business checking; a model that pads A-003 has no business writing copy.
