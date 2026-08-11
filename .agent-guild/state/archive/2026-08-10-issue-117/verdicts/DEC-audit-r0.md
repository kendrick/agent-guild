---
task: DEC-audit
checker: auditor
vendor: anthropic
model: claude-opus-5
verdict: FAIL
checked_at: 2026-08-11T00:09:23Z
---

Round 0 audit of the six task files under `.agent-guild/state/tasks/` against `.agent-guild/state/constitution.md` (PASSed at `CON-audit-r3.md`) and `.agent-guild/state/spec.md`. No prior `DEC-audit-r*` exists.

Clause coverage is complete, the graph is acyclic, every executor/checker pair is legal under the routing table, and every check command runs as written from the repo root — I ran all four of them. The decomposition fails on a sequencing hole, not a coverage hole: **two tasks edit build inputs after the only task that runs the build, and no edge or check catches the drift they create.** C-3 is the constitution's one `blocker` alongside C-4, and as decomposed the job can finish with it unmet and every verdict green.

Three further defects: a factual error T-006 instructs its worker to write down and its checker to verify, the T-006 sizing you asked about (it is over the line, and W6 told you so in advance), and a check-string shape a haiku checker has to interpret.

The three W-items you acted on are correctly carried. W1's HEAD pin uses the right sha — `164057dbe07d537136677ba3dae139e61ff2c328` is HEAD right now, and `4958efa` was stale by six commits, not four. W3's six files are all named in T-006's `check_method` with `openQuestions.md` explicit. W4's redirect to the readable skill body is correct and necessary: `checker-judgment` is declared `tools: Read, Bash, Write, Grep, Glob` at `.claude/agents/checker-judgment.md:5` with no `Skill`, and `~/.claude/skills/humanizer/SKILL.md` exists.

## Per-task results

| task | clauses | executor | checker | result | description | evidence |
| ---- | ------- | -------- | ------- | ------ | ----------- | -------- |
| T-001 | C-2, C-7 | worker-standard/sonnet | checker-judgment | PASS | excerpt self-contained: frontmatter sample, verbatim matched-pair form, three-step precedence, the cwd-vs-script-relative warning. One wrong line citation (D5) | T-001.md:37-55 |
| T-002 | C-1 | worker-standard/sonnet | checker-deterministic | PASS | six labels verbatim in the excerpt and in the grep; `check()` output shape explained; temp-dir fixture rationale given | ran it: exit 1, `missing or failing case: job: derived from provenance ref` |
| T-003 | C-3, C-5 | worker-bulk/haiku | checker-deterministic | **FAIL** | the only task that runs `build-plugin.py`, and nothing sequences it after T-005 or T-006 (D1). `followed by` needs interpretation from a zero-discretion checker (D4) | T-003.md:11-12,16 |
| T-004 | C-4 | worker-standard/sonnet | checker-judgment | PASS | attribution table, discriminators, and both hard rows verified true against the file; `importlib` snippet carries an absolute path; the dirty-file assertion is stronger than a HEAD pin | verified: 18 rows, rows 7-10 byte-identical to #32's ledger, skills repo clean at `e8faecf` |
| T-005 | C-6 | worker-craft/opus | checker-judgment | **FAIL** | body promises "a later task regenerates those from this one"; no such edge exists in any task's `deps` (D1) | T-005.md:34 vs T-003.md:16 |
| T-006 | C-8, C-9, C-5 | worker-craft/opus | checker-judgment | **FAIL** | records a false count its own check must verify (D2); three clauses over seven files in one dispatch (D3); C-8 obliges it to edit T-005's file, unsaid (D3b); script clause on a judgment checker (D6) | T-006.md:5,19-20,40 |
| clause coverage | — | — | — | PASS | C-1…C-9 each cited by at least one task; no clause orphaned | see coverage table |
| spec coverage | — | — | — | PASS | every spec section lands on a task or a constitution non-goal that preserves its facts | see coverage table |
| dep DAG | — | — | — | **FAIL** | acyclic and every referenced task exists, but two required edges are missing (D1) | see Q4 |
| routing | — | — | — | **FAIL** | five of six correct; T-006 routes a script clause to checker-judgment (D6) | CLAUDE.md routing table |
| check commands | — | — | — | PASS | all four run as written from the repo root; quoting reproduces exactly | ran all four |

## 1. Coverage

Clause direction, no orphans:

| clause | carried by | check type matches clause |
| --- | --- | --- |
| C-1 | T-002 | script → checker-deterministic ✓ |
| C-2 | T-001 | rubric → checker-judgment ✓ |
| C-3 | T-003 | script → checker-deterministic ✓ |
| C-4 | T-004 | rubric → checker-judgment ✓ |
| C-5 | T-003, T-006 | script → deterministic in T-003 ✓, judgment in T-006 ✗ (D6) |
| C-6 | T-005 | rubric → checker-judgment ✓ |
| C-7 | T-001 | rubric → checker-judgment ✓ |
| C-8 | T-006 | rubric → checker-judgment ✓ |
| C-9 | T-006 | rubric → checker-judgment ✓ |

Spec direction, no orphans:

| spec section | task |
| --- | --- |
| The job field (precedence, schema shape, no-null, quote pair) | T-001 |
| Files → schema, `ledger-append.py` | T-001 |
| Files → `test_ledger_append.py` | T-002 |
| Files → `SKILL.md` step 3 | T-005 |
| Files → `docs/vendor-ledger.md` | T-006 |
| Files → generated mirrors | T-003 |
| The archive step | T-005 |
| Backfill → 18 rows, table, order preserved, validation | T-004 |
| Backfill → the two out-of-scope findings, the duplication finding | T-006 |
| Verification → three suites, `--check` | T-003 |
| Verification → five new cases + the issue's repro | T-002 (six labels, a superset) |
| Wrap-up → commit messages, humanizer | T-006 |
| Wrap-up → `dataContracts.md`, `conventions.md` | T-006 |
| Wrap-up → branch, commits, close comment | constitution non-goals, ruled legitimate in CON-audit r2/r3 |

Nothing in either direction is uncovered. Coverage is not why this fails.

## 2. One-dispatch sizing

T-003 is the opposite problem from the one you flagged: its work is one command (`build-plugin.py`) and its check is `--check` plus a scope script, so the paired check costs roughly what the work costs. That is still justified — C-3 is a `blocker` and the doer must not be the judge — but it argues for folding the regeneration into the terminal task D1 needs anyway, rather than leaving it as a standalone dispatch that runs too early.

T-001, T-002, T-004, T-005 are each one sitting. T-004 is the largest of them, and it is sized correctly because you handed the worker the answer table, both adversarial rows, and the `importlib` snippet; the re-derivation cost sits with the checker, where it belongs.

**T-006 is over the line, and it is over on three axes at once.** It authors four files plus `commit-message.md`, revises prose in two files it did not write, and carries three clauses whose combined check surface is six files, a humanizer audit, a HEAD assertion, and a nine-argument scope script. Your instinct is right and W6 named it in advance: "Two clauses span many files… Split them across tasks even though each is one clause." The decomposition went the other way and merged a third clause in. The concrete cost is the retry ladder: a single missing sentence in `openQuestions.md` FAILs the task, and rework re-dispatches an opus worker over the commit messages, the docs, the working-memory files, and the two borrowed prose fixes it already got right. With D2 sitting in the same task, that rework is not hypothetical.

## 3. Routing

Executor tiers are right. T-003 mechanical → worker-bulk/haiku. T-001, T-002, T-004 clear-spec correctness → worker-standard/sonnet; T-004 is defensible at sonnet specifically because the attribution table is supplied rather than derived. T-005, T-006 prose a person reads → worker-craft/opus.

Every checker can execute its own `check_method` with the tools its role declares. Both checker roles carry `Read, Bash, Write, Grep, Glob`, so T-003's `checker-deterministic` can run both scripts and T-006's `checker-judgment` can run the C-5 script. The one genuine tool gap in the constitution — C-8's humanizer — is closed by T-006 pointing at the skill body.

The routing defect is a rule violation rather than a capability one: T-006 puts a deterministic script clause (C-5) on a judgment checker, against "A clause checked by a script routes to `checker-deterministic`." An opus checker handed a script tends to narrate its output rather than transcribe an exit code.

One risk that is not a defect but will bite: T-003's C-3 binds the health of files T-003 does not own, and its body correctly forbids the worker from fixing them. A red suite there produces a FAIL that a haiku worker cannot clear, and the retry ladder will burn a tier and escalate a task whose executor was never the problem. Read a T-003 C-3 FAIL as a signal to reopen T-001 or T-002, not as a T-003 retry.

## 4. The dep DAG

Acyclic, and every referenced id exists: `T-001 → T-002 → T-003`, `T-001 → T-004 → T-006`, `T-005 → T-006`. No cycle, two leaves (T-003 and T-006).

Every declared edge is real, and I checked rather than assumed:

- `T-002 → T-001`: the tests exercise the flag T-001 adds.
- `T-003 → T-001, T-002`: both edit files with generated mirrors (`ledger-append.py` and `test_ledger_append.py` both exist under `plugin/project-template/.agent-guild/scripts/` and the `plugins/` twin), so the build must follow both.
- `T-004 → T-001`: T-004 validates by importing `load_schema()` from this repo's script; without T-001 the schema has no `job` and the pass is meaningless.
- `T-006 → T-001`: it revises prose T-001 authored.
- `T-006 → T-005`: real, though not for the reason the task body gives — C-8's clause text names "the rewritten retrospective step" among the prose T-006 must audit.
- `T-006 → T-004`: the softest edge in the set. The three findings are properties of the pre-backfill file and derivable without T-004 running. It holds up because the skills-repo commit message describes work T-004 does. Keep it; it is not defensive enough to remove.

The two missing edges are D1.

## 5. Spec excerpts

This is the criterion you expected to have missed, and it is the one you did best on. A cold worker can act on all six. T-002 carries the labels verbatim and explains why they are load-bearing. T-004 carries the table, the two contradicting timestamps, and runnable validation code with an absolute path. T-005 quotes the current step 3 verbatim — I diffed it against `guild-core/workflows/retrospective/SKILL.md:24-29` and the quote is exact — and its enumeration matches a real archive layout (`briefs/ log/ notes/ tasks/ verdicts/` plus the three top-level files, per `~/repos/skills/.agent-guild/state/archive/2026-08-08-issue-27/`). T-006's anchors resolve: `## Vendor Call Ledger` at `dataContracts.md:61`, both `## State File Naming` and `## Hooks and Checks` in `conventions.md`, and `docs/vendor-ledger.md:49` is indeed the flags paragraph.

Two excerpt defects, both narrow: T-001's wrong line citation (D5) and T-006's silence about the retrospective step its own clause obliges it to audit (D3b).

## 6. The check commands

All four run from the repo root as written. Quoting survives the folded block scalar — I parsed each task with the kit's own `_lib.parse_frontmatter`, not with PyYAML, since that is what the hooks use, and `str.strip("'\"")` in T-001 and the nested double quotes in T-002 come through byte-exact.

| command | result |
| --- | --- |
| T-002 C-1 | exit 1, `missing or failing case: job: derived from provenance ref` — fails today for the right reason and names the first gap |
| T-003 C-3 | exit 0, `136 passed, 0 failed` plus a clean `--check` |
| T-003/T-006 C-5 HEAD guard | exit 0 against the real HEAD |
| T-003/T-006 C-5 scope | `OK: 0 path(s) in scope`, exit 0 |

The long single-quoted loop in T-002 is fine: no single quote appears inside it, `$L` expands in the inner `bash -c` that `check-build.sh:36` runs, and the three-space `ok   job: ` separator matches the suite's `check()` output. The one shape problem is D4.

## Diagnosis

- **D1** (blocker; T-003, T-005, T-006): **nothing regenerates or re-checks the shipped trees after T-005 and T-006 edit build inputs.** `build-plugin.py --check` byte-compares a fresh build against the committed trees (`filecmp.cmp(fresh, committed, shallow=False)`, `scripts/build-plugin.py:988`). T-005 edits `guild-core/workflows/retrospective/SKILL.md`, which renders into `.claude/skills/`, `plugin/skills/`, and `plugins/agent-guild/skills/`. T-006 edits the schema's `job` description and `ledger-append.py`'s docstring in place (`T-006.md:46`), both of which render into two project-templates. T-003 is the only task that runs the build and the only task carrying C-3, and its `deps` are `[T-001, T-002]` — neither T-005 nor T-006 is upstream of it, and neither depends on it. The DAG therefore permits, and scheduling order encourages, T-003 to run and pass before either edit lands, after which no check re-runs.

  I proved the drift rather than inferring it: appending one line to `guild-core/workflows/retrospective/SKILL.md` and re-running `--check` gives exit 1, `dogfooded Claude wrappers diverge from the shared core (1 difference(s)): skills/retrospective/content differs: SKILL.md`. I restored the file; `git status --porcelain` is empty and `--check` is green again.

  This is C-3's own failing example ("the #43 failure repeating") and the spec's "editing one ships broken", on a `blocker` clause, reachable with every verdict green. It also means the C-2 behavior bar and the test suite never re-run after T-006 touches `ledger-append.py`, so a docstring edit that breaks the module is caught by nothing.

  Fix: add a terminal task — call it T-007 — with `deps: [T-002, T-003, T-004, T-005, T-006]`, executor `worker-bulk`/`haiku`, checker `checker-deterministic`, carrying C-3 and C-5. Its work is `python3 scripts/build-plugin.py` and nothing else; its `check_method` is T-003's two commands verbatim. Then drop C-3 and C-5 from T-003 (leaving T-003 as the mid-job regeneration it already is, or folding it into T-007 entirely), drop C-5 from T-006, and correct T-005's "a later task regenerates those from this one" to name T-007. The job then has one leaf, and the last thing that happens before the orchestrator commits is a fresh build plus a scope check.

- **D2** (major; T-006): **the "eleven rows" finding is false — the file has ten.** `T-006.md:40` instructs the worker to record "Eleven of the 18 rows record absolute artifact paths under `/Users/karnett/`". Counted two ways against `~/repos/skills/.agent-guild/state/archive/2026-08-08-issue-27/log/vendor-calls.jsonl`: `grep -c "/Users/karnett/"` returns 10, and a per-row walk returns 10 at indices `[1, 3, 4, 6, 8, 12, 13, 14, 15, 16]`. Ten is also the count of rows with any absolute artifact path, so the number is wrong under either reading. C-9's `check_method` requires the checker to "confirm each named fact is present and accurate," so an opus checker that re-derives — which is the whole of its job — will count ten and FAIL T-006 on a sentence T-006 told the worker to write. The alternative outcome is worse: a checker that trusts the task ships a false count into `openQuestions.md`, the artifact whose entire purpose is that "reported" means an artifact rather than a memory.

  Fix: change `T-006.md:40` to eleven → ten. The same wrong number is in C-9's clause text (`constitution.md:73`) and in the spec (`spec.md:62`), and `compose-brief.py` ships cited clause text verbatim to the courier lane, so the courier will see "eleven" even after the task is fixed. Correct the clause too and re-submit CON-audit, or accept a known courier disagreement on T-006 and say so in the task.

- **D3** (major; T-006): **one dispatch carries three clauses across seven files.** See section 2. Fix: split into a documentation task (C-9: `docs/vendor-ledger.md`, `dataContracts.md`, `conventions.md`, `openQuestions.md`, plus the in-place prose fixes to the schema description and docstring) and a prose/message task (C-8: `commit-message.md` plus the humanizer audit over everything this job wrote), with C-5 moving to T-007 per D1. The C-8 task depends on the C-9 task and on T-005, since C-8's subject is prose the other tasks produce.

  **D3b**, inside the same fix: C-8's clause text names "the rewritten retrospective step" as prose that must pass the audit, but `T-006.md:46` lists only two borrowed files — the schema description and the docstring — and T-005's body tells its own worker that `guild-core/` is its file. As written, a C-8 FAIL on the retrospective step's voice hands the T-006 worker a file another task claims to own, with no instruction saying it may touch it. Name `guild-core/workflows/retrospective/SKILL.md` in the C-8 task's excerpt as prose it may revise, and say in T-005 that a later task may revise its wording for voice without changing what it instructs.

- **D4** (minor; T-003, T-006): **C-5's `check_method` reads as one command and is two.** The folded scalar joins the lines, so `_lib.parse_frontmatter` yields `…check-build.sh 'test "$(git rev-parse HEAD)" = "164…"…' followed by .agent-guild/scripts/check-diff-scope.py …` on a single line. T-003's checker is `checker-deterministic` — haiku, explicitly "zero discretion" — and it has to split that string into two invocations and decide how to combine two exit codes before it can transcribe anything. Fix: label them, e.g. `C-5a: <head guard>` and `C-5b: <scope script>`, and state that C-5 passes only if both exit 0. Same edit in both tasks (or once, if C-5 consolidates into T-007 per D1).

- **D5** (minor; T-001): **wrong line citation.** `T-001.md:55` cites `.agent-guild/scripts/compose-brief.py:58` for the matched-pair strip; the actual form is at `compose-brief.py:64`. Line 58 is inside the frontmatter delimiter loop. The companion citation, `check-provenance.py:74`, is correct. Harmless in practice because the excerpt gives the code form inline, but a worker who opens the cited line finds unrelated code and has to hunt. Fix: `:58` → `:64`.

- **D6** (minor; T-006): **a script clause on a judgment checker.** T-006 lists C-5, whose check is two shell commands, under `checker: checker-judgment`, against the routing rule that a script-checked clause goes to `checker-deterministic`. Not a capability failure — `checker-judgment` has `Bash` — but it invites an opus checker to interpret an exit code. Resolved for free by D1's move of C-5 into T-007.

## What stays weak even after these fixes

- **W2 still applies and now has a scheduling edge.** `commit-message.md` lives under `state/`, which Phase 3's archive step sweeps into `archive/<date>/`. If you archive before committing, the audited messages are at the archived path. Commit first.
- **W5 will produce a `blocked` courier verdict on T-001.** C-2's rubric requires writing fixture files and running the script; a read-only Codex courier cannot. Record it as lane limitation, not as a defect in the work.
- **T-003's C-3 blames the wrong worker.** Covered in section 3: a red suite there is a T-001/T-002 signal, and escalating T-003 up the ladder will not fix it. Under D1's restructure the same caution transfers to T-007.
- **C-1's exit code is not suite health.** `bash -c` runs without `pipefail` and the `tee` pipeline discards the suite's status, so T-002's check can exit 0 with an unrelated case red. That is deliberate and C-3 covers it; do not read a T-002 PASS as "the suite is green."
- **C-1's grep is a substring match.** A case labelled `job: derived from provenance ref, negative case` satisfies the check for the shorter label. T-002's excerpt carries the labels verbatim, which is the mitigation available; C-2 reading the behavior independently is the real backstop.
