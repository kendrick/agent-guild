#!/usr/bin/env python3
"""Translate Codex lifecycle-hook JSON into the shared Guild gate contract.

This file owns host representation only. The four enforcement policies remain
in dispatch-guard.py, orchestrator-write-guard.py, subagent-return.py, and
stop-gate.py; this adapter maps Codex field names and preserves their process
exit codes and output verbatim.
"""
import json
import os
import re
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _lib  # noqa: E402

GATES = {
    "dispatch-guard": ("PreToolUse", "dispatch-guard.py"),
    "orchestrator-write-guard": (
        "PreToolUse",
        "orchestrator-write-guard.py",
    ),
    "session-nudge": ("SessionStart", "session-nudge.py"),
    "stop-gate": ("Stop", "stop-gate.py"),
    "subagent-return": ("SubagentStop", "subagent-return.py"),
}
PATCH_TARGET_RE = re.compile(
    r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$",
    re.MULTILINE,
)
TIER_NAMES = {"haiku", "sonnet", "opus", "fable"}
DISPATCH_TOOLS = ("Agent", "spawn_agent")
# Codex can also hand new work to an agent that already exists. That reaches
# the same gate as a spawn, but carries none of what a spawn carries: no agent
# type, no readable message, only the target's agent path (#77).
FOLLOWUP_TOOLS = ("followup_task",)
WRITE_TOOLS = ("Edit", "Write", "apply_patch")
KNOWN_TOOLS = DISPATCH_TOOLS + FOLLOWUP_TOOLS + WRITE_TOOLS


class AdapterError(Exception):
    """A malformed or incompatible Codex hook request."""


def _block(message):
    sys.stderr.write(f"codex-hook-adapter: {message.rstrip()}\n")
    return 2


def _read_input():
    try:
        value = json.loads(sys.stdin.read())
    except json.JSONDecodeError as error:
        raise AdapterError(f"hook stdin is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise AdapterError("hook stdin must be a JSON object")
    return value


def _project_root(cwd):
    if not isinstance(cwd, str) or not cwd.strip():
        raise AdapterError("hook input has no usable cwd")
    current = os.path.realpath(cwd)
    if not os.path.isdir(current):
        raise AdapterError(f"hook cwd is not a directory: {cwd!r}")

    while True:
        if os.path.isdir(os.path.join(current, ".agent-guild")):
            return current
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.realpath(cwd)


def _paused(project):
    try:
        return os.path.exists(
            os.path.join(project, ".agent-guild", "state", "PAUSED")
        )
    except OSError:
        return False


def _text_fragments(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_text_fragments(item))
        return result
    if not isinstance(value, dict):
        return []

    result = []
    for key in ("text", "input_text", "message", "prompt", "content"):
        if key in value:
            result.extend(_text_fragments(value[key]))
    return result


def _dispatch_input(data):
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        raise AdapterError("PreToolUse dispatch has no object tool_input")
    if _bare_tool_name(data.get("tool_name")) in FOLLOWUP_TOOLS:
        # `target` is an agent path, bare (`t_001`) or rooted
        # (`/root/t_001/t_001`); both shapes came off a live host. It's the
        # only field here in the clear, so it's all the gate gets. Handed over
        # raw—recovering a guild id from it is gate policy, not host
        # representation.
        target = tool_input.get("target")
        if not isinstance(target, str) or not target.strip():
            raise AdapterError(
                "followup_task names no readable target, so nothing can be "
                "checked about who it re-tasks"
            )
        return {**data, "tool_input": {"followup_target": target.strip()}}
    # `task_name` carries the guild id (#71), so it can't also back-stop the
    # agent name here. A dispatch naming no agent is better off failing the
    # guild-membership test than being handed an id to match against
    # GUILD_AGENTS.
    agent = (
        tool_input.get("agent_type")
        or tool_input.get("subagent_type")
        or ""
    )
    prompt_parts = []
    if tool_input.get("message") is not None:
        prompt_parts.extend(_text_fragments(tool_input["message"]))
    if tool_input.get("items") is not None:
        prompt_parts.extend(_text_fragments(tool_input["items"]))
    if not prompt_parts and tool_input.get("prompt") is not None:
        prompt_parts.extend(_text_fragments(tool_input["prompt"]))

    model = tool_input.get("model")
    mapped = {
        "subagent_type": agent,
        "prompt": "\n".join(part for part in prompt_parts if part),
    }
    # The shared task tier names are host-neutral scheduling labels. A Codex
    # model slug is not one of those labels, so the shared gate should use the
    # selected Guild role's default tier unless an explicit tier label arrived.
    if isinstance(model, str) and model.strip().lower() in TIER_NAMES:
        mapped["model"] = model.strip().lower()
    # The one field that survives both host boundaries in the clear. Passed
    # through verbatim rather than parsed here: sorting a bare id into its
    # namespace is gate policy, and this file owns host representation only.
    task_name = tool_input.get("task_name")
    if isinstance(task_name, str) and task_name.strip():
        mapped["dispatch_id"] = task_name.strip()
    return {**data, "tool_input": mapped}


def _patch_targets(data):
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        raise AdapterError("PreToolUse write has no object tool_input")
    direct = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(direct, str) and direct.strip():
        return [direct.strip()]

    command = tool_input.get("command")
    if not isinstance(command, str):
        return []
    targets = []
    for match in PATCH_TARGET_RE.finditer(command):
        target = match.group(1).strip()
        if target and target not in targets:
            targets.append(target)
    return targets


def _run_gate(script, data):
    process = subprocess.run(
        [sys.executable, os.path.join(HERE, script)],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if process.stdout:
        sys.stdout.write(process.stdout)
    if process.stderr:
        sys.stderr.write(process.stderr)
    if process.returncode in {0, 2}:
        return process.returncode
    return _block(
        f"{script} exited {process.returncode}; treating the gate failure "
        "as a block"
    )


def _run_write_gate(script, data):
    targets = _patch_targets(data)
    if data.get("agent_id"):
        mapped = {
            **data,
            "tool_input": {"file_path": targets[0] if targets else ""},
        }
        return _run_gate(script, mapped)
    if not targets:
        if _lib.no_job_active():
            return _run_gate(
                script, {**data, "tool_input": {"file_path": ""}}
            )
        return _block(
            "could not identify any target path in apply_patch tool_input"
        )
    for target in targets:
        mapped = {**data, "tool_input": {"file_path": target}}
        return_code = _run_gate(script, mapped)
        if return_code != 0:
            return return_code
    return 0


def _mapped_input(gate, data, skill_prefix):
    data = {**data, "hook_host": "codex"}
    if gate == "dispatch-guard":
        return _dispatch_input(data)
    if gate == "subagent-return":
        # The id lives in the PARENT's transcript, in the `task_name` argument
        # of the spawn_agent call. The child never sees it: its dispatch
        # message is encrypted, which is the whole reason #71 moved the id to
        # a field. Reading the child instead finds whatever `Audit-ID:` string
        # happens to sit in the role instructions, which is how a live probe
        # got a worker's return attributed to CON-audit.
        #
        # Falls back to the child when the parent path is unusable, which is
        # what a host that only supplies `agent_transcript_path` looks like.
        parent = data.get("transcript_path")
        child = data.get("agent_transcript_path")
        usable = (
            parent
            if isinstance(parent, str) and os.path.isfile(parent)
            else child
        )
        return {**data, "transcript_path": usable or parent}
    if gate == "session-nudge":
        return {
            **data,
            "hook_host": "codex",
            "agent_guild_skill_prefix": skill_prefix,
        }
    return data


def _bare_tool_name(value):
    if not isinstance(value, str):
        return ""
    name = re.split(r"(?:__|[.:])", value)[-1]
    if name in KNOWN_TOOLS:
        return name
    # Codex glues a tool's namespace to its name with no separator at all:
    # `collaboration` + `spawn_agent` arrives as `collaborationspawn_agent`.
    # The session transcript keeps the two as distinct fields, so this is a
    # presentation quirk of the hook layer rather than a rename, and the
    # longest known suffix recovers the real tool (#71). The registered
    # matchers bound what reaches here, so this can't quietly fold an
    # unrelated tool into a guild-relevant one.
    for known in sorted(KNOWN_TOOLS, key=len, reverse=True):
        if name.endswith(known):
            return known
    return name


def main(argv):
    if len(argv) not in {2, 3} or argv[1] not in GATES:
        names = "|".join(sorted(GATES))
        return _block(f"usage: codex-hook-adapter.py {{{names}}} [prefix]")
    gate = argv[1]
    skill_prefix = argv[2] if len(argv) == 3 else ""

    try:
        data = _read_input()
        project = _project_root(data.get("cwd"))
        os.environ["CLAUDE_PROJECT_DIR"] = project
        if _paused(project):
            return 0

        expected_event, script = GATES[gate]
        actual_event = data.get("hook_event_name")
        if actual_event != expected_event:
            raise AdapterError(
                f"{gate} expected {expected_event}, got "
                f"{actual_event or 'no hook_event_name'}"
            )
        tool_name = _bare_tool_name(data.get("tool_name"))
        if gate == "dispatch-guard" and tool_name not in (
            DISPATCH_TOOLS + FOLLOWUP_TOOLS
        ):
            raise AdapterError(
                f"dispatch-guard expected Agent, spawn_agent, or "
                f"followup_task, got {data.get('tool_name') or 'no tool_name'}"
            )
        if gate == "orchestrator-write-guard" and tool_name not in WRITE_TOOLS:
            raise AdapterError(
                "orchestrator-write-guard expected Edit, Write, or "
                f"apply_patch, got {data.get('tool_name') or 'no tool_name'}"
            )
        if gate == "orchestrator-write-guard":
            return _run_write_gate(script, data)
        return _run_gate(
            script, _mapped_input(gate, data, skill_prefix)
        )
    except AdapterError as error:
        return _block(str(error))
    except BaseException as error:
        return _block(f"unexpected adapter failure: {error}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
