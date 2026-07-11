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


def run_hook(name, payload, proj):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=proj)
    p = subprocess.run(
        [sys.executable, os.path.join(HOOKS, name)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return p.returncode, p.stdout, p.stderr


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
        os.makedirs(os.path.join(d, "state", sub))
    return d


def write_task(proj, tid, **fields):
    defaults = dict(status="pending", executor="worker-standard",
                    executor_model="sonnet", checker="checker-deterministic",
                    retries=0, max_retries=2, artifacts="[]")
    defaults.update(fields)
    arts = defaults.pop("artifacts")
    fm = [f"{k}: {v}" for k, v in defaults.items()]
    body = "---\n" + f"id: {tid}\n" + "\n".join(fm) + f"\nartifacts: {arts}\n---\n"
    with open(os.path.join(proj, "state", "tasks", f"{tid}.md"), "w") as f:
        f.write(body)


def write_verdict(proj, name, verdict="PASS", diagnosis=False):
    body = f"---\ntask: T\ntier: sonnet\nretry: 0\nchecker: checker-deterministic\nverdict: {verdict}\n---\n\n## Per-clause results\n\n"
    if diagnosis:
        body += "## Diagnosis\n\n- file: x.html:1\n  clause: C-1\n"
    else:
        body += "## Diagnosis\n\n<!-- placeholder only -->\n"
    with open(os.path.join(proj, "state", "verdicts", name), "w") as f:
        f.write(body)


def con_pass(proj):
    write_verdict(proj, "CON-audit-r0.md", "PASS")


def transcript(proj, text, role="user", content_list=False):
    path = os.path.join(proj, "state", "log", "tx.jsonl")
    if content_list:
        content = [{"type": "text", "text": text}]
    else:
        content = text
    line = json.dumps({"type": role, "message": {"role": role, "content": content}})
    with open(path, "w") as f:
        f.write('{"type":"system","message":{"role":"system","content":"boot"}}\n')
        f.write(line + "\n")
    return path


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
open(os.path.join(proj, "state", "PAUSED"), "w").close()
rc, out, err = run_hook("stop-gate.py", {"stop_hook_active": False}, proj)
check("PAUSED + open task → exit 0", rc == 0, f"rc={rc}")
os.remove(os.path.join(proj, "state", "PAUSED"))

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
stalled = os.path.exists(os.path.join(proj, "state", "STALLED.md"))
check("livelock strikes 1,2 block", rc1 == 2 and rc2 == 2, f"{rc1},{rc2}")
check("livelock strike 3 → exit 0", rc3 == 0, f"rc={rc3}")
check("livelock strike 3 → STALLED.md written", stalled)

# malformed task file → treated as open (fail closed)
proj = fresh_proj()
with open(os.path.join(proj, "state", "tasks", "T-009.md"), "w") as f:
    f.write("this file has no frontmatter at all\n")
rc, out, err = run_hook("stop-gate.py", {}, proj)
check("malformed task → exit 2 (fail closed)", rc == 2, f"rc={rc}")

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
logged = os.path.exists(os.path.join(proj, "state", "log", "dispatches.log"))
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
audlog = os.path.exists(os.path.join(proj_aud, "state", "log", "dispatches.log"))
check("audition dispatch (Audition-ID, no Task-ID) → exit 0", rc == 0, f"rc={rc} err={err}")
check("audition dispatch → logged", audlog)

# regression: the audition path must not swallow a genuinely untagged dispatch.
rc, out, err = run_hook("dispatch-guard.py",
                        {"tool_input": {"subagent_type": "worker-bulk", "prompt": "just sort the lines"}}, proj_aud)
check("no Task-ID and no Audition-ID → exit 2", rc == 2 and "no id line" in err, err)

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

# checker paths
write_task(proj, "T-002", status="checking", executor_model="sonnet", retries=0)
write_verdict(proj, "T-002-sonnet-r0.md", "PASS")
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker wrote PASS verdict → exit 0", rc == 0, f"rc={rc} err={err}")

os.remove(os.path.join(proj, "state", "verdicts", "T-002-sonnet-r0.md"))
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker, no verdict file → exit 2", rc == 2 and "isn't done" in err, err)

write_verdict(proj, "T-002-sonnet-r0.md", "FAIL", diagnosis=False)
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker FAIL w/o diagnosis → exit 2", rc == 2 and "Diagnosis" in err, err)

write_verdict(proj, "T-002-sonnet-r0.md", "FAIL", diagnosis=True)
tx = transcript(proj, "Task-ID: T-002")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "checker-deterministic", "transcript_path": tx}, proj)
check("checker FAIL w/ diagnosis → exit 0", rc == 0, f"rc={rc} err={err}")

# fail-closed: transcript has no id
tx = transcript(proj, "I did the work but never mention the id")
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": tx}, proj)
check("no id in transcript → exit 2 loud (HOOK ERROR)", rc == 2 and "HOOK ERROR" in err, err)

# fail-closed: transcript path unreadable
rc, out, err = run_hook("subagent-return.py",
                        {"agent_type": "worker-standard", "transcript_path": "/no/such/file.jsonl"}, proj)
check("missing transcript → exit 2 loud", rc == 2 and "HOOK ERROR" in err, err)

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

# --------------------------------------------------- orchestrator-write-guard
print("orchestrator-write-guard.py")
proj = fresh_proj()
rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, "README.md")}}, proj)
check("no job → any write allowed (exit 0)", rc == 0, f"rc={rc}")

write_task(proj, "T-001", status="assigned")
rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, "state", "spec.md")}}, proj)
check("job active, write under state/ → exit 0", rc == 0, f"rc={rc} err={err}")

rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, "README.md")}}, proj)
check("job active, write outside state/ → exit 2", rc == 2 and "orchestrator contract" in err.lower(), err)

open(os.path.join(proj, "state", "PAUSED"), "w").close()
rc, out, err = run_hook("orchestrator-write-guard.py",
                        {"tool_input": {"file_path": os.path.join(proj, "README.md")}}, proj)
check("PAUSED lifts write-guard → exit 0", rc == 0, f"rc={rc}")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
