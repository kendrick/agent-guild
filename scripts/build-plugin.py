#!/usr/bin/env python3
"""Build the publishable agent-guild Claude Code plugin from in-repo sources.

The guild lives across `.claude/` and `.agent-guild/` so it can be dogfooded
in this repo, but a plugin ships as one self-contained tree: agents, a fixed
skill set, hooks plus a generated registration, a per-project payload for the
future init skill, and a manifest. This script assembles that tree from the
live sources rather than hand-copying, so the published plugin never drifts
from what this repo actually runs.

Modes:
    build-plugin.py              build into ./plugin/ (repo root)
    build-plugin.py --out DIR    build into DIR instead (what the checks use)
    build-plugin.py --check      rebuild into a temp dir, diff it against the
                                  committed plugin/, and run
                                  `claude plugin validate --strict` on it

Exit codes: 0 success; 1 a build or check step failed (message on stderr
names the actual problem, not a bare "failed").

Stdlib only, so the kit stays copy-in portable -- see
.agent-guild/scripts/check-provenance.py and new-task.py for the same rule.
"""
import argparse
import filecmp
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
PLUGIN_SRC_MANIFEST = os.path.join(ROOT, "scripts", "plugin-src", "plugin.json")
PLUGIN_SRC_README = os.path.join(ROOT, "docs", "plugin-readme.md")
CHANGELOG_PATH = os.path.join(ROOT, "CHANGELOG.md")
DEFAULT_OUT = os.path.join(ROOT, "plugin")

GUILD_AGENTS = [
    "auditor",
    "checker-deterministic",
    "checker-judgment",
    "worker-bulk",
    "worker-craft",
    "worker-standard",
]

# The lifecycle skills always ship. `init` (#22) and the hooks nudge (#23)
# join automatically once their sources exist -- they don't today. Treating
# them as include-when-present, rather than hardcoding their absence, means
# this script doesn't need a follow-up edit the day either one lands.
GUILD_SKILLS = ["constitution", "decompose", "retrospective", "audition", "job"]
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
    modify its inputs, so a careless --out pointed at .claude/ or
    .agent-guild/ (which starts with rmtree-ing whatever's already there) is
    a mistake to catch up front, not a git diff to notice after the fact."""
    for protected in (CLAUDE_DIR, GUILD_DIR):
        if out_dir == protected or out_dir.startswith(protected + os.sep):
            raise BuildError(
                f"--out {out_dir} is inside a read-only source tree "
                f"({protected}); refusing to build there"
            )


def copy_agents(out_dir):
    """Copy exactly the six guild agents byte-identical into agents/."""
    src_dir = os.path.join(CLAUDE_DIR, "agents")
    dst_dir = os.path.join(out_dir, "agents")
    os.makedirs(dst_dir, exist_ok=True)
    for name in GUILD_AGENTS:
        src = os.path.join(src_dir, f"{name}.md")
        if not os.path.isfile(src):
            raise BuildError(f"missing guild agent source: {src}")
        shutil.copy2(src, os.path.join(dst_dir, f"{name}.md"))


def copy_skills(out_dir):
    """Copy the guild skill directories (full contents) into skills/.
    Returns the list of skill names actually shipped, so callers that only
    care about what's really in the output (hooks.json, namespacing) don't
    have to re-derive the include-when-present logic themselves."""
    src_dir = os.path.join(CLAUDE_DIR, "skills")
    dst_dir = os.path.join(out_dir, "skills")
    os.makedirs(dst_dir, exist_ok=True)
    shipped = list(GUILD_SKILLS)
    for name in OPTIONAL_SKILLS:
        if os.path.isdir(os.path.join(src_dir, name)):
            shipped.append(name)
    for name in shipped:
        src = os.path.join(src_dir, name)
        if not os.path.isdir(src):
            raise BuildError(f"missing guild skill source: {src}")
        shutil.copytree(
            src, os.path.join(dst_dir, name), ignore=_IGNORE_BUILD_BYPRODUCTS
        )
    return shipped


def copy_hooks(out_dir):
    """Copy the hook scripts byte-identical into hooks/. Returns the list of
    filenames actually shipped (see copy_skills for why)."""
    src_dir = os.path.join(GUILD_DIR, "hooks")
    dst_dir = os.path.join(out_dir, "hooks")
    os.makedirs(dst_dir, exist_ok=True)
    shipped = list(GUILD_HOOKS)
    for name in OPTIONAL_HOOKS:
        if os.path.isfile(os.path.join(src_dir, name)):
            shipped.append(name)
    for name in shipped:
        src = os.path.join(src_dir, name)
        if not os.path.isfile(src):
            raise BuildError(f"missing guild hook source: {src}")
        shutil.copy2(src, os.path.join(dst_dir, name))
    return shipped


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


def assemble_project_template(out_dir):
    """Build project-template/.agent-guild/ -- the per-project payload the
    future init skill copies into a user's repo: the orchestrator contract,
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


def build(out_dir):
    """Run the full build into out_dir, replacing whatever was there. Steps
    run in dependency order: hooks.json needs the hook files already copied
    (to validate against), namespacing needs the skills, project-template, and
    README already assembled (it edits the copies in place)."""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    copy_agents(out_dir)
    shipped_skills = copy_skills(out_dir)
    shipped_hooks = copy_hooks(out_dir)
    generate_hooks_json(out_dir, shipped_hooks)
    assemble_project_template(out_dir)
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
        if not filecmp.cmp(os.path.join(built, rel), os.path.join(committed, rel), shallow=False):
            diffs.append(f"content differs: {rel}")
    return diffs


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
    """Rebuild into a temp dir and compare against the committed plugin/.
    Exits 0 only when the changelog has caught up with the manifest version,
    the trees match, AND `claude plugin validate --strict` passes -- a
    missing plugin/, a content drift, a missing `claude` CLI, or a
    forgotten changelog section must all fail loudly rather than let a
    skipped check read as green."""
    changelog_problem = check_changelog_section()
    if changelog_problem:
        sys.stderr.write(f"build-plugin.py --check: {changelog_problem}\n")
        return 1

    committed = DEFAULT_OUT
    if not os.path.isdir(committed):
        sys.stderr.write(
            f"build-plugin.py --check: {committed} does not exist -- run a "
            f"build first\n"
        )
        return 1

    with tempfile.TemporaryDirectory(prefix="build-plugin-check-") as tmp:
        fresh = os.path.join(tmp, "plugin")
        build(fresh)
        diffs = diff_trees(fresh, committed)
        if diffs:
            sys.stderr.write(
                f"build-plugin.py --check: {committed} is stale relative to a "
                f"fresh build ({len(diffs)} difference(s)):\n"
            )
            for d in diffs:
                sys.stderr.write(f"  - {d}\n")
            return 1

        claude_bin = shutil.which("claude")
        if claude_bin is None:
            sys.stderr.write(
                "build-plugin.py --check: the `claude` CLI is not on PATH -- "
                "cannot run `claude plugin validate --strict`, and a skipped "
                "validation must never report success\n"
            )
            return 1

        proc = subprocess.run([claude_bin, "plugin", "validate", "--strict", committed])
        if proc.returncode != 0:
            sys.stderr.write(
                f"build-plugin.py --check: `claude plugin validate --strict "
                f"{committed}` failed (exit {proc.returncode})\n"
            )
            return proc.returncode

    print(f"OK: {committed} matches a fresh build and passes claude plugin validate --strict")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="build-plugin.py",
        description=(
            "Build the publishable agent-guild plugin from in-repo sources.\n\n"
            "Modes:\n"
            "  build-plugin.py              build into ./plugin/ (repo root)\n"
            "  build-plugin.py --out DIR    build into DIR instead (used by tests)\n"
            "  build-plugin.py --check      rebuild into a temp dir, diff against\n"
            "                               the committed plugin/, and run\n"
            "                               `claude plugin validate --strict` on it"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--out",
        metavar="DIR",
        help="build into DIR instead of the default ./plugin/ (repo root)",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify the committed plugin/ is up to date instead of building",
    )
    args = parser.parse_args()

    try:
        if args.check:
            return run_check()
        out_dir = os.path.abspath(args.out) if args.out else DEFAULT_OUT
        _guard_out_dir(out_dir)
        build(out_dir)
        print(f"OK: built plugin at {out_dir}")
        return 0
    except BuildError as e:
        sys.stderr.write(f"build-plugin.py: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
