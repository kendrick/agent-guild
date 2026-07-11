# SMOKE.md: See Every Gate Fire Once

Ten minutes in a fresh Claude Code session, run before the kit guards real work. Each step is a thing to type or run and the exact behavior to expect. If a step doesn't match, fix that gate before trusting it.

Two terminals help: one running `claude` in the repo root (the **session**), one plain **shell** in the same directory for seeding state and inspecting files. Prompts to paste into the session are shown as `> ...`.

## Preflight

1. Start `claude` in the repo root. On a freshly copied-in kit, Claude Code asks you to trust the workspace before it will run the project's hooks. **Accept it.** Until you do, the hooks don't fire, and a session with no gates is not proof of anything, it just looks like it passed.
2. Type `/hooks`. Expect four registered: `stop-gate` (Stop), `subagent-return` (SubagentStop), `dispatch-guard` and `orchestrator-write-guard` (PreToolUse).
3. In the shell: `python3 hooks/test_hooks.py`. Expect `44 passed, 0 failed`. This proves the gate logic offline; the steps below prove it fires inside a live session.

Start from a clean slate in the shell:

```
rm -f state/tasks/T-*.md state/verdicts/*.md state/disputes/*.md state/notes/*.md state/log/* state/PAUSED state/STALLED.md
```

## Part A: The Four Hook Gates

### A1. A no-job session stops normally

- Session: `> What is 2 + 2?`
- Expect: it answers `4` and the turn ends. The stop gate no-ops because no task is open. If the turn won't end, the no-job gate is broken and the kit would strangle ordinary use.

### A2. A dispatch with no Task-ID is denied

- Session: `> Use the Agent tool to dispatch subagent_type worker-standard with the prompt "write a limerick". Send it exactly like that.`
- Expect: `dispatch-guard` blocks before the subagent starts, with a message containing `has no id line`. The orchestrator relays that it needs a `Task-ID`.

### A3. The stop gate holds a turn open while a task is unfinished

- Shell: seed one open task.
  ```
  scripts/new-task.py "smoke gate probe"
  ```
  (This creates `state/tasks/T-001.md` at status `pending`, which counts as open.)
- Session: `> How many open tasks are there right now?`
- Expect: the session cannot end the turn. `stop-gate` blocks and hands back the next move for `T-001` (assign and dispatch its executor). The session relays that instead of stopping clean.

### A4. The write-guard keeps the orchestrator out of deliverables

- With `T-001` still open, Session: `> Add the line "smoke test" to the very top of README.md.`
- Expect: `orchestrator-write-guard` blocks the edit with a message containing `orchestrator contract`, telling the session to dispatch a worker or have you pause. The orchestrator does not edit README.

### A5. PAUSED lifts every gate

- Shell: `touch state/PAUSED`
- Session: `> Now add the line "smoke test" to the top of README.md.`
- Expect: the edit goes through, and the turn ends without the stop gate blocking, even though `T-001` is still open. Every hook stands down while `state/PAUSED` exists.
- Shell cleanup: undo the README edit and clear the probe state.
  ```
  git checkout README.md
  rm -f state/PAUSED state/tasks/T-001.md state/log/*
  ```

## Part B: The Lifecycle Loop

This drives a tiny real job so you watch a FAIL, a dispute, and an escalation happen. The check is deterministic (a `grep`), and you control the artifact, so each outcome is predictable rather than up to a model's mood.

### B0. Seed a toy constitution, a passing audit, and one task

Run this whole block in the shell:

```
cat > state/spec.md <<'EOF'
# Spec
Produce guild-motto.txt: a single line, all uppercase, containing the word GUILD.
EOF

cat > state/constitution.md <<'EOF'
# Constitution: smoke
## Clauses
### C-1: motto shouts the guild
- text: guild-motto.txt contains the exact uppercase word GUILD.
- check: scripts/check-build.sh "grep -q GUILD guild-motto.txt"
- severity: blocker
- failing example: a file reading "the guild endures" (lowercase).
EOF

# A passing constitution audit, so dispatch-guard unblocks workers.
cat > state/verdicts/CON-audit-r0.md <<'EOF'
---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: PASS
checked_at: 2026-01-01T00:00:00Z
---
## Per-clause results
| clause | method | evidence | expected | actual | result |
| C-1 | falsifiable + scripted | has a failing example and a grep check | falsifiable | falsifiable | PASS |
EOF

scripts/new-task.py "write the guild motto"
```

Then open `state/tasks/T-001.md` in your editor and set these frontmatter fields: `clauses: [C-1]`, `executor: worker-standard`, `executor_model: sonnet`, `checker: checker-deterministic`, `check_method: scripts/check-build.sh "grep -q GUILD guild-motto.txt"`, `status: assigned`. In the `## Spec excerpt` section write: `Write guild-motto.txt containing exactly one line: GUILD ENDURES`.

### B1. Happy path to complete

- Session: `> Dispatch the executor for T-001. Its Task-ID is T-001.`
- Expect: worker-standard runs, writes `guild-motto.txt`, sets `artifacts` and `status: needs-check`, drops a note in `state/notes/T-001.md`. `subagent-return` lets it finish because the state file proves the protocol. The stop gate then blocks the turn until the orchestrator sets `T-001` to `checking` and dispatches `checker-deterministic`. The checker runs the grep, it passes, and a PASS verdict lands at `state/verdicts/T-001-sonnet-r0.md`. The orchestrator sets `T-001` complete.
- Shell check: `cat state/verdicts/T-001-sonnet-r0.md` shows `verdict: PASS`.

### B2. A forced FAIL and rework

- Shell: reset the task and break the artifact so the check must fail.
  ```
  printf 'the guild endures\n' > guild-motto.txt   # lowercase: violates C-1
  ```
  In the editor set `T-001` back to `status: checking`, `retries: 0`.
- Session: `> Dispatch checker-deterministic for T-001.`
- Expect: the checker runs the grep, it fails (exit 1), and it writes `state/verdicts/T-001-sonnet-r0.md` as `verdict: FAIL` with a `## Diagnosis` naming the file and C-1. The orchestrator copies that diagnosis into the task's `## Rework diagnosis`, sets `status: assigned`, `retries: 1`, and re-dispatches the worker, which uppercases the file. A re-check passes.

### B3. A forced dispute and ruling

- Shell: make the artifact actually correct, then plant a wrong FAIL and a dispute, as if a checker misread valid work.
  ```
  printf 'GUILD ENDURES\n' > guild-motto.txt
  cat > state/verdicts/T-001-sonnet-r1.md <<'EOF'
  ---
  task: T-001
  tier: sonnet
  retry: 1
  checker: checker-deterministic
  verdict: FAIL
  ---
  ## Diagnosis
  - file: guild-motto.txt:1 / clause C-1 / expected GUILD / actual "not found"
  EOF
  cat > state/disputes/T-001-sonnet-r1.md <<'EOF'
  ---
  task: T-001
  verdict_ref: state/verdicts/T-001-sonnet-r1.md
  filed_by: worker-standard
  claim: The file already contains GUILD; the check was misread.
  status: open
  ---
  ## Worker evidence
  - clause C-1 requires the word GUILD; guild-motto.txt:1 reads "GUILD ENDURES".
  EOF
  ```
  In the editor set `T-001` to `status: disputed`, `retries: 1`.
- Session: `> Rule on the dispute for T-001.`
- Expect: the orchestrator reads `guild-motto.txt` itself, confirms it satisfies C-1, appends an `## Orchestrator ruling` to the dispute upholding the worker, sets the dispute `status: worker-upheld`, and marks `T-001` complete. It does not just take the worker's word; it checks the artifact.

### B4. A forced escalation

- Shell / editor: set `T-001` to `status: rework`, `executor_model: sonnet`, `retries: 2` (the sonnet tier's budget is spent).
- Session: `> T-001 has exhausted its retry budget at the sonnet tier. Proceed per the retry ladder.`
- Expect: the orchestrator escalates. It sets `executor_model: opus`, resets `retries: 0`, appends an entry to `escalations`, and writes a line to `state/log/escalations.log`. When it re-dispatches, it passes `model: opus` so the dispatch matches the new tier; `dispatch-guard` would block a sonnet dispatch here.
- Shell check: `cat state/log/escalations.log` shows the sonnet-to-opus bump.

### B5. Retrospective

- Session: `> Run /retrospective for this job.`
- Expect: `summarize.py` reports the FAIL you forced as a catch, the escalation, and the upheld dispute. The write-up names them.
- Shell cleanup:
  ```
  rm -f guild-motto.txt state/tasks/T-*.md state/verdicts/*.md state/disputes/*.md state/notes/*.md state/log/* state/spec.md state/constitution.md
  ```

## Part C: Two Things That Look Like Breakage But Aren't

- **The first accessibility check is slow and needs the network.** `scripts/check-a11y.mjs` installs Playwright and axe into `scripts/node_modules` on its first run, which takes a couple of minutes and a connection. That's expected, once. Run offline, it can't bootstrap and exits 3, which a checker reports as an ERROR verdict (the check couldn't run), never a PASS or a clause FAIL.
- **If a session ever ends with tasks still open, look for `state/STALLED.md`.** The stop gate writes it when the same unfinished state blocked it three times running, then stands down so you aren't stuck. It names the tasks that jammed: a checker owing a verdict, a dispute needing a ruling, or a task that should be abandoned. Resolve by hand and delete the file. A fixture in `hooks/test_hooks.py` already exercises this path, so you don't need to provoke it live.

## Fresh-Copy Portability

To confirm the kit travels: copy `CLAUDE.md .claude/ hooks/ scripts/ templates/` into a throwaway project, add `state/` to that project's `.gitignore`, create the `state/` subdirs, start `claude` there, and rerun Part A. The one new thing you'll see is Claude Code's trust prompt for the project's hooks on first launch. Accept it. That prompt is the kit working as designed, not a fault.
