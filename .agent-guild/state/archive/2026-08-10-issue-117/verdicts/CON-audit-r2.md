---
task: CON-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-10T23:47:17Z
---

Round 2 audit of the revised `.agent-guild/state/constitution.md` against `.agent-guild/state/spec.md` (the plan for #117, `source: file`). Prior rounds: `.agent-guild/state/verdicts/CON-audit-r0.md`, `.agent-guild/state/verdicts/CON-audit-r1.md`. Clauses mapped by content, not by id.

Three of r1's four defect clusters close. `--validate` is gone and correctly re-labelled a non-goal. C-2's `&&` chain is gone; I ran the OR form and it exits 0 with all three suites green. C-3's derivation and its pinned validation path are sound. The close-comment non-goal is, on the merits, legitimate scoping — with one leak, below.

The document fails on three things. Two are new this round: the ordering rule the constitution states in its own preamble makes C-7 impossible to check, and C-1's consolidation removed the last independent verification of the job's central behavior without replacing it. The third is r1's D2(c), which was a FAIL driver and is neither covered nor declared out of scope.

## Per-clause results

| clause | severity | result | description | evidence |
| ------ | -------- | ------ | ----------- | -------- |
| C-1 | major | FAIL | the count binds "six lines starting `ok   job:`", not the six named labels and not what they assert; no clause anywhere exercises `derive_job()` | constitution.md:14-23 |
| C-2 | blocker | PASS | OR form verified runnable and green from repo root, exit 0; r1's A1 closed | verified, exit 0 |
| C-3 | blocker | PASS | derivation verified in r1 and unchanged; validation now pinned to this repo's copy, which is the right fix. Import mechanics caveat in A3 | constitution.md:31-35 |
| C-4 | major | PASS | nine allowlist args verified against the script's interface, `OK: 0 path(s) in scope`; the ordering rule it states is correct for itself and for C-3 | verified, exit 0 |
| C-5 | minor | PASS | rubric applies in one read; failing example is still `SKILL.md`'s literal current text | guild-core/workflows/retrospective/SKILL.md:25 |
| C-6 | minor | PASS | one-line rubric; precedent form confirmed at `compose-brief.py:64` and `check-provenance.py:74` | constitution.md:49-53 |
| C-7 | minor | FAIL | its commit-message half cannot be checked under the preamble's ordering rule; the commit does not exist when the checker runs | constitution.md:9, 56-59 |
| C-8 | major | PASS | five files, each fact enumerated; the shape r1's A7 asked for. Missing the third finding, charged to coverage | constitution.md:61-65 |
| coverage | — | FAIL | the branch and commit shape carry no clause and no non-goal; the duplication finding lost its only home | see D3 |
| contradictions | — | FAIL | preamble/C-4 ordering vs. C-7 | see D1 |
| non-goals | — | PASS | the close comment is honest scoping, not a dodge; see the ruling in D3(b). Others narrow scope without constraining work | constitution.md:71-82 |
| protected content | — | PASS | "none" is still correct | constitution.md:69 |

## Diagnosis

### D1 — C-7 (contradiction): the ordering rule forbids the artifact C-7 checks

The preamble states it as a rule, not a preference: "**nothing is committed until every check has run.** … The commit is the last act of the job, after verdicts." C-4 repeats it: "The work stays uncommitted until every clause has a verdict."

C-7 then requires that "the commit messages … pass a humanizer audit. Commit bodies are not hard-wrapped, and no commit message carries a `Co-Authored-By` trailer." Every clause includes C-7, so when C-7's checker runs there is no commit and no commit message. The checker's only honest moves are `blocked`, or a pass on the four prose pieces that do exist plus a vacuous pass on the fifth — and a vacuous pass on the bar is the failure mode r0 and r1 both failed clauses for.

This is not r0's A5 / r1's A3 advisory ("order it in the task"). Task-level ordering could have solved it when the constitution was silent. The constitution is now explicit that no ordering exists in which C-7's subject can be checked.

The scope of the rule is also wider than its own justification. The preamble says two clauses depend on it, and names the reason: `check-diff-scope.py` reads `git status --porcelain` and `git diff --name-only`. I confirmed that is how the script builds its path set (`check-diff-scope.py:86-104`), and the same reasoning covers C-3's "diff the file against its git baseline" in the skills repo. Those two are C-3 and C-4. C-7 is neither.

Required change, either form:

- **Narrow the rule to what needs it.** Say the working tree stays uncommitted until C-3 and C-4 have verdicts, then the commit lands, then C-7 checks it — naming the invocation, e.g. `git log -1 --format=%B`. That keeps the rule's real purpose and gives C-7 a subject.
- **Or give C-7 a pre-commit subject.** Require the commit message drafted to a file the checker reads before the commit exists. If you take this route, name the path, or C-7 falls back to asking the worker what it intends to write, which is a self-report.

Whichever you pick, the `Co-Authored-By` half is the one to protect. It is a standing user rule, it is trivially violable by a default harness trailer, and right now nothing will ever look at it.

### D2 — C-1 (major): the count binds the labels' prefix, not the behavior

The count check does close r1's gap in one direction, and I verified the mechanics end to end. Today it exits 1 with zero cases; the suite prints `  ok   {label}` (`test_ledger_append.py:26`) and 37 `ok` lines; six synthetic `job:` lines make the pipeline exit 0. Behavior that ships untested does fail the clause. That half works.

But C-1 is now the only clause covering the job's central deliverable — the derivation precedence, `--job`, the omit-the-key path — and its sole check reads a line count from tests the same worker wrote. Nothing in the constitution opens `test_ledger_append.py`, and nothing runs `derive_job()` independently. r1's C-1 had the checker run the three derivation scenarios by hand in a scratch directory; the consolidation deleted that and put nothing in its place. So the trade r1 flagged did not close, it inverted: the checker now trusts the worker's assertions instead of the worker's coverage. That is the self-report the org chart exists to prevent, and routing the clause to checker-deterministic guarantees no one ever reads the file.

To the question directly: yes, the clause is still worth having, and no, its failing examples do not describe the real failure. Three artifacts pass this check:

- **Six vacuous cases.** `check(True, "job: derived from provenance ref")` six times. Count 6, exit 0, clause PASS, and `derive_job()` may not exist.
- **Six cases with the wrong labels.** The check greps a prefix, not the six strings. `job: a` through `job: f` pass. The clause's second failing example ("five cases land and the sixth is forgotten") survives whenever any other `job:`-prefixed case takes the missing one's place.
- **A red suite.** If the six `job:` cases pass and a pre-existing case breaks, the count is still 6 and C-1 passes. C-2 catches this one, so it is cross-covered — noted so the decomposition doesn't treat C-1's exit code as suite health.

There is also a failure in the other direction, which I verified: `grep -qx 6` demands exactly six. A worker who writes a seventh `job:`-labelled case — say, one covering C-6's quote-pair strip, which is the natural place to put it — gets exit 1 and a FAIL from a deterministic checker with no way to tell over-coverage from under-coverage. The constitution should not penalize test coverage, and it should not quietly push C-6's coverage out of the file.

Required change, both parts:

1. **Pin the labels and drop the exact-six ceiling.** Grep each of the six strings with `grep -qF "ok   <label>"` rather than counting a prefix. That makes the clause's text and its check say the same thing, makes a substituted case fail, and lets a seventh case exist.
2. **Have something read the cases.** Either add a judgment half to C-1 — open `test_ledger_append.py`, confirm each of the six invokes the real `derive_job()`/CLI and asserts on its output rather than on a constant — or restore r1's hand-run derivation scenarios as a second check. Part 1 without part 2 leaves the vacuous-assertion artifact passing.

If you take the judgment half, C-1 splits: the label check stays deterministic (haiku), the read routes to checker-judgment. That is the correct routing, not an escalation.

### D3 — coverage: two spec bars still carry nothing

**(a) The branch and the commit shape.** Spec Wrap-up bullet 1: branch `fix/117-ledger-job-identity` here, one commit, a separate commit in the skills repo. r1 raised this as D2(c) and the round did not address it. The non-goals cover "neither pushed"; nothing covers the branch or the commit count. The repo is on `main` with a clean worktree right now (`git rev-parse --abbrev-ref HEAD` → `main`), so a worker starting from this state commits to `main` by default. This is the cheapest deterministic check left in the document — `git rev-parse --abbrev-ref HEAD` and `git log --oneline` — and it belongs to checker-deterministic. Add the clause, or add it to Non-goals and say the branch is the orchestrator's to create. Silence is the one option that isn't available, because the constitution now has an explicit Non-goals list, which makes an unmentioned spec bar a gap rather than a scoping decision.

**(b) The duplication finding.** Spec Backfill, last line of the paragraph: "I'll note the duplication in the close comment as worth its own issue rather than quietly deleting a run's record." The constitution's non-goal repeats the judgment — "Worth its own issue; not this job's call to delete a run's record" — and C-8 enumerates exactly two findings for `openQuestions.md`: the `/Users/karnett/` paths and the fractional-seconds `started_at`. This is a third finding, and the close comment was its only spec-designated home.

Which is where the ruling you asked for lands. **The close-comment non-goal is honest scoping, not a dodge**, and it survives r1's test — a clause cannot retire a spec bar by substituting a different artifact, but this is not a substitution. Closing a GitHub issue is an act taken after the work lands, by a party that isn't a worker, on a repo nothing here is allowed to push to. The two things the comment was to carry are both preserved as checkable artifacts: the attribution table is C-3's backfilled file, and the two findings are C-8's `openQuestions.md` entries. Retiring the wrapper while keeping every fact it carried is exactly the right move.

The leak is that the non-goal took a third fact down with it. Fix it the same way you fixed the other two: add the duplication of the four #32 rows to C-8's `openQuestions.md` list. One phrase, and the reporting obligation is an artifact again rather than something someone remembers.

## Advisory (not FAIL drivers)

- **A1 — no clause states its working directory.** All three script checks resolve repo-relative paths (`scripts/build-plugin.py`, the nine allowlist args), and `check-diff-scope.py`'s docstring is explicit that git's relative paths only line up from the toplevel. Verified green from the repo root. A haiku checker dispatched with no cwd could run from `.agent-guild/` and get a `3`. One line in the preamble covers all three.
- **A2 — C-1's check leaves the checker nothing to cite.** `check-build.sh` tees `bash -c`'s output, but the pipeline's stdout is consumed by `grep -q`, so the log holds only the two `check-build.sh:` framing lines — I confirmed this on the run above. A deterministic checker gets exit 1 and cannot say which case is missing, which turns one rework round into several. Redirect the suite's output to the log (or run the suite, then grep its saved output) so the FAIL names the gap.
- **A3 — C-3's import instruction needs one mechanical word.** `ledger-append.py` is hyphenated, so `import` by module name fails; a checker needs `importlib.util.spec_from_file_location`. Both functions are module-scope as the clause assumes (`schema_violation` at :81, `load_schema` at :128) and `SCHEMA_PATH` resolves from the script's own directory (:46), so importing this repo's copy pulls this repo's schema automatically — which is what makes the "never the skills repo's frozen copy" warning self-enforcing once the right file is loaded. Say `importlib`, or an opus checker will spend a turn discovering it. Confirmed the archive file holds 18 rows and this repo's schema still has zero occurrences of `job`, so C-1's and C-3's premises both hold.
- **A4 — the issue's verbatim reproduction is discharged by a test, not run.** Spec Verification: "Then the issue's reproduction verbatim, which should now yield two rows a reader can attribute." C-1's `job: two jobs' rows are distinguishable` encodes that scenario, which is a better artifact than a manual run. Acceptable as-is; flagging it so the decomposition knows the substitution was deliberate.
- **A5 — r0's A1 and r1's A4 still apply, unchanged.** The courier's local-time stamp, #116, and #99 appear nowhere in the spec the constitution names as its source. They narrow scope rather than constrain work, so this stays harmless. Cite them or drop them.
- **A6 — no other contradictions.** I checked every remaining pair: C-1's "not in `required`" against C-3's "validates against the amended schema"; C-3's "no other field altered" against the non-goals that forbid fixing the paths and the `started_at`; C-2's "never hand-edited" against C-4's allowlist permitting those trees; C-1's omit-the-key against absence being the only spelling. All consistent. C-4's ordering rule and C-3's git-baseline diff are the same rule and agree. D1 is the only conflict in the document.
- **A7 — routing is right where it stands.** Three deterministic (C-1, C-2, C-4) and five judgment (C-3, C-5, C-6, C-7, C-8) is the correct shape, and it answers r1's A2. If you take D2's judgment half, C-1 becomes a split clause rather than a wholly judgment one — keep the label grep on haiku.

## What stays weak but acceptable, for the decomposition

Assuming D1, D2, and D3 are repaired, these are the soft spots the task set should compensate for rather than the constitution:

- **C-8 carries five files in one clause at `major`.** Its rubric is the document's best — each fact enumerated per file — but one checker reading five files returns one verdict, so a single missing sentence in `conventions.md` fails the whole clause and reworks all five. Split it across tasks even though it is one clause.
- **C-5 and C-6 are both one-read rubrics on small surfaces.** Cheap and sound. Neither needs its own task; attach them to the tasks that touch `SKILL.md` and `ledger-append.py`.
- **C-3 is the only irreversible artifact in the job** and it is in another repo, outside C-4's scope check entirely. Nothing here verifies that the skills-repo working tree stays otherwise clean. C-3's "no other field on any row is altered" covers the file; nothing covers the repo. Worth a line in the task, not a clause.
- **C-7 audits prose whose quality is a matter of taste** against a skill the checker has to invoke. It is genuinely judgment and correctly routed, but expect it to be the clause disputes come from.
