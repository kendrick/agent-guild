---
task: DEC-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: PASS
checked_at: 2026-07-14T00:00:00Z
---

<!-- DEC-audit round 0 for the single-task decomposition (T-001) of issue #21,
"commit the plugin/ tree, retire dist/". CON-audit PASSed at r1. Audited against
.agent-guild/state/spec.md and constitution.md C-1..C-5, plus the CLAUDE.md
routing table. All findings re-derived from the live tree (build script read,
sources/gitignore inspected), not from the task's self-description. -->

## Per-task results

| task  | executor / checker            | clauses cited      | coverage | routing | deps | check_method fidelity | result |
| ----- | ----------------------------- | ------------------ | -------- | ------- | ---- | --------------------- | ------ |
| T-001 | worker-bulk / checker-deterministic | C-1,C-2,C-3,C-4,C-5 | full     | sound   | [] DAG-ok | verbatim to constitution | PASS   |

## Coverage

Every requirement the issue settles maps to a clause carried by T-001:

- `plugin/` tree at repo root, guild-only content — C-1 (fresh-build equality) + C-3 (component set).
- lifecycle skills plus `init` and `job` — C-3 asserts the exact six-skill set `audition constitution decompose init job retrospective`.
- six guild agents / four gates — carried through C-1: the fresh `--check` rebuild re-derives `GUILD_AGENTS` (6) and `GUILD_HOOKS` (the four gates) from source, so any missing agent or gate breaks the file-for-file diff.
- manifest `author`-as-object + `version 0.2.0` + `SessionStart` + nudge shipping + working-memory excluded — all C-3.
- `dist/` retirement (tree + gitignore entry + comment) — C-4.
- no stray footprint — C-5.

All five clauses C-1..C-5 are cited; no spec requirement is left uncovered.

## check_method fidelity

T-001's `check_method` delegates verbatim: "run the exact check commands from
constitution.md C-1..C-5 exactly as written, transcribe exit codes and output."
Every cited clause is deterministic (exit-code / string-equality, no rubric), so
the deterministic check_method is consistent with each clause and correctly
paired with `checker-deterministic` per the routing rule (deterministic clauses →
checker-deterministic).

## Single-task legitimacy

One atomic, ordered recipe with a single indivisible deliverable (one build run
produces the whole `plugin/` tree; the version bump and gitignore edit are its
two prerequisites). Splitting would create artificial deps around one build
invocation. Single task is legitimate here.

## Routing (judged honestly against the CLAUDE.md table)

First job into the haiku lane (worker-bulk + checker-deterministic) on the claim
that every step is mechanical and every check is a script. I scrutinized each
step for hidden judgment a haiku worker could fumble:

- **Step 1, version bump** — exact find-replace, both strings given verbatim. Mechanical.
- **Step 2, gitignore edit** — the two target lines are named by exact content (`dist/` entry + `# Build artifacts` comment) and confirmed to be the last two lines of a short file (verified: only line 25 matches `(^|/)dist`, only line 24 matches `Build artifacts`). Locating them needs no judgment. Residual note below.
- **Step 3, `rm -rf dist`** — literal command.
- **Step 4, build** — single command `python3 scripts/build-plugin.py`, no args.
- **Step 5, five checks + the `--check`-fails contingency** — the instruction pre-resolves the only branch ("rebuild rather than hand-editing anything under `plugin/`"), so no on-the-fly judgment is required; the worker follows a literal directive.

No step rises to sonnet-level judgment. Every failure mode is bounded: C-5 pins
the repo-wide footprint, C-1 rejects any hand-edit under `plugin/`, and the
deterministic checker re-runs all five commands independently, with the retry
ladder escalating to sonnet after two FAILs. Routing is sound.

Residual (not a defect): C-5's porcelain excludes `.gitignore`, so a haiku
worker that mangled an *unrelated* `.gitignore` line while removing the two
named ones would not be caught by any clause. The step 2 instruction is explicit
("change nothing else in the file"), the file is short, and this is within haiku
competence — it does not warrant sonnet and does not block the decomposition. I
note it only so the orchestrator watches the gitignore diff at commit time.

## deps / DAG

`deps: []`. Single task, no intra-job predecessor — trivially a DAG, no cycles,
no dangling references. The issue's cross-issue preconditions (build script,
`init` #22, nudge #23) are already satisfied on disk: `scripts/build-plugin.py`
is committed, `.claude/skills/init/SKILL.md` exists, and
`.agent-guild/hooks/session-nudge.py` exists — so the build's include-when-present
`init` skill and `session-nudge.py` hook both land, which is exactly what C-3
requires. Nothing here depends on uncommitted prior state.

## Cold-build readiness + ordering

The excerpt is a complete, self-contained ordered recipe: worker-bulk can
execute steps 1-4 literally without reading the full spec (step 5 sends it to
the constitution for the exact check commands, as intended).

Ordering is correct and load-bearing. `write_plugin_manifest` (build-plugin.py
@295) copies `scripts/plugin-src/plugin.json` verbatim into
`plugin/.claude-plugin/`. So the version bump MUST precede the build (step 1
before step 4), and it does. The resulting tree carries `0.2.0`, satisfying C-3;
and because C-1's `--check` rebuilds fresh from the same already-bumped source,
the temp rebuild also carries `0.2.0` and diffs clean against `plugin/` — so C-1
and C-3 are satisfied simultaneously. The inverse orders both fail: building
before bumping leaves `plugin/` at `0.1.0` (C-3 fails), and bumping after
building leaves `plugin/` stale so `--check` finds drift (C-1 fails). The recipe
picks the one order that greens both.

## Diagnosis

<!-- No FAIL this round. -->
