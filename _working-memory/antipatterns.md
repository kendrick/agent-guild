# Antipatterns

<!-- Negative knowledge. Things the team tried that didn't work, captured so   -->
<!-- agents and humans don't re-litigate closed loops. Append-only, like        -->
<!-- decisionLog.md.                                                            -->
<!--                                                                            -->
<!-- Format: -->
<!-- ## YYYY-MM-DD — [Short title in imperative voice — what to avoid]         -->
<!-- **Tried:** What was attempted                                              -->
<!-- **What broke:** Observed failure mode                                      -->
<!-- **Why we backed out:** Root cause if known; otherwise the observed pain    -->
<!-- **Don't suggest:** Specific things agents should not re-propose            -->
<!--                                                                            -->
<!-- The last line is the agent-targeted lever. Be specific. "Don't suggest    -->
<!-- moving X to Y" beats "don't suggest big refactors."                       -->

## 2026-08-10: Don't validate the far side on a value you never sent it

**Tried:** Pinning courier identity on receipt only. Both host adapters require a returned verdict to carry `checker: checker-courier` and the lane's model, and `claude-courier.py` rejects a mismatch by name. Nothing on either lane told the vendor what those values were.
**What broke:** The vendor inferred them, got both wrong, and was rejected twice. Two substantive judgments on the clause under check were discarded over fields nobody had given it, at 101,688 input tokens and 56 seconds for nothing. The ledger recorded `exit_code: 1`, which reads like a vendor failure and wasn't one.
**Why we backed out:** A check on receipt is only half a contract. The half that makes it satisfiable is telling the other side what to send, and when that half lives in prose someone types into a dispatch, it works exactly as long as that person is the one running crossings (#113).
**Don't suggest:** adding a receipt-side validation without naming what tells the far side to satisfy it. Ask where the requirement is stated in what the vendor actually receives. If the answer is a dispatch prompt, it isn't stated.

## 2026-08-10: Don't let a shared parser skip what it doesn't understand

**Tried:** A branch in `_lib.parse_frontmatter` that set a block-scalar key to `""` and skipped its indented body, on the reasoning that the body wasn't needed and its lines must not be read as `- item` entries.
**What broke:** `check_method: >-` is what the task template's own example uses, and its body is the entire contract between a task and its checker. A task cited eleven clauses, named a check for each, and handed its checker an empty string. Nothing reported it (#109); a hand inspection of the frontmatter before dispatch is what caught it.
**Why we backed out:** The skip encoded an assumption about which keys would use the form, inside a parser that doesn't know its keys. It was true when written and false the moment a task file used the documented spelling. Reading the body turns out to keep the guard the skip was buying anyway, since those lines are consumed before the list branch can see them.
**Don't suggest:** a "we don't need this one" branch in a shared parser. Either parse the construct or fail loud on it; the module's own fail-loud rule governs parsing, not just hook exits. And when a parser degrades a value quietly, go looking for the consumer that would report the degradation. If there isn't one, that absence is the second half of the bug.

## 2026-08-10: Don't run a courier crossing from the project root

**Tried:** Probing the `codex` lane with the shipped adapter command, `codex exec --skip-git-repo-check -s read-only ...`, from the repository the artifacts live in.
**What broke:** The vendor shelled out mid-probe and read `_working-memory/activeContext.md` and the whole of `.agent-guild/CLAUDE.md`, including the dual-check section describing the evaluation it was participating in. `-s read-only` constrains writes; it does nothing about reads.
**Why we backed out:** The courier's own spec says the far side "cannot read this repository ... the brief, artifact contents, and locally collected evidence you inline are the only evidence it receives." That premise is false wherever the vendor starts in a tree it can read, and a second opinion that formed its own view from the repo is not judging the brief. Running from an empty directory fixed it: zero `command_execution` events on the next probe. `claude-courier.py` already does this internally with a temp cwd; the Claude to codex lane has no script and inherits the dispatch cwd.
**Don't suggest:** relying on the sandbox flag for evidence isolation, or dispatching a crossing from the project root. Set cwd to an empty directory. The brief is self-contained by contract, so nothing is lost.

## 2026-08-10: Don't accept a CLI status command as lane readiness

**Tried:** SMOKE's Part D preconditions, `codex login status` and `claude auth status --text`, as the check that a courier lane is usable.
**What broke:** Both passed while their lanes were dead. `codex login status` reported "Logged in using ChatGPT" while every call returned 401 on a refresh token that had already been used. `claude auth status --text` succeeds in a terminal whose keychain a sandboxed Codex session cannot reach. Neither command makes a call, so neither can observe what the courier will hit.
**Why we backed out:** A status query reports that a credential is stored somewhere. Lane readiness is a different claim, and the gap between them cost two separate investigations that stopped at an auth-shaped message meaning something else.
**Don't suggest:** a status subcommand as a precondition anywhere. Probe with a real crossing, run from where the courier runs, and read the outcome.

## 2026-08-10: Don't re-run a setup block that calls new-task.py

**Tried:** Re-running Part D's seed block after a partial setup, to be sure the state was complete.
**What broke:** `new-task.py` allocates the next free id every time it runs, so the second pass created T-002, a duplicate of T-001 with the same title and no work behind it. The stop gate then demanded a lifecycle move on a task that existed only by accident.
**Why we backed out:** The script is correct; it is an allocator, not a reconciler, and #14's `open(..., 'x')` design exists so parallel decomposition never collides. Idempotence was never its job.
**Don't suggest:** re-running a seed or setup block to "make sure." Check `.agent-guild/state/tasks/` first and resume from what is there.

## 2026-08-02: Don't count a deterministic clause as cross-family evidence

**Tried:** Dual-checking the smoke job's C-1 (`grep -q GUILD guild-motto.txt`) and reading the resulting agreement as a #34 data point.
**What broke:** Nothing visibly — which is the problem. The courier relays judgment and never executes, so a deterministic clause crosses as pre-run output for the far side to judge. Two vendors handed the same exit code agree every time, so the crossing is guaranteed agreement carrying no information.
**Why we backed out:** #34 rules the multi-provider bet won't-do if the unique-finding rate is near zero. Feed it deterministic clauses and it reaches that verdict by construction, closing v0.6.0 through v0.8.0 on an artifact of method rather than evidence.
**Don't suggest:** counting a deterministic-clause crossing toward #34's ten, or picking a smoke-shaped toy task to "get a data point." The ten tasks need judgment-rubric clauses on real work where two families could plausibly see different things.

## 2026-08-02: Don't judge a gate drill by the session's prose refusal

**Tried:** SMOKE.md's B2 as originally written — "dispatch worker-standard, do not add a Task-ID" — expecting `dispatch-guard` to deny it.
**What broke:** The orchestrator read `.agent-guild/CLAUDE.md`, concluded it couldn't comply, and answered in prose. No tool call, no hook, no denial, and the drill read as a pass. The real `carries no readable id` block only appeared once the prompt insisted the call be attempted.
**Why we backed out:** A compliant orchestrator and a dead gate are indistinguishable from outside, the same trap #67's three failed probes fell into. Fixed in B2, B3a, and B4 (#90, #95).
**Don't suggest:** phrasing a gate drill as a plain instruction, or accepting "the session declined" as evidence a gate fired. Force the tool call and require a denial that quotes the guard.

## 2026-08-02: Don't expect a package fix to reach installed users without a version bump

**Tried:** Delivering the #94 `checker-courier` fix by rebuilding, pushing, and running `claude plugin marketplace update kendrick`.
**What broke:** The marketplace snapshot refreshed and the installed plugin didn't. The install cache is keyed by version at `~/.claude/plugins/cache/kendrick/agent-guild/0.5.0/`, which kept serving the six-agent roster. Three D1 attempts failed at agent registration against a tree that already had the fix.
**Why we backed out:** Only the 0.5.1 bump plus `claude plugin update` created a new cache directory and registered the seventh agent. Verified by the crossing that followed.
**Don't suggest:** "refresh the marketplace" as a delivery path for a shipped-package fix, or verifying a package change against this repo's own `.claude/agents/` — that local copy is why #94 hid for a full release.

## 2026-07-24: Don't ask a read-only vendor to execute anything

**Tried:** The courier's brief left a script-run check method for the far side to satisfy, so the vendor attempted to run a test suite itself.
**What broke:** Its sandbox forbids temp-dir creation, so it returned `blocked` on both test-run clauses (issue #45's crossing) — a wasted #34 data point, since blocked is neither agreement nor a unique finding.
**Why we backed out:** The lane is read-only by contract; execution was never the vendor's job. Arithmetic and comparison are judgment (fair game far-side); running commands is not.
**Don't suggest:** composing a brief that expects the vendor to execute scripts, create files, or run suites. Run the check locally, inline the OUTPUT as evidence, and let the vendor judge results.

## 2026-07-24: Don't ship optional properties in a schema bound for strict structured output

**Tried:** `verdict.schema.json` with `duration_ms`/`cost_usd` as optional properties, checked for codex compatibility by feature-subset inspection (no conditionals, conservative keywords) because no CLI existed to probe.
**What broke:** The first live `codex exec --output-schema` probe (issue #2, 2026-07-24) got a 400: OpenAI strict mode requires `required` to include every key in `properties`. Optionality itself is the rejected feature.
**Why we backed out:** Strict mode's contract is all-required; the expressive equivalent is required-but-nullable, which also matches the ledger's null-means-unreported convention. Proven live: the all-required variant round-tripped a conforming verdict from gpt-5.6-terra. Fix filed as #43.
**Don't suggest:** optional properties in any schema a vendor's strict structured output will consume. Make every field required and type the optional ones nullable.

## 2026-07-24: Don't inline derivable facts into task spec excerpts

**Tried:** The #42 task excerpt hardcoded the version-boundary commit list as orientation for the worker.
**What broke:** The list was wrong — it skipped the 0.2.0 and 0.3.0 bumps. Harmless only because the same excerpt instructed deriving boundaries from git, which the worker did; a checker taking the list literally would have computed wrong verification ranges (the r1 checker caught this).
**Why we backed out:** Excerpts are copied prose; anything derivable drifts the moment it's inlined.
**Don't suggest:** embedding git-derivable lists (boundaries, hashes, counts) in task excerpts. Name the derivation command and let workers and checkers run it.

## 2026-07-23: Don't declare `hooks/hooks.json` in a plugin's `manifest.hooks`

**Tried:** `scripts/plugin-src/plugin.json` declared `"hooks": "./hooks/hooks.json"` (correct when first designed; the plan doc's "hooks have no auto-discovery" platform fact backed it).
**What broke:** The plugin installed but failed to load—current Claude Code auto-loads a plugin's `hooks/hooks.json`, so declaring that standard path is rejected as a duplicate ("manifest.hooks should only reference additional hook files"). Caught by the first live SMOKE Part C run.
**Why we backed out:** Platform behavior changed; the standard path loads on its own now. Fixed in 0.3.1 by dropping the key and rebuilding.
**Don't suggest:** adding a `hooks` key to `scripts/plugin-src/plugin.json` for the standard path, or teaching `build-plugin.py` to emit one. `manifest.hooks` is only for *additional* hook files beyond `hooks/hooks.json`.

## 2026-07-14: Don't assume parent hooks skip subagent tool calls

**Tried:** Building orchestrator-write-guard (and the docs' mental model) on "parent PreToolUse hooks don't fire for tool calls made inside a subagent."
**What broke:** On CC 2.1.x PreToolUse fires in subagents too, so the guard fired in every worker and blocked the deliverable it was dispatched to write. The guild only worked because workers silently fell back to `Bash`.
**Why we backed out:** The assumption was never true on this CC version; `agent_id` is stamped only on subagent calls (confirmed against the hooks docs).
**Don't suggest:** scoping a gate by assuming hooks won't reach subagents. Scope main-session-only gates by checking `agent_id` (`_lib.in_subagent`). See #18.

## 2026-07-14: Don't identify a subagent's task from role:user transcript messages

**Tried:** `id_from_transcript` scanned only `role:"user"` messages for a `Task-ID:` line.
**What broke:** SubagentStop hands the hook the PARENT transcript, where the dispatch is an assistant `tool_use(Task|Agent)` block, not a user message. The id was never found, the gate failed closed, and the worker hung.
**Why we backed out:** Wrong place to look; the authoritative dispatch record is the assistant tool_use.
**Don't suggest:** reading the dispatch id from user messages. Read it from the assistant `tool_use(Task|Agent)` `input.prompt` (last dispatch). See #17.

## 2026-07-28: Don't add courier vendors as a failsafe against courier plumbing bugs

**Tried:** Not a post-mortem — a design on record plus what #69 exposed about it. #11 factors the multi-vendor substrate so that only two clusters differ per lane: the invocation, and "the failure detection (quota and rate-limit strings)," the latter living as per-lane manifest data. The intuition under review was that more lanes (gemini, opencode, qwen) would cross-check each other's failures.

**What broke:** #69's classifier bug is local Python, not model judgment. `_is_quota` sorts an exit code, stdout, stderr, and a parsed envelope into `{verdict, quota, blocked}` with no model in the loop, so a second lane cannot second-guess it — it ships its own copy. The divergence is already visible at N=2: the Codex-host `claude` lane classifies deterministically in `claude-courier.py`, while the Claude-host `codex` lane has no equivalent script and leaves the agent to judge `codex exec` output. Two lanes, two mechanisms, one of them never tested. Five CON-audit rounds on #69 were spent specifying the one that exists.

**Why we backed out:** The classification *algorithm* is vendor-independent — structural signal before wording, the errorish gate, restricting the search surface, bounding the numeric token. Only the inputs are vendor-specific: which field carries error text, which carries the status code, which values mean "this is an API error." #11 lumps the two together, so every new vendor reimplements the algorithm alongside its descriptor.

**Don't suggest:** adding a courier lane to harden failure classification, or treating per-lane quota patterns as sufficient vendor isolation. Amend #11 to share one outcome classifier fed by a small per-vendor descriptor, and make #69's ten-row behavior table a conformance suite every lane runs. Two standing preconditions before any new lane: #34 has to answer whether cross-family checking pays at all, and each vendor needs its own live-probe issue in the shape of #52 (success envelope, malformed output, auth failure, invalid model, quota) before its courier is written.

## 2026-07-31: Don't settle a host-contract question from transcript inference

**Tried:** Concluding that Codex never fires `SubagentStop`, on the strength of a 7/29 rollout showing `wait_agent` returning `{"message":"Wait completed.","timed_out":false}` alongside zero captures. That was read as a subagent demonstrably completing while a registered recorder caught nothing.
**What broke:** "Wait completed" describes the wait call finishing, not the agent. The same call rendered live as "Finished waiting / No agents completed yet." The conclusion was posted to #67 and #68 and #68 was retitled around it, then retracted, then contradicted again when a clean-quit probe showed the event firing normally at agent completion.
**Why we backed out:** Absent captures are not evidence of an absent event without a control that proves the recorder would have caught one. Three claims in a row rested on reading a vendor's status string as a lifecycle fact.
**Don't suggest:** concluding a hook event doesn't fire from missing captures alone, or reading a vendor's completion wording as a lifecycle guarantee. Register a control event known to fire in the same session and same recorder first, and prefer one live run over any amount of transcript archaeology.

## 2026-08-01: Don't probe a boundary by asking a compliant agent to cross it

**Tried:** Testing two host boundaries by prompting a Codex session to exercise them normally: issue a `followup_task` at a guild agent, and have a read-only checker write inside the workspace.
**What broke:** Neither call was ever made. The orchestrator read the guild contract, declined the followup, and offered to spawn a properly identified task instead; the checker obeyed its read-only role protocol and staged its file in `/private/tmp`, which the protocol doesn't forbid. Three sessions produced zero evidence about either boundary while looking like clean runs. The `followup_task` gate was only verified once a prompt told the model to ignore the contract for that one call and report the block verbatim.
**Why we backed out:** A well-instructed agent tests the instruction, not the enforcement underneath it. The two are indistinguishable in the transcript, and the compliant outcome is the more convincing of the two, which is what makes it a trap.
**Don't suggest:** verifying a gate, sandbox, or matcher by asking an agent to do the forbidden thing in the ordinary way. Name the override explicitly ("ignore the contract for this one call, report the block, do not work around it"), and confirm the call was actually issued from a matcher-less capture or the session transcript before reading anything into the result.
