#!/usr/bin/env python3
"""SessionStart(startup): nudge a half-installed project toward /agent-guild:init.

Installing the plugin only gets a project the user-scope half of the kit. The
per-project half—the CLAUDE.md import line, the state directories, the
constitution/spec workflow—has to be run once per repo. A project that never
ran it just silently doesn't have working gates; nothing else would tell the
user. This hook is that one nudge: on session start, print a single line
pointing at /agent-guild:init when the project looks like it meant to use the
guild but didn't finish setting it up.

Zero-evidence silence beats discoverability: with no .agent-guild/ directory
at all, we say nothing, even though a one-line "hey, agent-guild is available"
would help someone who's never heard of it. A user-scope plugin install runs
this hook in EVERY project the user opens, guild or not, so the only safe
default is silence until the project itself shows intent (a .agent-guild/
directory). Nagging unrelated repos on every session start would make the
plugin something people disable, not adopt.

Double-registration is the other thing worth a nudge for. The guild ships two
ways—copy-in (gates registered in the project's .claude/settings.json) and
plugin (gates from this file's own hooks.json)—and having both active in one
project makes every gate fire twice. The copy-in settings.json registers no
SessionStart hook, so when the plugin is enabled, this plugin-rooted instance
is the only nudge that ever runs; detection is structurally one-sided, and no
dedupe machinery is needed. A project-rooted instance (copied straight into
.agent-guild/hooks/) never runs this check at all—it has no way to tell a
copy-in it's part of from a copy-in left behind by mistake, and doesn't need
to, since the plugin-rooted instance already covers the pairing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

STATE_SUBDIRS = ("tasks", "verdicts", "disputes", "notes", "log")
IMPORT_LINE = "@.agent-guild/CLAUDE.md"

# The load-bearing name: if a copy-in .claude/settings.json wires the guild's
# gates at all, dispatch-guard.py is among them (it's the PreToolUse entry
# every dispatch goes through), so grepping for it alone is enough without
# enumerating every sibling gate script.
GUILD_GATE_SIGNATURE = "dispatch-guard.py"

DOUBLE_REGISTRATION_WARNING = (
    "agent-guild: this project's gates are registered twice (this plugin's "
    "hooks.json AND .claude/settings.json)—every gate fires twice, and "
    "the stall counter reaches STALLED after two real blocks instead of "
    "three. Fix it by removing the guild hooks block from "
    ".claude/settings.json (migrating copy-in to plugin), or disable the "
    "plugin for this project by hand-editing .claude/settings.local.json to "
    'add "enabledPlugins": {"agent-guild@agent-guild": false} (or `claude '
    "plugin disable agent-guild@agent-guild --scope local` if you've "
    "verified that's safe in your setup)—never --scope project, which "
    "writes the tracked settings.json."
)


def _running_from_plugin_root(here, root):
    """True when THIS FILE's own path sits outside the project tree—i.e.
    we're executing from a plugin's cache directory
    (~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/hooks/...)
    rather than a copy-in at <root>/.agent-guild/hooks/session-nudge.py. The
    copy-in always lands under root, so "not under root" is both necessary
    and sufficient—no need to hardcode the plugins-cache shape, which
    Claude Code doesn't publish as a stable path. Takes explicit paths
    (rather than reading __file__ itself) so a test can exercise both roots
    without faking a real plugin install."""
    here = os.path.realpath(here)
    root = os.path.realpath(root)
    try:
        return os.path.commonpath([here, root]) != root
    except ValueError:
        # Different drives or otherwise incomparable paths: definitely not
        # under root.
        return True


def _copy_in_gate_registered(settings_path):
    """True if the project's .claude/settings.json wires the guild's gates
    itself—the copy-in half of the footgun. A missing or malformed file is
    silently fine: this is a nudge, not a gate, and it must never crash on a
    project's arbitrary settings file."""
    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False
    return GUILD_GATE_SIGNATURE in json.dumps(data.get("hooks", {}))


def _missing_pieces(root):
    """Repo-relative names of whatever's missing for a finished per-project
    install, in a stable order so the message is deterministic."""
    missing = [f"state/{sub}" for sub in STATE_SUBDIRS
               if not os.path.isdir(_lib.state_path(sub))]

    claude_md = os.path.join(root, "CLAUDE.md")
    if not os.path.isfile(claude_md):
        missing.append("CLAUDE.md")
    else:
        with open(claude_md, encoding="utf-8") as f:
            if IMPORT_LINE not in f.read():
                missing.append(f"CLAUDE.md {IMPORT_LINE} import line")
    return missing


def main(data):
    # Intended scope: SessionStart doesn't fire per-subagent, so there's nothing
    # to no-op—but were that ever to change, this nudge is read-only and harmless
    # wherever it runs.
    root = _lib.project_dir()

    # Double-registration check runs first, independent of the partial-init
    # check below: it reads evidence from the PROJECT's own settings.json,
    # not this instance's .agent-guild/ completeness, and only the
    # plugin-rooted instance ever needs to run it (see the module docstring).
    if _running_from_plugin_root(os.path.abspath(__file__), root):
        settings_path = os.path.join(root, ".claude", "settings.json")
        if _copy_in_gate_registered(settings_path):
            print(DOUBLE_REGISTRATION_WARNING)
            return 0

    # No .agent-guild/ at all: the project has shown no intent to use the
    # guild, so say nothing (see the module docstring's asymmetry note).
    if not os.path.isdir(os.path.join(root, ".agent-guild")):
        return 0

    missing = _missing_pieces(root)
    if not missing:
        return 0

    print(
        "agent-guild: this project looks partially initialized (missing "
        f"{', '.join(missing)}) — run /agent-guild:init to finish the install."
    )
    return 0


if __name__ == "__main__":
    _lib.run("session-nudge", main)
