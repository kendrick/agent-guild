---
task: CON-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: PASS
checked_at: 2026-08-10T23:56:22Z
---

Round 3 audit of `.agent-guild/state/constitution.md` against `.agent-guild/state/spec.md` (the plan for #117, `source: file`). Prior rounds: `CON-audit-r0.md`, `CON-audit-r1.md`, `CON-audit-r2.md`. Clauses mapped by content, not by id.

All three r2 FAIL drivers close, and I verified each rather than taking the submission's word for it. Every clause's stated failing example is now detectable by that clause's own check or, in the one case noted below, by a named sibling clause. Coverage against the spec is complete. No two clauses contradict.

This document is sound enough to build against. The soft spots at the end are real and the decomposition has to carry them; none of them lets the job's central bars pass untested.

## Per-clause results

| clause | severity | result | description | evidence |
| ------ | -------- | ------ | ----------- | -------- |
| C-1 | major | PASS | six exact labels grepped with `-F`, each bound to a passing `ok` line; exits 1 today naming `job: derived from provenance ref`; no seventh-case ceiling | verified, exit 1 |
| C-2 | major | PASS | judgment rubric exercises the three precedence cases independently and forbids reading C-1's assertions; schema and no-null read directly | constitution.md:30-34 |
| C-3 | blocker | PASS | OR form re-verified green from repo root, all three consumers combined | verified, exit 0 |
| C-4 | blocker | PASS | derivation procedure unchanged from the one I re-derived in r1; validation still pinned to this repo's copy | verified: 18 rows, skills repo clean at `e8faecf` |
| C-5 | major | PASS | nine allowlist args verified against the script's interface, `OK: 0 path(s) in scope`; state carve-out confirmed at `check-diff-scope.py:112` | verified, exit 0 |
| C-6 | minor | PASS | rubric applies in one read; failing example is still `SKILL.md`'s literal current text ("Offer to move this run's state…", no enumeration) | guild-core/workflows/retrospective/SKILL.md:29 |
| C-7 | minor | PASS | one-line rubric; precedent form confirmed in r2 at `compose-brief.py:64` and `check-provenance.py:74` | constitution.md:60-64 |
| C-8 | minor | PASS | `commit-message.md` gives the clause a subject that exists before either commit; its absence is a stated failing example | constitution.md:66-70 |
| C-9 | major | PASS | six files, each fact enumerated; the duplication finding lands here, closing r2's D3(b). Wording caveat in W3 | constitution.md:72-76 |
| coverage | — | PASS | every spec section maps to a clause or to a non-goal that preserves its facts as checked artifacts | see "Coverage walk" |
| contradictions | — | PASS | r2's D1 is gone with the rule that caused it; I re-checked every remaining pair | see "Contradictions" |
| non-goals | — | PASS | the commit non-goal is legitimate scoping under the same test that cleared the close comment in r2 | constitution.md:82-92 |
| protected content | — | PASS | "none" is still correct | constitution.md:78-80 |

## The five questions, answered directly

### 1. Do C-1 and C-2 bind coverage and correctness independently? Yes.

Neither can pass on the other's evidence, and I confirmed the mechanism rather than the claim.

C-1's grep is bound to passing cases specifically. `check()` prints `  ok   {label}` on success and `  FAIL {label}  {detail}` on failure (`test_ledger_append.py:22-29`), so `grep -qF "ok   job: <label>"` cannot match a failing case. A missing case and a red case both exit 1, and the first missing label goes to stderr — I ran it and got `missing or failing case: job: derived from provenance ref`, matching your report. The `grep -qx 6` ceiling is gone, so a seventh `job:`-labelled case no longer produces a FAIL a deterministic checker can't explain.

C-2 is the behavior bar r1 asked for and r2 found deleted. Its rubric names the three fixtures, tells the checker to read the written line each time, and explicitly forbids substituting C-1's assertions. Six vacuous cases — the artifact r2 showed passing the old consolidated clause — fail C-2 outright, because the checker runs `ledger-append.py` itself and reads what it wrote. The reverse substitution is impossible by construction: C-1 is a script, and no rubric can talk it into passing.

The routing follows: C-1 to checker-deterministic, C-2 to checker-judgment. Two bars, two agents, different evidence, as advertised. The scratch-directory instruction is still doing the work r1's A5 identified — a script-relative `derive_job()` run from a scratch dir would resolve *this* repo's `spec.md`, whose `ref` is a `.claude/plans/` path and therefore visibly not the fixture's.

### 2. Does the commit non-goal resolve D2, or move a spec bar out of reach? It resolves it.

Both halves hold up.

**The contradiction is gone at the root.** r2's D1 was structural: the preamble forbade commits until every verdict landed, and a clause required a commit message to exist. Removing worker commits entirely and giving the message a pre-commit artifact dissolves the ordering constraint rather than negotiating with it. Nothing in the document now requires an artifact that cannot exist when its checker runs.

**Retiring the commit act is scoping, not evasion,** under the same test I applied to the close comment in r2: a clause may not retire a spec bar by substituting a different artifact, but this is not a substitution. Committing is an act taken after the work lands, by a party that is not a worker, and the constitution says so, names the branch (`fix/117-ledger-job-identity`), names both commits, and preserves the only checkable content the act carries — the message text — as C-8's artifact. r2 offered exactly two remedies for D3(a): add the clause, or add it to Non-goals and say the branch is the orchestrator's to create. The document took the second. I am not going to fail the remedy I authorized.

It also removes rather than relocates the risk r2 named. r2's concern was that a worker starting from a clean `main` commits to `main` by default. No worker commits now, so the default has no worker to trip.

The residual is that the no-commit rule is itself unchecked, and two clauses lean on it. That is W1 below, and it belongs to the decomposition, not to a fourth round.

### 3. Is `commit-message.md` a legitimate artifact or ceremony? Legitimate.

Three things make it real rather than decorative.

It is the spec's own bar, not an invention. Wrap-up bullet 2 requires a humanizer pass **on the commit messages** — the messages are a spec deliverable independent of the commits, and drafting them to a file is the only shape in which that deliverable can be audited before the commits exist.

It is the named remedy from r2's D1, with the path filled in as that diagnosis required. The alternative r2 warned about — a checker asking the worker what it intends to write — does not arise, because the checker reads a file.

Its absence fails. C-8's failing example says so outright: "no `commit-message.md`, which leaves the standing no-attribution rule with nothing checking it." So the clause cannot pass vacuously by the file never appearing, which is the specific failure ceremony usually enables.

Two mechanical points I checked. The path is writable by the agent that needs it: `orchestrator-write-guard.py` no-ops inside subagents (`orchestrator-write-guard.py:36-37`), so a worker can write under `state/`. And `.agent-guild/state/` is gitignored — the current tree holds an untracked constitution, spec, and three verdicts against a clean `git status` — so the drafted messages never leak into the commit they describe.

What `commit-message.md` does not do is bind the eventual commit to the audited text. Nothing can, from inside a job that ends before the commit. That is the same residual the close comment carries and the same one r2 accepted; noted in W2.

### 4. Coverage walk

| spec section | bar | carried by |
| --- | --- | --- |
| The job field | three-step precedence, derivation over flag | C-2 |
| The job field | `job` under `properties`, `string`, not `required` | C-2 |
| The job field | absence is the only spelling; never `null` | C-2 |
| The job field | description saying what absence means | C-9 |
| The job field | one matching quote pair, not `str.strip("'\"")` | C-7 |
| Files | schema property | C-2, C-9 |
| Files | `--job`, `derive_job()`, docstring | C-2 (behavior), C-9 (docstring) |
| Files | new test cases | C-1 |
| Files | `SKILL.md` step 3 names `log/` | C-6 |
| Files | `docs/vendor-ledger.md` | C-9 |
| Files | generated mirrors regenerated, not hand-edited | C-3 (`--check` drift), C-5 (scope) |
| The archive step | enumeration plus the reason | C-6 |
| Backfill | 18 rows, the attribution table, order preserved | C-4 |
| Backfill | nothing else touched | C-4 |
| Backfill | validated against **this** repo's amended schema | C-4 |
| Backfill | duplication reported, not deleted | C-9 (finding), non-goal (not deleted) |
| Backfill | the two out-of-scope findings reported | C-9 |
| Backfill | skills repo's frozen payload not refreshed | non-goal |
| Verification | all three suites | C-3 |
| Verification | the five new cases | C-1 (six labels, a superset) |
| Verification | the issue's reproduction verbatim | C-1's `two jobs are distinguishable`; substitution carried from r2's A4 |
| Verification | validation pass over all 18 rows | C-4 |
| Wrap-up | branch, one commit here, one there, nothing pushed | non-goal (see Q2) |
| Wrap-up | humanizer pass on messages and prose | C-8 |
| Wrap-up | `dataContracts.md`, `conventions.md` | C-9 |
| Wrap-up | close #117 with the table and the findings | non-goal, ruled legitimate in r2; facts preserved by C-4 and C-9 |

No spec requirement is uncovered. C-1's six labels are a superset of the spec's five cases (it adds `job: schema keeps the field optional`), which is over-coverage and fine.

### 5. Where a worker or checker could still guess

Four places, none of which lets a bar pass untested. They are W1 through W4 below. The one worth naming here as an answer to the question: **C-5's second failing example describes a defect C-5's check cannot report** — `plugin/` is on its own allowlist, so a hand-edit is in scope and the script says `OK`. The bar itself is intact, because C-3's `--check` catches any hand-edit that produces drift and a hand-edit that produces no drift is byte-identical to a regeneration. But the prose invites a checker to hunt for something its check won't show. In practice a deterministic checker reports the script's exit code and moves on, so this misleads a reader rather than a run.

## Contradictions

Re-checked every pair, with attention to what the no-commit rule now touches:

- The preamble's no-commit rule is unqualified, so it covers the skills repo too. C-4's "diff the file against its git baseline" needs exactly that, and gets it. r2's D1 conflict has no successor.
- C-1's coverage note against C-2's correctness rubric: complementary by design, not overlapping. C-1's note disclaims correctness explicitly.
- C-1's `.agent-guild/state/log/ledger-suite.out` against C-5's allowlist: the state carve-out in `check-diff-scope.py:112` covers it unconditionally. C-8's `commit-message.md` likewise.
- C-2's "not in `required`" against C-4's "validates against the amended schema": consistent.
- C-4's "no other field altered" against the non-goals forbidding the path and `started_at` repairs: consistent, mutually reinforcing.
- C-3's "never hand-edited" against C-5's allowlist permitting those trees: consistent; the trees must change, and only by regeneration.
- The non-goal against refreshing the skills repo's frozen payload against C-4's "never the skills repo's frozen copy": consistent.
- Preamble ordering: with commits out, no clause imposes an order any other clause forbids. The only remaining ordering fact is that C-4 and C-5 read a working tree, which the rule guarantees.

## What stays weak but acceptable, for the decomposition

### W1 — the no-commit rule is load-bearing and unchecked

The preamble says it plainly and C-5's failing example admits the consequence: a worker who committed empties `git status --porcelain` and `git diff --name-only`, and `check-diff-scope.py` reports `OK: 0 path(s) in scope` having judged nothing. The same shape weakens C-4's "no other field on any row is altered" in the skills repo, where the git-baseline diff goes empty.

Nothing in the machinery stops it. I grepped the hooks: no gate mentions commits, and `orchestrator-write-guard.py` documents that the Bash path is deliberately unguarded. This rests entirely on the contract.

The decomposition should close it at the task level, which it can do without touching the constitution:

- On the task carrying C-5, prepend a HEAD assertion to the check — `test "$(git rev-parse HEAD)" = "4958efa"` against the job's baseline — so an empty scope set can only mean an empty scope set.
- On the task carrying C-4, have the rubric confirm the archive file appears as modified in the skills repo's `git status --porcelain` before trusting the baseline diff. That repo is clean at `e8faecf` right now, so the assertion is available.
- State the no-commit rule in the task body of every task that writes files, not just in the constitution. Committing finished work is a habit, not an act of defiance, and the workers most likely to do it are the ones least likely to read the preamble twice.

### W2 — nothing binds the commit to the audited message

C-8 audits `commit-message.md`; the orchestrator later types a commit. No artifact connects them, and none can from inside the job. Same residual as the close comment, accepted on the same grounds. One operational note: Phase 3's archive step sweeps `state/` into `archive/<date>/`, so if the commits happen after the retrospective, the messages live at the archived path. Commit before archiving, or read from the archive.

### W3 — C-9's check says "five files" and the clause names six

The enumeration is schema, `ledger-append.py`, `docs/vendor-ledger.md`, `dataContracts.md`, `conventions.md` — five — and then `openQuestions.md` arrives in the next sentence carrying the three findings. The check reads "read all five files and confirm each named fact is present and accurate." The operative instruction is "each named fact," and the findings are named facts in a clause whose own title says "and the side findings are recorded," so an opus checker will not skip them. But the count gives a literal reader an out on precisely the content r2 failed this document for omitting. Have the task's `check_method` name `_working-memory/openQuestions.md` and its three findings explicitly rather than inheriting the clause's count.

### W4 — C-8's humanizer audit needs a tool checker-judgment does not have

`checker-judgment` is declared `tools: Read, Bash, Write, Grep, Glob` (`.claude/agents/checker-judgment.md:5`). No `Skill`. A checker told to "run the humanizer audit" and finding no way to invoke it may return `blocked`, which costs a round trip for nothing. The skill body is readable at `~/.claude/skills/humanizer/SKILL.md`; say so in the task. The authoring side is fine — worker roles declare no `tools:` line and inherit `Skill`, so the worker can invoke it formally the way the standing rule requires.

### W5 — the courier lane cannot execute C-2's rubric

C-2 requires writing a fixture `spec.md` and running `ledger-append.py` to produce a line. A read-only Codex courier cannot write, so the second opinion on C-2 will likely come back `blocked`. That is comparison-data loss for #34 and nothing more — the checker of record has already ruled by the time the courier goes out. Flagging it so a blocked courier verdict on that task is read as a lane limitation rather than a defect in the work.

### W6 — carried forward from r2, unadopted and still true

- **C-4's "importing"** needs `importlib.util.spec_from_file_location`; `ledger-append.py` is hyphenated and cannot be imported by module name. Both functions are module-scope (`schema_violation` at :81, `load_schema` at :128) and `SCHEMA_PATH` resolves from the script's own directory (:46), so loading the right file pulls the right schema automatically. Put the word `importlib` in the task or an opus checker spends a turn finding it.
- **C-1's grep is a substring match.** A case labelled `job: derived from provenance ref, negative case` satisfies the requirement for `job: derived from provenance ref`. Low risk given C-2 reads the behavior independently, but the labels are worth naming verbatim in the task so the worker writes them exactly.
- **C-1 does not bind suite health.** Six green `job:` cases beside a red pre-existing case still exits 0, because `bash -c` runs without `pipefail` and the suite's status is discarded by the `tee` pipeline. That is deliberate and C-3 covers it; do not let the decomposition read C-1's exit code as "the suite is green."
- **Two clauses span many files.** C-9 covers six files and C-8 covers five prose pieces plus the message file, each returning one verdict. A single missing sentence reworks everything the clause touches. Split them across tasks even though each is one clause.
- **Non-goals citing #116, #99, and the courier's local-time stamp** appear nowhere in the spec the constitution names as its source. They narrow scope rather than constrain work, so this stays harmless. Third round it has been mentioned; drop it or cite it whenever the spec is next touched.
- **The issue's verbatim reproduction** is discharged by C-1's `job: two jobs are distinguishable` rather than run by hand. Deliberate substitution, better artifact, noted so the decomposition does not schedule a manual repro that no clause requires.
