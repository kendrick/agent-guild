#!/usr/bin/env python3
"""Behavioral tests for Codex hook packaging and project installation.

Run: python3 scripts/test_codex_hooks_packaging.py
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS_DIR)
BUILD_PATH = os.path.join(SCRIPTS_DIR, "build-plugin.py")
BUILD_SPEC = importlib.util.spec_from_file_location(
    "build_plugin_codex_hooks", BUILD_PATH
)
BUILD = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD)

MANAGED_SIGNATURE = "codex-hook-adapter.py"
EXPECTED_SCRIPTS = {
    "_lib.py",
    "codex-hook-adapter.py",
    "dispatch-guard.py",
    "orchestrator-write-guard.py",
    "session-nudge.py",
    "stop-gate.py",
    "subagent-return.py",
    "test_codex_adapter.py",
    "test_hooks.py",
}


def read_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def handler_commands(config):
    return [
        handler["command"]
        for groups in config["hooks"].values()
        for group in groups
        for handler in group.get("hooks", [])
        if handler.get("type") == "command"
    ]


def managed_handler_count(config):
    return sum(
        MANAGED_SIGNATURE in command for command in handler_commands(config)
    )


class CodexHookPackagingTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(
            prefix="ag-codex-hook-package-"
        )
        self.codex_out = os.path.join(self.tempdir.name, "codex")
        BUILD.build_codex(self.codex_out)
        self.installer = os.path.join(
            self.codex_out, "project-template", "install.py"
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def run_installer(self, project, project_skills=True):
        command = [sys.executable, self.installer, "codex", project]
        if project_skills:
            command.append("--project-skills")
        return subprocess.run(command, capture_output=True, text=True)

    def test_plugin_and_ide_configs_register_the_same_shared_gates(self):
        plugin_hooks = os.path.join(self.codex_out, "hooks")
        project_hooks = os.path.join(
            self.codex_out,
            "project-template",
            ".agent-guild",
            "hooks",
        )
        self.assertEqual(set(os.listdir(plugin_hooks)), EXPECTED_SCRIPTS | {
            "hooks.json"
        })
        self.assertEqual(set(os.listdir(project_hooks)), EXPECTED_SCRIPTS)
        for name in EXPECTED_SCRIPTS:
            with open(
                os.path.join(plugin_hooks, name), "rb"
            ) as plugin_stream:
                plugin_bytes = plugin_stream.read()
            with open(
                os.path.join(project_hooks, name), "rb"
            ) as project_stream:
                self.assertEqual(
                    plugin_bytes,
                    project_stream.read(),
                    f"{name} drifted between plugin and IDE payloads",
                )

        plugin_config = read_json(
            os.path.join(plugin_hooks, "hooks.json")
        )
        project_config = read_json(
            os.path.join(
                self.codex_out,
                "project-template",
                ".codex",
                "hooks.json",
            )
        )
        self.assertEqual(
            set(plugin_config["hooks"]),
            {
                "SessionStart",
                "PreToolUse",
                "SubagentStop",
                "Stop",
            },
        )
        self.assertEqual(
            set(plugin_config["hooks"]), set(project_config["hooks"])
        )
        self.assertEqual(managed_handler_count(plugin_config), 5)
        self.assertEqual(managed_handler_count(project_config), 5)
        self.assertTrue(
            all("${PLUGIN_ROOT}" in command for command in handler_commands(
                plugin_config
            ))
        )
        self.assertTrue(
            all("${PLUGIN_ROOT}" not in command for command in handler_commands(
                project_config
            ))
        )

        pre_tool_groups = plugin_config["hooks"]["PreToolUse"]
        self.assertEqual(
            {group["matcher"] for group in pre_tool_groups},
            {BUILD.CODEX_DISPATCH_MATCHER, BUILD.CODEX_WRITE_MATCHER},
        )

    def test_dispatch_matcher_covers_the_namespaced_tool_name(self):
        """The registered matcher is the whole gate on a Codex host: when it
        misses, dispatch-guard is silently absent rather than blocking, which
        is how v0.5.1 shipped an unenforced host (#71). Codex anchors its
        matchers, since `Agent|spawn_agent` never fired against the
        concatenated name while `.*` did, so these assert under fullmatch,
        the strictest of the plausible semantics."""
        dispatch = re.compile(BUILD.CODEX_DISPATCH_MATCHER)
        for name in ("collaborationspawn_agent", "spawn_agent", "Agent"):
            self.assertTrue(dispatch.fullmatch(name), name)
        # A sibling in the same namespace. Matching it would drag a tool the
        # gate can't read into a gate that fails closed.
        for name in ("collaborationwait_agent", "Bash", "spawn_agents"):
            self.assertIsNone(dispatch.fullmatch(name), name)

        write = re.compile(BUILD.CODEX_WRITE_MATCHER)
        # Unnamespaced in every capture, unlike the dispatch tool.
        for name in ("apply_patch", "Edit", "Write"):
            self.assertTrue(write.fullmatch(name), name)

    def test_ide_install_merges_only_guild_handlers_and_is_idempotent(self):
        project = os.path.join(self.tempdir.name, "project")
        os.makedirs(os.path.join(project, ".codex"))
        hooks_path = os.path.join(project, ".codex", "hooks.json")
        unrelated = {
            "schemaVersion": 1,
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 tools/my-hook.py",
                                "timeout": 7,
                            }
                        ],
                    }
                ]
            },
        }
        with open(hooks_path, "w", encoding="utf-8") as stream:
            json.dump(unrelated, stream, indent=2)
            stream.write("\n")

        first = self.run_installer(project)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("/hooks", first.stdout)
        self.assertIn("not automatically trusted", first.stdout)
        installed = read_json(hooks_path)
        self.assertEqual(installed["schemaVersion"], 1)
        self.assertIn(
            "python3 tools/my-hook.py", handler_commands(installed)
        )
        self.assertEqual(managed_handler_count(installed), 5)

        with open(hooks_path, "rb") as stream:
            first_bytes = stream.read()
        second = self.run_installer(project)
        self.assertEqual(second.returncode, 0, second.stderr)
        with open(hooks_path, "rb") as stream:
            self.assertEqual(first_bytes, stream.read())

        installed_adapter = os.path.join(
            project,
            ".agent-guild",
            "hooks",
            "codex-hook-adapter.py",
        )
        with open(installed_adapter, "w", encoding="utf-8") as stream:
            stream.write("# stale managed hook\n")
        refreshed = self.run_installer(project)
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
        with open(installed_adapter, encoding="utf-8") as stream:
            self.assertNotEqual(stream.read(), "# stale managed hook\n")

    def test_plugin_mode_does_not_duplicate_hooks_into_the_project(self):
        project = os.path.join(self.tempdir.name, "plugin-project")
        os.makedirs(project)
        result = self.run_installer(project, project_skills=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/hooks", result.stdout)
        self.assertIn("not automatically trusted", result.stdout)
        self.assertFalse(
            os.path.exists(os.path.join(project, ".codex", "hooks.json"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(project, ".agent-guild", "hooks")
            )
        )

    def test_existing_top_level_fields_without_hooks_are_preserved(self):
        project = os.path.join(self.tempdir.name, "top-level-project")
        os.makedirs(os.path.join(project, ".codex"))
        hooks_path = os.path.join(project, ".codex", "hooks.json")
        with open(hooks_path, "w", encoding="utf-8") as stream:
            json.dump({"schemaVersion": 1, "projectNote": "keep"}, stream)
            stream.write("\n")

        result = self.run_installer(project)
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = read_json(hooks_path)
        self.assertEqual(installed["schemaVersion"], 1)
        self.assertEqual(installed["projectNote"], "keep")
        self.assertEqual(managed_handler_count(installed), 5)

    def test_malformed_existing_hooks_fail_before_any_project_write(self):
        project = os.path.join(self.tempdir.name, "malformed-project")
        os.makedirs(os.path.join(project, ".codex"))
        hooks_path = os.path.join(project, ".codex", "hooks.json")
        with open(hooks_path, "w", encoding="utf-8") as stream:
            stream.write("{not json\n")

        result = self.run_installer(project)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hooks.json", result.stderr)
        self.assertFalse(
            os.path.exists(os.path.join(project, ".agent-guild"))
        )
        with open(hooks_path, encoding="utf-8") as stream:
            self.assertEqual(stream.read(), "{not json\n")

    def test_setup_docs_require_explicit_review_and_trust(self):
        path = os.path.join(ROOT, "docs", "building.md")
        with open(path, encoding="utf-8") as stream:
            docs = stream.read()
        codex_section = docs.split("## Build The Codex Package", 1)[1]
        self.assertIn("`/hooks`", codex_section)
        self.assertIn("review", codex_section.lower())
        self.assertIn("trust", codex_section.lower())
        self.assertIn("not automatically trusted", codex_section.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
