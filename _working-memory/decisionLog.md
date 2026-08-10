# Decision Log

Append-only; newest entry on top. Don't edit past entries; supersede them with a new one.

Each entry follows this shape:

```markdown
## 2026-04-19: Short title

**Source:** the commit, PR, or discussion it came from (optional for hand-written entries)

**Context:** Why this came up.
**Decision:** What was decided.
**Alternatives considered:** What was rejected, and why.
```

## 2026-08-10: What The Vendor Must Know Lives In The Brief, And What A Field Means Lives In The Schema

**Source:** #113 and #115, fixed together

**Context:** Two live failures with one cause. A crossing was rejected twice for returning `checker: checker-judgment` and a guessed model, because the lane validates identity on receipt and nothing ever told the far side what to send; the workaround that then worked five times for five was prose someone typed into a dispatch. Separately, a `pass` came back carrying twelve `blocker` findings, every one affirming that something was correct, because `severity` had no enum, no stated relation to `verdict`, and no definition the vendor could read.

**Decision:** Split the two by delivery channel. Severity semantics go in `verdict.schema.json`, which both lanes already hand the vendor as the output schema (`codex exec --output-schema`, `claude --json-schema`) and which in-family checkers validate against, so one edit reaches every writer of a verdict. Identity can't go there, since `vendor` and `model` are lane-specific and the schema is generic, so `compose-brief.py` takes `--vendor`/`--model` and appends a `## Verdict contract` section carrying the whole instruction the courier used to retype: nine fields, four identity values to echo, null metrics, fail-needs-a-finding, and what severity means. Both flags or neither, so the existing golden briefs stay a real regression guard.

**The severity ruling:** `blocker`, `major`, `minor`, `info`, by defect impact. A finding recording a satisfied clause is `info`. The mechanism behind #115 was almost certainly the brief itself: it quotes clause text verbatim, a clause reads `**severity**: blocker`, and the roles ask for one finding per cited clause including on a pass, so the clause's severity became the label for every finding about it. A `pass` now carries only `info` and `minor`, enforced in `validate-verdict.py` as its third semantic rule, since a `blocker` or `major` asserts a defect and contradicts a verdict saying every clause is satisfied.

**Verified live** rather than by fixture alone. One codex-lane crossing with a deliberately blocker-severity clause that the artifact satisfies: `checker: checker-courier` and `model: gpt-5.6-terra` correct on the first attempt, the satisfied clause returned `info`, validator clean, 17,761 input tokens and 9 seconds.

**Alternatives considered:** Stamping identity onto the response after it returns, which #113 called the stronger option. Rejected because it makes the courier the author of a verdict it is supposed to transcribe, which is the separation the org chart exists to keep, and because it fixes the symptom while leaving the vendor uninformed. A lane table inside `compose-brief.py` (rejected—duplicates the pin the adapters already own, and single-sourcing vendor config is #35). Enforcing only `pass` + `blocker`, which is all #115's acceptance criteria demanded (rejected—`major` asserts a real defect too, and a rule with an unexplained hole is a rule nobody trusts).

## 2026-08-10: Teach The Frontmatter Parser Block Scalars Rather Than Take A YAML Dependency

**Source:** #109; commit d05d6ca

**Context:** `_lib.parse_frontmatter` set a block-scalar key to `""` and skipped its indented body, commented "we don't need its body." For `check_method` that body is the entire contract between a task and its checker, and `>-` is the natural spelling for a value running past a thousand characters. The #97 run's first T-001 cited eleven clauses and parsed to `''`. The file read correctly in an editor, `clauses:` parsed normally, and only a hand inspection before dispatch caught it.

**Decision:** Parse the body rather than refuse the file, which the issue offered as the equally acceptable alternative. `|` and `>` with any chomping indicator now parse; unsupported edges (explicit indentation indicators like `|2`, anchors, nesting) are named in the docstring instead of silently mishandled. The second half is a refusal: `dispatch-guard` blocks a task citing clauses with an empty `check_method`, ahead of the worker/checker split, because a checker with nothing to run reports a pass.

**How it was verified without a dependency:** Ruby's psych. pyyaml isn't installed and the stdlib-only rule covers the tests as much as the hooks, so thirteen fixtures were diffed against `ruby -ryaml`, which ships with macOS. All thirteen agree, including `|+`/`>+` chomping, blank-line runs, and more-indented folded lines. The harness stayed in the scratchpad; the committed tests assert the values it confirmed.

**Alternatives considered:** Adding pyyaml (rejected—the hooks are stdlib-only by design, and the issue ruled it out). Refusing a block scalar loudly instead of parsing it (rejected—the task template's own `check_method` example uses `>-`, so refusal would break every task written the documented way). Supporting only the three forms the issue names (rejected—`|-` and `>+` would keep the identical silent-empty bug under a different spelling). Fixing `compose-brief.py` and `check-provenance.py`'s own parsers alongside (deferred—neither reads `check_method`, so nothing is broken today).

**Still open:** the double-quoted-scalar escaping hazard the issue names as a separate defect has no issue filed.

## 2026-08-10: The Codex To Claude Lane Needs Two Things, And Auth Was The Smaller One

**Source:** #92; commits 0353930 and aeb8b09; the first live crossing, 2026-08-10

**Context:** Every courier crossing from a Codex host on macOS came back `blocked` with `Not logged in · Please run /login`, and the CLI was logged in. That read as a credential problem for months, and it was half of one.

**Decision:** Document both requirements, because each one hides behind the other. A headless token from `claude setup-token`, supplied as `CLAUDE_CODE_OAUTH_TOKEN`, clears the login keychain a sandboxed Codex session cannot open. `sandbox_workspace_write.network_access = true` in the Codex TOML gives the request somewhere to go. Supply only the token and the failure changes shape rather than clearing: the credential resolves, and the call then dies silent at the 120-second bound. `curl https://api.anthropic.com/v1/messages` fails to resolve in 1.3ms inside the sandbox, and Claude Code retries transport failures rather than erroring out, so a blackholed connection looks exactly like a hang. Both together produced the project's first non-blocked crossing: verdict pass, schema-valid, exit 0, 13 seconds, two cents.

**What it cost to find:** three separate auth-shaped error messages that each meant something else. A stale refresh token 401 on the Claude host while `codex login status` reported a healthy login; the keychain in the sandbox; and finally DNS. The courier's own timeout branch now recognizes the third: silence on both streams for the whole wall clock is the signature of a sandbox with no egress, so it names the curl check and the config key instead of reporting elapsed time.

**Alternatives considered:** Shipping the token as *the* fix, which the first commit did. Rejected once the live run showed it trades an error that names its cause for one that says nothing at all, which is nearly as costly as being wrong. Also rejected: treating the whole thing as a Codex sandbox limitation and declaring the reciprocal lane unviable, which the working config disproves.

## 2026-08-10: An Exhausted Courier Lane Substitutes Nothing

**Source:** #97; commit 1687dc4, merged as 20e93f0

**Context:** Four places disagreed about what happens when the lane goes down. The routing table named the in-family checker as the fallback, the state map said no substitution was needed, `docs/installing.md` said the Guild falls back, and `dispatch-guard`'s message advised a re-dispatch in the same breath as saying the denial costs nothing.

**Decision:** Nothing is substituted, and the reason is timing. A courier only goes out after the checker of record has returned, so by the time the lane is denied there is nothing left to re-run. Worse, a re-run landing at the lane-suffixed stem would let #34 count a same-host check as cross-vendor agreement, which is the one way to corrupt that sample without anyone noticing. The state map entry for `exhausted/<lane>` owns the rule; the guard message quotes it rather than paraphrasing.

**Alternatives considered:** Keeping the substitution and rewriting the state map to match. Rejected on the #34 contamination alone. The Claude smoke run's D2 had already followed the state map and written down why it was ignoring the guard's advice, so the working behavior was already the correct one.

## 2026-08-02: v0.5.1 Shipped On Two Live Smoke Runs, With Its Failures Written Down

**Source:** both host matrices run live; issues #88–#102; PR #93; commits 861eca9 and 1aaa4c5; tag v0.5.1

**Context:** SMOKE.md had been accurate about what the gates *say* since #78 and had never actually been executed. The milestone required both matrices to pass, so the tag hung on running them rather than reading them.

**Decision:** Run both, correct whatever they contradicted, and tag with the failures documented rather than hidden. C4 is now marked Claude-only: the ladder's rungs are Claude model names, Codex has nothing to put behind them, and an escalated task there wedges between the gate refusing the stale tier and the host refusing the new one (#88). The milestone description was rewritten three times before it described what shipped instead of what was intended.

**What the runs bought:** ten filed issues, one of which mattered immediately. The Claude package had been shipping six agents against Codex's nine since v0.5.0, missing `checker-courier`, so the dual-check regime the contract calls mandatory had never run for a single plugin user (#94). Fixed, and verified with a real crossing rather than a passing build: `T-001-opus-r0-codex.json`, vendor `openai`, model `gpt-5.6-terra`, verdict pass. First genuine cross-vendor second opinion the project has produced.

**Alternatives considered:** Filing the four small convention divergences separately was rejected for #101, which puts stem, dispute frontmatter, and timestamp behind the return gate — fix them one at a time and the next four appear. Re-milestoning #34 out of v0.6.0 was considered and rejected: the issue body and the milestone description both already name it the entry gate, so the ordering was written down and only its blockers were invisible. Recording the blockers was the smaller correct fix.

## 2026-08-01: One Codex Agent Name Per Dispatch, And No Re-Tasking Through `followup_task`

**Source:** issue #77; PR #80, verified live in a Codex session the same day

**Context:** Codex treats `task_name` as a unique agent name inside a session tree and rejects one already in use. Carrying one id per task (#71) therefore made the second dispatch for a task collide, and the obvious workaround `t_001_checker` was blocked because `bare_id` only parsed `t_001`. With both routes closed the model reached the running agent through `collaborationfollowup_task`, which no matcher covered. Four such calls ran in one session, one of them from inside a subagent. That call names no agent type, carries an encrypted message, and identifies its target only by agent path, so none of the dispatch checks can run against it, while `SubagentStop` still fires and the return gate judges whatever comes back. A whole job completed with `dispatch-guard` never applying.

**Decision:** Make the wire name unique per dispatch rather than per task (`t_001_r0_worker`, `t_001_r0_checker`, `con_audit_r0`), with `bare_id` stripping any trailing discriminator back to the canonical `T-001` so task files, verdict stems, and the dispatch log are untouched. The discriminator is free-form on purpose. Gate `followup_task` in the Codex matcher and refuse it outright whenever any segment of its target parses as a guild id, since refusal is the only move available when there is nothing left to check. The block names a spare `task_name` so it teaches rather than merely stops. Both halves ship together: closing the ungated path without fixing the collision would only move the pressure elsewhere.

**Alternatives considered:** Constraining the discriminator to a fixed role vocabulary (rejected—a too-tight shape is exactly what pushed the model off `spawn_agent`, and a re-dispatch repeating both role and retry count still needs room to name itself); recovering a Task-ID from the followup itself and checking it like a spawn (rejected—the target is an agent path and the message is encrypted, so there is no id to recover); allowing a followup at a guild agent whose task is in a legal state (rejected—state is the only thing that could be checked, and tier, executor identity, and the CON-audit precondition would all go unverified).

## 2026-07-31: The Guild Never Takes Work On Its Own Gates In This Repo

**Source:** #68 and #77 routing decisions

**Context:** Both issues were candidates for a dogfooded guild run, and both change files under `.agent-guild/hooks/`. This repo registers its gates from the working tree (`.claude/settings.json` points `PreToolUse` at `.agent-guild/hooks/dispatch-guard.py`), so a worker editing them is rewriting the machinery while the job depends on it.
**Decision:** Route any change to `.agent-guild/hooks/*.py` directly, never through a guild job. Everything outside `hooks/` stays eligible, which is why #78's docs sweep goes to the guild and #77's gate work does not. The failure this avoids is not hypothetical: `_lib` is imported by all four gates, so one bad edit takes down dispatching, the write guard, the return gate, and the stop gate at once, including the gate that would otherwise report the job stuck.
**Alternatives considered:** Splitting an issue so only its non-gate files go to the guild (rejected—it fragments one coherent change across two executors for no gain); running the job with `PAUSED` set (rejected—it disables the verification the job exists to exercise); accepting the risk because the suite would catch it (rejected—the suite runs after the edit, and the job needs the gates during it). Note this constraint belongs to this repo alone: a project consuming the kit never has its own gates as the artifact under change.

## 2026-07-31: The Codex Return Path Reads The Parent And Transcribes The Verdict

**Source:** issues #68 and #71; PRs #75 and #76

**Context:** The return gate recovered a task id from the child's transcript, where it has never existed, because the id rides in the parent's `spawn_agent` arguments and the child's dispatch message is encrypted. Against a live payload the gate resolved a worker's return as `CON-audit`, found no task file, and failed open. Separately, in-family checkers run `sandbox_mode: read-only` on Codex and could not write the verdict JSON the gate demanded, while `checker-courier` was the only agent given a Codex protocol at all.
**Decision:** Prefer the parent's `transcript_path` and fall back to the child only when the parent path is unusable. Let read-only in-family checkers return the verdict inline under an `AGENT_GUILD_VERDICT` marker, gate-validated for schema plus `task_id` and `checker` identity, then persisted unchanged by the parent. The orchestrator's write is a transcription and it must not edit the object: editing a verdict it commissioned would make it the author of its own check.
**Alternatives considered:** Correlating returns by `agent_id` instead of by transcript (rejected—the parent transcript records no mapping from a spawn call to the resulting agent id); leaving identity checks to `validate-verdict.py` (rejected—the validator knows a verdict's shape, not which task it belongs to, and a verdict persisted against the wrong stem is worse than one refused); documenting the read-only gap rather than closing it (rejected once #75 made the gate reachable, since checkers would have started deadlocking).

## 2026-07-31: The Codex Dispatch Id Rides In `task_name`, Lowercased And Underscored

**Source:** issue #71; PRs #72 and #74

**Context:** Codex encrypts a dispatch's `message` before any hook sees it, so `Task-ID: T-NNN` in the prompt is unreadable there. Three defects stacked underneath: the registered matcher never matched the tool name Codex reports (`collaborationspawn_agent`), `_bare_tool_name` rejected that name, and the id was unreadable regardless. Fixing the matcher alone would have taken the host from unenforced to unusable.
**Decision:** Carry the id in `task_name`, the one dispatcher-set field readable at both the dispatch payload and the transcript. Codex validates that field as an agent name and rejects anything outside `[a-z0-9_]`, so the wire form is `t_001` and `con_audit`; `_lib.bare_id` canonicalizes back to `T-001` so task filenames, verdict stems, and the dispatch log are unchanged. `dispatch-guard` reads the structured field first and falls back to the prompt line, leaving the Claude host untouched.
**Alternatives considered:** `tool_use_id`/`call_id` (rejected—host-generated, so they can correlate an id but never carry one); keeping the prompt line and accepting an unenforced Codex host (rejected—that is what milestone 7 shipped); renaming the canonical id repo-wide to fit the charset (rejected—the wire form is a host detail and everything downstream already keys on `T-NNN`).

## 2026-07-27: One Install Guide And One Smoke Lifecycle Serve Both Hosts

**Source:** issue #55

**Context:** First-Class Codex added real platform setup differences, but keeping Claude and Codex guides or lifecycle drills side by side would make shared Guild behavior drift and force users to reconcile near-copies.
**Decision:** Make `docs/installing.md` the one user installation source for Claude plugin, Codex CLI/desktop plugin, repo-local Codex IDE, cross-vendor credentials, hook trust, and duplicate-registration safety. Root and packaged READMEs point to it; `docs/building.md` remains a maintainer build reference. Keep one host-neutral `SMOKE.md` lifecycle with a small invocation/lane map and thin, independently checkable fresh-project launch drills for each supported surface.
**Alternatives considered:** Separate Claude and Codex install guides (rejected—the shared init and lifecycle would be duplicated); keeping user setup in the build reference (rejected—it mixes maintainer and adopter paths); cloning the full smoke lifecycle per host (rejected—only dispatch representation, skill syntax, hook trust, and courier lane differ).

## 2026-07-26: One Generated Codex Package Is The Git Marketplace Surface

**Source:** issue #53

**Context:** Codex had a complete generated package, but it lived only in ignored `dist/` with a committed hash. A Git marketplace needs a real package path inside the repository, and hand-maintained marketplace or package copies would recreate the parallel implementation surface the shared core removed.
**Decision:** Generate and commit the Codex package at `plugins/agent-guild/`, generate `.agents/plugins/marketplace.json` beside the existing Claude marketplace, and derive both marketplace views from `scripts/plugin-src/plugin.json` plus one `scripts/plugin-src/marketplace.json`. The default build syncs both package trees and marketplaces; `--check` rebuilds and diffs all four generated release views. Explicit `dist/` builds remain scratch/CI artifacts. The old Codex hash lock retires because the committed generated tree is now the stronger drift boundary.
**Alternatives considered:** Keep only the hash and publish an attached archive (rejected—the Git marketplace cannot resolve ignored content); author the Codex package or marketplace by hand (rejected—it creates a second implementation and metadata drift); publish from a separate repository (rejected—it creates a parallel release process).

## 2026-07-26: Claude Marketplace Identity Is `agent-guild@kendrick`

**Source:** issue #48; isolated Claude Code 2.1.212 marketplace experiment

**Context:** The plugin and marketplace were both named `agent-guild`, producing the typo-like qualified id `agent-guild@agent-guild`. Renaming the marketplace also creates a migration hazard if the old source remains configured.
**Decision:** Keep the plugin name `agent-guild`, rename only the Claude marketplace to `kendrick`, and use the qualified id `agent-guild@kendrick` in every install, disable, and uninstall surface. Tell existing users to uninstall the old qualified plugin and remove the old marketplace before adding the renamed source. An isolated CLI run proved both marketplace names, cache trees, and qualified plugins can coexist and both are enabled in a neutral project, which would double-register every hook.
**Alternatives considered:** Leaving the redundant identity (rejected—it obscures publisher ownership); relying on the unqualified plugin name (rejected—it is ambiguous once both marketplace sources coexist); asking users only to add the renamed marketplace (rejected—the stale installed copy stays independently enabled).

## 2026-07-26: Reciprocal couriers share one protocol and keep host commands in adapters

**Source:** issue #54

**Context:** Codex-hosted jobs needed an independent Claude second opinion, but the courier core still embedded the Claude-hosted `codex exec` route and Codex project agents are intentionally read-only.
**Decision:** Keep evidence, validation, ledger, quota, and second-opinion semantics in one host-neutral `checker-courier` role; put the exact Codex and Claude commands in thin agent adapter suffixes. The Codex lane invokes a stdlib-only `claude-courier.py` boundary that pins `claude-haiku-4-5-20251001`, isolates the CLI with no tools or MCP servers, adapts only the schema's top-level `$schema`, requires and independently validates `structured_output`, aggregates retry usage, classifies structured 429s, and enforces a wall-clock bound. A read-only Codex courier returns the marked outcome; the return gate validates it before the parent persists the `-claude` verdict and ledger, or appends the quota ledger line before creating `exhausted/claude`. The unsuffixed in-family verdict remains authoritative.
**Alternatives considered:** Duplicating the full courier procedure in the Codex adapter (rejected—it recreates the parallel implementation surface); granting the Codex courier workspace write (rejected—it weakens the read-only verifier boundary); trusting Claude's exit code or `--json-schema` alone (rejected—controlled malformed output can exit zero without `structured_output`); blocking the whole task when the external lane is unavailable (rejected—the second opinion is comparison data, not the verdict of record).

## 2026-07-26: Codex lifecycle adapters reuse the four shared gates

**Source:** issue #56

**Context:** Claude's four enforcement gates already held the Guild policy, but Codex names lifecycle fields and structured edits differently, discovers plugin and project hooks at different scopes, and requires explicit user trust for hook definitions.
**Decision:** Keep policy only in the existing four stdlib Python gates and translate Codex command-hook JSON through one `codex-hook-adapter.py`. Preserve exit code 2 plus stderr as the blocking/continuation protocol; map `spawn_agent`, multi-target `apply_patch`, child transcript paths, and subagent identity into the shared contract. Generate plugin and repo-local hook configs from one inventory. Plugin setup relies only on plugin hooks; repo-local bootstrap owns the shared scripts and merges only handler commands carrying the Guild adapter signature into `.codex/hooks.json`, preserving unrelated configuration. Setup always directs the user to review and explicitly trust definitions in `/hooks`; installation never claims trust.
**Alternatives considered:** Forking all four gates for Codex (rejected—the policies would drift); reimplementing policy inside a stateful adapter (rejected—the current Codex payload supplies subagent identity directly); overwriting `.codex/hooks.json` (rejected—it is project-owned shared configuration); installing project hooks alongside plugin hooks (rejected—every gate would fire twice); implying installation automatically trusted hooks (rejected—Codex intentionally keeps that authority with the user).

## 2026-07-26: One workflow core and installer engine serve both hosts

**Source:** issue #57

**Context:** Claude already carried the complete lifecycle and working-memory workflows, while the staged Codex package exposed only a subset and its separate installer guide duplicated setup behavior. Codex also has two valid skill scopes with different invocation names: plugin skills are namespaced, while repo-local skills are not.
**Decision:** Author all twelve workflow bodies only under `guild-core/workflows/`, render host frontmatter and the thin `init` command suffix from adapters, and ship one stdlib-only `install-project.py` engine in both packages. Claude plugin init preserves project settings and installs the payload plus bounded guidance. Codex plugin init installs the payload, roster, and bounded guidance while relying on plugin skills; repo-local Codex adds `--project-skills` to install `.agents/skills/`. The exact entrypoints are `/agent-guild:job`, `$agent-guild:job`, and `$job`, respectively.
**Alternatives considered:** Copying Claude skill bodies into a Codex source tree (rejected—it creates a second implementation); maintaining host-specific installation guides or engines (rejected—their safety and ownership rules would drift); always installing repo-local Codex skills (rejected—an installed plugin would expose duplicate skill names); translating Codex skills into slash commands (rejected—Codex's documented explicit syntax is `$skill-name`).

## 2026-07-26: Codex verifiers return content across a read-only host boundary

**Source:** issue #50

**Context:** The shared Guild checker and auditor roles describe writing their own state files, while Codex can enforce a stronger project-agent sandbox and the initializer must coexist with project and global user configuration.
**Decision:** Generate the complete nine-agent project roster as standalone `.codex/agents/*.toml` from the shared role bodies plus Codex adapter metadata. Auditor and checker agents run `read-only`; their host instructions override shared write steps and require returning the intended path and complete proposed content to the parent orchestrator for persistence. The initializer updates only the generated project roster and one bounded `AGENTS.md` section, preserves unrelated content, never reads or writes global Codex configuration, rejects redirected `.codex` paths, and fails closed on malformed ownership markers.
**Alternatives considered:** Granting checkers workspace write so shared prompts could remain literal (rejected—it weakens independent verification); forking Codex-specific role prose (rejected—it recreates the duplicate implementation surface); replacing all of `AGENTS.md` or `.codex/` (rejected—it would destroy project-owned configuration); installing into global `$CODEX_HOME` (rejected—Guild behavior is project-scoped).

## 2026-07-26: CI verifies and packages both hosts without committing output

**Source:** maintainer request during PR #60

**Context:** A shared-core build is only dependable if each host has an unambiguous command and pull requests catch stale generated state without creating another automated writer.
**Decision:** Expose explicit `claude`, `codex`, and `all` build targets; document their sources, outputs, sync command, and checks in one canonical guide. GitHub Actions runs the full suite and strict Claude validator, rejects generated drift, proves a fresh Claude build is identical to the established published package, and uploads both packages—including their hidden manifests—as an ephemeral artifact. It never commits generated files.
**Alternatives considered:** Keeping the target split implicit in maintainer-only commands (rejected—easy to build or edit the wrong tree); having CI auto-commit rebuilds (rejected—it obscures source/output mistakes and introduces a privileged writer); uploading only Codex (rejected—building both from the same revision is the clearest evidence that the shared-core contract holds).

## 2026-07-26: Host packages are rendered artifacts, not parallel source trees

**Source:** maintainer review of PR #60; supersedes the issue #51 decision immediately below

**Context:** The first #51 implementation called the dogfooded Claude tree a shared core and committed 47 Codex package files beside it; 45 were byte-identical copies, so the repository gained exactly the parallel content surface First-Class Codex was meant to avoid.
**Decision:** Author shared role behavior and workflow bodies/assets only under `guild-core/`; keep host-bound frontmatter and manifest metadata under `scripts/plugin-src/adapters/`; generate the dogfooded Claude wrappers and both packages from those inputs. Preserve the existing published Claude tree for marketplace compatibility, but stage Codex under ignored `dist/` and commit only its compact content lock until #53 defines the publishing surface. A check rejects edits to generated dogfood, stale Claude output, stale Codex content, and a hand-edited staged artifact.
**Alternatives considered:** Treating committed generated copies as sufficiently DRY (rejected—the edit path was singular but the repository surface was not); keeping `.claude/` as the semantic core (rejected—it mixed shared behavior with Claude representation); committing the incomplete Codex staging tree before #50, #56, and #57 supply its actual adapters (rejected—it looked like a second implementation and exposed Claude wrappers as Codex content).

## 2026-07-26: Both host distributions are generated from the dogfooded source graph

**Source:** issue #51

**Context:** First-Class Codex needs a package target without creating a second Agent Guild implementation or turning the repo's live Claude setup into another generated copy developers cannot edit directly.
**Decision:** Keep the dogfooded `.claude/` and `.agent-guild/` trees as the canonical shared source graph. `scripts/build-plugin.py` now generates both `plugin/` and `codex-plugin/` from that graph and one authored version. Schemas, scripts, templates, scenario assets, workflow bodies, and role definitions are single-sourced; target builders may change only platform representation, currently Claude invocation namespacing and Codex skill frontmatter/manifest metadata. `--check` rebuilds and diffs both committed targets, so hand edits fail regardless of host.
**Alternatives considered:** Maintaining a parallel Codex source tree (rejected—the drift #51 exists to prevent); moving every live source into a third abstract directory immediately (rejected—it would make both dogfooded host trees generated artifacts before the later agent, hook, and skill adapter issues define their stable representations).

## 2026-07-26: First-Class Codex targets v0.5.1

**Source:** maintainer direction during issue #52

**Context:** The First-Class Codex roadmap was filed under a speculative v0.9.0 milestone after v0.5.0 shipped, but the release target changed before implementation began.
**Decision:** Ship the First-Class Codex arc as v0.5.1, not v0.9.0. Work commits still leave the version untouched; the one mechanical release commit carries the 0.5.1 bump when the milestone wraps.
**Alternatives considered:** Keeping v0.9.0 because the issue bodies and milestone already named it (rejected—the maintainer explicitly changed the release target, and tracking metadata does not outrank the release decision).

## 2026-07-26: The reciprocal Claude lane requires a schema adapter and envelope validation

**Source:** issue #52, live Claude Code 2.1.212 probes

**Context:** The Codex-hosted second-opinion courier needs a concrete Claude CLI contract, including its read-only boundary, structured output, malformed output, authentication failures, and quota signals.
**Decision:** Pin `claude-haiku-4-5-20251001` and invoke Claude in safe mode with no tools, no MCP servers, plan permissions, no persistence, closed stdin, and all evidence inline. Generate the Claude `--json-schema` argument by removing only the canonical verdict schema's top-level `$schema` declaration; require and independently validate `structured_output` because malformed provider output can exit zero without it. Treat `api_error_status: 429` as quota and impose a courier-owned wall-clock bound because the CLI otherwise retries silently up to 11 attempts.
**Alternatives considered:** Passing the canonical Draft 2020-12 schema byte-for-byte (rejected—Claude CLI rejects its `$schema` URI before a model call); trusting exit code zero (rejected—a controlled malformed response exited zero with no `structured_output`); relying on the CLI's retry policy (rejected—it is silent, long, and ignored the tested retry-limit override).

## 2026-07-24: External dispatch costs ~100x the in-family marginal

**Source:** issue #33, `docs/handoff-cost.md`, measured over six courier dispatches

**Context:** The multi-provider roadmap kept deferring to an economic number nobody had measured.
**Decision:** Measured, not decided: serialized context for an external check runs 49.8x to 202.9x the orchestrator's in-family marginal (mean 99x, aggregate 102.5x)—99% of what a vendor receives is overhead the in-family path never pays, because an in-family checker reads artifacts from disk while a vendor must receive everything inline. Denominated in tokens; the lane reports no per-call dollars. The v0.7.0 write-granted-lane gate becomes numeric: ratio ≥ 100, with extrapolation assumptions labeled (worker briefs run larger, iteration multiplies calls, blind-diff retries re-pay full context). Cross-family checking is affordable at these rates; cross-family working re-pays the multiplier every loop.
**Alternatives considered:** Waiting for worker-lane data before setting a gate (rejected—#36 needs the constraint now, and check-lane data plus labeled assumptions beats a vibe).

## 2026-07-24: The cross-family lane ships as checker-courier under an auto-dual regime

**Source:** issue #8 (commit 2be781f), amended by #44 (269a249)

**Context:** An executor and checker from the same model family share correlated blind spots; breaking that correlation is the entire multi-provider premise.
**Decision:** `checker-courier` — a haiku courier relaying judgment checks to an external vendor CLI over a lane (codex today, `gpt-5.6-terra` far side), producing a SECOND-OPINION verdict at a lane-suffixed stem that never decides a task. Named lane-neutral from birth so #11 adds lanes rather than renaming an agent. Until #34 closes, every task reaching `checking` also gets a courier crossing, so the evaluation fills through ordinary work. The compose step inlines everything the vendor needs (brief, artifacts, clause-referenced evidence); the vendor fetches and executes nothing.
**Alternatives considered:** A codex-specific `checker-codex` (rejected per the standing #8 comment—renaming later is churn); making the second opinion able to fail a task (rejected—a second opinion is not a second gate).

## 2026-07-24: Release cadence is minor-only while the user base is small

**Source:** docs/publishing.md (commits f13e7c5, 3f43098)

**Context:** Per-job patch releases (0.3.2 through 0.4.1) were becoming the de facto rule without anyone deciding they should be.
**Decision:** Phase-dependent, not doctrine. In dev mode with barely an installed base, work accumulates across jobs and ships as one 0.X.0 cut at milestone close. Patch releases stay first-class for the cases that warrant them (security fixes, broken installs), and their importance grows with the user base.
**Alternatives considered:** Ruling patch releases out entirely (rejected—sometimes crucial); keeping per-job releases (rejected—ceremony without readers).

## 2026-07-24: Releases are two-commit, tagged per bump, with generated changelogs

**Source:** issue #42 (commit 952b82e), the tag-per-bump amendment (3c113c8), first live runs at v0.3.6 and v0.4.0

**Context:** Releases left no reader-facing record, nothing enforced remembering a changelog, and fix-level versions had no tags — half a record.
**Decision:** `make-changelog.py` harvests commits between plugin.json version-bump boundaries into unwrapped conventional sections (group headings, bold scope leads, linked hashes); it never invents prose. Enforcement is mechanical: `build-plugin.py --check` fails a bumped-but-sectionless version, and `--notes` refuses to cut a noteless release. The ritual is two-commit — work commits never touch the version; one mechanical release commit carries bump + in-flight section + rebuild — and every release commit gets tagged with a GitHub release, patch bumps included; a milestone close is just the bump that closes it. Kit-payload jobs leave the version untouched; the release is the maintainer ritual at wrap.
**Alternatives considered:** git-cliff/conventional-changelog tooling (rejected for now — tags-as-boundaries would add a forgettable parallel discipline; recorded as the exit ramp on #42 if the format ever needs to grow); milestone-only tags (rejected — the version field and changelog exist per bump, so taglessness left the record incomplete).

## 2026-07-24: Verdicts are canonical JSON; blocked absorbs ERROR

**Source:** issue #29 (commit 1594cf8)

**Context:** A second checker family (#8) needs a contract to write against; Markdown verdicts could only be validated by parsing conventions that drift.
**Decision:** JSON is the verdict of record, schema-validated, with Markdown rendered from it; `subagent-return` mechanically rejects nonconforming checker returns; a fail requires evidence-backed findings. The enum is `pass|fail|blocked`, with `blocked` carrying the old ERROR semantics (couldn't run, doesn't count against the worker) so one vocabulary covers broken checks and vendor quota alike. The schema stays structured-output-safe (no conditionals); semantic rules live in the validator. The migration dogfooded itself mid-run — the job's own later verdicts were gate-validated JSON.
**Alternatives considered:** Adding `error` to the enum (rejected — two near-synonymous states); keeping ERROR outside the schema (rejected — broken checks would produce forever-nonconforming files).

## 2026-07-24: Isolation strategy — patch-return default, worktrees only for workspace-write lanes

**Source:** issue #32, closed with this decision

**Context:** Claude Code supports `isolation: worktree` for subagents; #36 (per-lane write mode) needed a fed decision, and the question of native-worker isolation was open.
**Decision:** Native guild workers get no worktrees — structurally blocked anyway, since the message bus is the gitignored `.agent-guild/state/` and worktrees materialize tracked files only, so a worktree'd worker can't see its own task file. External lanes default to patch-return (vendor emits a diff, the haiku courier applies it — the apply step is mechanically cheap; the real price is the vendor can't iterate against its own edits). Workspace-write is a measured per-lane exception that arrives worktree-required, because a write-granted foreign process is an untrusted writer that could otherwise reach the unrecoverable state bus. No task-scoped claims layer until a real collision happens.
**Alternatives considered:** Worktrees everywhere (rejected — merge-back cost plus the state-bus incompatibility); "writes bypass hooks" as the justification (rejected as dishonest — native workers can Bash-write past the hooks too; the real differentials are writer trust and bus exposure).

## 2026-07-24: Open-weight ships as lane config, never a privileged path; OpenCode rejected as universal shim

**Source:** issue #31, closed with this decision

**Context:** Two filed paths for open-weight models: pure-function tier zero (direct Ollama calls for mechanical subtasks) vs a harness-wrapped courier via OpenCode, with the side question of OpenCode replacing all vendor shims.
**Decision:** The kit ships no open-weight slot; vendors are manifest lane recipes (the v0.6.0 substrate), and open-weight joins that way when the #34 evaluation justifies it. OpenCode is rejected as the forced universal shim — each vendor keeps a direct recipe — but adopted as this maintainer's personal lane recipe for open-weight, which the config-not-architecture design makes possible without imposing it on other guild users. Tier zero stays unbuilt for lack of measured need.
**Alternatives considered:** OpenCode as the one shim for all vendors (rejected — a dependency on one project's abstraction before the first direct lane even ran); building tier zero now (rejected — no evidence of need).

## 2026-07-23: Ship the guild as a public Claude Code plugin (v0.3.1)

**Source:** commits b294bf7, e7058df, edba55b; epic #19; issues #24, #25

**Context:** Plugin packaging was deferred since the kit began (a standing open question), the blocker being that a plugin can't ship an always-on `CLAUDE.md`.
**Decision:** Published. The repo is its own marketplace (`.claude-plugin/marketplace.json` sources `./plugin`); `scripts/build-plugin.py` assembles `plugin/` from in-repo sources; `/agent-guild:init` finishes each install by copying the per-project payload (contract, scripts, templates) and adding the `@.agent-guild/CLAUDE.md` import; a SessionStart nudge catches partial installs. Verified end to end by SMOKE Part C in a real project (add, install, init, and the plugin's own dispatch-guard denying an untagged dispatch). Tagged v0.3.1, not v0.3.0—see the hooks-load antipattern in [[antipatterns]].
**Alternatives considered:** A SessionStart hook injecting the contract (rejected—`additionalContext` persistence is undocumented, so the one-line import is the reliable path).

## 2026-07-23: Version the roadmap with v0.X.0 milestones, checker lane first

**Source:** the multi-provider planning session; the (now retired) backlog.md; GitHub milestones v0.3.1–v0.8.0

**Context:** The repo had no versions and a loose multi-provider backlog that overlapped the existing codex-lane issues.
**Decision:** Six milestones (v0.3.1 through v0.8.0) tracking `plugin.json`, git-tagged at close. The multi-provider arc ships the cross-family **checker** lane before any external worker lane, gated on a 10-task dual-check evaluation that decides whether external workers get built at all. External vendors are always parallel lanes, never rungs on the Claude-only escalation ladder.
**Alternatives considered:** The existing epic #9's worker-first order (rejected—the checker is read-only, has no write-guard collision surface, is cheaper to build, and produces the go/no-go data the worker lanes depend on).

## 2026-07-22: `/job` flows into `/constitution` instead of stopping at a handoff

**Source:** commit 1c0dfee; issue #26

**Context:** Intake ended by pointing the user at `/constitution`, which read as the guild stalling—especially in auto mode, where the stop gate can't help because intake is pre-Phase-0 and no task exists yet.
**Decision:** Step 5 of the `job` skill invokes `/constitution` in the same turn once `check-provenance.py` passes. Every failure path still stops with an honest message and never invokes `/constitution`; the collapsed interview's confirm-and-adjust step stays the user's touchpoint.
**Alternatives considered:** Leaving the handoff and documenting it (rejected—the stall was the whole complaint).

## 2026-07-14: Scope orchestrator gates to the main session via `agent_id`

**Source:** SMOKE.md B2 run in a copied-in kit; confirmed against the CC hooks docs.

**Context:** The kit assumed "parent hooks do not fire for tool calls made inside subagents," so `orchestrator-write-guard` treated any trip as the orchestrator overreaching. False on CC 2.1.x — PreToolUse fires inside subagents too, so the guard was blocking workers from writing their own deliverables. The guild only appeared to work because workers fell back to `Bash`, which the guard's `Write|Edit|MultiEdit` matcher never covered.
**Decision:** Scope main-session-only gates by the `agent_id` Claude Code stamps on subagent hook input (absent in the main session). Added `_lib.in_subagent(data)`; `orchestrator-write-guard` no-ops when it's true. Corrected the docstring, README, projectOverview, and AGENTS.
**Alternatives considered:** A settings.json scope option (none exists); branching on `agent_type` (present in the main session under `--agent`, so it would wrongly disable the gate). Left open: the guard still ignores `Bash`, so the orchestrator could bypass it via shell redirection — tracked as a separate gap.

## 2026-07-14: Read the dispatch id from the tool_use block, and backstop SubagentStop

**Source:** commit ed29c54, PR #17

**Context:** `subagent-return` couldn't tell which task a subagent ran. `id_from_transcript` scanned `role:user` messages, but CC hands SubagentStop the PARENT transcript, where the dispatch is an assistant `tool_use(Task|Agent)` block. The id was never found, the gate failed closed, and with no backstop on SubagentStop the worker hung indefinitely.
**Decision:** Read the id from the assistant `tool_use(Task|Agent)` `input.prompt` (last dispatch, the one that just finished), with `role:user` text as a fallback. Add a stall backstop to `subagent-return` mirroring the Stop gate's.
**Alternatives considered:** PAUSED (lifts every gate); loosening the regex (the id was well-formed, just where the parser never looked).

## 2026-07-14: Commit the working-memory kit into the guild repo

**Source:** commit e5f6ac0

**Context:** The WM overlay (see the 2026-07-13 entry below) went in untracked, leaving open whether it belonged in this repo or should stay local.
**Decision:** Committed it (e5f6ac0), so the guild ships the working-memory kit bundled in. Closes the corresponding open question, now removed from openQuestions.

## 2026-07-13: Install the working-memory kit as an untracked overlay

**Source:** working tree (untracked `_working-memory/`, `scripts/`, `.github/`, `AGENTS.md`; modified `CLAUDE.md`, `.gitignore`)

**Context:** The guild repo had no durable, cross-session project memory. A separate copy-in kit provides one.
**Decision:** Layer the working-memory kit onto the guild and hydrate its files from the codebase before committing. The kit is not yet tracked—whether it lands in this repo or stays local is still open (see [[openQuestions]]).
**Alternatives considered:** Hand-writing context into `CLAUDE.md` (rejected—it bloats the always-on contract and has no update discipline).

## 2026-07-13: Consolidate the kit under `.agent-guild/`

**Source:** commit 5546d19, PR #16

**Context:** A copy-in install used to spray five entries across the host repo root (`CLAUDE.md`, `.claude/`, `hooks/`, `scripts/`, `templates/`, plus a runtime `state/`). That's a lot of surface for anyone trying the kit or keeping a repo tidy.
**Decision:** Move `hooks/`, `scripts/`, `templates/`, and the runtime `state/` bus under a single hidden `.agent-guild/`, and the orchestrator contract to `.agent-guild/CLAUDE.md`. The root `CLAUDE.md` becomes a one-line `@.agent-guild/CLAUDE.md` import. Install footprint drops to two directories: `.claude/` and `.agent-guild/`.
**Alternatives considered:** Ship as a plugin now (deferred—see the plugin entry). Keep the flat layout (rejected—clutters the host root).

## 2026-07-11: Let auditions through the gates with an allow path, not PAUSED

**Source:** commit d330792, PR #10

**Context:** Audition dispatches carry no `Task-ID`, so `dispatch-guard` blocked them and `subagent-return` failed closed on the id-less transcript—an audition subagent could never finish.
**Decision:** Add an `Audition-ID: A-NNN` allow path (log-and-pass) across `_lib.py` and both hooks, mirroring the auditor precedent.
**Alternatives considered:** The `PAUSED` escape hatch (rejected—it lifts every gate, which makes the audition run unrepresentative of a gated job).

## 2026-07-10: Enforcement lives at the main-session boundary only

**Source:** commit 39693ea

**Context:** Claude Code hooks fire on the main session's actions, not on tool calls made inside a subagent.
**Decision:** Put all four mechanical gates at main-session boundaries (`dispatch-guard`, `subagent-return`, `stop-gate`, `orchestrator-write-guard`) and back subagent-internal behavior with prompts plus tool allowlists (e.g. checkers ship with no Edit tool). Be explicit in the docs about which guarantees are gated and which are prompt-guided.
**Alternatives considered:** Treating prompt rules as equivalent to gates (rejected—it overstates what the kit guarantees).

## 2026-07-10: Fixed model ladder haiku → sonnet → opus → fable

**Source:** commit 66cfbf1 (orchestrator contract)

**Context:** Tasks vary from mechanical to taste-heavy, and a failed tier needs somewhere to escalate.
**Decision:** Route each task by the work, not a default. Escalation climbs the ladder with the retry budget reset at each rung; `fable` is the reserved final rung for genuinely hard, ambiguous problems. There is no rung above it.
**Alternatives considered:** A single model for everything (rejected—the kit's whole premise is that a cheap model under an independent check beats one expensive model grading itself).

## Deferred: package the kit as a Claude Code plugin

**Source:** README "Later: A Plugin"; commit 4cc4d9d

**Context:** Most of the kit (agents, skills, hooks) would package as a plugin under `.claude-plugin/plugin.json`.
**Decision:** Defer. A plugin can't ship an always-on `CLAUDE.md`, so the contract still needs a per-project import or a SessionStart hook that injects it. Expect a hybrid (static tooling as a plugin, the contract and `state/` staying in the project), worth it only once the kit runs across many projects.
