---
task: DEC-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: PASS
checked_at: 2026-07-14T00:00:00Z
---

<!--
DEC-audit round 0. No prior DEC-audit-r*.md exists in the live verdicts/ dir.
Decomposition is a single task, T-001, audited against spec.md (intake of
kendrick/agent-guild#20) and constitution.md (CON-audit PASS at r0). Deliverables
do not exist yet; the task's deterministic checks were confirmed to reference the
constitution's exact commands and the judgment rubrics confirmed faithful to
clause text, not run to green.
-->

## Per-task results

| task | coverage | clauses cited / check_method | routing | deps | result |
| ---- | -------- | ---------------------------- | ------- | ---- | ------ |
| T-001 | All six spec duties carried: component copy → C-2; hooks.json generation → C-3; project-template assembly → C-2; namespacing transform → C-4 (+ read-only guarantee C-7); `--check` semantics → C-5; manifest source → C-1 (+ platform validation C-6). All eight clauses C-1..C-8 appear in `clauses:` and are addressed by `check_method`. | Cites all eight; C-2/C-3/C-5/C-6/C-7 run "the exact check commands from constitution.md" (deterministic, by reference); C-1/C-4/C-8 are judgment rubrics faithful to clause text; C-5 carries a judgment supplement (missing-CLI branch) coherent with C-5. | executor worker-standard/sonnet; checker checker-judgment/opus. | `[]` | PASS |

## Coverage

Every spec duty maps to at least one clause carried by T-001, and the mapping is faithful to the clause text:

- Component copy (six named agents byte-identical, five guild skills, six hook files, working-memory content excluded) → C-2.
- `hooks/hooks.json` generation from `.claude/settings.json`, path rewrite to `"${CLAUDE_PLUGIN_ROOT}"/hooks/`, no dangling registration → C-3.
- `project-template/.agent-guild/` assembly (contract, scripts, templates) → C-2.
- Bare-to-namespaced invocation map on plugin-bound prose only, sources untouched → C-4 and C-7.
- `--check` semantics (rebuild-to-temp, diff against `plugin/`, hard-fail on drift, absence, and missing `claude` CLI; run `validate --strict` on match) → C-5, with the validator standard in C-6.
- Manifest source `scripts/plugin-src/plugin.json` (stdlib script + checked-in manifest, `author` object, `hooks` pointer, version 0.1.0) → C-1, validated by the platform in C-6.

Read-only-to-inputs and the exact-declared-surface guarantee → C-7. House code style → C-8. No spec requirement is left unclaused.

**Single-task legitimacy.** The deliverable is one coherent artifact: `build-plugin.py` and the manifest source it copies through. The plugin-src `plugin.json` does not deserve a separate task with its own checker — it is not independently verifiable. Its only observable behavior is realized through the build (C-1 reads it, C-2 confirms it lands as `.claude-plugin/plugin.json`, C-6 validates the built output with `claude plugin validate --strict`). Splitting it out would create a task whose "check" is either a bare JSON-shape lint (already covered by C-1) or a validation that requires running the very build it would be separated from. One executor, one artifact, one lifecycle is the right granularity here.

## Check-method fidelity

- Deterministic clauses (C-2, C-3, C-5, C-6, C-7) are checked by explicit reference to "the exact check commands from .agent-guild/state/constitution.md," which the CON-audit already confirmed parse and fail loud. The task does not paraphrase or weaken them.
- Judgment clauses (C-1, C-4, C-8) carry rubrics that track the clause text: C-1 names stdlib-only imports, exec bit, `--help` coverage, and the four manifest properties; C-4 combines a deterministic grep spot-check for `/agent-guild:` invocations with a read for path/heading overreach and a `git status` source-mutation check; C-8 reads the script against the two named reference files with concrete fail conditions.
- **C-5 judgment supplement.** Added per the CON-audit's non-blocking advisory that the deterministic C-5 check runs where `claude` is present and cannot exercise the missing-CLI branch. The supplement directs the checker to read the `--check` code path and confirm it hard-fails with a naming message when the CLI is absent, "never skip validation silently." This restates C-5's own text ("hard-fail — a skipped validation must never read as green") and closes the exercise gap by reading rather than running. It supplements C-5; it does not contradict it.

## Routing

Consistent with the CLAUDE.md routing table.

- Executor worker-standard on sonnet: the work is clear-spec implementation judged on correctness. The spec excerpt fully specifies the CLI, the four build steps with exact rewrite targets, `--check` semantics, manifest shape, and house style — this is sonnet's lane, not a taste job for worker-craft nor mechanical bulk.
- Checker checker-judgment on opus: the clause mix includes judgment work (C-1, C-4, C-8, and the C-5 supplement), so the check cannot route to a deterministic-only haiku checker. A judgment checker on opus also runs the deterministic commands (C-2/C-3/C-5/C-6/C-7) — the table permits the judgment tier to execute scripts, whereas the reverse (haiku applying rubrics) is not permitted. Single judgment checker for the whole task is correct.

## deps

`deps: []` is correct. T-001 is the only task in the decomposition and is the epic-blocking build script (spec: "Blocks the other children in this epic"); it has no upstream producer. A single-node graph with no edges is a trivial DAG with no cycle, and no referenced task is missing.

## Cold-build readiness

A worker could build this from the spec excerpt plus the constitution. The excerpt is self-sufficient for the deliverable: it gives the exact CLI, the four numbered build duties with concrete rewrite targets and the word-boundary namespacing approach, the full `--check` contract, the manifest schema (including the `author`-as-object trap and the `hooks` pointer), and the house-style references. It points the worker to `docs/plugin-publish-plan.md` ("Build script" and "Verified Platform Facts") for design rationale — that file exists (confirmed) and contains both referenced sections. The pointer supplies rationale and platform facts (validator behavior, manifest-isolation reasoning) rather than load-bearing build steps the excerpt omits, so it is an appropriate reference, not a coverage gap that would strand a worker who read only the excerpt and the constitution.
