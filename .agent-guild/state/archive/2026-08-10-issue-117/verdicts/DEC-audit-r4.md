---
task: DEC-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: PASS
checked_at: 2026-08-11T00:45:41Z
---

Round 4 audit of the seven task files under `.agent-guild/state/tasks/` against `.agent-guild/state/constitution.md` and `.agent-guild/state/spec.md`. Prior: `DEC-audit-r0.md` (FAIL, six), `-r1.md` (FAIL, four), `-r2.md` (FAIL, two), `-r3.md` (FAIL, three).

**All three r3 findings close.** D13's pass-and-report instruction is gone and what replaced it is the outcome the validator, the schema, and the lifecycle already agreed on. D14's `git diff` claim is gone, replaced with an evidence source that exists and a stated reason nobody has to re-derive, and the worker's report channel moved onto the finishing message, which the orchestrator reads. D15's C-8 `check` now names the same five pieces its `text` does, so the composed brief no longer carries a clause a courier could read as licensing a fail on files T-007 may not touch.

This is a PASS. The decomposition is sound enough to run. What remains is watch material, listed at the end, and one cheap edit I would take if you touch T-007 for any other reason — but not a reason to touch it on its own.

## Per-task results

| task | clauses | executor | checker | result | description | evidence |
| ---- | ------- | -------- | ------- | ------ | ----------- | -------- |
| T-001 | C-2, C-7 | worker-standard/sonnet | checker-judgment | PASS | unchanged; both quote-strip anchors re-read this round | `compose-brief.py:64`, `check-provenance.py:74`, both the matched-pair form |
| T-002 | C-1 | worker-standard/sonnet | checker-deterministic | PASS | check still fails today for the right reason | ran it: exit 1, `missing or failing case: job: derived from provenance ref` |
| T-003 | C-3, C-5 | worker-bulk/haiku | checker-deterministic | PASS | terminal; HEAD pin still matches; state carve-out re-read in the script | ran all three: 0, 0, `OK: 0 path(s) in scope`; `check-diff-scope.py:110` |
| T-004 | C-4 | worker-standard/sonnet | checker-judgment | PASS | every index claim re-derived from the file this round, not carried from r3 | 18 rows; karnett at `[1,3,4,6,8,12,13,14,15,16]`; dups `[7,8,9,10]`; row 15 stem `T-006-sonnet-r0-codex.json` |
| T-005 | C-6 | worker-craft/opus | checker-judgment | PASS | quoted step 3 still byte-exact against `SKILL.md:24` | diffed the quote against the file |
| T-006 | C-9 | worker-craft/opus | checker-judgment | PASS | all three finding counts re-derived and exact | index 2 sole fractional `…686223Z`; index 17 sole empty `artifacts` |
| T-007 | C-8, C-6, C-9 | worker-craft/opus | checker-judgment | **PASS** | D13, D14, D15 all closed; the upstream-gap path now terminates in a FAIL with a named owner | `T-007.md:33-44`, `:81`; brief `:53` |
| clause coverage | — | — | — | PASS | C-1…C-9 all carried, no orphan | see section 1 |
| spec coverage | — | — | — | PASS | no section without a task | see section 1 |
| dep DAG | — | — | — | PASS | acyclic, every id resolves, single leaf T-003 | walked it programmatically |
| routing | — | — | — | PASS | seven of seven legal against the CLAUDE.md table | script clauses → deterministic, rubric clauses → judgment |
| check commands | — | — | — | PASS | all five run from the repo root and mean what they say | ran all five |
| frontmatter parse | — | — | — | PASS | the `ORCHESTRATOR:` line does not become a key | `_lib.read_task('T-007')` yields the same 14 keys as T-003 |
| briefs | — | — | — | PASS | all seven compose; every cited clause resolves | ran `compose-brief.py` on T-001…T-007 |

## 1. Coverage

Clause direction: C-1→T-002, C-2/C-7→T-001, C-3/C-5→T-003, C-4→T-004, C-6→T-005 and T-007, C-8→T-007, C-9→T-006 and T-007. No orphan clause, no task citing a clause the constitution lacks.

Spec direction: The Job Field→T-001 and T-002; The Archive Step→T-005; Backfill→T-004; Verification→T-002 and T-003; Files→T-001, T-002, T-005, T-006, T-003; Wrap-Up→T-006 and T-007. Commits, the close comment, and the frozen skills payload all land on named non-goals. Context carries no deliverable. Re-walked, unchanged since r0.

One thin spot, named for the record rather than as a defect: spec `:64` promises to "say so plainly" that the 18 rows were validated against *this* repo's schema and not the skills repo's frozen copy. That fact survives in C-4's `check`, in T-004's excerpt, and in the constitution's last non-goal — all archived, none of them a checked artifact the way C-9's `openQuestions.md` is. The spec's own Wrap-Up bullet only asks the close comment to name the attribution table and the two out-of-scope findings, and both of those do survive as checked artifacts, so the constitution's claim on line 85 holds as written. Carry the caveat into the close comment yourself.

## 2. Q1 — do D13/D14/D15 close, and does the ORCHESTRATOR line belong in `check_method`?

**D13 closes.** `T-007.md:33-35` now says an absent fact is a FAIL and quotes the validator's own closing clause as the reason. I re-ran the reproduction you did: `validate-verdict.py:168-177` rejects `pass` + `major`, `DEFECT_SEVERITIES = ("blocker", "major")` at `:149`, and `subagent-return.py` runs the validator on every checker return. The instruction now agrees with the ruling instead of contradicting it. The courier half closes too, and this is the part I did not expect: the excerpt at `:81` — which *is* in the composed brief, at line 53 — now tells the second opinion the same thing ("Your checker will fail the clause and name the owning task"). A courier hitting a missing fact gets the pass/fail answer from the one channel it can read. That was an open Q4 item in r3 and it is gone.

**D14 closes.** The `git diff` claim is gone and its refutation is stated in the file, so no future reader re-derives it. The replacement evidence source is legal for the agent that must use it: I re-read `checker-judgment.md` looking for a prohibition on reading another task's verdict and there is none — the only forbidden directory is `state/notes/`, and "What you read" is a list of what you need, not an exclusive whitelist. So `verdicts/T-005-judgment-r*.md` and `T-006-judgment-r*.md` are reachable. The report-channel half closes too: `:81` now says "State it plainly in the message you finish with," with the reason attached.

**D15 closes.** C-8's `check` names the five pieces its `text` names, plus the authored-vs-audited split. I composed T-007's brief and read the result: clause block line 9 carries the enumeration, and there is no longer any reading under which a courier can fail T-007 on C-8 for the voice of `dataContracts.md`, `conventions.md`, or `openQuestions.md`.

**On the ORCHESTRATOR line.** It works, it reaches its addressee, and it misleads nobody — but `check_method` is the wrong field for it, and you were right to ask.

What I checked rather than assumed. It survives the frontmatter parser: `_lib.read_task('T-007')` returns the same fourteen keys as every other task, with the line intact inside the folded scalar rather than promoted to a key of its own — which was the real mechanical risk, since `_lib.py` hand-rolls its YAML. It does not reach the courier: `compose-brief.py` assembles clause blocks, `## Spec excerpt`, and `## Rework diagnosis`, and nothing else, so `check_method` never crosses the lane. It does reach you, because you read task files. And it reaches the checker of record, which is the only party it is not addressed to.

That last one is the cost, and it is small. The checker cannot act on the line, and the worst it does is tell the checker that a FAIL here is cheap — which, if it colors anything, colors it in the safe direction. Against that: `decompose/SKILL.md:22` defines the field as "the check for every clause the task cites," and both checker roles describe it as their rubric. Mixing routing policy into it makes the field mean two things.

The better home is a new `## Routing` section in the task body. `compose-brief.py` extracts sections by name and ignores the rest, so an extra section stays invisible to the courier exactly as `check_method` does today, and the worker — which reads the whole file — already has the same policy at `:81`. That is a five-minute edit with no downside. It is not worth a round on its own, and I would not spend one on it.

## 3. Q2 — the recurring shape, said plainly

Fifth walk. Here is the honest answer.

**No clause can now end this job violated with every verdict green unless an agent defies an explicit instruction in its own task file.** I walked all nine.

- C-1 is checked deterministically at T-002 and again inside C-3's full suite at T-003, and one of its six cases (`schema keeps the field optional`) reads the schema directly, so half of C-2 gets an automated backstop that re-runs last.
- C-2, C-4, C-7 are each checked once, by judgment, and nothing downstream can violate them without breaking a "wording only, not behavior" prohibition its task file states outright.
- C-3 and C-5 are terminal and deterministic.
- C-6 and C-9 are written under one task, re-confirmed under another, and the re-confirmation now terminates in FAIL rather than in a green verdict carrying a finding.
- C-8 is checked at T-007 and nothing after T-007 touches prose.

**The other shape — a task unable to clear a clause it holds — still exists, but it is now routed rather than silent, and that is the right trade.** T-007 holds C-6 and C-9 and cannot author the content behind them for `dataContracts.md`, `conventions.md`, or `openQuestions.md`. That is structural: T-007's job on those clauses is re-confirmation, not authorship. The alternative — dropping C-6 and C-9 from T-007 — buys nothing and costs a great deal, because then a voice pass that dissolves step 3's enumeration or drops a finding ships with every verdict green, which is the worse version of the same shape. The decomposition picked the handled version. Same story at T-003, whose `:52` stops a mechanical worker from patching someone else's red suite and hands the routing to you.

So: the shape is not eliminated, it is converted from a silent failure into a FAIL with an owner, and the ORCHESTRATOR line is what makes the conversion pay. That is as far as task files can carry it.

One soft spot inside that, worth watching rather than fixing. The FAIL instruction at `:33` names both clauses — "On C-6 or C-9" — so its scope is explicit and a checker that passes on an absent fact is defying it. But the *reason* it gives ("validate-verdict.py refuses a pass that carries a major finding") is true of C-9 and not of C-6, which is `minor`; the validator will happily accept `pass` + `minor`. A checker that reads the justification as the rule rather than the rule as the rule could take the pass route on C-6 alone. The imperative covers it; the argument behind the imperative does not. This is the one place where the fifth-walk answer is "defiance, but not obviously so."

## 4. Q3 — over-specification

T-007 is the densest task in the job and it is at, not past, the ceiling. Its excerpt runs 29 lines carrying seven distinct obligations, but each leads with a bolded imperative and none hides inside another's paragraph. Its `check_method` is 2,663 characters that YAML folds into one paragraph — in the file the checker reads, the clause boundaries are line breaks; through a parser they are inline markers in a wall. Both readings are legal and both are navigable, but that field is now doing four jobs (three rubrics, a meta-protocol, a routing note) and it is the reason the `## Routing` suggestion above is worth taking eventually.

The one requirement genuinely at risk of being lost in the density is not in `check_method` — it is in the excerpt, and it is the *checker* that would lose it. `:62` requires both messages be "conventional-commit style with a scope, e.g. `fix(ledger): ...`". C-8 checks the humanizer audit, the absence of hard wraps, the absence of attribution trailers, and the file's existence. It does not check commit style. So a worker who writes two well-voiced non-conventional subjects passes C-8, and since T-007 `:83` says you commit "verbatim," the style would ship. Small and cosmetic, and you read the file before you commit — but it is an excerpt requirement with nothing behind it, and a checker deciding whether style is in C-8's scope has to guess. Log it as a thing you eyeball at wrap-up.

## 5. Q4 — what still has to be guessed

- **Whether the upstream verdict can actually name the right owner.** T-005 and T-006 are both `complete` before T-007 runs, so their verdicts are always PASS attesting presence. Applied mechanically, the instruction at `:36` therefore always resolves to "the fact was there before T-007, so T-007 lost it" — including for the three working-memory files T-007 is forbidden to touch, where the true owner is T-006 by construction. The checker has the license boundary in front of it at `:81` and an opus checker should reason from it, so this self-corrects; and if it doesn't, it surfaces as a dispute rather than a green board. But the rule that would settle it in one sentence is not written down: *a fact missing from `dataContracts.md`, `conventions.md`, or `openQuestions.md` is T-006's by construction, whatever T-006's verdict says; the upstream verdict only adjudicates the files T-007 may reword.*
- **Which of C-6's and C-9's two verdicts governs.** Unchanged from r2 and r3. T-007's is later and its FAIL blocks completion, so the run behaves correctly; only a reader of the archive is left guessing. Say it in the retrospective.
- **Whether commit style is C-8's business.** Section 4.

## 6. What I re-verified rather than took on trust

| claim | result |
| --- | --- |
| HEAD still matches T-003's pin | `164057dbe07d537136677ba3dae139e61ff2c328`, tree clean |
| `state/` is invisible to C-5 | `.gitignore:5` matches `.agent-guild/state/**`; `check-diff-scope.py:110` carves it out unconditionally |
| the ledger's 18 rows | 18; karnett paths on `[1,3,4,6,8,12,13,14,15,16]`; fractional `started_at` on index 2 only; empty `artifacts` on index 17 only; no row carries `job` yet |
| the four duplicated rows | `[7,8,9,10]`, byte-identical to all four rows of the #32 archive |
| row 15's stem | `T-006-sonnet-r0-codex.json`, stamped `2026-08-08T00:00:00Z` |
| the schema is strict | `additionalProperties: false`, so a backfilled `job` is only legal after T-001 lands — T-004's `deps` covers it |
| `conventions.md:65` | em dashes unspaced, no hard wrapping, Title Case headings — three of C-8's four rules |
| the humanizer section numbers | §10 Rule of Three Overuse, §14 Em Dashes, §17 Title Case in Headings — all three overrides cite the right sections |
| `checker-judgment` has no Skill tool | `tools: Read, Bash, Write, Grep, Glob`; T-007's instruction to read the criteria from the SKILL.md file is correct |
| `worker-craft` does have it | no `tools` key, so it inherits — T-007 `:66` "You have the Skill tool" is correct |
| a checker may read another task's verdict | `checker-judgment.md` forbids `state/notes/` only |
| a worker may write under `state/` | `orchestrator-write-guard.py:38` no-ops in a subagent, so `commit-message.md` is writable |
| `validate-verdict.py` rejects pass+major | `:149` `DEFECT_SEVERITIES = ("blocker", "major")`, `:168-177`; and accepts pass+minor, which is why C-6 is the soft spot |
| T-005's quoted step 3 | byte-exact against `guild-core/workflows/retrospective/SKILL.md:24` |
| the quote-strip anchors | `compose-brief.py:64` and `check-provenance.py:74`, both the matched-pair form |
| all four build inputs are mirrored | schema, script, test, and skill all present under `plugin/project-template/` |
| the frontmatter parser survives `ORCHESTRATOR:` | 14 keys, identical to T-003's; the line stays inside the folded scalar |
| all five check commands | T-002 exit 1 naming the first gap; T-003's three: 0, 0, `OK: 0 path(s) in scope` |
| the DAG | acyclic, every referenced id exists, single leaf T-003 |
| all seven briefs compose | yes; C-8's five-piece enumeration present in T-007's, `check_method` absent from it |

## What stays weak, for the run

- **C-6's FAIL instruction is right and its stated reason is half-right.** Section 3. If T-007's checker returns `pass` on C-6 carrying a minor finding about step 3, that is the defect predicted here — treat it as a FAIL, not as a pass with a note.
- **The upstream verdict always says "present."** Section 5. If a C-9 FAIL names T-007 as the owner of a gap in `openQuestions.md`, the diagnosis is wrong about the owner even though the FAIL is right: rework T-006.
- **C-7 is verified exactly once with no automated backstop.** Unchanged since r2. None of C-1's six cases exercises quote stripping, and T-006 and T-007 both open `ledger-append.py` afterward under docstring-only licenses. Re-read the reader yourself before you commit.
- **Commit style is unchecked.** Section 4. Eyeball both subjects for `type(scope): ` before you use them verbatim.
- **Nothing re-runs T-003 if a completed task reopens after it.** A dispute ruling or a courier disagreement that sends T-006 or T-007 back after T-003 is green leaves the shipped trees stale with no verdict saying so. Regenerate by hand.
- **The HEAD pin is absolute and this is a live repo.** T-003's check fails on any commit landing on this branch mid-job, including one of yours or the user's that has nothing to do with the job. That is the guard working, but read the failure text before treating it as T-003's fault.
- **W5 stands.** C-2's rubric requires writing fixtures and running the script, which a read-only Codex courier cannot do. Expect `blocked` on T-001's courier verdict.
- **C-1's exit code is not suite health.** A T-002 PASS says six labelled cases are present and green, nothing more. C-3 at T-003 is what says the suite is.
- **W2 stands.** `commit-message.md` lives under `state/`, which Phase 3's archive step sweeps — and T-005's new enumeration makes that sweep more thorough. Commit before you archive.
- **T-006 and T-007 may both reword the schema description and the docstring.** Ordering resolves it, so this is duplicated effort rather than a collision.
- **I regenerated all seven briefs while auditing.** `state/briefs/T-001.md` through `T-007.md` are current as of this round; they will be rewritten at dispatch anyway.
