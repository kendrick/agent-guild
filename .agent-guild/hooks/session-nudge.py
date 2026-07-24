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
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

STATE_SUBDIRS = ("tasks", "verdicts", "disputes", "notes", "log")
IMPORT_LINE = "@.agent-guild/CLAUDE.md"


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
