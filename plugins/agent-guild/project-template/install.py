#!/usr/bin/env python3
"""Install Agent Guild's project payload through one host-aware engine.

The package builder places this file under `project-template/` in both host
packages. Plugin init skills call it without `--project-skills`; the direct
Codex IDE bootstrap adds that flag to install repo-local `.agents/skills`.
All writes stay inside the explicitly supplied project root.
"""
import json
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
SOURCE_CODEX_HOOKS = os.path.join(SOURCE_PAYLOAD, "hooks")
SOURCE_CODEX_HOOK_CONFIG = os.path.join(
    TEMPLATE_ROOT, ".codex", "hooks.json"
)
SOURCE_CODEX_SECTION = os.path.join(
    TEMPLATE_ROOT, "AGENTS.agent-guild.md"
)
SOURCE_SKILLS = os.path.join(PACKAGE_ROOT, "skills")
CODEX_HOOK_SIGNATURE = "codex-hook-adapter.py"

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


def _json_object(text, path):
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise InstallError(f"cannot parse {path}: {error}") from error
    if not isinstance(value, dict):
        raise InstallError(f"{path} must contain a JSON object")
    return value


def _validate_hook_groups(config, path, allow_missing=False):
    hooks = config.get("hooks")
    if hooks is None and allow_missing and "hooks" not in config:
        hooks = {}
        config["hooks"] = hooks
    if not isinstance(hooks, dict):
        raise InstallError(f"{path} must contain an object at hooks")
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise InstallError(
                f"{path} hooks.{event} must contain a list"
            )
        for index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise InstallError(
                    f"{path} hooks.{event}[{index}] must be an object"
                )
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                raise InstallError(
                    f"{path} hooks.{event}[{index}].hooks must be a list"
                )
            if not all(isinstance(handler, dict) for handler in handlers):
                raise InstallError(
                    f"{path} hooks.{event}[{index}].hooks must contain "
                    "objects"
                )
    return hooks


def _is_guild_hook(handler):
    command = handler.get("command")
    return (
        handler.get("type") == "command"
        and isinstance(command, str)
        and CODEX_HOOK_SIGNATURE in command
    )


def _codex_hooks_update(existing, existing_path):
    """Replace only Agent Guild handlers, preserving every unrelated entry."""
    source = _json_object(
        _read(SOURCE_CODEX_HOOK_CONFIG), SOURCE_CODEX_HOOK_CONFIG
    )
    source_hooks = _validate_hook_groups(
        source, SOURCE_CODEX_HOOK_CONFIG
    )
    if existing:
        merged = _json_object(existing, existing_path)
        existing_hooks = _validate_hook_groups(
            merged, existing_path, allow_missing=True
        )
    else:
        merged = {"hooks": {}}
        existing_hooks = merged["hooks"]

    for event, groups in list(existing_hooks.items()):
        retained_groups = []
        for group in groups:
            had_managed_handler = any(
                _is_guild_hook(handler) for handler in group["hooks"]
            )
            retained_handlers = [
                handler
                for handler in group["hooks"]
                if not _is_guild_hook(handler)
            ]
            if not had_managed_handler:
                retained_groups.append(group)
            elif retained_handlers:
                retained = dict(group)
                retained["hooks"] = retained_handlers
                retained_groups.append(retained)
        existing_hooks[event] = retained_groups

    for event, groups in source_hooks.items():
        existing_hooks.setdefault(event, []).extend(groups)
    return json.dumps(merged, indent=2) + "\n"


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
    codex_hook_files = []
    hook_prefix = "hooks" + os.sep
    if host == "codex":
        codex_hook_files = [
            relative[len(hook_prefix):]
            for relative in payload_files
            if relative.startswith(hook_prefix)
        ]
        payload_files = [
            relative
            for relative in payload_files
            if not relative.startswith(hook_prefix)
        ]
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
            if not codex_hook_files:
                raise InstallError(
                    f"packaged Codex hooks are empty: {SOURCE_CODEX_HOOKS}"
                )

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

    codex_hooks_path = os.path.join(
        project_root, ".codex", "hooks.json"
    )
    existing_codex_hooks = updated_codex_hooks = ""
    if host == "codex" and project_skills:
        _require_beneath(project_root, codex_hooks_path)
        existing_codex_hooks = (
            _read(codex_hooks_path)
            if os.path.exists(codex_hooks_path)
            else ""
        )
        updated_codex_hooks = _codex_hooks_update(
            existing_codex_hooks, codex_hooks_path
        )

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
    target_hooks = os.path.join(target_payload, "hooks")
    if host == "codex" and project_skills:
        _require_beneath(project_root, target_hooks)
        for relative in codex_hook_files:
            _require_beneath(
                target_hooks, os.path.join(target_hooks, relative)
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
    hooks_updated = hooks_unchanged = 0
    if host == "codex" and project_skills:
        hooks_updated, hooks_unchanged = _copy_owned(
            SOURCE_CODEX_HOOKS, target_hooks, codex_hook_files
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
    codex_hooks_changed = (
        host == "codex"
        and project_skills
        and updated_codex_hooks != existing_codex_hooks
    )
    if codex_hooks_changed:
        _atomic_write(codex_hooks_path, updated_codex_hooks)

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
        f"{skills_unchanged} unchanged; hooks={hooks_updated} updated/"
        f"{hooks_unchanged} unchanged; "
        f"{guidance_name}={'updated' if guidance_changed else 'unchanged'}; "
        f".gitignore={'updated' if gitignore_changed else 'unchanged'})"
    )
    if host == "codex":
        print(
            "NEXT: Codex hooks are not automatically trusted. Open `/hooks`, "
            "review the exact Agent Guild definitions, and trust them "
            "explicitly before relying on the gates."
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
