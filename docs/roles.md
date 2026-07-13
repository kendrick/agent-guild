# The Agent Guild: Roles

## The Orchestrator: The Boss Who Can't Touch the Tools

Top tier, and the only member forbidden from doing the actual work. It writes the constitution, decomposes the spec into tasks, dispatches everyone below, and rules on disputes. A hook (orchestrator-write-guard) physically blocks it from editing anything outside .agent-guild/state/ while a job runs, so "I'll just fix it myself" isn't on the menu. Its whole value is judgment and routing. The moment it starts building, the org chart collapses.

## The Literalist (worker-bulk: haiku)

The cheapest hire, and unbothered about it. Handles renames, file moves, format conversions, boilerplate, and exact-spec data entry: work with a right answer the spec already names. Won't improvise. If a task actually needs taste, it does the literal faithful thing and flags the routing mistake in its notes rather than reaching above its pay grade. Reads only its own task file and the constitution, and never peeks at anyone else's work.

## The Workhorse (worker-standard: sonnet)

The default builder. Code, config, structured content: anywhere the spec is explicit and the work is graded on correctness. Takes a clear spec in, returns a correct implementation, sets its own task to needs-check, and drops a self-report the checker will never be allowed to read. Most of the guild's actual output crosses this desk.

## The Artisan (worker-craft: opus)

The pricey hire you bring in for anything a person reads or sees: copy, interface, visual design. Writes in character with what already exists instead of a generic house style. Treats protected passages as sacred: it won't paraphrase a tagline, straighten a curly quote, or "improve" a word the manifest froze, and it runs check-protected.py on itself before finishing. A protected passage off by a single character is a blocker to this one, not a nitpick.

## The Courier (worker-courier: haiku)

The guild's first hire from outside the house, and pure transport. It carries no craft and no judgment of its own: it packs a fully self-contained build order, walks it across a shell boundary to a foreign model, confirms the artifacts actually came back, and files the same paperwork every worker files. The vendor is just a route it runs. Codex is the first one; Qwen, GLM, and Gemini are more of the same road. When a lane runs dry on quota it doesn't retry or improvise, it flags the outage and hands the task back to the Workhorse, with no ladder rung spent. Whatever it couldn't get built ships as-is with the gap named, for a checker to fail honestly.

## The Meter Reader (checker-deterministic: haiku)

Verifies the clauses that reduce to a script. Runs the exact command the task names, writes down the exit code and output, and forms no opinion whatsoever. All checks exit 0 means PASS; anything exits 1 means FAIL; a script that's missing or crashes means ERROR, never a guess. Cheap, incorruptible, and completely uninterested in what the worker claims it did.

## The Skeptic (checker-judgment: opus)

Verifies the taste and correctness clauses that need a human-style read, and trusts nothing. Its first rule is to ignore the worker's self-report entirely and never open .agent-guild/state/notes/. A worker who says "all links resolve" has told it nothing until it fetches them itself. It re-derives every claim from the artifact, quotes the evidence, and renders both light and dark when the clause is about appearance. Ships without an Edit tool on purpose: it judges, it doesn't repair.

## The Correspondent (checker-courier: haiku)

The Courier's opposite number on the verification side, and the strangest seat in the guild. You don't call it to check a clause, the Skeptic already does that, in-house and cheaper. You call it for the one thing nobody on staff can give you: a read from a mind that wasn't trained where the rest of you were trained. When the family grades its own work, a blind spot the family shares sails straight through, so the Correspondent wires the case to a different house entirely and files whatever verdict comes back, word for word, in the guild's own format. It judges nothing itself. That makes it the only member whose verdict rests partly on faith that the far side actually looked, a checker's job done with a courier's hands and a worker's "you'll have to trust I was there." Where Internal Affairs audits the house from the inside, the Correspondent reports on it from abroad.

## Internal Affairs (auditor: opus)

The one who audits the boss. Holds the orchestrator's own constitution and task breakdown to the same bar the workers face, on the principle that the orchestrator outranks workers but not the constitution. Rejects any clause that isn't falsifiable: if it can't name an artifact that would fail the clause, the clause fails. No worker can be dispatched until the auditor PASSes the constitution, which makes a rubber stamp here the most dangerous move in the building. Like the checkers, it has no Edit tool: it reports, and the orchestrator revises and resubmits.
