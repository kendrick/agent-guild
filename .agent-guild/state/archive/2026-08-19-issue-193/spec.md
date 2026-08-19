---
source: github-issue
ref: kendrick/agent-guild#193
issue: 193
title: feat(scripts): three defect shapes check-job-spec can catch mechanically, each of which cost an audit round
fetched_at: 2026-08-18T00:10:09Z
---

# feat(scripts): three defect shapes check-job-spec can catch mechanically, each of which cost an audit round

## Problem

The repo's position since #132 is that speed comes from not auditing cheap defects, and #182 restated it: a defect a script can catch should not cost an opus round. The `kendrick/dotfiles#22` run spent audit rounds on three shapes that `check-job-spec.py` could have caught before any auditor was dispatched.

**R10 misses its own target shape by one word.** `_governs_plural_noun` at `check-job-spec.py:1291-1293` reads the text immediately after the number and requires a word ending in `s`:

```python
def _governs_plural_noun(text, match):
    tail = text[match.end():].lstrip()
    return re.match(r"[A-Za-z][A-Za-z-]*s\b", tail) is not None
```

So `Four rules constrain how:` above three bullets fires R10, and `Four further rules constrain how:` above the same three bullets passes clean, because `further` is what follows the number. Any adjective between the count and the noun disables the rule.

This is not hypothetical phrasing. The `#22` decomposition carried `Three further rules constrain how:` above three bullets. That count happened to be correct, and nothing would have said so if it were not. In the same file, a false claim about the repo's own history reached DEC-audit r2 and was caught by an opus auditor reading the filesystem, not by the linter.

**Routing is entirely unchecked.** The routing table in `.agent-guild/CLAUDE.md` assigns a checker by clause kind: a clause checked by a script routes to `checker-deterministic`, a clause checked by a rubric routes to `checker-judgment`. `check-job-spec.py` never reads a task's `executor`, `executor_model`, or `checker` fields for this. The only occurrences of `executor:` in the file are inside `_FIXTURE_T001` at `:1644-1650`.

The harmful direction is well defined and mechanical: a `checker-deterministic` handed a judgment rubric cannot apply it, because that agent runs scripts and exercises no judgment. The reverse, a `checker-judgment` carrying script clauses, is safe and has house precedent, so only one direction needs a rule.

**R2's diagnostic names the wrong thing.** `nearest_anchor` at `:499-523` picks the backticked span closest to the citation within its sentence, where `anchor_spans` at `:490-496` only counts spans of 24 or more characters containing a space. A markdown list introduced by a colon keeps the sentence open across every bullet and into the following fields, so the anchor can come from several lines away.

On `#22` a citation on one line was anchored to a span in the same clause's `failing example` six lines below, producing:

```
job-spec: R2 citation-anchor: constitution.md:28 cites tests/install-failures.bats:74 but the quoted code is at tests/install-failures.bats:141
```

Line 74 was the correct citation. Line 141 is where the unrelated anchor lives. The message names two line numbers and neither the anchor text it matched nor the fact that it looked outside the current line, so the author's only recovery is to permute the prose until it passes. That cost two rounds of trial and error on this run.

## Proposed Behavior

Three changes to `.agent-guild/scripts/check-job-spec.py`, independently landable.

1. **Relax R10's adjacency requirement** so the plural noun may be separated from the count by adjectives, while keeping the rule from firing on a number that governs no list.
2. **Add a routing rule** that fails a task whose `checker` is `checker-deterministic` while any clause it cites has a `checker-judgment:` check method, naming both the task and the clause.
3. **Name the anchor in R2's diagnostic**, and say where it was found relative to the citation, so an author can tell a wrong citation from a wrongly-chosen anchor.

## Acceptance Criteria

- [ ] R10 fires on `Four further rules constrain how:` followed by three list items, naming the count and the item total.
- [ ] R10 still passes on every constitution and task set under `.agent-guild/state/archive/`, so relaxing adjacency introduces no false positive on the existing corpus.
- [ ] A task declaring `checker: checker-deterministic` while citing a clause whose check begins `checker-judgment:` exits nonzero, and the message names the task and that clause.
- [ ] A task declaring `checker: checker-judgment` while citing only script-checked clauses exits zero, since that direction is safe and has precedent in the archive.
- [ ] R2's diagnostic quotes the anchor text it matched and gives that anchor's line, distinct from the two line numbers it already reports.
- [ ] `python3 .agent-guild/scripts/test_check_job_spec.py` passes, with a case per change drawn from the archive rather than from invented fixtures, matching that suite's existing convention.
- [ ] `python3 .agent-guild/hooks/test_hooks.py` and `python3 scripts/build-plugin.py --check` both pass.

## An Open Question, Not a Claim

An `owns` overlap between a task and its own dependency passes both `check-job-spec.py` and `ready-set.py`. R13 requires overlapping owners to be connected by a dep path, which this pair is by construction, and `ready-set.py` never compares them because the dep relation defers the dependent out of the wave before the collision check runs.

Normally that is correct rather than a hole: the dep edge is exactly what stops the two running together. The case worth ruling on is rework. When a dependency is invalidated and re-dispatched while its dependent is already mid-flight, both are running, and if their `owns` overlap they are writing the same paths with nothing to detect it. Whether that is worth a rule or is adequately covered by the invalidation flow is a judgment call, so it is stated here rather than written as a criterion.

## Non-goals

**Anything that would have caught the `#22` findings the auditors actually found by execution.** Those were reference-implementation and discrimination defects, which are #119's and #191's territory, and no linter reaches them.

**A rule that validates `executor_model` against `executor`'s tier.** `dispatch-guard` already refuses a dispatch whose model disagrees with the recorded `executor_model`, and the remaining gap between tier and model is not a shape this run exercised.

**Changing R2's anchor-selection algorithm.** The heuristic from #132 is defensible and the sentence-scoping is deliberate. Only the diagnostic is at issue here, because an author who can see what the rule matched can fix the prose in one pass instead of several.

## For a Coding Agent

- **Verify with:** `python3 .agent-guild/scripts/test_check_job_spec.py`, then `python3 .agent-guild/hooks/test_hooks.py` and `python3 scripts/build-plugin.py --check`
- **Start here:** `check-job-spec.py:1291-1293` for `_governs_plural_noun`, `:1303` for `find_r10_violation`, `:490-523` for `anchor_spans` and `nearest_anchor`, and `:588-615` for the R2 branch that builds the diagnostic.
- **Read first:** the rule-ordering commentary at `:22-42`, since a routing rule has to be placed against the existing R6, R7, R13, R14, R15, R16 sequence and the reasons that order exists.
- **Done when:** every acceptance criterion passes and the archive corpus is still green.

## Evidence

`kendrick/dotfiles`, at `.agent-guild/state/` and archiving to `archive/2026-08-15/`:

- `verdicts/DEC-audit-r2.md` for the false count that reached an opus round, and for the R10 variants that established the adjacency blind spot.
- `verdicts/DEC-audit-r3.md` for the eleven-variant map separating what the linters catch from what they miss, including the routing variant that passes.
- `retrospective.md`, under "What the Constitution Missed", for the linter half of the account.
