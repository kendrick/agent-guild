---
task: DEC-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: FAIL
checked_at: 2026-07-14T00:00:00Z
---

<!-- DEC-audit round 0. Audits the decomposition (single task T-001) against
.agent-guild/state/spec.md and .agent-guild/state/constitution.md (CON-audit
PASS at r0). -->

## Per-task results

| task  | dimension        | finding                                                                                                                              | result |
| ----- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| T-001 | coverage         | Cites C-1..C-5 (all clauses). Issue reqs — normalize `subagent_type` before lookups, fixtures for bare+namespaced, land pre-#21 — all carried. | PASS   |
| T-001 | check_method     | C-2/C-3/C-4 delegated verbatim to the constitution's script commands; C-1/C-5 judgment rubrics restated faithfully.                   | PASS   |
| T-001 | single-task      | One coherent two-file fix; splitting helper from fixtures would be artificial. Legitimate.                                            | PASS   |
| T-001 | routing          | executor worker-standard/sonnet (clear-spec correctness); checker checker-judgment/opus. Mixed deterministic+judgment clauses under one checker → judgment checker is the correct (higher-capability) choice. Models match DEFAULT_MODEL. | PASS   |
| T-001 | deps / DAG       | `deps: []`, single task, trivial DAG, no dangling refs.                                                                               | PASS   |
| T-001 | seam feasibility | The prescribed seam (wrapper objects in `_lib.py`, `dispatch-guard.py` untouched per C-4) CANNOT satisfy C-2 and C-3. Proven empirically. | FAIL   |

## Diagnosis

The decomposition sends the worker into an unwinnable box: the seam the task
prescribes cannot satisfy C-2 and C-3, and the only seam that can violates C-4.

- **file**: `.agent-guild/state/tasks/T-001.md:66-76` (the "Spec excerpt" seam guidance)
  **clause**: C-2—"passes a namespaced auditor dispatch that carries a legal `Audit-ID` (exit 0)"; C-3 fixture 2—"namespaced worker fully legal ... passes"; against C-4—"entire working-tree footprint is modifications to `_lib.py` and `test_hooks.py` — no other modification."
  **expected**: A worker following the task's prescribed approach (a normalization helper exposed via `_lib`, with `GUILD_AGENTS`/`DEFAULT_MODEL`/`CHECKER_AGENTS` replaced by wrapper objects whose `__contains__`/`__getitem__` normalize the `<ns>:` prefix) produces a tree where C-2, C-3, C-4 all pass while `dispatch-guard.py` stays untouched.
  **actual**: Wrapper objects on the `_lib` collections cover only the sites where `agent` reaches those collections. They cannot touch the two sites where `dispatch-guard.py` consumes the raw namespaced `agent` string through bare `str` operators, and BOTH of those sites are load-bearing for the constitution's own checks:

  Enumeration of every `agent` consumption site in `dispatch-guard.py` (agent = `"agent-guild:..."`):
  - L43 `agent not in _lib.GUILD_AGENTS` — membership → wrapper `__contains__` covers it.
  - L54 `_lib.DEFAULT_MODEL[agent]`, L87, L69 — `__getitem__` → wrapper covers it.
  - L54/L69/L95 `_log(agent, ...)` — passes the RAW string; correct for C-1 log fidelity, no change wanted.
  - L89 `agent in _lib.CHECKER_AGENTS` — membership → wrapper covers it.
  - L61/L74/L115 block-message f-strings `{agent}` — raw is desired.
  - **L68 `if agent == "auditor":`** — bare `str.__eq__`. `"agent-guild:auditor" == "auditor"` is False, so a namespaced auditor with a legal Audit-ID never takes the auditor pass-through; it falls to L72-77 and is blocked ("names an Audit-ID but ... is not the auditor"), exit 2. No `_lib` wrapper participates in this comparison.
  - **L114 `agent != executor`** — bare `str.__ne__` against the bare `executor` field from the task file. `"agent-guild:worker-standard" != "worker-standard"` is True, so a fully-legal namespaced worker is blocked as an executor mismatch, exit 2. No `_lib` wrapper participates.

  Empirical confirmation — with the excerpt's exact wrapper seam installed (`NDict`/`NSet` normalizing `__contains__`/`__getitem__`) and `dispatch-guard.py` unmodified:
  - C-2 namespaced auditor + legal Audit-ID → **rc=2** (constitution requires 0): blocked at L68.
  - C-3 fixture 2, fully-legal namespaced worker → **rc=2** (constitution requires 0): blocked at L114.
  - C-2 no-id namespaced worker → rc=2 (correct): membership normalizes, `has no id line` fires. So the no-id block and fixture 2 are **not** jointly satisfiable under the wrapper seam — the no-id case passes but the legal case is wrongly blocked.

  The only fix that clears L68 and L114 is normalizing `agent` at its source in `dispatch-guard.py` (e.g. `agent = _lib.normalize(ti.get("subagent_type",""))` at L42, keeping the raw string for `_log`). That is a `dispatch-guard.py` modification, which C-4's porcelain assertion fails and which the task itself orders the worker to STOP on ("If a one-line change in `dispatch-guard.py` is genuinely unavoidable, STOP"). So the task offers two exits and both are dead ends: follow the wrapper seam → C-2 and C-3 FAIL; edit `dispatch-guard.py` → C-4 FAIL (and the task says stop). The decomposition is not cold-build-ready.

- **file**: `.agent-guild/state/constitution.md:16` (C-1) vs `:33-34` (C-4) — latent contradiction the fix must resolve, surfaced here because the decomposition rests on it.
  **clause**: C-1—"dispatch-guard.py ... must need no changes if the helper lives at the right seam — if dispatch-guard did change, judge whether the seam chosen is justified"; C-4—"no other modification ... anywhere."
  **expected**: A single reachable seam that both clauses accept.
  **actual**: C-1 concedes `dispatch-guard.py` may legitimately change ("judge whether the seam chosen is justified"), but C-4 forbids any change to it. Because the correct fix provably requires touching `dispatch-guard.py` (L68, L114 above), these two clauses cannot both hold for the real solution. The orchestrator must reconcile them before this task can be built — either widen C-4's footprint to include `dispatch-guard.py` (and drop C-1's "must need no changes" premise), or redesign so the raw-`agent` comparison sites genuinely route through `_lib` (which requires editing L42 either way).

### What a passing re-submission needs

1. Reconcile C-1 and C-4: expand the C-4 footprint to `_lib.py`, `test_hooks.py`, AND `dispatch-guard.py`, and rewrite C-1 to require normalizing `agent` at `dispatch-guard.py:42` (raw string preserved for `_log`) rather than asserting dispatch-guard needs no changes.
2. Rewrite the T-001 seam guidance to prescribe the single-line normalization at the source instead of the wrapper-object approach, and delete the "STOP if dispatch-guard must change" instruction.
3. Keep fixture 2 (legal namespaced worker against a bare `executor` field) — it is exactly the L114 regression, and it is the fixture that proves the source-normalization fix works.
