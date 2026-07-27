#!/usr/bin/env python3
"""Behavioral tests for the dual-target Agent Guild distribution build.

Run: python3 scripts/test_build_plugin.py
"""
import contextlib
import filecmp
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_PLUGIN_PATH = os.path.join(SCRIPTS_DIR, "build-plugin.py")
VERSION_SOURCE = os.path.join(SCRIPTS_DIR, "plugin-src", "plugin.json")

spec = importlib.util.spec_from_file_location("build_plugin", BUILD_PLUGIN_PATH)
build_plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_plugin)

passed = failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ok   {label}")
    else:
        failed += 1
        print(f"  FAIL {label}  {detail}")


def read_flat_toml(path):
    """Parse the builder's deliberately flat key = JSON-string TOML subset."""
    parsed = {}
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, separator, raw = stripped.partition(" = ")
            if not separator:
                raise ValueError(f"{path}:{number}: expected key = value")
            parsed[key] = json.loads(raw)
    return parsed


print("dual-target build")
with tempfile.TemporaryDirectory(prefix="build-plugin-test-") as tmp:
    claude_out = os.path.join(tmp, "claude")
    codex_out = os.path.join(tmp, "codex")

    core_dir = getattr(build_plugin, "CORE_DIR", None)
    core_role = (
        os.path.join(core_dir, "roles", "auditor.md") if core_dir else ""
    )
    core_skill = (
        os.path.join(core_dir, "workflows", "init", "SKILL.md")
        if core_dir
        else ""
    )
    condition = os.path.isfile(core_role) and os.path.isfile(core_skill)
    detail = f"CORE_DIR={core_dir!r}"
    if condition:
        with open(core_role, encoding="utf-8") as f:
            role_text = f.read()
        with open(core_skill, encoding="utf-8") as f:
            skill_text = f.read()
        condition = not role_text.startswith("---") and not skill_text.startswith(
            "---"
        )
        detail = (
            f"role_has_frontmatter={role_text.startswith('---')} "
            f"skill_has_frontmatter={skill_text.startswith('---')}"
        )
    check(
        "shared role and workflow behavior lives in a host-neutral core",
        condition,
        detail,
    )

    try:
        build_plugin._guard_out_dir(core_dir)
        condition = False
        detail = "shared core was accepted as a destructive build target"
    except build_plugin.BuildError as error:
        condition = core_dir in str(error)
        detail = str(error)
    check(
        "the builder refuses to overwrite the shared core",
        condition,
        detail,
    )

    explicit_claude = os.path.join(tmp, "explicit-claude")
    claude_proc = subprocess.run(
        [
            sys.executable,
            BUILD_PLUGIN_PATH,
            "--target",
            "claude",
            "--out",
            explicit_claude,
        ],
        capture_output=True,
        text=True,
    )
    claude_diffs = (
        build_plugin.diff_trees(
            os.path.join(os.path.dirname(SCRIPTS_DIR), "plugin"),
            explicit_claude,
        )
        if os.path.isdir(explicit_claude)
        else ["output missing"]
    )
    check(
        "the explicit Claude build reproduces the published plugin exactly",
        claude_proc.returncode == 0 and claude_diffs == [],
        (
            f"rc={claude_proc.returncode} diffs={claude_diffs!r} "
            f"stderr={claude_proc.stderr!r}"
        ),
    )

    explicit_codex = os.path.join(tmp, "explicit-codex")
    codex_proc = subprocess.run(
        [
            sys.executable,
            BUILD_PLUGIN_PATH,
            "--target",
            "codex",
            "--out",
            explicit_codex,
        ],
        capture_output=True,
        text=True,
    )
    check(
        "the explicit Codex build emits a standalone Codex package",
        codex_proc.returncode == 0
        and os.path.isfile(
            os.path.join(
                explicit_codex, ".codex-plugin", "plugin.json"
            )
        )
        and not os.path.exists(
            os.path.join(explicit_codex, ".claude-plugin")
        ),
        f"rc={codex_proc.returncode} stderr={codex_proc.stderr!r}",
    )

    explicit_all = os.path.join(tmp, "explicit-all")
    all_proc = subprocess.run(
        [
            sys.executable,
            BUILD_PLUGIN_PATH,
            "--target",
            "all",
            "--out",
            explicit_all,
        ],
        capture_output=True,
        text=True,
    )
    all_claude = os.path.join(explicit_all, "claude-plugin")
    all_codex = os.path.join(explicit_all, "codex-plugin")
    check(
        "the all-target build emits both packages under one output root",
        all_proc.returncode == 0
        and build_plugin.diff_trees(explicit_claude, all_claude) == []
        and build_plugin.diff_trees(explicit_codex, all_codex) == [],
        f"rc={all_proc.returncode} stderr={all_proc.stderr!r}",
    )

    try:
        scratch_core = os.path.join(tmp, "core")
        shutil.copytree(core_dir, scratch_core)
        role_marker = "\nCORE_ROLE_SENTINEL\n"
        skill_marker = "\nCORE_SKILL_SENTINEL\n"
        with open(
            os.path.join(scratch_core, "roles", "auditor.md"),
            "a",
            encoding="utf-8",
        ) as f:
            f.write(role_marker)
        with open(
            os.path.join(scratch_core, "workflows", "init", "SKILL.md"),
            "a",
            encoding="utf-8",
        ) as f:
            f.write(skill_marker)
        build_plugin.build_distributions(
            claude_out, codex_out, core_dir=scratch_core
        )
        with open(
            os.path.join(claude_out, "agents", "auditor.md"),
            encoding="utf-8",
        ) as f:
            claude_role = f.read()
        codex_role = read_flat_toml(
            os.path.join(
                codex_out,
                "project-template",
                ".codex",
                "agents",
                "auditor.toml",
            )
        )["developer_instructions"]
        rendered = [claude_role, codex_role]
        for target in (claude_out, codex_out):
            with open(
                os.path.join(target, "skills", "init", "SKILL.md"),
                encoding="utf-8",
            ) as f:
                rendered.append(f.read())
        condition = all(
            marker in text
            for marker, text in (
                (role_marker.strip(), rendered[0]),
                (role_marker.strip(), rendered[1]),
                (skill_marker.strip(), rendered[2]),
                (skill_marker.strip(), rendered[3]),
            )
        )
        detail = repr([text[-40:] for text in rendered])
    except (AttributeError, FileNotFoundError, TypeError) as error:
        condition = False
        detail = repr(error)
    check(
        "both host adapters render behavior from the injected shared core",
        condition,
        detail,
    )

    try:
        dogfood_out = os.path.join(tmp, "dogfood")
        build_plugin.build_dogfood(dogfood_out, core_dir=scratch_core)
        with open(
            os.path.join(dogfood_out, "agents", "auditor.md"),
            encoding="utf-8",
        ) as f:
            dogfood_role = f.read()
        with open(
            os.path.join(dogfood_out, "skills", "init", "SKILL.md"),
            encoding="utf-8",
        ) as f:
            dogfood_skill = f.read()
        condition = (
            role_marker.strip() in dogfood_role
            and skill_marker.strip() in dogfood_skill
            and dogfood_role.startswith("---\nname: auditor\n")
            and "disable-model-invocation: true" in dogfood_skill
        )
        detail = (
            f"role_tail={dogfood_role[-40:]!r} "
            f"skill_tail={dogfood_skill[-40:]!r}"
        )
    except (AttributeError, FileNotFoundError, TypeError) as error:
        condition = False
        detail = repr(error)
    check(
        "the dogfooded Claude wrappers are generated from the same core",
        condition,
        detail,
    )

    try:
        dogfood_root = os.path.join(tmp, "dogfood-root")
        os.makedirs(os.path.join(dogfood_root, "agents"))
        os.makedirs(os.path.join(dogfood_root, "skills", "unrelated"))
        os.makedirs(
            os.path.join(
                dogfood_root, "skills", "audition", "results"
            )
        )
        unrelated_agent = os.path.join(
            dogfood_root, "agents", "unrelated.md"
        )
        unrelated_skill = os.path.join(
            dogfood_root, "skills", "unrelated", "asset.txt"
        )
        audition_results = os.path.join(
            dogfood_root,
            "skills",
            "audition",
            "results",
            "results.jsonl",
        )
        with open(unrelated_agent, "w", encoding="utf-8") as f:
            f.write("keep agent\n")
        with open(unrelated_skill, "w", encoding="utf-8") as f:
            f.write("keep skill\n")
        with open(audition_results, "w", encoding="utf-8") as f:
            f.write("keep result\n")
        build_plugin.sync_dogfood(dogfood_root, core_dir=scratch_core)
        with open(unrelated_agent, encoding="utf-8") as f:
            agent_text = f.read()
        with open(unrelated_skill, encoding="utf-8") as f:
            skill_text = f.read()
        with open(audition_results, encoding="utf-8") as f:
            result_text = f.read()
        condition = (
            agent_text == "keep agent\n"
            and skill_text == "keep skill\n"
            and result_text == "keep result\n"
        )
        detail = (
            f"agent={agent_text!r} skill={skill_text!r} "
            f"result={result_text!r}"
        )
    except (AttributeError, FileNotFoundError, TypeError) as error:
        condition = False
        detail = repr(error)
    check(
        "dogfood sync preserves host-only content and audition results",
        condition,
        detail,
    )

    expected_codex_stage = os.path.join(
        os.path.dirname(SCRIPTS_DIR), "dist", "codex-plugin"
    )
    committed_codex = os.path.join(
        os.path.dirname(SCRIPTS_DIR), "codex-plugin"
    )
    check(
        "Codex package content is release-stage output, not a committed mirror",
        getattr(build_plugin, "DEFAULT_CODEX_OUT", None)
        == expected_codex_stage
        and not os.path.exists(committed_codex),
        (
            f"default={getattr(build_plugin, 'DEFAULT_CODEX_OUT', None)!r} "
            f"committed_exists={os.path.exists(committed_codex)}"
        ),
    )

    try:
        dogfood_diffs = build_plugin.dogfood_diffs(
            dogfood_out, core_dir=scratch_core
        )
        with open(
            os.path.join(dogfood_out, "agents", "auditor.md"),
            "a",
            encoding="utf-8",
        ) as f:
            f.write("hand edit\n")
        hand_edit_diffs = build_plugin.dogfood_diffs(
            dogfood_out, core_dir=scratch_core
        )
        condition = dogfood_diffs == [] and hand_edit_diffs == [
            "content differs: agents/auditor.md"
        ]
        detail = (
            f"clean={dogfood_diffs!r} hand_edit={hand_edit_diffs!r}"
        )
    except (AttributeError, FileNotFoundError, TypeError) as error:
        condition = False
        detail = repr(error)
    check(
        "dogfood drift checks reject edits outside the shared core",
        condition,
        detail,
    )

    try:
        lock_path = os.path.join(tmp, "codex.sha256")
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write("0" * 64 + "\n")
        lock_problem = build_plugin.codex_lock_problem(
            lock_path=lock_path, core_dir=scratch_core
        )
        condition = (
            lock_problem is not None
            and "stale" in lock_problem
            and lock_path in lock_problem
        )
        detail = repr(lock_problem)
    except (AttributeError, FileNotFoundError, TypeError) as error:
        condition = False
        detail = repr(error)
    check(
        "the compact Codex release lock rejects stale generated content",
        condition,
        detail,
    )

    try:
        lock_problem = build_plugin.codex_lock_problem()
        condition = lock_problem is None
        detail = repr(lock_problem)
    except (AttributeError, FileNotFoundError, TypeError) as error:
        condition = False
        detail = repr(error)
    check(
        "the committed Codex lock matches a fresh release-stage build",
        condition,
        detail,
    )

    try:
        build_plugin.build_distributions(claude_out, codex_out)
        with open(VERSION_SOURCE, encoding="utf-8") as f:
            authored_version = json.load(f)["version"]
        with open(
            os.path.join(claude_out, ".claude-plugin", "plugin.json"),
            encoding="utf-8",
        ) as f:
            claude_version = json.load(f)["version"]
        with open(
            os.path.join(codex_out, ".codex-plugin", "plugin.json"),
            encoding="utf-8",
        ) as f:
            codex_version = json.load(f)["version"]
        detail = (
            f"authored={authored_version!r} claude={claude_version!r} "
            f"codex={codex_version!r}"
        )
        condition = claude_version == codex_version == authored_version
    except (
        AttributeError,
        FileNotFoundError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        condition = False
        detail = repr(error)

    check(
        "one build emits Claude and Codex manifests at the authored version",
        condition,
        detail,
    )

    claude_payload = os.path.join(
        claude_out, "project-template", ".agent-guild"
    )
    codex_payload = os.path.join(
        codex_out, "project-template", ".agent-guild"
    )
    shared_payload_dirs = ("schemas", "scripts", "templates")
    if os.path.isdir(claude_payload) and os.path.isdir(codex_payload):
        payload_diffs = []
        for name in shared_payload_dirs:
            payload_diffs.extend(
                f"{name}/{difference}"
                for difference in build_plugin.diff_trees(
                    os.path.join(claude_payload, name),
                    os.path.join(codex_payload, name),
                )
            )
        condition = payload_diffs == []
        detail = "; ".join(payload_diffs)
    else:
        condition = False
        detail = (
            f"claude_payload={os.path.isdir(claude_payload)} "
            f"codex_payload={os.path.isdir(codex_payload)}"
        )
    check(
        "both targets receive byte-identical shared schemas, scripts, and templates",
        condition,
        detail,
    )

    result_seeds = [
        os.path.join(
            target,
            "skills",
            "audition",
            "results",
            "results.jsonl",
        )
        for target in (claude_out, codex_out)
    ]
    condition = all(
        os.path.isfile(seed) and os.path.getsize(seed) == 0
        for seed in result_seeds
    )
    check(
        "both packages seed an empty audition log outside authored core",
        condition,
        repr(result_seeds),
    )

    expected_skills = (
        "audition",
        "constitution",
        "decompose",
        "init",
        "job",
        "retrospective",
    )
    with open(
        os.path.join(codex_out, ".codex-plugin", "plugin.json"),
        encoding="utf-8",
    ) as f:
        codex_manifest = json.load(f)
    skill_diffs = []
    for name in expected_skills:
        source = os.path.join(
            core_dir, "workflows", name
        )
        built = os.path.join(codex_out, "skills", name)
        if not os.path.isdir(built):
            skill_diffs.append(f"missing skills/{name}")
            continue
        for difference in build_plugin.diff_trees(source, built):
            if difference == (
                "missing from a fresh build (committed plugin/ has it): "
                "results/results.jsonl"
            ):
                continue
            if difference != "content differs: SKILL.md":
                skill_diffs.append(f"skills/{name}/{difference}")
                continue
            with open(
                os.path.join(source, "SKILL.md"), encoding="utf-8"
            ) as f:
                source_body = f.read()
            with open(
                os.path.join(built, "SKILL.md"), encoding="utf-8"
            ) as f:
                built_body = f.read().split("---", 2)[2].lstrip("\n")
            if source_body != built_body:
                skill_diffs.append(f"skills/{name}/body differs")
    condition = (
        codex_manifest.get("skills") == "./skills/" and skill_diffs == []
    )
    detail = (
        f"manifest.skills={codex_manifest.get('skills')!r}; "
        + "; ".join(skill_diffs)
    )
    check(
        "Codex receives shared workflow bodies and assets through target wrappers",
        condition,
        detail,
    )

    interface = codex_manifest.get("interface")
    required_interface_fields = {
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "defaultPrompt",
    }
    condition = (
        isinstance(interface, dict)
        and required_interface_fields <= set(interface)
        and interface["displayName"] == "Agent Guild"
        and isinstance(interface["capabilities"], list)
        and bool(interface["capabilities"])
        and isinstance(interface["defaultPrompt"], list)
        and 1 <= len(interface["defaultPrompt"]) <= 3
    )
    check(
        "Codex manifest carries the required interface metadata",
        condition,
        repr(interface),
    )

    with open(
        os.path.join(codex_out, "skills", "init", "SKILL.md"),
        encoding="utf-8",
    ) as f:
        codex_init_frontmatter = f.read().split("---", 2)[1]
    check(
        "Codex init wrapper remains model-invocable",
        "disable-model-invocation: false" in codex_init_frontmatter
        and "disable-model-invocation: true" not in codex_init_frontmatter,
        codex_init_frontmatter,
    )

    expected_roles = {
        "auditor": ("gpt-5.6-sol", "xhigh", "read-only"),
        "checker-courier": ("gpt-5.6-terra", "low", "read-only"),
        "checker-deterministic": (
            "gpt-5.6-terra",
            "low",
            "read-only",
        ),
        "checker-judgment": ("gpt-5.6-sol", "high", "read-only"),
        "hydrator": ("gpt-5.6-sol", "high", "workspace-write"),
        "worker-bulk": ("gpt-5.6-terra", "low", "workspace-write"),
        "worker-craft": ("gpt-5.6-sol", "high", "workspace-write"),
        "worker-standard": (
            "gpt-5.6-terra",
            "medium",
            "workspace-write",
        ),
        "working-memory-synchronizer": (
            "gpt-5.6-terra",
            "medium",
            "workspace-write",
        ),
    }
    agent_dir = os.path.join(
        codex_out, "project-template", ".codex", "agents"
    )
    built_role_names = (
        {
            os.path.splitext(name)[0]
            for name in os.listdir(agent_dir)
            if name.endswith(".toml")
        }
        if os.path.isdir(agent_dir)
        else set()
    )
    role_diffs = []
    if built_role_names != set(expected_roles):
        role_diffs.append(
            f"roles={sorted(built_role_names)!r}, "
            f"expected={sorted(expected_roles)!r}"
        )
    for name, expected_config in expected_roles.items():
        source = os.path.join(core_dir or "", "roles", f"{name}.md")
        built = os.path.join(agent_dir, f"{name}.toml")
        if not os.path.isfile(source):
            role_diffs.append(f"missing shared role source: {name}")
            continue
        if not os.path.isfile(built):
            role_diffs.append(f"missing .codex/agents/{name}.toml")
            continue
        with open(source, encoding="utf-8") as f:
            source_body = f.read()
        try:
            config = read_flat_toml(built)
        except (ValueError, json.JSONDecodeError) as error:
            role_diffs.append(str(error))
            continue
        expected_model, expected_effort, expected_sandbox = expected_config
        if config.get("name") != name:
            role_diffs.append(
                f"{name}: name={config.get('name')!r}"
            )
        if not config.get("description"):
            role_diffs.append(f"{name}: empty description")
        if config.get("model") != expected_model:
            role_diffs.append(
                f"{name}: model={config.get('model')!r}"
            )
        if config.get("model_reasoning_effort") != expected_effort:
            role_diffs.append(
                f"{name}: effort="
                f"{config.get('model_reasoning_effort')!r}"
            )
        if config.get("sandbox_mode") != expected_sandbox:
            role_diffs.append(
                f"{name}: sandbox={config.get('sandbox_mode')!r}"
            )
        if source_body not in config.get("developer_instructions", ""):
            role_diffs.append(
                f"{name}: developer instructions do not derive from core"
            )
        if (
            expected_sandbox == "read-only"
            and "Return the intended output path and complete proposed "
            "file content to the parent orchestrator"
            not in config.get("developer_instructions", "")
        ):
            role_diffs.append(
                f"{name}: missing Codex read-only return protocol"
            )
        if (
            name in {"checker-deterministic", "checker-judgment"}
            and "report `vendor: openai` and your configured Codex model"
            not in config.get("developer_instructions", "")
        ):
            role_diffs.append(
                f"{name}: missing Codex verdict identity override"
            )
    check(
        "Codex generates the complete project roster from shared roles",
        role_diffs == []
        and not os.path.exists(os.path.join(codex_out, "core", "roles")),
        "; ".join(role_diffs),
    )

    courier_config = read_flat_toml(
        os.path.join(agent_dir, "checker-courier.toml")
    )
    courier_instructions = courier_config.get(
        "developer_instructions", ""
    )
    check(
        "the Codex courier fails closed until its reciprocal lane lands",
        "never invoke `codex` as the far-side vendor" in courier_instructions
        and "reciprocal Claude lane is not installed"
        in courier_instructions,
        courier_instructions[-600:],
    )

    installer = os.path.join(
        codex_out, "project-template", "install-codex.py"
    )
    project_root = os.path.join(tmp, "codex-project")
    project_agents = os.path.join(project_root, ".codex", "agents")
    os.makedirs(project_agents)
    original_agents_md = (
        "# Existing Project\n\n"
        "## Local Rules\n\n"
        "Keep this guidance exactly.\n"
    )
    with open(
        os.path.join(project_root, "AGENTS.md"), "w", encoding="utf-8"
    ) as f:
        f.write(original_agents_md)
    config_path = os.path.join(project_root, ".codex", "config.toml")
    unrelated_agent = os.path.join(project_agents, "unrelated.toml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write('model = "user-choice"\n')
    with open(unrelated_agent, "w", encoding="utf-8") as f:
        f.write('name = "unrelated"\n')
    fake_home = os.path.join(tmp, "home")
    os.makedirs(fake_home)
    home_marker = os.path.join(fake_home, "keep.txt")
    with open(home_marker, "w", encoding="utf-8") as f:
        f.write("untouched\n")
    install_env = dict(os.environ)
    install_env["HOME"] = fake_home
    first_install = subprocess.run(
        [sys.executable, installer, project_root],
        capture_output=True,
        text=True,
        env=install_env,
    )
    managed_diffs = []
    for name in expected_roles:
        source = os.path.join(agent_dir, f"{name}.toml")
        installed = os.path.join(project_agents, f"{name}.toml")
        if not os.path.isfile(installed):
            managed_diffs.append(f"missing {name}.toml")
        elif not filecmp.cmp(source, installed, shallow=False):
            managed_diffs.append(f"content differs: {name}.toml")
    with open(config_path, encoding="utf-8") as f:
        installed_config = f.read()
    with open(unrelated_agent, encoding="utf-8") as f:
        installed_unrelated = f.read()
    with open(home_marker, encoding="utf-8") as f:
        installed_home_marker = f.read()
    check(
        "the Codex initializer installs only the project-local Guild roster",
        first_install.returncode == 0
        and managed_diffs == []
        and installed_config == 'model = "user-choice"\n'
        and installed_unrelated == 'name = "unrelated"\n'
        and installed_home_marker == "untouched\n"
        and not os.path.exists(os.path.join(fake_home, ".codex")),
        (
            f"rc={first_install.returncode} diffs={managed_diffs!r} "
            f"config={installed_config!r} "
            f"unrelated={installed_unrelated!r} "
            f"home={sorted(os.listdir(fake_home))!r} "
            f"stdout={first_install.stdout!r} "
            f"stderr={first_install.stderr!r}"
        ),
    )

    agents_path = os.path.join(project_root, "AGENTS.md")
    section_start = "<!-- agent-guild:codex:start -->"
    section_end = "<!-- agent-guild:codex:end -->"
    if os.path.isfile(agents_path):
        with open(agents_path, encoding="utf-8") as f:
            first_agents_md = f.read()
    else:
        first_agents_md = ""
    section = (
        first_agents_md[
            first_agents_md.find(section_start) :
            first_agents_md.find(section_end) + len(section_end)
        ]
        if section_start in first_agents_md
        and section_end in first_agents_md
        else ""
    )
    before_second_digest = (
        build_plugin.tree_digest(project_root)
        if os.path.isdir(project_root)
        else ""
    )
    second_install = subprocess.run(
        [sys.executable, installer, project_root],
        capture_output=True,
        text=True,
        env=install_env,
    )
    after_second_digest = (
        build_plugin.tree_digest(project_root)
        if os.path.isdir(project_root)
        else ""
    )
    check(
        "the Codex initializer preserves AGENTS.md outside one idempotent section",
        first_install.returncode == 0
        and first_agents_md.startswith(original_agents_md)
        and first_agents_md.count(section_start) == 1
        and first_agents_md.count(section_end) == 1
        and all(name in section for name in expected_roles)
        and "read-only" in section
        and "workspace-write" in section
        and second_install.returncode == 0
        and before_second_digest == after_second_digest,
        (
            f"first_rc={first_install.returncode} "
            f"second_rc={second_install.returncode} "
            f"section={section!r} "
            f"before={before_second_digest!r} "
            f"after={after_second_digest!r}"
        ),
    )

    managed_agent = os.path.join(
        project_agents, "worker-standard.toml"
    )
    with open(managed_agent, "w", encoding="utf-8") as f:
        f.write("stale generated agent\n")
    stale_agents_md = first_agents_md.replace(
        section, f"{section_start}\nstale generated section\n{section_end}"
    )
    with open(agents_path, "w", encoding="utf-8") as f:
        f.write(stale_agents_md)
    update_install = subprocess.run(
        [sys.executable, installer, project_root],
        capture_output=True,
        text=True,
        env=install_env,
    )
    with open(agents_path, encoding="utf-8") as f:
        updated_agents_md = f.read()
    with open(config_path, encoding="utf-8") as f:
        updated_config = f.read()
    with open(unrelated_agent, encoding="utf-8") as f:
        updated_unrelated = f.read()
    check(
        "the Codex initializer refreshes only Agent Guild-owned content",
        update_install.returncode == 0
        and filecmp.cmp(
            managed_agent,
            os.path.join(agent_dir, "worker-standard.toml"),
            shallow=False,
        )
        and updated_agents_md == first_agents_md
        and updated_config == 'model = "user-choice"\n'
        and updated_unrelated == 'name = "unrelated"\n',
        (
            f"rc={update_install.returncode} "
            f"stdout={update_install.stdout!r} "
            f"stderr={update_install.stderr!r}"
        ),
    )

    malformed_project = os.path.join(tmp, "malformed-project")
    os.makedirs(malformed_project)
    malformed_agents_path = os.path.join(
        malformed_project, "AGENTS.md"
    )
    malformed_text = (
        "# User Guidance\n\n"
        f"{section_start}\n"
        "unterminated user-visible content\n"
    )
    with open(malformed_agents_path, "w", encoding="utf-8") as f:
        f.write(malformed_text)
    malformed_install = subprocess.run(
        [sys.executable, installer, malformed_project],
        capture_output=True,
        text=True,
        env=install_env,
    )
    with open(malformed_agents_path, encoding="utf-8") as f:
        after_malformed = f.read()
    check(
        "the Codex initializer fails closed on malformed ownership markers",
        malformed_install.returncode != 0
        and after_malformed == malformed_text
        and not os.path.exists(
            os.path.join(malformed_project, ".codex")
        )
        and "marker" in malformed_install.stderr.lower(),
        (
            f"rc={malformed_install.returncode} "
            f"stdout={malformed_install.stdout!r} "
            f"stderr={malformed_install.stderr!r}"
        ),
    )

    redirected_project = os.path.join(tmp, "redirected-project")
    redirected_codex = os.path.join(tmp, "outside-project")
    os.makedirs(redirected_project)
    os.makedirs(redirected_codex)
    outside_marker = os.path.join(redirected_codex, "keep.txt")
    with open(outside_marker, "w", encoding="utf-8") as f:
        f.write("outside stays untouched\n")
    os.symlink(
        redirected_codex, os.path.join(redirected_project, ".codex")
    )
    redirected_install = subprocess.run(
        [sys.executable, installer, redirected_project],
        capture_output=True,
        text=True,
        env=install_env,
    )
    with open(outside_marker, encoding="utf-8") as f:
        after_redirected = f.read()
    check(
        "the Codex initializer rejects project paths redirected outside",
        redirected_install.returncode != 0
        and sorted(os.listdir(redirected_codex)) == ["keep.txt"]
        and after_redirected == "outside stays untouched\n"
        and not os.path.exists(
            os.path.join(redirected_project, "AGENTS.md")
        ),
        (
            f"rc={redirected_install.returncode} "
            f"outside={sorted(os.listdir(redirected_codex))!r} "
            f"stdout={redirected_install.stdout!r} "
            f"stderr={redirected_install.stderr!r}"
        ),
    )

    codex_manifest_path = os.path.join(
        codex_out, ".codex-plugin", "plugin.json"
    )
    with open(codex_manifest_path, encoding="utf-8") as f:
        hand_edited_manifest = json.load(f)
    hand_edited_manifest["description"] = "hand-edited output"
    with open(codex_manifest_path, "w", encoding="utf-8") as f:
        json.dump(hand_edited_manifest, f, indent=2)
        f.write("\n")
    try:
        distribution_diffs = build_plugin.distribution_diffs(
            claude_out, codex_out
        )
        condition = distribution_diffs == [
            "codex: content differs: .codex-plugin/plugin.json"
        ]
        detail = repr(distribution_diffs)
    except AttributeError as error:
        condition = False
        detail = repr(error)
    check(
        "distribution check catches a hand-edited Codex build output",
        condition,
        detail,
    )

    original_claude_out = build_plugin.DEFAULT_OUT
    original_codex_out = getattr(build_plugin, "DEFAULT_CODEX_OUT", None)
    build_plugin.DEFAULT_OUT = claude_out
    build_plugin.DEFAULT_CODEX_OUT = codex_out
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            check_rc = build_plugin.run_check()
    finally:
        build_plugin.DEFAULT_OUT = original_claude_out
        if original_codex_out is None:
            del build_plugin.DEFAULT_CODEX_OUT
        else:
            build_plugin.DEFAULT_CODEX_OUT = original_codex_out
    check(
        "--check fails loudly on stale Codex output before validation",
        check_rc == 1
        and "codex: content differs: .codex-plugin/plugin.json"
        in stderr.getvalue(),
        f"rc={check_rc} stderr={stderr.getvalue()!r}",
    )

print(f"\n{passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
