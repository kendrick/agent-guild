#!/usr/bin/env python3
"""Install Agent Guild's project payload through one host-aware engine.

The package builder places this file under `project-template/` in both host
packages. Plugin init skills call it without `--project-skills`; the direct
Codex IDE bootstrap adds that flag to install repo-local `.agents/skills`.
All writes stay inside the explicitly supplied project root.
"""
import hashlib
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
PROVENANCE_NAME = "provenance.json"
CLAUDE_MANIFEST = os.path.join(PACKAGE_ROOT, ".claude-plugin", "plugin.json")
CODEX_MANIFEST = os.path.join(PACKAGE_ROOT, ".codex-plugin", "plugin.json")

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
    # The `_require_beneath` symlink-redirect guard has to run over every
    # payload path before any write happens anywhere in install() — this is
    # the pass that proves it, ahead of the agents/skills/hooks/state guards
    # below it. #183's own conflict handling now lives in `_sync_payload`,
    # which needs the provenance record loaded first to tell an edit from a
    # stale-but-clean file, so this pass no longer decides what a conflict is.
    target_root = os.path.join(project_root, ".agent-guild")
    _require_beneath(project_root, target_root)
    for relative in payload_files:
        target = os.path.join(target_root, relative)
        _require_beneath(target_root, target)


def _sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def _package_version(host):
    """The version field of THIS package's own manifest, read at run time.

    A copy of the package carries its own manifest beside project-template/,
    so a copy whose manifest reads a version nothing else does reports that
    version — the only way to tell a real lookup from a compiled-in string.
    """
    manifest_path = CLAUDE_MANIFEST if host == "claude" else CODEX_MANIFEST
    manifest = _json_object(_read(manifest_path), manifest_path)
    version = manifest.get("version")
    if not isinstance(version, str):
        raise InstallError(f"{manifest_path} has no string version")
    return version


def _load_provenance(path):
    """The prior run's `files` map, or {} for a pre-provenance project.

    A project with no record adopts what matches current source instead of
    trusting nothing; `_sync_payload` reads {} the same way whether the
    record is genuinely absent or this is a brand-new project with no
    payload on disk yet either.
    """
    if not os.path.exists(path):
        return {}
    record = _json_object(_read(path), path)
    files = record.get("files")
    if not isinstance(files, dict):
        raise InstallError(f"{path} must contain an object at files")
    return files


def _sync_payload(source_root, target_root, relative_files, recorded_files):
    """Bring each payload file to current source, governed by its record.

    Per file, per #183's ruling:
      - missing on disk: copy from source and record its hash (net-new file,
        or a file this project never had).
      - on disk, with a recorded hash that matches the bytes on disk: clean
        against its record, so upgrade to current source regardless of
        whether the stamp trails the plugin's — the record decides, not the
        stamp — and restamp its hash.
      - on disk, with a recorded hash that differs from the bytes on disk:
        a real local edit. Preserve the bytes, carry the recorded hash
        forward untouched, and report the path.
      - on disk, with no recorded hash (pre-provenance project): adopt it at
        its on-disk hash when the bytes already match source; otherwise
        preserve it and record no entry at all, so a later run can tell
        "shipped this way" from "reviewed and kept anyway".
    Returns (new_files, updated, unchanged, preserved, conflicts): new_files
    is the files map for the record this run writes, and conflicts is the
    sorted list of payload paths (".agent-guild/..." style) this run refused
    to overwrite.
    """
    new_files = {}
    updated = unchanged = preserved = 0
    conflicts = []
    for relative in relative_files:
        source = os.path.join(source_root, relative)
        target = os.path.join(target_root, relative)
        _require_beneath(target_root, target)
        key = os.path.join(".agent-guild", relative).replace(os.sep, "/")
        if not os.path.exists(target):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(source, target)
            new_files[key] = _sha256_file(target)
            updated += 1
            continue
        recorded_hash = recorded_files.get(key)
        if recorded_hash is None:
            if _same_file(source, target):
                new_files[key] = _sha256_file(target)
                unchanged += 1
            else:
                preserved += 1
                conflicts.append(key)
            continue
        if _sha256_file(target) == recorded_hash:
            if _same_file(source, target):
                new_files[key] = recorded_hash
                unchanged += 1
            else:
                shutil.copy2(source, target)
                new_files[key] = _sha256_file(target)
                updated += 1
        else:
            new_files[key] = recorded_hash
            preserved += 1
            conflicts.append(key)
    return new_files, updated, unchanged, preserved, conflicts


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

    # #183: read at run time, not compiled in, so a copy of the package
    # whose manifest carries a version nothing else does stamps that
    # version. Read up front so a missing/malformed manifest fails before
    # any write, matching every other packaged-input validation here.
    current_version = _package_version(host)

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
    prov_path = os.path.join(target_payload, PROVENANCE_NAME)
    # {} reads the same whether this is a brand-new project (nothing on disk
    # yet, so every file takes `_sync_payload`'s "missing" branch) or a
    # pre-provenance one (payload already on disk, so it adopts what
    # matches and preserves-and-reports the rest).
    recorded_files = _load_provenance(prov_path)

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

    (
        new_payload_files,
        payload_copied,
        payload_unchanged,
        payload_preserved,
        payload_conflicts,
    ) = _sync_payload(SOURCE_PAYLOAD, target_payload, payload_files, recorded_files)
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

    # Every install writes the record, on both hosts, so the next run always
    # has a stamp and a per-file hash to check against rather than falling
    # back to adoption forever.
    _atomic_write(
        prov_path,
        json.dumps(
            {"version": current_version, "files": new_payload_files},
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

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
    if payload_conflicts:
        print(
            "WARNING: local Agent Guild payload differs; preserved "
            "without writes: " + ", ".join(payload_conflicts)
        )
    payload_summary = (
        f"payload={payload_copied} updated/{payload_unchanged} unchanged/"
        f"{payload_preserved} preserved"
    )
    print(
        "OK: Agent Guild project install "
        f"(host={host}; {payload_summary}; "
        f"agents={agents_updated} updated/"
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
