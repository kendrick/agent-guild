---
task: CON-audit
tier: orchestrator
retry: 1
checker: auditor
verdict: PASS
checked_at: 2026-07-14T00:00:00Z
---

<!-- CON-audit round 1 for the GitHub-Issue Intake job (Job 1). Audits
.agent-guild/state/constitution.md against .agent-guild/state/spec.md, independently
and in full (r0's non-flagged findings re-derived, not trusted). Round 0
(CON-audit-r0.md) FAILed on two coverage gaps in C-1 and C-3; both were amended.
Scope: check-provenance.py is deliverable 2 and does not exist yet; the live DoD
run is the orchestrator's post-job demonstration, not a clause. -->

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment: well-formed + falsifiable + covers deliverable 1 | Amended text now names the output content contract: "structured as the provenance header first, then the spec content; for issues, the content is the issue title plus the full body with the issue's own markdown preserved (no summarizing, no stripping)." The rubric now checks "the output ordering (header, then content) and the title-plus-verbatim-body rule for issues are stated," and fails "if...the content contract is absent." Six argument forms, write-target, and no-fabrication retained. | ordering + issue title/body/markdown fidelity covered; falsifiable | a title-only or markdown-stripping skill now fails the rubric ("content contract...absent" / title-plus-verbatim-body rule not stated); the two r0 gaps close | PASS |
| C-2 | judgment: well-formed + routing | Side-by-side skill/validator contract read; keys `source`/`ref`/`fetched_at` + `issue`/`title`-when-github-issue mirror spec deliverable 2; bidirectional falsifiability stated (`fetched-at` hyphen example); prose cross-consistency is not scriptable, so judgment routing is correct. Unchanged from r0 and independently re-confirmed. | concrete, falsifiable, sound routing; no clash with amended C-1 | consistent — C-1 references the header C-2 defines; the title appearing in both header and body is the spec's own design (spec.md:15,26), not a contradiction | PASS |
| C-3 | deterministic, verified empirically | Amended text adds: "For every failing fixture, the self-test also asserts the validator emitted a diagnostic line naming the first violated rule — a bare nonzero exit with no message is itself a self-test failure." Check unchanged: `check-build.sh "python3 .../check-provenance.py --self-test"`. Empirically, the script is absent pre-build (`os error 2`), so a checker gets FAIL/ERROR pre-build, never a false PASS; check-build.sh exists and is executable. | a validator that exits 1 silently on failing fixtures fails its own self-test → nonzero exit → check FAILs; deterministic routing correct | closes the r0 diagnostic-line gap. The self-test is the spec's own chosen mechanism (spec.md:29), so folding the assertion into it is faithful; the fixture list matches the spec's enumerated battery exactly | PASS |
| C-4 | judgment: well-formed + covers deliverable 3 | Spec-exists branch must derive-and-confirm not interview, preserve the no-spec path, forbid re-asking; failing example ("may skim") statable. Judgment routing correct. Re-derived independently. | concrete, falsifiable, covered | same | PASS |
| C-5 | judgment: well-formed + covers deliverable 4 impl | Requires the guard to test `candidate/.agent-guild` (not bare existence), the `RuntimeError` raise, the unchanged primary path, and tests exercising both branches; `os.path.exists(candidate)` failing example is concrete. Reading the guard's source asserts the SOURCE of the property (a mere test-run could pass with weak coverage), so judgment routing is correct — not redundant with C-6. | concrete, falsifiable, covered, asserts source | same | PASS |
| C-6 | deterministic, verified empirically | Current suite `49 passed, 0 failed`. Regex re-tested this round: rejects 49 and every nonzero-failed line (`50 passed, 1 failed`, `48 passed, 1 failed`); accepts `50/51/150 passed, 0 failed`. check-build.sh propagates grep's exit. | rejects pre-change 49, accepts 50+/0-failed only | same | PASS |
| C-7 | deterministic, verified empirically | All six frozen paths exist; `git diff --quiet HEAD -- ...` exits 0 on the clean tree this round. Frozen list correctly excludes in-scope `_lib.py`/`test_hooks.py`/skills. Routing correct. | paths exist, clean-tree exit 0 | same | PASS |
| C-8 | judgment: well-formed + covers prose constraint | Concrete tells (hand-waving, missing frontmatter, session-tool assumptions beyond `gh`, non-triggering description); reference artifact named (`constitution/SKILL.md`); failing example statable. `major` severity defensible for style. Judgment routing correct. | concrete, falsifiable, covered | same | PASS |

Deterministic checks C-3 (missing-script surfacing), C-6 (regex boundaries), and C-7 (git diff on clean tree) were run empirically this round; results above are observed, not carried over from r0.

## Assessment

Both r0 amendments close exactly the gaps they targeted, and neither introduces a new contradiction.

- **C-3 diagnostic line.** The r0 hole — a validator whose failures do `sys.exit(1)` with no message passing the clause — is closed. The clause now makes "the self-test asserts each failing fixture emitted a diagnostic line naming the first violated rule; a bare nonzero exit is itself a self-test failure" part of what `--self-test` proves. A silently-failing validator now makes its own self-test exit nonzero, and check-build.sh propagates that as a check failure. This is verified through the spec's deliberately chosen mechanism (the embedded self-test, "checkable by one command with no external fixtures," spec.md:29) rather than an external fixture, so it is faithful to the deliverable. The clause's fixture list still mirrors the spec's enumerated battery one-for-one.

- **C-1 content contract.** The r0 hole — a skill that writes title-only, drops the body, or strips markdown satisfying every clause — is closed. The clause text now asserts header-then-content ordering and, for issues, "the issue title plus the full body with the issue's own markdown preserved (no summarizing, no stripping)," and the rubric fails when the content contract is absent or the title-plus-verbatim-body rule is unstated. Each is falsifiable with a concrete artifact (a SKILL.md that summarizes the body, or emits content before the header).

- **No new C-1/C-2/C-3 inconsistency.** C-1's "header first, then the spec content" and C-2's "YAML frontmatter at the top" agree. The issue `title` appearing in both C-2's header and C-1's body is the spec's own design (spec.md:15 body = title+body; spec.md:26 header carries `title`), not a clause collision. For non-issue sources C-1's content is the file/URL body and C-2 omits `issue`/`title` — consistent. C-3 shares no subject with C-1/C-2.

Everything r0 passed was re-derived, not trusted: all eight clauses name concrete, falsifiable checks; deterministic-vs-judgment routing is sound throughout (C-5 reads source to assert the property's origin rather than leaning on C-6's suite run, so the two are complementary, not redundant); the three script-backed checks were run empirically this round; no two clauses contradict; "no protected content" is legitimate for a behavior-packaging job; and the non-goals mirror the spec's Out Of Scope. Coverage is complete for every in-scope spec requirement (deliverables 1/2/3/4, the frozen-kit and stdlib constraints, and the prose-style constraint). The constitution is genuinely sound.
