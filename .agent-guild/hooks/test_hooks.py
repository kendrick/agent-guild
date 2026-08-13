#!/usr/bin/env python3
"""Fixture-based unit tests for the agent-guild hooks. No Claude Code needed:
each hook is a plain process reading JSON on stdin, so we drive it with
synthetic input against a scratch CLAUDE_PROJECT_DIR and assert exit code +
stderr substring.

Run: python3 hooks/test_hooks.py

The `transcript()` helper below encodes what subagent-return.py expects a Claude
Code subagent transcript to look like. That format is not a stable public
contract; if a CC release changes it and subagent-return starts failing closed
on real dispatches, update `transcript()` here to match the new shape, confirm
the tests pass, and the hook follows.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

HOOKS = os.path.dirname(os.path.abspath(__file__))

passed = failed = 0


def run_hook_path(script_path, payload, proj, extra_env=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=proj)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(
        [sys.executable, script_path],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return p.returncode, p.stdout, p.stderr


def run_hook(name, payload, proj, extra_env=None):
    return run_hook_path(os.path.join(HOOKS, name), payload, proj, extra_env)


def copy_in_hooks(proj):
    """Copy session-nudge.py + _lib.py into proj's own .agent-guild/hooks/,
    mirroring a real copy-in install. run_hook() always execs the ORIGINAL
    script under this repo's own .agent-guild/hooks/, which is never under a
    scratch proj tempdir—so every existing fixture already sees a
    plugin-rooted instance. Running THIS copy instead is the only way to get
    a genuinely project-rooted instance for the negative-case fixture below."""
    dst = os.path.join(proj, ".agent-guild", "hooks")
    os.makedirs(dst, exist_ok=True)
    for name in ("session-nudge.py", "_lib.py"):
        shutil.copy(os.path.join(HOOKS, name), os.path.join(dst, name))
    return os.path.join(dst, "session-nudge.py")


def write_settings_json(proj, hooks_obj):
    d = os.path.join(proj, ".claude")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"hooks": hooks_obj}, f)


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {label}")
    else:
        failed += 1
        print(f"  FAIL {label}  {detail}")


def fresh_proj():
    d = tempfile.mkdtemp(prefix="ag-hooktest-")
    for sub in ("tasks", "verdicts", "disputes", "notes", "log"):
        os.makedirs(os.path.join(d, ".agent-guild", "state", sub))
    return d


def write_task(proj, tid, **fields):
    defaults = dict(status="pending", executor="worker-standard",
                    executor_model="sonnet", checker="checker-deterministic",
                    retries=0, max_retries=2, artifacts="[]")
    defaults.update(fields)
    arts = defaults.pop("artifacts")
    fm = [f"{k}: {v}" for k, v in defaults.items()]
    body = "---\n" + f"id: {tid}\n" + "\n".join(fm) + f"\nartifacts: {arts}\n---\n"
    with open(os.path.join(proj, ".agent-guild", "state", "tasks", f"{tid}.md"), "w") as f:
        f.write(body)


def write_verdict(proj, name, verdict="PASS", diagnosis=False):
    body = f"---\ntask: T\ntier: sonnet\nretry: 0\nchecker: checker-deterministic\nverdict: {verdict}\n---\n\n## Per-clause results\n\n"
    if diagnosis:
        body += "## Diagnosis\n\n- file: x.html:1\n  clause: C-1\n"
    else:
        body += "## Diagnosis\n\n<!-- placeholder only -->\n"
    with open(os.path.join(proj, ".agent-guild", "state", "verdicts", name), "w") as f:
        f.write(body)


def con_pass(proj):
    write_verdict(proj, "CON-audit-r0.md", "PASS")


def write_fake_linter(proj, exit_code, stderr_line="job-spec: fake finding at T-001.md:1",
                       sleep_seconds=None):
    """A stand-in for scripts/check-job-spec.py. dispatch-guard depends on
    that CLI's exit code and stderr and nothing else, so a fake with a
    hardcoded exit drives all three branches. Using the real linter would tie
    these cases to its lint rules, and a rule change would then break the
    hook suite for a reason that has nothing to do with the hook.

    sleep_seconds, when given, makes the fake outlive dispatch-guard's own
    subprocess timeout instead of exiting—the fixture for the timeout branch,
    which needs a linter that genuinely never returns in time."""
    d = os.path.join(proj, ".agent-guild", "scripts")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "check-job-spec.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\n" "import sys\n")
        if sleep_seconds is not None:
            f.write("import time\n" f"time.sleep({sleep_seconds})\n")
        f.write(
            f"sys.stderr.write({stderr_line!r} + chr(10))\n"
            f"sys.exit({exit_code})\n"
        )
    os.chmod(path, 0o755)
    return path


KIT_ROOT = os.path.dirname(HOOKS)  # .agent-guild/, this repo's own real kit tree


def seed_verdict_toolchain(proj):
    """The checker branch of subagent-return.py shells out to the real
    validate-verdict.py (see _validate_verdict_json)—not a stub—so any
    scratch project exercising that path needs the actual script and schema
    copied in, mirroring what a real copied-in kit provides."""
    dst_scripts = os.path.join(proj, ".agent-guild", "scripts")
    os.makedirs(dst_scripts, exist_ok=True)
    shutil.copy(os.path.join(KIT_ROOT, "scripts", "validate-verdict.py"),
                os.path.join(dst_scripts, "validate-verdict.py"))
    dst_schemas = os.path.join(proj, ".agent-guild", "schemas")
    os.makedirs(dst_schemas, exist_ok=True)
    shutil.copy(os.path.join(KIT_ROOT, "schemas", "verdict.schema.json"),
                os.path.join(dst_schemas, "verdict.schema.json"))


def seed_ready_set(proj):
    """Copies the real ready-set.py, plus check-diff-scope.py (its
    paths_overlap import), into proj's own .agent-guild/scripts/—the same
    copy-in-kit posture seed_verdict_toolchain takes for
    validate-verdict.py. stop-gate.py's wave section has to be driven by
    the real script's real output, not a stand-in that could drift from
    what it actually decides (#125)."""
    dst = os.path.join(proj, ".agent-guild", "scripts")
    os.makedirs(dst, exist_ok=True)
    for name in ("ready-set.py", "check-diff-scope.py"):
        shutil.copy(os.path.join(KIT_ROOT, "scripts", name), os.path.join(dst, name))


def write_fake_ready_set(proj, sleep_seconds):
    """A stand-in for scripts/ready-set.py that outlives stop-gate's own
    subprocess timeout instead of returning—the fixture for the timeout
    branch, which needs a script that genuinely never answers in time."""
    d = os.path.join(proj, ".agent-guild", "scripts")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "ready-set.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "#!/usr/bin/env python3\n"
            "import time\n"
            f"time.sleep({sleep_seconds})\n"
        )
    os.chmod(path, 0o755)
    return path


def seed_ledger_line(proj, task_id, quota_event=True):
    """Append one real vendor-ledger line for task_id via the actual
    ledger-append.py (not hand-formatted JSON)—the quota fixture needs a
    genuinely conforming line, and ledger-append.py is the only sanctioned
    way to write one. Runs the repo's own script (it takes --ledger
    explicitly, so it needs no copy-in the way seed_verdict_toolchain's
    validate-verdict.py does)."""
    ledger = os.path.join(proj, ".agent-guild", "state", "log", "vendor-calls.jsonl")
    subprocess.run(
        [sys.executable, os.path.join(KIT_ROOT, "scripts", "ledger-append.py"),
         "--task-id", task_id, "--vendor", "openai", "--model", "gpt-5.6-terra",
         "--started-at", "2026-07-22T18:00:00Z", "--duration-ms", "4100",
         "--exit-code", "1", "--artifacts",
         *(["--quota-event"] if quota_event else []),
         "--ledger", ledger],
        check=True, capture_output=True, text=True,
    )
    return ledger


def write_verdict_json(proj, name, **overrides):
    """A checker verdict JSON per verdict.schema.json, conforming by default;
    callers override fields to build each fixture (bad enum, empty findings,
    a blocked outcome, ...). Mirrors PASS_VERDICT in test_verdict_tools.py."""
    data = {
        "task_id": "T-002",
        "checker": "checker-deterministic",
        "vendor": "anthropic",
        "model": "claude-haiku-4",
        "verdict": "pass",
        "findings": [],
        "timestamp": "2026-07-22T18:00:00Z",
        "duration_ms": 1200,
        "cost_usd": 0.02,
    }
    data.update(overrides)
    path = os.path.join(proj, ".agent-guild", "state", "verdicts", name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def _fresh_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_in_flight_marker(proj, tid, agent, dispatched_at=None):
    """A stand-in for what dispatch-guard.py's mark_in_flight() writes, so
    stop-gate/subagent-return fixtures can set up a marker directly without
    routing through a full dispatch. Fresh by default (dispatched "now");
    callers driving staleness use the AGENT_GUILD_INFLIGHT_STALE_S env seam
    instead of backdating the timestamp, since a TTL of 0 makes ANY
    dispatched_at instantly stale."""
    d = os.path.join(proj, ".agent-guild", "state", "log", "in-flight")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{tid}--{agent}.json"), "w") as f:
        json.dump({"dispatched_at": dispatched_at or _fresh_ts()}, f)


def transcript(proj, text, role="user", content_list=False):
    path = os.path.join(proj, ".agent-guild", "state", "log", "tx.jsonl")
    if content_list:
        content = [{"type": "text", "text": text}]
    else:
        content = text
    line = json.dumps({"type": role, "message": {"role": role, "content": content}})
    with open(path, "w") as f:
        f.write('{"type":"system","message":{"role":"system","content":"boot"}}\n')
        f.write(line + "\n")
    return path


def dispatch_transcript(proj, prompt, user_text=None, tool="Task"):
    """The shape CC actually hands SubagentStop: the PARENT transcript, where the
    dispatch is an assistant tool_use(Task|Agent) whose input.prompt carries the
    id. `user_text`, if given, is a role:user turn that does NOT carry a matchable
    id (the human's chatter), proving the gate reads the dispatch, not the human."""
    path = os.path.join(proj, ".agent-guild", "state", "log", "tx.jsonl")
    with open(path, "w") as f:
        f.write('{"type":"system","message":{"role":"system","content":"boot"}}\n')
        if user_text is not None:
            f.write(json.dumps({"type": "user", "message": {
                "role": "user", "content": [{"type": "text", "text": user_text}]}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Dispatching now."},
            {"type": "tool_use", "name": tool, "input": {
                "subagent_type": "worker-standard", "prompt": prompt}},
        ]}}) + "\n")
    return path


# --------------------------------------------------------- _lib.project_dir
print("_lib.py project_dir() fallback")
sys.path.insert(0, HOOKS)
import _lib as lib_mod  # noqa: E402  (needs sys.path set up first)

_orig_file = lib_mod.__file__
_orig_env = os.environ.pop("CLAUDE_PROJECT_DIR", None)
try:
    # Candidate WITH .agent-guild/ present (the copied-into-a-repo case) →
    # accepted. Point __file__ at a fake .../pkg/hooks/_lib.py so the
    # two-dirs-up math lands on our scratch tree instead of the real repo.
    scratch_ok = tempfile.mkdtemp(prefix="ag-projdir-ok-")
    os.makedirs(os.path.join(scratch_ok, ".agent-guild"))
    lib_mod.__file__ = os.path.join(scratch_ok, "pkg", "hooks", "_lib.py")
    got = lib_mod.project_dir()
    check("fallback: candidate with .agent-guild/ → accepted",
          os.path.realpath(got) == os.path.realpath(scratch_ok), f"got={got}")

    # Candidate WITHOUT .agent-guild/ (the plugin case: two-up lands beside
    # the plugin, not in the user's project) → raises RuntimeError naming it.
    scratch_bad = tempfile.mkdtemp(prefix="ag-projdir-bad-")
    lib_mod.__file__ = os.path.join(scratch_bad, "pkg", "hooks", "_lib.py")
    raised_right = False
    try:
        lib_mod.project_dir()
    except RuntimeError as e:
        raised_right = ".agent-guild" in str(e)
    check("fallback: candidate without .agent-guild/ → raises RuntimeError",
          raised_right)
    shutil.rmtree(scratch_ok, ignore_errors=True)
    shutil.rmtree(scratch_bad, ignore_errors=True)
finally:
    lib_mod.__file__ = _orig_file
    if _orig_env is not None:
        os.environ["CLAUDE_PROJECT_DIR"] = _orig_env

# -------------------------------------------- _lib.parse_frontmatter: block scalars
# Issue #109: a check_method written as `>-`—the natural spelling, since real
# ones run past a thousand characters—used to parse to ''. The task cited its
# clauses, looked right in review, and handed its checker nothing. Every
# expected value below was confirmed against Ruby's psych, a real YAML parser.
print("_lib.py parse_frontmatter block scalars (#109)")

REPRO = """---
id: T-999
check_method: {header}
  C-1: .agent-guild/scripts/check-build.sh "make test"
  C-2: checker-judgment: read the diff
clauses: [C-1, C-2]
---
"""
FOLDED = ('C-1: .agent-guild/scripts/check-build.sh "make test" '
          'C-2: checker-judgment: read the diff')
LITERAL = ('C-1: .agent-guild/scripts/check-build.sh "make test"\n'
           'C-2: checker-judgment: read the diff\n')

for header, want in ((">-", FOLDED), (">", FOLDED + "\n"), ("|", LITERAL)):
    fm = lib_mod.parse_frontmatter(REPRO.format(header=header))
    check(f"block scalar '{header}': body reaches the checker",
          fm["check_method"] == want, f"got={fm['check_method']!r}")
    check(f"block scalar '{header}': clauses beside it still parse as a list",
          fm["clauses"] == ["C-1", "C-2"], f"got={fm['clauses']!r}")

fm = lib_mod.parse_frontmatter("---\na: |-\n  x\n\n  y\nb: 1\n---\n")
check("literal '|-' strips the trailing newline, keeps interior blanks",
      fm["a"] == "x\n\ny", f"got={fm['a']!r}")
check("a key after a block scalar body still parses", fm["b"] == "1", f"got={fm!r}")

fm = lib_mod.parse_frontmatter("---\na: |+\n  x\n\n\nb: 1\n---\n")
check("literal '|+' keeps the trailing blank lines", fm["a"] == "x\n\n\n",
      f"got={fm['a']!r}")

fm = lib_mod.parse_frontmatter("---\na: >+\n  z\n\n\nb: 1\n---\n")
check("folded '>+' keeps the trailing blank lines", fm["a"] == "z\n\n\n",
      f"got={fm['a']!r}")

fm = lib_mod.parse_frontmatter(
    "---\nf: >-\n  a\n  b\n\n  c\n     more indented\n  d\ntail: 1\n---\n")
check("folded: blank line breaks the fold, a more-indented line stays verbatim",
      fm["f"] == "a b\nc\n   more indented\nd", f"got={fm['f']!r}")

# The guard the old code bought by dropping the body: a '- item' line inside a
# block scalar is body text, never a list entry. Reading the body keeps it,
# because those lines are consumed before the list branch can see them.
for header in ("|", ">-"):
    fm = lib_mod.parse_frontmatter(
        f"---\nm: {header}\n  - not a list item\n  - still not\n"
        "artifacts:\n  - a.py\n  - b.py\n---\n")
    check(f"block scalar '{header}': its '- ' lines are body, not list items",
          isinstance(fm["m"], str) and "not a list item" in fm["m"],
          f"got={fm['m']!r}")
    check(f"block scalar '{header}': a real block list after it still parses",
          fm["artifacts"] == ["a.py", "b.py"], f"got={fm['artifacts']!r}")

fm = lib_mod.parse_frontmatter("---\nm: >-\nnext: ok\n---\n")
check("block scalar with no body → empty string, next key intact",
      fm["m"] == "" and fm["next"] == "ok", f"got={fm!r}")

# ------------------------------------------------ _lib.unverifiable (#109)
print("_lib.py unverifiable()")
check("cites clauses, empty check_method → a reason naming the task file",
      ".agent-guild/state/tasks/T-001.md" in
      (lib_mod.unverifiable("T-001", {"clauses": ["C-1"], "check_method": ""}) or ""))
check("cites clauses with a check_method → None",
      lib_mod.unverifiable("T-001", {"clauses": ["C-1"], "check_method": "run x"})
      is None)
check("cites no clauses → None even with an empty check_method",
      lib_mod.unverifiable("T-001", {"clauses": [], "check_method": ""}) is None)
check("a single clause written as a bare scalar still counts",
      lib_mod.unverifiable("T-001", {"clauses": "C-1", "check_method": " "})
      is not None)

# --------------------------------------- _lib.labeled_ids / _id_in (#108)
# _id_in used to short-circuit TASK_ID_RE, AUDIT_ID_RE, AUDITION_ID_RE in
# DECLARATION order, so a Task-ID anywhere in a blob beat an Audit-ID that
# appeared earlier in the same text. The fix picks the earliest match BY
# POSITION; these two blobs are identical apart from which label comes first,
# which is exactly what the old code got wrong.
print("_lib.py labeled_ids() / _id_in() (#108)")

task_first = "Task-ID: T-001\nsome context in between\nAudit-ID: CON-audit"
audit_first = "Audit-ID: CON-audit\nsome context in between\nTask-ID: T-001"

check("Task-ID before Audit-ID → resolves to the task",
      lib_mod._id_in(task_first) == "T-001", f"got={lib_mod._id_in(task_first)!r}")
check("Audit-ID before Task-ID → resolves to the audit",
      lib_mod._id_in(audit_first) == "CON-audit",
      f"got={lib_mod._id_in(audit_first)!r}")

# Single-id blobs: unaffected by the rewrite, true by construction (only one
# candidate exists to be "earliest"), pinned anyway so a regression shows here
# rather than only in the hook-level fixtures below.
check("single Task-ID blob unchanged",
      lib_mod._id_in("Task-ID: T-042") == "T-042")
check("single Audit-ID blob unchanged",
      lib_mod._id_in("Audit-ID: DEC-audit") == "DEC-audit")
check("single Audition-ID blob unchanged",
      lib_mod._id_in("Audition-ID: A-007") == "A-007")
check("no labeled id anywhere → None",
      lib_mod._id_in("just some chatter, no ids") is None)

# labeled_ids() itself: every match, sorted by position, kind + id + position.
got = lib_mod.labeled_ids(audit_first)
check("labeled_ids finds both ids in the blob", len(got) == 2, f"got={got!r}")
check("labeled_ids sorts earliest-first",
      got[0][:2] == ("audit", "CON-audit") and got[1][:2] == ("task", "T-001"),
      f"got={got!r}")
check("labeled_ids positions are in document order",
      got[0][2] < got[1][2], f"got={got!r}")
check("labeled_ids on a single-id blob returns one tuple",
      lib_mod.labeled_ids("Audition-ID: A-003") == [("audition", "A-003", 0)],
      f"got={lib_mod.labeled_ids('Audition-ID: A-003')!r}")
check("labeled_ids on text with no ids returns []",
      lib_mod.labeled_ids("nothing to see here") == [])

# --------------------------------- _lib.py in-flight markers (#111)
# mark_in_flight/clear_in_flight/in_flight() exercised directly, in-process,
# ahead of the hook-level fixtures below—cheaper to pin the freshness math
# here than to prove it only through a full subprocess round-trip.
print("_lib.py mark_in_flight / clear_in_flight / in_flight() (#111)")
proj_lib = fresh_proj()
_prev_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
os.environ["CLAUDE_PROJECT_DIR"] = proj_lib
try:
    lib_mod.mark_in_flight("T-900", "worker-standard")
    fresh = lib_mod.in_flight()
    check("mark_in_flight → shows up as fresh immediately",
          "T-900--worker-standard" in fresh, f"fresh={fresh!r}")

    lib_mod.clear_in_flight("T-900", "worker-standard")
    fresh = lib_mod.in_flight()
    check("clear_in_flight → no longer listed",
          "T-900--worker-standard" not in fresh, f"fresh={fresh!r}")
    check("clear_in_flight on an already-missing marker → no error raised",
          lib_mod.clear_in_flight("T-900", "worker-standard") is None)

    lib_mod.mark_in_flight("T-901", "checker-deterministic")
    _prev_ttl_env = os.environ.get("AGENT_GUILD_INFLIGHT_STALE_S")
    os.environ["AGENT_GUILD_INFLIGHT_STALE_S"] = "0"
    try:
        fresh = lib_mod.in_flight()
    finally:
        if _prev_ttl_env is None:
            os.environ.pop("AGENT_GUILD_INFLIGHT_STALE_S", None)
        else:
            os.environ["AGENT_GUILD_INFLIGHT_STALE_S"] = _prev_ttl_env
    check("AGENT_GUILD_INFLIGHT_STALE_S=0 → an existing marker reads as stale",
          "T-901--checker-deterministic" not in fresh, f"fresh={fresh!r}")
    check("an explicit large ttl overrides the env seam (ttl=None is the only "
          "thing that reads it)",
          "T-901--checker-deterministic" in lib_mod.in_flight(ttl=999999))

    bad_dir = os.path.join(proj_lib, ".agent-guild", "state", "log", "in-flight")
    with open(os.path.join(bad_dir, "T-902--worker-bulk.json"), "w") as f:
        f.write("{not valid json")
    fresh = lib_mod.in_flight()
    check("a malformed marker is dropped, not fatal", isinstance(fresh, list),
          f"{fresh!r}")

    empty_proj = fresh_proj()
    os.environ["CLAUDE_PROJECT_DIR"] = empty_proj
    check("no in-flight/ directory at all → in_flight() returns []",
          lib_mod.in_flight() == [])
finally:
    if _prev_project_dir is None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
    else:
        os.environ["CLAUDE_PROJECT_DIR"] = _prev_project_dir

# ---------------------------------------------------------------- stop-gate
print("stop-gate.py")
proj = fresh_proj()
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("no tasks dir contents → exit 0", rc == 0, f"rc={rc}")

write_task(proj, "T-001", status="needs-check")
rc, out, err = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
check("open task → exit 2", rc == 2, f"rc={rc}")
check("open task → names next move (checker)", "checker" in err, err)

# PAUSED overrides
open(os.path.join(proj, ".agent-guild", "state", "PAUSED"), "w").close()
rc, out, err = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
check("PAUSED + open task → exit 0", rc == 0, f"rc={rc}")
os.remove(os.path.join(proj, ".agent-guild", "state", "PAUSED"))

# all complete
write_task(proj, "T-001", status="complete")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("all terminal → exit 0", rc == 0, f"rc={rc}")

# livelock: 3 consecutive same-digest blocks under stop_hook_active
proj = fresh_proj()
write_task(proj, "T-001", status="rework", retries=1)
rc1, _, _ = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
rc2, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, e3 = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
stalled = os.path.exists(os.path.join(proj, ".agent-guild", "state", "STALLED.md"))
check("livelock strikes 1,2 block", rc1 == 2 and rc2 == 2, f"{rc1},{rc2}")
check("livelock strike 3 → exit 0", rc3 == 0, f"rc={rc3}")
check("livelock strike 3 → STALLED.md written", stalled)

# a landed verdict is progress even when the task tuple doesn't move. A task
# sits at `checking` across its checker of record AND its courier second
# opinion, so two real checks can complete without status or retries changing.
# Counting that as a stall wrote a spurious STALLED.md during the #78 run and is
# the same blindness behind #81.
proj = fresh_proj()
write_task(proj, "T-001", status="checking", retries=0)
verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
os.makedirs(verdicts_dir, exist_ok=True)
rc1, _, _ = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
rc2, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
# checker of record returns; task stays at checking/0 because the orchestrator
# hasn't ruled on the verdict yet.
with open(os.path.join(verdicts_dir, "T-001-opus-r0.json"), "w") as f:
    f.write("{}\n")
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
stalled_after_verdict = os.path.exists(
    os.path.join(proj, ".agent-guild", "state", "STALLED.md"))
with open(os.path.join(proj, ".agent-guild", "state", "log", "stop-gate.state")) as f:
    count_after_verdict = json.load(f)["entries"]["T-001"]["count"]
check("verdict landing resets the stall counter",
      count_after_verdict == 1, f"count={count_after_verdict}")
check("verdict landing → no spurious STALLED.md on strike 3",
      not stalled_after_verdict)
check("the turn is still blocked (progress is not completion)",
      rc1 == 2 and rc2 == 2 and rc3 == 2, f"{rc1},{rc2},{rc3}")

# the backstop still fires when nothing lands: same task tuple, same verdict
# set, three strikes.
proj = fresh_proj()
write_task(proj, "T-001", status="checking", retries=0)
os.makedirs(os.path.join(proj, ".agent-guild", "state", "verdicts"), exist_ok=True)
with open(os.path.join(proj, ".agent-guild", "state", "verdicts",
                       "T-001-opus-r0.json"), "w") as f:
    f.write("{}\n")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc_last, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a checker owing a verdict still stalls after three strikes",
      rc_last == 0 and os.path.exists(
          os.path.join(proj, ".agent-guild", "state", "STALLED.md")),
      f"rc={rc_last}")

# ------------------------------------------ stop-gate: in-flight markers (#111)
# A subagent that's genuinely still working looks identical to a stuck loop
# from the task tuple alone—waves made that the common case, not a rare one.
print("stop-gate.py: in-flight markers (#111)")
STALE_ENV = {"AGENT_GUILD_INFLIGHT_STALE_S": "0"}

# test: a fresh marker holds the stall counter. Three blocked stops in a row
# write no STALLED.md, because the whole time a worker is legitimately
# mid-flight—dispatching another would duplicate it, and declaring the loop
# stuck would be just as wrong.
proj = fresh_proj()
write_task(proj, "T-001", status="assigned", retries=0)
write_in_flight_marker(proj, "T-001", "worker-standard")
state_file = os.path.join(proj, ".agent-guild", "state", "log", "stop-gate.state")
rc1, _, _ = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
rc2, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
stalled_inflight = os.path.exists(os.path.join(proj, ".agent-guild", "state", "STALLED.md"))
with open(state_file, encoding="utf-8") as f:
    count_inflight = json.load(f)["entries"]["T-001"]["count"]
check("fresh marker on an open task → three blocked stops write no STALLED.md",
      not stalled_inflight, f"count={count_inflight}")
check("fresh marker → the stall count is held, not advanced",
      count_inflight == 1, f"count={count_inflight}")
check("still blocks the turn each time (mid-flight isn't done)",
      rc1 == 2 and rc2 == 2 and rc3 == 2, f"{rc1},{rc2},{rc3}")

# test: stale still stalls. A marker whose TTL has lapsed (simulated via the
# AGENT_GUILD_INFLIGHT_STALE_S=0 test seam) is worth nothing—a dead agent
# must not permanently suppress the backstop.
proj = fresh_proj()
write_task(proj, "T-001", status="assigned", retries=0)
write_in_flight_marker(proj, "T-001", "worker-standard")
run_hook("stop-gate.py", {"stop_hook_active": False}, proj, extra_env=STALE_ENV)
run_hook("stop-gate.py", {"stop_hook_active": True}, proj, extra_env=STALE_ENV)
rc_stale3, _, _ = run_hook(
    "stop-gate.py", {"stop_hook_active": True}, proj, extra_env=STALE_ENV)
check("stale marker (TTL=0) → the backstop still fires after three strikes",
      rc_stale3 == 0 and os.path.exists(
          os.path.join(proj, ".agent-guild", "state", "STALLED.md")),
      f"rc={rc_stale3}")

# test: _next_move wording disambiguates fresh / absent / stale, for both
# `assigned` and `checking`.
for status, verb in (("assigned", "executor"), ("checking", "checker")):
    proj_w = fresh_proj()
    write_task(proj_w, "T-001", status=status, retries=0)
    rc, out, err = run_hook("stop-gate.py", {}, proj_w)
    check(f"{status}, no marker → names 'dispatch the {verb}'",
          rc == 2 and f"dispatch the {verb}" in err, err)

    proj_w = fresh_proj()
    write_task(proj_w, "T-001", status=status, retries=0)
    write_in_flight_marker(proj_w, "T-001", "worker-standard")
    rc, out, err = run_hook("stop-gate.py", {}, proj_w)
    check(f"{status}, fresh marker → 'mid-flight ... do not dispatch another'",
          rc == 2 and "mid-flight" in err and "do not dispatch another" in err,
          err)

    proj_w = fresh_proj()
    write_task(proj_w, "T-001", status=status, retries=0)
    write_in_flight_marker(proj_w, "T-001", "worker-standard")
    rc, out, err = run_hook("stop-gate.py", {}, proj_w, extra_env=STALE_ENV)
    check(f"{status}, stale marker → 'never returned; investigate, then re-dispatch'",
          rc == 2 and "never returned" in err
          and "investigate, then re-dispatch" in err,
          err)

# An absent marker at `checking` is ambiguous in a way `assigned` is not:
# subagent-return clears the marker on the way out, so a checker that already
# landed its verdict leaves the same absence as one nobody dispatched. The
# checker writes the verdict but the ORCHESTRATOR moves the status, so
# verdict-landed-and-still-`checking` is the ordinary state of every checked
# task. Telling the orchestrator to dispatch there would run a second checker
# over work that already passed.
proj_w = fresh_proj()
write_task(proj_w, "T-001", status="checking", retries=0)
write_verdict(proj_w, "T-001-sonnet-r0.md")
rc, out, err = run_hook("stop-gate.py", {}, proj_w)
check("checking, no marker, verdict landed → 'act on it', not 'dispatch'",
      rc == 2 and "act on it" in err and "dispatch the checker" not in err, err)

# Round-scoped, matching the courier-debt branch: an older round's verdict
# survives a rework cycle and must not be mistaken for this round's.
proj_w = fresh_proj()
write_task(proj_w, "T-001", status="checking", retries=1)
write_verdict(proj_w, "T-001-sonnet-r0.md")
rc, out, err = run_hook("stop-gate.py", {}, proj_w)
check("checking, only a PRIOR round's verdict → still 'dispatch the checker'",
      rc == 2 and "dispatch the checker" in err, err)

# A lane-suffixed file is a second opinion, never the verdict of record.
proj_w = fresh_proj()
write_task(proj_w, "T-001", status="checking", retries=0)
write_verdict(proj_w, "T-001-sonnet-r0-codex.md")
rc, out, err = run_hook("stop-gate.py", {}, proj_w)
check("checking, only a LANE verdict → still 'dispatch the checker'",
      rc == 2 and "dispatch the checker" in err, err)

# ------------------------------- stop-gate: at-most-once per real block (#111)
# Issue #41: with both the plugin's hooks.json and a copy-in settings.json
# active, the SAME real main-session Stop event fires stop-gate.py twice
# before the orchestrator resolves anything. Neither the task/verdict/debt
# state nor the marker set changes between the two firings, because nothing
# actually happened in between—but that's also true of a genuine second
# blocked turn where the orchestrator's own output didn't touch any of that
# state. The main transcript's own byte size is what tells them apart: two
# firings against the SAME transcript are one real block, and the counter
# holds rather than advancing. This supersedes the old double-advance
# expectation (a same-digest repeat used to always cost a full strike).
print("stop-gate.py: at-most-once per real block (#111)")
proj = fresh_proj()
write_task(proj, "T-001", status="rework", retries=1)
state_file = os.path.join(proj, ".agent-guild", "state", "log", "stop-gate.state")
tx_path = os.path.join(proj, ".agent-guild", "state", "log", "tx-dup.jsonl")
with open(tx_path, "w") as f:
    f.write('{"type":"system"}\n')

rc_a, _, _ = run_hook(
    "stop-gate.py", {"stop_hook_active": False, "transcript_path": tx_path}, proj)
with open(state_file, encoding="utf-8") as f:
    count_after_one_fire = json.load(f)["entries"]["T-001"]["count"]
check("at-most-once: one fire → count 1",
      count_after_one_fire == 1, f"count={count_after_one_fire}")

rc_b, _, _ = run_hook(
    "stop-gate.py", {"stop_hook_active": False, "transcript_path": tx_path}, proj)
with open(state_file, encoding="utf-8") as f:
    count_after_two_fires = json.load(f)["entries"]["T-001"]["count"]
check("at-most-once: same digest AND same transcript size → held at 1, not "
      "advanced",
      count_after_two_fires == 1, f"count={count_after_two_fires}")
check("both fires individually still blocked the turn (rc==2 each)",
      rc_a == 2 and rc_b == 2, f"{rc_a},{rc_b}")

# ...but a genuinely new blocked turn—the transcript grew, meaning the
# orchestrator actually did something—still advances normally.
with open(tx_path, "a") as f:
    f.write('{"type":"assistant"}\n')
rc_c, _, _ = run_hook(
    "stop-gate.py", {"stop_hook_active": False, "transcript_path": tx_path}, proj)
with open(state_file, encoding="utf-8") as f:
    count_after_grown_transcript = json.load(f)["entries"]["T-001"]["count"]
check("same digest, DIFFERENT transcript size → advances (a real repeated block)",
      count_after_grown_transcript == 2, f"count={count_after_grown_transcript}")

# malformed task file → treated as open (fail closed)
proj = fresh_proj()
with open(os.path.join(proj, ".agent-guild", "state", "tasks", "T-009.md"), "w") as f:
    f.write("this file has no frontmatter at all\n")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("malformed task → exit 2 (fail closed)", rc == 2, f"rc={rc}")

# in-subagent scope: a subagent's own Stop is not the orchestrator's turn
# ending, so this gate must no-op regardless of open tasks—and, since a
# subagent Stop should never touch the livelock counter, stop-gate.state must
# come out byte-identical. Seed the state file via a real main-session block
# first (the way it'd exist in a live run), snapshot it, then fire the
# subagent event and compare.
proj = fresh_proj()
write_task(proj, "T-001", status="needs-check")
write_task(proj, "T-002", status="assigned")
rc0, _, _ = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
check("(setup) main-session block seeds stop-gate.state", rc0 == 2, f"rc={rc0}")
state_file = os.path.join(proj, ".agent-guild", "state", "log", "stop-gate.state")
with open(state_file, "rb") as f:
    state_before = f.read()
rc, out, err = run_hook(
    "stop-gate.py", {"agent_id": "sub-1", "stop_hook_active": False}, proj)
check("subagent Stop, two open tasks → exit 0, empty output",
      rc == 0 and out == "" and err == "", f"rc={rc} out={out!r} err={err!r}")
with open(state_file, "rb") as f:
    state_after = f.read()
check("subagent Stop → stop-gate.state byte-identical",
      state_before == state_after, f"before={state_before!r} after={state_after!r}")

# --------------------------- stop-gate: ready-set wave presentation (#125)
# ready-set.py changes only how the block message reads, never whether it
# blocks—these fixtures prove both the presentation (the wave section, with
# its unmissable parallel-dispatch instruction) and the degrade path (any
# reason ready-set.py can't produce a result falls straight back to the
# pre-#125 per-task advice).
print("stop-gate.py: ready-set wave presentation (#125)")

proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="pending", deps="[]", owns="[file-a.py]")
write_task(proj, "T-002", status="pending", deps="[]", owns="[file-b.py]")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("wave: two dep-free tasks still block the turn", rc == 2, f"rc={rc}")
check("wave: unmissable one-message parallel-dispatch instruction",
      "ONE message" in err and "parallel" in err, err)
check("wave: both ready tasks named in the wave section",
      "T-001" in err and "T-002" in err, err)
check("wave: each entry names its executor agent",
      err.count("worker-standard") >= 2, err)

# a single-member wave gets no "in ONE message" fanout instruction—there's
# nothing to fan out.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="pending", deps="[]", owns="[file-a.py]")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("wave: a lone ready task names it without the fanout instruction",
      rc == 2 and "T-001" in err and "ONE message" not in err, err)

# --------------- stop-gate: deferred/attention buckets must reach the gate (#155)
# Before this fix, only ready_result["wave"] survived the trip through
# stop-gate.py—deferred and attention were computed by ready-set.py and then
# thrown away, and a task IN the wave lost its _next_move line too (the
# generic per-task advice is suppressed for anything `t[0] not in wave_ids`,
# with nothing put in its place for deferred/attention). These fixtures pin
# both halves: a deferred task must carry ready-set's own reason, not the
# generic "assign it and dispatch its executor" instruction that would have
# it dispatched straight into a dependency violation; an attention task must
# be marked as needing the orchestrator's judgment, not silently handed the
# same generic dispatch instruction toward a dep that can never resolve.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="pending", deps="[]", owns="[]")
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[]")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("deferred: unmet-dep task carries ready-set's own reason verbatim",
      "unmet deps: T-001 (pending)" in err, err)
check("deferred: unmet-dep task is NOT told the generic dispatch move",
      "T-002 [pending] → assign it and dispatch its executor." not in err, err)

proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="abandoned", deps="[]", owns="[]")
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[]")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("attention: abandoned-dep task is NOT told the generic dispatch move",
      "T-002 [pending] → assign it and dispatch its executor." not in err, err)
check("attention: abandoned-dep task is marked as needing judgment, "
      "carrying ready-set's reason verbatim",
      "T-002" in err and "needs your judgment" in err
      and "depends on abandoned task(s): T-001" in err, err)

# --------------------- stop-gate: a `rework` task must keep the retry ladder (#155)
# Before this fix, ready-set.py treated `rework` as a wave candidate, so a
# rework task with no unmet deps/collisions landed in the wave—and the wave
# suppression above then dropped its ladder text (the diagnosis-copy and
# retries-increment instructions) in favor of a bare "dispatch
# worker-standard" line. That line is also something dispatch-guard.py
# refuses outright: a worker only runs on an `assigned` task, never
# `rework`. ready-set.py now never offers `rework` in any bucket (see its
# module docstring), so this always falls through to _next_move.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="rework", deps="[]", owns="[file-a.py]",
           retries=1, max_retries=2)
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("rework task never enters the wave",
      "READY WAVE" not in err and "Ready to dispatch now" not in err, err)
check("rework task keeps its full retry-ladder instruction",
      "copy the checker's diagnosis into ## Rework diagnosis" in err
      and "retries 1" in err
      and "re-dispatch the same worker" in err, err)

# degrade path 1: ready-set.py never copied in at all (today's ordinary
# case for a repo that hasn't picked up #125's payload yet)—the gate must
# still block and still name the next move per task.
proj = fresh_proj()
write_task(proj, "T-003", status="pending", deps="[]", owns="[file-c.py]")
write_task(proj, "T-004", status="pending", deps="[]", owns="[file-d.py]")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("degrade (missing script): still blocks", rc == 2, f"rc={rc}")
check("degrade (missing script): no wave header",
      "READY WAVE" not in err, err)
check("degrade (missing script): per-task advice for both tasks",
      err.count("assign it and dispatch its executor") == 2, err)

# degrade path 2: ready-set.py is present but exits non-zero against this
# project's data (here, task files missing the deps/owns fields it
# requires)—still not a weaker block, just a plainer message.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-005", status="pending")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("degrade (script errors): still blocks", rc == 2, f"rc={rc}")
check("degrade (script errors): falls back to per-task advice, no wave header",
      "READY WAVE" not in err and "assign it and dispatch its executor" in err,
      err)

# degrade path 3: ready-set.py hangs past the gate's own short timeout.
proj = fresh_proj()
write_fake_ready_set(proj, sleep_seconds=2)
write_task(proj, "T-006", status="pending", deps="[]", owns="[file-f.py]")
rc, out, err = run_hook(
    "stop-gate.py", {}, proj,
    extra_env={"AGENT_GUILD_READY_SET_TIMEOUT": "0.2"})
check("degrade (script times out): still blocks", rc == 2, f"rc={rc}")
check("degrade (script times out): falls back to per-task advice, no wave header",
      "READY WAVE" not in err and "assign it and dispatch its executor" in err,
      err)

# ------------------------- stop-gate: per-task stall counters (#163)
# The stall counter used to be one digest+count for the whole job, and #111's
# marker hold was an any() over every open task—so ONE live subagent made
# every other task immune to the backstop. Measured on a real fixture: a task
# stuck at `disputed` sat frozen at count=1 through eight blocked firings
# while a sibling churned. Under waves something is nearly always mid-flight,
# so the backstop was off for the length of Phase 2.
print("stop-gate.py: per-task stall counters (#163)")
STATE_REL = (".agent-guild", "state", "log", "stop-gate.state")


def stall_entries(proj):
    with open(os.path.join(proj, *STATE_REL), encoding="utf-8") as f:
        return json.load(f)["entries"]


def stalled_text(proj):
    path = os.path.join(proj, ".agent-guild", "state", "STALLED.md")
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


# The issue's own repro, inverted into an expectation: the stuck sibling
# reaches STALLED.md on the ordinary three-strike schedule, the mid-flight
# task is still held at 1 (#111's guarantee, un-regressed), and the report
# names only what's actually stuck.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="assigned", deps="[]", owns="[a.py]", retries=0)
write_task(proj, "T-002", status="disputed", deps="[]", owns="[b.py]", retries=0)
write_in_flight_marker(proj, "T-001", "worker-standard")
run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
text = stalled_text(proj)
check("a stuck task stalls on schedule while a sibling holds a fresh marker",
      "T-002" in text, f"rc={rc3} text={text!r}")
check("STALLED.md names only the stuck task, not the mid-flight one",
      "T-001" not in text, text)
# Reporting T-002 parks it; the gate keeps blocking because T-001 is still
# open and still mid-flight. A job-wide stand-down here would let the turn
# end with a live worker nobody was going to check.
check("reporting one task doesn't stand the gate down for a healthy sibling",
      rc3 == 2, f"rc={rc3}")
check("the mid-flight task's own counter is still held at 1",
      stall_entries(proj)["T-001"]["count"] == 1, stall_entries(proj))

# A task deferred behind a dependency that's genuinely running has no move
# available to it, so its counter holds—otherwise removing the global
# umbrella would just trade one spurious STALLED.md for another.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="assigned", deps="[]", owns="[a.py]", retries=0)
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[b.py]", retries=0)
write_in_flight_marker(proj, "T-001", "worker-standard")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a task deferred behind a running dep writes no STALLED.md",
      rc3 == 2 and not stalled_text(proj), f"rc={rc3}")

# ...but when that dep's own marker goes stale, the dep stalls and the task
# waiting on it does not. Same fixture, TTL zeroed.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="assigned", deps="[]", owns="[a.py]", retries=0)
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[b.py]", retries=0)
write_in_flight_marker(proj, "T-001", "worker-standard")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj, extra_env=STALE_ENV)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj,
                     extra_env=STALE_ENV)
text = stalled_text(proj)
check("a stale-marker dep stalls; the task deferred behind it doesn't",
      "T-001" in text and "T-002" not in text, f"rc={rc3} text={text!r}")

# `budget` is the one deferral kind that must NOT hold. A spent retry budget
# is retry-ladder step 4—escalate, re-decompose, or surface it—and it can
# only ever resolve through the orchestrator. Holding it would leave a job
# whose last open task is budget-deferred blocked forever with no backstop.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="pending", deps="[]", owns="[a.py]",
           retries=2, max_retries=2)
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a spent-budget deferral still stalls (it can't resolve on its own)",
      rc3 == 0 and "T-001" in stalled_text(proj), f"rc={rc3}")

# The wedge valve: a dep cycle defers every task, with nothing alive to
# un-defer any of them. check-job-spec.py's R7 catches a cycle, but only at
# dispatch time, and dispatch time never arrives here. Honoring the hold
# would block forever with no backstop at all.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="pending", deps="[T-002]", owns="[a.py]")
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[b.py]")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
text = stalled_text(proj)
check("an all-deferred wedge (dep cycle) voids the hold and stalls loudly",
      rc3 == 0 and "T-001" in text and "T-002" in text, f"rc={rc3} text={text!r}")

# Degrading fails LOUD, not quiet: with no ready-set.py at all, nothing is
# deferral-held, so a legitimately waiting task can reach STALLED.md. A
# degrade that suppressed the backstop instead would rebuild #163's own hole.
proj = fresh_proj()
write_task(proj, "T-001", status="pending", deps="[]", owns="[a.py]")
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[b.py]")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("ready-set degraded → the backstop still fires (loud, not suppressed)",
      rc3 == 0 and "T-001" in stalled_text(proj), f"rc={rc3}")

# A sibling's marker can't mask another task's counter. T-062 is mid-flight
# the whole time; T-064 sits at `disputed` needing a ruling nobody gives it.
# Before per-entity counters, T-062's marker held the single global counter
# and this wrote nothing at all.
proj = fresh_proj()
write_task(proj, "T-062", status="assigned", retries=0)
write_in_flight_marker(proj, "T-062", "worker-standard")
write_task(proj, "T-064", status="disputed", retries=0)
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc3, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
text = stalled_text(proj)
check("an unruled dispute stalls even while a sibling task is mid-flight",
      "T-064" in text, f"rc={rc3} text={text!r}")
check("the mid-flight sibling stays out of that report",
      "T-062" not in text, text)

# ------------- stop-gate: what adversarial review caught in the #163 fix
# Every case below is a reproduction that failed against the first version of
# per-task counters. They are the expensive half of this issue: each one is a
# state the ordinary fixtures above can't reach, and each was found by
# driving the real hook rather than by reading it.
print("stop-gate.py: per-task counters, review regressions (#163)")

# Reporting a stuck task must not disarm the gate for the rest of the job.
# The first version returned 0 job-wide once anything tripped, and a tripped
# entity's count only resets when its OWN digest changes—so one task nobody
# ruled on stood the gate down permanently, which is worse than the global
# counter it replaced (that one at least re-armed whenever anything moved).
proj = fresh_proj()
write_task(proj, "T-001", status="disputed", deps="[]", owns="[a.py]")
for _ in range(3):
    rc_park, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a job with nothing left but parked entities lets the turn end",
      rc_park == 0 and "T-001" in stalled_text(proj), f"rc={rc_park}")
# A healthy task arrives after the stuck one was reported. The gate has to
# block for it: the whole point of parking is that being stuck on one thing
# doesn't excuse the orchestrator from everything else.
write_task(proj, "T-002", status="needs-check", deps="[]", owns="[b.py]",
           artifacts="[out.py]")
rc_after, _, err_after = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a parked task leaves the gate armed for its healthy siblings",
      rc_after == 2 and "T-002" in err_after, f"rc={rc_after} err={err_after}")
check("the parked task stops being advertised as a next move",
      "T-001 [disputed]" not in err_after, err_after)

# `owns: []` is what templates/task.md ships, and ready-set defers an
# undeclared task against EVERY id in --running. Holding that kind would let
# one live subagent freeze every other pending task's counter, which is
# #163's own bug relocated from the marker hold to the deferral hold.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="assigned", deps="[]", owns="[]")
for tid in ("T-002", "T-003"):
    write_task(proj, tid, status="pending", deps="[]", owns="[]")
write_in_flight_marker(proj, "T-001", "worker-standard")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
text = stalled_text(proj)
check("undeclared `owns` (the template default) doesn't hold a task's counter",
      "T-002" in text and "T-003" in text, text)
check("the live sibling is still held by its own marker, not stalled",
      "T-001" not in text, text)

# `owns-malformed` is the same shape as `owns-undeclared` (#162) and needs
# the same answer: a typo in an `owns` entry is fixed by editing the task
# file, and nobody edits a task the gate keeps reporting as legitimately
# waiting on something else.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="assigned", deps="[]", owns="[b.py]")
for tid in ("T-002", "T-003"):
    write_task(proj, tid, status="pending", deps="[]", owns="[./a.py]")
write_in_flight_marker(proj, "T-001", "worker-standard")
for _ in range(3):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
text = stalled_text(proj)
check("a malformed `owns` entry doesn't hold a task's counter either",
      "T-002" in text and "T-003" in text, text)

# A ready-set.py that flickers healthy/degraded must not pin every counter.
# The first version carried each task's ready-set disposition inside its
# digest, so an alternating input changed every digest every firing and
# reset every counter to 1 forever. ready-set exits 3 on any task file it
# can't parse, which includes one caught mid-rewrite by task-status.py.
proj = fresh_proj()
write_task(proj, "T-001", status="needs-check", deps="[]", owns="[a.py]",
           artifacts="[out.py]")
ready_set_path = os.path.join(proj, ".agent-guild", "scripts", "ready-set.py")
for i in range(6):
    if i % 2 == 0:
        seed_ready_set(proj)
    elif os.path.exists(ready_set_path):
        os.remove(ready_set_path)
    rc_flicker, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a flickering ready-set.py can't pin the counter at 1 forever",
      "T-001" in stalled_text(proj), stalled_text(proj))

# The valve must not read a fresh marker on a `complete` task as "nothing in
# flight". open_tasks() drops terminal tasks, so an opted-in courier still
# running against a task the orchestrator already completed is invisible to
# it, and the first version stalled a task for taking the gate's own advice
# while that courier was demonstrably still running.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="complete", deps="[]", owns="[a.py]")
write_task(proj, "T-002", status="pending", deps="[]", owns="[a.py]")
write_verdict_json(proj, "T-001-sonnet-r0.json", task_id="T-001")
write_in_flight_marker(proj, "T-001", "checker-courier")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc_courier, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a task deferred behind a live courier crossing is not stalled",
      rc_courier == 2 and not stalled_text(proj), f"rc={rc_courier}")

# A dep cycle beside one unrelated task must still surface. The valve keys
# off entities that could still trip, so once the unrelated task is reported
# and parked, the cycle is all that's left and the hold gives out.
proj = fresh_proj()
seed_ready_set(proj)
write_task(proj, "T-001", status="pending", deps="[T-002]", owns="[a.py]")
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[b.py]")
write_task(proj, "T-003", status="disputed", deps="[]", owns="[c.py]")
for _ in range(7):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
text = stalled_text(proj)
check("a dep cycle still surfaces once the unrelated task beside it parks",
      "T-001" in text and "T-002" in text and "T-003" in text, text)

# Version skew: a project's copied-in ready-set.py from before #163 emits
# `deferred` with no `kind`. Reading that as "not a hold" stalls a task that
# is legitimately waiting on a running dep, so the reason string is mapped
# back for exactly the two kinds that hold.
proj = fresh_proj()
seed_ready_set(proj)
with open(ready_set_path if False else os.path.join(
        proj, ".agent-guild", "scripts", "ready-set.py"), encoding="utf-8") as f:
    old_ready_set = f.read()
with open(os.path.join(proj, ".agent-guild", "scripts", "ready-set.py"),
          "w", encoding="utf-8") as f:
    f.write(old_ready_set.replace(
        '{"id": tid, "reason": reason, "kind": kind}',
        '{"id": tid, "reason": reason}'))
write_task(proj, "T-001", status="assigned", deps="[]", owns="[a.py]")
write_task(proj, "T-002", status="pending", deps="[T-001]", owns="[b.py]")
write_in_flight_marker(proj, "T-001", "worker-standard")
for _ in range(2):
    run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
rc_skew, _, _ = run_hook("stop-gate.py", {"stop_hook_active": True}, proj)
check("a pre-#163 ready-set.py (no `kind`) still holds a waiting task",
      rc_skew == 2 and not stalled_text(proj), f"rc={rc_skew}")

# ------------------------------------------------------------ dispatch-guard
print("dispatch-guard.py")
proj = fresh_proj()
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "Explore", "prompt": "go"}}, proj)
check("non-guild agent → exit 0", rc == 0, f"rc={rc}")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "do it"}}, proj)
check("worker w/o Task-ID → exit 2", rc == 2 and "no id line" in err, err)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-404"}}, proj)
check("worker, missing task file → exit 2", rc == 2 and "does not exist" in err, err)

write_task(proj, "T-001", status="assigned")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-001"}}, proj)
check("worker before CON-audit PASS → exit 2", rc == 2 and "constitution audit" in err, err)

con_pass(proj)
write_task(proj, "T-001", status="pending")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-001"}}, proj)
check("worker on pending (not assigned) → exit 2", rc == 2 and "not 'assigned'" in err, err)

# model mismatch: task escalated to opus, dispatched with sonnet default
write_task(proj, "T-001", status="assigned", executor="worker-standard", executor_model="opus")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-001"}}, proj)
check("model mismatch (opus task, sonnet dispatch) → exit 2", rc == 2 and "tier 'opus'" in err, err)

# correct model override clears it
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-001", "model": "opus"}}, proj)
check("model match (opus override) → exit 0", rc == 0, f"rc={rc} err={err}")

# wrong executor agent
write_task(proj, "T-001", status="assigned", executor="worker-standard", executor_model="sonnet")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-bulk", "prompt": "Task-ID: T-001", "model": "sonnet"}}, proj)
check("wrong executor agent → exit 2", rc == 2 and "names executor" in err, err)

# happy worker dispatch logs
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-001"}}, proj)
logged = os.path.exists(os.path.join(proj, ".agent-guild", "state", "log", "dispatches.log"))
check("legal worker dispatch → exit 0", rc == 0, f"rc={rc} err={err}")
check("legal worker dispatch → logged", logged)

# retry budget exhausted
write_task(proj, "T-001", status="assigned", retries=3, max_retries=2, executor_model="sonnet")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-001"}}, proj)
check("retries > max → exit 2 (escalate)", rc == 2 and "retry budget" in err, err)

# checker legality
write_task(proj, "T-002", status="checking")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-deterministic", "prompt": "Task-ID: T-002"}}, proj)
check("checker on 'checking' → exit 0", rc == 0, f"rc={rc} err={err}")

write_task(proj, "T-002", status="needs-check")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-deterministic", "prompt": "Task-ID: T-002"}}, proj)
check("checker on 'needs-check' → exit 2", rc == 2 and "not 'checking'" in err, err)

# auditor
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "prompt": "Audit-ID: CON-audit"}}, proj)
check("auditor with Audit-ID → exit 0", rc == 0, f"rc={rc} err={err}")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "prompt": "no id here"}}, proj)
check("auditor w/o Audit-ID → exit 2", rc == 2, f"rc={rc}")

# auditor: paperwork linter gate (#132). These drive a fake standing in for
# check-job-spec.py's CLI contract (exit 0/1/3); what's under test is how the
# hook reacts to each exit, not whether any particular lint rule is right.
write_fake_linter(proj, 0)
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "prompt": "Audit-ID: CON-audit"}}, proj)
check("auditor, linter exits 0 → exit 0", rc == 0, f"rc={rc} err={err}")

write_fake_linter(proj, 1, "job-spec: T-001.md:57 cites a stale line")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "prompt": "Audit-ID: CON-audit"}}, proj)
check("auditor, linter exits 1 → exit 2", rc == 2
      and "T-001.md:57 cites a stale line" in err and "check-job-spec" in err, err)
# The fixture's stderr line has no trailing punctuation on purpose (like the
# real linter's), so this pins that the appended sentence gets its own
# period instead of running on: "...stale line Fix that..." was the bug.
check("auditor, linter exits 1 → message reads as two sentences, not run together",
      "stale line. Fix that before spending an opus auditor" in err, err)

write_fake_linter(proj, 3, "job-spec: could not parse constitution.md")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "prompt": "Audit-ID: CON-audit"}}, proj)
check("auditor, linter exits 3 → exit 2, distinct from exit-1 message",
      rc == 2 and "exit 3" in err and "T-001.md:57 cites a stale line" not in err, err)

# auditor: linter times out (#132's adversarial-checker finding). The allow-
# through decision doesn't change—a hard fail here would deadlock a job
# behind a slow linter—but the gap has to be observable: a log line and a
# stderr note, where before there was nothing at all. AGENT_GUILD_JOB_SPEC_TIMEOUT
# shrinks dispatch-guard's own timeout so this test doesn't wait out the real
# (20s) one; see the seam's justifying comment in dispatch-guard.py.
write_fake_linter(proj, 0, sleep_seconds=1)
gate_gaps = os.path.join(proj, ".agent-guild", "state", "log", "gate-gaps.log")
if os.path.exists(gate_gaps):
    os.remove(gate_gaps)
rc, out, err = run_hook(
    "dispatch-guard.py",
    {"tool_input": {"subagent_type": "auditor", "prompt": "Audit-ID: CON-audit"}},
    proj, extra_env={"AGENT_GUILD_JOB_SPEC_TIMEOUT": "0.1"})
check("auditor, linter times out → exit 0 (allow-through, not a block)",
      rc == 0, f"rc={rc} err={err}")
gate_gap_logged = os.path.exists(gate_gaps) and "CON-audit" in open(gate_gaps).read()
check("auditor, linter times out → gate-gaps.log records the gap",
      gate_gap_logged,
      open(gate_gaps).read() if os.path.exists(gate_gaps) else "gate-gaps.log missing")
check("auditor, linter times out → stderr carries the notice",
      "timed out" in err and "CON-audit" in err, err)

os.remove(os.path.join(proj, ".agent-guild", "scripts", "check-job-spec.py"))
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "prompt": "Audit-ID: CON-audit"}}, proj)
check("auditor, no linter script (payload freeze) → exit 0", rc == 0, f"rc={rc} err={err}")

# a worker is gated on CON-audit only—the linter is auditor-only and must not
# affect it, even while the linter is failing.
proj_worker_linter = fresh_proj()
write_fake_linter(proj_worker_linter, 1, "job-spec: irrelevant to a worker dispatch")
write_task(proj_worker_linter, "T-900", status="assigned")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-900"}},
                        proj_worker_linter)
check("worker w/ failing linter, no CON-audit → exit 2 on CON-audit, not job-spec",
      rc == 2 and "constitution audit" in err and "job-spec" not in err, err)
con_pass(proj_worker_linter)
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-900"}},
                        proj_worker_linter)
check("worker w/ failing linter, CON-audit PASS → exit 0 (linter is auditor-only)",
      rc == 0, f"rc={rc} err={err}")

# audition: an Audition-ID passes with no task file and no CON-audit, because a
# tryout runs outside the lifecycle. Fresh proj so neither exists.
proj_aud = fresh_proj()
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-bulk", "prompt": "Audition-ID: A-001\nSort these lines."}}, proj_aud)
audlog = os.path.exists(os.path.join(proj_aud, ".agent-guild", "state", "log", "dispatches.log"))
check("audition dispatch (Audition-ID, no Task-ID) → exit 0", rc == 0, f"rc={rc} err={err}")
check("audition dispatch → logged", audlog)

# regression: the audition path must not swallow a genuinely untagged dispatch.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-bulk", "prompt": "just sort the lines"}}, proj_aud)
check("no Task-ID and no Audition-ID → exit 2", rc == 2 and "no id line" in err, err)

# ------------------------- dispatch-guard: two distinct labeled ids (#108, #160)
# A prompt carrying two or more DISTINCT labeled ids, each opening its own
# line, is ambiguous on its face—block outright rather than silently pick
# the earliest, since a dispatch-time block is something the dispatcher can
# still act on. This is deliberately LINE-anchored (see
# dispatch-guard.py's `_line_anchored_ids`), not the unanchored match
# `_lib.labeled_ids` does: .agent-guild/CLAUDE.md itself quotes
# `Audit-ID: CON-audit` mid-sentence, and matching that unanchored used to
# refuse any dispatch whose prompt quoted the contract for context (#160),
# on an "ambiguity" that was never there.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor",
                                         "prompt": "Audit-ID: CON-audit\nTask-ID: T-005"}},
                        proj_aud)
check("two line-anchored ids of DIFFERENT kinds → exit 2 (ambiguous)",
      rc == 2 and "more than one" in err, err)
check("ambiguous-id block names both candidate ids",
      "CON-audit" in err and "T-005" in err, err)
check("ambiguous-id block instructs keeping exactly one",
      "exactly one labeled id per dispatch" in err, err)
check("ambiguous-id block says the ids were found as separate lines",
      "separate lines" in err, err)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard",
                                         "prompt": "Task-ID: T-005\nTask-ID: T-007"}},
                        proj_aud)
check("two line-anchored ids of the SAME kind → exit 2 (ambiguous too)",
      rc == 2 and "more than one" in err and "T-005" in err and "T-007" in err, err)

# A mid-sentence mention—including a quoted excerpt of the orchestrator
# contract's own `Audit-ID: CON-audit` example—never opens a line, so it
# never joins the ambiguity check and never blocks the dispatch's own id.
write_task(proj, "T-010", status="assigned")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard",
                                         "prompt": "Task-ID: T-010\n"
                                         "Per the contract: \"Then dispatch the "
                                         "auditor with Audit-ID: CON-audit.\" "
                                         "Not relevant to this dispatch."}},
                        proj)
check("contract text quoted mid-sentence → no longer blocks",
      rc == 0, f"rc={rc} err={err}")

# A single line-anchored id resolves cleanly even when the prompt narrates
# other ids mid-sentence, same as the quoted-contract case above but with
# a mix of kinds.
write_task(proj, "T-011", status="assigned")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard",
                                         "prompt": "Task-ID: T-011\n"
                                         "As background: Audit-ID: CON-audit "
                                         "already passed, and Audition-ID: A-002 "
                                         "ran earlier—neither is this dispatch."}},
                        proj)
check("single line-anchored id + quoted mentions → resolves to the single id",
      rc == 0, f"rc={rc} err={err}")
logged_t011 = "T-011" in open(
    os.path.join(proj, ".agent-guild", "state", "log", "dispatches.log")
).read()
check("single-id-resolves dispatch logged against T-011, not a quoted mention",
      logged_t011)

# ------------------------------- dispatch-guard: a task with no checks (#109)
# Both halves of #109 in one place. A block-scalar check_method now reads, so
# the first task dispatches; one that genuinely names no check for the clauses
# it cites is refused, worker or checker alike.
write_task(proj, "T-003", status="assigned", executor_model="sonnet",
           clauses="[C-1, C-2]",
           check_method=">-\n  C-1: .agent-guild/scripts/check-build.sh\n"
                        "  C-2: checker-judgment: read the diff")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-003"}}, proj)
check("block-scalar check_method → dispatch allowed", rc == 0, f"rc={rc} err={err}")

write_task(proj, "T-003", status="assigned", executor_model="sonnet",
           clauses="[C-1, C-2]", check_method="")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-003"}}, proj)
check("cites clauses, no check_method → worker blocked",
      rc == 2 and "check_method is empty" in err, f"rc={rc} err={err}")
check("that block names the task file",
      ".agent-guild/state/tasks/T-003.md" in err, err)

write_task(proj, "T-003", status="checking", executor_model="sonnet",
           clauses="[C-1]", check_method="")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-deterministic", "prompt": "Task-ID: T-003"}}, proj)
check("cites clauses, no check_method → checker blocked too",
      rc == 2 and "check_method is empty" in err, f"rc={rc} err={err}")

# ------------------------------------------- dispatch-guard: structured id field
# Issue #71: Codex encrypts the dispatch message before any hook runs, so the id
# arrives in a field instead of a prompt line. The gate is host-neutral and takes
# either. Pinned here and not only in the adapter suite, so that losing the field
# branch fails against dispatch-guard itself rather than against one host's
# translation of it.
print("dispatch-guard.py: structured dispatch_id (issue #71)")
proj_id = fresh_proj()
con_pass(proj_id)
write_task(proj_id, "T-001", status="assigned")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "dispatch_id": "T-001",
                                        "prompt": "no id line here, the host encrypted it"}}, proj_id)
check("dispatch_id carries a Task-ID → exit 0", rc == 0, f"rc={rc} err={err}")

# Codex validates task_name as an agent name and rejects anything outside
# [a-z0-9_], so `t_001` is the only spelling that can reach the gate from that
# host. It has to resolve to the same task as `T-001` or the id is unusable
# exactly where #71 needed it to work.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "dispatch_id": "t_001",
                                        "prompt": "no id line here, the host encrypted it"}}, proj_id)
check("underscored wire form resolves to the same task → exit 0", rc == 0, f"rc={rc} err={err}")

with open(os.path.join(proj_id, ".agent-guild", "state", "log", "dispatches.log")) as f:
    logged = f.read()
check("underscored id is logged canonically as T-001",
      "T-001" in logged and "t_001" not in logged, logged)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "dispatch_id": "con_audit"}}, proj_id)
check("underscored Audit-ID resolves → exit 0", rc == 0, f"rc={rc} err={err}")

# With no field to read, the prompt line still decides. That's every Claude
# dispatch, so this is the check that #71 left that host alone.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-001"}}, proj_id)
check("prompt line still works with no dispatch_id → exit 0", rc == 0, f"rc={rc} err={err}")

# A free-text task_name is the common case: it's the dispatcher's own label,
# and reading one as an id would attach the dispatch to a task nobody named.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "dispatch_id": "lifecycle_payload",
                                        "prompt": "no id line"}}, proj_id)
check("dispatch_id in no known namespace → exit 2", rc == 2 and "no id line" in err, err)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "dispatch_id": "CON-audit"}}, proj_id)
check("dispatch_id carries an Audit-ID → exit 0", rc == 0, f"rc={rc} err={err}")

# The auditor takes an Audit-ID and nothing else. This used to raise instead of
# block, which on a PreToolUse hook means exit 1—waved through, not stopped.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "prompt": "Task-ID: T-001"}}, proj_id)
check("auditor handed a Task-ID → exit 2", rc == 2 and "takes an" in err, f"rc={rc} err={err}")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-bulk", "dispatch_id": "A-001"}}, fresh_proj())
check("dispatch_id carries an Audition-ID → exit 0", rc == 0, f"rc={rc} err={err}")

# ------------------------------------- dispatch-guard: per-dispatch names (#77)
# One name per task collides on the second dispatch, because Codex won't reuse
# an agent name in a session. The wire form carries a discriminator after the
# id and the gate strips it back off, so three agents on one task still log,
# check, and escalate as T-001.
print("dispatch-guard.py: per-dispatch task_name (issue #77)")
proj_uniq = fresh_proj()
con_pass(proj_uniq)
write_task(proj_uniq, "T-001", status="assigned")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "dispatch_id": "t_001_r0_worker",
                                        "prompt": "no id line here, the host encrypted it"}}, proj_uniq)
check("discriminated wire name resolves to the task → exit 0", rc == 0, f"rc={rc} err={err}")

with open(os.path.join(proj_uniq, ".agent-guild", "state", "log", "dispatches.log")) as f:
    logged = f.read()
check("discriminator never reaches the dispatch log",
      "T-001" in logged and "t_001" not in logged, logged)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "auditor", "dispatch_id": "con_audit_r0"}}, proj_uniq)
check("discriminated Audit-ID resolves → exit 0", rc == 0, f"rc={rc} err={err}")

# The retry ladder re-dispatches the same role, so the retry counter is what
# keeps the second attempt's name distinct from the first's.
write_task(proj_uniq, "T-001", status="assigned", retries=1)
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "dispatch_id": "t_001_r1_worker",
                                        "prompt": "rework"}}, proj_uniq)
check("a retry's distinct name still resolves → exit 0", rc == 0, f"rc={rc} err={err}")

# ------------------------------------- dispatch-guard: followup refusal (#77)
# A followup re-tasks an agent that already exists. It carries no agent type,
# no id, and no readable prompt, so there is nothing to check it against—and
# leaving it ungated let a whole job run while this gate never applied. Pinned
# against the gate itself, not only against the adapter that translates it.
print("dispatch-guard.py: followup_task refusal (issue #77)")
proj_fu = fresh_proj()
con_pass(proj_fu)
write_task(proj_fu, "T-001", status="checking")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"followup_target": "t_001"}}, proj_fu)
check("followup at a guild agent → exit 2", rc == 2 and "not allowed" in err, f"rc={rc} err={err}")
check("followup refusal names a fresh name to use instead", "t_001_r0_checker" in err, err)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"followup_target": "/root/t_001/t_001_r0_worker"}}, proj_fu)
check("followup through a rooted agent path → exit 2", rc == 2 and "T-001" in err, f"rc={rc} err={err}")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"followup_target": "research_helper"}}, proj_fu)
check("followup at a non-guild agent → exit 0", rc == 0, f"rc={rc} err={err}")

check("a refused followup is never logged as a dispatch",
      not os.path.exists(os.path.join(proj_fu, ".agent-guild", "state", "log", "dispatches.log")),
      "dispatches.log exists")

# ---------------------------------------- dispatch-guard: namespaced subagent_type
# Issue #27: a plugin-installed guild ships subagent_type as `<plugin>:<name>`
# (e.g. `agent-guild:worker-standard`), and a bare-name GUILD_AGENTS membership
# test used to miss it entirely, waving the dispatch through with none of the
# gates below applied.
print("dispatch-guard.py: namespaced subagent_type (issue #27)")
proj_ns = fresh_proj()

# Same block as the bare-name case above, now with a namespaced subagent_type:
# proves normalization happens before the id-line check, not after it.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "agent-guild:worker-standard",
                                        "prompt": "do it, no id line"}}, proj_ns)
check("namespaced worker w/o Task-ID → exit 2, blocked like bare form",
      rc == 2 and "has no id line" in err, err)

# Fully legal namespaced dispatch, no model override: effective_model falls
# back to DEFAULT_MODEL[agent], which KeyErrors if `agent` were left raw
# instead of normalized, and the executor comparison (`agent != executor`)
# fails the same way against the task's bare `executor:` field. Both traps
# only fire when the dispatch is otherwise legal enough to reach them.
con_pass(proj_ns)
write_task(proj_ns, "T-010", status="assigned", executor="worker-standard", executor_model="sonnet")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "agent-guild:worker-standard",
                                        "prompt": "Task-ID: T-010"}}, proj_ns)
check("namespaced worker, fully legal (no DEFAULT_MODEL KeyError, no executor mismatch) → exit 0",
      rc == 0, f"rc={rc} err={err}")

# The audit trail must show what actually ran, not the normalized form: a
# strip-in-_log bug would collapse this back to "worker-standard" and the log
# could no longer distinguish a plugin dispatch from an in-repo one.
with open(os.path.join(proj_ns, ".agent-guild", "state", "log", "dispatches.log"), encoding="utf-8") as f:
    dispatch_log = f.read()
check("dispatch log records the RAW namespaced string, not the bare name",
      "agent-guild:worker-standard" in dispatch_log, dispatch_log)

# Bare-name regression: the same fully-legal shape, un-namespaced, must still
# pass now that the entry seam runs bare_agent() on every subagent_type.
write_task(proj_ns, "T-011", status="assigned", executor="worker-standard", executor_model="sonnet")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard", "prompt": "Task-ID: T-011"}}, proj_ns)
check("bare-name worker, fully legal (regression after normalization) → exit 0",
      rc == 0, f"rc={rc} err={err}")

# ------------------------------------------- dispatch-guard: checker-courier
# Issue #8: checker-courier is the second-opinion lane—dispatchable on any
# checking task regardless of the task's own `checker` field—so these
# fixtures pin its three extra denials on top of that already-legal path.
print("dispatch-guard.py: checker-courier (issue #8)")
proj_courier = fresh_proj()
con_pass(proj_courier)
write_task(proj_courier, "T-020", status="checking", checker="checker-judgment")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-020"}}, proj_courier)
check("checker-courier on checking task named for checker-judgment → exit 0",
      rc == 0, f"rc={rc} err={err}")

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-020", "model": "opus"}}, proj_courier)
check("checker-courier with a model override → exit 2, says drop the override",
      rc == 2 and "Drop the override" in err, err)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": "Task-ID: T-020\nRun it with workspace-write access."}}, proj_courier)
check("checker-courier requesting workspace-write → exit 2, read-only by contract",
      rc == 2 and "read-only" in err, err)

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": "Task-ID: T-020\nRun with danger-full-access."}}, proj_courier)
check("checker-courier requesting danger-full-access → exit 2, read-only by contract",
      rc == 2 and "read-only" in err, err)

os.makedirs(os.path.join(proj_courier, ".agent-guild", "state", "exhausted"), exist_ok=True)
open(os.path.join(proj_courier, ".agent-guild", "state", "exhausted", "codex"), "w").close()
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-020"}}, proj_courier)
# The negative half is the point: a message that names the in-family checker
# reads as "go re-run it," and a substituted verdict at the lane-suffixed stem
# would let #34 count a same-host check as cross-vendor agreement. (#97)
check("checker-courier dispatch under exhausted/codex → exit 2, substitutes nothing",
      rc == 2 and "Nothing is substituted" in err and "PAUSED" in err
      and "checker-judgment" not in err, err)
os.remove(os.path.join(proj_courier, ".agent-guild", "state", "exhausted", "codex"))

rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-020"}}, proj_courier)
check("checker-courier dispatch once sentinel is cleared → exit 0", rc == 0, f"rc={rc} err={err}")

# --------------------------------- dispatch-guard: in-flight markers (#111)
# Every allowed dispatch drops a marker under state/log/in-flight/ so
# stop-gate.py can tell a genuinely running subagent apart from a stuck loop.
print("dispatch-guard.py: in-flight markers (#111)")
proj_dm = fresh_proj()
con_pass(proj_dm)
write_task(proj_dm, "T-040", status="assigned")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard",
                                        "prompt": "Task-ID: T-040"}}, proj_dm)
check("legal worker dispatch → exit 0", rc == 0, f"rc={rc} err={err}")
worker_marker = os.path.join(proj_dm, ".agent-guild", "state", "log",
                             "in-flight", "T-040--worker-standard.json")
check("legal worker dispatch → writes an in-flight marker",
      os.path.exists(worker_marker), worker_marker)
with open(worker_marker, encoding="utf-8") as f:
    marker_body = json.load(f)
check("in-flight marker → dispatched_at looks like UTC ISO8601 with a Z",
      isinstance(marker_body.get("dispatched_at"), str)
      and marker_body["dispatched_at"].endswith("Z"),
      marker_body)

write_task(proj_dm, "T-041", status="checking")
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": "Task-ID: T-041"}}, proj_dm)
check("legal checker-courier dispatch → exit 0", rc == 0, f"rc={rc} err={err}")
check("legal checker-courier dispatch → writes an in-flight marker",
      os.path.exists(os.path.join(proj_dm, ".agent-guild", "state", "log",
                                  "in-flight", "T-041--checker-courier.json")))

# A BLOCKED dispatch must never write a marker: only allowed dispatches mark.
proj_dm_block = fresh_proj()
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-standard",
                                        "prompt": "do it"}}, proj_dm_block)
check("blocked dispatch (no id) → exit 2 (unchanged)", rc == 2, f"rc={rc}")
check("blocked dispatch → no in-flight marker written",
      not os.path.exists(os.path.join(proj_dm_block, ".agent-guild", "state",
                                      "log", "in-flight")))

# ----------------- the courier after #167: opt-in, no crossing debt
# #34 ruled the cross-family bet does not pay, and #167 made the second
# opinion opt-in: nothing auto-dispatches a courier, and no verdict of record
# owes a crossing. What survives is the lane itself and the #100 guard, so
# these cases pin the three things that actually changed behavior.
print("checker-courier: opt-in, no crossing debt (#167)")

# 1. A verdict of record with no lane sibling ends the turn. This blocked
# before #167, on a debt nothing had discharged. The positive control is the
# same fixture with the task still open, so a clean exit can't be "the gate
# never looked."
proj = fresh_proj()
write_task(proj, "T-080", status="complete", retries=0)
write_verdict_json(proj, "T-080-sonnet-r0.json", task_id="T-080")
rc_clean, _, err_clean = run_hook("stop-gate.py", {}, proj)
write_task(proj, "T-081", status="checking", retries=0)
rc_open, _, _ = run_hook("stop-gate.py", {}, proj)
check("so: a verdict of record with no second opinion no longer holds the turn",
      rc_clean == 0 and rc_open == 2, f"rc_clean={rc_clean} err={err_clean!r} rc_open={rc_open}")

# 2. dispatch-guard's courier widening is gone with the debt it existed to
# make collectable: checker-courier is held to `checking` like every other
# checker. Paired with the allow-case on the identical fixture so the refusal
# is pinned to the status and nothing else.
proj = fresh_proj()
write_task(proj, "T-082", status="complete", retries=0)
write_verdict_json(proj, "T-082-sonnet-r0.json", task_id="T-082")
rc_done, _, err_done = run_hook(
    "dispatch-guard.py",
    {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-082"}}, proj)
write_task(proj, "T-082", status="checking", retries=0)
rc_checking, _, err_checking = run_hook(
    "dispatch-guard.py",
    {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-082"}}, proj)
check("so: checker-courier is refused off `checking`, like every other checker",
      rc_done == 2 and "not 'checking'" in err_done and rc_checking == 0,
      f"rc_done={rc_done} err={err_done!r} rc_checking={rc_checking} err={err_checking!r}")

# 3. C-2, the #100 incident verbatim: a courier dispatched for T-051 also
# wrote a sibling's (T-052) verdict, and T-052 was never itself dispatched.
# The write is surfaced as a row under state/log/ naming both Task-IDs.
# #167 took the reservation records this used to read; the in-flight marker
# is the substitute, written on the same legal-dispatch path.
proj = fresh_proj()
seed_verdict_toolchain(proj)
write_task(proj, "T-051", status="checking", retries=0)
write_task(proj, "T-052", status="checking", retries=0)
run_hook("dispatch-guard.py",
         {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-051"}}, proj)
write_verdict_json(proj, "T-051-sonnet-r0.json", task_id="T-051")
write_verdict_json(proj, "T-051-sonnet-r0-codex.json", task_id="T-051",
                   checker="checker-courier", vendor="openai", model="gpt-5.6-terra")
# T-052's verdict shows up too, from no dispatch of its own—the #100 shape.
write_verdict_json(proj, "T-052-sonnet-r0.json", task_id="T-052")
write_verdict_json(proj, "T-052-sonnet-r0-codex.json", task_id="T-052",
                   checker="checker-courier", vendor="openai", model="gpt-5.6-terra")
tx = transcript(proj, "Task-ID: T-051")
rc_return, _, err_return = run_hook(
    "subagent-return.py", {"agent_type": "checker-courier", "transcript_path": tx}, proj)
log_path = os.path.join(proj, ".agent-guild", "state", "log", "foreign-stem-writes.log")
log_text = open(log_path, encoding="utf-8").read() if os.path.exists(log_path) else ""
check("so: a foreign-stem write (#100) is surfaced under state/log/, naming both Task-IDs",
      rc_return == 0 and "T-051" in log_text and "T-052" in log_text,
      f"rc_return={rc_return} log={log_text!r}")

# The allow-case, differing in exactly the one thing under test: T-054 WAS
# legitimately dispatched, so its own courier marker is still fresh. That is
# the concurrency shape C-2 requires not be mistaken for the incident, and
# it's the case the marker re-basing has to keep getting right.
proj2 = fresh_proj()
seed_verdict_toolchain(proj2)
write_task(proj2, "T-053", status="checking", retries=0)
write_task(proj2, "T-054", status="checking", retries=0)
run_hook("dispatch-guard.py",
         {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-053"}}, proj2)
run_hook("dispatch-guard.py",
         {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-054"}}, proj2)
write_verdict_json(proj2, "T-053-sonnet-r0.json", task_id="T-053")
write_verdict_json(proj2, "T-053-sonnet-r0-codex.json", task_id="T-053",
                   checker="checker-courier", vendor="openai", model="gpt-5.6-terra")
write_verdict_json(proj2, "T-054-sonnet-r0.json", task_id="T-054")
write_verdict_json(proj2, "T-054-sonnet-r0-codex.json", task_id="T-054",
                   checker="checker-courier", vendor="openai", model="gpt-5.6-terra")
tx2 = transcript(proj2, "Task-ID: T-053")
rc_return2, _, err_return2 = run_hook(
    "subagent-return.py", {"agent_type": "checker-courier", "transcript_path": tx2}, proj2)
log_path2 = os.path.join(proj2, ".agent-guild", "state", "log", "foreign-stem-writes.log")
log_text2 = open(log_path2, encoding="utf-8").read() if os.path.exists(log_path2) else ""
check("so: a concurrent courier's own in-flight crossing is never surfaced as foreign (C-2)",
      rc_return2 == 0 and "T-054" not in log_text2, f"rc={rc_return2} log={log_text2!r}")

# A STALE marker must not keep granting that exemption: whatever ran never
# came back, so a lane file at its stem is a foreign write again. Same
# fixture as the allow-case above, with T-054's marker aged out through the
# same env seam _lib.in_flight() reads.
rc_return3, _, _ = run_hook(
    "subagent-return.py", {"agent_type": "checker-courier", "transcript_path": tx2}, proj2,
    extra_env={"AGENT_GUILD_INFLIGHT_STALE_S": "0"})
log_text3 = open(log_path2, encoding="utf-8").read() if os.path.exists(log_path2) else ""
check("so: a stale courier marker stops exempting its stem (C-2)",
      rc_return3 == 0 and "T-054" in log_text3, f"rc={rc_return3} log={log_text3!r}")

# --------------------------------------------------------- subagent-return
print("subagent-return.py")
proj = fresh_proj()
rc, out, err = run_hook("subagent-return.py", {"agent_type": "Explore"}, proj)
check("non-guild agent → exit 0", rc == 0, f"rc={rc}")

write_task(proj, "T-001", status="needs-check", artifacts="[out.html]")
tx = transcript(proj, "Task-ID: T-001\nGo build it.")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("worker returned clean → exit 0", rc == 0, f"rc={rc} err={err}")

# content-as-list transcript variant
tx = transcript(proj, "Task-ID: T-001", content_list=True)
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("worker, list-content transcript → exit 0", rc == 0, f"rc={rc} err={err}")

# REAL CC shape: id lives only in the assistant tool_use(Task) dispatch, and the
# human's own turn says "Task-ID is T-001" (no colon, unmatchable). This is the
# exact case that infinite-hung the worker before the id-extraction fix.
tx = dispatch_transcript(proj, "Task-ID: T-001\n\nYou are the worker. Build it.",
                         user_text="Dispatch the executor for T-001. Its Task-ID is T-001.")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("worker, tool_use-dispatch transcript → exit 0", rc == 0, f"rc={rc} err={err}")

# same, via the Agent tool name
tx = dispatch_transcript(proj, "Task-ID: T-001\nGo.", tool="Agent")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("worker, Agent-tool dispatch transcript → exit 0", rc == 0, f"rc={rc} err={err}")

write_task(proj, "T-001", status="assigned", artifacts="[]")
tx = transcript(proj, "Task-ID: T-001")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("worker skipped protocol → exit 2", rc == 2 and "Protocol incomplete" in err, err)

write_task(proj, "T-001", status="needs-check", artifacts="[]")
tx = transcript(proj, "Task-ID: T-001")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("worker needs-check but no artifacts → exit 2", rc == 2 and "artifacts" in err, err)

# checker paths: the verdict of record is JSON at T-NNN-<tier>-r<retries>.json,
# gated by running it through validate-verdict.py (the same CLI contract
# test_verdict_tools.py exercises directly). Six fixture cases per issue #29's
# C-5: a conforming pass, a missing file, malformed JSON, a schema violation,
# a semantic violation (fail with no findings), and a conforming blocked.
seed_verdict_toolchain(proj)
write_task(proj, "T-002", status="checking", executor_model="sonnet", retries=0)
vjson = os.path.join(proj, ".agent-guild", "state", "verdicts", "T-002-sonnet-r0.json")

write_verdict_json(proj, "T-002-sonnet-r0.json", verdict="pass")
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker wrote conforming JSON verdict → exit 0", rc == 0, f"rc={rc} err={err}")

os.remove(vjson)
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker, missing verdict JSON → exit 2, names the path",
      rc == 2 and "T-002-sonnet-r0.json" in err, err)

with open(vjson, "w", encoding="utf-8") as f:
    f.write("{not valid json")
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker, malformed verdict JSON → exit 2", rc == 2 and "T-002-sonnet-r0.json" in err, err)

write_verdict_json(proj, "T-002-sonnet-r0.json", verdict="maybe")
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker, schema violation (bad verdict enum) → exit 2, names the field",
      rc == 2 and "verdict" in err, err)

write_verdict_json(proj, "T-002-sonnet-r0.json", verdict="fail", findings=[])
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker, fail verdict with empty findings → exit 2, names findings",
      rc == 2 and "findings" in err, err)

write_verdict_json(proj, "T-002-sonnet-r0.json", verdict="blocked", findings=[])
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker, conforming blocked verdict → exit 0", rc == 0, f"rc={rc} err={err}")

# no id in transcript: fail loud but don't hang (exit 0), same as the block above
tx = transcript(proj, "I did the work but never mention the id")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("no id in transcript → exit 0 loud, no hang", rc == 0 and "could not identify" in err, err)

# Identification failure must NOT hang the subagent. A SubagentStop block only
# helps when the subagent can act on it, and it can't fix a bad transcript—so an
# id failure fails loud and exits 0, leaving the still-open task to the stop-gate.
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": "/no/such/file.jsonl"}, proj)
check("missing transcript → exit 0 loud, no hang", rc == 0 and "could not identify" in err, err)

tx = transcript(proj, "worker chatter with no id anywhere")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("transcript with no id → exit 0 loud, no hang", rc == 0 and "could not identify" in err, err)

tx = dispatch_transcript(proj, "Task-ID: T-777\nwork", tool="Agent")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("id resolves but no task file → exit 0 loud, no hang", rc == 0 and "could not identify" in err, err)

# auditor return
con_pass(proj)
tx = transcript(proj, "Audit-ID: CON-audit")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "auditor", "transcript_path": tx}, proj)
check("auditor wrote CON-audit verdict → exit 0", rc == 0, f"rc={rc} err={err}")

# regression (#108): an auditor's OWN dispatch prompt often carries context
# about other work in flight—here, a note about T-005, still open, labeled
# with its own Task-ID. The old _id_in short-circuited TASK_ID_RE before
# AUDIT_ID_RE regardless of which label actually came first in the text, so
# this transcript used to resolve to T-005 and the auditor got told to write
# a verdict at a task stem it should never touch.
tx = dispatch_transcript(
    proj,
    "Audit-ID: CON-audit\n\nFor context, T-005 is still open "
    "(Task-ID: T-005), assigned to worker-standard. Audit the "
    "constitution regardless.",
)
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "auditor", "transcript_path": tx}, proj)
check("auditor prompt also carrying a Task-ID → still resolves to the audit",
      rc == 0, f"rc={rc} err={err}")
check("auditor never asked for a task-stem verdict",
      "T-005" not in err, err)

# audition return: an A-NNN ident finishes without a task file or verdict, since
# the battery scorer judges the output, not this gate.
tx = transcript(proj, "Audition-ID: A-001\nSort these lines.")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-bulk", "transcript_path": tx}, proj)
check("audition subagent (A-001 transcript) → exit 0", rc == 0, f"rc={rc} err={err}")

# in-subagent scope: this gate judges the returning subagent solely against the
# task named in ITS OWN dispatch. A sibling task sitting incomplete must never
# leak into the exit code or the message.
proj_scope = fresh_proj()
write_task(proj_scope, "T-001", status="needs-check", artifacts="[out.html]")
write_task(proj_scope, "T-002", status="assigned")  # sibling: not this worker's task
tx = transcript(proj_scope, "Task-ID: T-001\nGo build it.")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj_scope)
check("worker clean return on T-001 while T-002 sits assigned → exit 0, no T-002 mention",
      rc == 0 and "T-002" not in out and "T-002" not in err, f"rc={rc} out={out!r} err={err!r}")

seed_verdict_toolchain(proj_scope)
write_task(proj_scope, "T-001", status="checking", executor_model="sonnet", retries=0)
write_task(proj_scope, "T-002", status="checking")  # sibling: verdict-less, not this checker's task
write_verdict_json(proj_scope, "T-001-sonnet-r0.json", task_id="T-001", verdict="pass")
tx = transcript(proj_scope, "Task-ID: T-001")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj_scope)
check("checker valid return on T-001 while T-002 has no verdict → exit 0, no T-002 demand",
      rc == 0 and "T-002" not in out and "T-002" not in err, f"rc={rc} out={out!r} err={err!r}")

# --------------------------------- subagent-return: in-flight markers (#111)
print("subagent-return.py: in-flight markers (#111)")


def _in_flight_path(proj, tid, agent):
    return os.path.join(proj, ".agent-guild", "state", "log", "in-flight",
                        f"{tid}--{agent}.json")


proj_mark = fresh_proj()
write_task(proj_mark, "T-030", status="needs-check", artifacts="[out.html]")
write_in_flight_marker(proj_mark, "T-030", "worker-standard")
marker_path = _in_flight_path(proj_mark, "T-030", "worker-standard")
tx = transcript(proj_mark, "Task-ID: T-030\nGo build it.")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj_mark)
check("worker clean return → exit 0", rc == 0, f"rc={rc} err={err}")
check("worker clean return → its in-flight marker is cleared",
      not os.path.exists(marker_path), marker_path)

# A block leaves the marker alone: the agent hasn't finished, so nothing
# should read it as no longer in flight.
proj_block = fresh_proj()
write_task(proj_block, "T-031", status="assigned", artifacts="[]")  # protocol incomplete
write_in_flight_marker(proj_block, "T-031", "worker-standard")
marker_path = _in_flight_path(proj_block, "T-031", "worker-standard")
tx = transcript(proj_block, "Task-ID: T-031")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj_block)
check("worker protocol incomplete → exit 2 (unchanged)", rc == 2, f"rc={rc}")
check("blocked return → marker is left in place", os.path.exists(marker_path), marker_path)

# An unidentifiable return also leaves the marker alone—staleness, not this
# gate, is what eventually ages it out.
proj_unid = fresh_proj()
write_in_flight_marker(proj_unid, "T-032", "worker-standard")
marker_path = _in_flight_path(proj_unid, "T-032", "worker-standard")
tx = transcript(proj_unid, "chatter with no id anywhere")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj_unid)
check("unidentifiable return → exit 0 loud (unchanged)",
      rc == 0 and "could not identify" in err, err)
check("unidentifiable return → marker is left in place",
      os.path.exists(marker_path), marker_path)

# A checker's clean return clears its own marker too.
proj_check_mark = fresh_proj()
seed_verdict_toolchain(proj_check_mark)
write_task(proj_check_mark, "T-033", status="checking", executor_model="sonnet", retries=0)
write_verdict_json(proj_check_mark, "T-033-sonnet-r0.json", task_id="T-033", verdict="pass")
write_in_flight_marker(proj_check_mark, "T-033", "checker-deterministic")
marker_path = _in_flight_path(proj_check_mark, "T-033", "checker-deterministic")
tx = transcript(proj_check_mark, "Task-ID: T-033")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj_check_mark)
check("checker clean return → exit 0", rc == 0, f"rc={rc} err={err}")
check("checker clean return → its in-flight marker is cleared",
      not os.path.exists(marker_path), marker_path)

# ------------------------------------------- subagent-return: checker-courier
print("subagent-return.py: checker-courier (issue #8)")

# Valid lane-suffixed verdict accepted; the in-family checker's OWN return on
# the same task still validates at the standard (unsuffixed) stem—the lane
# suffix is courier-only, never a change to what checker-judgment writes.
proj_lane = fresh_proj()
seed_verdict_toolchain(proj_lane)
write_task(proj_lane, "T-021", status="checking", checker="checker-judgment",
           executor_model="sonnet", retries=0)

write_verdict_json(proj_lane, "T-021-sonnet-r0-codex.json",
                    task_id="T-021", checker="checker-courier", vendor="openai",
                    model="gpt-5.6-terra", verdict="pass")
tx = transcript(proj_lane, "Task-ID: T-021")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-courier", "transcript_path": tx}, proj_lane)
check("checker-courier valid lane-suffixed verdict (T-NNN-<tier>-r<retries>-codex.json) → exit 0",
      rc == 0, f"rc={rc} err={err}")

write_verdict_json(proj_lane, "T-021-sonnet-r0.json",
                    task_id="T-021", checker="checker-judgment", verdict="pass")
tx = transcript(proj_lane, "Task-ID: T-021")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-judgment", "transcript_path": tx}, proj_lane)
check("in-family checker return on the same task still validated at the standard stem → exit 0",
      rc == 0, f"rc={rc} err={err}")

# Quota return: sentinel + a ledger line (real ledger-append.py) carrying
# quota_event: true + no suffixed verdict file at all → accepted.
proj_quota = fresh_proj()
seed_verdict_toolchain(proj_quota)
write_task(proj_quota, "T-022", status="checking", checker="checker-deterministic",
           executor_model="sonnet", retries=0)
os.makedirs(os.path.join(proj_quota, ".agent-guild", "state", "exhausted"), exist_ok=True)
open(os.path.join(proj_quota, ".agent-guild", "state", "exhausted", "codex"), "w").close()
seed_ledger_line(proj_quota, "T-022", quota_event=True)
tx = transcript(proj_quota, "Task-ID: T-022")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-courier", "transcript_path": tx}, proj_quota)
check("checker-courier quota return (ledger quota_event + sentinel, no verdict) → exit 0",
      rc == 0, f"rc={rc} err={err}")

# The identity negatives (#142). Each of these verdicts is schema-valid and
# semantically fine; the only thing wrong is a claim about who produced it.
# Before this gate existed, all four were filed without comment, and one of
# them—model "gpt-5.6" where the lane pins "gpt-5.6-terra"—is sitting in the
# #34 corpus because of it.
for field, bad, expected in (
    ("model", "gpt-5.6", "gpt-5.6-terra"),
    ("vendor", "anthropic", "openai"),
    ("checker", "checker-judgment", "checker-courier"),
    ("task_id", "T-999", "T-024"),
):
    proj_ident = fresh_proj()
    seed_verdict_toolchain(proj_ident)
    write_task(proj_ident, "T-024", status="checking", checker="checker-judgment",
               executor_model="sonnet", retries=0)
    fixture = {"task_id": "T-024", "checker": "checker-courier",
               "vendor": "openai", "model": "gpt-5.6-terra", "verdict": "pass"}
    fixture[field] = bad
    write_verdict_json(proj_ident, "T-024-sonnet-r0-codex.json", **fixture)
    tx = transcript(proj_ident, "Task-ID: T-024")
    rc, out, err = run_hook("subagent-return.py",
                            {"agent_type": "checker-courier", "transcript_path": tx}, proj_ident)
    check(f"checker-courier lane verdict with a wrong {field} → exit 2",
          rc == 2 and field in err and repr(expected) in err,
          f"rc={rc} err={err}")

# A fail is a judgment, not an identity problem: the gate must not confuse the
# two, or it becomes a second way for the lane to reject sound work.
proj_fail = fresh_proj()
seed_verdict_toolchain(proj_fail)
write_task(proj_fail, "T-025", status="checking", checker="checker-judgment",
           executor_model="sonnet", retries=0)
write_verdict_json(proj_fail, "T-025-sonnet-r0-codex.json",
                   task_id="T-025", checker="checker-courier", vendor="openai",
                   model="gpt-5.6-terra", verdict="fail",
                   findings=[{"clause_id": "C-7", "severity": "major",
                              "description": "the artifact misses the clause",
                              "evidence": "line 12"}])
tx = transcript(proj_fail, "Task-ID: T-025")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-courier", "transcript_path": tx}, proj_fail)
check("checker-courier lane verdict with correct identity and a fail → exit 0",
      rc == 0, f"rc={rc} err={err}")

# And the check stays inside its lane: an in-family verdict of record names
# whichever model ran it, and has no pinned identity to be measured against.
proj_infam = fresh_proj()
seed_verdict_toolchain(proj_infam)
write_task(proj_infam, "T-026", status="checking", checker="checker-judgment",
           executor_model="sonnet", retries=0)
write_verdict_json(proj_infam, "T-026-sonnet-r0.json",
                   task_id="T-026", checker="checker-judgment",
                   model="some-other-model", verdict="pass")
tx = transcript(proj_infam, "Task-ID: T-026")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-judgment", "transcript_path": tx}, proj_infam)
check("in-family verdict of record keeps its own free-choice model → exit 0",
      rc == 0, f"rc={rc} err={err}")

# Negative: neither a valid suffixed verdict nor quota evidence present → denied.
proj_noquota = fresh_proj()
seed_verdict_toolchain(proj_noquota)
write_task(proj_noquota, "T-023", status="checking", checker="checker-deterministic",
           executor_model="sonnet", retries=0)
tx = transcript(proj_noquota, "Task-ID: T-023")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-courier", "transcript_path": tx}, proj_noquota)
check("checker-courier return with neither verdict nor quota evidence → exit 2",
      rc == 2 and "quota bailout" in err, err)

# --------------------------------------------------- orchestrator-write-guard
print("subagent-return.py: marker key normalization (#163)")

# The two sides of the in-flight marker agreed only by accident.
# dispatch-guard writes {ident}--{bare-agent}.json, having run bare_agent()
# at dispatch; this hook compared the RAW agent_type against GUILD_AGENTS,
# which a namespaced type like "agent-guild:worker-standard" always fails.
# So it returned 0 on the membership test before validation OR the marker
# clear ever ran—not a namespaced return being checked and passing, but one
# the gate never looked at, leaving its marker to age out over the full TTL.
proj = fresh_proj()
write_task(proj, "T-041", status="needs-check", artifacts="[out.html]")
write_in_flight_marker(proj, "T-041", "worker-standard")
ns_marker = _in_flight_path(proj, "T-041", "worker-standard")
tx = transcript(proj, "Task-ID: T-041\nGo build it.")
rc, out, err = run_hook(
    "subagent-return.py",
    {"agent_type": "agent-guild:worker-standard", "transcript_path": tx}, proj)
check("namespaced worker, clean return → exit 0", rc == 0, f"rc={rc} err={err}")
check("namespaced worker, clean return → its bare-named marker is cleared",
      not os.path.exists(ns_marker), ns_marker)

# Same namespaced type, protocol incomplete: it has to fail validation now
# rather than be waved through unseen.
proj = fresh_proj()
write_task(proj, "T-042", status="assigned", artifacts="[]")
tx = transcript(proj, "Task-ID: T-042")
rc, out, err = run_hook(
    "subagent-return.py",
    {"agent_type": "agent-guild:worker-standard", "transcript_path": tx}, proj)
check("namespaced worker, protocol incomplete → exit 2 (validation now applies)",
      rc == 2 and "Protocol incomplete" in err, err)

# The one _unidentifiable() caller that knows its ident. The other two are
# structurally blind—the marker is keyed on exactly the thing they can't
# read—so they leave it for the TTL rather than glob for it and risk
# deleting a live wave sibling's. This one can name it, and a subagent that
# genuinely finished shouldn't suppress its own task's backstop for an hour
# over a task file that no longer exists.
proj = fresh_proj()
write_in_flight_marker(proj, "T-040", "worker-standard")
gone_marker = _in_flight_path(proj, "T-040", "worker-standard")
tx = transcript(proj, "Task-ID: T-040\nGo build it.")
rc, out, err = run_hook(
    "subagent-return.py",
    {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("no task file → exit 0 loud, no hang",
      rc == 0 and "could not identify" in err, err)
check("no task file → its in-flight marker is cleared",
      not os.path.exists(gone_marker), gone_marker)

# ------------------------------------------------------ orchestrator-write-guard
print("orchestrator-write-guard.py")
proj = fresh_proj()
rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, "README.md")}}, proj)
check("no job → any write allowed (exit 0)", rc == 0, f"rc={rc}")

write_task(proj, "T-001", status="assigned")
rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, ".agent-guild", "state", "spec.md")}}, proj)
check("job active, write under .agent-guild/state/ → exit 0", rc == 0, f"rc={rc} err={err}")

rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, "README.md")}}, proj)
check("job active, write outside .agent-guild/state/ → exit 2", rc == 2 and "orchestrator contract" in err.lower(), err)

# The same forbidden write, but from a SUBAGENT (agent_id present). PreToolUse
# fires inside subagents, so the gate must pass a worker writing its deliverable.
rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"agent_id": "sub-xyz", "agent_type": "worker-standard",
                         "tool_input": {"file_path": os.path.join(proj, "guild-motto.txt")}}, proj)
check("job active, subagent (agent_id) writes deliverable → exit 0", rc == 0, f"rc={rc} err={err}")

open(os.path.join(proj, ".agent-guild", "state", "PAUSED"), "w").close()
rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, "README.md")}}, proj)
check("PAUSED lifts write-guard → exit 0", rc == 0, f"rc={rc}")

# --------------------------------------------------------- session-nudge.py
print("session-nudge.py")

zero_evidence = tempfile.mkdtemp(prefix="ag-nudge-zero-")
rc, out, err = run_hook("session-nudge.py", {}, zero_evidence)
check("no .agent-guild/ at all → silent, exit 0", rc == 0 and out == "", f"rc={rc} out={out!r}")

partial_no_state_dirs = tempfile.mkdtemp(prefix="ag-nudge-nostate-")
os.makedirs(os.path.join(partial_no_state_dirs, ".agent-guild"))
rc, out, err = run_hook("session-nudge.py", {}, partial_no_state_dirs)
check("state dirs missing → nudges, mentions init", rc == 0 and "init" in out, f"rc={rc} out={out!r}")
check("state dirs missing → exactly one stdout line", out.count("\n") == 1, f"out={out!r}")

# fresh_proj() makes every state/ subdir but no root CLAUDE.md—exactly the
# "state complete, import line missing" case.
no_import_line = fresh_proj()
rc, out, err = run_hook("session-nudge.py", {}, no_import_line)
check("CLAUDE.md missing → nudges, mentions init", rc == 0 and "init" in out, f"rc={rc} out={out!r}")

fully_init = fresh_proj()
with open(os.path.join(fully_init, "CLAUDE.md"), "w") as f:
    f.write("See @.agent-guild/CLAUDE.md for the orchestrator contract.\n")
rc, out, err = run_hook("session-nudge.py", {}, fully_init)
check("fully initialized → silent, exit 0", rc == 0 and out == "", f"rc={rc} out={out!r}")

# ------------------------------------------- session-nudge.py: double-registration (issue #41)
print("session-nudge.py: double-registration detection (issue #41)")

# A real copy-in .claude/settings.json wires dispatch-guard.py under PreToolUse,
# same shape as this repo's own .claude/settings.json.
COPY_IN_GUILD_HOOKS = {
    "PreToolUse": [
        {"matcher": "Task|Agent", "hooks": [
            {"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.agent-guild/hooks/dispatch-guard.py\""}
        ]},
    ],
}
UNRELATED_HOOKS = {
    "PreToolUse": [
        {"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 some-other-projects-linter.py"}
        ]},
    ],
}

# run_hook() always execs the real script under THIS repo's .agent-guild/hooks/,
# never under the scratch proj dir, so every case below is already
# plugin-rooted without any extra faking (see copy_in_hooks()'s docstring).
plugin_rooted_hit = tempfile.mkdtemp(prefix="ag-nudge-dblreg-hit-")
write_settings_json(plugin_rooted_hit, COPY_IN_GUILD_HOOKS)
rc, out, err = run_hook("session-nudge.py", {}, plugin_rooted_hit)
check("plugin-rooted + copy-in settings.json → one double-registration warning",
      rc == 0 and "registered twice" in out, f"rc={rc} out={out!r}")
check("plugin-rooted + copy-in settings.json → exactly one stdout line",
      out.count("\n") == 1, f"out={out!r}")
check("double-registration warning cites the verified stall-counter consequence",
      "STALLED after two real blocks" in out, out)
check("double-registration warning names --scope local, not --scope project, as the resolution",
      "--scope local" in out and "never --scope project" in out, out)
check("double-registration warning names the kendrick-qualified plugin id",
      "agent-guild@kendrick" in out and "agent-guild@agent-guild" not in out, out)

plugin_rooted_miss = tempfile.mkdtemp(prefix="ag-nudge-dblreg-miss-")
write_settings_json(plugin_rooted_miss, UNRELATED_HOOKS)
rc, out, err = run_hook("session-nudge.py", {}, plugin_rooted_miss)
check("plugin-rooted + no copy-in registration → no double-registration warning",
      rc == 0 and "registered twice" not in out, f"rc={rc} out={out!r}")

malformed_settings = tempfile.mkdtemp(prefix="ag-nudge-dblreg-malformed-")
os.makedirs(os.path.join(malformed_settings, ".claude"))
with open(os.path.join(malformed_settings, ".claude", "settings.json"), "w") as f:
    f.write("{not valid json")
rc, out, err = run_hook("session-nudge.py", {}, malformed_settings)
check("malformed settings.json → no crash, exit 0", rc == 0, f"rc={rc} err={err!r}")
check("malformed settings.json → no HOOK ERROR", "HOOK ERROR" not in err, err)
check("malformed settings.json → no double-registration warning",
      "registered twice" not in out, out)

# Project-rooted instance: run the COPY of session-nudge.py that lives inside
# proj's own .agent-guild/hooks/, so __file__ is genuinely under root and
# _running_from_plugin_root() is False—the copy-in half of the pair never
# runs this check at all (see the module docstring's asymmetry note).
project_rooted = tempfile.mkdtemp(prefix="ag-nudge-dblreg-projrooted-")
write_settings_json(project_rooted, COPY_IN_GUILD_HOOKS)
copied_script = copy_in_hooks(project_rooted)
rc, out, err = run_hook_path(copied_script, {}, project_rooted)
check("project-rooted + copy-in settings.json → no double-registration warning",
      rc == 0 and "registered twice" not in out, f"rc={rc} out={out!r}")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
