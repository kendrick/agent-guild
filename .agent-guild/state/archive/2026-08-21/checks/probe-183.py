#!/usr/bin/env python3
"""Probes for #183's constitution, one subcommand per behavior clause.

Each probe drives the packaged Claude installer, plugin/project-template/install.py,
end to end in a throwaway directory under the system tmpdir, then reads what the
installer actually did. None of them read the test suites: a check that greps test
source can be satisfied by comment lines (#141), so these build the artifact and
inspect it.

Every probe that mutates its venue asserts the mutation landed before re-running
the installer. A mutation that silently failed makes every later assertion report
success against a run that did nothing.

Contract pinned by C-1 (the clauses cite it, the probes enforce it):
  .agent-guild/provenance.json is a JSON object with exactly two keys:
    version: string, the plugin version that wrote the payload, equal to the
             "version" field of the host package's own manifest beside the
             installer's project-template/ root (.claude-plugin/plugin.json for
             the Claude package, .codex-plugin/plugin.json for the Codex one);
             these probes drive the Claude package, so MANIFEST is that one
    files:   object mapping project-root-relative payload paths, "/"-separated
             (e.g. ".agent-guild/CLAUDE.md"), to lowercase hex sha256 of the
             bytes as shipped
  The payload scope is the payload set install() computes: under .agent-guild/,
  excluding state/, the record itself, and the Codex repo-local hooks/, which
  install() splits out and copies with _copy_owned so they upgrade on every
  re-init. Provenance governs only what _copy_missing can preserve; see
  the paragraph in docs/installing.md saying install() splits those hooks
  out of the payload before the drift check runs, and payload_files() below.

Exit 0 = the clause holds. Any assertion failure exits nonzero with the reason.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
INSTALLER = os.path.join(REPO, "plugin", "project-template", "install.py")
CODEX_INSTALLER = os.path.join(
    REPO, "plugins", "agent-guild", "project-template", "install.py"
)
CODEX_MANIFEST = os.path.join(
    REPO, "plugins", "agent-guild", ".codex-plugin", "plugin.json"
)
SOURCE_PAYLOAD = os.path.join(
    REPO, "plugin", "project-template", ".agent-guild"
)
MANIFEST = os.path.join(REPO, "plugin", ".claude-plugin", "plugin.json")
NUDGE = os.path.join(REPO, "plugin", "hooks", "session-nudge.py")
CODEX_NUDGE = os.path.join(
    REPO, "plugins", "agent-guild", "hooks", "session-nudge.py"
)
PROV_REL = ".agent-guild/provenance.json"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def current_version():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)["version"]


# Probes execute scripts inside the tracked plugin/ tree, which build-plugin's
# --check diffs byte for byte, so a stray __pycache__ from a probe run would
# fail C-8. No bytecode, ever.
_ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def install(target):
    return subprocess.run(
        [sys.executable, INSTALLER, "claude", target],
        capture_output=True,
        text=True,
        env=_ENV,
    )


def fresh(tmp):
    r = install(tmp)
    assert r.returncode == 0, f"fresh install failed: {r.stderr!r}"
    return r


def payload_files(root):
    """The payload set install() computes: not everything under .agent-guild/.

    The Codex repo-local hooks land under .agent-guild/hooks/ on the
    --project-skills route and look like payload, but install() splits them out
    before the drift check and copies them with _copy_owned, so they are
    overwritten on every re-init and provenance has nothing to decide about
    them (docs/installing.md draws the same line, where it says install() splits
    those hooks out of the payload before the drift check runs).
    """
    out = []
    base = os.path.join(root, ".agent-guild")
    for dirpath, _dirnames, filenames in os.walk(base):
        rel_dir = os.path.relpath(dirpath, base)
        if rel_dir == "state" or rel_dir.startswith("state" + os.sep):
            continue
        if rel_dir == "hooks" or rel_dir.startswith("hooks" + os.sep):
            continue
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            key = rel.replace(os.sep, "/")
            if key == PROV_REL:
                continue
            out.append(key)
    return sorted(out)


def load_prov(root):
    path = os.path.join(root, PROV_REL)
    assert os.path.isfile(path), f"provenance record missing: {path}"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_prov(root, prov):
    path = os.path.join(root, PROV_REL)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prov, f)
    reread = load_prov(root)
    assert reread == prov, "provenance rewrite did not land"


def venue():
    return tempfile.mkdtemp(prefix="probe183-")


def source_bytes(key):
    rel = key[len(".agent-guild/"):]
    with open(os.path.join(SOURCE_PAYLOAD, rel), encoding="utf-8") as f:
        return f.read()


def _assert_record_covers(tmp, label, version=None):
    prov = load_prov(tmp)
    assert set(prov) == {"version", "files"}, f"{label}: keys {sorted(prov)!r}"
    ver = version or current_version()
    assert prov["version"] == ver, f"{label}: {prov['version']!r} != plugin {ver!r}"
    files = prov["files"]
    assert PROV_REL not in files, f"{label}: the record lists itself"
    expected = payload_files(tmp)
    assert set(files) == set(expected), (
        f"{label}: entry set diverges from installed payload: "
        f"missing={sorted(set(expected) - set(files))!r} "
        f"extra={sorted(set(files) - set(expected))!r}"
    )
    for key in expected:
        on_disk = sha256(os.path.join(tmp, key.replace("/", os.sep)))
        assert files[key] == on_disk, f"{label}: hash mismatch for {key}"


def pinned_package(kind):
    """Copy a shipped package and set its manifest to a version nothing carries.

    Returns (package_root, version). Both packages' manifests derive from one
    scripts/plugin-src/plugin.json, so every real fixture runs at the single
    string both already claim and a compiled-in version passes. This is the only
    way to falsify "reads the running version from its own package's manifest".
    """
    src = os.path.join(REPO, "plugin") if kind == "claude" else os.path.join(
        REPO, "plugins", "agent-guild"
    )
    manifest_rel = (
        os.path.join(".claude-plugin", "plugin.json")
        if kind == "claude"
        else os.path.join(".codex-plugin", "plugin.json")
    )
    dest = os.path.join(tempfile.mkdtemp(prefix="probe183-pkg-"), "pkg")
    shutil.copytree(src, dest)
    manifest_path = os.path.join(dest, manifest_rel)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["version"] = "9.9.9"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with open(manifest_path, encoding="utf-8") as f:
        assert json.load(f)["version"] == "9.9.9", "manifest rewrite did not land"
    return dest, "9.9.9"


def c1():
    # The Codex arm first: an implementation that writes the record only on the
    # claude branch leaves every Codex project pre-provenance forever, and the
    # suites carry no provenance assertions to catch it.
    codex_tmp = venue()
    rc = subprocess.run(
        [sys.executable, CODEX_INSTALLER, "codex", codex_tmp],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rc.returncode == 0, f"codex install failed: {rc.stderr!r}"
    codex_prov = load_prov(codex_tmp)
    with open(CODEX_MANIFEST, encoding="utf-8") as f:
        codex_ver = json.load(f)["version"]
    assert codex_prov["version"] == codex_ver, (
        f"codex record stamped {codex_prov['version']!r}, manifest {codex_ver!r}"
    )
    assert set(codex_prov) == {"version", "files"}, (
        f"codex record carries extra keys: {sorted(codex_prov)!r}"
    )
    codex_expected = payload_files(codex_tmp)
    assert set(codex_prov["files"]) == set(codex_expected), (
        "codex record does not cover the codex payload: "
        f"missing={sorted(set(codex_expected) - set(codex_prov['files']))!r} "
        f"extra={sorted(set(codex_prov['files']) - set(codex_expected))!r}"
    )
    for key in codex_expected:
        on_disk = sha256(os.path.join(codex_tmp, key.replace("/", os.sep)))
        assert codex_prov["files"][key] == on_disk, f"codex hash mismatch for {key}"
    stale = dict(codex_prov, version="0.0.1")
    write_prov(codex_tmp, stale)
    assert load_prov(codex_tmp)["version"] == "0.0.1", "stamp-down did not land"
    rc2 = subprocess.run(
        [sys.executable, CODEX_INSTALLER, "codex", codex_tmp],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rc2.returncode == 0, f"codex idempotent re-run failed: {rc2.stderr!r}"
    _assert_record_covers(codex_tmp, "codex re-run", version=codex_ver)

    # The Codex branch gets the pinned-manifest treatment too. Both shipped
    # manifests carry the same string, so an arm that reads only the real ones
    # cannot separate a lookup from a literal on either host.
    codex_pkg, codex_pinned = pinned_package("codex")
    codex_pinned_tmp = venue()
    rcp = subprocess.run(
        [
            sys.executable,
            os.path.join(codex_pkg, "project-template", "install.py"),
            "codex",
            codex_pinned_tmp,
        ],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rcp.returncode == 0, f"pinned codex install failed: {rcp.stderr!r}"
    assert load_prov(codex_pinned_tmp)["version"] == codex_pinned, (
        "the codex stamp does not come from the installing package's manifest: "
        f"{load_prov(codex_pinned_tmp)['version']!r} != {codex_pinned!r}"
    )
    shutil.rmtree(os.path.dirname(codex_pkg), ignore_errors=True)

    # The third shipped shape: the repo-local Codex bootstrap, which lands the
    # hook scripts under .agent-guild/hooks/. They are _copy_owned, so the
    # record must not carry them, and this is the only arm that can tell.
    skills_tmp = venue()
    rs = subprocess.run(
        [sys.executable, CODEX_INSTALLER, "codex", skills_tmp, "--project-skills"],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rs.returncode == 0, f"codex --project-skills install failed: {rs.stderr!r}"
    hooks_dir = os.path.join(skills_tmp, ".agent-guild", "hooks")
    assert os.path.isdir(hooks_dir) and os.listdir(hooks_dir), (
        "fixture is not the repo-local shape: no hooks landed"
    )
    skills_prov = load_prov(skills_tmp)
    recorded_hooks = [k for k in skills_prov["files"] if k.startswith(".agent-guild/hooks/")]
    assert recorded_hooks == [], (
        f"record carries owned hook files it does not govern: {sorted(recorded_hooks)!r}"
    )
    assert set(skills_prov) == {"version", "files"}, (
        f"repo-local record carries extra keys: {sorted(skills_prov)!r}"
    )
    assert skills_prov["version"] == codex_ver, (
        f"repo-local record stamped {skills_prov['version']!r}, manifest {codex_ver!r}"
    )
    skills_expected = payload_files(skills_tmp)
    assert set(skills_prov["files"]) == set(skills_expected), (
        "repo-local record does not cover the payload: "
        f"missing={sorted(set(skills_expected) - set(skills_prov['files']))!r} "
        f"extra={sorted(set(skills_prov['files']) - set(skills_expected))!r}"
    )
    for key in skills_expected:
        on_disk = sha256(os.path.join(skills_tmp, key.replace("/", os.sep)))
        assert skills_prov["files"][key] == on_disk, (
            f"repo-local hash mismatch for {key}"
        )
    rs2 = subprocess.run(
        [sys.executable, CODEX_INSTALLER, "codex", skills_tmp, "--project-skills"],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rs2.returncode == 0, f"repo-local re-run failed: {rs2.stderr!r}"
    skills_prov2 = load_prov(skills_tmp)
    rerun_hooks = [
        k for k in skills_prov2["files"] if k.startswith(".agent-guild/hooks/")
    ]
    assert rerun_hooks == [], (
        f"the re-run recorded owned hook files: {sorted(rerun_hooks)!r}"
    )
    _assert_record_covers(skills_tmp, "repo-local re-run", version=codex_ver)

    pkg_root, pinned = pinned_package("claude")
    pinned_tmp = venue()
    rp = subprocess.run(
        [
            sys.executable,
            os.path.join(pkg_root, "project-template", "install.py"),
            "claude",
            pinned_tmp,
        ],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rp.returncode == 0, f"pinned-package install failed: {rp.stderr!r}"
    assert load_prov(pinned_tmp)["version"] == pinned, (
        "the stamp does not come from the installing package's manifest: "
        f"{load_prov(pinned_tmp)['version']!r} != {pinned!r}"
    )
    shutil.rmtree(os.path.dirname(pkg_root), ignore_errors=True)

    tmp = venue()
    fresh(tmp)
    _assert_record_covers(tmp, "fresh install")
    # A record built only from the files this run copied looks complete on a
    # fresh install, where every file is copied. The idempotent re-run copies
    # nothing, so it is the run that separates a whole-payload record from one
    # scoped to the current run's writes.
    stale_claude = dict(load_prov(tmp), version="0.0.1")
    write_prov(tmp, stale_claude)
    assert load_prov(tmp)["version"] == "0.0.1", "stamp-down did not land"
    r = install(tmp)
    assert r.returncode == 0, f"idempotent re-run failed: {r.stderr!r}"
    _assert_record_covers(tmp, "re-run on an already-initialized project")


def c2():
    tmp = venue()
    fresh(tmp)
    # TWO stale-but-clean files, because "every payload file whose bytes match
    # its recorded hash" cannot be exercised on a set of one: an implementation
    # upgrading only the first passes that.
    keys = [".agent-guild/scripts/ready-set.py", ".agent-guild/templates/task.md"]
    marker = "# older release shipped different bytes\n"
    prov = load_prov(tmp)
    for k in keys:
        t = os.path.join(tmp, k.replace("/", os.sep))
        with open(t, "a", encoding="utf-8") as f:
            f.write(marker)
        with open(t, encoding="utf-8") as f:
            assert f.read().endswith(marker), f"edit to {k} did not land"
        prov["files"][k] = sha256(t)
    prov["version"] = "0.0.1"
    write_prov(tmp, prov)
    r = install(tmp)
    assert r.returncode == 0, f"upgrade run failed: {r.stderr!r}"
    prov2 = load_prov(tmp)
    for k in keys:
        t = os.path.join(tmp, k.replace("/", os.sep))
        with open(t, encoding="utf-8") as f:
            assert f.read() == source_bytes(k), f"stale-but-clean {k} was not upgraded"
        assert prov2["files"][k] == sha256(t), f"hash not restamped for {k}"
    key = keys[0]
    target = os.path.join(tmp, key.replace("/", os.sep))
    assert prov2["version"] == current_version(), "stamp not advanced"
    # Exactly one file's bytes differed from source, so exactly one moved and
    # every other payload file is unchanged. Reading only the updated term lets
    # an implementation report the rest as `preserved` — the issue's own
    # headline symptom, naming files the user never touched.
    m = re.search(
        r"payload=(\d+) updated/(\d+) unchanged/(\d+) preserved", r.stdout
    )
    assert m, f"summary carries no payload triple: {r.stdout!r}"
    updated, unchanged, preserved = (int(g) for g in m.groups())
    total = len(payload_files(tmp))
    assert updated == len(keys), (
        f"summary counts {updated} moved, expected {len(keys)}: {r.stdout!r}"
    )
    assert preserved == 0, f"summary preserves a file nobody edited: {r.stdout!r}"
    assert unchanged == total - len(keys), (
        f"summary loses files: {r.stdout!r} against {total} payload files"
    )

    # The stamp does not gate the per-file decision. This arm holds the record
    # at the CURRENT version while a file is clean against its recorded hash and
    # differs from source, which is the state an implementation reading "trails
    # the plugin's" as a precondition skips forever.
    tmp2 = venue()
    fresh(tmp2)
    target2 = os.path.join(tmp2, key.replace("/", os.sep))
    with open(target2, "a", encoding="utf-8") as f:
        f.write(marker)
    with open(target2, encoding="utf-8") as f:
        assert f.read().endswith(marker), "edit did not land"
    prov2 = load_prov(tmp2)
    prov2["files"][key] = sha256(target2)
    assert prov2["version"] == current_version(), "arm requires a current stamp"
    write_prov(tmp2, prov2)
    r2 = install(tmp2)
    assert r2.returncode == 0, f"current-stamp run failed: {r2.stderr!r}"
    with open(target2, encoding="utf-8") as f:
        assert f.read() == source_bytes(key), (
            "a file clean against its record was skipped because the stamp matched"
        )


def c3():
    tmp = venue()
    fresh(tmp)
    key_a = ".agent-guild/CLAUDE.md"
    key_b = ".agent-guild/scripts/ready-set.py"
    key_c = ".agent-guild/templates/task.md"
    # TWO edited files, because a one-element set assertion proves only that a
    # set has one element: an implementation reporting just the first conflict
    # passes it, and the spec's own repro (spec.md:43-46) edits two.
    key_d = ".agent-guild/schemas/verdict.schema.json"
    path_a = os.path.join(tmp, key_a.replace("/", os.sep))
    path_b = os.path.join(tmp, key_b.replace("/", os.sep))
    path_c = os.path.join(tmp, key_c.replace("/", os.sep))
    path_d = os.path.join(tmp, key_d.replace("/", os.sep))
    edit_a = "\n<!-- real local edit, never restamped -->\n"
    edit_d = "\n"
    with open(path_a, "a", encoding="utf-8") as f:
        f.write(edit_a)
    with open(path_d, "a", encoding="utf-8") as f:
        f.write(edit_d)
    with open(path_b, "a", encoding="utf-8") as f:
        f.write("# stale but clean against its recorded hash\n")
    os.remove(path_c)
    prov = load_prov(tmp)
    prov["files"][key_b] = sha256(path_b)
    prov["version"] = "0.0.1"
    write_prov(tmp, prov)
    with open(path_a, encoding="utf-8") as f:
        edited_a = f.read()
    with open(path_d, encoding="utf-8") as f:
        edited_d = f.read()
    assert edited_a.endswith(edit_a), "edit to A did not land"
    assert edited_d.endswith(edit_d), "edit to D did not land"
    assert prov["files"][key_a] != sha256(path_a), "A must diverge from its record"
    assert prov["files"][key_d] != sha256(path_d), "D must diverge from its record"
    assert not os.path.exists(path_c), "delete of C did not land"
    r = install(tmp)
    assert r.returncode == 0, f"mixed run failed: {r.stderr!r}"
    with open(path_a, encoding="utf-8") as f:
        assert f.read() == edited_a, "locally edited file was overwritten"
    # The set, not two spot checks. An implementation that reports every file
    # it did not write as preserved names 37 paths the user never touched and
    # still passes `key_b not in stdout` — that warning is the defect the issue
    # was filed about, reproduced verbatim.
    with open(path_d, encoding="utf-8") as f:
        assert f.read() == edited_d, "second locally edited file was overwritten"
    named = sorted(p for p in payload_files(tmp) if p in r.stdout)
    assert named == sorted([key_a, key_d]), (
        f"diagnostic names {named!r}, not exactly the two edits: {r.stdout!r}"
    )
    with open(path_b, encoding="utf-8") as f:
        assert f.read() == source_bytes(key_b), "clean stale file was not upgraded"
    assert os.path.isfile(path_c), "net-new file did not land"
    with open(path_c, encoding="utf-8") as f:
        assert f.read() == source_bytes(key_c), "net-new file diverges from source"
    # The refusal has to survive the version bump the same run performed. A run
    # that preserves the edit and then restamps its entry from the bytes on
    # disk passes everything above, and then overwrites the user's edit on the
    # next release, because by then the edit reads as clean.
    prov_after = load_prov(tmp)
    assert prov_after["files"][key_a] == prov["files"][key_a], (
        "a preserved file's recorded hash was refreshed from its on-disk bytes"
    )
    # A run that preserves something still advances the stamp. Holding the
    # version back whenever there are conflicts leaves a user with one local
    # edit pinned forever: the payload upgrades, the stamp never moves, and the
    # nudge fires every session with nothing that clears it.
    assert prov_after["version"] == current_version(), (
        f"a run that preserved a file left the stamp at {prov_after['version']!r}"
    )
    prov_after["version"] = "0.0.2"
    write_prov(tmp, prov_after)
    r2 = install(tmp)
    assert r2.returncode == 0, f"next-release run failed: {r2.stderr!r}"
    with open(path_a, encoding="utf-8") as f:
        assert f.read() == edited_a, "the next release overwrote the preserved edit"
    assert key_a in r2.stdout, f"the next release stops refusing the edit: {r2.stdout!r}"


def c4():
    tmp = venue()
    fresh(tmp)
    key_a = ".agent-guild/CLAUDE.md"
    key_b = ".agent-guild/scripts/ready-set.py"
    key_d = ".agent-guild/schemas/verdict.schema.json"
    path_a = os.path.join(tmp, key_a.replace("/", os.sep))
    path_d = os.path.join(tmp, key_d.replace("/", os.sep))
    edit_a = "\n<!-- local edit predating provenance -->\n"
    edit_d = "\n"
    with open(path_a, "a", encoding="utf-8") as f:
        f.write(edit_a)
    with open(path_d, "a", encoding="utf-8") as f:
        f.write(edit_d)
    os.remove(os.path.join(tmp, PROV_REL))
    with open(path_a, encoding="utf-8") as f:
        edited_a = f.read()
    with open(path_d, encoding="utf-8") as f:
        edited_d = f.read()
    assert edited_a.endswith(edit_a), "edit to A did not land"
    assert edited_d.endswith(edit_d), "edit to D did not land"
    assert not os.path.exists(os.path.join(tmp, PROV_REL)), "record removal did not land"
    r = install(tmp)
    assert r.returncode == 0, f"adoption run failed: {r.stderr!r}"
    prov = load_prov(tmp)
    assert prov["version"] == current_version(), "adopted stamp is not current"
    assert prov["files"][key_b] == sha256(
        os.path.join(tmp, key_b.replace("/", os.sep))
    ), "matching file was not adopted at its on-disk bytes"
    # A differing file is not adopted at all: stamping it under any hash makes a
    # later run's comparison meaningless, so it carries no entry until a run
    # legitimately writes it.
    assert key_a not in prov["files"], (
        "adoption recorded an entry for a file it refused"
    )
    assert key_d not in prov["files"], (
        "adoption recorded an entry for the second file it refused"
    )
    refused = {key_a, key_d}
    adopted_expected = {k for k in payload_files(tmp) if k not in refused}
    assert set(prov["files"]) == adopted_expected, (
        "adopted record is not exactly the matching files: "
        f"missing={sorted(adopted_expected - set(prov['files']))!r} "
        f"extra={sorted(set(prov['files']) - adopted_expected)!r}"
    )
    for k in sorted(adopted_expected):
        on_disk = sha256(os.path.join(tmp, k.replace("/", os.sep)))
        assert prov["files"][k] == on_disk, f"adopted hash mismatch for {k}"
    named_adopt = sorted(p for p in payload_files(tmp) if p in r.stdout)
    assert named_adopt == sorted([key_a, key_d]), (
        f"adoption names {named_adopt!r}, not exactly the two differing files: {r.stdout!r}"
    )
    with open(path_a, encoding="utf-8") as f:
        assert f.read() == edited_a, "adoption overwrote a local edit"
    assert key_a in r.stdout, f"adoption run does not report the differing file: {r.stdout!r}"
    r2 = install(tmp)
    assert r2.returncode == 0, f"post-adoption run failed: {r2.stderr!r}"
    with open(path_a, encoding="utf-8") as f:
        assert f.read() == edited_a, "post-adoption run overwrote the edit"
    with open(path_d, encoding="utf-8") as f:
        assert f.read() == edited_d, (
            "post-adoption run overwrote the second edit: wholesale trust, "
            "delayed by one re-init"
        )
    named_rerun = sorted(p for p in payload_files(tmp) if p in r2.stdout)
    assert named_rerun == sorted([key_a, key_d]), (
        f"post-adoption run names {named_rerun!r}, not both refused files: {r2.stdout!r}"
    )
    # The user's only escape hatch. Restoring the shipped bytes is exactly the
    # remedy the warning implies, so a run meeting a file with no entry whose
    # bytes match current source records it and stops warning. The alternative
    # warns forever with no action that clears it.
    with open(path_d, "w", encoding="utf-8") as f:
        f.write(source_bytes(key_d))
    with open(path_d, encoding="utf-8") as f:
        assert f.read() == source_bytes(key_d), "revert of D did not land"
    r3 = install(tmp)
    assert r3.returncode == 0, f"post-revert run failed: {r3.stderr!r}"
    prov3 = load_prov(tmp)
    assert prov3["files"].get(key_d) == sha256(path_d), (
        "a reverted file matching current source was not recorded"
    )
    assert key_d not in r3.stdout, (
        f"a reverted file is still reported as a local edit: {r3.stdout!r}"
    )
    assert key_a in r3.stdout, f"the still-edited file stopped being named: {r3.stdout!r}"


def tree_state(root):
    state = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            state[os.path.relpath(path, root)] = sha256(path)
    return state


def run_nudge(script, project, host):
    """Drive one nudge deployment and prove it wrote nothing.

    Every arm goes through here, because "byte-identical before and after" is a
    property of each run rather than of the one run a probe happens to snapshot.
    hook_host matters: session-nudge defaults to "claude", while a real Codex
    session always carries hook_host "codex" (codex-hook-adapter.py:230), so an
    arm that omits it exercises the Claude branch and calls it Codex coverage.
    """
    before = tree_state(project)
    r = subprocess.run(
        [sys.executable, script],
        input=json.dumps(
            {
                "cwd": project,
                "hook_event_name": "SessionStart",
                "session_id": "probe183",
                "hook_host": host,
            }
        ),
        capture_output=True,
        text=True,
        env=dict(_ENV, CLAUDE_PROJECT_DIR=project),
    )
    after = tree_state(project)
    assert after == before, (
        f"the nudge wrote to the project ({script}, host={host}): "
        f"added={sorted(set(after) - set(before))!r} "
        f"removed={sorted(set(before) - set(after))!r} "
        f"changed={sorted(k for k in set(after) & set(before) if after[k] != before[k])!r}"
    )
    return r


def c5():
    ver = current_version()

    # Arm 1, the Claude package against a stale project. The fixture is a real
    # install with its stamp edited down, not a hand-built skeleton: a project
    # holding only a marker and a record is also partially initialized, so the
    # partial-init nudge fires on it and the probe would be settling which
    # warning wins rather than checking this clause.
    tmp = venue()
    fresh(tmp)
    prov = load_prov(tmp)
    prov["version"] = "0.0.1"
    write_prov(tmp, prov)
    r = run_nudge(NUDGE, tmp, "claude")
    assert r.returncode == 0, f"nudge exited {r.returncode}: {r.stderr!r}"
    out = r.stdout
    assert "0.0.1" in out, f"stamped version missing from nudge output: {out!r}"
    assert ver in out, f"running plugin version missing from nudge output: {out!r}"
    assert "/agent-guild:init" in out, f"fix command missing from nudge output: {out!r}"
    assert "?" in out, f"nudge reports without asking whether to run it: {out!r}"

    # Arm 2, the silent direction. A gap message keyed on "a record exists"
    # rather than on the versions differing tells every user of an up-to-date
    # project to upgrade to the version they are already on, every session
    # start — what session-nudge.py's own docstring rules out.
    current = venue()
    fresh(current)
    r_quiet = run_nudge(NUDGE, current, "claude")
    assert r_quiet.returncode == 0, f"nudge exited {r_quiet.returncode} on a current project"
    assert ver not in r_quiet.stdout and "/agent-guild:init" not in r_quiet.stdout, (
        f"nudge reports a version gap on an up-to-date project: {r_quiet.stdout!r}"
    )

    # Arm 3, the Codex package. The running-version lookup reads the manifest of
    # the package the hook file ships inside, and that manifest is host-specific.
    codex_tmp = venue()
    rc = subprocess.run(
        [sys.executable, CODEX_INSTALLER, "codex", codex_tmp],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rc.returncode == 0, f"codex install failed: {rc.stderr!r}"
    codex_prov = load_prov(codex_tmp)
    codex_prov["version"] = "0.0.1"
    write_prov(codex_tmp, codex_prov)
    r_codex = run_nudge(CODEX_NUDGE, codex_tmp, "codex")
    assert r_codex.returncode == 0, f"codex nudge exited {r_codex.returncode}: {r_codex.stderr!r}"
    with open(CODEX_MANIFEST, encoding="utf-8") as f:
        codex_ver = json.load(f)["version"]
    out_c = r_codex.stdout
    assert "0.0.1" in out_c, f"codex nudge omits the stamped version: {out_c!r}"
    assert codex_ver in out_c, f"codex nudge omits the running version: {out_c!r}"
    assert "?" in out_c, f"codex nudge does not ask: {out_c!r}"
    assert "$init" in out_c, f"codex nudge names no runnable command: {out_c!r}"
    assert "/agent-guild:init" not in out_c, (
        f"codex session told to run the Claude command: {out_c!r}"
    )

    # Arm 3b, the version lookup itself. Both packages' manifests derive from
    # one scripts/plugin-src/plugin.json, so a hardcoded version string matches
    # every real manifest and no arm above can tell. Copy the Codex package,
    # move its manifest to a version nothing else carries, and run that copy's
    # nudge: only a real lookup reports it.
    for kind, project, host in (
        ("codex", codex_tmp, "codex"),
        ("claude", tmp, "claude"),
    ):
        pkg_root, pinned = pinned_package(kind)
        r_pinned = run_nudge(
            os.path.join(pkg_root, "hooks", "session-nudge.py"), project, host
        )
        assert r_pinned.returncode == 0, (
            f"copied {kind} package nudge failed: {r_pinned.stderr!r}"
        )
        assert pinned in r_pinned.stdout, (
            f"the {kind} nudge does not read its own package's manifest: "
            f"{r_pinned.stdout!r}"
        )
        shutil.rmtree(os.path.dirname(pkg_root), ignore_errors=True)

    # F5: the double-registration branch returns 0 before anything below it, and
    # #104 says this very repo is in that state. A gap notice written below that
    # return is silent exactly where the plugin is installed twice.
    both = venue()
    fresh(both)
    both_prov = load_prov(both)
    both_prov["version"] = "0.0.1"
    write_prov(both, both_prov)
    os.makedirs(os.path.join(both, ".claude"), exist_ok=True)
    settings = os.path.join(both, ".claude", "settings.json")
    with open(settings, "w", encoding="utf-8") as f:
        json.dump(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 .agent-guild/hooks/dispatch-guard.py",
                                }
                            ]
                        }
                    ]
                }
            },
            f,
        )
    with open(settings, encoding="utf-8") as f:
        assert "dispatch-guard" in f.read(), "double-registration fixture did not land"
    r_both = run_nudge(NUDGE, both, "claude")
    assert r_both.returncode == 0, f"double-registered nudge failed: {r_both.stderr!r}"
    assert "0.0.1" in r_both.stdout and ver in r_both.stdout, (
        f"the version gap is lost when the plugin is registered twice: {r_both.stdout!r}"
    )
    assert "registered twice" in r_both.stdout, (
        f"the double-registration warning was dropped: {r_both.stdout!r}"
    )

    # The combined state, which is the only place the two readings of C-5's
    # "keeps its current behavior" differ. Every other arm is blind to it: the
    # arm above is fully installed, so a nudge that dropped the early return
    # prints nothing extra there, and the partial-init arm is not
    # double-registered, so the return never fires. C-5 settles it on the
    # status quo — the return relocates below the notice, it does not go — so
    # a project that is both must NOT get the partial-init report.
    combined = venue()
    fresh(combined)
    combined_prov = load_prov(combined)
    combined_prov["version"] = "0.0.1"
    write_prov(combined, combined_prov)
    os.makedirs(os.path.join(combined, ".claude"), exist_ok=True)
    combined_settings = os.path.join(combined, ".claude", "settings.json")
    with open(combined_settings, "w", encoding="utf-8") as f:
        json.dump(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 .agent-guild/hooks/dispatch-guard.py",
                                }
                            ]
                        }
                    ]
                }
            },
            f,
        )
    combined_missing = os.path.join(combined, ".agent-guild", "state", "tasks")
    shutil.rmtree(combined_missing)
    assert not os.path.isdir(combined_missing), "combined fixture: removal did not land"
    with open(combined_settings, encoding="utf-8") as f:
        assert "dispatch-guard" in f.read(), "combined fixture: settings did not land"
    r_combined = run_nudge(NUDGE, combined, "claude")
    assert r_combined.returncode == 0, (
        f"combined-state nudge failed: {r_combined.stderr!r}"
    )
    assert "0.0.1" in r_combined.stdout and ver in r_combined.stdout, (
        f"the version gap is lost in the combined state: {r_combined.stdout!r}"
    )
    assert "registered twice" in r_combined.stdout, (
        f"the double-registration warning was dropped: {r_combined.stdout!r}"
    )
    assert "partially initialized" not in r_combined.stdout, (
        "the double-registration early return was removed rather than relocated, "
        f"so a third message printed: {r_combined.stdout!r}"
    )

    # Jurisdiction still governs. Hoisting the notice above the marker gate is
    # one way to make it survive the early return above, and it makes the hook
    # speak in a repo that never opted in (#213).
    unmarked = venue()
    fresh(unmarked)
    unmarked_prov = load_prov(unmarked)
    unmarked_prov["version"] = "0.0.1"
    write_prov(unmarked, unmarked_prov)
    os.remove(os.path.join(unmarked, ".agent-guild", "CLAUDE.md"))
    assert not os.path.exists(
        os.path.join(unmarked, ".agent-guild", "CLAUDE.md")
    ), "marker removal did not land"
    r_unmarked = run_nudge(NUDGE, unmarked, "claude")
    assert r_unmarked.returncode == 0, (
        f"unmarked nudge exited {r_unmarked.returncode}: {r_unmarked.stderr!r}"
    )
    assert r_unmarked.stdout.strip() == "", (
        f"the nudge speaks in a project carrying no marker: {r_unmarked.stdout!r}"
    )

    # Arm 5, independence from the partial-init path. session-nudge returns
    # early when nothing is missing, so a gap notice written below that return
    # never fires in the fully installed project it exists for; and one written
    # above it must not suppress the partial-init report either. Both messages
    # belong to the same run.
    partial = venue()
    fresh(partial)
    partial_prov = load_prov(partial)
    partial_prov["version"] = "0.0.1"
    write_prov(partial, partial_prov)
    missing_dir = os.path.join(partial, ".agent-guild", "state", "tasks")
    shutil.rmtree(missing_dir)
    assert not os.path.isdir(missing_dir), "removal did not land"
    r_partial = run_nudge(NUDGE, partial, "claude")
    assert r_partial.returncode == 0, f"partial+stale nudge failed: {r_partial.stderr!r}"
    assert "0.0.1" in r_partial.stdout and ver in r_partial.stdout, (
        f"the version gap is lost when another nudge also fires: {r_partial.stdout!r}"
    )
    assert "partially initialized" in r_partial.stdout, (
        f"the gap notice suppressed the partial-init report: {r_partial.stdout!r}"
    )

    # Arm 4, the repo-local copy. It ships inside no package, so it has no
    # manifest to read and makes no version claim. Stating that is the point:
    # the alternative is a raise, which the adapter turns into a blocked session
    # start for every repo-local Codex project.
    local = venue()
    rl = subprocess.run(
        [sys.executable, CODEX_INSTALLER, "codex", local, "--project-skills"],
        capture_output=True,
        text=True,
        env=_ENV,
    )
    assert rl.returncode == 0, f"repo-local install failed: {rl.stderr!r}"
    local_nudge = os.path.join(local, ".agent-guild", "hooks", "session-nudge.py")
    assert os.path.isfile(local_nudge), "repo-local nudge did not land"
    local_prov = load_prov(local)
    local_prov["version"] = "0.0.1"
    write_prov(local, local_prov)
    r_local = run_nudge(local_nudge, local, "codex")
    assert r_local.returncode == 0, (
        f"repo-local nudge blocked the session: rc={r_local.returncode} {r_local.stderr!r}"
    )
    assert "0.0.1" not in r_local.stdout and ver not in r_local.stdout, (
        f"repo-local nudge claims a version gap it cannot resolve: {r_local.stdout!r}"
    )


def c6():
    tmp = venue()
    subprocess.run(["git", "init", "-q", tmp], check=True)
    fresh(tmp)
    assert os.path.isfile(os.path.join(tmp, PROV_REL)), "provenance record missing"
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", PROV_REL], cwd=tmp
    ).returncode
    assert ignored == 1, "provenance.json is gitignored; a tracked record must be addable"
    state_ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".agent-guild/state/log"], cwd=tmp
    ).returncode
    assert state_ignored == 0, "state/ stopped being ignored"


def main():
    probes = {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "c6": c6}
    if len(sys.argv) != 2 or sys.argv[1] not in probes:
        sys.stderr.write(f"usage: probe-183.py {{{'|'.join(sorted(probes))}}}\n")
        return 2
    probes[sys.argv[1]]()
    print(f"probe {sys.argv[1]}: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
