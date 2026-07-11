---
name: constitution
description: Phase 0 of a guild job. Interview the user, then write state/constitution.md—the falsifiable standard every task is checked against. Use when starting a job, defining what "done right" means, or writing or refreshing the constitution before decomposing work.
---

# Write the constitution

The constitution is the one place "done right" is defined, so every later task, verdict, and dispute ruling can point at a clause instead of arguing taste. Its governing property is **falsifiable**: every clause names a concrete check and describes an artifact that would fail it. A clause you cannot fail is a clause that verifies nothing.

Work through these steps in order. The output is `state/constitution.md` (from `templates/constitution.md`) plus, if the job has protected words, a passages manifest.

## 1. Interview

Load the question bank in [interview.md](interview.md) and work the user through it: the job's goal, its quality bars, any words that must ship verbatim, the target environments, and what's explicitly out of scope. Ask; don't assume. A constitution written from guesses fails the audit or, worse, passes and misdirects every worker.

Done when you can state the job's quality bars in the user's own terms, not generic ones.

## 2. Draft clauses

Turn each quality bar into a clause in `state/constitution.md`. Per the template, each clause carries an id, its text, a check method, a severity, and a failing example. The check method is one of:
- a script: `scripts/check-foo.sh <args>`, which routes the clause to checker-deterministic;
- a rubric: `checker-judgment: <one line>`, which routes it to checker-judgment.

State each clause so a violation is recognizable. "Every page's `<h1>` matches the nav label linking to it" is a clause. "The site feels welcoming" is not.

Done when every quality bar from the interview is a clause with a named check.

## 3. Falsify each clause

For every clause, write its failing example: a specific artifact that would violate it. This is the load-bearing step. If you cannot describe what failure looks like, the clause is unfalsifiable—rewrite it into something checkable or cut it. An unfalsifiable clause survives audit only by luck and then lets any work through.

Done when every clause has a concrete failing example and none is vague.

## 4. Manifest protected words

If the interview surfaced words that must ship verbatim (taglines, quotes, legal copy), record them in a protected-passages manifest from `templates/protected-passages.md`. Compute each hash from the exact text:

```
python3 -c 'import sys,hashlib; print(hashlib.sha256(sys.stdin.read().rstrip("\n").encode()).hexdigest())'
```

Point every clause that guards protected content at `scripts/check-protected.py <manifest>`. Skip this step only if nothing is protected.

## 5. Send it to audit

Tell the orchestrator to dispatch the **auditor** with `Audit-ID: CON-audit`. Until a CON-audit PASS verdict exists, `dispatch-guard` blocks every worker, so the constitution is verified before anything is built against it. If the audit fails, revise the flagged clauses and re-submit; do not route around it.
