---
task: DEC-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-11T00:18:29Z
---

Round 1 audit of the seven task files under `.agent-guild/state/tasks/` against `.agent-guild/state/constitution.md` and `.agent-guild/state/spec.md`. Prior: `DEC-audit-r0.md` (FAIL, six diagnoses).

**All six r0 diagnoses are fixed, one of them incompletely.** D1's sequencing hole is closed for the build. D2's count is corrected in the constitution, the spec, and T-006 — but not in T-004, which still says eleven. D3's split is real and the sizing is right. D4, D5, and D6 are clean; I re-ran every check command and re-checked both line citations.

The decomposition still fails, and it fails on the same shape D1 had, moved to different clauses. **T-007 is licensed to rewrite the prose that C-6 and C-9 bind, it runs after both of those clauses have been checked, and nothing re-verifies them.** T-003 closes that loop for the build and the suites; nothing closes it for the two judgment clauses whose subject files T-007 edits. A second defect sits inside T-007 as well: its worker and its checker are handed contradictory rubrics, so a disagreement on any prose carrying an em dash is not a risk but an arithmetic certainty.

## Per-task results

| task | clauses | executor | checker | result | description | evidence |
| ---- | ------- | -------- | ------- | ------ | ----------- | -------- |
| T-001 | C-2, C-7 | worker-standard/sonnet | checker-judgment | PASS | D5 fixed; both citations verified correct this round | `compose-brief.py:64` and `check-provenance.py:74` both carry the matched-pair form |
| T-002 | C-1 | worker-standard/sonnet | checker-deterministic | PASS | unchanged from r0; check still fails today for the right reason | ran it: exit 1, `missing or failing case: job: derived from provenance ref` |
| T-003 | C-3, C-5 | worker-bulk/haiku | checker-deterministic | PASS | terminal, depends on all six; D4 fixed — three numbered commands, "report each exit code separately" | ran all three: exit 0, exit 0, `OK: 0 path(s) in scope` |
| T-004 | C-4 | worker-standard/sonnet | checker-judgment | **FAIL** | still says "Eleven rows" at line 58; the D2 sweep missed this file (D9) | `T-004.md:58` vs the verified ten |
| T-005 | C-6 | worker-craft/opus | checker-judgment | **FAIL** | never told another task may revise its prose; the only silent side of a three-way boundary (D10). C-6 is also reachable-broken by T-007 (D7) | `T-005.md:34` vs `T-007.md:40` |
| T-006 | C-9 | worker-craft/opus | checker-judgment | **FAIL** | correctly rebuilt and correctly sized, but C-9's subject files are editable by T-007 downstream with no re-check (D7) | `T-006.md:42,44` vs `T-007.md:40` |
| T-007 | C-8 | worker-craft/opus | checker-judgment | **FAIL** | worker and checker get different rubrics (D8); edits C-6/C-9-bound prose with neither clause on its own ticket (D7) | `T-007.md:13-16` vs `T-007.md:42` |
| clause coverage | — | — | — | PASS | C-1…C-9 each cited exactly where the split put them; no orphan, no duplicate ownership | see coverage table |
| spec coverage | — | — | — | PASS | the split introduced no gap between the halves | see section 4 |
| dep DAG | — | — | — | PASS | acyclic, every id resolves, one leaf | parsed with `_lib.parse_frontmatter`, walked the graph |
| routing | — | — | — | PASS | seven of seven legal; no script clause on a judgment checker (D6 clear) | CLAUDE.md routing table |
| check commands | — | — | — | PASS | all four run from the repo root; quoting survives the folded scalar byte-exact | ran all four |

## 1. Does terminal-T-003 close D1?

For the build, yes. `deps: [T-001, T-002, T-004, T-005, T-006, T-007]` puts every authoring task upstream of the only task that runs `build-plugin.py`, so no edit to a build input can land after the regeneration. I enumerated the build inputs each task touches and every one has an edge into T-003: the schema and `ledger-append.py` (T-001, reworded by T-006 and T-007), `test_ledger_append.py` (T-002), `guild-core/workflows/retrospective/SKILL.md` (T-005, reworded by T-007). T-003 is the graph's single leaf. C-3's suites also re-run after T-006 and T-007 touch the docstring, which closes r0's secondary worry that a prose edit could break the module unwatched.

For judgment clauses, no — see D7. And two rework paths stay open:

- **A T-003 FAIL sends work to a task T-003 does not own.** T-003's body correctly forbids its worker from fixing a red suite. But nothing tells the orchestrator that, so the retry ladder's default — re-dispatch the same executor, same model — rebuilds a tree whose input is still wrong, fails again, and escalates a haiku worker to sonnet for a fault in T-001's code. Two retries and one escalation burn before anyone reopens the right task.
- **Anything reopened after T-003 completes re-opens the drift.** The DAG can't express "T-003 must re-run if an upstream task returns to `assigned`," and the lifecycle has no reopen edge at all. If a dispute ruling or a courier disagreement sends T-006 or T-007 back to work after T-003 is green, the shipped trees go stale and no verdict says so.

Neither is a decomposition defect I can fail on — both are orchestrator policy. Both belong on the watch list, and the first one is the likeliest thing to go wrong during this run.

## 2. T-007, new and unaudited

**Sizing: correct.** One authored file, two messages, plus a read-and-revise pass over four pieces of prose. That is one sitting, and it is the right half of the split: it is the pass that only makes sense once every other author has landed, which is exactly what `deps: [T-001, T-004, T-005, T-006]` says.

**Routing: correct.** Prose a person reads → `worker-craft`/opus. A rubric clause → `checker-judgment`. `T-004` as a dependency is defensible for the same reason r0 accepted it on the old T-006: the skills-repo commit message describes work T-004 does.

**Rubric completability: the tool gap is closed, the criteria gap is not.** `checker-judgment` declares `tools: Read, Bash, Write, Grep, Glob` (`.claude/agents/checker-judgment.md:5`) with no `Skill`, and T-007's `check_method` correctly redirects it to the readable body — `~/.claude/skills/humanizer/SKILL.md` exists and is self-contained, 48 headings, no references out to sibling files. `worker-craft` declares no `tools:` at all, so its "you have the Skill tool" is right. What the checker cannot do is apply that file and reach the same verdict the worker was aiming at. That is D8.

**Excerpt quality: good, with one absence.** The commit-message brief is concrete about scope, style, and the why (the task-id collision, one timestamp wrong). Both hard rules are stated in the body and re-stated in the check. The list of what the audit looks for is a real working list rather than a pointer. The absence is that nothing in the excerpt tells the worker that the prose it is licensed to rewrite is load-bearing under two other clauses.

## 3. The T-005 / T-006 / T-007 boundary

Two of the three sides are stated and correct. T-006 is told plainly that it does not own `guild-core/workflows/retrospective/SKILL.md` (`T-006.md:44`). T-007 is told it may edit that step's wording and why that does not collide (`T-007.md:40`): T-005's clause is about whether the step instructs, T-007's is about how it reads. A worker reading only its own file knows what to do in both cases.

T-005 is the silent side. Its body says only that "a later task regenerates those from this one," about the generated copies. It never says another task may revise its wording. That reads fine on the first pass and badly on a rework: a T-005 worker re-dispatched after T-007 has edited step 3 opens the file, finds prose it did not write, has nothing in its task explaining why, and the natural move is to restore its own version — silently undoing the C-8 fix that T-007's checker already passed. That is D10.

The ownership question the boundary does not answer at all is who is accountable for step 3 still satisfying C-6 after T-007 rewrites it. Neither task says. That is D7.

## 4. Did the split leave a gap?

No. I walked both halves against the old T-006 and against the spec.

| what old T-006 carried | now | covered |
| --- | --- | --- |
| `docs/vendor-ledger.md` | T-006 | ✓ |
| `_working-memory/dataContracts.md` | T-006 | ✓ |
| `_working-memory/conventions.md` | T-006 | ✓ |
| `_working-memory/openQuestions.md`, three findings | T-006, with indices | ✓ |
| prose fixes to the schema description and docstring | T-006 (may) and T-007 (may), T-007 last | ✓, overlap not gap |
| `commit-message.md`, two messages | T-007 | ✓ |
| the humanizer pass | T-007 | ✓ |
| C-5's scope check | T-003 | ✓ |

Clause direction: C-1→T-002, C-2/C-7→T-001, C-3/C-5→T-003, C-4→T-004, C-6→T-005, C-8→T-007, C-9→T-006. Each clause on exactly one task now, which is cleaner than r0's state where C-5 sat on two. Spec direction is unchanged from r0 and still complete; the wrap-up section's two halves land on T-006 and T-007 respectively, and the branch/close-comment items remain constitution non-goals.

The content facts C-9 needs in the two files T-001 authors are instructed in T-001 (`:35` for the description, `:57` for the docstring) and verified in T-006, which depends on T-001. That seam is sound.

## 5. What I re-verified rather than took on trust

| claim | result |
| --- | --- |
| the count is ten | `grep -c` gives 10; a per-row walk gives 10 at `[1, 3, 4, 6, 8, 12, 13, 14, 15, 16]` — T-006's indices are exact |
| the fractional-seconds row | index 2, `2026-08-08T00:15:45.686223Z`, one row — T-006 correct |
| `compose-brief.py:64` | correct; `if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'"` |
| `check-provenance.py:74` | correct, same form |
| the HEAD pin | `164057dbe07d537136677ba3dae139e61ff2c328` is HEAD; working tree clean; skills repo clean at `e8faecf` |
| T-005's verbatim quote of step 3 | byte-exact against `guild-core/workflows/retrospective/SKILL.md` |
| `commit-message.md` under `state/` passes C-5 | yes, `check-diff-scope.py` permits `.agent-guild/state/` unconditionally (its docstring, and confirmed by the run) |
| T-003's three commands | exit 0, exit 0, `OK: 0 path(s) in scope` |
| T-002's command | exit 1, names the first missing label |
| the DAG | acyclic, all ids resolve, single leaf T-003 |

## Diagnosis

- **D7** (major; T-005, T-006, T-007): **T-007 rewrites prose that C-6 and C-9 bind, after both clauses have been checked, and nothing re-verifies them.** T-007's scope for its voice pass is "the `job` description in `.agent-guild/schemas/vendor-call.schema.json`, `ledger-append.py`'s module docstring, step 3 of `guild-core/workflows/retrospective/SKILL.md`, and the addition to `docs/vendor-ledger.md`" (`T-007.md:40`). Three of those four are C-9's subject — the clause requires the description to say what the field holds and that absence means unattributed, the docstring to document the three-step precedence, and `docs/vendor-ledger.md` to document the field and its derivation. The fourth is C-6's entire subject. T-007's `deps` put it after T-005 and T-006, so both clauses are `complete` before it starts. T-007's own clause is C-8, which asks how the prose reads and nothing about what it must still contain. T-003 follows, but carries only C-3 and C-5 — suites and diff scope, which cannot see a missing sentence. The job can therefore finish with C-9 (major) or C-6 (minor) violated and every verdict green. This is r0's D1 with the build swapped out for a judgment clause.

  It is not a hypothetical, because the audit T-007 runs pushes in exactly the direction the clauses forbid. `~/.claude/skills/humanizer/SKILL.md` §10 is rule-of-three overuse, §16 is inline-header vertical lists, and the skill's general posture is to dissolve enumerations into prose. C-6 requires that step 3 "names `log/` inside an enumeration" and gives the reason, and explicitly fails "a parenthetical aside that mentions logs without instructing." A worker doing a competent humanizer pass turns `tasks/`, `verdicts/`, `disputes/`, `notes/`, `log/`, `briefs/` into a sentence, drops the reason clause as inflated significance, and has followed T-007's instruction not to change what the step *says* while breaking C-6 outright. Same mechanism for C-9's "an absent key means unattributed" in the schema description, which reads as exactly the kind of clarifying tail a voice pass trims.

  Fix, cheapest version: add C-6 and C-9 to T-007's `clauses`, and append to its `check_method` that after the voice audit the checker re-confirms C-6's enumeration-plus-reason in step 3 and C-9's three named facts in the description, the docstring, and `docs/vendor-ledger.md`. Routing stays legal — both are judgment clauses and T-007's checker is already `checker-judgment`. Then say in T-007's body that these four pieces of prose are load-bearing under clauses it does not own, quote what each must still contain, and state that a voice fix which drops a required fact fails the task. Narrowing T-007's scope instead is not available: C-8's clause text names all of this prose, so the constitution requires the edit license.

- **D8** (major; T-007): **the worker and the checker are held to different rubrics, and they contradict on em dashes and headings.** T-007's body tells its worker "Keep em dashes where they genuinely beat a comma or a colon, unspaced. Keep title-cased headings" (`T-007.md:42`). Its `check_method` tells the checker to "read the audit criteria directly from `~/.claude/skills/humanizer/SKILL.md` and apply them yourself" (`T-007.md:13-15`), relaying none of those caveats. That file's §14 reads: "The final rewrite contains no em dashes (—) or en dashes (–). The em dash is one of the most reliable AI tells, so treat this as a hard constraint, not a 'use sparingly' preference," followed by "Before returning the final rewrite, scan it for `—` and `–`. Any hit means the draft isn't done." §17 bans title case in headings. So a worker that follows its task exactly produces prose its checker is instructed to fail, on a clause whose failing example is about voice rather than punctuation. `commit-message.md` requires two headings, so §17 fires whatever the worker does.

  The skill has an override — §38, "A sample outranks this skill's style rules, including the em dash rule in §14" — but it is keyed to a user-provided writing sample, and no task supplies one to either agent. So the escape hatch is unreachable as decomposed. The house rules do exist in this repo, at `_working-memory/conventions.md:63-65`: "Em dashes chain directly to the text on both sides—like this—never wrapped in spaces. Don't hard-wrap prose lines; let the display wrap. Headings are Title Case." Nothing in T-007 points either agent at them.

  Fix: relay the same three caveats to the checker in `check_method`, and anchor them rather than paraphrasing — `_working-memory/conventions.md:63-65` outranks §14, §16, and §17; unspaced em dashes are not a defect; Title Case headings are not a defect; genuinely list-shaped content stays a list and only the tripartite tic counts. Worth pushing the same sentence into C-8's `check` text and re-submitting CON-audit, since `compose-brief.py` ships cited clause text verbatim to the courier lane and the courier will otherwise audit against the unmodified skill.

- **D9** (minor; T-004): **the D2 sweep missed a file — T-004 still says eleven.** `T-004.md:58` reads "Eleven rows record absolute artifact paths under a `/Users/karnett/` home that does not exist on this machine." The correct number is ten, which is what the constitution, the spec, and T-006 now say. Not load-bearing for C-4, which does not check the count, so this will not fail T-004 on its own. It matters because it is the last surviving copy of a number two tasks describe: a `checker-judgment` that reads T-004 for context while checking T-006 finds the two task files disagreeing about the same file, and the correct move at that point — trust the ledger — is only written down in T-006. Fix: `T-004.md:58`, eleven → ten.

- **D10** (minor; T-005): **T-005 is not told that another task may revise its prose.** r0's D3b asked for this in both directions. T-006 got its half (`T-006.md:44`) and T-007 got its half (`T-007.md:40`); T-005 says only "a later task regenerates those from this one," which is about the generated copies, not the wording. On the first pass this costs nothing, because T-005 runs before T-007. It costs on a rework: a T-005 worker re-dispatched after T-007 has edited step 3 finds its own prose rewritten by an agent it has never heard of, with no instruction covering the case, and restoring its version is the natural response — which reverts a C-8 fix that already passed, with T-007 complete and nothing scheduled to notice. Fix: one sentence in T-005 saying a later task may revise the step's wording for voice without changing what it instructs, and that a rework should edit the current text rather than restore the original.

## What to watch during the run, once these are fixed

- **A T-003 FAIL is not a T-003 worker problem.** Its body forbids its own worker from fixing a red suite, which is right, but the retry ladder's default is to re-dispatch that worker. Two retries and an escalation to sonnet will burn before the actual owner is reopened. Read a T-003 C-3 failure as naming the task that owns the failing file, reopen that task, and only then re-dispatch T-003 — and do not count those attempts against T-003's budget.
- **Nothing re-runs T-003 if a completed task reopens after it.** The DAG has no reverse edge and the lifecycle has no reopen state. If a dispute ruling or a #34 courier comparison sends T-006 or T-007 back to work after T-003 is green, regenerate again by hand before wrapping up.
- **W2 from r0, now with a real file behind it.** `commit-message.md` lives under `state/`, which Phase 3's archive step sweeps into `archive/<date>/`. T-005's own new enumeration will make that sweep more thorough, not less. Commit before you archive, or the audited messages are at the archived path.
- **W5 from r0 stands.** C-2's rubric requires writing fixture files and running the script, which a read-only Codex courier cannot do. Expect `blocked` on T-001's courier verdict and record it as a lane limitation rather than a defect in the work.
- **C-1's exit code is not suite health**, and **C-1's grep is a substring match** — both unchanged from r0. Do not read a T-002 PASS as "the suite is green"; C-3 in T-003 is what says that.
- **T-006 and T-007 both may reword the schema description and the docstring.** Ordering resolves it (T-007 last), so this is duplicated effort rather than a collision. If T-006's checker fails the description's prose and T-007 then rewrites it anyway, the rework was wasted; consider telling T-006's worker to leave voice alone and write for accuracy.
