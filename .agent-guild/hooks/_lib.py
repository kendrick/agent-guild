"""Shared helpers for the agent-guild hooks.

Design rules every hook here obeys:

  Fail loud, fail closed. Any unexpected error exits 2 (block) with a HOOK
  ERROR banner, never a silent exit 0. A gate that can't run is a gate that
  blocks—the alternative is verification silently disappearing, which is the
  one failure this kit exists to prevent.

  No-job gate. With no open task, every hook exits 0 immediately, so plain Q&A
  sessions and work on the kit itself run without friction.

  Escape hatch. If .agent-guild/state/PAUSED exists, every hook exits 0—checked before any
  logic that could throw, so a genuinely broken hook is still escapable.

Stdlib only: this runs wherever python3 does, with no install step, so the kit
stays copy-in portable.
"""
import json
import os
import re
import sys

TERMINAL = {"complete", "abandoned"}

# Each guild agent's default model, so dispatch-guard can compute the effective
# model of a dispatch (override if present, else this) and match it to the
# task's current tier. Escalation bumps the model via override, not the agent.
DEFAULT_MODEL = {
    "worker-bulk": "haiku",
    "worker-standard": "sonnet",
    "worker-craft": "opus",
    "checker-deterministic": "haiku",
    "checker-judgment": "opus",
    "auditor": "opus",
}
GUILD_AGENTS = set(DEFAULT_MODEL)
WORKER_AGENTS = {"worker-bulk", "worker-standard", "worker-craft"}
CHECKER_AGENTS = {"checker-deterministic", "checker-judgment"}


def bare_agent(subagent_type):
    """Normalize a dispatched subagent_type to the bare name GUILD_AGENTS and
    DEFAULT_MODEL key on. Once the kit ships inside a Claude Code plugin,
    subagent_type arrives namespaced (`agent-guild:worker-standard`,
    `agent-guild:auditor`, ...); a bare-name membership test against that raw
    string misses, and dispatch-guard's `agent not in GUILD_AGENTS` check waves
    every guild dispatch through ungated—no Task-ID requirement, no CON-audit
    precondition, no tier match. Taking the suffix after the LAST colon keeps
    this rename-robust: any future `<ns>:` prefix normalizes the same way with
    no update here, and a bare name (no colon) passes through unchanged."""
    return subagent_type.rsplit(":", 1)[-1]


TASK_ID_RE = re.compile(r"\bTask-ID:\s*(T-\d+)", re.IGNORECASE)
AUDIT_ID_RE = re.compile(r"\bAudit-ID:\s*(CON-audit|DEC-audit)", re.IGNORECASE)
# Auditions run outside the task lifecycle—no task file, no tier, no verdict
# gate—so they carry their own id namespace that the gates log and wave through.
AUDITION_ID_RE = re.compile(r"\bAudition-ID:\s*(A-\d+)", re.IGNORECASE)


def project_dir():
    d = os.environ.get("CLAUDE_PROJECT_DIR")
    if d and os.path.isdir(d):
        return d
    # _lib.py lives in .agent-guild/hooks/, so the repo root is two dirs up—
    # true while the kit is copied straight into a repo, but false the moment
    # this file ships inside a Claude Code plugin: two-up from the plugin's
    # hooks/ lands beside the plugin, not in the user's project. Fail loud
    # (per the module's own top-of-file rule) rather than let state silently
    # land in the wrong tree.
    candidate = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if os.path.isdir(os.path.join(candidate, ".agent-guild")):
        return candidate
    raise RuntimeError(
        f"project_dir(): CLAUDE_PROJECT_DIR is unset/invalid and the "
        f"two-dirs-up fallback candidate {candidate!r} has no .agent-guild/ "
        f"directory. This is likely _lib.py running from inside a plugin "
        f"install, where two-up is the plugin's parent, not the user's "
        f"project—set CLAUDE_PROJECT_DIR instead of trusting the guess."
    )


def state_path(*parts):
    # The whole runtime bus lives under .agent-guild/ so a copied-in kit leaves
    # the user's repo root uncluttered. project_dir() is still the repo root.
    return os.path.join(project_dir(), ".agent-guild", "state", *parts)


def paused():
    """True if the user has parked the gates. Must never raise."""
    try:
        return os.path.exists(state_path("PAUSED"))
    except Exception:
        return False


def read_input():
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def in_subagent(data):
    """True if this hook fired for a tool call INSIDE a subagent rather than the
    main session. Claude Code stamps an `agent_id` on subagent hook input and
    leaves it off main-session input, so a gate meant to constrain only the
    orchestrator no-ops when it's present. Load-bearing: PreToolUse DOES fire
    inside subagents on CC 2.1.x (an earlier assumption that it didn't was
    wrong), so without this the write-guard blocks workers from writing the very
    deliverables they were dispatched to produce."""
    return bool(data.get("agent_id"))


# --- tiny frontmatter parser (no pyyaml dependency) -----------------------

def _coerce(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip("'\"") for x in inner.split(",")]
    return v.strip("'\"")


def parse_frontmatter(text):
    """Parse the leading --- ... --- block. Handles scalars, inline [a,b]
    lists, and block '- item' lists. Good enough for our task/verdict files;
    deliberately not a full YAML engine."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    i = 1
    key = None  # the key a following '- item' line would extend; None disables it
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            break
        # Continuation of a block list, e.g. the items under `artifacts:`.
        m = re.match(r"^\s+-\s+(.*)$", line)
        if m and key is not None:
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(_coerce(m.group(1)))
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            if val in (">-", ">", "|"):
                # Folded/literal block scalar. We don't need its body, and its
                # indented lines must not be mistaken for list items.
                fm[key] = ""
                key = None
            elif val == "":
                fm[key] = ""  # tentative; a following '- item' upgrades to list
            else:
                fm[key] = _coerce(val)
                key = None  # scalar or inline list is complete
        i += 1
    return fm


def task_file(tid):
    return state_path("tasks", f"{tid}.md")


def read_task(tid):
    """Return the task's frontmatter dict, or None if the file is absent."""
    path = task_file(tid)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())


def open_tasks():
    """List of (id, status, retries) for every non-terminal task. Empty when
    no job is active."""
    tdir = state_path("tasks")
    if not os.path.isdir(tdir):
        return []
    out = []
    for name in sorted(os.listdir(tdir)):
        if not re.match(r"^T-\d+\.md$", name):
            continue
        with open(os.path.join(tdir, name), encoding="utf-8") as f:
            fm = parse_frontmatter(f.read())
        # A T-*.md we can't read a status from is a problem, not a non-task:
        # surface it as open ("malformed") so the gate blocks loudly rather
        # than letting an unreadable task slip through as done.
        status = str(fm.get("status", "")).strip() or "malformed"
        if status not in TERMINAL:
            try:
                retries = int(str(fm.get("retries", "0")).strip() or "0")
            except ValueError:
                retries = 0
            out.append((str(fm.get("id", name[:-3])), status, retries))
    return out


def no_job_active():
    return len(open_tasks()) == 0


def con_audit_passed():
    """True once any CON-audit verdict records PASS. dispatch-guard blocks all
    worker dispatches until then, so the orchestrator's own constitution is
    verified before any worker builds against it."""
    vdir = state_path("verdicts")
    if not os.path.isdir(vdir):
        return False
    for name in os.listdir(vdir):
        if name.startswith("CON-audit-") and name.endswith(".md"):
            with open(os.path.join(vdir, name), encoding="utf-8") as f:
                fm = parse_frontmatter(f.read())
            if str(fm.get("verdict", "")).strip().upper() == "PASS":
                return True
    return False


# Claude Code records a subagent dispatch as an assistant tool_use block for one
# of these tool names; the id we need rides in that block's `input.prompt`.
_DISPATCH_TOOLS = {"Task", "Agent"}


def _id_in(text):
    """First Task-ID / Audit-ID / Audition-ID in a blob of text, or None."""
    if not isinstance(text, str):
        return None
    m = (TASK_ID_RE.search(text) or AUDIT_ID_RE.search(text)
         or AUDITION_ID_RE.search(text))
    return m.group(1) if m else None


def id_from_transcript(transcript_path):
    """Extract the Task-ID / Audit-ID / Audition-ID a subagent was dispatched
    with. FRAGILE: depends on Claude Code's transcript JSONL shape, which is not
    a stable public contract. Any failure to find an id raises, and the caller
    turns that into a loud fail-closed block.

    Where the id actually lives: SubagentStop hands us the PARENT session
    transcript (verified on CC 2.1.x—there is no separate subagent transcript
    carrying the dispatch prompt as a user turn). So the authoritative record is
    the orchestrator's assistant tool_use(Task|Agent) call, whose `input.prompt`
    holds the `Task-ID: T-NNN` line—NOT a role:user message. Under the guild's
    serial dispatch (one subagent dispatched and awaited at a time) the LAST such
    dispatch is the one that just finished. We still scan role:user text as a
    fallback, so a CC version that records the prompt as the subagent's own
    opening turn keeps working. The fixture tests pin both shapes; update them
    here if CC changes the format again.
    """
    with open(transcript_path, encoding="utf-8") as f:
        raw_lines = f.readlines()

    tool_ids = []  # from assistant Task/Agent dispatches, in document order
    user_ids = []  # from role:user message text, in document order
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message", obj)
        content = msg.get("content") if isinstance(msg, dict) else None

        if isinstance(content, list):
            for b in content:
                if (isinstance(b, dict) and b.get("type") == "tool_use"
                        and b.get("name") in _DISPATCH_TOOLS):
                    got = _id_in((b.get("input") or {}).get("prompt", ""))
                    if got:
                        tool_ids.append(got)

        role = msg.get("role") if isinstance(msg, dict) else None
        role = role or obj.get("role") or obj.get("type")
        if role == "user":
            got = _id_in(_text_of(content))
            if got:
                user_ids.append(got)

    if tool_ids:
        return tool_ids[-1]
    if user_ids:
        return user_ids[-1]
    raise ValueError(
        f"no Task-ID/Audit-ID/Audition-ID found in any Task/Agent dispatch or "
        f"user message of {transcript_path}"
    )


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict) and isinstance(b.get("text"), str):
                parts.append(b["text"])
        return "\n".join(parts)
    return ""


def block(msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    return 2


def run(name, fn):
    """Wrap a hook's main function with the fail-loud, PAUSED-first contract.
    fn receives the parsed hook input and returns an exit code (or None = 0)."""
    if paused():
        sys.exit(0)
    try:
        data = read_input()
        rc = fn(data)
        sys.exit(0 if rc is None else int(rc))
    except SystemExit:
        raise
    except BaseException:
        import traceback
        sys.stderr.write(
            f"HOOK ERROR in {name}: {traceback.format_exc()}\n"
            "The verification gate did NOT run. Fix .agent-guild/hooks/ before proceeding "
            "(or `touch .agent-guild/state/PAUSED` to override deliberately).\n"
        )
        sys.exit(2)
