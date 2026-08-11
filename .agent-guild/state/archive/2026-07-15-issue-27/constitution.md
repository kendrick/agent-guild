# Constitution: Namespaced Dispatch Recognition (Issue #27)

<!-- Spec: .agent-guild/state/spec.md (intake of kendrick/agent-guild#27).
Fully-collapsed interview: the issue settles the fix (normalize subagent_type
before the GUILD_AGENTS/DEFAULT_MODEL lookups; fixture coverage for bare and
namespaced forms; must land before #21). Design detail settled here as
orchestrator: normalization takes the suffix after the last colon for lookup
purposes only — logs keep the original dispatched string so the record shows
what actually ran. Deliverable surface: .agent-guild/hooks/_lib.py and
test_hooks.py, nothing else. -->

## Clauses

### C-1: normalize once at the source, identity in the log
- **text**: `_lib.py` gains a single helper mapping any `<ns>:`-prefixed `subagent_type` to its bare suffix (bare names pass through unchanged), and `dispatch-guard.py` applies it exactly once, where the agent string enters (`agent = <helper>(ti.get("subagent_type", ""))`), so every downstream consumption — `GUILD_AGENTS` membership, `DEFAULT_MODEL` lookups, the `== "auditor"` branch, the `!= executor` comparison — sees the bare name. The raw dispatched string is kept in its own variable and is what `_log` records, so the audit trail shows what actually ran. No scattered strips, and no behavior change in subagent-return, stop-gate, or the write-guard. (DEC-audit r0 proved a wrapper-only seam in `_lib` cannot work: the auditor-branch and executor string comparisons in dispatch-guard consume the raw string directly.)
- **check**: checker-judgment: read the diffs of both files; confirm one normalization application at the entry seam, raw-string log fidelity, every downstream site consuming the normalized name, and zero changes beyond the seam and the helper.
- **severity**: blocker
- **failing example**: the strip is applied inside `_log()` too, so the dispatch log shows `worker-standard` for a dispatch that actually ran `agent-guild:worker-standard`, and the record can no longer distinguish plugin from in-repo dispatches.

### C-2: the gate now gates namespaced dispatches — proven behaviorally
- **text**: Run as a real hook process, `dispatch-guard.py` blocks a namespaced guild dispatch that omits a Task-ID exactly as it blocks a bare one (exit 2, "has no id line"), and passes a namespaced auditor dispatch that carries a legal `Audit-ID` (exit 0). This is the live failure #27 documents, exercised end to end, not inferred from unit internals.
- **check**: .agent-guild/scripts/check-build.sh 'proj=$(mktemp -d) && mkdir -p "$proj/.agent-guild/state/tasks" "$proj/.agent-guild/state/log" && printf "%s" "{\"tool_input\":{\"subagent_type\":\"agent-guild:worker-standard\",\"prompt\":\"no id line here\"}}" | CLAUDE_PROJECT_DIR="$proj" python3 .agent-guild/hooks/dispatch-guard.py 2>"$proj/err1"; rc1=$?; grep -q "has no id line" "$proj/err1" && test "$rc1" -eq 2 && printf "%s" "{\"tool_input\":{\"subagent_type\":\"agent-guild:auditor\",\"prompt\":\"Audit-ID: CON-audit\"}}" | CLAUDE_PROJECT_DIR="$proj" python3 .agent-guild/hooks/dispatch-guard.py; test $? -eq 0'
- **severity**: blocker
- **failing example**: the helper strips only the literal `agent-guild:` prefix, a future rename of the plugin to `guild` reintroduces the bypass, and the namespaced no-id dispatch exits 0 again.

### C-3: fixture coverage for both forms, suite green
- **text**: `test_hooks.py` gains fixtures driving `dispatch-guard.py` with namespaced `subagent_type` values alongside the existing bare-name coverage — at minimum: namespaced worker without Task-ID blocked; namespaced worker fully legal (task assigned, CON-audit present, model matching) passes; bare names still behave (regression). The full suite reports at least 53 passed, 0 failed (51 today plus at least two new).
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/hooks/test_hooks.py 2>&1 | grep -qE "(5[3-9]|[6-9][0-9]|[1-9][0-9]{2,}) passed, 0 failed"'
- **severity**: blocker
- **failing example**: the new fixtures only cover the blocked case, so a normalization bug that blocks namespaced dispatches but never lets a *legal* one through (DEFAULT_MODEL KeyError on the namespaced key) ships green.

### C-4: the footprint is exactly the three hook files
- **text**: The job's entire working-tree footprint is modifications to `.agent-guild/hooks/_lib.py`, `.agent-guild/hooks/dispatch-guard.py`, and `.agent-guild/hooks/test_hooks.py` — no other modification, deletion, or untracked addition anywhere (repo-wide porcelain assertion with three excludes, per the house pattern from #22's audit). `dispatch-guard.py` is in scope because DEC-audit r0 proved the fix requires normalizing at its entry seam; the change there is bounded by C-1 to that seam.
- **check**: .agent-guild/scripts/check-build.sh 'test -z "$(git status --porcelain -- . ":(exclude).agent-guild/hooks/_lib.py" ":(exclude).agent-guild/hooks/dispatch-guard.py" ":(exclude).agent-guild/hooks/test_hooks.py")"'
- **severity**: blocker
- **failing example**: the worker also edits `subagent-return.py` "while in there," changing a live gate no clause reviewed.

### C-5: the fix explains itself
- **text**: The normalization helper carries a why-comment naming the incident class it guards against — plugin-shipped agents dispatch under `<plugin>:<name>` and a bare-name membership test silently un-gates them — in the module's existing comment voice (compare `in_subagent()`'s load-bearing note). The new fixtures' labels say what they prove.
- **check**: checker-judgment: read the helper's comment and the fixture labels; fail on a bare `# strip prefix` or fixture names that don't state the behavior under test.
- **severity**: major
- **failing example**: the helper ships with no comment, and the next refactor "simplifies" it away, reintroducing the bypass the moment nobody remembers why the split existed.

## Protected content

- none.

## Non-goals

- Committing the plugin tree (#21), the nudge (#23), marketplace (#24), docs (#25), the `/job` flow-through fix (#26).
- Disabling the stale dist-era plugin in this repo — the issue records it, but that's the user's environment action, not a repo deliverable.
- Any change to the SubagentStop matcher or hooks.json generation; the substring match already fires for namespaced agents, and #21's build carries the registration surface.
