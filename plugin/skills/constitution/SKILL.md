---
name: constitution
description: Phase 0 of a guild job. Interview the user, then write .agent-guild/state/constitution.md—the falsifiable standard every task is checked against. Use when starting a job, defining what "done right" means, or writing or refreshing the constitution before decomposing work.
---

# Write the constitution

The constitution is the one place "done right" is defined, so every later task, verdict, and dispute ruling can point at a clause instead of arguing taste. Its governing property is **falsifiable**: every clause names a concrete check and describes an artifact that would fail it. A clause you cannot fail is a clause that verifies nothing.

Work through these steps in order. The output is `.agent-guild/state/constitution.md` (from `.agent-guild/templates/constitution.md`) plus, if the job has protected words, a passages manifest.

## 1. Interview

**If `.agent-guild/state/spec.md` exists** (typically written by the `/agent-guild:job` intake skill, carrying a provenance header), collapse the interview instead of running the full question bank:
1. Read the spec end to end, including its provenance header (`source`, `ref`, `fetched_at`, and `issue`/`title` when the source is a GitHub issue).
2. Derive candidate quality bars straight from the spec's own content: its stated goal, Definition of Done, deliverables, constraints, and non-goals. Each candidate becomes a clause draft per steps 2-3 below.
3. Present the candidates to the user for confirmation and adjustment. Ask only what the spec leaves genuinely open — severity rankings, protected words, or target environments the spec doesn't name.
4. Never re-ask a question the spec already answers. If the spec states the goal, the audience, a constraint, or a non-goal, treat it as settled and move on to drafting.

**If no `.agent-guild/state/spec.md` exists**, run the full interview: load the question bank in [interview.md](interview.md) and work the user through it: the job's goal, its quality bars, any words that must ship verbatim, the target environments, and what's explicitly out of scope. Ask; don't assume. A constitution written from guesses fails the audit or, worse, passes and misdirects every worker.

Done when you can state the job's quality bars in the user's own terms, not generic ones.

## 2. Draft clauses

Turn each quality bar into a clause in `.agent-guild/state/constitution.md`. Per the template, each clause carries an id, its text, a check method, a severity, and a failing example. The check method is one of:
- a script: `.agent-guild/scripts/check-foo.sh <args>`, which routes the clause to checker-deterministic;
- a rubric: `checker-judgment: <one line>`, which routes it to checker-judgment.

State each clause so a violation is recognizable. "Every page's `<h1>` matches the nav label linking to it" is a clause. "The site feels welcoming" is not.

Done when every quality bar from the interview is a clause with a named check.

## 3. Falsify each clause

For every clause, write its failing example: a specific artifact that would violate it. This is the load-bearing step. If you cannot describe what failure looks like, the clause is unfalsifiable—rewrite it into something checkable or cut it. An unfalsifiable clause survives audit only by luck and then lets any work through.

Done when every clause has a concrete failing example and none is vague.

## 4. Manifest protected words

If the interview surfaced words that must ship verbatim (taglines, quotes, legal copy), record them in a protected-passages manifest from `.agent-guild/templates/protected-passages.md`. Compute each hash from the exact text:

```
python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().rstrip("\n").encode()).hexdigest())'
```

Point every clause that guards protected content at `.agent-guild/scripts/check-protected.py <manifest>`. Skip this step only if nothing is protected.

## 5. Send it to audit

Tell the orchestrator to dispatch the **auditor** with `Audit-ID: CON-audit`. Until a CON-audit PASS verdict exists, `dispatch-guard` blocks every worker, so the constitution is verified before anything is built against it. If the audit fails, revise the flagged clauses and re-submit; do not route around it.
