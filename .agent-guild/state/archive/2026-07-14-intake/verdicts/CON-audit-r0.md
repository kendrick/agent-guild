---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: FAIL
checked_at: 2026-07-14T23:10:36Z
---

<!-- CON-audit round 0 for the GitHub-Issue Intake job (Job 1). Audits
.agent-guild/state/constitution.md against .agent-guild/state/spec.md. -->

## Per-clause results

| clause | method | evidence (command output / quoted artifact / fetched page) | expected | actual | result |
| ------ | ------ | ---------------------------------------------------------- | -------- | ------ | ------ |
| C-1 | judgment: clause well-formed + falsifiable + covers deliverable 1 | Rubric checks the six argument forms, write-target = `spec.md`, and no-fabrication-on-error — all concrete and falsifiable. But the rubric never checks the spec's output-content requirement: "the provenance header followed by the spec content (for issues: title + body; preserve the issue's own markdown)". | every explicit deliverable-1 requirement maps to the clause's check | ordering (header-then-content) and issue content fidelity (title+body, preserved markdown) uncovered | FAIL |
| C-2 | judgment: clause well-formed + routing | Side-by-side skill/validator contract read; keys `source`/`ref`/`fetched_at` + `issue`/`title`-when-github-issue match spec deliverable 2 exactly; bidirectional falsifiability stated; judgment routing correct (prose cross-consistency is not scriptable). | concrete, falsifiable, sound routing | same | PASS |
| C-3 | deterministic, verified empirically | `check-build.sh "python3 .../check-provenance.py --self-test"`: missing script (pre-build) → exit 2, propagated by check-build.sh; a pre-build checker gets FAIL/ERROR, never PASS. Command well-formed, checker-deterministic routing correct. BUT the enumerated self-test asserts only exit-code behavior of the five fixtures; spec deliverable 2's "Non-zero exit with a line naming the first violated rule" is not asserted by any clause. | every explicit deliverable-2 requirement maps to a clause's check | validator error-message content (names the first violated rule) uncovered | FAIL |
| C-4 | judgment: clause well-formed + covers deliverable 3 | Spec-exists branch must derive-and-confirm not interview, must preserve the no-spec path, must forbid re-asking; failing example (vague "may skim") is statable. Judgment routing correct. | concrete, falsifiable, covered | same | PASS |
| C-5 | judgment: clause well-formed + covers deliverable 4 impl | Requires the guard to test `candidate/.agent-guild` (not bare existence), the `RuntimeError` raise, the unchanged primary path, and tests exercising both branches; failing example (`os.path.exists(candidate)`) is concrete. Asserts the SOURCE of the property, not ambient state. Judgment routing correct. | concrete, falsifiable, covered | same | PASS |
| C-6 | deterministic, verified empirically | Current suite: `49 passed, 0 failed`. Regex `[5-9][0-9]+ passed, 0 failed\|[1-9][0-9]{2,} passed, 0 failed` tested: rejects 49; accepts 50/51/100/149/500/1050 with 0 failed; rejects every nonzero-failed line (`50 passed, 10 failed`, `48 passed, 1 failed`, `150 passed, 20 failed`); rejects single-digit counts. No false accepts found. check-build.sh propagates grep's exit. | rejects pre-change count, accepts 50+/0-failed only | same | PASS |
| C-7 | deterministic, verified empirically | All six frozen paths exist; `check-build.sh "git diff --quiet HEAD -- ..."` exits 0 on the clean tree. Diffs only out-of-scope surface; in-scope `_lib.py`/`test_hooks.py`/skills correctly excluded. checker-deterministic routing correct. | paths exist, clean-tree exit 0 | same | PASS |
| C-8 | judgment: clause well-formed + covers prose constraint | Concrete tells (hand-waving, missing frontmatter, session-tool assumptions beyond `gh`, non-triggering description); reference artifact named (`constitution/SKILL.md`); failing example statable. Severity `major` (vs blocker) is defensible for style. Judgment routing correct. | concrete, falsifiable, covered | same | PASS |

Deterministic checks C-3 (missing-script surfacing), C-6 (regex), and C-7 (git diff on clean tree) were run empirically; results above are observed, not asserted.

## Diagnosis

Two explicit, in-scope spec requirements have no clause that verifies them. Each is demonstrable: an artifact can satisfy every clause as written and still violate the spec.

- **file**: .agent-guild/state/constitution.md:24-28 (C-3)
  **clause**: C-3—"runs an embedded fixture battery and exits 0 only if all fixtures behave: a fully valid github-issue header passes; missing `fetched_at` fails; a malformed timestamp fails; `source: github-issue` without `issue` fails; `--issue N` mismatch fails."
  **expected**: some clause verifies spec deliverable 2's stated validator contract "Non-zero exit with a line naming the first violated rule" (.agent-guild/state/spec.md:29). C-3 is the only clause exercising the validator, so this belongs in its self-test.
  **actual**: C-3's fixture battery asserts only exit-code behavior (pass vs fail) per fixture; it never asserts the failure output names the violated rule. A `check-provenance.py` whose failures do `sys.exit(1)` with no message passes C-3 (and passes C-2, which only matches header keys) yet violates the spec's diagnostic contract. Fix: extend C-3's self-test to assert each failing fixture's stderr names its violated rule, or add a clause covering it.

- **file**: .agent-guild/state/constitution.md:12-16 (C-1)
  **clause**: C-1—"confirm each of the six situations has explicit instructions, the write target is exactly `.agent-guild/state/spec.md`, and the failure path forbids fabrication."
  **expected**: C-1 (the only clause covering deliverable 1's output) verifies spec deliverable 1's output-content requirement: "writes exactly one file, `.agent-guild/state/spec.md`, containing the provenance header (below) followed by the spec content (for issues: title + body; preserve the issue's own markdown)" (.agent-guild/state/spec.md:15).
  **actual**: the rubric checks the six argument forms, the write target, and no-fabrication, but not (a) that output is the provenance header followed by content in that order, nor (b) that the issue path emits title + body with the issue's markdown preserved. A skill that writes title-only, drops the body, or strips markdown passes C-1's rubric while violating the spec. Header presence is loosely reachable via C-2's contract read, but ordering and issue-body fidelity are covered by no clause. Fix: add these to C-1's rubric (or a companion clause).

Everything else is sound: clauses name concrete, falsifiable checks; deterministic-vs-judgment routing is correct throughout; the three script-backed checks were verified empirically; no two clauses contradict (C-7's frozen list correctly excludes the in-scope `_lib.py`/`test_hooks.py`/skills that C-5/C-6/C-1/C-4/C-8 touch); the "no protected content" declaration is legitimate for a behavior-packaging job; the non-goals mirror the spec's Out Of Scope; and excluding the live DoD run from the clauses is correct (subagents cannot invoke skills). Fix the two coverage gaps and re-submit for round 1.
