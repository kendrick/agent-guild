# Data Contracts

The kit has no application data. Its "contracts" are the shapes of the file-based message bus under `.agent-guild/state/`, and the source of truth for each is a template in `.agent-guild/templates/`. Consume these shapes through the templates; don't restate them here (that just drifts).

## Project Bootstrap Ownership

The shared installer copies missing host-neutral payload files under `.agent-guild/` but never overwrites differing local payload content. It owns its bounded guidance section: `<!-- agent-guild:claude:start -->`…`<!-- agent-guild:claude:end -->` in `CLAUDE.md`, or `<!-- agent-guild:codex:start -->`…`<!-- agent-guild:codex:end -->` in `AGENTS.md`. Existing legacy Claude guidance consisting of the exact `@.agent-guild/CLAUDE.md` import remains valid and unchanged.

For Codex, the installer also owns the generated files matching the packaged roster under `.codex/agents/`. In repo-local mode only, it owns packaged files under `.agents/skills/`, except the audition result log, and packaged scripts under `.agent-guild/hooks/`. It merges Agent Guild handlers into `.codex/hooks.json`, identifying ownership by the `codex-hook-adapter.py` command signature; all unrelated top-level fields, event groups, and handlers remain project-owned. It may replace owned generated files, hook handlers, and guidance sections on update. It must preserve `.codex/config.toml`, unrelated hooks, agents and skills, audition results, all guidance outside the markers, and every path outside the project; malformed hook JSON, marker cardinality/order, or any managed path resolving outside the project is a fail-closed error before writes.

Codex agents whose generated `sandbox_mode` is `read-only` never persist verdict, ledger, task, or other state content. Their return contract is the intended state-file path plus complete proposed file content; the parent orchestrator independently checks and persists it.

## The Bus

`.agent-guild/state/` holds the running job. Everything is Markdown, with the schema-bearing files carrying YAML frontmatter:

- `spec.md`, `constitution.md` — the job's inputs, written by the orchestrator.
- `tasks/T-NNN.md` — one file per unit of work. Schema: `.agent-guild/templates/task.md`.
- `verdicts/T-NNN-<tier>-r<retries>.json` — one checker verdict per attempt, JSON of record (see Verdict Result below) with a rendered `.md` sibling at the same stem. Audit verdicts (`CON-audit-rN.md`, `DEC-audit-rN.md`) stay Markdown.
- `disputes/T-NNN-<tier>-r<retries>.md` — a worker's case that a check was wrong. Schema: `.agent-guild/templates/dispute.md`.
- `notes/T-NNN.md` — the worker's self-report. Off-limits to checkers and the orchestrator by design; it exists so verification never leans on "I did it."
- `briefs/T-NNN.md` — self-contained vendor briefs from `compose-brief.py` (see Briefs below).
- `log/` — dispatches, escalations, the stop-gate's per-task livelock counters, and the vendor call ledger (see below).

## Constitution Weight Line

Source: `.agent-guild/templates/constitution.md`. A `**Job weight**: <light | standard | deep>[, corrected from <derived weight> by the user], <one-line reason>` line sits between the title and the template's comment block, written by the `constitution` skill in Phase 0 (#123). It sets one budget, the clause ceiling: 5 for light, 8 for standard, none for deep. The auditor reads it for that ceiling and reports an unexplained overrun or a missing line; nothing else reads it, and no script parses it at all. The optional middle segment keeps the derived weight when the user overrides it, because the correction is the most useful thing the retrospective can report back about the derivation.

Nothing below `## Clauses` is safe to add to lightly: `check-job-spec.parse_constitution` ends a clause block at the next `### C-N:` heading rather than at `##`, so `## Protected content` and `## Non-goals` are scanned as the last clause's prose and a citation defect in them is reported against that clause. The weight line sits *above* `## Clauses` and is unaffected. Tracked in #160.

## Task Frontmatter

Source: `.agent-guild/templates/task.md`. Fields: `id`, `title`, `spec` (anchor into `spec.md`), `clauses[]`, `executor`, `executor_model`, `checker`, `check_method`, `status`, `retries`, `max_retries`, `deps[]`, `dep_rationale[]`, `owns[]`, `escalations[]`, `artifacts[]`. Every clause in `clauses` must appear in `check_method`, named to a script invocation or a `checker-judgment` rubric.

`owns[]` (#133) declares every path the task writes: an exact file path, or a directory prefix ending in `/`. Two tasks whose entries overlap must be connected by a dep path, which is what keeps them out of one wave (`rule_R13`). An empty `owns` is the ABSENCE of a claim, not a claim to write nothing, and it is the shipped template default. `ready-set.py` therefore refuses to group a task that declares none with any peer (#162); R13 and R14 still skip such a task entirely, which is the half of #162 still open.

`dep_rationale[]` (#125) carries one `T-NNN: why` line per entry in `deps`. `rule_R14` checks only that the two lists correspond one to one, and only on a task that also declares `owns`. Whether a rationale actually holds is DEC-audit judgment, not a linter's.

`check_method` is normally a YAML block scalar (`>-`), which `_lib.parse_frontmatter` reads since #109; before that it parsed to `''` and the checker ran nothing. Any block scalar works now (`|`, `>`, with any chomping indicator), matching YAML semantics closely enough that Ruby's psych agrees on the kit's fixtures. Explicit indentation indicators (`|2`), anchors, and nesting are still unsupported and always were. A task that cites clauses while `check_method` resolves empty is refused by `dispatch-guard` for workers and checkers alike.

## Status Enum

`pending` → `assigned` → `needs-check` → `checking` → then `rework` (loops back to `assigned`) or `disputed` or `complete`; `abandoned` is the cancelled terminal. Who moves each status is the table in `.agent-guild/CLAUDE.md`—workers set only `needs-check` and `disputed`; the orchestrator owns the rest.

## Verdict Result

JSON is the verdict of record (since #29): `verdicts/T-NNN-<tier>-r<retries>.json` conforming to `.agent-guild/schemas/verdict.schema.json`, validated by `validate-verdict.py`, with the human-readable `.md` sibling generated by `render-verdict.py` — never hand-written (`.agent-guild/templates/verdict.md` is the renderer's shape reference). `subagent-return` rejects a checker return whose JSON is missing or nonconforming. `verdict` is one of:

- `pass` — every clause satisfied, each backed by evidence the checker re-derived.
- `fail` — one or more clauses violated; at least one finding with concrete `evidence` is required (validator-enforced; the dispute protocol depends on it).
- `blocked` — the check itself couldn't run (script crashed, tool unreachable, vendor quota). Carries the old ERROR semantics: fix the check, re-dispatch, doesn't count against the worker's tier budget.

All nine properties are required, with `duration_ms` and `cost_usd` typed nullable (#43): OpenAI strict structured output rejects optionality outright, so required-but-nullable is how an optional field is expressed to a vendor. Null means unreported, never zero, matching the ledger's convention.

A finding's `severity` is an enum of `blocker`, `major`, `minor`, `info`, measured by defect impact (#115). `info` is a finding that records a clause being *satisfied* — a clause's own severity in the constitution is the cost of violating it, not the label for every finding about it. A `pass` therefore carries only `info` and `minor`; `validate-verdict.py` rejects one carrying `blocker` or `major`, its third semantic rule alongside fail-needs-a-finding and evidence-must-be-non-empty. The schema can't express any of the three (structured-output-safe, no if/then), but its `description` strings do reach the vendor: both lanes pass the schema itself as the output schema.

## Second-Opinion Verdicts

The courier writes to a host-mapped lane suffix: `verdicts/T-NNN-<tier>-r<retries>-<lane>.json` plus its rendered sibling, where Claude uses `codex` and Codex uses `claude`. It uses the canonical verdict schema and is comparison data only; the standard-stem verdict decides the task and is never outvoted.

A read-only Codex courier returns `AGENT_GUILD_COURIER_OUTCOME\n<json>` rather than writing state. The object has exactly `status`, `verdict`, `ledger`, `attempts`, and `diagnostic`; the return gate validates its task/lane/model identities, ledger field types, quota consistency, and canonical verdict before the parent persists it. For `status: verdict`, the parent writes the unchanged `-claude` verdict, validates/renders it, then appends the ledger. For `status: quota`, the parent appends the quota ledger line first, then creates `state/exhausted/claude`, with no verdict.

## Read-Only In-Family Returns

A Codex in-family checker (`checker-deterministic`, `checker-judgment`) runs `sandbox_mode: read-only` and cannot write its own verdict, so it returns `AGENT_GUILD_VERDICT\n<json>` as its last message. The object is the canonical schema verdict with no envelope around it, unlike the courier's outcome above, because an in-family checker produces no ledger and has no quota protocol. The return gate validates it against the schema and confirms `task_id` and `checker` match the return it belongs to, then the parent writes it unchanged to the standard stem and renders the `.md` sibling. The file stays the verdict of record wherever a checker can write one: the inline branch opens only when the file is missing or invalid and the host is Codex, so the Claude path never reaches it.

`subagent-return.py` compares the returned `ledger` object against a required key set **plus** `optional_ledger_fields`, rather than against one exact set. `discarded` is the first member (#116/T-009); a future optional key appends there. Widening that set is the load-bearing half of adding any ledger field the claude lane emits — without it the hook blocks the return, the crossing is never promoted, and the debt rides to `STALLED.md` with every test still green, because both consumer fixtures hand-build their payloads instead of calling the courier.

## Lane Exhaustion

`state/exhausted/<lane>` — a per-lane sentinel (directory form, so one `ls` shows every downed lane), created by a courier on a quota signal *after* its ledger line lands, so the ledger always explains the sentinel. While it exists, `dispatch-guard` denies dispatches on that lane; only the user clears it, the same contract as PAUSED.

## Vendor Call Ledger

`state/log/vendor-calls.jsonl`, one JSON line per external invocation, schema `.agent-guild/schemas/vendor-call.schema.json`, appended only through `ledger-append.py` (validate-before-append; append-only even over a malformed line). Null means the vendor didn't report it — never a fabricated zero. `brief_tokens` uses the `heuristic-bytes/4` estimator, named in the `tokenizer` field. Collector doc: `docs/vendor-ledger.md`, including the three courier obligations #8's constitution must enforce.

`job` names the run a row came from, spelled as that run's provenance `ref` (`kendrick/skills#17`). It's the line's only optional key, and optional on purpose: it sits in `properties` and not in `required`, so rows written before #117 still validate. An absent key reads as unattributed rather than attributed to nothing; there is no null spelling. `ledger-append.py` resolves it in three steps and no others: `--job VALUE`, then `spec.md`'s provenance `ref` read from the working directory, then omission. Deriving from the spec is what makes it stick—`.agent-guild/state/` is wiped between jobs, and a courier that has to pass a flag is a courier that can forget to. (#117)

`attempts` (integer) and `discarded` (array of objects carrying `reason`, `duration_ms`, `exit_code`, `tokens_in`, `tokens_out`) were added by #116. Both are optional, and optionality is the whole point: it is what keeps the 21 rows written before the change valid. Inside a `discarded` entry the types mirror the top-level fields of the same name, so `tokens_in`/`tokens_out` are `["number", "null"]` and an attempt whose usage the vendor never reported writes `null`.

Two figures the ledger still does not carry, both visible in the same vendor `usage` block: `cached_input_tokens` and `reasoning_output_tokens`. `codex-courier.py:196` names the first and declines to read it, and whether it is a subset of `input_tokens` or disjoint from it is unresolved — the answer decides whether the ledger misprices or undercounts (#157).

## Briefs

`state/briefs/T-NNN.md` from `compose-brief.py T-NNN [--out PATH] [--vendor V --model M]`: task id/title, the full text of every cited constitution clause (never ids alone), the `## Spec excerpt` verbatim, and `## Prior attempt diagnosis` only when a rework diagnosis exists. Self-contained by contract — no state paths presented as readable, no CLAUDE.md references. The golden tests in `test_compose_brief.py` pin this format; it's what external vendors receive.

`--vendor` and `--model` carry the lane's pinned identity and append a final `## Verdict contract` section: the four identity fields to echo verbatim (`task_id`, `checker: checker-courier`, vendor, model), null call metrics, the fail-needs-a-finding rule, and what each severity means. Pass both or neither; one alone exits 1. Each host adapter's courier suffix names the flags for its own lane, which is where the pin lives until #35 single-sources vendor config. Before #113 none of this was in the brief and the far side guessed its own identity.

## Job Spec Linter

`check-job-spec.py [STATE] [--repo-root PATH] [--audit-id CON-audit|DEC-audit] [--self-test]`, run over `state/constitution.md` and `state/tasks/`. Exit 0 clean, 1 a rule is violated, 3 infra (state dir missing, a file unreadable, a kit script it imports unavailable). A violation is exactly one stderr line prefixed `job-spec: ` with the rule id first, and only the first violation is reported, rules evaluated proofs-before-heuristics. Under `CON-audit` an empty `tasks/` is expected and the wiring, DAG, and build-order rules are skipped; under `DEC-audit` an empty `tasks/` is itself the failure.

`dispatch-guard` is the consumer and treats the three exits differently: 1 blocks and quotes the diagnostic with a reproduce command, 3 blocks with its own message because a linter that could not read the paperwork is no evidence the paperwork is sound, and a missing script or a timeout allows the dispatch. Missing is the payload-freeze case, where a repo's hooks can be newer than the scripts beside them and a hard fail would brick every auditor dispatch. A timeout appends to `state/log/gate-gaps.log` and writes a stderr note, so an un-run gate is auditable rather than silent.

The rule severities it checks against are imported from `validate-verdict.py`'s `DEFECT_SEVERITIES` rather than restated, so the pass-carrying-a-defect rule keeps one home. (#132)

## Ready Set

`ready-set.py [STATE] [--running T-NNN ...]` prints one JSON object with four keys, always in this order: `wave` (dispatch executors now, each `{id, agent, reason}`), `checks` (`needs-check` tasks owing a checker, same shape), `deferred` (`{id, reason, kind}`, reason naming unmet deps, an owns collision, undeclared ownership, or a spent retry budget), and `attention` (`{id, reason}`: a `disputed` task, or one whose dep is `abandoned`). `kind` (#163) is the machine-readable twin of `deferred`'s reason string: `"deps"`, `"owns"`, `"owns-undeclared"`, or `"budget"`. Exit 0 computed, 3 infra: an unreadable or unparseable task file, a duplicate frontmatter `id`, or a STATE dir that does not exist. A STATE dir with no `tasks/` is exit 0 with empty buckets, since no job active is not an error.

It is a pure function of the task files plus the supplied `--running` list, and it deliberately never reads `state/log/in-flight/` itself. That is what makes a Claude host and a Codex host compute the same wave from the same inputs; a fallback to reading markers here would reintroduce the host drift the script exists to remove. Determinism is part of the contract: every bucket sorts ascending by numeric task id, and where two candidates collide the lower id wins the wave.

`stop-gate.py` is the only in-tree consumer. It supplies `--running` from its own fresh markers and must honor all four buckets, since a task the gate advises against ready-set's own verdict is how #165's review found the gate instructing a dependency violation. Since #163 it also reads `kind` to pace its own per-task stall counters (see Stop-Gate State below), not just to phrase the block message. Only `"deps"` and `"owns"` hold a task's counter, since nothing but waiting resolves either. `"budget"` does not: a spent retry budget is an orchestrator judgment call (escalate a tier, re-decompose, hand it to the user) that waiting can never resolve. `"owns-undeclared"` does not either, and that one is load-bearing: ready-set defers an undeclared task against every id in `--running`, and `owns: []` is what `templates/task.md` ships, so holding it would let one live subagent freeze every other pending task's counter, which is the exact bug #163 was filed about. A missing script, a timeout, a non-zero exit, a partial result, or unparseable JSON all degrade to per-task `_next_move` advice and empty the deferred set, so every task stays eligible; the gate never blocks less than it did before, only presents (and paces) differently. A `deferred` entry with no `kind` at all (a copied-in script predating #163) is the one partial case the gate maps back from the reason string rather than treating as a degrade, so version skew doesn't punish a task that is legitimately waiting.

## Stop-Gate State

`state/log/stop-gate.state` (#163): `{"entries": {key: {"digest", "count"}}, "transcript_size": N}`. One entry per open task (keyed `T-NNN`) and one per held courier debt (keyed `debt:<stem>-<lane>`). `digest` is that entity's own slice of the job state (status, retries, its own verdicts and in-flight markers, and, for a task, its ready-set disposition); `count` is how many consecutive blocked turns it's sat unchanged through. `STALLED.md` names an entity once its count reaches 3. A file written before #163 carries no `entries` key at all and reads as empty, restarting every counter; there's no migration, since the file only tracks one job's blocked turns and a mid-flight upgrade loses at most two strikes of history.
