---
task: DEC-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-11T00:28:00Z
---

Round 2 audit of the seven task files under `.agent-guild/state/tasks/` against `.agent-guild/state/constitution.md` and `.agent-guild/state/spec.md`. Prior: `DEC-audit-r0.md` (FAIL, six diagnoses), `DEC-audit-r1.md` (FAIL, four).

**All four r1 diagnoses are fixed, and D7 is fixed in the right place.** Adding C-6 and C-9 to T-007 with re-confirmation rubrics closes the hole rather than papering over it, and the C-6 rubric's "even if it reads better" is the sentence that makes it enforceable. D9's count is corrected. D10's sentence is in T-005 and it covers the rework case explicitly. D8's overrides are stated on both halves and they do not contradict.

The structure is now sound. Coverage is complete in both directions, the DAG is acyclic with a single leaf, every executor/checker pair is legal, all five check commands run from the repo root, and I re-derived every number in every task file rather than taking it on trust. I found no third instance of the D1/D7 shape.

It fails on one thing, and it is inside the fix rather than beside it: **T-007's edit license is wording-only, but two of its three clauses are content clauses.** C-6 and C-9 fail on missing content. If either arrives already broken from T-005 or T-006, T-007's worker has no legal move, and the retry ladder's default answer is to burn opus's budget and escalate to fable for a fault it was forbidden to touch. A second, minor defect: the `conventions.md:63` anchor supports two of the three house overrides and points at a heading rather than the rule.

## Per-task results

| task | clauses | executor | checker | result | description | evidence |
| ---- | ------- | -------- | ------- | ------ | ----------- | -------- |
| T-001 | C-2, C-7 | worker-standard/sonnet | checker-judgment | PASS | unchanged and clean since r1; both citations re-verified | `compose-brief.py:64`, `check-provenance.py:74` |
| T-002 | C-1 | worker-standard/sonnet | checker-deterministic | PASS | unchanged; check still fails today for the right reason and names the first gap | ran it: exit 1, `missing or failing case: job: derived from provenance ref` |
| T-003 | C-3, C-5 | worker-bulk/haiku | checker-deterministic | PASS | terminal, `deps` covers all six; HEAD pin still matches HEAD | ran all three: exit 0, exit 0, `OK: 0 path(s) in scope` |
| T-004 | C-4 | worker-standard/sonnet | checker-judgment | PASS | D9 fixed — `T-004.md:58` reads "Ten rows" | verified: 10 rows at `[1, 3, 4, 6, 8, 12, 13, 14, 15, 16]` |
| T-005 | C-6 | worker-craft/opus | checker-judgment | PASS | D10 fixed at `T-005.md:36`, and it covers the re-dispatch case by name | quote of step 3 still byte-exact against `guild-core/workflows/retrospective/SKILL.md` |
| T-006 | C-9 | worker-craft/opus | checker-judgment | PASS | every count in it re-derived and exact; ownership boundary stated at `:44` | 10 / index 2 `…686223Z` / dup at `[7,8,9,10]` — all three findings correct |
| T-007 | C-8, C-6, C-9 | worker-craft/opus | checker-judgment | **FAIL** | re-confirmation rubrics are right; the edit license under them is not (D11). Anchor defect (D12) | `T-007.md:66` vs `T-007.md:23-31` |
| clause coverage | — | — | — | PASS | C-1…C-9 all carried; C-6 and C-9 deliberately double-owned, later owner governs | see section 1 |
| spec coverage | — | — | — | PASS | unchanged from r1; the three-clause T-007 introduced no gap and no orphan | see section 1 |
| dep DAG | — | — | — | PASS | acyclic, all ids resolve, single leaf T-003 | walked with `_lib.parse_frontmatter` |
| routing | — | — | — | PASS | seven of seven legal; C-6 and C-9 are judgment clauses and T-007's checker is `checker-judgment` | CLAUDE.md routing table |
| check commands | — | — | — | PASS | all five run from the repo root; quoting survives the folded scalar byte-exact | ran all five |

## 1. Coverage, unchanged and still complete

Clause direction: C-1→T-002, C-2/C-7→T-001, C-3/C-5→T-003, C-4→T-004, C-6→T-005 **and T-007**, C-8→T-007, C-9→T-006 **and T-007**. No orphan.

The double ownership is the D7 fix working as intended, and it costs one thing worth naming: after the run, C-6 and C-9 each have two verdicts. The later one governs, but nothing in the files says so, and a retrospective reading "what did C-9 come back as" finds two answers. Watch-list item, not a defect.

Spec direction is unchanged from r0 and r1 and I re-walked it: every section lands on a task or on a constitution non-goal that preserves its facts. The one asymmetry I checked and cleared is that C-8's clause text enumerates five prose pieces while its constitution `check` says "each piece of prose this job wrote", which is looser and would sweep in the working-memory files. T-007's `check_method` uses the enumeration, which matches the clause text. Correct call.

## 2. Q1 — does three clauses on T-007 recreate D3?

No, and the reason is worth stating precisely, because the surface counts look similar.

D3's complaint about the old T-006 was never "three clauses." It was that **rework redid authoring**: one missing sentence in `openQuestions.md` re-dispatched an opus worker across four authored files plus two commit messages plus two borrowed prose fixes it had already gotten right.

T-007 authors one file. Its other two clauses are re-reads with the answers supplied — C-6's rubric names what to look for in one step of one file, and C-9's rubric hands the checker the counts (`ten rows, one fractional-seconds timestamp, four duplicated rows`) instead of asking it to re-derive them from the ledger. So a C-6 or C-9 FAIL on T-007 costs a bounded revision, not a re-authoring pass. That is the right shape.

The check surface did grow: eight distinct files across three clauses, which is more than the six the old T-006 carried. r0 section 2 already settled that this is where cost belongs — the same reasoning that made T-004 correctly sized at sonnet. Cheap reads on the checker's side beat a clause nobody re-confirms.

## 3. Q2 — are the two rubrics stated identically enough?

Yes. Side by side, worker body (`T-007.md:57-59`) against check text (`T-007.md:15-20`):

| override | body | check | verdict |
| --- | --- | --- | --- |
| em dash | "stay where they beat a comma or a colon, chained directly to the text on both sides with no surrounding spaces" | "kept where they earn their place and chain directly to the text on both sides with no surrounding spaces, so §14's ban does not apply" | equivalent; the threshold wording differs ("beat a comma" vs "earn their place") but neither licenses a ban, which is what D8 was about |
| headings | "stay Title Case. The skill's §17 says lowercase; ignore it" | "stay Title Case, so §17 does not apply" | identical |
| rule of three | "fine when three is the true count. §10 is about padding to three" | "fine when three is the true count, so §10 applies only to padding" | identical |

D8's mechanism was arithmetic: `commit-message.md` needs two headings, so §17 fired no matter what the worker did, and any em dash was an automatic finding. Both are now disarmed on both sides. I confirmed the skill text the overrides displace is the text r1 quoted: §14 at `SKILL.md:171-183` ("no em dashes… treat this as a hard constraint"), §17 at `:201-206`, §10 at `:141-146`. The skill's own escape hatch at `:38` is still keyed to a user-provided writing sample and still unreachable here, which is why the overrides had to be stated rather than relied on.

**One correction to the reasoning behind the fix, which does not change the outcome.** The dispatch says the check text spells the overrides out "since `compose-brief.py` ships clause text verbatim to a courier that cannot read this repo." `compose-brief.py` does not ship `check_method` at all. `compose()` at `:207-217` assembles the brief from three things: the constitution clause blocks for every cited clause, the task's `## Spec excerpt`, and the rework diagnosis if one exists. I composed all seven briefs and grepped T-007's: `no Skill tool`, `re-confirm after the voice pass`, and `§14's ban does not apply` are all absent, while the body's `§17` and "house overrides" are present. So the courier gets the overrides — through the **body**, not the check. The redundancy was worth having anyway, since it is the checker of record that reads `check_method`, but do not carry the belief forward: on the wire, the spec excerpt is the half that travels.

## 4. Q3 — is there a third path to a green job with a violated clause?

I did not find one. I walked every clause forward from its last check to the end of the schedule and asked what edits land after it.

| clause | last checked at | edits after that point | covered by |
| --- | --- | --- | --- |
| C-1 | T-002 | none — no later task's scope includes `test_ledger_append.py` | plus C-3 re-runs the suite at T-003 |
| C-2 | T-001 | T-006 and T-007 may reword the schema description and the docstring | C-3 at T-003 re-runs the suite, whose `schema keeps the field optional` and `derived from provenance ref` cases assert C-2's facts; malformed JSON fails the same run |
| C-3, C-5 | T-003 | none — terminal | — |
| C-4 | T-004 | none touches the skills repo; nothing commits, so the dirty-file evidence survives | — |
| C-6 | **T-007** | T-003 regenerates copies, does not edit `guild-core/` | the D7 fix |
| C-7 | T-001 | same two tasks open `ledger-append.py` | **nothing** — see the weak list |
| C-8 | T-007 | T-003 touches no prose | — |
| C-9 | **T-007** | none | the D7 fix |

C-7 is the only clause verified exactly once with no automated backstop, and two later tasks open its file. I am not failing on it: reaching it requires a worker to violate an explicit prohibition ("do not touch behavior in the script or the schema", `T-007.md:66`), and every clause is violable by a worker that ignores its task. D1 and D7 were different in kind — there, a worker following its instructions *correctly* produced the violation. That is the shape I searched for and did not find a third time.

The two paths r1 left open are both still open and both still orchestrator policy rather than decomposition defects: a completed task reopening after T-003 goes green, and the DAG's inability to express a re-run edge.

## 5. Q4 — can the task files route a misattributed FAIL?

Partly, and the coverage is uneven in a way worth fixing.

**T-003 handles its own side.** `T-003.md:52` says "If a suite is red, report it — do not fix the underlying code here. That belongs to whichever task owns the file." A worker reading only its own file knows exactly what to do. What no file can say is which task the orchestrator should reopen — the file that fails is named by the check output, not by the task. So T-003's half is written down and yours is not, and yours has to stay discipline. There is no decomposition edit that fixes it, because the DAG has no reverse edge and the lifecycle has no reopen state.

**T-007 has the same hazard and none of the guardrail.** That is D11.

## 6. What I re-verified rather than took on trust

| claim | result |
| --- | --- |
| HEAD still matches T-003's pin | `164057dbe07d537136677ba3dae139e61ff2c328`, working tree clean |
| skills repo untouched | clean at `e8faecf` |
| the ten `/Users/karnett/` rows | 10, at `[1, 3, 4, 6, 8, 12, 13, 14, 15, 16]` — T-006's indices exact, T-004:58 now agrees |
| the fractional-seconds row | index 2, `2026-08-08T00:15:45.686223Z`, exactly one |
| the four duplicated rows | indices `[7, 8, 9, 10]`, byte-identical to all four rows of the #32 archive |
| the empty-artifacts row | index 17, the only one |
| `conventions.md:63` | **heading**, not the rule — the rule is `:65` (D12) |
| what `:65` actually says | em dashes unspaced, no hard wrapping, Title Case headings, comments explain why. No rule-of-three rule (D12) |
| humanizer §10 / §14 / §17 | `SKILL.md:141`, `:171`, `:201` — all three cited correctly |
| `docs/vendor-ledger.md` flags paragraph | `:49`, as T-006 says |
| `dataContracts.md` anchor | `## Vendor Call Ledger` at `:61` |
| `conventions.md` anchors | `## State File Naming` `:17`, `## Hooks and Checks` `:23` |
| T-005's verbatim quote of step 3 | byte-exact |
| the DAG | acyclic, all ids resolve, single leaf T-003 |
| all seven briefs compose | yes; every cited clause resolves in the constitution |
| the five check commands | T-002 exit 1 (right reason); T-003's three: exit 0, exit 0, `OK: 0 path(s) in scope` |

## Diagnosis

- **D11** (major; T-007): **T-007's edit license is wording-only, but two of its three clauses fail on missing content.** `T-007.md:66` grants it exactly this: "You may edit the wording of anything named above… Do not change what any of these files says, only how it says it." "Named above" is the four prose passages at `:53`; the three working-memory files are not among them, and T-007 has no license over them at all. Meanwhile its C-9 rubric (`:27-31`) fails the task if any of **six** files is missing a fact, `_working-memory/openQuestions.md` and its three counts included, and its C-6 rubric (`:23-26`) fails it if step 3 is missing its reason sentence.

  Both rubrics say "re-confirm after the voice pass," which is the intent — catch what T-007 broke. Neither says how to tell that from a fact that was never there. A `checker-judgment` handed "confirm all six files still carry every fact C-9 names" will read the six files and fail on an absent fact regardless of who dropped it. So the failure splits two ways and the task file covers one:

  - T-007's own pass trimmed it. The worker fixes it; `:61-64` warns about exactly this and explains why the humanizer's instincts are wrong there. Handled, and handled well.
  - It arrived broken, because T-006's or T-005's checker missed it. The worker cannot legally clear the FAIL. Adding a missing finding to `openQuestions.md` is content, in a file it does not own. Restoring a dropped reason sentence to step 3 is content, in a file where its license is wording-only. The instruction that covers the good case forbids the fix in the bad one.

  The cost is the retry ladder at its most expensive rung. T-007 is `worker-craft`/opus, so two retries burn against a worker with no legal move, and step 4 escalates to fable — the last rung, spent on a task whose executor was never the problem. T-003 does not have this problem, because `T-003.md:52` tells its worker to report a red suite rather than fix it. T-007 needs the same sentence and one more, because unlike T-003 it holds a partial license and the boundary is therefore fuzzier rather than absent.

  Fix, two sentences in T-007's `## Spec excerpt`: say that if a C-6 or C-9 fact is missing **before** your pass — you did not remove it — report it in your artifacts and leave it alone, because it belongs to T-005 or T-006 and a wording license does not extend to restoring content. And say the mirror in the `check_method`, so the diagnosis routes itself: a C-6 or C-9 finding must state whether the fact was present before the voice pass, since `git diff` on the file makes that answerable. That second half is what turns a stuck FAIL into a reopen of the owning task.

- **D12** (minor; T-007): **the `conventions.md:63` anchor is off by two lines and supports two of the three overrides.** Both halves cite it — `:16` in the check text ("recorded at `_working-memory/conventions.md:63`") and `:55` in the body ("recorded at `_working-memory/conventions.md:63`"). Line 63 is the section heading `## Prose Voice (docs and comments)`; the rule is line 65, which reads in full: "Em dashes chain directly to the text on both sides—like this—never wrapped in spaces. Don't hard-wrap prose lines; let the display wrap. Headings are Title Case. Comments explain the why, not the what."

  That line carries the em-dash override and the Title Case override. It does **not** carry the rule-of-three override, which lives in the user's global preferences rather than in this repo. So the claim "they are the project's own standard, recorded at `_working-memory/conventions.md:63`" is accurate for two of three and false for the third. This is more than a citation nit because of who reads it: a `checker-judgment` told an override is recorded at a specific line will open that line, find a heading, read on, find two of the three rules, and now has a reason to discount the one override that is not there — reopening a narrow version of D8 on the exact axis (§10, list shape) that C-6 exists to protect.

  Fix: cite `:65` in both places, and attribute the third override honestly — say it is this job's ruling for this prose rather than a recorded convention, or drop the anchor from that bullet. One more upside: `:65` also carries "Don't hard-wrap prose lines," which is C-8's other hard rule, so the corrected anchor supports more of the task than the current one does.

## What stays weak, for the run

- **C-7 is verified once and has no automated backstop.** T-001's checker reads the matched-pair form; no test case in C-1's six exercises quote stripping, and `docs`-shaped fixtures in the suite use an unquoted `ref`. T-006 and T-007 both open `ledger-append.py` afterward under a docstring-only license. If either C-2 or C-7 comes back into play late, re-read the reader by hand.
- **C-6 and C-9 will each have two verdicts.** T-005's and T-007's for C-6, T-006's and T-007's for C-9. The later governs. Nothing in the files says that, so say it in the retrospective rather than letting a reader pick.
- **A T-003 FAIL is not T-003's worker's fault**, and the task file can only get you halfway. `T-003.md:52` stops the worker from patching someone else's file; nothing routes the reopen. Read the failing suite's output for the file, reopen that task, re-dispatch T-003 afterward, and do not count the attempts against T-003's budget.
- **Nothing re-runs T-003 if a completed task reopens after it.** Unchanged from r1. A dispute ruling or a #34 courier disagreement that sends T-006 or T-007 back to work after T-003 is green leaves the shipped trees stale with no verdict saying so. Regenerate by hand before wrapping up.
- **The courier reads the body, not the check.** Established in section 3. Anything a courier must know has to be in the constitution clause text or the `## Spec excerpt` — putting it only in `check_method` reaches the checker of record and nobody else.
- **W5 stands.** C-2's rubric requires writing fixture files and running the script, which a read-only Codex courier cannot do. Expect `blocked` on T-001's courier verdict; that is a lane limitation, not a defect in the work.
- **C-1's exit code is not suite health, and C-1's grep is a substring match.** Both unchanged since r0. A T-002 PASS does not mean the suite is green; C-3 at T-003 is what says that.
- **W2 stands.** `commit-message.md` lives under `state/`, which Phase 3's archive step sweeps into `archive/<date>/` — and T-005's new enumeration makes that sweep more thorough. Commit before you archive.
- **T-006 and T-007 may both reword the schema description and the docstring.** Ordering resolves it, so this is duplicated effort rather than a collision. If T-006's checker fails the description on voice, that rework is wasted work T-007 would have done anyway.
