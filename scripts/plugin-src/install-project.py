#!/usr/bin/env python3
"""Install Agent Guild's project payload through one host-aware engine.

The package builder places this file under `project-template/` in both host
packages. Plugin init skills call it without `--project-skills`; the direct
Codex IDE bootstrap adds that flag to install repo-local `.agents/skills`.
All writes stay inside the explicitly supplied project root.
"""
import os
import shutil
import sys
import tempfile


CLAUDE_SECTION_START = "<!-- agent-guild:claude:start -->"
CLAUDE_SECTION_END = "<!-- agent-guild:claude:end -->"
CODEX_SECTION_START = "<!-- agent-guild:codex:start -->"
CODEX_SECTION_END = "<!-- agent-guild:codex:end -->"
SKILL_PREFIX_TOKEN = "{{AGENT_GUILD_SKILL_PREFIX}}"
STATE_DIRS = ("tasks", "verdicts", "disputes", "notes", "log")

TEMPLATE_ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE_ROOT = os.path.dirname(TEMPLATE_ROOT)
SOURCE_PAYLOAD = os.path.join(TEMPLATE_ROOT, ".agent-guild")
SOURCE_AGENTS = os.path.join(TEMPLATE_ROOT, ".codex", "agents")
SOURCE_CODEX_SECTION = os.path.join(
    TEMPLATE_ROOT, "AGENTS.agent-guild.md"
)
SOURCE_SKILLS = os.path.join(PACKAGE_ROOT, "skills")

CLAUDE_SECTION = (
    f"{CLAUDE_SECTION_START}\n"
    "<!-- Added by the Agent Guild project installer. -->\n"
    "@.agent-guild/CLAUDE.md\n"
    f"{CLAUDE_SECTION_END}\n"
)


class InstallError(Exception):
    """A safe, user-actionable installation failure."""


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as error:
        raise InstallError(f"cannot read {path}: {error}") from error


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


def _bounded_update(existing, section, start_marker, end_marker, label):
    starts = existing.count(start_marker)
    ends = existing.count(end_marker)
    if starts == ends == 0:
        separator = ""
        if existing:
            separator = "\n" if existing.endswith("\n") else "\n\n"
        return existing + separator + section
    if starts != 1 or ends != 1:
        raise InstallError(
            f"{label} has malformed Agent Guild ownership markers: "
            f"found {starts} start marker(s) and {ends} end marker(s)"
        )
    start = existing.index(start_marker)
    end = existing.index(end_marker)
    if end < start:
        raise InstallError(
            f"{label} has malformed Agent Guild ownership markers: "
            "the end marker appears before the start marker"
        )
    end += len(end_marker)
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


def _relative_files(root):
    found = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(
            name
            for name in directories
            if name not in {"__pycache__", "node_modules"}
        )
        for name in sorted(files):
            if name == "package-lock.json":
                continue
            found.append(
                os.path.relpath(os.path.join(current, name), root)
            )
    return found


def _validate_source_tree(root, label):
    if not os.path.isdir(root):
        raise InstallError(f"packaged {label} is missing: {root}")
    files = _relative_files(root)
    if not files:
        raise InstallError(f"packaged {label} is empty: {root}")
    return files


def _gitignore_update(existing):
    covered = False
    for raw in existing.splitlines():
        pattern = raw.strip()
        if not pattern or pattern.startswith("#") or pattern.startswith("!"):
            continue
        normalized = pattern.lstrip("/")
        if normalized in {
            ".agent-guild/",
            ".agent-guild/**",
            ".agent-guild/state/",
            ".agent-guild/state/**",
        }:
            covered = True
            break
    if covered:
        return existing
    separator = "" if not existing or existing.endswith("\n") else "\n"
    return existing + separator + ".agent-guild/state/\n"


def _codex_section(project_skills):
    section = _read(SOURCE_CODEX_SECTION)
    if (
        section.count(CODEX_SECTION_START) != 1
        or section.count(CODEX_SECTION_END) != 1
        or section.index(CODEX_SECTION_END)
        < section.index(CODEX_SECTION_START)
    ):
        raise InstallError(
            "packaged AGENTS.md section has malformed markers: "
            f"{SOURCE_CODEX_SECTION}"
        )
    if SKILL_PREFIX_TOKEN not in section:
        raise InstallError(
            "packaged AGENTS.md section is missing its skill-prefix token"
        )
    prefix = "" if project_skills else "agent-guild:"
    return section.replace(SKILL_PREFIX_TOKEN, prefix)


def _preflight_payload(project_root, payload_files):
    conflicts = []
    target_root = os.path.join(project_root, ".agent-guild")
    _require_beneath(project_root, target_root)
    for relative in payload_files:
        source = os.path.join(SOURCE_PAYLOAD, relative)
        target = os.path.join(target_root, relative)
        _require_beneath(target_root, target)
        if os.path.exists(target) and not _same_file(source, target):
            conflicts.append(os.path.join(".agent-guild", relative))
    if conflicts:
        raise InstallError(
            "local Agent Guild payload differs; preserved without writes: "
            + ", ".join(conflicts)
        )


def _copy_missing(source_root, target_root, relative_files):
    copied = unchanged = 0
    for relative in relative_files:
        source = os.path.join(source_root, relative)
        target = os.path.join(target_root, relative)
        if os.path.exists(target):
            unchanged += 1
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied, unchanged


def _copy_owned(source_root, target_root, relative_files):
    updated = unchanged = 0
    for relative in relative_files:
        source = os.path.join(source_root, relative)
        target = os.path.join(target_root, relative)
        _require_beneath(target_root, target)
        if _same_file(source, target):
            unchanged += 1
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target)
        updated += 1
    return updated, unchanged


def install(host, project_root, project_skills=False):
    if host not in {"claude", "codex"}:
        raise InstallError(f"unsupported host: {host}")
    if project_skills and host != "codex":
        raise InstallError("--project-skills is only valid for the Codex host")

    project_root = os.path.abspath(project_root)
    if not os.path.isdir(project_root):
        raise InstallError(
            f"project root is not a directory: {project_root}"
        )

    payload_files = _validate_source_tree(
        SOURCE_PAYLOAD, "project payload"
    )
    agent_files = []
    skill_files = []
    if host == "codex":
        agent_files = _validate_source_tree(
            SOURCE_AGENTS, "Codex agent roster"
        )
        if project_skills:
            skill_files = [
                relative
                for relative in _validate_source_tree(
                    SOURCE_SKILLS, "workflow skills"
                )
                if relative
                != os.path.join(
                    "audition", "results", "results.jsonl"
                )
            ]

    guidance_name = "CLAUDE.md" if host == "claude" else "AGENTS.md"
    guidance_path = os.path.join(project_root, guidance_name)
    gitignore_path = os.path.join(project_root, ".gitignore")
    for path in (guidance_path, gitignore_path):
        _require_beneath(project_root, path)

    existing_guidance = (
        _read(guidance_path) if os.path.exists(guidance_path) else ""
    )
    if host == "claude":
        if (
            "@.agent-guild/CLAUDE.md" in existing_guidance
            and CLAUDE_SECTION_START not in existing_guidance
            and CLAUDE_SECTION_END not in existing_guidance
        ):
            updated_guidance = existing_guidance
        else:
            updated_guidance = _bounded_update(
                existing_guidance,
                CLAUDE_SECTION,
                CLAUDE_SECTION_START,
                CLAUDE_SECTION_END,
                guidance_name,
            )
    else:
        section = _codex_section(project_skills)
        updated_guidance = _bounded_update(
            existing_guidance,
            section,
            CODEX_SECTION_START,
            CODEX_SECTION_END,
            guidance_name,
        )

    existing_gitignore = (
        _read(gitignore_path) if os.path.exists(gitignore_path) else ""
    )
    updated_gitignore = _gitignore_update(existing_gitignore)

    double_registration = False
    if host == "claude":
        claude_settings = os.path.join(
            project_root, ".claude", "settings.json"
        )
        if os.path.isfile(claude_settings):
            settings_text = _read(claude_settings)
            double_registration = any(
                name in settings_text
                for name in (
                    "dispatch-guard.py",
                    "orchestrator-write-guard.py",
                    "stop-gate.py",
                    "subagent-return.py",
                )
            )

    _preflight_payload(project_root, payload_files)
    target_payload = os.path.join(project_root, ".agent-guild")

    target_agents = os.path.join(project_root, ".codex", "agents")
    if host == "codex":
        _require_beneath(project_root, target_agents)
        for relative in agent_files:
            _require_beneath(
                target_agents, os.path.join(target_agents, relative)
            )
    target_skills = os.path.join(project_root, ".agents", "skills")
    if project_skills:
        _require_beneath(project_root, target_skills)
        for relative in skill_files:
            _require_beneath(
                target_skills, os.path.join(target_skills, relative)
            )

    state_root = os.path.join(target_payload, "state")
    for name in STATE_DIRS:
        _require_beneath(
            target_payload,
            os.path.join(state_root, name, ".gitkeep"),
        )

    payload_copied, payload_unchanged = _copy_missing(
        SOURCE_PAYLOAD, target_payload, payload_files
    )
    agents_updated = agents_unchanged = 0
    if host == "codex":
        agents_updated, agents_unchanged = _copy_owned(
            SOURCE_AGENTS, target_agents, agent_files
        )
    skills_updated = skills_unchanged = 0
    if project_skills:
        skills_updated, skills_unchanged = _copy_owned(
            SOURCE_SKILLS, target_skills, skill_files
        )

    for name in STATE_DIRS:
        keep = os.path.join(state_root, name, ".gitkeep")
        if not os.path.exists(keep):
            _atomic_write(keep, "")

    guidance_changed = updated_guidance != existing_guidance
    if guidance_changed:
        _atomic_write(guidance_path, updated_guidance)
    gitignore_changed = updated_gitignore != existing_gitignore
    if gitignore_changed:
        _atomic_write(gitignore_path, updated_gitignore)

    if double_registration:
        print(
            "WARNING: agent-guild gates are registered twice in the "
            "Claude plugin and .claude/settings.json; every gate will fire "
            "twice. Remove the project settings hook block or disable the "
            "plugin locally—never add or rewrite settings automatically."
        )
    print(
        "OK: Agent Guild project install "
        f"(host={host}; payload={payload_copied} updated/"
        f"{payload_unchanged} unchanged; agents={agents_updated} updated/"
        f"{agents_unchanged} unchanged; skills={skills_updated} updated/"
        f"{skills_unchanged} unchanged; "
        f"{guidance_name}={'updated' if guidance_changed else 'unchanged'}; "
        f".gitignore={'updated' if gitignore_changed else 'unchanged'})"
    )


def main(argv):
    if len(argv) not in {3, 4}:
        sys.stderr.write(
            "usage: install.py {claude|codex} PROJECT_ROOT "
            "[--project-skills]\n"
        )
        return 2
    host = argv[1]
    project_root = argv[2]
    project_skills = len(argv) == 4 and argv[3] == "--project-skills"
    if len(argv) == 4 and not project_skills:
        sys.stderr.write(
            "usage: install.py {claude|codex} PROJECT_ROOT "
            "[--project-skills]\n"
        )
        return 2
    try:
        install(host, project_root, project_skills)
    except (InstallError, OSError) as error:
        sys.stderr.write(f"install.py: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
