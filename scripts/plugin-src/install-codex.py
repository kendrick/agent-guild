#!/usr/bin/env python3
"""Install Agent Guild's generated Codex roster into one project.

The package builder places this script beside `.codex/agents/` and the bounded
`AGENTS.agent-guild.md` section it consumes. It writes only project-local
Agent Guild-owned paths; personal and global Codex configuration are outside
its contract.
"""
import os
import shutil
import sys
import tempfile


SECTION_START = "<!-- agent-guild:codex:start -->"
SECTION_END = "<!-- agent-guild:codex:end -->"
TEMPLATE_ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE_AGENTS = os.path.join(TEMPLATE_ROOT, ".codex", "agents")
SOURCE_SECTION = os.path.join(TEMPLATE_ROOT, "AGENTS.agent-guild.md")


class InstallError(Exception):
    """A safe, user-actionable bootstrap failure."""


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as error:
        raise InstallError(f"cannot read {path}: {error}") from error


def _bounded_update(existing, section):
    starts = existing.count(SECTION_START)
    ends = existing.count(SECTION_END)
    if starts == ends == 0:
        separator = ""
        if existing:
            separator = "\n" if existing.endswith("\n") else "\n\n"
        return existing + separator + section
    if starts != 1 or ends != 1:
        raise InstallError(
            "AGENTS.md has malformed Agent Guild ownership markers: "
            f"found {starts} start marker(s) and {ends} end marker(s)"
        )
    start = existing.index(SECTION_START)
    end = existing.index(SECTION_END)
    if end < start:
        raise InstallError(
            "AGENTS.md has malformed Agent Guild ownership markers: "
            "the end marker appears before the start marker"
        )
    end += len(SECTION_END)
    return existing[:start] + section.rstrip("\n") + existing[end:]


def _atomic_write(path, content):
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    current_mode = None
    if os.path.exists(path):
        current_mode = os.stat(path).st_mode & 0o777
    handle, temporary = tempfile.mkstemp(
        prefix=".agent-guild-", dir=parent, text=True
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write(content)
        if current_mode is not None:
            os.chmod(temporary, current_mode)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _same_file(first, second):
    try:
        with open(first, "rb") as left, open(second, "rb") as right:
            return left.read() == right.read()
    except OSError:
        return False


def _require_beneath(root, path):
    resolved_root = os.path.realpath(root)
    resolved_path = os.path.realpath(path)
    try:
        is_beneath = (
            os.path.commonpath((resolved_root, resolved_path))
            == resolved_root
        )
    except ValueError:
        is_beneath = False
    if not is_beneath:
        raise InstallError(
            f"refusing path redirected outside {root}: {path}"
        )


def _sources():
    if not os.path.isdir(SOURCE_AGENTS):
        raise InstallError(
            f"generated Codex agent template is missing: {SOURCE_AGENTS}"
        )
    agents = sorted(
        name for name in os.listdir(SOURCE_AGENTS) if name.endswith(".toml")
    )
    if not agents:
        raise InstallError(
            f"generated Codex agent template is empty: {SOURCE_AGENTS}"
        )
    section = _read(SOURCE_SECTION)
    if (
        section.count(SECTION_START) != 1
        or section.count(SECTION_END) != 1
        or section.index(SECTION_END) < section.index(SECTION_START)
    ):
        raise InstallError(
            f"generated AGENTS.md section has malformed markers: "
            f"{SOURCE_SECTION}"
        )
    return agents, section


def install(project_root):
    project_root = os.path.abspath(project_root)
    if not os.path.isdir(project_root):
        raise InstallError(
            f"project root is not a directory: {project_root}"
        )

    agents, section = _sources()
    agents_md = os.path.join(project_root, "AGENTS.md")
    existing_agents_md = _read(agents_md) if os.path.exists(agents_md) else ""
    updated_agents_md = _bounded_update(existing_agents_md, section)

    target_agents = os.path.join(project_root, ".codex", "agents")
    _require_beneath(project_root, target_agents)
    copied = unchanged = 0
    for name in agents:
        source = os.path.join(SOURCE_AGENTS, name)
        target = os.path.join(target_agents, name)
        _require_beneath(target_agents, target)
        if _same_file(source, target):
            unchanged += 1
            continue
        os.makedirs(target_agents, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1

    agents_md_changed = updated_agents_md != existing_agents_md
    if agents_md_changed:
        _atomic_write(agents_md, updated_agents_md)

    print(
        "OK: Agent Guild Codex bootstrap "
        f"({copied} agent file(s) updated, {unchanged} unchanged; "
        f"AGENTS.md {'updated' if agents_md_changed else 'unchanged'})"
    )


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(
            "usage: install-codex.py PROJECT_ROOT\n"
        )
        return 2
    try:
        install(argv[1])
    except InstallError as error:
        sys.stderr.write(f"install-codex.py: {error}\n")
        return 1
    except OSError as error:
        sys.stderr.write(f"install-codex.py: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
