# Handoff Cost: What an External Dispatch Actually Costs

This report asks a narrow question: when the orchestrator hands a check to an external vendor lane instead of keeping it in-family, how much more context does that handoff serialize, and is the gap big enough to matter? It draws on the guild's own dispatch history rather than a synthetic benchmark, so every figure below traces to a ledger line.

## Method

### The Distinction That Drives Everything Else

An in-family checker (`checker-deterministic`, `checker-judgment`) runs inside this repo and reads whatever it needs off disk directly: the task file, the artifact, the constitution clause. The orchestrator's marginal cost of dispatching one is just the dispatch prompt itself, a `Task-ID` line, a pointer to the task file, and a short protocol reminder. A courier dispatch to an external vendor (lane `codex`, far side `gpt-5.6-terra`) crosses a process boundary instead. Nothing on the far side can open this repo's files, so the orchestrator has to inline everything the vendor needs: the brief, the artifact contents, the clause text, whatever evidence the check depends on. That inlined total is what `tokens_in` measures.

Those two numbers are not the same thing, and comparing them directly would be misleading. It would compare what the orchestrator serializes outward for a vendor against what an in-family agent reads for itself off disk, at no serialization cost to the orchestrator at all. This report compares serialization to serialization: orchestrator-serialized context for the external case (`tokens_in`) against orchestrator-serialized context for the in-family case (the dispatch prompt alone). An in-family agent's own disk reads stay out of scope on both sides.

### Tokenizer

Every count below uses `heuristic-bytes/4`: UTF-8 byte length divided by four, no real tokenizer involved. `brief_tokens`, `tokens_in`, and `tokens_out` in the table are the ledger's own values, already labeled with this tokenizer. The in-family estimate column is computed the same way, by hand, from real text (see below), so both sides of the comparison use one consistent yardstick.

### Fixed-Overhead Treatment

`tokens_in` bundles two things a courier can't separate: the vendor's fixed session overhead (system prompt, tool schemas) and the evidence the orchestrator actually inlined for that dispatch. No ledger field isolates the fixed piece. This report bounds it rather than guessing at it: the smallest observed `tokens_in` across the five dispatches, 20,855 (this job's own T-001 crossing), upper-bounds fixed-overhead-plus-minimal-evidence. That dispatch's brief, 1,498 tokens, isn't the smallest of the five (issue #44's 983 tokens is smaller), yet its `tokens_in` still comes in lower. That points to the floor being dominated by fixed session overhead rather than by how much evidence a given dispatch carries. The table itself reports `tokens_in` unadjusted, with no per-row subtraction, since there's no way to know how much of any given row's evidence was minimal. That bound still means every row's true marginal-evidence delta against an in-family dispatch is probably somewhat smaller than the raw `tokens_in` figure suggests.

### In-Family Measurement Method

No ledger exists for in-family dispatches, so there's no logged `tokens_in` to compare against. The estimate here comes from measuring a real dispatch prompt directly, two components, both counted the same way:

1. **Dispatch framing.** The boilerplate every worker dispatch carries: the `Task-ID` line, the pointer to the task and constitution files, and the worker-protocol reminder. Measured from this very report's own dispatch prompt, the text this worker received to produce this file: 884 bytes, 221 tokens at `heuristic-bytes/4`.
2. **Task-specific payload.** The part that varies per task. The archived tasks' `check_method` blocks are a reasonable proxy for this, since that's the clause-checking detail a dispatch has to carry inline. Measured directly from each archived task file's YAML frontmatter.

Summed, framing plus payload gives a per-dispatch in-family marginal estimate, reported per row in the table's last column since the payload component varies by task.

### Sequencing Disclosure

This report was drafted against four archived dispatches: the ledger lines under `2026-07-24-issue-{8,44,45,46}`. A fifth row was added at finalization, produced by this job's own dual-check crossing on its own T-001 task (checked by `checker-judgment` plus a `checker-courier` second opinion under the dual-check regime). That crossing generated a courier dispatch of its own rather than reusing a pre-existing one, which is why the table's fifth row cites this same job as its source. The finalize task (T-002) added that row, along with the conclusion and threshold below.

## The Table

| Task checked (source job) | `brief_tokens` | `tokens_in` | `tokens_out` | Outcome | In-family marginal estimate |
| --- | ---: | ---: | ---: | --- | ---: |
| T-003, "Docs: auto-dual contract, decompose convention, SMOKE drills" (issue #8) | 1,559 | 57,661 | 602 | agree | 561 tokens |
| T-001, "Amend checker-courier step 2: the three evidence sources" (issue #44) | 983 | 21,405 | 346 | agree | 430 tokens |
| T-001, "check-diff-scope.py, its tests, the template pointer" (issue #45) | 1,543 | 99,217 | 2,310 | blocked | 489 tokens |
| T-001, "The consumer-suite rule lands in both skills" (issue #46) | 1,144 | 39,081 | 884 | agree | 451 tokens |
| T-001, "Draft the handoff-cost report: method, the four rows" (issue #33) | 1,498 | 20,855 | 711 | agree | 394 tokens |

`cost_usd` is null on all five lines. The vendor reports no cost figure, and this report doesn't estimate one where the ledger says none exists.

The "blocked" row (issue #45) is not a checker failure: the vendor tried to run a test suite inside its own read-only sandbox and couldn't. That's a sandbox constraint, not a verdict on the work under check. It's included because it's a real dispatch with a real `tokens_in` figure, not because it settles anything about accuracy.

In-family marginal estimates: dispatch framing (221 tokens, measured once, held constant) plus that task's `check_method` block (173 to 340 tokens across the five, measured individually). See the method note above for how each number was produced.

## Small-N Framing

Five dispatches, all on one vendor lane (`codex`), all read-only judgment checks. No worker-lane dispatch exists in the ledger yet: the regime hasn't run one. So anything this report implies about write-granted external workers is extrapolation from a different kind of check, on a different risk profile; the Threshold section below states that extrapolation's assumptions explicitly. Read the figures below as what five checker dispatches on one lane show, not as a settled verdict on external dispatch generally.

## Conclusion

Serialization overhead swamps the underlying check across all five dispatches. `tokens_in` runs 49.8x to 202.9x the matched in-family marginal estimate per row, a mean of 99x and an aggregate ratio (summed `tokens_in` over summed in-family estimate, all five rows) of 102.5x. As a share of the external dispatch's own token cost, that's 97.99% to 99.51% overhead per row, 99.02% in aggregate: nearly every token an external checker call spends is serialization, not verification.

That overhead is material for CHECK dispatches. Even the cheapest row on record (issue #44, 49.8x) still means a read-only check that would cost about 430 marginal tokens in-family instead cost over twenty thousand tokens externally, a two-order-of-magnitude gap wide enough that no plausible refinement of the fixed-overhead bound (Method, above) would close it. The conclusion holds regardless of how much of `tokens_in` eventually turns out to be irreducible vendor overhead versus inlined evidence.

## Threshold

The v0.7.0 question is whether a write-granted external WORKER lane is worth building. This report sets that gate at a ratio of 100: an external WORKER dispatch should be treated as uneconomical once its `tokens_in` divided by its in-family marginal estimate, averaged across a representative batch, reaches or exceeds 100x. That's a round number set just above the mean ratio (99x) this ledger already measures for the cheapest kind of external call it has on record, read-only, single-shot checker dispatches.

A write-granted worker dispatch is structurally worse than every dispatch behind that mean, for three reasons, each an assumption this report is making rather than measuring from worker-lane data that doesn't exist yet:

1. Worker briefs run larger than checker briefs (assumption). A checker dispatch inlines a clause, an artifact excerpt, and whatever evidence a rubric names. A worker dispatch has to inline the full file or files it's meant to edit, plus enough surrounding context to edit correctly, more bytes serialized than any row in this table carries.
2. Iteration multiplies calls (assumption). A checker fires once per check. A worker task typically needs several revisions, and unlike an in-family Task dispatch that re-reads the same on-disk files for free between iterations, an external worker has no session to return to: every revision re-pays the full brief-plus-context serialization, so an N-iteration worker task costs roughly N times one dispatch's `tokens_in`, not once.
3. A blind-diff retry is expensive, not cheap (assumption). When a worker's diff fails a check, the retry can't send just the delta. It has no way to know what the checker actually looked at, so the safe retry re-sends the full context, usually with the failure detail added on top.

Because a worker dispatch starts above the checker mean on brief size alone and only grows from there under iteration and retries, 100x is a conservative floor for the gate, not an aggressive one. It's also mechanically testable: once real worker-lane ledger lines exist, compute the same `tokens_in`-to-in-family-estimate ratio per dispatch. A batch averaging at or above 100x confirms the lane is uneconomical under this gate; a batch running well under it, under 50x, this ledger's current checker-lane floor, would be grounds to revisit the number, not to abandon having one.
