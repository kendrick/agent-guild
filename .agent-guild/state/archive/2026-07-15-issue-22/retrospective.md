# Retrospective: /agent-guild:init (Issue #22)

Fourth guild run, second through `/job` intake, and the first with a fully-collapsed Phase 0: the issue plus the plan doc settled every design call, so no user questions were needed between intake and clause-drafting. One task, one worker attempt, PASS on all six clauses.

## Catches

One, by the auditor at CON-audit r0, and it sharpened a pattern worth keeping: my C-5 "nothing else changed" clause enforced its promise with an enumerated path list and `git diff`. The auditor demonstrated two false greens — the list omitted files (including `.agent-guild/CLAUDE.md`, the very contract init copies), and `git diff` is blind to untracked strays; it verified a new file under `.claude/agents/` read as clean. The rewrite enforces the footprint repo-wide: `git status --porcelain` over `.` with a single pathspec exclude for the deliverable. r1 verified empirically that tracked edits, deletions, and untracked additions outside the exclude all fail, and gitignored paths never leak in. The generalized lesson joins the standing one: a "nothing else changed" clause must be a whole-tree assertion with explicit exclusions, never a list of places to look.

## Mid-Job Discovery Worth More Than The Job

The stale dist-era plugin coming online mid-session exposed that plugin-shipped agents carry namespaced `subagent_type` values (`agent-guild:worker-standard`), which `dispatch-guard`'s bare-name `GUILD_AGENTS` set doesn't match — in a plugin-installed project, the central gate waves every guild dispatch through ungated while the SubagentStop matcher still fires on substring. Filed as #27, blocking #21. That's the kind of integration defect no offline clause in this job could have caught; it surfaced only because the dev environment accidentally became a plugin environment.

## Strain

None. Single task, first-attempt PASS, no disputes, no escalations. The worker ran both deterministic checks before returning and the checker re-derived everything including a read of the built, namespaced copy.

## What Feeds The Epic

Init's source now exists, so the next `plugin/` build picks it up automatically — the include-when-present rule did its job with zero build-script changes (C-4 proved that in-line). Remaining before #21 can commit the tree: the nudge (#23) and the dispatch-guard namespacing fix (#27). #27 should land first among them; a committed plugin whose gates don't gate is worse than no plugin.
