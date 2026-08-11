---
task: DEC-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-11T01:06:00Z
---

Round 3 audit of the seven task files under `.agent-guild/state/tasks/` against `.agent-guild/state/constitution.md` and `.agent-guild/state/spec.md`. Prior: `DEC-audit-r0.md` (FAIL, six), `-r1.md` (FAIL, four), `-r2.md` (FAIL, two).

**D12 closes cleanly.** Both halves cite `_working-memory/conventions.md:65`, both attribute two of three overrides to it and the third to this job, and I read line 65 to confirm it says what the citation claims: em dashes unspaced, no hard wrapping, Title Case headings. The corrected anchor now backs three of C-8's rules instead of two.

**The C-8 constitution edit is the right call and it works on the wire.** `extract_clause()` lifts the whole `### C-8:` block, so `text`, `check`, `severity`, and `failing example` all travel. I composed T-007's brief and read the three overrides in it at line 8. The unasked change did what you wanted.

**D11 closes on the worker's side and fails on the checker's.** `T-007.md:74` is correct and well-aimed: report, do not write, you hold no authoring license over the three working-memory files. That half is done. The `check_method` half is not, and it fails three separate ways at once, one of them mechanically demonstrable. Worse, it is the fourth instance of the D1/D7 shape you asked me to walk for — and this time the decomposition creates it deliberately rather than leaking it.

## Per-task results

| task | clauses | executor | checker | result | description | evidence |
| ---- | ------- | -------- | ------- | ------ | ----------- | -------- |
| T-001 | C-2, C-7 | worker-standard/sonnet | checker-judgment | PASS | unchanged; both anchors re-verified | `compose-brief.py:64`, `check-provenance.py:74` |
| T-002 | C-1 | worker-standard/sonnet | checker-deterministic | PASS | unchanged; check still fails today for the right reason | ran it: exit 1, `missing or failing case: job: derived from provenance ref` |
| T-003 | C-3, C-5 | worker-bulk/haiku | checker-deterministic | PASS | terminal; HEAD pin still matches; state carve-out confirmed in the script | ran all three: 0, 0, `OK: 0 path(s) in scope`; `check-diff-scope.py:112` |
| T-004 | C-4 | worker-standard/sonnet | checker-judgment | PASS | every row-index claim re-derived from the file, not from the table | 18 rows; karnett at `[1,3,4,6,8,12,13,14,15,16]`; dups at `[7,8,9,10]` |
| T-005 | C-6 | worker-craft/opus | checker-judgment | PASS | unchanged since r2; re-dispatch sentence at `:36` still covers the post-voice-pass case | quote of step 3 byte-exact |
| T-006 | C-9 | worker-craft/opus | checker-judgment | PASS | all three findings' counts re-derived and exact | index 2 `…686223Z`, sole fractional row; empty-artifacts row is index 17 |
| T-007 | C-8, C-6, C-9 | worker-craft/opus | checker-judgment | **FAIL** | body half of D11 fixed; check half unwritable, unrouted, and resting on evidence that cannot answer | `T-007.md:33-37`, `:74` |
| clause coverage | — | — | — | PASS | C-1…C-9 all carried | see section 1 |
| spec coverage | — | — | — | PASS | unchanged; no orphan, no gap | see section 1 |
| dep DAG | — | — | — | PASS | acyclic, all ids resolve, single leaf T-003 | walked all seven `deps` lists |
| routing | — | — | — | PASS | seven of seven legal against the CLAUDE.md table | script clauses → deterministic, rubric clauses → judgment |
| check commands | — | — | — | PASS | all five run from the repo root; folded scalars survive byte-exact | ran all five |
| briefs | — | — | — | PASS | all seven compose; every cited clause resolves | ran `compose-brief.py` on T-001…T-007 |

## 1. Coverage, still complete

Clause direction: C-1→T-002, C-2/C-7→T-001, C-3/C-5→T-003, C-4→T-004, C-6→T-005 and T-007, C-8→T-007, C-9→T-006 and T-007. No orphan clause, no task citing a clause the constitution lacks.

Spec direction: Context carries no deliverable; The Job Field→T-001 and T-002; The Archive Step→T-005; Backfill→T-004; Verification→T-002 and T-003; Files→T-001, T-002, T-005, T-006, T-003; Wrap-Up→T-006 and T-007, with commits, the close comment, and the frozen skills payload all landing on named constitution non-goals that preserve their facts. Unchanged from r0 and I re-walked it.

## 2. Q1 — does the C-8 edit break anything?

No contradiction between the new clause text and any task file. C-8's text and T-007's `check_method` enumerate the same five prose pieces. The provenance sentences agree: the constitution says the first two overrides come from `conventions.md:65`, T-007 says the first two plus the no-hard-wrap rule do, and both are true of what line 65 actually says.

One mismatch the edit inherits rather than creates, and it got sharper: C-8's `check` still reads "each piece of prose this job wrote," which is wider than the clause text's five-item enumeration. That is D15 below. It is minor because the checker of record reads `check_method`, which uses the enumeration.

The edit also confirms the r2 correction was worth acting on. I ran `compose-brief.py T-007` and read the output: the overrides are in the clause block at line 8, `- **severity**: major` sits at line 22 under C-9, and none of `check_method`'s text appears anywhere in the brief. The `check_method` reaches exactly one reader, and it is not the courier.

## 3. Q2 and Q3 — the fourth instance, and it is inside the D11 fix

The shape is a clause genuinely violated with every verdict green. Here is the walk.

`T-007.md:33-37` tells the checker: a fact that never arrived is the upstream task's defect, so report it and **pass this task on that clause**. Trace what happens when that fires on C-9.

T-007 is the last task that carries C-9. T-003 runs after it and carries C-3 and C-5 only. So a PASS on T-007 sets it `complete`, T-003 goes green on suites and diff scope, and the job ends with C-9's `openQuestions.md` finding still missing and seven pass verdicts on the record. Nothing in any task file, any clause, or the lifecycle in `CLAUDE.md` turns "reported in the verdict" into an action. There is no reopen status, no DAG edge back to T-006, and no later check.

That is the D1/D7 shape, and unlike C-7 (which requires a worker to defy an explicit prohibition) this one arrives by everyone following instructions correctly. It needs an upstream miss to start — T-006's checker erring, a dispute you rule for the worker, or a #34 courier disagreement that moves a fact back out — but that is a normal event in a system built on the premise that checkers can be wrong. Being the fourth instance is what makes it worth the round.

The C-6 case ends the same way and is quieter still, since C-6 is `minor` and a pass verdict may legally carry a minor finding. Nothing rejects it, nothing acts on it, and the retrospective sees a green board.

## 4. Q4 — what still has to be guessed

- **What severity to file the upstream-gap finding at.** D13(a). The checker is forced to choose between contradicting its instruction, misgrading a major defect as minor, or calling a real gap `info`, which the schema defines as "no defect at all."
- **Whether the courier is covered by the pass instruction.** `T-007.md:74` says "your checker has been told to distinguish… and to pass you on the second." That sentence is in the `## Spec excerpt`, so the courier reads it, sees itself plausibly described as a checker, and does not receive the reporting protocol from `check_method`. It hits the same validator with less guidance.
- **How wide C-8's audit reaches.** D15.
- **Which of C-6's and C-9's two verdicts governs.** Unchanged from r2. Still nowhere in the files.

## 5. What I re-verified rather than took on trust

| claim | result |
| --- | --- |
| HEAD still matches T-003's pin | `164057dbe07d537136677ba3dae139e61ff2c328`, tree clean |
| `conventions.md:65` content | em dashes unspaced, no hard-wrapping, Title Case headings, comments explain why — three of C-8's four rules, no rule-of-three |
| the ledger's 18 rows | 18; karnett paths on 10 at `[1,3,4,6,8,12,13,14,15,16]`; fractional `started_at` on index 2 only; empty artifacts on index 17 only |
| the four duplicated rows | `[7,8,9,10]`, byte-identical to all four rows of the #32 archive |
| row 15's stem | `T-006-sonnet-r0-codex.json`, stamped `2026-08-08T00:00:00Z` — T-004's table is right |
| `check-diff-scope.py` permits `state/` | yes, `:112`, unconditional prefix carve-out, so `commit-message.md` and `briefs/` cost T-003 nothing |
| all five check commands | T-002 exit 1 (right reason, first gap named); T-003's three: 0, 0, `OK: 0 path(s) in scope` |
| the DAG | acyclic, every referenced id exists, single leaf T-003 |
| all seven briefs compose | yes; C-8's overrides present in T-007's, `check_method` absent from it |
| pass + major is rejected | ran `validate-verdict.py` on a synthetic T-007 verdict — exit 1, see D13(a) |
| `subagent-return` enforces it | `subagent-return.py:86-105` shells out to `validate-verdict.py` on every checker return |
| no per-task snapshot exists | no stash or snapshot machinery in `hooks/` or `scripts/` outside test fixtures |

## Diagnosis

- **D13** (major; T-007 `check_method:33-37`): **the pass-and-report instruction has no writable form, no readable destination, and no actor.** All three at once, and each closes a different escape.

  **(a) The verdict cannot carry it.** C-9's severity is `major`. `validate-verdict.py:168-177` rejects any pass verdict carrying a `blocker` or `major` finding, and `subagent-return.py:86-105` runs that validator as a hard gate on every checker return, courier included. I built the verdict this instruction asks for and ran it:

  ```
  validate-verdict: findings[0].severity: verdict is 'pass' but this finding is 'major';
  a pass carries only 'info' (a clause satisfied) or 'minor' findings.
  If the defect is real, the verdict is 'fail'
  ```

  The validator's own last clause is the guild ruling against this instruction. So the checker's legal moves are: `fail`, contradicting `check_method`; `minor`, misgrading a major-severity gap; or `info`, which the schema defines as "no defect at all" and which is simply false. Every one of the three is wrong, and the checker has to pick without being told which.

  **(b) The worker's report goes where you may not read.** `T-007.md:74` says "Say so in your notes and finish." `CLAUDE.md` says of `state/notes/`: "Workers write notes; you never read them." r2's suggested wording was "report it in your artifacts," which lands in the task frontmatter you do read. The change from artifacts to notes closed the one channel that worked.

  **(c) Nothing acts on the report even if it lands.** Section 3. A PASS terminates T-007, T-003 carries neither C-6 nor C-9, and there is no reopen edge to T-005 or T-006.

  Fix direction, not a rewrite: the verdict for a genuine upstream gap has to be `fail` — that is what the validator, the schema, and the lifecycle all already agree on — with the finding's `clause_id` naming C-6 or C-9 and its description naming T-005 or T-006 as the site of the repair. Then T-007 needs the sentence T-003 already has at `:52`, in the orchestrator's direction rather than the worker's: this FAIL routes to reopening the owning task and does not count against T-007's retry budget. That preserves the D11 fix's real point (opus never burns a retry on a fault it was forbidden to touch) without buying it with a green verdict over a violated clause. `blocked` is the wrong instrument here: the check completed, it just judged someone else's work.

- **D14** (major; T-007 `check_method:33-34` and body `:74`): **`git diff` cannot answer the question it is assigned.** The instruction is "any finding must state whether the fact was missing BEFORE this task's pass or was lost during it — `git diff` over the working tree answers that directly." It does not, in exactly the cases it is invoked for.

  No worker commits (constitution, line 13), and T-003 pins HEAD to `164057db` precisely to guarantee that. So for the entire job the working tree is one cumulative diff against a single pre-job baseline, with no per-task boundary in it. I checked for a snapshot mechanism and there is none anywhere in `hooks/` or `scripts/`.

  Run the two cases. T-006 never writes the fractional-seconds finding: `git diff _working-memory/openQuestions.md` shows two findings added, the third absent. T-006 writes it and T-007's voice pass drops it: `git diff` shows two findings added, the third absent. Byte-identical. C-6 is the same story — step 3's pre-job text is at HEAD, and "T-005 never wrote the reason sentence" and "T-007 deleted it" both render as a rewritten step 3 with no reason sentence.

  The one evidence source that does answer is the upstream checker's verdict: `verdicts/T-005-judgment-r*.md` and `T-006-judgment-r*.md` are per-clause attestations that the facts were present at that moment, and T-006's rubric already requires its checker to confirm all six files fact by fact. Point the instruction there. Notes are not an option for the same reason as D13(b) and because a checker re-deriving from a worker's self-report is the thing checkers exist not to do.

- **D15** (minor; constitution C-8 `check`, visible in T-007's brief): **the clause's check is wider than its own text, and the gap is now a contradiction inside a single composed brief.** C-8's text enumerates five prose pieces. Its `check` says "run the humanizer audit over each piece of prose this job wrote," which sweeps in `dataContracts.md`, `conventions.md`, and `openQuestions.md` — prose this job wrote, in files the same brief tells T-007 it holds no authoring license over (`:53` of the composed brief). A courier reads the clause block and the body and gets both halves, with no `check_method` to break the tie, so it can fail T-007 on C-8 for voice in files T-007 is forbidden to touch.

  Contained today, because courier verdicts are comparison data and the checker of record reads `check_method`'s enumeration. r2 cleared the looseness when it was only looseness; the explicit no-license sentence turned it into a conflict. Cheap to fix while D13 and D14 are open: make C-8's `check` name the same five pieces its text does.

## What stays weak, for the run

- **C-7 is still verified exactly once with no automated backstop.** Unchanged since r2. None of C-1's six cases exercises quote stripping, and T-006 and T-007 both open `ledger-append.py` afterward under docstring-only licenses. Re-read the reader by hand before you wrap up.
- **C-6 and C-9 will each carry two verdicts.** T-005's and T-007's, T-006's and T-007's. The later governs; nothing in the files says so. Say it in the retrospective rather than letting a reader pick.
- **A T-003 FAIL is not T-003's worker's fault.** `T-003.md:52` stops the worker from patching someone else's file and that is as far as a task file can get. Read the failing suite's output for the file, reopen that task, re-dispatch T-003 after, and do not count the attempts against T-003's budget.
- **Nothing re-runs T-003 if a completed task reopens after it.** A dispute ruling or a courier disagreement that sends T-006 or T-007 back to work after T-003 is green leaves the shipped trees stale with no verdict saying so. Regenerate by hand.
- **The courier reads the clause block and the `## Spec excerpt`, never `check_method`.** Re-confirmed this round by composing T-007's brief and grepping it. Anything a second opinion must know belongs in clause text or the excerpt.
- **W5 stands.** C-2's rubric requires writing fixtures and running the script, which a read-only Codex courier cannot do. Expect `blocked` on T-001's courier verdict.
- **C-1's exit code is not suite health.** A T-002 PASS says six labelled cases are present and green, nothing more. C-3 at T-003 is what says the suite is.
- **W2 stands.** `commit-message.md` lives under `state/`, which Phase 3's archive step sweeps — and T-005's new enumeration makes that sweep more thorough. Commit before you archive.
- **T-006 and T-007 may both reword the schema description and the docstring.** Ordering resolves it, so this is duplicated effort rather than a collision.
