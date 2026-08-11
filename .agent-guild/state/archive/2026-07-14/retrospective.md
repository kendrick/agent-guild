# Retrospective: Package The Kit As A Claude Code Plugin (#15)

A dogfood run: the guild building a real piece of its own backlog. Six tasks, every one passing on its first attempt. Two catches, both on the orchestrator's own constitution, both before a single worker ran. No disputes, no escalations, no ERROR verdicts.

## Catches

Both FAILs came from the auditor during CON-audit, three rounds in.

- Round 0 caught a coverage gap. The spec required "add `dist/` to `.gitignore`" but no clause guarded it. Since every task must cite a clause, decompose couldn't have produced a task for that step, so the requirement would have gone undispatched and the build artifact left committable in the very repo the non-destructive rule protects. Adding clause C-9 closed it.
- Round 1 caught a check that passed its own failing example. C-9's first version, `git check-ignore -q`, consults git's global excludes as well as the repo's, and this host's `~/.config/git/ignore` already lists `dist/`. So the check exited 0 even with the repo `.gitignore` untouched: a green light that would have reopened the r0 gap, and a misleading one, since a fresh clone or CI runner without that global entry would still treat `dist/plugin/` as committable. The auditor built a fixture repo with a matching global excludes file to prove it, then verified the corrected check (assert the repo's own `.gitignore` is the deciding source) fails on the untouched case and passes only when the repo ignores the artifact.

Nothing reached the worker tier. Every worker task passed its checker on the first try, and the passes were earned: checkers byte-compared the packaged `_lib.py` against source, ran the packaged `test_hooks.py` to 49 passing, and cross-checked the README's claims against the files it cited.

## Strain

None at the worker tier. No retries, no tier escalations. The only place the job strained was CON-audit, three rounds to reach PASS, and that is the design working as intended. The org chart puts the auditor over the orchestrator so the standard gets stress-tested before anyone builds against it, and this run spent its whole verification budget there because that is where the defects were.

## Disputes

None. No checker verdict was contested.

## Check-Infra Debt

No ERROR verdicts; every named check ran. The auditor pre-flighted the deterministic checks against throwaway fixtures during CON-audit (process substitution through `check-build.sh`, the grep negation, the `git diff` path scoping), so by the time a checker leaned on one it was already known to fire correctly on both a passing package and the clause's stated failing example.

## What Verification Missed

The most useful output of the run:

- A check that reads ambient state can pass for the wrong reason. The C-9 defect wasn't sloppy logic; it was a check whose result depended on the author's machine, namely git's global excludes. The same trap waits in any check that consults an environment variable, an installed CLI, or user config. The rule to carry into the next constitution: a deterministic check should assert the specific source of the property it cares about, not just the observable outcome, so ambient config a teammate or CI won't share can't satisfy it.
- A wording inconsistency slipped both audits, and a worker caught it. The spec wrote the rewired hook path as bare `$CLAUDE_PLUGIN_ROOT`; the constitution and task specified the quoted `"${CLAUDE_PLUGIN_ROOT}"` form, which is the correct one, since it survives a plugin path with spaces. Structural audits check coverage and consistency, not every wording nuance, so it passed them. The T-003 worker flagged it and followed the safer form. Workers reading their spec against the constitution are a real backstop, not only executors.
- The failure machinery never ran on real work. Zero worker FAILs means the job never exercised the retry ladder, a tier escalation, or a dispute on a real artifact. Those paths are still validated only by the SMOKE fixtures. A future dogfood should include a genuinely ambiguous or hard task on purpose, so FAIL, rework, and escalate get a live rehearsal, along with a real dispute.
- The offline and structural scoping held. No clause turned out unfalsifiable in practice. The one advisory the auditor logged (C-9's grep would also match a pathological global excludes file literally named `.gitignore`) was recorded rather than blocked, since it isn't the clause's stated failing example. The live "gates fire in a fresh session" run stayed a documented manual step, as scoped.

## The Deliverable

`dist/plugin/` holds the staged package: the manifest, the agents and skills, the hooks with their rewired `hooks.json`, and a README documenting the hybrid install. It is non-destructive, with the live in-repo kit untouched and verified by C-8 on every task. The cutover, removing the in-repo tooling and switching the project onto the plugin, remains a deliberate human follow-up, out of scope by design.
