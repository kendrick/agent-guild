# Retrospective: Commit The Plugin Tree (Issue #21)

Seventh guild run, and the first through the haiku lane end to end: worker-bulk executed an ordered recipe, checker-deterministic transcribed five script results, and the whole build-and-verify cycle cost a fraction of the sonnet jobs. One auditor catch at Phase 0, then a clean first-attempt PASS.

## Catches

One, at CON-audit r0, same species as #22's: my C-4 check greped for "dist" but the clause also required the accompanying `# Build artifacts` comment removed — a string the grep can never match. A worker deleting the entry but orphaning the comment would have passed a check while violating the clause. One appended grep closed it, r1 verified all three states (both present, entry-gone-comment-left, both gone). Running tally says this is now the house's most common orchestrator defect: a clause whose text promises more than its check inspects. The check must cover every noun in the clause.

## The Haiku Lane Held

Routing by the work, not the job's importance, was the right call. DEC-audit walked every step for hidden judgment before approving haiku (exact find-replace, two named gitignore lines it confirmed were the only matches, a no-arg build, pre-resolved failure branches) and flagged one residual — the porcelain check excludes `.gitignore`, so an unrelated gitignore edit would be invisible to the clauses — which the orchestrator cleared by eyeballing the diff at commit time: exactly the two dist lines. Committing the epic's most consequential artifact via its cheapest worker, safely, is the routing table working as designed.

## Strain

None. First-attempt PASS, all five checks exit 0, `--check` now standing as the permanent drift gate over a derived tree.

## What Feeds The Epic

`plugin/` is committed reality: 44 files — six guild skills (init and job included), six agents, the four gates plus the nudge with its SessionStart registration live, manifest at 0.2.0 with the author object. `dist/` is gone from disk and from `.gitignore`. Remaining: #24 makes this repo the marketplace (small, unblocked now), #25 writes the install story, #26 fixes the /job handoff. After #24 lands and pushes, a colleague can run `/plugin marketplace add kendrick/agent-guild` for real — the first external install of what six jobs built.
