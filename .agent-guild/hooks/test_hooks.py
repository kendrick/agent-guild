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
    count_after_verdict = json.load(f)["count"]
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

# double-registration proof (issue #41): with both the plugin's hooks.json and
# a copy-in settings.json active, the SAME real main-session Stop event fires
# stop-gate.py twice before the orchestrator resolves anything—so one real
# blocked state costs two counts, not one, and STALLED.md fires after two
# real blocks instead of three. Simulate that by invoking the hook twice on
# an unchanged task state and asserting the counter lands on 2, not 1.
proj = fresh_proj()
write_task(proj, "T-001", status="rework", retries=1)
state_file = os.path.join(proj, ".agent-guild", "state", "log", "stop-gate.state")

rc_a, _, _ = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
with open(state_file, encoding="utf-8") as f:
    count_after_one_fire = json.load(f)["count"]
check("stall-counter double-invocation: one fire → count 1",
      count_after_one_fire == 1, f"count={count_after_one_fire}")

rc_b, _, _ = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
with open(state_file, encoding="utf-8") as f:
    count_after_two_fires = json.load(f)["count"]
check("stall-counter double-invocation: same blocked state fired twice → counter advances by two total",
      count_after_two_fires == 2, f"count={count_after_two_fires}")
check("both fires individually blocked the turn (rc==2 each)",
      rc_a == 2 and rc_b == 2, f"{rc_a},{rc_b}")

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

# ------------------------------------------ second_opinion_debts(): the debt gate (#100)
# second_opinion_debts() is what stop-gate.py and dispatch-guard.py both read to
# close the #100 hole: a Claude-host run reached `complete` on 2026-08-02 with a
# completed task and no crossing, and nothing noticed. Every case below drives
# one of the two GATES as a real process against a scratch verdicts/ directory
# built by hand, never the predicate directly, so a regression in how a gate
# USES second_opinion_debts() shows up here too, not only a regression in the
# predicate itself. Where the sole observable is a clean exit, the case pairs
# it with a positive control in the same project—the identical fixture minus
# (or plus) the one thing under test—so a pass can't be "the predicate saw
# nothing," only "correctly discharged" or "correctly still owing."
#
# #141 raised the bar for what counts as "discharged": a lane-suffixed file's
# mere presence used to be enough (#100's actual bug), so any case below that
# claims a discharge now has to earn it through the real dispatch-guard
# reserve + subagent-return promote round trip—never by hand-writing the lane
# file, which is exactly the shape of the incident this job closes off.
print("second_opinion_debts(): the debt gate (#100)")


def authorize_courier_crossing(proj, tid, tier="sonnet", retries=0, lane="codex"):
    """Legitimately authorize a courier crossing for (tid, tier, retries) on
    `lane`, through the real gates—never by hand-writing the lane file, which
    is the #100 shape #141 closes off. Returns the verdict JSON path.

    lane="codex" simulates a Claude-hosted courier: dispatch-guard reserves
    with the default (Claude) lane, the courier writes its own verdict file,
    and subagent-return validates + promotes straight off that file.

    lane="claude" simulates a Codex-hosted courier: dispatch-guard reserves
    with hook_host=codex (so courier_lane resolves to the reciprocal "claude"
    lane), the read-only courier can't write anything itself, so
    subagent-return promotes from its returned AGENT_GUILD_COURIER_OUTCOME
    marker—and this helper then persists the verdict file itself, exactly as
    documented for "the parent" (constraint #2: a design that only works
    when the courier writes the file strands every Codex-lane debt forever).
    """
    seed_verdict_toolchain(proj)  # both branches validate through validate-verdict.py
    stem = f"{tid}-{tier}-r{retries}"
    dispatch_payload = {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": f"Task-ID: {tid}"}}
    if lane == "claude":
        dispatch_payload["hook_host"] = "codex"
    rc, _, err = run_hook("dispatch-guard.py", dispatch_payload, proj)
    assert rc == 0, f"authorize_courier_crossing: reservation dispatch failed rc={rc} err={err}"

    if lane == "codex":
        vpath = write_verdict_json(proj, f"{stem}-codex.json", task_id=tid,
                                    checker="checker-courier", vendor="openai",
                                    model="gpt-5.6-terra", verdict="pass")
        tx = transcript(proj, f"Task-ID: {tid}")
        rc, _, err = run_hook("subagent-return.py",
                              {"agent_type": "checker-courier", "transcript_path": tx}, proj)
        assert rc == 0, f"authorize_courier_crossing: promotion return failed rc={rc} err={err}"
        return vpath

    verdict = {"task_id": tid, "checker": "checker-courier", "vendor": "anthropic",
               "model": "claude-haiku-4-5-20251001", "verdict": "pass", "findings": [],
               "timestamp": "2026-07-22T18:00:00Z", "duration_ms": 1200, "cost_usd": 0.02}
    outcome = {
        "status": "verdict", "verdict": verdict, "attempts": 1, "diagnostic": None,
        "ledger": {"task_id": tid, "vendor": "claude", "model": "claude-haiku-4-5-20251001",
                   "started_at": "2026-07-22T18:00:00Z", "duration_ms": 1200, "exit_code": 0,
                   "tokens_in": 100, "tokens_out": 50, "cost_usd": 0.02, "quota_event": False},
    }
    tx = transcript(proj, f"Task-ID: {tid}")
    rc, _, err = run_hook(
        "subagent-return.py",
        {"agent_type": "checker-courier", "transcript_path": tx, "hook_host": "codex",
         "last_assistant_message": "AGENT_GUILD_COURIER_OUTCOME\n" + json.dumps(outcome)},
        proj,
    )
    assert rc == 0, f"authorize_courier_crossing: codex promotion return failed rc={rc} err={err}"
    return write_verdict_json(proj, f"{stem}-claude.json", **verdict)

# 1. A debt registers even while a task sits at "checking"—and specifically
# swaps the block message from the generic "act on the verdict" line to the
# courier-specific one. Removing the verdict-of-record on the identical
# fixture keeps the task open (still blocks) but drops that specific line,
# which is what pins the wording change to the debt and not to "checking" on
# its own—the plain open-task case already covered above (line ~344) would
# pass this case even with the debt path completely broken.
proj = fresh_proj()
write_task(proj, "T-030", status="checking", retries=0)
verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
write_verdict_json(proj, "T-030-sonnet-r0.json", task_id="T-030")
rc1, out1, err1 = run_hook("stop-gate.py", {}, proj)
os.remove(os.path.join(verdicts_dir, "T-030-sonnet-r0.json"))
rc2, out2, err2 = run_hook("stop-gate.py", {}, proj)
check("so: debt with the task at checking blocks the turn",
      rc1 == 2 and "dispatch checker-courier before completing" in err1
      and "T-030" in err1 and rc2 == 2
      and "dispatch checker-courier before completing" not in err2,
      f"rc1={rc1} err1={err1!r} rc2={rc2} err2={err2!r}")

# 2. The #100 regression itself: a task already moved to `complete` still
# owes, and stop-gate still blocks even though open_tasks() has nothing to
# show for it (complete is terminal). Removing the verdict-of-record on the
# identical fixture (no debt anywhere) flips it to a clean exit, pinning the
# block to the debt alone.
proj = fresh_proj()
write_task(proj, "T-031", status="complete", retries=0)
verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
write_verdict_json(proj, "T-031-sonnet-r0.json", task_id="T-031")
rc1, out1, err1 = run_hook("stop-gate.py", {}, proj)
os.remove(os.path.join(verdicts_dir, "T-031-sonnet-r0.json"))
rc2, out2, err2 = run_hook("stop-gate.py", {}, proj)
check("so: debt with the task at complete blocks the turn",
      rc1 == 2 and "T-031-sonnet-r0-codex.json" in err1 and rc2 == 0,
      f"rc1={rc1} err1={err1!r} rc2={rc2}")

# 3. Discharge route 1: a codex-lane sibling—but #141 raised the bar for what
# counts. Refuse-case: a hand-written sibling, exactly the #100 shape (a
# file with the right name, no dispatch behind it), still owes. Allow-case:
# the identical fixture, minus the forgery, reached through the real
# dispatch-guard reserve + subagent-return promote round trip—the only thing
# that should ever flip this from owing to discharged.
proj = fresh_proj()
write_task(proj, "T-032", status="complete", retries=0)
write_verdict_json(proj, "T-032-sonnet-r0.json", task_id="T-032")
forged = write_verdict_json(proj, "T-032-sonnet-r0-codex.json", task_id="T-032",
                             checker="checker-courier", vendor="openai",
                             model="gpt-5.6-terra")
rc_forged, _, err_forged = run_hook("stop-gate.py", {}, proj)
os.remove(forged)
check("so: an unauthorized codex lane sibling does not discharge the debt (#100)",
      rc_forged == 2 and "T-032-sonnet-r0-codex.json" in err_forged,
      f"rc={rc_forged} err={err_forged!r}")

authorize_courier_crossing(proj, "T-032", lane="codex")
rc_auth, _, err_auth = run_hook("stop-gate.py", {}, proj)
check("so: a codex lane sibling discharges the debt once the gate authorized it (#141)",
      rc_auth == 0, f"rc={rc_auth} err={err_auth!r}")

# 4. Discharge route 2: a claude-lane sibling. Same refuse/allow shape as
# case 3, so a predicate that only recognizes ONE lane's authorization (a
# real way to half-implement route 2) still gets caught.
proj = fresh_proj()
write_task(proj, "T-033", status="complete", retries=0)
write_verdict_json(proj, "T-033-sonnet-r0.json", task_id="T-033")
forged = write_verdict_json(proj, "T-033-sonnet-r0-claude.json", task_id="T-033",
                             checker="checker-courier", vendor="anthropic",
                             model="claude-haiku-4-5-20251001")
rc_forged, _, err_forged = run_hook("stop-gate.py", {}, proj)
os.remove(forged)
check("so: an unauthorized claude lane sibling does not discharge the debt (#100)",
      rc_forged == 2 and "T-033" in err_forged,
      f"rc={rc_forged} err={err_forged!r}")

authorize_courier_crossing(proj, "T-033", lane="claude")
rc_auth, _, err_auth = run_hook("stop-gate.py", {}, proj)
check("so: a claude lane sibling discharges the debt once the gate authorized it (#141)",
      rc_auth == 0, f"rc={rc_auth} err={err_auth!r}")

# 5. Discharge route 3: the courier's own quota sentinel, on this (default,
# Claude-host) lane.
proj = fresh_proj()
write_task(proj, "T-034", status="complete", retries=0)
write_verdict_json(proj, "T-034-sonnet-r0.json", task_id="T-034")
exhausted_dir = os.path.join(proj, ".agent-guild", "state", "exhausted")
os.makedirs(exhausted_dir, exist_ok=True)
sentinel = os.path.join(exhausted_dir, "codex")
open(sentinel, "w").close()
rc1, _, err1 = run_hook("stop-gate.py", {}, proj)
os.remove(sentinel)
rc2, _, err2 = run_hook("stop-gate.py", {}, proj)
check("so: an exhausted lane discharges the debt",
      rc1 == 0 and rc2 == 2, f"rc1={rc1} err1={err1!r} rc2={rc2} err2={err2!r}")

# 6. r0's finding, and the fifteenth case: the sentinel that discharges has to
# be THIS host's lane, not any lane. Driven with hook_host: codex, so the far
# side is claude—exhausted/claude must discharge, and exhausted/codex (the
# WRONG lane for a Codex host) must not. A predicate that ignores `data` and
# hardcodes "codex" passes case 5 above and fails only here, which is why
# case 5 alone can't stand in for this one.
proj = fresh_proj()
write_task(proj, "T-035", status="complete", retries=0)
write_verdict_json(proj, "T-035-sonnet-r0.json", task_id="T-035")
exhausted_dir = os.path.join(proj, ".agent-guild", "state", "exhausted")
os.makedirs(exhausted_dir, exist_ok=True)
claude_sentinel = os.path.join(exhausted_dir, "claude")
codex_sentinel = os.path.join(exhausted_dir, "codex")
open(claude_sentinel, "w").close()
rc_right_lane, _, err_right = run_hook("stop-gate.py", {"hook_host": "codex"}, proj)
os.remove(claude_sentinel)
open(codex_sentinel, "w").close()
rc_wrong_lane, _, err_wrong = run_hook("stop-gate.py", {"hook_host": "codex"}, proj)
os.remove(codex_sentinel)
check("so: the exhausted-lane discharge follows the host lane",
      rc_right_lane == 0 and rc_wrong_lane == 2,
      f"exhausted/claude+hook_host=codex → rc={rc_right_lane} err={err_right!r}; "
      f"exhausted/codex+hook_host=codex → rc={rc_wrong_lane} err={err_wrong!r}")

# 7. Discharge route 4: the orchestrator's own waiver that a host refused the
# dispatch outright.
proj = fresh_proj()
write_task(proj, "T-036", status="complete", retries=0)
verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
write_verdict_json(proj, "T-036-sonnet-r0.json", task_id="T-036")
waiver = os.path.join(verdicts_dir, "T-036-sonnet-r0-codex.denied")
open(waiver, "w").close()
rc1, _, err1 = run_hook("stop-gate.py", {}, proj)
os.remove(waiver)
rc2, _, err2 = run_hook("stop-gate.py", {}, proj)
check("so: a denied waiver discharges the debt",
      rc1 == 0 and rc2 == 2, f"rc1={rc1} err1={err1!r} rc2={rc2} err2={err2!r}")

# 8. Discharge route 5: a `blocked` verdict of record has nothing yet for a
# crossing to compare against, so it owes nothing. Rewriting the SAME file to
# a non-blocked verdict, with nothing else in the fixture changed, is what
# proves the discharge tracks the `verdict` field rather than the fixture
# just being empty.
proj = fresh_proj()
write_task(proj, "T-037", status="complete", retries=0)
write_verdict_json(proj, "T-037-sonnet-r0.json", task_id="T-037", verdict="blocked")
rc1, _, err1 = run_hook("stop-gate.py", {}, proj)
write_verdict_json(proj, "T-037-sonnet-r0.json", task_id="T-037", verdict="pass")
rc2, _, err2 = run_hook("stop-gate.py", {}, proj)
check("so: a blocked verdict of record owes nothing",
      rc1 == 0 and rc2 == 2, f"rc1={rc1} err1={err1!r} rc2={rc2} err2={err2!r}")

# 9. The named trap: `rc == 0` against a project whose only verdict file is an
# auditor stem passes identically whether the predicate correctly skips
# auditor stems, or crashes reading the directory and returns an empty list
# either way. Adding a genuinely owing T-NNN stem alongside it, in the SAME
# project, and confirming THAT flips the exit code (and that the auditor stem
# never shows up as an owing debt itself) is what tells the two apart.
proj = fresh_proj()
verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
with open(os.path.join(verdicts_dir, "CON-audit-r0.json"), "w", encoding="utf-8") as f:
    json.dump({"verdict": "PASS"}, f)
rc1, _, err1 = run_hook("stop-gate.py", {}, proj)
write_task(proj, "T-038", status="complete", retries=0)
write_verdict_json(proj, "T-038-sonnet-r0.json", task_id="T-038")
rc2, _, err2 = run_hook("stop-gate.py", {}, proj)
check("so: an auditor stem owes nothing",
      rc1 == 0 and rc2 == 2 and "T-038-sonnet-r0-codex.json" in err2
      and "CON-audit" not in err2,
      f"rc1={rc1} err1={err1!r} rc2={rc2} err2={err2!r}")

# 10. The debt is tracked per verdict-of-record STEM (task + tier + retry),
# not per task: r0 gets a genuinely AUTHORIZED lane sibling and is discharged,
# r1 has none and still owes, in the same run. A predicate that discharged by
# task_id alone would clear both the moment either retry got a sibling; a
# predicate that only checked file presence (pre-#141) would pass this even
# with a hand-written r1 sibling, so the pairing below with case 3/4 is what
# actually pins "per retry round" to authorization rather than to a filename.
proj = fresh_proj()
write_task(proj, "T-039", status="checking", retries=0)
authorize_courier_crossing(proj, "T-039", retries=0, lane="codex")
write_task(proj, "T-039", status="complete", retries=1)
write_verdict_json(proj, "T-039-sonnet-r0.json", task_id="T-039")
write_verdict_json(proj, "T-039-sonnet-r1.json", task_id="T-039")
rc, _, err = run_hook("stop-gate.py", {}, proj)
check("so: the debt is per retry round, and only an authorized round discharges",
      rc == 2 and "T-039-sonnet-r1-codex.json" in err
      and "T-039-sonnet-r0-codex.json" not in err,
      f"rc={rc} err={err!r}")

# 11. A verdict of record that can't be parsed owes rather than crashing the
# gate—loud, not silent, per _lib.py's own top-of-file contract. Asserting the
# absence of the HOOK ERROR banner alongside the exit code is what rules out
# an uncaught exception landing in run()'s own fail-loud handler, which also
# exits 2, so this can't be satisfied by a crash instead of a clean debt.
proj = fresh_proj()
write_task(proj, "T-040", status="complete", retries=0)
verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
with open(os.path.join(verdicts_dir, "T-040-sonnet-r0.json"), "w", encoding="utf-8") as f:
    f.write("{not json")
rc, _, err = run_hook("stop-gate.py", {}, proj)
check("so: an unreadable verdict of record owes a debt",
      rc == 2 and "HOOK ERROR" not in err and "T-040" in err,
      f"rc={rc} err={err!r}")

# 12. PAUSED stands every gate down, the debt gate included—checked before any
# of this logic runs. Clearing PAUSED on the identical fixture flips it
# straight back to blocked, pinning the pass to PAUSED rather than to some
# accidental absence of debt.
proj = fresh_proj()
write_task(proj, "T-041", status="complete", retries=0)
write_verdict_json(proj, "T-041-sonnet-r0.json", task_id="T-041")
paused_file = os.path.join(proj, ".agent-guild", "state", "PAUSED")
open(paused_file, "w").close()
rc1, _, err1 = run_hook("stop-gate.py", {}, proj)
os.remove(paused_file)
rc2, _, err2 = run_hook("stop-gate.py", {}, proj)
check("so: PAUSED stands the debt gate down",
      rc1 == 0 and rc2 == 2, f"rc1={rc1} err1={err1!r} rc2={rc2} err2={err2!r}")

# 13. C-4's widening: checker-courier may run against a `complete` task whose
# debt is still outstanding, so the stop gate's demand is actually
# collectible. Clearing the debt (no verdict record at all) on the identical
# fixture then refuses it on status, so the pass above can't be "courier
# always runs on a complete task."
proj = fresh_proj()
write_task(proj, "T-042", status="complete", retries=0)
verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
write_verdict_json(proj, "T-042-sonnet-r0.json", task_id="T-042")
rc1, _, err1 = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": "Task-ID: T-042"}}, proj)
os.remove(os.path.join(verdicts_dir, "T-042-sonnet-r0.json"))
rc2, _, err2 = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": "Task-ID: T-042"}}, proj)
check("so: courier dispatch allowed on a complete task with a debt",
      rc1 == 0 and rc2 == 2 and "not 'checking'" in err2,
      f"rc1={rc1} err1={err1!r} rc2={rc2} err2={err2!r}")

# 14. The widening is debt-gated, not status-gated: a `complete` task whose
# debt is already discharged still refuses a courier on status, the same as
# any other non-checking task. Refuse-case: the debt is discharged for real
# (authorized via the same round trip as case 3), so the courier dispatch is
# refused on status alone. Allow-case, differing in exactly the one thing
# under test (authorization, not the file's presence): the identical fixture
# with an unauthorized sibling still owes, so the widening still lets the
# courier through—proving the refusal above tracks discharge, not a filename.
proj = fresh_proj()
write_task(proj, "T-043", status="checking", retries=0)
authorize_courier_crossing(proj, "T-043", lane="codex")
write_task(proj, "T-043", status="complete", retries=0)
write_verdict_json(proj, "T-043-sonnet-r0.json", task_id="T-043")
rc1, _, err1 = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": "Task-ID: T-043"}}, proj)
check("so: courier dispatch still refused on a complete task with no debt (#141: authorized, not merely present)",
      rc1 == 2 and "not 'checking'" in err1, f"rc1={rc1} err1={err1!r}")

proj_unauth = fresh_proj()
write_task(proj_unauth, "T-047", status="complete", retries=0)
write_verdict_json(proj_unauth, "T-047-sonnet-r0.json", task_id="T-047")
write_verdict_json(proj_unauth, "T-047-sonnet-r0-codex.json", task_id="T-047",
                    checker="checker-courier", vendor="openai", model="gpt-5.6-terra")
rc2, _, err2 = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "checker-courier",
                                        "prompt": "Task-ID: T-047"}}, proj_unauth)
check("so: an unauthorized sibling still owes, so the widening still allows the courier dispatch",
      rc2 == 0, f"rc2={rc2} err2={err2!r}")

# 15. The debt only relaxes the status check for checker-courier itself. An
# in-family checker (checker-judgment here) still needs `checking` even on a
# task carrying an outstanding debt—otherwise the checker of record could
# re-run against a task nobody reopened.
proj = fresh_proj()
write_task(proj, "T-044", status="complete", retries=0)
write_verdict_json(proj, "T-044-sonnet-r0.json", task_id="T-044")
rc, _, err = run_hook("dispatch-guard.py",
                      {"tool_input": {"subagent_type": "checker-judgment",
                                      "prompt": "Task-ID: T-044"}}, proj)
check("so: an in-family checker is still refused on a complete task",
      rc == 2 and "not 'checking'" in err, f"rc={rc} err={err!r}")

# Beyond the fifteen: every courier fixture above this task (and every one
# already in the suite before it, at test_hooks.py:828-864) runs against a
# debt-FREE task, so nothing covers the courier's own remaining conditions on
# the debt-bearing path. Without these two, a dispatch guard that returns 0
# early on any debt-bearing courier—ahead of the model and workspace checks
# below—would pass every case above while making the read-only boundary a
# dead letter for every real courier dispatch.
proj = fresh_proj()
write_task(proj, "T-045", status="complete", retries=0)
write_verdict_json(proj, "T-045-sonnet-r0.json", task_id="T-045")
rc, _, err = run_hook("dispatch-guard.py",
                      {"tool_input": {"subagent_type": "checker-courier",
                                      "prompt": "Task-ID: T-045", "model": "opus"}}, proj)
check("so: a debt-bearing courier dispatch is still refused for a model override",
      rc == 2 and "Drop the override" in err, f"rc={rc} err={err!r}")

proj = fresh_proj()
write_task(proj, "T-046", status="complete", retries=0)
write_verdict_json(proj, "T-046-sonnet-r0.json", task_id="T-046")
rc, _, err = run_hook(
    "dispatch-guard.py",
    {"tool_input": {"subagent_type": "checker-courier",
                     "prompt": "Task-ID: T-046\nRun it with workspace-write access."}},
    proj)
check("so: a debt-bearing courier dispatch is still refused for workspace-write",
      rc == 2 and "read-only" in err, f"rc={rc} err={err!r}")

# 18. C-1's anti-laundering requirement: a forged sibling that PREDATES any
# dispatch for its stem stays unauthorized even once a real courier for that
# exact round is legitimately dispatched and returns—reserve_crossing()
# refuses to record authorization for a stem something already occupies, so
# the forged content can never be laundered by the next legitimate crossing.
# Both the dispatch and the return report success (nothing about THEM is
# illegal), and the debt still stands—the discharge is what's refused, not
# the subagent's own protocol.
proj = fresh_proj()
seed_verdict_toolchain(proj)
write_task(proj, "T-050", status="checking", retries=0)
write_verdict_json(proj, "T-050-sonnet-r0.json", task_id="T-050")
write_verdict_json(proj, "T-050-sonnet-r0-codex.json", task_id="T-050",
                    checker="checker-courier", vendor="openai", model="gpt-5.6-terra")
rc_dispatch, _, err_dispatch = run_hook(
    "dispatch-guard.py",
    {"tool_input": {"subagent_type": "checker-courier", "prompt": "Task-ID: T-050"}}, proj)
tx = transcript(proj, "Task-ID: T-050")
rc_return, _, err_return = run_hook(
    "subagent-return.py", {"agent_type": "checker-courier", "transcript_path": tx}, proj)
write_task(proj, "T-050", status="complete", retries=0)
rc_stop, _, err_stop = run_hook("stop-gate.py", {}, proj)
check("so: a forged file that predates its dispatch is never laundered into authorization (#141)",
      rc_dispatch == 0 and rc_return == 0 and rc_stop == 2 and "T-050" in err_stop,
      f"rc_dispatch={rc_dispatch} err_dispatch={err_dispatch!r} rc_return={rc_return} "
      f"err_return={err_return!r} rc_stop={rc_stop} err_stop={err_stop!r}")

# 19. C-2, the #100 incident verbatim: a courier dispatched for T-051 also
# wrote a sibling's (T-052) verdict, and T-052 was never itself dispatched.
# Refuse-case: the write is surfaced (a row under state/log/, naming both
# Task-IDs) and T-052's own debt stays owed regardless. Allow-case, differing
# in exactly the one thing under test: the identical fixture except T-053 (in
# place of T-052) WAS legitimately dispatched—its own reservation exists,
# courier still in flight—the exact concurrency shape C-2 requires not be
# mistaken for the incident. A time-window predicate would fire on this case;
# reservation-based discharge does not.
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

write_task(proj, "T-052", status="complete", retries=0)
rc_stop, _, err_stop = run_hook("stop-gate.py", {}, proj)
check("so: the foreign write still does not discharge the OTHER task's own debt",
      rc_stop == 2 and "T-052" in err_stop, f"rc_stop={rc_stop} err_stop={err_stop!r}")

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
check("so: a concurrent agent's OWN reserved crossing is never surfaced as foreign (C-2)",
      rc_return2 == 0 and "T-054" not in log_text2, f"rc={rc_return2} log={log_text2!r}")

# 20. C-5's two authorization-shaped malformed inputs: a missing authorization
# record, and a truncated/non-JSON one. Neither may crash the gate—loud, not
# silent, same contract case 11 already pins for a malformed verdict of
# record—and both read as unauthorized (still owing), never as a free pass.
proj = fresh_proj()
write_task(proj, "T-055", status="complete", retries=0)
write_verdict_json(proj, "T-055-sonnet-r0.json", task_id="T-055")
write_verdict_json(proj, "T-055-sonnet-r0-codex.json", task_id="T-055",
                    checker="checker-courier", vendor="openai", model="gpt-5.6-terra")
rc_missing, _, err_missing = run_hook("stop-gate.py", {}, proj)
check("so: a missing authorization record owes rather than crashing",
      rc_missing == 2 and "HOOK ERROR" not in err_missing and "T-055" in err_missing,
      f"rc={rc_missing} err={err_missing!r}")

verdicts_dir = os.path.join(proj, ".agent-guild", "state", "verdicts")
with open(os.path.join(verdicts_dir, "T-055-sonnet-r0-codex.authorized"), "w",
          encoding="utf-8") as f:
    f.write("{not json")
rc_truncated, _, err_truncated = run_hook("stop-gate.py", {}, proj)
check("so: a truncated/non-JSON authorization record owes rather than crashing",
      rc_truncated == 2 and "HOOK ERROR" not in err_truncated and "T-055" in err_truncated,
      f"rc={rc_truncated} err={err_truncated!r}")

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
