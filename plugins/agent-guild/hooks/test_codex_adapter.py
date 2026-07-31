#!/usr/bin/env python3
"""Behavioral fixtures for the Codex lifecycle-hook adapter.

Each fixture uses the public Codex command-hook JSON shape and executes the
adapter as a real process. The policy assertions deliberately mirror the
existing Claude hook suite: this file tests only host-bound translation,
project-root resolution, and exit-code behavior.

Run: python3 .agent-guild/hooks/test_codex_adapter.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


HOOKS = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.join(HOOKS, "codex-hook-adapter.py")
KIT_ROOT = os.path.dirname(HOOKS)
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Copied verbatim from a codex-cli 0.145.0 dispatch captured while probing
# issue #67, minus `cwd`, which each test points at its own temp project. Two
# things here are the whole of issue #71 and neither survives paraphrase: the
# tool arrives as its namespace and name run together, and `message` is a
# Fernet token no hook can read. Anything that regresses either one should
# fail against this payload rather than against a tidied-up fixture.
LIVE_DISPATCH = {
    "session_id": "019fac53-247f-7290-b07f-38d4e4be17dd",
    "turn_id": "019fac53-252d-7083-8c73-13adb5dcc587",
    "transcript_path": (
        "/Users/karnett/.codex/sessions/2026/07/29/"
        "rollout-2026-07-29T00-22-37-019fac53-247f-7290-b07f-38d4e4be17dd"
        ".jsonl"
    ),
    "hook_event_name": "PreToolUse",
    "model": "gpt-5.6-terra",
    "permission_mode": "bypassPermissions",
    "tool_name": "collaborationspawn_agent",
    "tool_input": {
        "task_name": "lifecycle_payload",
        "agent_type": "worker-standard",
        "fork_turns": "none",
        "message": (
            "gAAAAABqaY4itlnl6FTGVOtwGIrOMQjBuCTHUBgGHBP-_xNXZCUOxpZMK8jF"
            "_LCb8d0Z8mYEHUBHuz9vTuUc-waaUmXI_7Oa6flLWFWxYY6_62cHUGZ5LdKb"
            "E_zTaHut3apNuOy2TrwU"
        ),
    },
    "tool_use_id": "call_RwoZAd8u0GQcwDzfikH4RrHx",
}


def live_dispatch(project, task_name=None):
    payload = json.loads(json.dumps(LIVE_DISPATCH))
    payload["cwd"] = project
    if task_name is not None:
        payload["tool_input"]["task_name"] = task_name
    return payload


def write_task(project, task_id, **overrides):
    fields = {
        "status": "pending",
        "executor": "worker-standard",
        "executor_model": "sonnet",
        "checker": "checker-deterministic",
        "retries": 0,
        "max_retries": 2,
        "artifacts": "[]",
    }
    fields.update(overrides)
    body = ["---", f"id: {task_id}"]
    body.extend(f"{key}: {value}" for key, value in fields.items())
    body.extend(["---", ""])
    path = os.path.join(
        project, ".agent-guild", "state", "tasks", f"{task_id}.md"
    )
    with open(path, "w", encoding="utf-8") as stream:
        stream.write("\n".join(body))


def con_pass(project):
    """dispatch-guard blocks every worker until the constitution has a PASS
    audit, so any worker-dispatch fixture has to seed one first."""
    body = (
        "---\ntask: T\ntier: sonnet\nretry: 0\n"
        "checker: checker-deterministic\nverdict: PASS\n---\n"
    )
    path = os.path.join(
        project, ".agent-guild", "state", "verdicts", "CON-audit-r0.md"
    )
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(body)


def codex_input(event, project, **fields):
    payload = {
        "session_id": "019fa0c0-23f4-7951-b9ae-f97f8f3a6f39",
        "turn_id": "turn-56",
        "transcript_path": None,
        "cwd": project,
        "hook_event_name": event,
        "model": "gpt-5.6-sol",
        "permission_mode": "default",
    }
    payload.update(fields)
    return payload


def codex_transcript(project, text, shape="response_item"):
    path = os.path.join(
        project, ".agent-guild", "state", "log", f"{shape}.jsonl"
    )
    if shape == "response_item":
        records = [
            {
                "type": "session_meta",
                "payload": {"cwd": project, "parent_thread_id": "parent-1"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            },
        ]
    elif shape == "function_call":
        # How the dispatch above is recorded in the session transcript. `name`
        # and `namespace` are separate fields here, since the hook layer is
        # what glues them, and `arguments` arrives as a JSON string carrying
        # the same encrypted message the dispatch payload did.
        records = [
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "spawn_agent",
                    "namespace": "collaboration",
                    "arguments": json.dumps(
                        {
                            "task_name": text,
                            "agent_type": "worker-standard",
                            "fork_turns": "none",
                            "message": LIVE_DISPATCH["tool_input"]["message"],
                        }
                    ),
                    "call_id": "call_6HoWG9EfZWdrJJnbABRVhxk6",
                },
            }
        ]
    elif shape == "event_msg":
        records = [
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": text},
            }
        ]
    else:
        records = [{"type": "future_unstable_shape", "payload": {"body": text}}]
    with open(path, "w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")
    return path


def seed_verdict_toolchain(project):
    scripts = os.path.join(project, ".agent-guild", "scripts")
    schemas = os.path.join(project, ".agent-guild", "schemas")
    os.makedirs(scripts, exist_ok=True)
    os.makedirs(schemas, exist_ok=True)
    shutil.copy(
        os.path.join(KIT_ROOT, "scripts", "validate-verdict.py"),
        os.path.join(scripts, "validate-verdict.py"),
    )
    shutil.copy(
        os.path.join(KIT_ROOT, "schemas", "verdict.schema.json"),
        os.path.join(schemas, "verdict.schema.json"),
    )


def courier_outcome(task_id, status="verdict"):
    quota = status == "quota"
    verdict = None
    if not quota:
        verdict = {
            "task_id": task_id,
            "checker": "checker-courier",
            "vendor": "anthropic",
            "model": CLAUDE_MODEL,
            "verdict": "pass",
            "findings": [],
            "timestamp": "2026-07-26T18:00:00Z",
            "duration_ms": None,
            "cost_usd": None,
        }
    outcome = {
        "status": status,
        "verdict": verdict,
        "ledger": {
            "task_id": task_id,
            "vendor": "claude",
            "model": CLAUDE_MODEL,
            "started_at": "2026-07-26T18:00:00Z",
            "duration_ms": 1200,
            "exit_code": 1 if quota else 0,
            "tokens_in": None,
            "tokens_out": None,
            "cost_usd": None,
            "quota_event": quota,
        },
        "attempts": 1,
        "diagnostic": "429" if quota else None,
    }
    return "AGENT_GUILD_COURIER_OUTCOME\n" + json.dumps(outcome)


class CodexAdapterTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="ag-codex-hook-")
        self.project = self.tempdir.name
        for name in ("tasks", "verdicts", "disputes", "notes", "log"):
            os.makedirs(
                os.path.join(
                    self.project, ".agent-guild", "state", name
                )
            )

    def tearDown(self):
        self.tempdir.cleanup()

    def run_adapter(self, gate, payload, *extra):
        env = os.environ.copy()
        env.pop("CLAUDE_PROJECT_DIR", None)
        return subprocess.run(
            [sys.executable, ADAPTER, gate, *extra],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )

    def test_dispatch_maps_spawn_agent_and_preserves_exit_two_block(self):
        write_task(self.project, "T-056", status="checking")
        untagged = codex_input(
            "PreToolUse",
            self.project,
            tool_name="spawn_agent",
            tool_use_id="call-dispatch-1",
            tool_input={
                "agent_type": "checker-deterministic",
                "message": "Check the implementation.",
            },
        )
        blocked = self.run_adapter("dispatch-guard", untagged)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        # Every dispatch through this adapter is a Codex one, so the block
        # names the field that host can actually read.
        self.assertIn("no readable id", blocked.stderr)

        tagged = {
            **untagged,
            "tool_input": {
                **untagged["tool_input"],
                "message": "Task-ID: T-056\nCheck the implementation.",
            },
        }
        allowed = self.run_adapter("dispatch-guard", tagged)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_live_dispatch_payload_reaches_the_gate_and_is_identified(self):
        # The gate has to survive the real payload end to end: the glued tool
        # name, the unreadable message, and an id it can only get from
        # task_name. Any one of those left unhandled makes the host unusable,
        # every dispatch rejected for carrying no readable id.
        write_task(self.project, "T-001", status="assigned")
        con_pass(self.project)

        as_captured = self.run_adapter(
            "dispatch-guard", live_dispatch(self.project)
        )
        self.assertEqual(as_captured.returncode, 2, as_captured.stderr)
        self.assertIn("no readable id", as_captured.stderr)
        # An operator told to fix this by editing the prompt would be chasing
        # a field this host encrypts. The block has to name task_name.
        self.assertIn("task_name", as_captured.stderr)
        self.assertNotIn("in the prompt", as_captured.stderr)

        # The wire form, because this host rejects a task_name outside
        # [a-z0-9_] with "agent_name must use only lowercase letters, digits,
        # and underscores". `T-001` is unsendable here, so a fixture that used
        # it would be testing a dispatch Codex would never make.
        tagged = self.run_adapter(
            "dispatch-guard", live_dispatch(self.project, "t_001")
        )
        self.assertEqual(tagged.returncode, 0, tagged.stderr)
        with open(
            os.path.join(
                self.project, ".agent-guild", "state", "log", "dispatches.log"
            ),
            encoding="utf-8",
        ) as stream:
            # Canonical on the way out. Task files, verdict stems, and this
            # log all key on `T-001`, and only the wire spelling differs.
            self.assertIn("T-001", stream.read())

        # A host that lifts the charset later shouldn't need a gate change.
        canonical = self.run_adapter(
            "dispatch-guard", live_dispatch(self.project, "T-001")
        )
        self.assertEqual(canonical.returncode, 0, canonical.stderr)

    def test_task_name_carries_audit_and_audition_ids_too(self):
        auditor = live_dispatch(self.project, "con_audit")
        auditor["tool_input"]["agent_type"] = "auditor"
        allowed = self.run_adapter("dispatch-guard", auditor)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        with open(
            os.path.join(
                self.project, ".agent-guild", "state", "log", "dispatches.log"
            ),
            encoding="utf-8",
        ) as stream:
            self.assertIn("CON-audit", stream.read())

        # An auditor id on a worker is the same mismatch the prompt path
        # rejects; arriving in a structured field doesn't excuse it.
        misrouted = live_dispatch(self.project, "con_audit")
        blocked = self.run_adapter("dispatch-guard", misrouted)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("Task-ID", blocked.stderr)

        # An audition runs outside the lifecycle: no task file, no CON-audit.
        audition = live_dispatch(self.project, "a_001")
        audition["tool_input"]["agent_type"] = "worker-bulk"
        tryout = self.run_adapter("dispatch-guard", audition)
        self.assertEqual(tryout.returncode, 0, tryout.stderr)

    def test_task_name_is_no_longer_read_as_the_agent_name(self):
        # agent_type is the only source for the agent. task_name once backed
        # it up, which would now route a dispatch by its id whenever that id
        # happened to read like an agent name.
        payload = live_dispatch(self.project, "worker-standard")
        del payload["tool_input"]["agent_type"]
        result = self.run_adapter("dispatch-guard", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.project,
                    ".agent-guild",
                    "state",
                    "log",
                    "dispatches.log",
                )
            )
        )

    def test_sibling_namespaced_tool_is_not_folded_into_a_dispatch(self):
        # `collaborationwait_agent` rides the same namespace as the dispatch
        # tool. Suffix recovery must not claim it, or the gate would block a
        # tool it has no business seeing.
        payload = codex_input(
            "PreToolUse",
            self.project,
            tool_name="collaborationwait_agent",
            tool_use_id="call_JYbdZh1I2GPvoWUSecH8pTOk",
            tool_input={"timeout_ms": 60000},
        )
        result = self.run_adapter("dispatch-guard", payload)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("expected Agent or spawn_agent", result.stderr)

    def test_dispatch_accepts_documented_structured_items_input(self):
        write_task(self.project, "T-056", status="checking")
        payload = codex_input(
            "PreToolUse",
            self.project,
            tool_name="spawn_agent",
            tool_use_id="call-dispatch-2",
            tool_input={
                "agent_type": "checker-deterministic",
                "items": [
                    {"type": "text", "text": "Task-ID: T-056"},
                    {"type": "text", "text": "Check it."},
                ],
            },
        )
        result = self.run_adapter("dispatch-guard", payload)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_codex_courier_dispatch_uses_the_claude_lane_sentinel(self):
        write_task(
            self.project,
            "T-054",
            status="checking",
            checker="checker-judgment",
        )
        exhausted = os.path.join(
            self.project, ".agent-guild", "state", "exhausted"
        )
        os.makedirs(exhausted)
        open(os.path.join(exhausted, "claude"), "w").close()
        payload = codex_input(
            "PreToolUse",
            self.project,
            tool_name="spawn_agent",
            tool_use_id="call-courier",
            tool_input={
                "agent_type": "checker-courier",
                "message": "Task-ID: T-054\nGet a second opinion.",
            },
        )

        blocked = self.run_adapter("dispatch-guard", payload)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("'claude' lane is exhausted", blocked.stderr)
        self.assertNotIn("exhausted/codex", blocked.stderr)

        os.remove(os.path.join(exhausted, "claude"))
        allowed = self.run_adapter("dispatch-guard", payload)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        with open(
            os.path.join(
                self.project,
                ".agent-guild",
                "state",
                "log",
                "dispatches.log",
            ),
            encoding="utf-8",
        ) as stream:
            dispatch_log = stream.read()
        self.assertIn("| claude\n", dispatch_log)

    def test_apply_patch_checks_every_target_and_scopes_subagents(self):
        write_task(self.project, "T-056", status="assigned")
        patch = """*** Begin Patch
*** Update File: .agent-guild/state/tasks/T-056.md
@@
-status: pending
+status: assigned
*** Update File: README.md
@@
-old
+new
*** End Patch
"""
        payload = codex_input(
            "PreToolUse",
            self.project,
            tool_name="apply_patch",
            tool_use_id="call-patch-1",
            tool_input={"command": patch},
        )
        blocked = self.run_adapter("orchestrator-write-guard", payload)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("README.md", blocked.stderr)

        worker_payload = {
            **payload,
            "agent_id": "019fa0c0-worker",
            "agent_type": "worker-standard",
        }
        allowed = self.run_adapter(
            "orchestrator-write-guard", worker_payload
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_apply_patch_fails_closed_when_no_target_can_be_read(self):
        write_task(self.project, "T-056", status="assigned")
        payload = codex_input(
            "PreToolUse",
            self.project,
            tool_name="apply_patch",
            tool_use_id="call-patch-bad",
            tool_input={"command": "*** Begin Patch\nnot a patch\n*** End Patch"},
        )
        result = self.run_adapter("orchestrator-write-guard", payload)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("could not identify", result.stderr)

    def test_unreadable_patch_still_obeys_the_shared_no_job_exemption(self):
        payload = codex_input(
            "PreToolUse",
            self.project,
            tool_name="apply_patch",
            tool_use_id="call-patch-no-job",
            tool_input={"command": "*** Begin Patch\nnot a patch\n*** End Patch"},
        )
        result = self.run_adapter("orchestrator-write-guard", payload)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_subagent_stop_reads_current_codex_response_item_transcript(self):
        write_task(self.project, "T-056", status="assigned")
        transcript = codex_transcript(
            self.project,
            "Task-ID: T-056\nImplement the adapter.",
            "response_item",
        )
        payload = codex_input(
            "SubagentStop",
            self.project,
            transcript_path="/parent/rollout.jsonl",
            agent_transcript_path=transcript,
            agent_id="019fa0c0-worker",
            agent_type="worker-standard",
            stop_hook_active=False,
            last_assistant_message="Done.",
        )
        blocked = self.run_adapter("subagent-return", payload)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("Protocol incomplete for T-056", blocked.stderr)

        write_task(
            self.project,
            "T-056",
            status="needs-check",
            artifacts="[README.md]",
        )
        allowed = self.run_adapter("subagent-return", payload)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_subagent_stop_handles_codex_event_message_transcript(self):
        write_task(
            self.project,
            "T-056",
            status="needs-check",
            artifacts="[README.md]",
        )
        transcript = codex_transcript(
            self.project, "Task-ID: T-056\nImplement it.", "event_msg"
        )
        payload = codex_input(
            "SubagentStop",
            self.project,
            agent_transcript_path=transcript,
            agent_id="019fa0c0-worker",
            agent_type="worker-standard",
            stop_hook_active=False,
            last_assistant_message="Done.",
        )
        result = self.run_adapter("subagent-return", payload)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_return_recovers_the_id_from_an_encrypted_dispatch_record(self):
        # PROVISIONAL, and the test can't fix that: SubagentStop has never
        # been observed firing on a Codex host (#68), so this proves the
        # parser against the transcript shape rather than against a real
        # return. What it does rule out is the parser going looking for the
        # id in the one field the host encrypts.
        write_task(
            self.project,
            "T-056",
            status="needs-check",
            artifacts="[README.md]",
        )
        transcript = codex_transcript(
            self.project, "t_056", "function_call"
        )
        payload = codex_input(
            "SubagentStop",
            self.project,
            agent_transcript_path=transcript,
            agent_id="019fa0c0-worker",
            agent_type="worker-standard",
            stop_hook_active=False,
            last_assistant_message="Done.",
        )
        result = self.run_adapter("subagent-return", payload)
        self.assertEqual(result.returncode, 0, result.stderr)

        # A task_name in no guild namespace is not an id, and inventing one
        # from it would silently attach a return to the wrong task.
        unlabelled = codex_transcript(
            self.project, "lifecycle_payload", "function_call"
        )
        blind = self.run_adapter(
            "subagent-return",
            {**payload, "agent_transcript_path": unlabelled},
        )
        self.assertEqual(blind.returncode, 0, blind.stderr)
        self.assertIn("could not identify", blind.stderr)

    def test_return_gate_reads_the_parent_transcript_not_the_child(self):
        # A live SubagentStop payload carries both transcripts. Only the
        # parent's holds the id, in the spawn_agent `task_name` argument; the
        # child sees an encrypted dispatch message and a role prompt that
        # happens to mention an Audit-ID. Reading the child attributed a
        # worker's return to CON-audit on a real host.
        write_task(
            self.project,
            "T-001",
            status="needs-check",
            artifacts="[README.md]",
        )
        parent = codex_transcript(self.project, "t_001", "function_call")
        child = codex_transcript(
            self.project, "Audit-ID: CON-audit", "response_item"
        )
        payload = codex_input(
            "SubagentStop",
            self.project,
            transcript_path=parent,
            agent_transcript_path=child,
            agent_id="019fb613-e38e-7482-bedf-0ef115aa4fc8",
            agent_type="worker-standard",
            stop_hook_active=False,
            last_assistant_message="ACKNOWLEDGED",
        )

        result = self.run_adapter("subagent-return", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("could not identify", result.stderr)
        self.assertNotIn("CON-audit", result.stderr)

        # A host that sends only the child transcript still works. The
        # fallback is what keeps the earlier Codex shapes readable.
        fallback = self.run_adapter(
            "subagent-return",
            {**payload, "transcript_path": "/nonexistent/parent.jsonl"},
        )
        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        self.assertIn("could not identify", fallback.stderr)

    def test_read_only_in_family_checker_returns_its_verdict_inline(self):
        # Issue #68. A Codex in-family checker is sandbox read-only, so the
        # file-backed branch demanded the one thing its sandbox forbids. It
        # returns the verdict instead and the parent persists it, which is
        # the handoff checker-courier has always had and these never got.
        seed_verdict_toolchain(self.project)
        write_task(
            self.project,
            "T-054",
            status="checking",
            checker="checker-deterministic",
        )
        transcript = codex_transcript(self.project, "Task-ID: T-054")

        def payload(message):
            return codex_input(
                "SubagentStop",
                self.project,
                agent_transcript_path=transcript,
                agent_id="019fb613-checker",
                agent_type="checker-deterministic",
                stop_hook_active=False,
                last_assistant_message=message,
            )

        def verdict(**overrides):
            body = {
                "task_id": "T-054",
                "checker": "checker-deterministic",
                "vendor": "openai",
                "model": "gpt-5.6-terra",
                "verdict": "pass",
                "findings": [],
                "timestamp": "2026-07-31T02:49:44Z",
                "duration_ms": 1200,
                "cost_usd": None,
            }
            body.update(overrides)
            return "AGENT_GUILD_VERDICT\n" + json.dumps(body)

        allowed = self.run_adapter("subagent-return", payload(verdict()))
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

        # The gate validates but never writes. Persisting is the parent's
        # job, the same split the courier lane already uses.
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.project,
                    ".agent-guild",
                    "state",
                    "verdicts",
                    "T-054-sonnet-r0.json",
                )
            )
        )

        # A verdict naming another task would be persisted against the wrong
        # stem, which is worse than refusing it.
        blocked = self.run_adapter(
            "subagent-return", payload(verdict(task_id="T-999"))
        )
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("task_id", blocked.stderr)

        blocked = self.run_adapter(
            "subagent-return", payload(verdict(checker="checker-judgment"))
        )
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("checker", blocked.stderr)

        blocked = self.run_adapter(
            "subagent-return", payload(verdict(verdict="maybe"))
        )
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("does not validate", blocked.stderr)

        # No marker at all is the common failure, so the block has to name
        # the route rather than repeat "write the file you cannot write".
        blocked = self.run_adapter("subagent-return", payload("Done."))
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("AGENT_GUILD_VERDICT", blocked.stderr)
        self.assertNotIn("Write a conforming verdict per", blocked.stderr)

    def test_read_only_codex_courier_returns_a_validated_claude_outcome(self):
        seed_verdict_toolchain(self.project)
        write_task(
            self.project,
            "T-054",
            status="checking",
            checker="checker-judgment",
        )
        transcript = codex_transcript(
            self.project,
            "Task-ID: T-054\nGet a second opinion.",
        )
        payload = codex_input(
            "SubagentStop",
            self.project,
            agent_transcript_path=transcript,
            agent_id="019fa0c0-courier",
            agent_type="checker-courier",
            stop_hook_active=False,
            last_assistant_message=courier_outcome("T-054"),
        )

        result = self.run_adapter("subagent-return", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.project,
                    ".agent-guild",
                    "state",
                    "verdicts",
                    "T-054-sonnet-r0-claude.json",
                )
            )
        )

        wrong_task = {
            **payload,
            "last_assistant_message": courier_outcome("T-999"),
        }
        blocked = self.run_adapter("subagent-return", wrong_task)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("task_id", blocked.stderr)

        marker, raw = courier_outcome("T-054").split("\n", 1)
        malformed_metrics = json.loads(raw)
        malformed_metrics["ledger"]["duration_ms"] = "fast"
        bad_ledger = {
            **payload,
            "last_assistant_message": (
                marker + "\n" + json.dumps(malformed_metrics)
            ),
        }
        blocked = self.run_adapter("subagent-return", bad_ledger)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("ledger.duration_ms", blocked.stderr)

    def test_read_only_codex_courier_quota_return_precedes_parent_writes(self):
        write_task(
            self.project,
            "T-054",
            status="checking",
            checker="checker-deterministic",
        )
        transcript = codex_transcript(
            self.project,
            "Task-ID: T-054\nGet a second opinion.",
        )
        payload = codex_input(
            "SubagentStop",
            self.project,
            agent_transcript_path=transcript,
            agent_id="019fa0c0-courier",
            agent_type="checker-courier",
            stop_hook_active=False,
            last_assistant_message=courier_outcome(
                "T-054", status="quota"
            ),
        )

        result = self.run_adapter("subagent-return", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.project,
                    ".agent-guild",
                    "state",
                    "exhausted",
                    "claude",
                )
            )
        )

    def test_unknown_future_transcript_shape_fails_loud_without_hanging(self):
        write_task(self.project, "T-056", status="assigned")
        transcript = codex_transcript(
            self.project, "Task-ID: T-056", "future"
        )
        payload = codex_input(
            "SubagentStop",
            self.project,
            agent_transcript_path=transcript,
            agent_id="019fa0c0-worker",
            agent_type="worker-standard",
            stop_hook_active=False,
        )
        result = self.run_adapter("subagent-return", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("could not identify", result.stderr)
        self.assertIn("instead of hanging", result.stderr)

    def test_stop_gate_blocks_root_but_not_subagent_turns(self):
        write_task(self.project, "T-056", status="pending")
        payload = codex_input(
            "Stop",
            self.project,
            stop_hook_active=False,
            last_assistant_message="Done.",
        )
        blocked = self.run_adapter("stop-gate", payload)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("T-056 [pending]", blocked.stderr)

        subagent = {
            **payload,
            "agent_id": "019fa0c0-worker",
            "agent_type": "worker-standard",
        }
        allowed = self.run_adapter("stop-gate", subagent)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_session_start_emits_codex_init_nudge_from_nested_cwd(self):
        nested = os.path.join(self.project, "packages", "demo")
        os.makedirs(nested)
        payload = codex_input(
            "SessionStart",
            nested,
            turn_id=None,
            source="startup",
        )
        result = self.run_adapter(
            "session-nudge", payload, "agent-guild:"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("$agent-guild:init", result.stdout)
        self.assertNotIn("/agent-guild:init", result.stdout)

    def test_wrong_event_for_gate_fails_closed(self):
        payload = codex_input(
            "Stop",
            self.project,
            stop_hook_active=False,
        )
        result = self.run_adapter("dispatch-guard", payload)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("expected PreToolUse", result.stderr)

    def test_wrong_tool_for_pre_tool_gate_fails_closed(self):
        payload = codex_input(
            "PreToolUse",
            self.project,
            tool_name="Bash",
            tool_use_id="call-wrong-tool",
            tool_input={"command": "true"},
        )
        result = self.run_adapter("dispatch-guard", payload)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("expected Agent or spawn_agent", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
