# Constitution: <job name>

**Job weight**: <light | standard | deep>, <one-line reason, confirmed with the user>

<!--
Phase 0 produces this ONCE. It is the single standard "done right" is measured
against—every task, every verdict, and every dispute ruling references it by
clause id. The /constitution skill writes it; the auditor agent must PASS it
(CON-audit) before any worker is dispatched (dispatch-guard enforces this).

THE WEIGHT LINE above is set by the /constitution skill in Phase 0 and read by
the auditor, which holds the clause count to that weight's ceiling and spends
its rounds from that weight's audit round budget. See CLAUDE.md's weight table.

THE FALSIFIABILITY RULE: every clause must name a concrete check method AND be
something you can state a failing example for. If you cannot describe an
artifact that violates the clause, the clause is unfalsifiable—rewrite it or
drop it. "The site should feel welcoming" is not a clause. "Every page's
<h1> matches the nav label that links to it" is.

CHECK METHOD is one of:
  - a script: .agent-guild/scripts/check-foo.sh <args>  (exit 0 = pass; deterministic)
  - a judgment call: "checker-judgment: <one-line rubric the checker applies>"
Deterministic checks route to checker-deterministic (haiku); judgment checks
route to checker-judgment (opus). A scoped-diff clause ("touch only these
paths") has a standard script—don't hand-roll it as judgment prose:
.agent-guild/scripts/check-diff-scope.py <allowed>... [--ignore <path>].

Those two are the whole list. A shell pipeline written straight into the check
is a third form nothing verifies, so hand it to the sanctioned runner instead:
check-build.sh 'one; two; exit $((a|b))'. That is still the first form, and
check-job-spec.py shell-parses whatever you pass it.

When a clause names N things, list them instead of spreading them across a
sentence. check-job-spec.py can compare a count against a list. It cannot
compare one against prose, and #117 spent an audit round on a clause that read
"five files" above six of them.
-->

## Clauses

### C-1: <short name>
- **text**: <the standard, stated so a violation is recognizable>
- **check**: .agent-guild/scripts/check-foo.sh <args>   <!-- or: checker-judgment: <rubric> -->
- **severity**: blocker   <!-- blocker | major | minor -->
- **failing example**: <one concrete artifact that would violate this>

### C-2: <short name>
- **text**:
- **check**:
- **severity**:
- **failing example**:

## Protected content

<!-- If any author words must ship verbatim, list the manifest and point every
relevant clause's check at .agent-guild/scripts/check-protected.py. -->
- manifest: .agent-guild/templates/protected-passages.md   <!-- or a job-local copy -->

## Non-goals

<!-- What this job explicitly does NOT cover, so workers don't gold-plate and
the auditor doesn't flag missing coverage that was never in scope. -->
-
