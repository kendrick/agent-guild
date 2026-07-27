#!/usr/bin/env python3
"""Behavioral tests for the dual-target Agent Guild distribution build.

Run: python3 scripts/test_build_plugin.py
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
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
        rendered = []
        for target, role_dir in (
            (claude_out, "agents"),
            (codex_out, os.path.join("core", "roles")),
        ):
            with open(
                os.path.join(target, role_dir, "auditor.md"),
                encoding="utf-8",
            ) as f:
                rendered.append(f.read())
            with open(
                os.path.join(target, "skills", "init", "SKILL.md"),
                encoding="utf-8",
            ) as f:
                rendered.append(f.read())
        condition = all(
            marker in text
            for marker, text in (
                (role_marker.strip(), rendered[0]),
                (skill_marker.strip(), rendered[1]),
                (role_marker.strip(), rendered[2]),
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

    expected_roles = (
        "auditor",
        "checker-deterministic",
        "checker-judgment",
        "worker-bulk",
        "worker-craft",
        "worker-standard",
    )
    role_diffs = []
    for name in expected_roles:
        source = os.path.join(core_dir or "", "roles", f"{name}.md")
        built = os.path.join(
            codex_out, "core", "roles", f"{name}.md"
        )
        if not os.path.isfile(built):
            role_diffs.append(f"missing core/roles/{name}.md")
            continue
        with open(source, "rb") as f:
            source_bytes = f.read()
        with open(built, "rb") as f:
            built_bytes = f.read()
        if source_bytes != built_bytes:
            role_diffs.append(f"content differs: core/roles/{name}.md")
    check(
        "Codex stages neutral role sources without Claude agent wrappers",
        role_diffs == [],
        "; ".join(role_diffs),
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
