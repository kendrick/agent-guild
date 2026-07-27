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
        self.assertIn("has no id line", blocked.stderr)

        tagged = {
            **untagged,
            "tool_input": {
                **untagged["tool_input"],
                "message": "Task-ID: T-056\nCheck the implementation.",
            },
        }
        allowed = self.run_adapter("dispatch-guard", tagged)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

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
