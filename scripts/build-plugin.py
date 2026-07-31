#!/usr/bin/env python3
"""Build the Agent Guild's Claude and Codex plugin distributions.

Shared behavior lives in `guild-core/` and the host-neutral `.agent-guild/`
payload. Thin adapter metadata supplies host representation; the repository's
Claude dogfood and both packages are generated views of those sources.

Modes:
    build-plugin.py              sync both published packages and marketplaces
    build-plugin.py --target claude --out DIR
                                 build only the Claude package
    build-plugin.py --target codex --out DIR
                                 build only the Codex package
    build-plugin.py --target all --out DIR
                                 build both as children of DIR
    build-plugin.py --check      verify shared-core wrappers, generated output,
                                  marketplaces, and Claude validation

Exit codes: 0 success; 1 a build or check step failed (message on stderr
names the actual problem, not a bare "failed").

Stdlib only, so the kit stays copy-in portable -- see
.agent-guild/scripts/check-provenance.py and new-task.py for the same rule.
"""
import argparse
import filecmp
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE_DIR = os.path.join(ROOT, ".claude")
GUILD_DIR = os.path.join(ROOT, ".agent-guild")
CORE_DIR = os.path.join(ROOT, "guild-core")
PLUGIN_SRC_MANIFEST = os.path.join(ROOT, "scripts", "plugin-src", "plugin.json")
MARKETPLACE_METADATA_PATH = os.path.join(
    ROOT, "scripts", "plugin-src", "marketplace.json"
)
CLAUDE_ADAPTER_PATH = os.path.join(
    ROOT, "scripts", "plugin-src", "adapters", "claude.json"
)
CODEX_ADAPTER_PATH = os.path.join(
    ROOT, "scripts", "plugin-src", "adapters", "codex.json"
)
INSTALLER_PATH = os.path.join(
    ROOT, "scripts", "plugin-src", "install-project.py"
)
PLUGIN_SRC_README = os.path.join(ROOT, "docs", "plugin-readme.md")
CHANGELOG_PATH = os.path.join(ROOT, "CHANGELOG.md")
DEFAULT_OUT = os.path.join(ROOT, "plugin")
DEFAULT_CODEX_OUT = os.path.join(ROOT, "plugins", "agent-guild")
CLAUDE_MARKETPLACE_PATH = os.path.join(
    ROOT, ".claude-plugin", "marketplace.json"
)
CODEX_MARKETPLACE_PATH = os.path.join(
    ROOT, ".agents", "plugins", "marketplace.json"
)

GUILD_AGENTS = [
    "auditor",
    "checker-courier",
    "checker-deterministic",
    "checker-judgment",
    "hydrator",
    "worker-bulk",
    "worker-craft",
    "worker-standard",
    "working-memory-synchronizer",
]

CLAUDE_PLUGIN_AGENTS = [
    "auditor",
    "checker-deterministic",
    "checker-judgment",
    "worker-bulk",
    "worker-craft",
    "worker-standard",
]

# The lifecycle skills always ship. Optional components join automatically
# when their source exists, so the source inventory stays the one inclusion
# boundary for both host targets.
GUILD_SKILLS = [
    "constitution",
    "decompose",
    "retrospective",
    "audition",
    "job",
    "hydrate-discover",
    "hydrate-draft",
    "hydrate-extract",
    "hydrate-propose",
    "hydrate-reconcile",
    "update-working-memory",
]
OPTIONAL_SKILLS = ["init"]

GUILD_HOOKS = [
    "_lib.py",
    "dispatch-guard.py",
    "orchestrator-write-guard.py",
    "stop-gate.py",
    "subagent-return.py",
    "test_hooks.py",
]
OPTIONAL_HOOKS = ["session-nudge.py"]
CODEX_HOOKS = ["codex-hook-adapter.py", "test_codex_adapter.py"]

# check-a11y.mjs self-bootstraps node_modules/ and a lockfile on first run
# (.agent-guild/scripts/package.json), and Python leaves __pycache__ behind
# next to any module it imports. .gitignore already keeps all three out of
# the repo itself; a build that swept them in anyway would ship whatever
# happened to be sitting on the machine that ran it, not this repo's sources.
_IGNORE_BUILD_BYPRODUCTS = shutil.ignore_patterns(
    "__pycache__", "node_modules", "package-lock.json"
)

# Bare invocation -> namespaced form. Applied only to plugin-bound prose (the
# packaged SKILL.md bodies and the packaged project-template CLAUDE.md) --
# never to file paths. "/decompose" reads identically whether it's the
# invocation in "`/decompose`" or the path segment in "skills/decompose/", so
# telling them apart is apply_namespacing's whole job; see its docstring.
NAMESPACE_MAP = {
    "constitution": "agent-guild:constitution",
    "decompose": "agent-guild:decompose",
    "retrospective": "agent-guild:retrospective",
    "audition": "agent-guild:audition",
    "job": "agent-guild:job",
    "init": "agent-guild:init",
}


class BuildError(Exception):
    """Raised for any build-time problem; str(e) is the full diagnostic."""


def _guard_out_dir(out_dir):
    """Refuse to build into a read-only source tree. The build must never
    modify its inputs, so a careless --out pointed at .claude/,
    .agent-guild/, or guild-core/ is a mistake to catch up front, not a git
    diff to notice after the builder removes the target."""
    for protected in (CLAUDE_DIR, GUILD_DIR, CORE_DIR):
        if out_dir == protected or out_dir.startswith(protected + os.sep):
            raise BuildError(
                f"--out {out_dir} is inside a read-only source tree "
                f"({protected}); refusing to build there"
            )


def _load_json(path, label):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError(f"cannot read {label} {path}: {error}") from error


def _render_frontmatter(lines, body):
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body


def _adapter_frontmatter(kind, name, target):
    adapter = _load_json(CLAUDE_ADAPTER_PATH, "Claude adapter")
    try:
        lines = list(adapter[kind][name])
    except KeyError as error:
        raise BuildError(
            f"Claude adapter has no {kind} metadata for {name}"
        ) from error
    if target == "codex":
        codex = _load_json(CODEX_ADAPTER_PATH, "Codex adapter")
        overrides = codex.get("skill_frontmatter_overrides", {}).get(name, {})
        for key, value in overrides.items():
            prefix = f"{key}:"
            matching = [
                i for i, line in enumerate(lines) if line.startswith(prefix)
            ]
            replacement = f"{key}: {value}"
            if matching:
                lines[matching[0]] = replacement
            else:
                lines.append(replacement)
    return lines


def _adapter_skill_suffix(name, target):
    adapter_path = (
        CLAUDE_ADAPTER_PATH if target == "claude" else CODEX_ADAPTER_PATH
    )
    adapter = _load_json(adapter_path, f"{target.title()} adapter")
    return adapter.get("skill_body_suffixes", {}).get(name, "")


def _adapter_agent_suffix(name, target):
    adapter_path = (
        CLAUDE_ADAPTER_PATH if target == "claude" else CODEX_ADAPTER_PATH
    )
    adapter = _load_json(adapter_path, f"{target.title()} adapter")
    return adapter.get("agent_body_suffixes", {}).get(name, "")


def copy_agents(
    out_dir, core_dir=CORE_DIR, names=GUILD_AGENTS, target="claude"
):
    """Render Claude agent wrappers around host-neutral role behavior."""
    src_dir = os.path.join(core_dir, "roles")
    dst_dir = os.path.join(out_dir, "agents")
    os.makedirs(dst_dir, exist_ok=True)
    for name in names:
        src = os.path.join(src_dir, f"{name}.md")
        if not os.path.isfile(src):
            raise BuildError(f"missing shared role source: {src}")
        with open(src, encoding="utf-8") as f:
            body = f.read()
        body += _adapter_agent_suffix(name, target)
        rendered = _render_frontmatter(
            _adapter_frontmatter("agents", name, "claude"), body
        )
        with open(
            os.path.join(dst_dir, f"{name}.md"), "w", encoding="utf-8"
        ) as f:
            f.write(rendered)


def copy_skills(
    out_dir, core_dir=CORE_DIR, target="claude", seed_runtime=True
):
    """Render target skill wrappers around shared workflow bodies and assets.

    Returns the list of skill names actually shipped, so callers that only
    care about what's really in the output (hooks.json, namespacing) don't
    have to re-derive the include-when-present logic themselves."""
    src_dir = os.path.join(core_dir, "workflows")
    dst_dir = os.path.join(out_dir, "skills")
    os.makedirs(dst_dir, exist_ok=True)
    shipped = list(GUILD_SKILLS)
    for name in OPTIONAL_SKILLS:
        if os.path.isdir(os.path.join(src_dir, name)):
            shipped.append(name)
    for name in shipped:
        src = os.path.join(src_dir, name)
        if not os.path.isdir(src):
            raise BuildError(f"missing shared workflow source: {src}")
        shutil.copytree(
            src, os.path.join(dst_dir, name), ignore=_IGNORE_BUILD_BYPRODUCTS
        )
        skill_path = os.path.join(dst_dir, name, "SKILL.md")
        with open(skill_path, encoding="utf-8") as f:
            body = f.read()
        body += _adapter_skill_suffix(name, target)
        rendered = _render_frontmatter(
            _adapter_frontmatter("skills", name, target), body
        )
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        if name == "audition" and seed_runtime:
            results_dir = os.path.join(dst_dir, name, "results")
            os.makedirs(results_dir, exist_ok=True)
            with open(
                os.path.join(results_dir, "results.jsonl"),
                "w",
                encoding="utf-8",
            ):
                pass
    return shipped


_CODEX_READ_ONLY_PROTOCOL = """

## Codex Host Boundary

This project-scoped agent runs in a read-only sandbox. Do not write or edit any project, artifact, task, state, ledger, or verdict file—even where the shared role protocol above tells a Claude-hosted agent to write one. Return the intended output path and complete proposed file content to the parent orchestrator instead. The parent owns persistence after independently checking the return. When a shared verdict contract names the Claude host identity, report `vendor: openai` and your configured Codex model instead. This host boundary takes precedence over every write instruction above.
"""


def generate_codex_agents(out_dir, core_dir=CORE_DIR):
    """Render project-scoped Codex agent TOML from shared role prompts."""
    codex_adapter = _load_json(CODEX_ADAPTER_PATH, "Codex adapter")
    configured = codex_adapter.get("agents", {})
    expected = set(GUILD_AGENTS)
    if set(configured) != expected:
        missing = sorted(expected - set(configured))
        extra = sorted(set(configured) - expected)
        raise BuildError(
            "Codex agent adapter must match the shared roster exactly "
            f"(missing={missing}, extra={extra})"
        )
    src_dir = os.path.join(core_dir, "roles")
    dst_dir = os.path.join(out_dir, "project-template", ".codex", "agents")
    os.makedirs(dst_dir, exist_ok=True)
    keys = (
        "name",
        "description",
        "model",
        "model_reasoning_effort",
        "sandbox_mode",
        "developer_instructions",
    )
    for name in GUILD_AGENTS:
        src = os.path.join(src_dir, f"{name}.md")
        if not os.path.isfile(src):
            raise BuildError(f"missing shared role source: {src}")
        with open(src, encoding="utf-8") as f:
            body = f.read()
        metadata = configured[name]
        instructions = body
        if metadata.get("sandbox_mode") == "read-only":
            instructions += _CODEX_READ_ONLY_PROTOCOL
        instructions += _adapter_agent_suffix(name, "codex")
        values = {
            "name": name,
            **metadata,
            "developer_instructions": instructions,
        }
        missing = [key for key in keys if key not in values]
        if missing:
            raise BuildError(
                f"Codex agent adapter for {name} is missing {missing}"
            )
        with open(
            os.path.join(dst_dir, f"{name}.toml"),
            "w",
            encoding="utf-8",
        ) as f:
            for key in keys:
                value = json.dumps(values[key], ensure_ascii=False)
                f.write(f"{key} = {value}\n")

    section_path = os.path.join(
        out_dir, "project-template", "AGENTS.agent-guild.md"
    )
    with open(section_path, "w", encoding="utf-8") as f:
        f.write("<!-- agent-guild:codex:start -->\n")
        f.write("## Agent Guild\n\n")
        f.write(
            "Before running an Agent Guild job, read "
            "`.agent-guild/CLAUDE.md`; its lifecycle and state-file "
            "contract is authoritative. Apply the Codex host mapping "
            "below.\n\n"
        )
        f.write("### Project Agent Roster\n\n")
        f.write("| Agent | Route | Sandbox |\n")
        f.write("| --- | --- | --- |\n")
        for name in GUILD_AGENTS:
            metadata = configured[name]
            f.write(
                f"| `{name}` | {metadata['description']} | "
                f"`{metadata['sandbox_mode']}` |\n"
            )
        f.write("\n### Codex Dispatch Boundary\n\n")
        f.write(
            "- The main session is the orchestrator. Delegate Guild work "
            "to the exact project agent named by the routing table.\n"
        )
        f.write(
            "- Worker and checker dispatches carry `Task-ID: T-NNN`; "
            "auditor dispatches carry `Audit-ID: CON-audit` or "
            "`Audit-ID: DEC-audit`. Put the id in the prompt on a Claude "
            "host, in `task_name` on a Codex host, where it must be "
            "lowercased and underscored (`t_001`, `con_audit`).\n"
        )
        f.write(
            "- On a Codex host that name must be unique per **dispatch**, "
            "not per task: this host refuses to reuse an agent name inside "
            "a session, and a task runs at least a worker, a checker, and a "
            "courier. Put a discriminator after the id and leave the id "
            "itself intact (`t_001_r0_worker`, `t_001_r0_checker`, "
            "`con_audit_r0`). Anything after the number is yours to choose; "
            "the gate strips it back to `T-001`.\n"
        )
        f.write(
            "- Never use `followup_task` to re-task a guild agent, "
            "including to work around a name clash. `dispatch-guard` "
            "refuses it: the call carries no id, no agent type, and no "
            "readable prompt, so no check can run against it. Spawn a fresh "
            "agent under a new name instead.\n"
        )
        f.write(
            "- Read-only agents return the intended state-file path and "
            "complete content to the orchestrator. Never grant them write "
            "access to bypass that boundary.\n"
        )
        f.write(
            "- A read-only `checker-courier` returns an "
            "`AGENT_GUILD_COURIER_OUTCOME` from the fixed Claude runner. "
            "For a verdict outcome, persist the supplied verdict unchanged "
            "at the `-claude` suffixed path, validate and render it, then "
            "record the supplied metrics through `ledger-append.py`. For a "
            "quota outcome, append that ledger line first with "
            "`--quota-event`, then create "
            "`.agent-guild/state/exhausted/claude`; write no verdict. A "
            "courier outcome never replaces the unsuffixed in-family "
            "verdict.\n"
        )
        f.write(
            "- Agent Guild owns only this marked section of `AGENTS.md` "
            "and its generated files under `.codex/agents/`.\n"
        )
        f.write("\n### Workflow Entry Point\n\n")
        f.write(
            "- Start existing work with `$"
            "{{AGENT_GUILD_SKILL_PREFIX}}"
            "job <issue|file|url>`.\n"
        )
        f.write("<!-- agent-guild:codex:end -->\n")


def build_dogfood(out_dir, core_dir=CORE_DIR):
    """Render the Claude wrappers this repository uses while developing."""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    copy_agents(out_dir, core_dir)
    copy_skills(out_dir, core_dir, seed_runtime=False)


def sync_dogfood(out_dir=CLAUDE_DIR, core_dir=CORE_DIR):
    """Overlay generated shared wrappers without touching host-only content."""
    with tempfile.TemporaryDirectory(prefix="build-dogfood-") as tmp:
        fresh = os.path.join(tmp, "claude")
        build_dogfood(fresh, core_dir)
        os.makedirs(os.path.join(out_dir, "agents"), exist_ok=True)
        os.makedirs(os.path.join(out_dir, "skills"), exist_ok=True)
        for name in GUILD_AGENTS:
            shutil.copy2(
                os.path.join(fresh, "agents", f"{name}.md"),
                os.path.join(out_dir, "agents", f"{name}.md"),
            )
        for name in [*GUILD_SKILLS, *OPTIONAL_SKILLS]:
            source = os.path.join(fresh, "skills", name)
            if os.path.isdir(source):
                shutil.copytree(
                    source,
                    os.path.join(out_dir, "skills", name),
                    dirs_exist_ok=True,
                )


def _hook_names(target):
    shipped = list(GUILD_HOOKS)
    for name in OPTIONAL_HOOKS:
        if os.path.isfile(os.path.join(GUILD_DIR, "hooks", name)):
            shipped.append(name)
    if target == "codex":
        shipped.extend(CODEX_HOOKS)
    return shipped


def copy_hook_scripts(dst_dir, target):
    """Copy one host's hook scripts from the shared source inventory."""
    if target not in {"claude", "codex"}:
        raise BuildError(f"unsupported hook target: {target}")
    src_dir = os.path.join(GUILD_DIR, "hooks")
    os.makedirs(dst_dir, exist_ok=True)
    shipped = _hook_names(target)
    for name in shipped:
        src = os.path.join(src_dir, name)
        if not os.path.isfile(src):
            raise BuildError(f"missing guild hook source: {src}")
        shutil.copy2(src, os.path.join(dst_dir, name))
    return shipped


def copy_hooks(out_dir, target="claude"):
    """Copy the hook scripts byte-identical into hooks/. Returns the list of
    filenames actually shipped (see copy_skills for why)."""
    dst_dir = os.path.join(out_dir, "hooks")
    return copy_hook_scripts(dst_dir, target)


# A registered command looks like:
#   python3 "$CLAUDE_PROJECT_DIR/.agent-guild/hooks/stop-gate.py"
# and must become:
#   python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/stop-gate.py
# -- the quoting narrows from wrapping the whole path to wrapping only the
# env var, matching how the rest of the plugin's own docs write it.
_HOOK_COMMAND_RE = re.compile(r'"\$CLAUDE_PROJECT_DIR/\.agent-guild/hooks/([^"]+)"')


def generate_hooks_json(out_dir, shipped_hooks):
    """Derive hooks/hooks.json from the live .claude/settings.json rather
    than hand-copying a stale one -- the dist-era package drifted from the
    real registration exactly this way. Rewrites every command's path,
    preserves events/matchers/timeouts, and appends the SessionStart nudge
    only when session-nudge.py actually shipped (a registration pointed at a
    file the package doesn't contain would 404 on every session start)."""
    settings_path = os.path.join(CLAUDE_DIR, "settings.json")
    try:
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
    except OSError as e:
        raise BuildError(f"cannot read {settings_path}: {e}")

    def rewrite_command(command):
        m = _HOOK_COMMAND_RE.search(command)
        if not m:
            raise BuildError(
                f"hook command doesn't match the expected "
                f'$CLAUDE_PROJECT_DIR/.agent-guild/hooks/<script> shape: {command!r}'
            )
        script = m.group(1)
        if script not in shipped_hooks:
            raise BuildError(
                f"hooks.json would register {script}, which the build didn't "
                f"ship under hooks/ -- add it to GUILD_HOOKS/OPTIONAL_HOOKS"
            )
        return _HOOK_COMMAND_RE.sub(f'"${{CLAUDE_PLUGIN_ROOT}}"/hooks/{script}', command)

    rewritten = {}
    for event, entries in settings.get("hooks", {}).items():
        new_entries = []
        for entry in entries:
            new_entry = dict(entry)
            new_entry["hooks"] = [
                {**h, "command": rewrite_command(h["command"])} for h in entry["hooks"]
            ]
            new_entries.append(new_entry)
        rewritten[event] = new_entries

    if "session-nudge.py" in shipped_hooks:
        rewritten.setdefault("SessionStart", []).append(
            {
                "matcher": "startup",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/session-nudge.py',
                        "timeout": 10,
                    }
                ],
            }
        )

    hooks_json_path = os.path.join(out_dir, "hooks", "hooks.json")
    with open(hooks_json_path, "w", encoding="utf-8") as f:
        json.dump({"hooks": rewritten}, f, indent=2)
        f.write("\n")


# Codex reports a namespaced tool as its namespace and name run together, so
# `collaboration` + `spawn_agent` arrives as `collaborationspawn_agent`. Its
# matchers are anchored regexes: `Agent|spawn_agent` never fired against that
# name while `.*` did, so the namespace has to be spelled out here or the
# dispatch gate is silently absent (#71). Bounded to a lowercase prefix and
# to the two dispatch primitives on purpose: `collaborationwait_agent` rides
# the same namespace and must not reach a gate that would then block it. The
# write tools need no equivalent, `apply_patch` arrives unnamespaced.
# `followup_task` re-tasks an agent that already exists. Leaving it out is what
# let a whole job run while dispatch-guard never applied (#77), so it is gated
# here even though the gate's only move against it is refusal.
CODEX_DISPATCH_MATCHER = "[a-z]*spawn_agent|[a-z]*followup_task|Agent"
CODEX_WRITE_MATCHER = "Edit|Write|apply_patch"


def _codex_hook_groups(command_root, skill_prefix):
    adapter = f'python3 "{command_root}/codex-hook-adapter.py"'
    nudge_command = f"{adapter} session-nudge"
    if skill_prefix:
        nudge_command += f" {skill_prefix}"
    guild_agents = "|".join(GUILD_AGENTS)
    return {
        "SessionStart": [
            {
                "matcher": "startup",
                "hooks": [
                    {
                        "type": "command",
                        "command": nudge_command,
                        "timeout": 10,
                    }
                ],
            }
        ],
        "PreToolUse": [
            {
                "matcher": CODEX_DISPATCH_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{adapter} dispatch-guard",
                        "timeout": 30,
                    }
                ],
            },
            {
                "matcher": CODEX_WRITE_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": (
                            f"{adapter} orchestrator-write-guard"
                        ),
                        "timeout": 30,
                    }
                ],
            },
        ],
        "SubagentStop": [
            {
                "matcher": guild_agents,
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{adapter} subagent-return",
                        "timeout": 30,
                    }
                ],
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{adapter} stop-gate",
                        "timeout": 30,
                    }
                ]
            }
        ],
    }


def generate_codex_hooks_json(out_dir):
    """Generate plugin and repo-local configs from one Codex hook inventory."""
    plugin_config = {
        "hooks": _codex_hook_groups(
            "${PLUGIN_ROOT}/hooks", "agent-guild:"
        )
    }
    plugin_path = os.path.join(out_dir, "hooks", "hooks.json")
    with open(plugin_path, "w", encoding="utf-8") as f:
        json.dump(plugin_config, f, indent=2)
        f.write("\n")

    project_config = {
        "hooks": _codex_hook_groups(
            '$(git rev-parse --show-toplevel)/.agent-guild/hooks', ""
        )
    }
    project_path = os.path.join(
        out_dir, "project-template", ".codex", "hooks.json"
    )
    os.makedirs(os.path.dirname(project_path), exist_ok=True)
    with open(project_path, "w", encoding="utf-8") as f:
        json.dump(project_config, f, indent=2)
        f.write("\n")


def assemble_project_template(out_dir, target="claude"):
    """Build project-template/.agent-guild/ -- the per-project payload the
    init skill copies into a user's repo: the orchestrator contract,
    the check scripts, the task/verdict templates, and the verdict schema."""
    dst_root = os.path.join(out_dir, "project-template", ".agent-guild")
    os.makedirs(dst_root, exist_ok=True)
    shutil.copy2(
        os.path.join(GUILD_DIR, "CLAUDE.md"), os.path.join(dst_root, "CLAUDE.md")
    )
    shutil.copytree(
        os.path.join(GUILD_DIR, "scripts"),
        os.path.join(dst_root, "scripts"),
        ignore=_IGNORE_BUILD_BYPRODUCTS,
    )
    shutil.copytree(
        os.path.join(GUILD_DIR, "templates"),
        os.path.join(dst_root, "templates"),
        ignore=_IGNORE_BUILD_BYPRODUCTS,
    )
    shutil.copytree(
        os.path.join(GUILD_DIR, "schemas"),
        os.path.join(dst_root, "schemas"),
        ignore=_IGNORE_BUILD_BYPRODUCTS,
    )
    if target == "codex":
        copy_hook_scripts(os.path.join(dst_root, "hooks"), "codex")
    if not os.path.isfile(INSTALLER_PATH):
        raise BuildError(f"missing project installer: {INSTALLER_PATH}")
    shutil.copy2(
        INSTALLER_PATH,
        os.path.join(out_dir, "project-template", "install.py"),
    )


# A bare invocation is a slash immediately preceded by start-of-line,
# whitespace, a backtick, or opening/quoting punctuation -- never by another
# path character. That's the difference between "`/decompose`" (an
# invocation) and "skills/decompose/" (a path segment) even though both
# contain the substring "/decompose": in the path, the character before the
# slash is a letter, not a boundary.
_INVOCATION_PRE_RE = r'(?:^|[\s`(\[{"\'])'


def _rewrite_invocations(text, names_to_namespaced):
    if not names_to_namespaced:
        return text
    names = "|".join(re.escape(n) for n in names_to_namespaced)
    pattern = re.compile(_INVOCATION_PRE_RE + r"/(" + names + r")\b", re.MULTILINE)

    def _sub(m):
        whole = m.group(0)
        name = m.group(1)
        pre = whole[: -(len(name) + 1)]  # everything before the slash
        return f"{pre}/{names_to_namespaced[name]}"

    return pattern.sub(_sub, text)


def apply_namespacing(out_dir, shipped_skills):
    """Rewrite bare guild invocations to their namespaced plugin form, in the
    packaged skill SKILL.md files, the packaged project-template CLAUDE.md, and
    the packaged README -- the plugin-bound prose that names them. The map only
    includes skills that actually shipped, so an absent `init` never gets
    rewritten into a token nothing in the package defines."""
    names_to_namespaced = {
        name: NAMESPACE_MAP[name] for name in shipped_skills if name in NAMESPACE_MAP
    }
    targets = [
        os.path.join(out_dir, "skills", name, "SKILL.md") for name in shipped_skills
    ]
    targets.append(os.path.join(out_dir, "project-template", ".agent-guild", "CLAUDE.md"))
    targets.append(os.path.join(out_dir, "README.md"))
    for path in targets:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        rewritten = _rewrite_invocations(text, names_to_namespaced)
        if rewritten != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(rewritten)


def copy_readme(out_dir):
    """Copy the authored plugin README (docs/plugin-readme.md) to README.md.
    apply_namespacing rewrites its bare guild invocations in place right after,
    the same path the SKILL.md bodies take -- so the source may name the skills
    either way and the packaged README always lands namespaced."""
    if not os.path.isfile(PLUGIN_SRC_README):
        raise BuildError(f"missing plugin README source: {PLUGIN_SRC_README}")
    shutil.copy2(PLUGIN_SRC_README, os.path.join(out_dir, "README.md"))


def write_plugin_manifest(out_dir):
    """Copy the checked-in manifest source through to .claude-plugin/. The
    manifest is authored once in scripts/plugin-src/plugin.json rather than
    generated, since nothing about it is derived from other sources."""
    dst_dir = os.path.join(out_dir, ".claude-plugin")
    os.makedirs(dst_dir, exist_ok=True)
    if not os.path.isfile(PLUGIN_SRC_MANIFEST):
        raise BuildError(f"missing manifest source: {PLUGIN_SRC_MANIFEST}")
    shutil.copy2(PLUGIN_SRC_MANIFEST, os.path.join(dst_dir, "plugin.json"))


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def marketplace_payloads():
    """Render both host catalogs from one plugin and marketplace identity."""
    manifest = _load_json(PLUGIN_SRC_MANIFEST, "release manifest")
    metadata = _load_json(
        MARKETPLACE_METADATA_PATH, "marketplace metadata"
    )
    codex_adapter = _load_json(CODEX_ADAPTER_PATH, "Codex adapter")
    try:
        plugin_name = manifest["name"]
        description = manifest["description"]
        marketplace_name = metadata["name"]
        display_name = metadata["displayName"]
        owner = manifest["author"]
        category = codex_adapter["interface"]["category"]
    except KeyError as error:
        raise BuildError(
            f"release or Codex adapter metadata is missing {error.args[0]!r}"
        ) from error

    claude = {
        "name": marketplace_name,
        "owner": owner,
        "description": description,
        "plugins": [
            {
                "name": plugin_name,
                "source": "./plugin",
                "description": description,
            }
        ],
    }
    codex = {
        "name": marketplace_name,
        "interface": {"displayName": display_name},
        "plugins": [
            {
                "name": plugin_name,
                "source": {
                    "source": "local",
                    "path": f"./plugins/{plugin_name}",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": category,
            }
        ],
    }
    return claude, codex


def write_marketplaces(
    claude_path=CLAUDE_MARKETPLACE_PATH,
    codex_path=CODEX_MARKETPLACE_PATH,
):
    """Write both host marketplace views from shared release metadata."""
    claude, codex = marketplace_payloads()
    _write_json(claude_path, claude)
    _write_json(codex_path, codex)


def build_codex(out_dir, core_dir=CORE_DIR):
    """Build the Codex target from shared behavior plus thin host adapters."""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(os.path.join(out_dir, ".codex-plugin"))
    copy_skills(out_dir, core_dir, target="codex")
    copy_hooks(out_dir, target="codex")
    manifest = _load_json(PLUGIN_SRC_MANIFEST, "release manifest")
    codex_adapter = _load_json(CODEX_ADAPTER_PATH, "Codex adapter")
    manifest.update(
        {
            key: value
            for key, value in codex_adapter.items()
            if key
            not in {
                "agents",
                "agent_body_suffixes",
                "skill_body_suffixes",
                "skill_frontmatter_overrides",
            }
        }
    )
    manifest["interface"]["developerName"] = manifest["author"]["name"]
    _write_json(
        os.path.join(out_dir, ".codex-plugin", "plugin.json"),
        manifest,
    )
    assemble_project_template(out_dir, target="codex")
    generate_codex_hooks_json(out_dir)
    generate_codex_agents(out_dir, core_dir)


def build_distributions(claude_out, codex_out, core_dir=CORE_DIR):
    """Build both host distributions from the repository's authored inputs."""
    build(claude_out, core_dir)
    build_codex(codex_out, core_dir)


def build(out_dir, core_dir=CORE_DIR):
    """Run the full build into out_dir, replacing whatever was there. Steps
    run in dependency order: hooks.json needs the hook files already copied
    (to validate against), namespacing needs the skills, project-template, and
    README already assembled (it edits the copies in place)."""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    copy_agents(out_dir, core_dir, names=CLAUDE_PLUGIN_AGENTS)
    shipped_skills = copy_skills(out_dir, core_dir)
    shipped_hooks = copy_hooks(out_dir, target="claude")
    generate_hooks_json(out_dir, shipped_hooks)
    assemble_project_template(out_dir, target="claude")
    copy_readme(out_dir)
    apply_namespacing(out_dir, shipped_skills)
    write_plugin_manifest(out_dir)


def diff_trees(built, committed):
    """Return human-readable differences between two directory trees ([] if
    identical in both file set and content). Named per-file, since a bare
    nonzero exit from --check would leave CI logs with nothing to act on."""

    def relfiles(base):
        found = set()
        for root, _dirs, files in os.walk(base):
            for name in files:
                found.add(os.path.relpath(os.path.join(root, name), base))
        return found

    built_files = relfiles(built)
    committed_files = relfiles(committed)
    diffs = []
    for rel in sorted(built_files - committed_files):
        diffs.append(f"missing from committed plugin/ (fresh build has it): {rel}")
    for rel in sorted(committed_files - built_files):
        diffs.append(f"missing from a fresh build (committed plugin/ has it): {rel}")
    for rel in sorted(built_files & committed_files):
        if not filecmp.cmp(
            os.path.join(built, rel),
            os.path.join(committed, rel),
            shallow=False,
        ):
            diffs.append(f"content differs: {rel}")
    return diffs


def dogfood_diffs(committed, core_dir=CORE_DIR):
    """Return drift in generated shared wrappers, ignoring host-only siblings."""
    with tempfile.TemporaryDirectory(prefix="build-dogfood-check-") as tmp:
        fresh = os.path.join(tmp, "claude")
        build_dogfood(fresh, core_dir)
        diffs = []
        for name in GUILD_AGENTS:
            rel = os.path.join("agents", f"{name}.md")
            expected = os.path.join(fresh, rel)
            actual = os.path.join(committed, rel)
            if not os.path.isfile(actual):
                diffs.append(f"missing generated dogfood wrapper: {rel}")
            elif not filecmp.cmp(expected, actual, shallow=False):
                diffs.append(f"content differs: {rel}")
        for name in [*GUILD_SKILLS, *OPTIONAL_SKILLS]:
            expected = os.path.join(fresh, "skills", name)
            if not os.path.isdir(expected):
                continue
            actual = os.path.join(committed, "skills", name)
            if not os.path.isdir(actual):
                diffs.append(f"missing generated dogfood wrapper: skills/{name}")
                continue
            diffs.extend(
                f"skills/{name}/{diff}"
                for diff in diff_trees(expected, actual)
                if not (
                    name == "audition"
                    and diff.endswith("results/results.jsonl")
                )
            )
        return diffs


def tree_digest(root):
    """Hash a generated tree's paths, executable bits, and bytes."""
    digest = hashlib.sha256()
    for current, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as f:
                payload = f.read()
            executable = b"1" if os.stat(path).st_mode & 0o111 else b"0"
            digest.update(rel.encode("utf-8"))
            digest.update(b"\0")
            digest.update(executable)
            digest.update(b"\0")
            digest.update(payload)
            digest.update(b"\0")
    return digest.hexdigest()


def marketplace_diffs(committed_claude, committed_codex):
    """Return drift in either generated marketplace file."""
    with tempfile.TemporaryDirectory(prefix="build-marketplaces-check-") as tmp:
        fresh_claude = os.path.join(tmp, "claude.json")
        fresh_codex = os.path.join(tmp, "codex.json")
        write_marketplaces(
            claude_path=fresh_claude,
            codex_path=fresh_codex,
        )
        diffs = []
        for label, fresh, committed in (
            ("claude", fresh_claude, committed_claude),
            ("codex", fresh_codex, committed_codex),
        ):
            if not os.path.isfile(committed):
                diffs.append(
                    f"{label} marketplace: missing generated file {committed}"
                )
            elif not filecmp.cmp(fresh, committed, shallow=False):
                diffs.append(
                    f"{label} marketplace: content differs: {committed}"
                )
        return diffs


def distribution_diffs(committed_claude, committed_codex):
    """Rebuild both targets and return target-prefixed drift diagnostics."""
    with tempfile.TemporaryDirectory(prefix="build-distributions-check-") as tmp:
        fresh_claude = os.path.join(tmp, "claude")
        fresh_codex = os.path.join(tmp, "codex")
        build_distributions(fresh_claude, fresh_codex)
        return [
            *(
                f"claude: {diff}"
                for diff in diff_trees(fresh_claude, committed_claude)
            ),
            *(
                f"codex: {diff}"
                for diff in diff_trees(fresh_codex, committed_codex)
            ),
        ]


def check_changelog_section():
    """Return None if the version in plugin-src/plugin.json has a matching
    `## <version>` section in CHANGELOG.md, else the problem as a string.
    Factored out from run_check so a test can call it directly against a
    scratch tree instead of shelling out to the whole --check pipeline.

    This is the backstop issue #42 exists for: a version bump landing
    without release notes because nobody remembered the changelog step."""
    try:
        with open(PLUGIN_SRC_MANIFEST, encoding="utf-8") as f:
            version = json.load(f)["version"]
    except (OSError, KeyError, json.JSONDecodeError) as e:
        return f"cannot read the version from {PLUGIN_SRC_MANIFEST}: {e}"

    if os.path.isfile(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, encoding="utf-8") as f:
            changelog_text = f.read()
    else:
        changelog_text = ""

    if not re.search(rf"(?m)^## {re.escape(version)}\b", changelog_text):
        return (
            f"CHANGELOG.md has no section for {version} -- run "
            f"`make-changelog.py {version}` to fix"
        )
    return None


def run_check():
    """Verify generated dogfood, both published trees, and marketplaces.

    Exits 0 only when the changelog has caught up with the manifest version,
    generated wrappers and artifacts match the shared core, AND
    `claude plugin validate --strict` passes on the Claude target."""
    changelog_problem = check_changelog_section()
    if changelog_problem:
        sys.stderr.write(f"build-plugin.py --check: {changelog_problem}\n")
        return 1

    if not os.path.isdir(DEFAULT_OUT):
        sys.stderr.write(
            f"build-plugin.py --check: Claude output {DEFAULT_OUT} does not "
            "exist -- run a build first\n"
        )
        return 1

    if not os.path.isdir(DEFAULT_CODEX_OUT):
        sys.stderr.write(
            f"build-plugin.py --check: Codex output {DEFAULT_CODEX_OUT} does "
            "not exist -- run a build first\n"
        )
        return 1

    wrapper_diffs = dogfood_diffs(CLAUDE_DIR)
    if wrapper_diffs:
        sys.stderr.write(
            "build-plugin.py --check: dogfooded Claude wrappers diverge from "
            f"the shared core ({len(wrapper_diffs)} difference(s)):\n"
        )
        for diff in wrapper_diffs:
            sys.stderr.write(f"  - {diff}\n")
        return 1

    diffs = distribution_diffs(DEFAULT_OUT, DEFAULT_CODEX_OUT)
    if diffs:
        sys.stderr.write(
            "build-plugin.py --check: generated distributions are stale "
            f"relative to a fresh build ({len(diffs)} difference(s)):\n"
        )
        for d in diffs:
            sys.stderr.write(f"  - {d}\n")
        return 1

    marketplace_problems = marketplace_diffs(
        CLAUDE_MARKETPLACE_PATH,
        CODEX_MARKETPLACE_PATH,
    )
    if marketplace_problems:
        sys.stderr.write(
            "build-plugin.py --check: generated marketplaces are stale "
            f"relative to release metadata "
            f"({len(marketplace_problems)} difference(s)):\n"
        )
        for problem in marketplace_problems:
            sys.stderr.write(f"  - {problem}\n")
        return 1

    claude_bin = shutil.which("claude")
    if claude_bin is None:
        sys.stderr.write(
            "build-plugin.py --check: the `claude` CLI is not on PATH -- "
            "cannot run `claude plugin validate --strict`, and a skipped "
            "validation must never report success\n"
        )
        return 1

    proc = subprocess.run(
        [claude_bin, "plugin", "validate", "--strict", DEFAULT_OUT]
    )
    if proc.returncode != 0:
        sys.stderr.write(
            f"build-plugin.py --check: `claude plugin validate --strict "
            f"{DEFAULT_OUT}` failed (exit {proc.returncode})\n"
        )
        return proc.returncode

    print(
        "OK: shared-core wrappers, both published packages, and both "
        "marketplaces match fresh builds; the Claude plugin passes strict "
        "validation"
    )
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="build-plugin.py",
        description=(
            "Build Agent Guild host distributions from shared sources.\n\n"
            "Modes:\n"
            "  build-plugin.py              sync both published packages and marketplaces\n"
            "  --target claude --out DIR    build only the Claude package\n"
            "  --target codex --out DIR     build only the Codex package\n"
            "  --target all --out DIR       build both packages under DIR\n"
            "  build-plugin.py --check      verify core-derived wrappers, outputs,\n"
            "                               marketplaces, and Claude validation"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--target",
        choices=("claude", "codex", "all"),
        help="build an explicit host target (requires --out)",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify the committed plugin/ is up to date instead of building",
    )
    parser.add_argument(
        "--out",
        metavar="DIR",
        help="output directory for --target (without --target: Claude compatibility)",
    )
    args = parser.parse_args()

    if args.check and args.out:
        parser.error("--check cannot be combined with --out")
    if args.target and not args.out:
        parser.error("--target requires --out DIR")

    try:
        if args.check:
            return run_check()
        if args.target:
            out_dir = os.path.abspath(args.out)
            _guard_out_dir(out_dir)
            if args.target == "claude":
                build(out_dir)
                print(f"OK: built Claude plugin at {out_dir}")
            elif args.target == "codex":
                build_codex(out_dir)
                print(f"OK: built Codex plugin at {out_dir}")
            else:
                if os.path.exists(out_dir):
                    shutil.rmtree(out_dir)
                os.makedirs(out_dir)
                claude_out = os.path.join(out_dir, "claude-plugin")
                codex_out = os.path.join(out_dir, "codex-plugin")
                build_distributions(claude_out, codex_out)
                print(
                    f"OK: built Claude plugin at {claude_out} and Codex "
                    f"plugin at {codex_out}"
                )
            return 0
        if args.out:
            out_dir = os.path.abspath(args.out)
            _guard_out_dir(out_dir)
            build(out_dir)
            print(f"OK: built Claude plugin at {out_dir}")
            return 0
        _guard_out_dir(DEFAULT_OUT)
        _guard_out_dir(DEFAULT_CODEX_OUT)
        sync_dogfood()
        build_distributions(DEFAULT_OUT, DEFAULT_CODEX_OUT)
        write_marketplaces()
        print(
            f"OK: built Claude plugin at {DEFAULT_OUT} and Codex plugin at "
            f"{DEFAULT_CODEX_OUT}; generated both marketplaces"
        )
        return 0
    except BuildError as e:
        sys.stderr.write(f"build-plugin.py: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
