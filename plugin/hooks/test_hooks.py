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


def run_hook_path(script_path, payload, proj):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=proj)
    p = subprocess.run(
        [sys.executable, script_path],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return p.returncode, p.stdout, p.stderr


def run_hook(name, payload, proj):
    return run_hook_path(os.path.join(HOOKS, name), payload, proj)


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
