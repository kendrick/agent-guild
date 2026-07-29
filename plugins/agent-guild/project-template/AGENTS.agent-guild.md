<!-- agent-guild:codex:start -->
## Agent Guild

Before running an Agent Guild job, read `.agent-guild/CLAUDE.md`; its lifecycle and state-file contract is authoritative. Apply the Codex host mapping below.

### Project Agent Roster

| Agent | Route | Sandbox |
| --- | --- | --- |
| `auditor` | Guild auditor for the constitution and task decomposition. Dispatch with an Audit-ID. | `read-only` |
| `checker-courier` | Read-only Guild courier for an independent second opinion. Dispatch with a Task-ID; its suffixed verdict never decides the task. | `read-only` |
| `checker-deterministic` | Read-only Guild checker that runs only the deterministic checks named by a task. Dispatch with a Task-ID. | `read-only` |
| `checker-judgment` | Read-only Guild checker that independently evaluates judgment clauses against artifact evidence. Dispatch with a Task-ID. | `read-only` |
| `hydrator` | Guild specialist for the five-phase working-memory hydration pipeline. | `workspace-write` |
| `worker-bulk` | Guild worker for mechanical, zero-judgment execution. Dispatch with a Task-ID. | `workspace-write` |
| `worker-craft` | Guild worker for user-facing, taste-sensitive work. Dispatch with a Task-ID. | `workspace-write` |
| `worker-standard` | Guild worker for clear-spec implementation judged primarily on correctness. Dispatch with a Task-ID. | `workspace-write` |
| `working-memory-synchronizer` | Guild specialist for synchronizing working memory after material project changes. | `workspace-write` |

### Codex Dispatch Boundary

- The main session is the orchestrator. Delegate Guild work to the exact project agent named by the routing table.
- Worker and checker dispatches carry `Task-ID: T-NNN`; auditor dispatches carry `Audit-ID: CON-audit` or `Audit-ID: DEC-audit`. Put the id in the prompt on a Claude host, in `task_name` on a Codex host.
- Read-only agents return the intended state-file path and complete content to the orchestrator. Never grant them write access to bypass that boundary.
- A read-only `checker-courier` returns an `AGENT_GUILD_COURIER_OUTCOME` from the fixed Claude runner. For a verdict outcome, persist the supplied verdict unchanged at the `-claude` suffixed path, validate and render it, then record the supplied metrics through `ledger-append.py`. For a quota outcome, append that ledger line first with `--quota-event`, then create `.agent-guild/state/exhausted/claude`; write no verdict. A courier outcome never replaces the unsuffixed in-family verdict.
- Agent Guild owns only this marked section of `AGENTS.md` and its generated files under `.codex/agents/`.

### Workflow Entry Point

- Start existing work with `${{AGENT_GUILD_SKILL_PREFIX}}job <issue|file|url>`.
<!-- agent-guild:codex:end -->
