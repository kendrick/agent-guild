# Spec: GitHub-Issue Intake (Job 1)

## Goal

Make the guild consumable from existing specs and GitHub issues: a `/job` skill that turns an issue or a BYO spec into `.agent-guild/state/spec.md` with a verifiable provenance header, and a constitution skill that collapses its interview when such a spec already exists. This is Job 1 of the two-job plan at `~/.claude/plans/spin-it-up-as-fluffy-parrot.md`; Job 2 (plugin packaging, init, marketplace) will be filed as GitHub issues and consumed *through* this intake, so every Job 2 issue doubles as a live test of what this job builds.

## Definition Of Done (user's words)

In this repo: run `/job <issue-number>`, get a provenance-headed `spec.md`, and flow into a collapsed constitution.

## Deliverables

1. **`/job` skill** at `.claude/skills/job/SKILL.md` — a bare in-repo skill (namespacing to `/agent-guild:job` is Job 2's build-script concern). Behavior:
   - Argument forms: bare number or `#N` → `gh issue view` against the current repo; `owner/repo#N` or a GitHub issue URL → `gh issue view -R <owner/repo>` (or the URL form); an existing local file path → read the file as the spec body; any other URL → fetch it.
   - Output: writes exactly one file, `.agent-guild/state/spec.md`, containing the provenance header (below) followed by the spec content (for issues: title + body; preserve the issue's own markdown).
   - No argument → do not guess: explain the two paths (point at an issue/file, or proceed to the constitution interview which authors the spec).
   - Failure honesty: if `gh` fails (not installed, not authed, issue not found), report the actual error and write nothing. Never fabricate spec content.

2. **Provenance header contract + validator.** The header is YAML frontmatter at the top of `spec.md` with flat keys:
   ```
   ---
   source: github-issue | file | url
   ref: <owner/repo#N | path | URL>
   issue: <N>                # required when source is github-issue; absent otherwise
   title: <issue title>      # required when source is github-issue
   fetched_at: <ISO-8601 UTC, e.g. 2026-07-14T18:00:00Z>
   ---
   ```
   A new dependency-free validator, `.agent-guild/scripts/check-provenance.py <spec.md> [--issue N]`, exits 0 only when: `source`, `ref`, `fetched_at` present; `fetched_at` parses as ISO-8601 UTC; when `source: github-issue`, `issue` is present and consistent with the `N` in `ref`; and with `--issue N`, the recorded issue equals N. Non-zero exit with a line naming the first violated rule. The validator also ships a `--self-test` mode that runs an embedded fixture battery (a valid header passes; missing `fetched_at`, malformed timestamp, `github-issue` without `issue`, and `--issue` mismatch each fail) so the contract is checkable by one command with no external fixtures. This makes the header deterministic-checkable per the user's directive — it is the part of intake most likely to silently drift.

3. **Constitution skill collapse.** Edit `.claude/skills/constitution/SKILL.md`: a new pre-interview step — when `.agent-guild/state/spec.md` already exists, read it, derive candidate quality bars from the spec content, and present them to the user for confirmation/adjustment instead of running the full question bank. The full interview remains the path when no spec exists. The skill must not re-ask what the spec already answers.

4. **`_lib.py` fallback hardening (rides along).** In `.agent-guild/hooks/_lib.py`, `project_dir()`'s fallback currently returns two-dirs-up unconditionally when `CLAUDE_PROJECT_DIR` is unset. Harden it: accept the two-dirs-up candidate only if it contains a `.agent-guild/` directory; otherwise raise `RuntimeError` (fail loud, per the module's own design rule). Add a covering test to `test_hooks.py`; the full suite stays green. This upstreams the fix the first dogfood applied only to the staged copy, so Job 2's build script can copy `_lib.py` verbatim.

## Constraints

- The live enforcement kit stays intact: `.claude/settings.json`, the four gate scripts (`dispatch-guard.py`, `orchestrator-write-guard.py`, `stop-gate.py`, `subagent-return.py`), and `.claude/agents/` are not modified by this job. (`_lib.py` and `test_hooks.py` ARE in scope, per deliverable 4.)
- Everything stays stdlib/dependency-free per repo convention.
- Skill and validator prose: agent-facing instructions, written to the repo's existing skill style (compare `constitution/SKILL.md`); clarity is a check, the humanizer loop is not required for these.

## Out Of Scope (Job 2, by user directive)

Build script, committed `plugin/` dir, `/agent-guild:init`, SessionStart nudge, marketplace/manifests, README/docs/SMOKE updates, namespacing of any reference. Nothing else from the reference design enters Job 1.
