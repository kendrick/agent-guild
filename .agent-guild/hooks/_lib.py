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
    # checker-courier's own brain is host-configured; "codex" here is the
    # Claude host's default LANE, not a model. Codex adapters select the
    # reciprocal "claude" lane through courier_lane(data). Dispatches carry
    # no model override; read this value as lane/logging plumbing.
    "checker-courier": "codex",
}
GUILD_AGENTS = set(DEFAULT_MODEL)
WORKER_AGENTS = {"worker-bulk", "worker-standard", "worker-craft"}
CHECKER_AGENTS = {"checker-deterministic", "checker-judgment", "checker-courier"}


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

# Issue #71: Codex encrypts a dispatch's `message` before any hook sees it, so
# the labelled forms above have nothing to match against on that host. The id
# instead rides in `task_name`, which the dispatcher sets and which stays clear
# through both the dispatch payload and the transcript. A bare field value has
# no label to key on, so these sort it by shape.
# Codex validates task_name as an agent name: `agent_name must use only
# lowercase letters, digits, and underscores`. So `T-001` cannot be sent
# verbatim, and the underscore spelling `t_001` is the wire form. Accept either
# separator in either case and hand back the canonical id, because everything
# downstream—task filenames, verdict stems, the dispatch log—is `T-001`.
# Codex also treats task_name as a UNIQUE agent name within a session tree and
# rejects one already in use. A task needs at least two agents and usually three
# under the dual-check regime, so one name per task collides on the second
# dispatch—and when it did, the model routed around the collision through
# `followup_task`, which no gate covered (#77). The wire form therefore carries
# a discriminator after the id (`t_001_r0_worker`), and everything past the
# number is stripped back off here. Free-form rather than a fixed role
# vocabulary on purpose: `t_001_checker` getting blocked is what pushed the
# model off `spawn_agent` in the first place, and a re-dispatch that repeats
# both the role and the retry count still needs room to name itself.
_DISCRIMINATOR = r"(?:_[a-z0-9_]+)?"
_BARE_TASK_RE = re.compile(rf"^T[-_](\d+){_DISCRIMINATOR}$", re.IGNORECASE)
_BARE_AUDIT_RE = re.compile(
    rf"^(CON|DEC)[-_]audit{_DISCRIMINATOR}$", re.IGNORECASE
)
_BARE_AUDITION_RE = re.compile(rf"^A[-_](\d+){_DISCRIMINATOR}$", re.IGNORECASE)


def bare_id(value):
    """Sort a bare dispatch id into ``(kind, id)``—kind being 'task', 'audit',
    or 'audition', and id always in canonical form. Returns ``(None, None)``
    for a value in no known namespace, which is the common case: `task_name`
    is a free-text field and most of what arrives there is a dispatcher's own
    label, not a guild id."""
    if not isinstance(value, str):
        return None, None
    value = value.strip()
    match = _BARE_TASK_RE.match(value)
    if match:
        return "task", f"T-{match.group(1)}"
    match = _BARE_AUDIT_RE.match(value)
    if match:
        return "audit", f"{match.group(1).upper()}-audit"
    match = _BARE_AUDITION_RE.match(value)
    if match:
        return "audition", f"A-{match.group(1)}"
    return None, None


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


def lane_exhausted(lane):
    """True if a courier lane's quota sentinel is set (state/exhausted/<lane>,
    the per-lane directory form, adopted now so a future second lane needs no
    migration). Must never raise, same contract as paused(): the sentinel is
    user-managed state on disk, and a permissions or filesystem oddity while
    reading it should count as an absent sentinel rather than crash the
    gate."""
    try:
        return os.path.exists(state_path("exhausted", lane))
    except Exception:
        return False


def courier_lane(data=None):
    """Return the far-side lane for this host.

    Claude-hosted jobs use the long-standing Codex lane. The Codex lifecycle
    adapter stamps `hook_host: codex`, selecting the reciprocal Claude lane
    without forking any gate policy or changing Claude's existing default.
    """
    if isinstance(data, dict) and data.get("hook_host") == "codex":
        return "claude"
    return DEFAULT_MODEL["checker-courier"]


def read_input():
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def in_subagent(data):
    """True if this hook fired for a tool call INSIDE a subagent rather than the
    main session. Supported Claude Code and Codex hook payloads stamp an
    `agent_id` on subagent input and leave it off main-session input, so a gate
    meant to constrain only the orchestrator no-ops when it's present.
    Load-bearing: tool hooks fire inside subagents, so without this the
    write-guard blocks workers from writing the deliverables they were
    dispatched to produce."""
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
_DISPATCH_TOOLS = {"Task", "Agent", "spawn_agent"}


def _id_in(text):
    """First Task-ID / Audit-ID / Audition-ID in a blob of text, or None."""
    if not isinstance(text, str):
        return None
    m = (TASK_ID_RE.search(text) or AUDIT_ID_RE.search(text)
         or AUDITION_ID_RE.search(text))
    return m.group(1) if m else None


def id_from_transcript(transcript_path):
    """Extract the Task-ID / Audit-ID / Audition-ID a subagent was dispatched
    with. FRAGILE: both Claude Code and Codex document their transcript JSONL
    as unstable. Any failure to find an id raises, and the caller turns that
    into a loud, non-hanging return warning.

    Claude's SubagentStop supplies the parent transcript, where the id lives in
    the last assistant Task/Agent tool_use input. Codex supplies the child
    transcript explicitly, where the opening prompt is currently a
    response_item message or event_msg user_message. We scan both records, plus
    Codex function_call dispatches, so this parser remains one shared
    compatibility boundary rather than a host-specific policy fork.
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
        records = [obj]
        payload = obj.get("payload")
        if isinstance(payload, dict):
            records.append(payload)

        for record in records:
            msg = record.get("message", record)
            content = msg.get("content") if isinstance(msg, dict) else None

            if isinstance(content, list):
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and block.get("name") in _DISPATCH_TOOLS
                    ):
                        got = _id_in(
                            _dispatch_prompt(block.get("input") or {})
                        )
                        if got:
                            tool_ids.append(got)

            if (
                record.get("type") == "function_call"
                and record.get("name") in _DISPATCH_TOOLS
            ):
                arguments = record.get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                got = _id_in(_dispatch_prompt(arguments))
                if not got:
                    # The prompt scan above finds nothing on a Codex host,
                    # where `message` is encrypted here exactly as it is in
                    # the dispatch payload. `task_name` is clear at both ends,
                    # which is why the id rides there (#71). Observed against a
                    # live return once the full lifecycle ran on Codex; the
                    # earlier note here that SubagentStop never fires was wrong
                    # (#68).
                    got = bare_id(arguments.get("task_name"))[1]
                if got:
                    tool_ids.append(got)

            role = msg.get("role") if isinstance(msg, dict) else None
            role = role or record.get("role") or record.get("type")
            if role in {"user", "user_message"}:
                user_text = (
                    record.get("message")
                    if record.get("type") == "user_message"
                    else content
                )
                got = _id_in(_text_of(user_text))
                if got:
                    user_ids.append(got)

    if tool_ids:
        return tool_ids[-1]
    if user_ids:
        return user_ids[-1]
    raise ValueError(
        f"no Task-ID/Audit-ID/Audition-ID found in any agent dispatch or "
        f"user message of {transcript_path}"
    )


def _dispatch_prompt(tool_input):
    if not isinstance(tool_input, dict):
        return ""
    parts = []
    for key in ("prompt", "message", "items"):
        if key in tool_input:
            text = _text_of(tool_input[key])
            if text:
                parts.append(text)
    return "\n".join(parts)


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict):
                text = _text_of(b)
                if text:
                    parts.append(text)
        return "\n".join(parts)
    if isinstance(content, dict):
        parts = []
        for key in ("text", "input_text", "message", "content"):
            if key in content:
                text = _text_of(content[key])
                if text:
                    parts.append(text)
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
