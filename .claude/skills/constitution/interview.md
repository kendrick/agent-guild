# Constitution interview

The question bank for step 1. Adapt to the job; the goal is a quality bar stated in the user's terms for each area that matters, not a completed checklist.

## Goal and audience
- In one sentence, what is this job producing, and for whom?
- Who is the toughest reader or user, and what would make them reject it? (That persona often outranks the default design.)
- What does success look like a week after it ships?

## Quality bars
- What would make you send this back? Each answer is a candidate clause.
- Are there standards this must meet (WCAG level, a style guide, a performance budget, a compliance rule)? Name the exact level, not "accessible" or "fast."
- Which bars are blockers versus nice-to-have? (Maps to clause severity.)

## Protected words
- Is there any text that must appear exactly, down to the punctuation? Quotes, taglines, legal or brand copy, names.
- Who is the author of that text, and would a paraphrase be a real problem? (If yes, it goes in the protected-passages manifest.)

## Environments and surfaces
- Where does this run or render? Browsers, light and dark themes, screen readers, mobile, print, specific runtimes or versions.
- Which of those must be checked every build, not just once?

## Non-goals
- What is explicitly out of scope, so workers don't gold-plate and the auditor doesn't flag missing coverage that was never wanted?
- What existing thing should this stay consistent with rather than reinvent?

## Turning answers into clauses
For each answer that names a bar, ask two questions before writing the clause:
1. How would a machine or a checker tell pass from fail? That answer is the check method.
2. What artifact would fail this? That answer is the failing example. If you can't produce one, the bar isn't a clause yet—sharpen it until you can.
