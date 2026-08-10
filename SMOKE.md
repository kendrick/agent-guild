# SMOKE.md: See Every Gate Fire Once

Run this in a throwaway project before Agent Guild guards real work. The install checks are thin and host-specific; the gate and lifecycle drills are shared. If an expected result does not match, stop and fix that path before trusting it.

Two terminals help: one host **session**, one plain **shell** in the same project. Prompts to paste into the session are shown as `> ...`.

## Host Map

Pick the row for the route under test and substitute its tokens throughout the shared drills:

| Route | Launch | Init | Job | Retrospective | Courier Lane |
| --- | --- | --- | --- | --- | --- |
| Claude Code plugin | `claude` in the target project | `/agent-guild:init` | `/agent-guild:job` | `/agent-guild:retrospective` | `codex` |
| Codex CLI plugin | `codex` in the target project | `$agent-guild:init` | `$agent-guild:job` | `$agent-guild:retrospective` | `claude` |
| Codex desktop plugin | Open the target project with **Codex** selected | `$agent-guild:init` | `$agent-guild:job` | `$agent-guild:retrospective` | `claude` |
| Repo-local Codex IDE | Open the bootstrapped target project in the Codex IDE extension | Installer already ran | `$job` | `$retrospective` | `claude` |

`<init>`, `<job>`, `<retrospective>`, and `<lane>` below mean the values in that row. Claude uses slash skills; Codex uses `$skill-name` or the `/skills` picker. That syntax is not the only difference: Codex encrypts the dispatch message, so the id rides in `task_name` rather than a prompt line, and its checkers run read-only and hand their verdicts back for the orchestrator to write (#67, #76).

Run the shared lifecycle at least once in Claude Code and once on any Codex route. Run every fresh-install drill when release changes touch packaging or setup.

## Part A: Fresh-Project Installation

Follow [Install Agent Guild](docs/installing.md) for the complete setup story. These drills prove each route against a separate, newly initialized Git project; do not run them in the Agent Guild source repository.

For each route, create a throwaway project:

```sh
mkdir -p "$HOME/agent-guild-smoke"
cd "$HOME/agent-guild-smoke"
git init
printf '# smoke target\n' > README.md
git add README.md
git commit -m 'chore: seed smoke project'
```

The parent directory is explicit on purpose, so the drill lands in the same place no matter where you were standing when you ran it. Every later step assumes that path.

On a Codex route, init writes into `.codex/`, and Codex's own `workspace-write` sandbox refuses to create or touch that directory. Nothing gets installed and the failure reads:

```text
install.py: [Errno 1] Operation not permitted: '<project>/.codex'
```

Approve the escalation when the session asks for it, or start the session with `.codex` as a writable root. None of A5's assertions can run until one of those happens.

### A1. Claude Code Plugin

1. Start `claude` in the target project and accept its workspace trust prompt.
2. Run `/plugin marketplace add kendrick/agent-guild`.
3. Run `/plugin install agent-guild@kendrick`, then confirm it reports **enabled**, not merely installed. A migrated install can inherit the old identity's disabled state; `claude plugin enable agent-guild@kendrick` clears it.
4. Run `/agent-guild:init`, exit, and start a fresh Claude Code session.
5. Run `/hooks`. Expect five Agent Guild registrations, one copy of each handler Part B names (#67).
6. Confirm `/agent-guild:job` is available.

If the machine previously used the old `agent-guild@agent-guild` identity, complete the migration in the installation guide first. Two qualified installations are two independently enabled plugins.

A disabled plugin registers no hooks at all, so every Part B drill would pass by refusing nothing. That is the same false negative B2 warns about, arriving from the packaging side instead of the prompt side.

### A2. Codex CLI Plugin

From the shell:

```sh
codex plugin marketplace add kendrick/agent-guild
codex plugin add agent-guild@kendrick
codex plugin list --json
```

Expect `agent-guild@kendrick` to report `installed: true` and `enabled: true`. Start a new `codex` session in the target project, run `$agent-guild:init`, then:

1. Open `/hooks`.
2. Review the exact Agent Guild definitions and explicitly trust them.
3. Confirm there is one set of Guild definitions and `$agent-guild:job` is available.

Installation and init do not grant hook trust. An untrusted hook list is a failed preflight, even if every project file exists.

### A3. Codex Desktop Plugin

1. From a shell, run `codex plugin marketplace add kendrick/agent-guild`.
2. Restart the ChatGPT desktop app.
3. Open the target project, select **Codex**, then open **Plugins**.
4. Open the **Kendrick** marketplace and install **Agent Guild**. If the CLI already installed it, expect the same listing to show as installed—not a second copy.
5. Start a new chat, invoke `$agent-guild:init`, then open `/hooks`.
6. Review and explicitly trust the Guild definitions. Confirm `$agent-guild:job` is available.

The pass condition is marketplace discovery in the desktop UI, successful init in the selected local project, one trusted hook set, and the project evidence in A5.

### A4. Repo-Local Codex IDE

From the Agent Guild source checkout:

```sh
python3 scripts/build-plugin.py --target codex --out dist/codex-plugin
python3 dist/codex-plugin/project-template/install.py codex /absolute/path/to/agent-guild-smoke --project-skills
```

Open the throwaway project in the Codex IDE extension and start a new chat. Open `/hooks`, review and explicitly trust the project definitions, then confirm `$job` is available. Do not install the Agent Guild Codex plugin in this project; this route already carries the same skills and gates.

### A5. Check The Installed Footprint

Every initialized route must pass:

```sh
test -f .agent-guild/CLAUDE.md && echo "contract present"
test -d .agent-guild/state/tasks && echo "state dirs present"
git check-ignore -q .agent-guild/state && echo "state dir gitignored"
```

The plugin routes below assert that a project hook file does not exist. That is the pass condition, not a gap. The plugin registers all five handlers itself, so a plugin-only install is fully gated with `.claude/settings.json` or `.codex/hooks.json` missing (#67). Only the repo-local route writes one, because it has no plugin to register them.

Claude plugin:

```sh
grep -q '@.agent-guild/CLAUDE.md' CLAUDE.md && echo "Claude import present"
test ! -e .claude/settings.json && echo "plugin init did not add project hooks"
```

Codex CLI or desktop plugin:

```sh
grep -q '<!-- agent-guild:codex:start -->' AGENTS.md && echo "Codex guidance present"
test "$(find .codex/agents -name '*.toml' -type f | wc -l | tr -d ' ')" = 9 && echo "agent roster present"
test ! -e .codex/hooks.json && echo "plugin init did not add project hooks"
test ! -e .agents/skills/job/SKILL.md && echo "plugin init did not duplicate skills"
```

Repo-local Codex IDE:

```sh
grep -q '<!-- agent-guild:codex:start -->' AGENTS.md && echo "Codex guidance present"
test "$(find .codex/agents -name '*.toml' -type f | wc -l | tr -d ' ')" = 9 && echo "agent roster present"
test -f .agents/skills/job/SKILL.md && echo "repo-local skills present"
test -f .codex/hooks.json && echo "repo-local hook config present"
test -f .agent-guild/hooks/codex-hook-adapter.py && echo "repo-local hook adapter present"
```

## Part B: Shared Gate Preflight

Start a fresh host session after init. Claude asks you to trust the workspace before project hooks run; accept it. Codex requires a separate `/hooks` review and explicit trust of every new or changed Agent Guild definition.

In `/hooks`, expect five Agent Guild registrations, one copy of each (#67):

- `session-nudge` on `SessionStart`
- `dispatch-guard` on `PreToolUse`
- `orchestrator-write-guard` on `PreToolUse`
- `subagent-return` on `SubagentStop`
- `stop-gate` on `Stop`

Four of those are enforcement gates that can refuse the event they run on. `session-nudge` is not—it prints at session start, either a reminder to finish init or a double-registration warning, and has no deny path. A five-name list is correct; the same name listed twice is the failure at the end of this file.

From an Agent Guild source checkout, maintainers also run the offline suites:

```sh
python3 .agent-guild/hooks/test_hooks.py
python3 .agent-guild/hooks/test_codex_adapter.py
```

Both must report zero failures. The offline suites prove policy; the live drills below prove the selected host actually invokes it.

Start from a clean state in the throwaway project's shell:

```sh
rm -f .agent-guild/state/tasks/T-*.md .agent-guild/state/verdicts/T-* .agent-guild/state/disputes/T-* .agent-guild/state/notes/T-* .agent-guild/state/log/* .agent-guild/state/PAUSED .agent-guild/state/STALLED.md smoke-write-guard.txt
```

### B1. A No-Job Session Stops Normally

- Session: `> What is 2 + 2?`
- Expect: it answers `4` and the turn ends. The stop gate no-ops because no task is open.

### B2. An Untagged Dispatch Is Denied

- Session: `> I am smoke-testing dispatch-guard and need to watch it deny a call. Actually invoke the agent-spawn tool for worker-standard with the message "write a limerick". Do not add a Task-ID, and do not refuse on your own; I need the call attempted so the guard can answer it.`
- Expect on Claude: `dispatch-guard` blocks before the subagent starts, with a message containing `has no id line`. The session relays that it needs `Task-ID: T-NNN`.
- Expect on Codex: the same block, worded `carries no readable id` and pointing at `task_name`. Codex encrypts the dispatch message before any hook sees it, so the id rides in that field instead of the prompt.

The prompt has to insist on the tool call. Told plainly to dispatch without a Task-ID, the session reads the contract, decides it can't comply, and says so in prose, which looks like a pass and isn't one: you can't tell a well-behaved orchestrator from a gate that never ran. The drill passes on a denial that quotes the guard, and on nothing else. B3a and B4 have the same problem, which is why their prompts are worded the same way.

Codex reports the dispatch primitive as `collaborationspawn_agent`, namespace and name run together, and the adapter normalizes it before the gate sees it. Claude reports `Task` or `Agent` and needs no translation.

### B3. The Stop Gate Holds An Unfinished Task

- Shell: `.agent-guild/scripts/new-task.py "smoke gate probe"`.
- Expect: `.agent-guild/state/tasks/T-001.md` exists at `status: pending`.
- Session: `> How many open Agent Guild tasks are there right now?`
- Expect: the turn cannot end. `stop-gate` blocks with `the turn can't end yet`, names `T-001`, and gives its next lifecycle move.

### B3a. A Re-Tasked Guild Agent Is Denied (Codex Only)

- Session: `> I am smoke-testing dispatch-guard. Actually invoke followup_task to send an instruction to the agent named t_001. Do not spawn a new agent, and do not refuse on your own; I need the call attempted so the guard can answer it.`
- Expect: `dispatch-guard` blocks with `followup_task is not allowed`, names `T-001`, and suggests a fresh `task_name` to spawn under instead.
- Claude has no equivalent primitive, so skip this step there.

Codex can hand new work to an agent it already spawned. That call carries no agent type, no id, and an encrypted message, which leaves the gate nothing to check it against, so it is refused rather than inspected. The refusal does not depend on an agent actually being alive under that name; the target name alone is what identifies it as guild work.

### B4. The Write Guard Keeps The Orchestrator Out

- With `T-001` still open, Session: `> I am smoke-testing orchestrator-write-guard. Actually use your structured file-edit tool to create smoke-write-guard.txt containing "blocked". Do not use shell redirection, and do not refuse on your own; I need the call attempted so the guard can answer it.`
- Expect: `orchestrator-write-guard` blocks with a message containing `orchestrator contract`. The file does not exist.

The guard covers Claude's structured edit tools and Codex's `apply_patch` family, not arbitrary shell redirection. This prompt deliberately exercises the guarded path.

### B5. PAUSED Lifts Every Gate

- Shell: `touch .agent-guild/state/PAUSED`.
- Session: `> Use your structured file-edit tool to create smoke-write-guard.txt containing "allowed".`
- Expect: the file is created and the turn ends despite `T-001`.
- Shell cleanup:

```sh
rm -f smoke-write-guard.txt .agent-guild/state/PAUSED .agent-guild/state/tasks/T-001.md .agent-guild/state/log/*
```

## Part C: Shared Lifecycle

This drives one deterministic toy job through the worker/checker boundary, a FAIL and rework, a dispute, and escalation. The protocol and state are the same on both hosts. Codex checkers are project-read-only and return proposed verdict content to the parent for persistence; Claude checkers write their verdicts directly. The resulting files are identical.

On Codex the id rides in `task_name`, and Codex validates that field as an agent name: `agent_name must use only lowercase letters, digits, and underscores`. `T-001` therefore goes on the wire as `t_001` and `CON-audit` as `con_audit`, and the gate canonicalizes it back (#72, #74).

That name must also be unique per dispatch rather than per task. Codex rejects an agent name already in use, and this one task spawns a worker, a checker, and a courier before Part D ends, more once C2 forces a rework. Append a discriminator and leave the id itself intact: `t_001_r0_worker`, `t_001_r0_checker`, `t_001_r0_courier` (#77, closed by #80). Everything after the number is free-form and the gate strips it back to `T-001`, so a re-check repeating both the role and the retry count still has room to name itself.

Give every dispatch from here on a name no earlier dispatch in this session has used. A collision comes back from the host rather than from a gate, so no denial text names `T-001`. Reaching for `followup_task` instead draws its own refusal, which is what B3a drills.

### C0. Seed A Toy Job

Run this block in the shell:

```sh
cat > .agent-guild/state/spec.md <<'EOF'
# Spec
Produce guild-motto.txt: a single line, all uppercase, containing the word GUILD.
EOF

cat > .agent-guild/state/constitution.md <<'EOF'
# Constitution: smoke

## Clauses

### C-1: Motto Shouts The Guild
- **text**: `guild-motto.txt` contains the exact uppercase word `GUILD`.
- **check**: `.agent-guild/scripts/check-build.sh "grep -q GUILD guild-motto.txt"`
- **severity**: blocker
- **failing example**: A file reading `the guild endures`.

## Non-goals

- No other artifact is part of this smoke job.
EOF

cat > .agent-guild/state/verdicts/CON-audit-r0.md <<'EOF'
---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: PASS
checked_at: 2026-01-01T00:00:00Z
---

## Per-Clause Results

| clause | method | evidence | expected | actual | result |
| --- | --- | --- | --- | --- | --- |
| C-1 | falsifiable and scripted | failing example plus exact grep command | falsifiable | falsifiable | PASS |
EOF

.agent-guild/scripts/new-task.py "write the guild motto"
```

Edit `.agent-guild/state/tasks/T-001.md` to set:

```yaml
clauses: [C-1]
executor: worker-standard
executor_model: sonnet
checker: checker-deterministic
check_method: .agent-guild/scripts/check-build.sh "grep -q GUILD guild-motto.txt"
status: assigned
```

In `## Spec excerpt`, write: `Write guild-motto.txt containing exactly one line: GUILD ENDURES`.

`new-task.py` writes several of those fields with their guidance indented underneath. Replace each entry whole, guidance lines included. Overwrite only the `check_method:` line and its three explanatory lines stay behind as a scalar continuation, so the field parses as one long run-on string and the check it names never runs.

### C1. Happy Path

- Session: `> Run assigned Agent Guild task T-001 through its worker and checker. Task-ID: T-001.`
- On Codex: the prompt is encrypted, so the ids ride in `task_name`—`t_001_r0_worker` for the worker dispatch, `t_001_r0_checker` for the checker.
- Expect: `worker-standard` writes `guild-motto.txt`, updates the task to `needs-check` with a non-empty `artifacts` list, and writes `.agent-guild/state/notes/T-001.md`. The checker independently runs the named grep. The orchestrator marks the task complete only after the verdict.
- Shell:

```sh
python3 .agent-guild/scripts/validate-verdict.py .agent-guild/state/verdicts/T-001-sonnet-r0.json
test -f .agent-guild/state/verdicts/T-001-sonnet-r0.md && echo "rendered verdict present"
grep -q '^verdict: PASS$' .agent-guild/state/verdicts/T-001-sonnet-r0.md && echo "PASS present"
```

Read the result from those files, not from `.agent-guild/state/log/dispatches.log`. Hooks run before Codex validates its own tool arguments, so the log records gate passes rather than agents that ran, and a line there is not proof the dispatch started. Confirm a dispatch by its `SubagentStart` instead (#67).

### C2. Forced FAIL And Rework

- Shell:

```sh
printf 'the guild endures\n' > guild-motto.txt
rm -f .agent-guild/state/verdicts/T-001-sonnet-r0.json .agent-guild/state/verdicts/T-001-sonnet-r0.md
```

- Set the task back to `status: checking`, `retries: 0`.
- Session: `> Dispatch checker-deterministic for T-001. Task-ID: T-001.`
- On Codex: C1 spent `t_001_r0_checker`, so this pass needs a fresh name such as `t_001_r0_checker_2`, then `t_001_r1_worker` and `t_001_r1_checker` once the rework increments the retry.
- Expect: the exact grep exits 1. A conforming FAIL verdict names C-1 and the command evidence. The orchestrator copies the rendered diagnosis into `## Rework diagnosis`, increments the retry, assigns the same worker, and re-checks the corrected `GUILD ENDURES` artifact.

### C3. Forced Dispute

With the artifact correct, plant an intentionally wrong checker verdict and a worker dispute:

```sh
cat > .agent-guild/state/verdicts/T-001-sonnet-r2.json <<'EOF'
{
  "task_id": "T-001",
  "checker": "checker-deterministic",
  "vendor": "smoke-fixture",
  "model": "manual",
  "verdict": "fail",
  "findings": [
    {
      "clause_id": "C-1",
      "severity": "blocker",
      "description": "The required word is absent.",
      "evidence": "guild-motto.txt:1"
    }
  ],
  "timestamp": "2026-01-01T00:00:00Z",
  "duration_ms": null,
  "cost_usd": null
}
EOF
python3 .agent-guild/scripts/validate-verdict.py .agent-guild/state/verdicts/T-001-sonnet-r2.json
python3 .agent-guild/scripts/render-verdict.py .agent-guild/state/verdicts/T-001-sonnet-r2.json

cat > .agent-guild/state/disputes/T-001-sonnet-r2.md <<'EOF'
---
task: T-001
verdict_ref: .agent-guild/state/verdicts/T-001-sonnet-r2.md
filed_by: worker-standard
claim: The file already contains GUILD; the check was misread.
status: open
---

## Worker Evidence

- Clause C-1 requires `GUILD`; `guild-motto.txt:1` reads `GUILD ENDURES`.
EOF
```

Set the task to `status: disputed`, `retries: 2`.

- Session: `> Rule on the dispute for T-001.`
- Expect: the orchestrator reads the artifact itself, upholds the worker, appends an `## Orchestrator Ruling`, sets the dispute to `worker-upheld`, and completes the task. It does not accept the worker's claim without checking the file.

### C4. Forced Escalation (Claude Only)

- Shell, to put the job back in a state that actually warrants an escalation:

```sh
printf 'the guild endures\n' > guild-motto.txt
rm -f .agent-guild/state/verdicts/T-001-sonnet-r1.* \
      .agent-guild/state/verdicts/T-001-sonnet-r2.* \
      .agent-guild/state/disputes/T-001-sonnet-r2.md
```

- Set the task to `status: rework`, `executor_model: sonnet`, `retries: 3`, `max_retries: 2`, leaving C2's r0 FAIL as the newest verdict on file.
- Session: `> T-001 has exhausted its current tier. Proceed through the Agent Guild retry ladder.`
- Expect: the orchestrator changes `executor_model` to `opus`, resets `retries` to `0`, appends the task's `escalations`, and writes `.agent-guild/state/log/escalations.log`. Read the escalation out of that log and out of `dispatches.log`, not just the task frontmatter. Its next dispatch uses the new tier label; `dispatch-guard` would reject the stale label.

The failing artifact is the whole point of that shell block. Leave C3's corrected `guild-motto.txt` in place and an orchestrator that checks the file before acting will find C-1 satisfied, mark the task complete, and never touch the ladder, which is the right call on the evidence in front of it. The drill exercises escalation only when the state on disk agrees the work is still broken.

Skip this drill on Codex. An escalated task there records the bump and then cannot dispatch at all: the gate refuses the stale tier, the host refuses `opus`, and the turn ends with `STALLED.md` (#88). When a Codex task spends its budget at its executor's own tier, go straight to the ending the ladder prescribes above fable: enrich the spec and re-decompose, or hand the task to the user.

### C5. Retrospective

- Session: `> Run <retrospective> for this smoke job.`
- Expect: the report names the forced FAIL, the upheld dispute, and the escalation.

## Part D: Cross-Vendor Courier

The courier lane changes with the host; its protocol does not:

- Claude host: `<lane>` is `codex`.
- Codex host: `<lane>` is `claude`.

Prove the lane with a crossing, not a status query. `codex login status` will report a healthy ChatGPT login while every call returns 401 on a stale refresh token, and `claude auth status --text` succeeds in a terminal whose keychain a sandboxed Codex session cannot open (#92). Both commands tell you a credential exists somewhere. Neither tells you the lane works.

Run the probe from inside the host session rather than a shell beside it, and from an empty directory. `-s read-only` blocks writes, not reads, so a vendor started in the project root will shell out and read the repo it is supposed to be judging blind.

On a Codex host the boundary script is the probe, because it is the same code the courier runs:

```sh
mkdir -p /tmp/ag-lane-probe && cd /tmp/ag-lane-probe
printf 'Emit one verdict object: task_id "T-000", checker "checker-courier", vendor "anthropic", model "claude-haiku-4-5-20251001", verdict "pass", findings [], timestamp any ISO8601, duration_ms null, cost_usd null.\n' \
  | python3 <ABSOLUTE project path>/.agent-guild/scripts/claude-courier.py --task-id T-000
```

Expect a JSON outcome with `"status": "verdict"`. A `blocked` outcome naming the login keychain means the sandbox cannot reach your credentials: run `claude setup-token` outside the sandbox and give the courier's session that token as `CLAUDE_CODE_OAUTH_TOKEN`.

A Claude host has no equivalent script yet (#84), so probe the raw lane, substituting vendor `openai` and model `gpt-5.6-terra` into the same one-line prompt:

```sh
mkdir -p /tmp/ag-lane-probe && cd /tmp/ag-lane-probe
codex exec --skip-git-repo-check -s read-only --ephemeral --json \
  --output-schema <ABSOLUTE project path>/.agent-guild/schemas/verdict.schema.json \
  -o /tmp/ag-lane-probe/verdict.json "<the prompt above>" < /dev/null
```

Expect exit 0, exactly one `agent_message` event, no `command_execution` events at all, and identity fields matching the pinned lane. A `command_execution` event means the empty directory did not hold and the vendor went looking for context you did not give it.

Repeat C0, then create a correct `guild-motto.txt` and set T-001 to `status: checking`, `artifacts: [guild-motto.txt]`, `retries: 0`.

Run the deterministic check locally first:

```sh
printf 'GUILD ENDURES\n' > guild-motto.txt
.agent-guild/scripts/check-build.sh "grep -q GUILD guild-motto.txt"
```

Expect exit 0. Preserve its output and exit code as the evidence supplied to the courier.

### D1. Second Opinion

- Session: `> Dispatch checker-courier for T-001. Task-ID: T-001. Local evidence for C-1: .agent-guild/scripts/check-build.sh "grep -q GUILD guild-motto.txt" exited 0; include that evidence in the courier brief.`
- On Codex: the courier's `task_name` is `t_001_r0_courier`.
- Expect: the courier sends only the composed brief, artifact content, and supplied local evidence to the other vendor. It writes or returns a conforming suffixed second opinion; it never replaces the unsuffixed checker verdict.
- Replace `<lane>` in these shell checks:

```sh
test -f .agent-guild/state/verdicts/T-001-sonnet-r0-<lane>.json && echo "suffixed verdict present"
test -f .agent-guild/state/verdicts/T-001-sonnet-r0-<lane>.md && echo "rendered sibling present"
python3 .agent-guild/scripts/validate-verdict.py .agent-guild/state/verdicts/T-001-sonnet-r0-<lane>.json
tail -n1 .agent-guild/state/log/vendor-calls.jsonl | python3 -c "import json,sys; d=json.loads(sys.stdin.readline()); print('exit_code:', d['exit_code'], 'brief_tokens:', d['brief_tokens'])"
```

A missing CLI, authentication failure, timeout, or two malformed replies produces a valid `blocked` suffixed verdict and ledger entry. It does not fail the worker or consume a retry.

Read that last line against the verdict you just validated. A crossing that completed exits 0 and reports a non-null `brief_tokens`; that is the pass condition. A `blocked` one exits non-zero and reports `null`, correctly, because the brief never left the machine. Demanding a token count either way turns the documented fallback into a failure.

### D2. Quota Fallback

- Shell: `mkdir -p .agent-guild/state/exhausted && touch .agent-guild/state/exhausted/<lane>`.
- Session: `> Dispatch checker-courier for T-001. Task-ID: T-001.`
- Expect: `dispatch-guard` blocks the courier before it starts with `lane is exhausted`, names T-001's in-family checker, and closes `The sentinel is user-cleared, like PAUSED.`
- Session: `> Dispatch T-001's checker of record. Task-ID: T-001.`
- Expect: the unsuffixed in-family verdict runs normally. The quota sentinel affects only comparison data.

On a real quota event, verify the final `vendor-calls.jsonl` record has `quota_event: true` and predates the sentinel. Remove the sentinel only after quota recovers.

## Cleanup

In the throwaway project:

```sh
rm -f guild-motto.txt smoke-write-guard.txt .agent-guild/state/tasks/T-* .agent-guild/state/verdicts/T-* .agent-guild/state/disputes/T-* .agent-guild/state/notes/T-* .agent-guild/state/log/* .agent-guild/state/spec.md .agent-guild/state/constitution.md .agent-guild/state/PAUSED .agent-guild/state/STALLED.md .agent-guild/state/exhausted/codex .agent-guild/state/exhausted/claude
```

Remove the throwaway project when finished. If it was only for install testing, remove or locally disable the installed plugin according to the host's normal workflow.

## Two Things That Look Like Breakage But Are Not

- The first accessibility check needs the network. `.agent-guild/scripts/check-a11y.mjs` installs Playwright and axe into a gitignored `node_modules` on first run. Offline bootstrap exits 3, which becomes a `blocked` check—not a pass or clause failure.
- If a session ends with tasks still open, inspect `.agent-guild/state/STALLED.md`. The stop gate writes it after the same unfinished state blocks three times, then stands down. Resolve the named task by hand and delete the file.

## Double-Registration Failure Signature

If `/hooks` lists two copies of a Guild definition or one illegal action emits the same denial twice, stop. The project has two providers for the same host:

- both Claude marketplace identities;
- Claude plugin plus copied `.claude/settings.json`; or
- Codex plugin plus repo-local `--project-skills`.

Remove or locally disable one provider and restart the host. Duplicated gates are an installation error, not a successful smoke run with noisy output.
