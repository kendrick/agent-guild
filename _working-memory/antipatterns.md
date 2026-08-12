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

## 2026-08-11: Don't treat a field a model writes about itself as identity evidence

**Tried:** Verifying a courier verdict's `model` by comparing it against the lane's pinned string. The far side was told the exact value to echo (#113 added that instruction), so echoing something else was read as a signal worth acting on.
**What broke:** Over the #100 run the codex lane returned `gpt-5.6` where the adapter pins `gpt-5.6-terra`, intermittently, on the same lane and the same composition path. Both possible responses did damage and the run produced one of each. T-001 r0 persisted the unverified value into the corpus #34 rules on. T-004 refused it and blocked, discarding a `fail` with two major findings that had nothing to do with the model field.
**Why we backed out:** The comparison was never testing what it looked like. Asking a model to write down its own name gets you a string it was handed and is now repeating, and instruction-following on that string degrades with prompt length. Nothing about the answer is evidence of which model answered. The lane knows what it ran, so the lane stamps it: `-m` on the command, the value stamped onto the verdict, the vendor's echo recorded as an `info` finding when it diverges. Note the reciprocal lane's `modelUsage` check survived this, because that is the CLI's own billing record rather than the model's opinion of itself.
**Don't suggest:** validating any field a model wrote about its own identity, configuration, or capabilities against an expected value, and never blocking a judgment on one. Verify what the far side genuinely knows (which task, which role, whose API), take the rest from the caller, and record a divergence rather than acting on it.

One fact in the 2026-07-28 courier-vendors entry below stopped being true with this work, and it is the half that entry was least happy about: the Claude-host `codex` lane now classifies deterministically in `codex-courier.py`, with its own behavior table, rather than leaving an agent to read `codex exec` output. "Two lanes, two mechanisms, one of them never tested" is down to two lanes and two tested mechanisms. The entry's actual recommendation is untouched and still open: one shared classifier fed by a per-vendor descriptor, instead of the second copy this shipped.

## 2026-08-10: Don't cap audit rounds before removing the cheap ones

**Tried:** #120's proposal to give CON-audit and DEC-audit a round budget, on the reasoning that eight rounds on `skills#27` and nine on `agent-guild#117` were obviously too many.
**What broke:** Nothing yet, because it was measured before it was built. Replaying #117 against a three-round cap: the cap lands before DEC r2 found a task holding a clause its own worker was forbidden to clear, and before DEC r3 found a `check_method` instructing a verdict `validate-verdict.py` refuses to write. The budget buys wall clock by cutting exactly where the value was.
**Why we backed out:** The round count was a symptom. Six of #117's eleven audit findings were provable by a script — unresolvable citations, a count disagreeing with its source file, a clause saying "five files" above a list of six, a DAG hole — and each cost a full opus round at 300-550 seconds. Remove those and the round count falls out; cap the rounds and you lose the judgment ones too, since the mechanical defects surface first.
**Don't suggest:** a budget, a timeout, or a "good enough after N rounds" rule on any verification loop before measuring what the loop is actually spending its rounds on. Sort the findings into "a script could have proven this" and "this needed judgment" first. If the first pile is large, that is the fix.

Revisited 2026-08-12 under #120, on the deferral [[decisionLog]] recorded: the budget was parked until #132's linter removed the cheap rounds, and #132 shipped. A budget was built on that basis, 1 round light / 2 standard / 3 deep, and then cut again. This time there were numbers. Counting CON-audit stems across the three runs that finished *after* the linter landed: `2026-08-11-issue-100` used r0 through r2, `2026-08-11-issue-141` used r0 through r4, and `2026-08-12-courier-lane-cleanup` used r0 through r3. Two of the three blow a deep budget of 3, and on the most recent one the round the cap removes is r2, where the auditor found C-9 and C-2 contradicting each other so that every worker was guaranteed to fail whatever they did.

So the entry holds, and holds harder than when it was written. Its precondition was met and the conclusion did not change: removing the mechanically provable rounds shortened the loop without bringing it under three. What shipped instead bounds the *document* rather than the loop, a clause ceiling carried by [[job-weight]], on the reasoning that clause count is what the round count tracks. If a round budget is proposed a third time, it needs a derivation against this corpus in the proposal, not after review.

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

**Recurred 2026-08-12**, 19 days after this entry was written, on the courier-lane cleanup run's T-004 crossing. The courier asked the far side to copy a working tree and run `compose-brief.py`; the vendor has no execution environment and returned `blocked` with an empty findings array, at 124,687 input tokens, the most expensive crossing of the run. The same run's later crossings, composed as evidence plus a question, cost about a sixth of that. The entry existed, was correct, and did not reach the agent that needed it — which says the remedy belongs in `guild-core/roles/checker-courier.md`, not only here.

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

## 2026-08-11: Don't add a third-party import to anything a hook can reach

**Tried:** Reaching for `markdown-it-py` while building `check-job-spec.py` (#132), to get a real Markdown AST with line maps instead of hand-rolling block structure, and PyYAML for the frontmatter parser instead of extending the kit's own.
**What broke:** Caught before it shipped. `plugin/hooks/hooks.json` invokes every gate as bare `python3 <script>` with a 30s budget: no venv, no pinned interpreter, and `install-project.py` has zero dependency-install logic. An `ImportError` anywhere reachable from `dispatch-guard` becomes `HOOK ERROR` and exit 2, which blocks every auditor dispatch in that project. The linter built to unblock jobs would have deadlocked them.
**Why we backed out:** The escape hatches are all worse. A pip bootstrap on first run fights PEP 668 and the hook's own timeout; vendoring adds a few thousand lines to every user's repo through `copytree`; an optional import with a regex fallback makes the gate's verdict depend on what happens to be installed. The measured payoff was small anyway: an AST would have improved exactly one rule, and none of the rules worth worrying about are Markdown problems. PyYAML fails for a second reason that outranks packaging: the linter's job is to prove the paperwork is readable by the tools that consume it, and those tools use the kit's hand-rolled parser, so a stricter-or-looser parser would bless files the real consumers choke on.
**Don't suggest:** any non-stdlib import in `.agent-guild/scripts/` or `.agent-guild/hooks/`, and don't suggest PyYAML for kit frontmatter even where it would be more correct. Extend the parser in `compose-brief.py` or import from it. `graphlib`, `difflib`, `shlex`, and `bash -n` cover most of what the temptation is actually for.

## 2026-08-11: Don't measure near-duplicate prose with SequenceMatcher.ratio

**Tried:** Catching a count that disagrees across two artifacts (#117's D9, where one task still said "eleven" after a sweep fixed everything else) by comparing number-stripped sentences with `difflib.SequenceMatcher(...).ratio()` above a threshold.
**What broke:** No threshold exists. Measured on the real corpus, the defect's own sentence pairs score 0.386 and 0.432 while legitimate number-differing pairs run 0.55 to 1.000, because the `## Courier comparison` blocks are byte-identical templates carrying per-task numbers. The signal sits underneath the noise floor, so any cutoff either misses every real case or fires on template boilerplate.
**Why we backed out:** Whole-sentence similarity answers "are these sentences alike," and the question is "do these two sentences share a long span that one of them numbers differently." Longest common substring answers that directly: at a 60-character floor the corpus yields zero hits clean and one exact hit mutated, with a 93-versus-38 margin.
**Don't suggest:** a similarity ratio with a tuned cutoff for any near-duplicate-prose detection in this repo. Reach for `find_longest_match` on the normalized text and gate on span length. And measure the signal against the noise on a real corpus before believing any threshold, rather than picking one that sounds strict.

## 2026-08-11: Don't make a rule non-gating by printing to stdout

**Tried:** Shipping a low-confidence linter rule as "warn-only" during #132's design, so a heuristic with a false-positive risk could report without blocking a dispatch.
**What broke:** It would have been dead code. `check-job-spec.py` runs as a subprocess inside `dispatch-guard`, which reads the child's stderr to build its block message and discards stdout. A rule that only prints produces output no human or agent ever sees, while still carrying its full maintenance and false-positive-tuning cost.
**Why we backed out:** In a hook-invoked script "warn" is not a middle setting between block and absent, it is a more expensive spelling of absent. The rule was cut instead, and the gap closed from the other end by making the paperwork decidable: the constitution template and skill now ask an author to list what a clause enumerates, so the mechanical rule that does gate can check it.
**Don't suggest:** a warn-only, advisory, or `--strict`-gated tier for any check that runs inside a hook, unless the same change also gives the warning a path to a human. Either it gates, or it changes the input format so a gating rule can handle it, or it doesn't exist. (#139 revisits how a gating heuristic should *identify itself* — that is a different question from whether it gates.)

## 2026-08-12: Don't patch a status-ownership bug with an orchestrator-side repair loop

**Tried:** #148 rewinds a task's status from `checking` to `needs-check` when a worker returns, because `subagent-return.py:434` accepts only `needs-check` from a worker and re-reads the file at return time. Rather than wait for the fix, the orchestrator ran a watcher that reset the field every fifteen seconds.
**What broke:** It converted a silent state bug into a visible fight between two agents that were each behaving correctly. T-007's worker grepped `subagent-return.py` and `_lib.py`, checked for symlinks and duplicate files, and reported that something outside its own tool calls was advancing the field between rounds. It was right, and it spent a meaningful share of its turn getting there.
**Why we backed out:** The workaround is invisible to the agent it fights, so the cost lands on whoever is trying to behave correctly.
**Don't suggest:** repairing task state on a timer, or any orchestrator-side loop that contests a field another agent is required to write. Fix the ownership conflict, or tell the worker its handoff already landed.

## 2026-08-12: Don't guard the one crash site a task file happened to name

**Tried:** `test_codex_courier.py` aborts under a `None` outcome, which makes C-5's mutation arm unreliable because cases below the abort never run. T-008 was told to guard line 403 and did. T-009 was told to guard 393 and did.
**What broke:** The suite still aborts, now at 505, with 507, 795, 797 and 809 behind it. T-008's checker found the run dying identically with and without the fix; T-009's found it reaching 18 checks before dying anyway. Three checkers across three tasks have now lost time to the same file.
**Why we backed out:** Naming a site treats a file-wide pattern as a point defect, and each fix looks complete until the next mutation finds the next one.
**Don't suggest:** guarding a single named dereference. Sweep the file for the pattern, and say in the task that the guard is exempt from the mutation arm because it repairs the instrument rather than adding behavior.
