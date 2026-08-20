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

  Jurisdiction. Init owns writing the tracked marker .agent-guild/CLAUDE.md;
  a gate that finds none exits 0 before touching disk. A bare .agent-guild/
  is not evidence of that—init also adds state/ to .gitignore, so `git rm`
  of every tracked payload file leaves the state tree standing with no
  marker in it. A user-scope plugin install fires these hooks in every repo
  on the machine, not just the ones that ran init, so a gate that writes
  state before checking jurisdiction manufactures state in repos that never
  asked for it, or that asked and then said no.

Stdlib only: this runs wherever python3 does, with no install step, so the kit
stays copy-in portable.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

TERMINAL = {"complete", "abandoned"}

# The two courier lanes a verdict of record can be seconded on. One home for
# this pair: scripts/classify-crossings.py:122 still spells "codex"/"claude"
# inline (out of scope for this change), but nothing new should.
COURIER_LANES = ("codex", "claude")

# What a courier verdict on each lane must claim about who produced it. The
# runners stamp these; this is the gate's copy, so a verdict that reaches the
# return path claiming something else is refused rather than filed.
#
# `vendor` here is the PROVIDER, matching the verdict's own field. The ledger's
# vendor is the lane name instead, which is the pair the #100 archive has rows
# disagreeing about.
LANE_IDENTITY = {
    "codex": {"vendor": "openai", "model": "gpt-5.6-terra"},
    "claude": {"vendor": "anthropic", "model": "claude-haiku-4-5-20251001"},
}


def courier_identity_violation(verdict, task_id, lane):
    """The first identity field of a courier verdict that doesn't match the
    lane, as (field, actual, expected), or None.

    Applies only to the lane-suffixed stem. An in-family verdict of record
    names whichever model actually ran it and has no pinned identity to check
    against.
    """
    identity = LANE_IDENTITY.get(lane)
    if not isinstance(verdict, dict) or identity is None:
        return None
    expected = {
        "task_id": task_id,
        "checker": "checker-courier",
        "vendor": identity["vendor"],
        "model": identity["model"],
    }
    for field, want in expected.items():
        if verdict.get(field) != want:
            return field, verdict.get(field), want
    return None

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
    if os.path.isfile(os.path.join(candidate, ".agent-guild", "CLAUDE.md")):
        return candidate
    raise RuntimeError(
        f"project_dir(): CLAUDE_PROJECT_DIR is unset/invalid and the "
        f"two-dirs-up fallback candidate {candidate!r} has no "
        f".agent-guild/CLAUDE.md marker. This is likely _lib.py running from "
        f"inside a plugin install, where two-up is the plugin's parent, not "
        f"the user's project—set CLAUDE_PROJECT_DIR instead of trusting the "
        f"guess."
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


def guild_initialized():
    """True if this repo has ever run init. Must never raise—including
    project_dir()'s own RuntimeError, which a user-scope plugin install
    triggers constantly: every hook fires in every repo on the machine, most
    of which have no .agent-guild/ at all. _lib.run() turns any raised
    exception into exit 2 (block), so a raise here would block the Stop of
    every session in every unrelated repo, which is strictly worse than the
    bug this check exists to fix."""
    try:
        return os.path.isfile(
            os.path.join(project_dir(), ".agent-guild", "CLAUDE.md")
        )
    except Exception:
        return False


def lane_exhausted(lane):
    """True if a courier lane's quota sentinel is set (state/exhausted/<lane>,
    the per-lane directory form, adopted now so a future second lane needs no
    migration). Must never raise, same contract as paused(): a broken check
    here can't be allowed to block the in-family fallback dispatch-guard
    steers callers toward when a lane is exhausted."""
    try:
        return os.path.exists(state_path("exhausted", lane))
    except Exception:
        return False


IN_FLIGHT_TTL_S_DEFAULT = 3600.0


def _in_flight_dir():
    return state_path("log", "in-flight")


def mark_in_flight(ident, agent):
    """Record that `agent` was just legally dispatched for `ident` (a
    Task-ID, Audit-ID, or Audition-ID)—called from dispatch-guard.py at
    every allowed dispatch. stop-gate.py reads these to tell a genuinely
    stuck loop apart from a subagent that's still working (#111): the task
    tuple, the verdict set, and the debt list all stay put while a worker or
    checker is mid-flight, which is exactly what used to make a long-running
    dispatch look identical to a livelock. Waves made that the common case
    instead of a rare one.

    Best-effort, same posture as dispatch-guard's own _log(): a write
    failure here must never turn a legal dispatch into a block. Losing a
    marker silently degrades back to the pre-#111 blindness, not to
    anything worse.
    """
    try:
        d = _in_flight_dir()
        os.makedirs(d, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        path = os.path.join(d, f"{ident}--{agent}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"dispatched_at": ts}, f)
    except Exception:
        pass


def clear_in_flight(ident, agent):
    """Remove the marker mark_in_flight wrote for (ident, agent). Called
    from subagent-return.py once a subagent's return is fully resolved. A
    missing file is not an error: the marker can legitimately already be
    gone (aged out under the TTL, or never written because the dispatch
    predates this feature)."""
    try:
        path = os.path.join(_in_flight_dir(), f"{ident}--{agent}.json")
        os.remove(path)
    except FileNotFoundError:
        pass
    except Exception:
        pass


def in_flight(ttl=None):
    """Sorted list of in-flight marker stems (`<ident>--<bare-agent>`, the
    filename minus `.json`) whose dispatch is still FRESH: within `ttl`
    seconds of now. `ttl=None` (the default) reads
    AGENT_GUILD_INFLIGHT_STALE_S if set, else IN_FLIGHT_TTL_S_DEFAULT
    (3600s)—the env var is the test seam, letting a test zero out every
    marker's freshness instantly instead of waiting out a real hour to prove
    a dead agent's marker ages out.

    Staleness matters on purpose: nothing here suppresses stall detection
    permanently. A marker that can't be read or parsed is treated as absent
    rather than crashing the gate: a wedged marker file must never be able to
    jam the very livelock backstop it exists to unblock.
    """
    if ttl is None:
        try:
            ttl = float(os.environ.get(
                "AGENT_GUILD_INFLIGHT_STALE_S", str(IN_FLIGHT_TTL_S_DEFAULT)))
        except ValueError:
            ttl = IN_FLIGHT_TTL_S_DEFAULT
    d = _in_flight_dir()
    try:
        names = os.listdir(d)
    except OSError:
        return []
    now = datetime.now(timezone.utc)
    fresh = []
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, name), encoding="utf-8") as f:
                record = json.load(f)
            dispatched_at = datetime.strptime(
                record["dispatched_at"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
        except Exception:
            continue  # malformed/unreadable marker: not fresh, not fatal
        if (now - dispatched_at).total_seconds() <= ttl:
            fresh.append(name[: -len(".json")])
    return sorted(fresh)


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


# A verdict of record's stem: T-<n>-<tier>-r<n>, no lane suffix. Anchored at
# both ends so a lane sibling (…-r0-codex.json) can't match—its filename has
# a segment past r<n> that this pattern has no room for.
_RECORD_STEM_RE = re.compile(r"^(T-\d+)-[A-Za-z0-9]+-r(\d+)$")

# A lane-suffixed verdict filename, stem plus one of the two courier lanes.
# Used only to find CANDIDATE foreign files (#141/#100); whether one is
# actually foreign is decided by the dispatcher's in-flight marker, not by
# this shape match.
_LANE_VERDICT_RE = re.compile(
    r"^(T-\d+-[A-Za-z0-9]+-r\d+)-(" + "|".join(COURIER_LANES) + r")\.json$"
)


def crossing_stem(tid, tier, retries):
    """The verdict-of-record stem a courier crossing for (tid, tier, retries)
    corresponds to: T-NNN-tier-rN, no lane suffix. dispatch-guard.py and
    subagent-return.py each compute this independently from the SAME three
    inputs—the task's own id, tier, and retry count—never from a filename
    that happens to land in verdicts/. That's the whole fix for #100/#141:
    a file's name used to be trusted as its own proof of authorization."""
    return f"{tid}-{tier}-r{retries}"


def foreign_stem_writes(owner_tid, lane):
    """Lane-suffixed verdict files in verdicts/ that belong to some task
    OTHER than `owner_tid` and had no courier dispatched against them (C-2)—
    the #100 shape verbatim: a courier dispatched for T-001 also wrote
    T-002-...-codex.json, and nothing had ever authorized that crossing.
    Called from subagent-return.py's checker-courier success path, so
    `owner_tid` is the Task-ID the RETURNING courier was dispatched under.

    #167 made the second opinion opt-in and retired the crossing debt, which
    took the reservation records this used to read. The in-flight marker is
    the substitute and the better fit: it already records one live dispatch
    per (task, agent), dispatch-guard writes it on the same legal-dispatch
    path that used to reserve, and it ages out on its own. A file whose own
    task has a FRESH checker-courier marker is a concurrent legitimate
    crossing mid-flight, not a foreign write, and C-2 requires exactly that
    concurrency not be mistaken for the incident it names.

    Already-flagged files (a sibling `.flagged` marker, written by
    surface_foreign_stem_write) are skipped so repeated courier returns
    don't grow the log without bound. Never raises: a scan failure on a
    subagent's success path must not turn a legal return into a block.
    """
    try:
        vdir = state_path("verdicts")
        names = set(os.listdir(vdir))
    except OSError:
        return []
    live = set(in_flight())
    found = []
    for name in sorted(names):
        m = _LANE_VERDICT_RE.match(name)
        if not m or m.group(2) != lane:
            continue
        stem = m.group(1)
        rm = _RECORD_STEM_RE.match(stem)
        if not rm:
            continue
        file_tid = rm.group(1)
        if file_tid == owner_tid:
            continue  # our own crossing, handled by the normal validation path
        if f"{name}.flagged" in names:
            continue  # already surfaced once
        if f"{file_tid}--checker-courier" in live:
            continue  # a legitimate dispatch of its own, just not this one
        found.append((file_tid, stem, name))
    return found


def surface_foreign_stem_write(owner_tid, file_tid, name):
    """Log one foreign-stem write (C-2) and flag it so it's reported once,
    not on every later courier return that happens to scan the same
    directory. A row under .agent-guild/state/log/ is one of C-2's two
    named surfacing channels—chosen over a non-zero exit because a block
    here would hang a subagent for something that isn't its own fault: the
    file it's being blamed for was never something it wrote or could fix.
    Best-effort, like dispatch-guard's own _log(): a failure to record this
    must never turn a legal return into a block."""
    try:
        os.makedirs(state_path("log"), exist_ok=True)
        # Concurrent under a wave (#164): rides the same O_APPEND reliance
        # dispatch-guard._log documents. This row is longer than most, still
        # far under PIPE_BUF.
        with open(state_path("log", "foreign-stem-writes.log"), "a", encoding="utf-8") as f:
            f.write(
                f"{name} names {file_tid}, but was found during a "
                f"checker-courier return dispatched for {owner_tid}; no "
                f"dispatch ever authorized {file_tid}'s crossing at this "
                "stem (#100).\n"
            )
        open(state_path("verdicts", f"{name}.flagged"), "w").close()
    except Exception:
        pass


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


_KEY_RE = re.compile(r"^([A-Za-z0-9_]+):\s*(.*)$")
# Block scalar header: style (| literal, > folded) plus an optional chomping
# indicator. Explicit indentation indicators (`|2`) are deliberately not
# matched—see parse_frontmatter's docstring.
_BLOCK_SCALAR_RE = re.compile(r"^([|>])([+-]?)$")


def _read_block_scalar(lines, start, style, chomp):
    """Read a block scalar's body starting at `lines[start]`. Returns
    (value, index of the first line past the body).

    Frontmatter here is flat—every key sits at column 0—so "indented at all"
    is the parent-indent test YAML would otherwise compute from the key's own
    column."""
    end = start
    while end < len(lines):
        line = lines[end]
        if line.strip() == "" or line[:1] in (" ", "\t"):
            end += 1
            continue
        break  # column-0 content: the next key, the closing ---, anything else

    body = lines[start:end]
    while body and body[-1].strip() == "":
        body.pop()  # trailing blanks belong to the document, not the scalar
        end -= 1

    first = next((ln for ln in body if ln.strip()), "")
    indent = len(first) - len(first.lstrip())
    body = [ln[indent:] if ln.strip() else "" for ln in body]

    if style == "|":
        text = "\n".join(body)
    else:
        # Folding: a line break between two plain lines becomes a space, a run
        # of n blank lines becomes n newlines, and a line that is STILL
        # indented after the dedent is "more indented"—kept verbatim, with the
        # breaks around it intact. That last rule is what keeps an indented
        # continuation inside a check_method from being flattened into its
        # neighbor.
        out = []
        blanks = 0
        prev_indented = False
        for line in body:
            if not line.strip():
                blanks += 1
                continue
            indented = line[:1].isspace()
            if out or blanks:
                if blanks:
                    out.append("\n" * blanks)
                elif indented or prev_indented:
                    out.append("\n")
                else:
                    out.append(" ")
            out.append(line)
            blanks, prev_indented = 0, indented
        text = "".join(out)

    if text:
        text += "\n"  # the final line break, which chomping now rules on
    if chomp == "-":
        text = text.rstrip("\n")
    elif chomp == "+":
        blanks = 0
        while end + blanks < len(lines) and lines[end + blanks].strip() == "":
            blanks += 1
        text += "\n" * blanks
    return text, end


def parse_frontmatter(text):
    """Parse the leading --- ... --- block. Handles scalars, inline [a,b]
    lists, block '- item' lists, and block scalars (`|`, `>`, with any
    chomping indicator). Good enough for our task/verdict files; deliberately
    not a full YAML engine—no anchors, no nesting, no explicit indentation
    indicators (`|2`), no multi-line flow collections."""
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
        m = _KEY_RE.match(line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            block = _BLOCK_SCALAR_RE.match(val)
            if block:
                # A task's check_method is written this way because it runs
                # long, and the body used to be dropped on the floor: the task
                # cited its clauses, named its checks, and handed the checker
                # an empty string (#109). Reading the body also keeps the guard
                # that dropping it used to buy—the body's indented `- item`
                # lines are consumed here, so they never reach the list branch
                # above.
                fm[key], i = _read_block_scalar(
                    lines, i + 1, block.group(1), block.group(2)
                )
                key = None
                continue
            if val == "":
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


def unverifiable(tid, task):
    """The reason `task` can't be verified as written, or None if it can.

    One reason today: it cites clauses and names no check for them. That
    combination looks fine in an editor and passes every other gate, and it
    used to be what a block-scalar check_method silently degraded into
    (#109)—a checker with nothing to run, reporting a pass."""
    clauses = task.get("clauses")
    if isinstance(clauses, str):
        clauses = [clauses] if clauses.strip() else []
    if not clauses:
        return None
    if str(task.get("check_method", "")).strip():
        return None
    return (
        f"{tid} cites clauses {', '.join(str(c) for c in clauses)} but its "
        f"check_method is empty: .agent-guild/state/tasks/{tid}.md. A task "
        "that names no check for the clauses it cites can't be verified—the "
        "checker would have nothing to run and would report a pass anyway. "
        "Write each cited clause's check into check_method (a "
        ".agent-guild/scripts/ invocation, or 'checker-judgment: <rubric>') "
        "before dispatching."
    )


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


def file_sha256(path):
    """Hex sha256 of a file's bytes, or None when it can't be read. Content and
    not mtime, so a rewrite that changes nothing leaves the gate open (#110)."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def audit_stamp_path(verdict_path):
    """Where an audit's approved-content digest lives: a sidecar beside the
    verdict, not a field inside it. The verdict belongs to the auditor that
    wrote it, and a hook reaching into that file would make the gate a
    co-author of the check it later reads."""
    return verdict_path + ".sha256"


def latest_audit_round(audit_id):
    """(n, path) for the highest round among state/verdicts/<audit_id>-r<N>.md,
    or (None, None) when the auditor has never filed one.

    The round is parsed as an integer. Sorting the filenames instead puts r10
    before r2, which reads the ninth round's verdict as the job's latest for
    the rest of the run."""
    vdir = state_path("verdicts")
    if not os.path.isdir(vdir):
        return None, None
    pat = re.compile(rf"^{re.escape(audit_id)}-r(\d+)\.md$")
    best_n, best_path = None, None
    for name in os.listdir(vdir):
        m = pat.match(name)
        if m:
            n = int(m.group(1))
            if best_n is None or n > best_n:
                best_n, best_path = n, os.path.join(vdir, name)
    return best_n, best_path


def next_audit_round(audit_id):
    """The round the auditor being dispatched will write. Same arithmetic the
    auditor's own brief gives it: 0 when no round exists, otherwise one past
    the highest. Predicting it is what lets the constitution be fingerprinted
    when the audit is commissioned rather than when it comes back."""
    n, _ = latest_audit_round(audit_id)
    return 0 if n is None else n + 1


# One message table for both gates, so the two audits can't drift into
# different vocabularies for the same refusal.
_AUDIT_GATE_MSG = {
    "CON-audit": {
        "missing": (
            "No PASS constitution audit yet. Run /constitution, then dispatch "
            "the auditor (Audit-ID: CON-audit) and get a PASS before any worker "
            "builds against the constitution. Verification applies to all ranks."
        ),
        "not_pass": (
            "CON-audit r{n} is {verdict}—the latest constitution audit did not "
            "pass. Revise per its diagnosis and re-dispatch the auditor "
            "(Audit-ID: CON-audit) for a fresh PASS."
        ),
    },
    "DEC-audit": {
        "missing": (
            "Tasks exist but no DEC-audit verdict does. Dispatch the auditor "
            "(Audit-ID: DEC-audit) and get a PASS before any worker runs a "
            "task. Verification covers the decomposition, not just the "
            "constitution."
        ),
        "not_pass": (
            "DEC-audit r{n} is {verdict}—the latest decomposition audit did not "
            "pass. Fix what its diagnosis names, then re-dispatch the auditor "
            "(Audit-ID: DEC-audit) for a fresh PASS before dispatching workers."
        ),
    },
}


def audit_gate(audit_id, artifact_path=None):
    """(ok, reason) for one of the worker path's audit gates. reason is a
    complete block message on refusal, None on pass.

    Only the latest round counts. An older PASS used to satisfy the gate for
    the rest of the job no matter what the rounds after it found, which is how
    a constitution that failed three consecutive audits kept dispatching
    workers (#110, observed on the #97 run).

    artifact_path binds the PASS to the bytes it judged, via the sidecar
    dispatch-guard stamps when the audit is commissioned. Without it the gate
    asks only whether the
    latest round passed—which is all a decomposition can be asked today, since
    task files change status throughout a job and would invalidate a digest on
    the first transition."""
    msgs = _AUDIT_GATE_MSG[audit_id]
    n, vpath = latest_audit_round(audit_id)
    if vpath is None:
        return False, msgs["missing"]

    with open(vpath, encoding="utf-8") as f:
        fm = parse_frontmatter(f.read())
    verdict = str(fm.get("verdict", "")).strip().upper() or "unreadable"
    if verdict != "PASS":
        return False, msgs["not_pass"].format(n=n, verdict=verdict)

    if artifact_path is None:
        return True, None

    try:
        rel = os.path.relpath(artifact_path, project_dir())
    except (OSError, ValueError):
        rel = artifact_path

    # Read the artifact before the stamp. A missing constitution and a missing
    # stamp both refuse, but only one of them is fixable by re-auditing, so
    # reporting the stamp first sends you around a loop that can't close.
    current = file_sha256(artifact_path)
    if current is None:
        return False, (
            f"{audit_id} r{n} records PASS but {rel} does not exist. Restore or "
            f"rewrite it, then re-audit (Audit-ID: {audit_id})."
        )

    stamp = None
    try:
        with open(audit_stamp_path(vpath), encoding="utf-8") as f:
            stamp = f.read().strip()
    except OSError:
        pass
    if not stamp:
        return False, (
            f"{audit_id} r{n} records PASS but carries no approved-content "
            f"stamp (the verdict predates digest stamping, or the stamp was "
            f"removed). Re-dispatch the auditor (Audit-ID: {audit_id}) for a "
            "fresh PASS."
        )

    if current != stamp:
        return False, (
            f"{rel} changed since {audit_id} r{n} approved it. Re-dispatch the "
            f"auditor (Audit-ID: {audit_id}) and get a fresh PASS on the "
            "current text before any worker builds against it."
        )
    return True, None


# Claude Code records a subagent dispatch as an assistant tool_use block for one
# of these tool names; the id we need rides in that block's `input.prompt`.
_DISPATCH_TOOLS = {"Task", "Agent", "spawn_agent"}


_LABELED_ID_PATTERNS = (
    ("task", TASK_ID_RE),
    ("audit", AUDIT_ID_RE),
    ("audition", AUDITION_ID_RE),
)


def labeled_ids(text):
    """Every labeled Task-ID / Audit-ID / Audition-ID in a blob of text, as
    (kind, id, position) tuples sorted by match start—`kind` one of "task",
    "audit", "audition". Finds every match of every pattern rather than
    stopping at the first regex to hit, so a caller can reason about ALL the
    ids a blob carries, not just whichever one a fixed regex order surfaces
    first."""
    if not isinstance(text, str):
        return []
    found = []
    for kind, pattern in _LABELED_ID_PATTERNS:
        for m in pattern.finditer(text):
            found.append((kind, m.group(1), m.start()))
    found.sort(key=lambda t: t[2])
    return found


def _id_in(text):
    """Earliest labeled Task-ID / Audit-ID / Audition-ID in a blob of text, or
    None. Earliest BY POSITION, not by which regex is declared first: a
    dispatch prompt commonly carries context beyond its own id (e.g. an
    auditor's prompt noting an unrelated task still in flight), and the id
    that labels THIS dispatch is whichever one actually comes first in the
    text, regardless of which of the three patterns happens to match it."""
    found = labeled_ids(text)
    return found[0][1] if found else None


def dispatch_candidates(transcript_path):
    """Every agent dispatch a transcript records, in document order, as
    `(ident, agent)` pairs, plus the ids found in plain user text.

    FRAGILE: both Claude Code and Codex document their transcript JSONL as
    unstable. Claude's SubagentStop supplies the parent transcript, where the id
    lives in an assistant Task/Agent tool_use input. Codex supplies the child
    transcript explicitly, where the opening prompt is currently a response_item
    message or event_msg user_message. We scan both records, plus Codex
    function_call dispatches, so this parser remains one shared compatibility
    boundary rather than a host-specific policy fork.

    The pairs are what let a returning subagent be told apart from its wave
    siblings. The contract dispatches a wave as parallel Task calls in ONE
    assistant message, so position identifies nobody: on #193 a checker and a
    worker went out together and the checker's return resolved to the worker's
    task, leaking a marker for the full TTL (#204). `agent` is the type the
    dispatch asked for, or "" where the record doesn't say, and a caller must
    read "" as matching anything—a host that stops reporting the type should
    degrade to the old ambiguity rather than narrow every candidate away and
    identify nobody at all.
    """
    with open(transcript_path, encoding="utf-8") as f:
        raw_lines = f.readlines()

    tool_dispatches = []  # (ident, agent) per dispatch, in document order
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
                        tool_input = block.get("input") or {}
                        got = _id_in(_dispatch_prompt(tool_input))
                        if got:
                            tool_dispatches.append(
                                (got, _dispatched_agent(tool_input))
                            )

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
                    tool_dispatches.append((got, _dispatched_agent(arguments)))

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

    return tool_dispatches, user_ids


def _dispatched_agent(tool_input):
    """The bare agent type a dispatch record asked for, or "" if it doesn't say.
    Claude puts it in the Task input's `subagent_type`, Codex in the
    function_call arguments' `agent_type`."""
    if not isinstance(tool_input, dict):
        return ""
    for key in ("subagent_type", "agent_type"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return bare_agent(value.strip())
    return ""


def _no_id_error(transcript_path):
    return ValueError(
        f"no Task-ID/Audit-ID/Audition-ID found in any agent dispatch or "
        f"user message of {transcript_path}"
    )


def _child_transcript(data, parent):
    """The returning subagent's OWN transcript, where its opening prompt names
    the task it was dispatched for. Claude writes it under the parent's session
    directory as `<session>/subagents/agent-<agent_id>.jsonl`—confirmed against
    live session data, five ids for five. A host may hand the path over
    directly instead. None when nothing readable turns up, which is an ordinary
    outcome rather than an error."""
    direct = data.get("agent_transcript_path")
    if isinstance(direct, str) and os.path.isfile(direct):
        return direct
    agent_id = data.get("agent_id")
    if not isinstance(agent_id, str):
        return None
    agent_id = agent_id.strip()
    # The id lands inside a path, so anything that could climb out of the
    # session directory disqualifies it. A host is not the threat here; a
    # malformed field is.
    separators = {os.sep, os.altsep} - {None, ""}
    if (
        not agent_id
        or os.path.isabs(agent_id)
        or "\0" in agent_id
        or ".." in agent_id
        or any(sep in agent_id for sep in separators)
    ):
        return None
    name = f"agent-{agent_id}.jsonl"
    session_dir = parent[: -len(".jsonl")] if parent.endswith(".jsonl") else None
    probes = [os.path.join(os.path.dirname(parent), name)]
    if session_dir:
        probes.insert(0, os.path.join(session_dir, "subagents", name))
    for probe in probes:
        if os.path.isfile(probe):
            return probe
    return None


def _ident_from_child(data, parent, candidates):
    """Which of `candidates` the returning agent's own transcript claims, or
    None. Exact identity where it is available at all: the child's opening
    prompt is the dispatch this agent actually received.

    Codex is excluded because its child prompt is encrypted, which is the whole
    reason its id rides `task_name` (#71).
    """
    if str(data.get("hook_host") or "").strip().lower() == "codex":
        return None
    child = _child_transcript(data, parent)
    if not child:
        return None
    try:
        _child_tools, child_users = dispatch_candidates(child)
    except (OSError, ValueError):
        return None
    # The dispatch prompt is the earliest labeled id in the child's user turns;
    # everything after it is tool results and follow-ups, which routinely name
    # other tasks. Trust it only where it names a dispatch we already found in
    # the parent, so a stray id in a tool result can never invent a candidate.
    if child_users and child_users[0] in candidates:
        return child_users[0]
    return None


def _log_ambiguous_return(agent, candidates, chosen):
    """Say out loud that identity was guessed rather than determined. Nothing
    downstream reads this; it exists so a mis-attributed return leaves a trace
    to find later, the way #204 itself was only findable because the checker
    happened to say something."""
    msg = (
        f"subagent-return could not separate this {agent} return from its wave "
        f"siblings ({', '.join(candidates)}); attributing it to {chosen}, the "
        "last matching dispatch. If this recurs, the host stopped supplying "
        "the per-agent transcript that tells siblings apart—see "
        "_lib._child_transcript."
    )
    try:
        with open(state_path("log", "return-gate.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    sys.stderr.write(msg + "\n")


def ident_for_return(data):
    """The id of the subagent whose SubagentStop this is, narrowed against
    everything the hook input knows about it.

    The transcript alone can only offer its LAST dispatch, which is right while
    dispatches are serial and a coin flip once a wave goes out in one message
    (#204). So each tier narrows the ambiguity the one above it left, exact
    evidence before heuristics: the agent's own type, then its own transcript,
    then which dispatches are still in flight.

    What it never does is decline to answer. An exception here becomes
    `_unidentifiable`, which exits 0 and skips the protocol check, the verdict
    validation, and the courier identity check alike—so refusing to guess would
    disable the gate on exactly the shape the contract dispatches every wave in,
    rather than merely misreading it. The floor is therefore the reading this
    gate always had, logged as a guess when that is what it is.
    """
    transcript = data.get("transcript_path")
    agent = bare_agent(data.get("agent_type", ""))
    tool_dispatches, user_ids = dispatch_candidates(transcript)

    if not tool_dispatches:
        # No wave treatment needed here, and none possible. This fallback only
        # fires when the transcript records ZERO dispatch tool calls, and a wave
        # is by definition two or more dispatch records, so the parallel shape
        # can never reach it. What does reach it is a child transcript with one
        # opening prompt (#71), and the earliest labeled id is that prompt—the
        # later ones are tool results, which name whatever the agent happened to
        # read.
        if user_ids:
            return user_ids[0]
        raise _no_id_error(transcript)

    # Tier 1: the type this return says it is. A dispatch that recorded no type
    # matches anything, and a narrowing that matches nothing falls back to the
    # full set rather than identifying nobody—a host that stops reporting the
    # type must degrade to the old ambiguity, not to a confident wrong answer.
    matched = [(i, a) for i, a in tool_dispatches if not a or a == agent]
    if not matched:
        matched = tool_dispatches

    # Dedupe keeping the LAST occurrence, so the tail stays the most recent
    # dispatch even where a rework re-dispatched an id already in the list.
    uniq = []
    for ident, _agent in matched:
        if ident in uniq:
            uniq.remove(ident)
        uniq.append(ident)
    if len(uniq) == 1:
        return uniq[0]

    # Tier 2: the agent's own transcript. This outranks the marker sweep below
    # because it is evidence rather than inference—a marker says only that some
    # dispatch has not been cleared yet, and the one survivor of a TTL can
    # easily be the sibling rather than the returner.
    own = _ident_from_child(data, transcript, uniq)
    if own:
        return own

    # Tier 3: which of them is still out. A parent transcript accumulates every
    # dispatch of the whole session, so most candidates are already home.
    live = set(in_flight())
    alive = [i for i in uniq if f"{i}--{agent}" in live]
    if len(alive) == 1:
        return alive[0]

    # Nothing separates them. Take the last matching dispatch, which is what
    # this gate read before any of this existed, and say that it was a guess.
    candidates = alive or uniq
    _log_ambiguous_return(agent, candidates, candidates[-1])
    return candidates[-1]


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
