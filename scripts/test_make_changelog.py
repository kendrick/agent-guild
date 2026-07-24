#!/usr/bin/env python3
"""Fixture-based tests for make-changelog.py and build-plugin.py's
version-has-section --check rule.

No repo state touched: every fixture is a from-scratch git repo built fresh
in a temp dir with synthetic version-bump commits, so these tests don't
depend on -- or drift with -- this repo's real history. make-changelog.py is
copied into the fixture repo's own scripts/ dir and run as a subprocess from
there: it resolves its ROOT from `__file__`, not cwd, so a copy planted
inside the fixture repo operates on the fixture repo, exactly like a real
checkout. The fixture repo carries a synthetic `origin` remote so
render_section's commit links have something real to derive from. The
--check rule is exercised by importing build-plugin.py's factored-out
check_changelog_section() directly against fixture paths, rather than
driving a full plugin build that has nothing to do with this rule.

Run: python3 scripts/test_make_changelog.py
"""
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
MAKE_CHANGELOG_SRC = os.path.join(REPO_ROOT, "make-changelog.py")
BUILD_PLUGIN_SRC = os.path.join(REPO_ROOT, "build-plugin.py")

# Matches the fixture's synthetic `origin` remote -- render_section derives
# commit links from it, so every rendered entry's URL should be built on
# this base.
BASE_URL = "https://github.com/test-org/test-fixture"

passed = failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {label}")
    else:
        failed += 1
        print(f"  FAIL {label}  {detail}")


def link(short_hash):
    """The exact `([hash](url))` markdown a rendered entry appends -- tests
    assert against this instead of hand-assembling the string inline at
    every call site."""
    return f"([{short_hash}]({BASE_URL}/commit/{short_hash}))"


def extract_section(text, version):
    """Independently re-derive a section's slice of CHANGELOG.md text (the
    heading through the char before the next `## ` heading), mirroring what
    the script's own _find_section does but implemented separately here so
    the test isn't just trusting the code under test to grade itself."""
    m = re.search(rf"(?ms)^(## {re.escape(version)}\b.*?)(?=^## |\Z)", text)
    return m.group(1) if m else None


# --------------------------------------------------------------- fixture repo


def _git(repo, *args, env=None):
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, env=env
    )
    assert proc.returncode == 0, f"git {args} failed: {proc.stderr}"
    return proc.stdout


def _commit_env(date):
    return {
        **os.environ,
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.com",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.com",
    }


def _commit(repo, message, date, files):
    """Write FILES (relpath -> content) and commit them with a fixed author
    and committer date, so section dates and commit ordering are
    deterministic instead of depending on wall-clock time. Stages
    everything (-A) -- fine for building the synthetic history, but callers
    simulating an uncommitted manifest bump alongside other work must stage
    explicitly instead (see the in-flight tests below)."""
    for relpath, content in files.items():
        full = os.path.join(repo, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message, env=_commit_env(date))
    return _git(repo, "rev-parse", "--short", "HEAD").strip()


def _commit_paths(repo, message, date, relpaths, files):
    """Write FILES and commit only RELPATHS -- used where an uncommitted
    manifest bump must stay uncommitted while an unrelated work commit
    lands, which `git add -A` would sweep in and ruin."""
    for relpath, content in files.items():
        full = os.path.join(repo, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    _git(repo, "add", *relpaths)
    _git(repo, "commit", "-q", "-m", message, env=_commit_env(date))
    return _git(repo, "rev-parse", "--short", "HEAD").strip()


def _plugin_json(version):
    return json.dumps({"name": "fixture-plugin", "version": version}, indent=2) + "\n"


MANIFEST_REL = os.path.join("scripts", "plugin-src", "plugin.json")


def build_fixture_repo():
    """A scratch repo with two synthetic version bumps (1.0.0, then 1.1.0)
    covering all five subject groups (feat, fix, docs, chore, and an
    unconventional subject for the catch-all) split across the two
    sections, a synthetic `origin` remote for commit-link derivation, and
    make-changelog.py copied into scripts/ so it runs against this repo,
    not the real one."""
    repo = tempfile.mkdtemp(prefix="make-changelog-test-")
    _git(repo, "init", "-q")
    _git(repo, "remote", "add", "origin", "git@github.com:test-org/test-fixture.git")

    hashes = {}
    hashes["readme"] = _commit(
        repo,
        "docs: scaffold scratch repo",
        "2024-01-01T09:00:00",
        {"README.md": "fixture repo\n"},
    )
    hashes["v1.0.0"] = _commit(
        repo,
        "chore(release): create plugin.json at 1.0.0",
        "2024-01-02T09:00:00",
        {MANIFEST_REL: _plugin_json("1.0.0")},
    )
    hashes["feat"] = _commit(
        repo,
        "feat(alpha): add the alpha feature",
        "2024-01-03T09:00:00",
        {"alpha.py": "# alpha\n"},
    )
    hashes["fix"] = _commit(
        repo,
        "fix(alpha): correct an off-by-one in alpha",
        "2024-01-04T09:00:00",
        {"alpha.py": "# alpha, fixed\n"},
    )
    hashes["docs"] = _commit(
        repo,
        "docs(alpha): document the alpha feature",
        "2024-01-05T09:00:00",
        {"ALPHA.md": "# Alpha\n"},
    )
    hashes["other"] = _commit(
        repo,
        "tidy up formatting",
        "2024-01-06T09:00:00",
        {"alpha.py": "# alpha, fixed and tidy\n"},
    )
    hashes["v1.1.0"] = _commit(
        repo,
        "chore(release): bump to 1.1.0",
        "2024-01-07T09:00:00",
        {MANIFEST_REL: _plugin_json("1.1.0")},
    )

    script_dst = os.path.join(repo, "scripts", "make-changelog.py")
    shutil.copy2(MAKE_CHANGELOG_SRC, script_dst)
    return repo, hashes


def run_generator(repo, *argv):
    script = os.path.join(repo, "scripts", "make-changelog.py")
    proc = subprocess.run(
        [sys.executable, script, *argv], cwd=repo, capture_output=True, text=True
    )
    return proc.returncode, proc.stdout, proc.stderr


def changelog_text(repo):
    path = os.path.join(repo, "CHANGELOG.md")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


# ------------------------------------------------------- section generation

print("section generation and grouping (first synthetic bump, no predecessor)")
repo, h = build_fixture_repo()
try:
    rc, out, err = run_generator(repo, "1.0.0")
    check("1.0.0: exit 0", rc == 0, f"rc={rc} err={err}")
    text = changelog_text(repo)
    header = text[: text.index("## 1.0.0")]
    check("1.0.0: header names the generator", "make-changelog.py" in header, header)
    check("1.0.0: section heading present", "## 1.0.0 — 2024-01-02" in text, text)
    check(
        "1.0.0: Documentation group has the readme commit, prefix stripped, unscoped",
        f"- scaffold scratch repo {link(h['readme'])}" in text,
        text,
    )
    check(
        "1.0.0: Chores group has the plugin.json commit, bold scope",
        f"- **release:** create plugin.json at 1.0.0 {link(h['v1.0.0'])}" in text,
        text,
    )
    check(
        "1.0.0: raw docs: prefix does not survive",
        "docs: scaffold scratch repo" not in text,
        text,
    )
    check(
        "1.0.0: raw chore(release): prefix does not survive",
        "chore(release):" not in text,
        text,
    )
    check(
        "1.0.0: does not include commits after its own boundary",
        h["feat"] not in text,
        text,
    )

    print("section generation and grouping (second synthetic bump, all five groups)")
    rc, out, err = run_generator(repo, "1.1.0")
    check("1.1.0: exit 0", rc == 0, f"rc={rc} err={err}")
    text = changelog_text(repo)
    section = extract_section(text, "1.1.0")
    check("1.1.0: section heading present", "## 1.1.0 — 2024-01-07" in text, text)

    # ------------------------------------------------- format-grammar golden
    # This section touches all five groups in one shot -- feat, fix, docs,
    # and chore commits plus one unconventional subject -- so it doubles as
    # the golden assertion for C-1's rendering grammar: every named heading,
    # bold-scope entries, an unscoped entry with no bold prefix, linked
    # hashes, and no raw `type(scope):` prefix anywhere.
    for heading in ("### Features", "### Bug Fixes", "### Documentation", "### Chores", "### Other"):
        check(f"1.1.0: golden section has heading {heading!r}", heading in section, section)
    check(
        "1.1.0: Features entry is bold-scoped and linked",
        f"- **alpha:** add the alpha feature {link(h['feat'])}" in section,
        section,
    )
    check(
        "1.1.0: Bug Fixes entry is bold-scoped and linked",
        f"- **alpha:** correct an off-by-one in alpha {link(h['fix'])}" in section,
        section,
    )
    check(
        "1.1.0: Documentation entry is bold-scoped and linked",
        f"- **alpha:** document the alpha feature {link(h['docs'])}" in section,
        section,
    )
    check(
        "1.1.0: Chores entry (own boundary commit, inclusive) is bold-scoped and linked",
        f"- **release:** bump to 1.1.0 {link(h['v1.1.0'])}" in section,
        section,
    )
    check(
        "1.1.0: Other entry keeps its unconventional subject verbatim, no bold scope",
        f"- tidy up formatting {link(h['other'])}" in section,
        section,
    )
    check(
        "1.1.0: unscoped entry has no bold-scope prefix at all",
        "**tidy" not in section and "**: tidy" not in section,
        section,
    )
    for raw_prefix in ("feat(alpha):", "fix(alpha):", "docs(alpha):", "chore(release):"):
        check(f"1.1.0: raw prefix {raw_prefix!r} does not survive", raw_prefix not in section, section)

    print("boundary detection: 1.1.0's section excludes 1.0.0's commits")
    check(
        "the readme commit (part of 1.0.0's range) is absent from 1.1.0's section",
        h["readme"] not in section,
        section,
    )
    check(
        "the 1.0.0 boundary commit itself is absent from 1.1.0's section",
        h["v1.0.0"] not in section,
        section,
    )

    print("double-run refusal (released version)")
    rc, out, err = run_generator(repo, "1.1.0")
    check("regenerating an existing section: nonzero exit", rc != 0, f"rc={rc}")
    check("regenerating an existing section: names 1.1.0 in the error", "1.1.0" in err, err)
    check(
        "regenerating an existing section: file has exactly one 1.1.0 heading",
        changelog_text(repo).count("## 1.1.0") == 1,
        changelog_text(repo),
    )

    print("--notes prints an existing section")
    rc, out, err = run_generator(repo, "--notes", "1.0.0")
    check("--notes 1.0.0: exit 0", rc == 0, f"rc={rc} err={err}")
    check("--notes 1.0.0: prints the heading", out.startswith("## 1.0.0 — 2024-01-02"), out)
    check(
        "--notes 1.0.0: prints its entry verbatim",
        f"- **release:** create plugin.json at 1.0.0 {link(h['v1.0.0'])}" in out,
        out,
    )
    check(
        "--notes 1.0.0: does not bleed into 1.1.0's section",
        "1.1.0" not in out,
        out,
    )

    print("--notes exits nonzero naming a missing section")
    rc, out, err = run_generator(repo, "--notes", "9.9.9")
    check("--notes 9.9.9 (missing): nonzero exit", rc != 0, f"rc={rc}")
    check("--notes 9.9.9 (missing): stdout is empty", out == "", out)
    check("--notes 9.9.9 (missing): names the missing version in stderr", "9.9.9" in err, err)

    print("argument validation")
    rc, out, err = run_generator(repo)
    check("no VERSION and no --notes: nonzero exit", rc != 0, f"rc={rc}")
    rc, out, err = run_generator(repo, "1.2.0", "--notes", "1.0.0")
    check("both VERSION and --notes: nonzero exit", rc != 0, f"rc={rc}")

    print("generating a version with neither a boundary commit nor a matching worktree bump refuses cleanly")
    rc, out, err = run_generator(repo, "9.9.9")
    check("ungenerated/nonexistent version: nonzero exit", rc != 0, f"rc={rc}")
    check("ungenerated/nonexistent version: names it in stderr", "9.9.9" in err, err)

    # --------------------------------------------------------- in-flight (C-1)

    print("in-flight generation: worktree-bumped manifest, no boundary commit yet")
    # A work commit lands after 1.1.0's release, still at version 1.1.0 --
    # this is what the in-flight section for 1.2.0 should pick up.
    beta_hash = _commit(
        repo,
        "feat(beta): add the beta feature",
        "2024-01-08T09:00:00",
        {"beta.py": "# beta\n"},
    )
    # Bump the manifest in the working tree only -- deliberately not
    # committed, simulating step 1 of the two-commit release ritual before
    # step 5's release commit exists.
    manifest_path = os.path.join(repo, MANIFEST_REL)
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(_plugin_json("1.2.0"))

    today = datetime.date.today().isoformat()
    rc, out, err = run_generator(repo, "1.2.0")
    check("in-flight 1.2.0: exit 0", rc == 0, f"rc={rc} err={err}")
    text = changelog_text(repo)
    check("in-flight 1.2.0: section dated today, not a commit date", f"## 1.2.0 — {today}" in text, text)
    section = extract_section(text, "1.2.0")
    check(
        "in-flight 1.2.0: covers the post-1.1.0 work commit",
        f"- **beta:** add the beta feature {link(beta_hash)}" in section,
        section,
    )
    check("in-flight 1.2.0: excludes 1.1.0's own commits", h["v1.1.0"] not in section, section)
    check(
        "in-flight 1.2.0: the uncommitted manifest bump stays uncommitted",
        _git(repo, "status", "--porcelain").strip() != "",
        "expected a dirty worktree (the bump is still unstaged)",
    )

    print("in-flight refresh: rerunning replaces the provisional section, no duplicate")
    # Another work commit lands while the manifest bump is *still*
    # uncommitted -- stage only the new file (git add -A would sweep the
    # pending manifest bump into this commit and end the in-flight state
    # early, which isn't what this case is testing).
    beta2_hash = _commit_paths(
        repo,
        "fix(beta): correct a beta rounding error",
        "2024-01-09T09:00:00",
        ["beta2.py"],
        {"beta2.py": "# beta, fixed\n"},
    )
    rc, out, err = run_generator(repo, "1.2.0")
    check("in-flight refresh: exit 0", rc == 0, f"rc={rc} err={err}")
    text = changelog_text(repo)
    check(
        "in-flight refresh: file still has exactly one 1.2.0 heading (replaced, not duplicated)",
        text.count("## 1.2.0") == 1,
        text,
    )
    section = extract_section(text, "1.2.0")
    check(
        "in-flight refresh: picks up the commit that landed since the first run",
        f"- **beta:** correct a beta rounding error {link(beta2_hash)}" in section,
        section,
    )
    check(
        "in-flight refresh: still carries the original beta commit",
        beta_hash in section,
        section,
    )
    check("in-flight refresh: still dated today", f"## 1.2.0 — {today}" in text, text)

    print("in-flight -> released transition: committing the bump makes reruns refuse, not replace")
    # Now land the actual release commit: the manifest bump plus nothing
    # else, matching the two-commit ritual's mechanical release commit.
    _git(repo, "add", MANIFEST_REL)
    _git(repo, "commit", "-q", "-m", "chore(release): bump to 1.2.0", env=_commit_env("2024-01-10T09:00:00"))
    rc, out, err = run_generator(repo, "1.2.0")
    check("released 1.2.0 rerun: nonzero exit (history is immutable once released)", rc != 0, f"rc={rc}")
    check("released 1.2.0 rerun: names 1.2.0 in the error", "1.2.0" in err, err)
    check(
        "released 1.2.0 rerun: CHANGELOG.md untouched (still exactly one 1.2.0 heading)",
        changelog_text(repo).count("## 1.2.0") == 1,
        changelog_text(repo),
    )
finally:
    shutil.rmtree(repo, ignore_errors=True)


# --------------------------------------------------------- --check rule (C-3)

print("build-plugin.py --check: version-has-section rule, both directions")

spec = importlib.util.spec_from_file_location("build_plugin_under_test", BUILD_PLUGIN_SRC)
build_plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_plugin)

check_repo = tempfile.mkdtemp(prefix="make-changelog-check-test-")
try:
    manifest_path = os.path.join(check_repo, "plugin.json")
    changelog_path = os.path.join(check_repo, "CHANGELOG.md")

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(_plugin_json("2.0.0"))

    build_plugin.PLUGIN_SRC_MANIFEST = manifest_path
    build_plugin.CHANGELOG_PATH = changelog_path

    problem = build_plugin.check_changelog_section()
    check(
        "bumped-but-sectionless manifest (no CHANGELOG.md at all): rule fails",
        problem is not None,
        problem,
    )
    check(
        "failure message names make-changelog.py as the fix",
        problem is not None and "make-changelog.py" in problem,
        problem,
    )
    check(
        "failure message names the missing version",
        problem is not None and "2.0.0" in problem,
        problem,
    )

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write("# Changelog\n\n## 1.9.0 — 2024-01-01\n\n### Chores\n- **release:** something (`abc1234`)\n")
    problem = build_plugin.check_changelog_section()
    check(
        "CHANGELOG.md present but missing this version's section: rule still fails",
        problem is not None,
        problem,
    )

    with open(changelog_path, "a", encoding="utf-8") as f:
        f.write("\n## 2.0.0 — 2024-01-08\n\n### Chores\n- **release:** bump to 2.0.0 (`def5678`)\n")
    problem = build_plugin.check_changelog_section()
    check("section now present: rule passes (returns None)", problem is None, problem)
finally:
    shutil.rmtree(check_repo, ignore_errors=True)


print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
