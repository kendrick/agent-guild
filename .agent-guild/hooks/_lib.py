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
    migration). Must never raise, same contract as paused(): a broken check
    here can't be allowed to block the in-family fallback dispatch-guard
    steers callers toward when a lane is exhausted."""
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


# A verdict of record's stem: T-<n>-<tier>-r<n>, no lane suffix. Anchored at
# both ends so a lane sibling (…-r0-codex.json) can't match—its filename has
# a segment past r<n> that this pattern has no room for—which matters because
# a lane file matching here would owe a second opinion on its own second
# opinion, a debt nothing could ever discharge.
_RECORD_STEM_RE = re.compile(r"^(T-\d+)-[A-Za-z0-9]+-r(\d+)$")

# A lane-suffixed verdict filename, stem plus one of the two courier lanes.
# Used only to find CANDIDATE foreign files (#141/#100); whether one is
# actually foreign is decided by crossing_reserved(), not by this shape match.
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


def _authorization_path(stem, lane):
    return state_path("verdicts", f"{stem}-{lane}.authorized")


def reserve_crossing(tid, stem, lane):
    """Record, at DISPATCH time, that a courier crossing for `stem`/`lane` is
    about to happen. Called from dispatch-guard.py right before a legal
    checker-courier dispatch is logged.

    A stem that already has a verdict file sitting on it is left unreserved
    on purpose: recording authorization for a path something already
    occupies would launder a forged file the moment a legitimate dispatch
    for the same round followed it—the exact anti-laundering requirement
    C-1 names. The forge check (check-141-conformance.py) writes its forged
    sibling with no dispatch at all, so this branch isn't what that script
    exercises; it's here for the case a forged file predates a real retry.

    Best-effort, same posture as dispatch-guard's own _log(): a write
    failure here must never turn an otherwise-legal dispatch into a block.
    It can only ever leave a stem unauthorized (an owed debt, still
    clearable by a `.denied` waiver), never crash the gate that calls it.
    """
    try:
        if os.path.exists(state_path("verdicts", f"{stem}-{lane}.json")):
            return False
        os.makedirs(state_path("verdicts"), exist_ok=True)
        record = {
            "task_id": tid,
            "promoted": False,
            "reserved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(_authorization_path(stem, lane), "w", encoding="utf-8") as f:
            json.dump(record, f)
        return True
    except Exception:
        return False


def promote_crossing(tid, stem, lane):
    """Record, at RETURN time, that the courier reserved for `stem`/`lane`
    actually finished and its content validated. Called from
    subagent-return.py once a checker-courier's return has passed schema and
    identity validation—including the Codex read-only path, where the
    courier itself never writes a file at all and the PARENT persists the
    verdict afterward; promoting from the validated OUTCOME rather than from
    a file on disk is what keeps every Codex-lane crossing from stranding.

    Reserving at dispatch alone would leave a window between "dispatched"
    and "returned" where anything else that landed a file at the reserved
    stem would read as authorized. Requiring promotion ties authorization to
    a SPECIFIC subagent's own SubagentStop, not merely to a Task/Agent call
    having gone out.

    A no-op (returns False) if nothing was ever reserved for this exact
    (tid, stem, lane)—the #100 shape, where the courier that wrote the file
    was dispatched for a DIFFERENT task and reserved a different stem, so
    its promotion (keyed to ITS OWN ident) never touches this one. Never
    raises, same contract as reserve_crossing.
    """
    path = _authorization_path(stem, lane)
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
    except Exception:
        return False
    if not isinstance(record, dict) or record.get("task_id") != tid:
        return False
    try:
        record["promoted"] = True
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f)
        return True
    except Exception:
        return False


def crossing_authorized(stem, lane):
    """True if the gate's own record shows `stem`/`lane` was both reserved
    AND promoted—see reserve_crossing/promote_crossing. This is the ONLY
    thing second_opinion_debts() trusts to grant discharge via a
    lane-suffixed verdict; the file's own existence proves nothing (#100).
    Never raises: an unreadable or malformed authorization record reads as
    unauthorized, the same fail-closed posture second_opinion_debts() itself
    holds to, and matches two of C-5's four malformed-input cases (a missing
    authorization record, and a truncated or non-JSON one)."""
    try:
        with open(_authorization_path(stem, lane), encoding="utf-8") as f:
            record = json.load(f)
    except Exception:
        return False
    return isinstance(record, dict) and record.get("promoted") is True


def crossing_reserved(stem, lane):
    """True if a reservation exists for `stem`/`lane`, whether or not it was
    ever promoted—used by foreign_stem_writes() to tell a legitimately
    in-flight crossing (reserved, courier still running, not yet returned)
    apart from one nobody ever dispatched at all. Never raises."""
    try:
        with open(_authorization_path(stem, lane), encoding="utf-8") as f:
            record = json.load(f)
    except Exception:
        return False
    return isinstance(record, dict) and bool(record.get("task_id"))


def foreign_stem_writes(owner_tid, lane):
    """Lane-suffixed verdict files in verdicts/ that belong to some task
    OTHER than `owner_tid` and carry no reservation of their own (C-2)—the
    #100 shape verbatim: a courier dispatched for T-001 also wrote
    T-002-...-codex.json, and nothing had ever authorized that crossing.
    Called from subagent-return.py's checker-courier success path, so
    `owner_tid` is the Task-ID the RETURNING courier was dispatched under.

    A file whose own stem IS reserved (crossing_reserved) is excluded even
    if not yet promoted: that's a concurrent, legitimately dispatched
    crossing for its own task mid-flight, not a foreign write, and C-2
    requires exactly that concurrency not be mistaken for the incident it
    names. Already-flagged files (a sibling `.flagged` marker, written by
    surface_foreign_stem_write) are skipped so repeated courier returns
    don't grow the log without bound. Never raises: a scan failure on a
    subagent's success path must not turn a legal return into a block.
    """
    try:
        vdir = state_path("verdicts")
        names = set(os.listdir(vdir))
    except OSError:
        return []
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
        if crossing_reserved(stem, lane):
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


def second_opinion_debts(data=None):
    """List of outstanding second-opinion debts, one per unresolved verdict
    of record, as (task_id, stem, lane).

    The dual-check regime (a courier crossing after every checker of record)
    is contract, not code: nothing previously read the verdicts directory to
    confirm a crossing actually landed, so a Claude-host run reached
    `complete` on 2026-08-02 without one and no gate noticed. This is the
    predicate stop-gate.py and dispatch-guard.py read to close that hole.

    Discharge is generous—an AUTHORIZED courier response either way (see
    crossing_authorized; #141 stopped a lane file's mere presence from being
    enough, after #100 showed a forged one could pass for it), the quota
    sentinel, an orchestrator waiver, a recorded skip on a stem citing only
    script-checked clauses (#128—compose-brief's exit 3 wrote no brief for a
    courier to cross with, so nothing was ever dispatchable), or a blocked
    verdict of record all clear a debt, since a `blocked` in-family check has
    nothing yet for a crossing to compare against. An unreadable verdict of
    record forecloses only that last route, since `blocked` can't be
    established from a file that won't parse; the first four still stand. A
    courier response IS one of them, so declaring a record corrupt without
    first looking for one would strand a debt no future dispatch could
    clear: the file the next courier would write is already on disk.

    Never raises, the same contract paused() and lane_exhausted() hold to:
    stop-gate.py calls this every turn, so a crash here is a hook crash on
    whatever verdict happens to be malformed that turn.
    """
    lane = courier_lane(data)
    try:
        vdir = state_path("verdicts")
        names = set(os.listdir(vdir))
    except OSError:
        return []

    debts = []
    for name in sorted(names):
        if not name.endswith(".json"):
            continue
        stem = name[: -len(".json")]
        m = _RECORD_STEM_RE.match(stem)
        if not m:
            continue
        task_id = m.group(1)

        if any(
            f"{stem}-{l}.json" in names and crossing_authorized(stem, l)
            for l in COURIER_LANES
        ):
            # routes 1/2: an AUTHORIZED courier response landed, either lane.
            # #141: the file's mere presence used to be enough (#100—a
            # courier dispatched for T-001 wrote T-002's verdict and nothing
            # noticed); now discharge requires the gate's own dispatch/return
            # record, not just a filename that happens to match.
            continue

        if lane_exhausted(lane):
            # Route 3, pinned to THIS host's lane and no other. A predicate
            # that also accepted the far lane's sentinel would discharge a
            # Codex host's debts off exhausted/codex, its own lane never
            # having to exist—deadlocking it forever instead.
            continue

        if os.path.exists(os.path.join(vdir, f"{stem}-{lane}.denied")):
            # Route 4: the orchestrator's hand-written record that no crossing
            # is coming—a host that refused the dispatch outright (#94), and
            # since #141 also a stem the gate never recorded as authorized.
            # That second case splits on whether a reservation was ever made.
            # A courier that died after a legal dispatch left one behind, and
            # promote_crossing keys on the record's task_id rather than on
            # which dispatch reserved it, so a re-dispatch still discharges
            # that stem the honest way—prefer that, since it yields real #34
            # comparison data. Nothing rescues a stem with no reservation at
            # all: reserve_crossing skips a stem that already carries a file
            # (the anti-laundering rule), so the waiver is the only exit
            # before the debt rides to STALLED.md.
            continue

        if os.path.exists(os.path.join(vdir, f"{stem}-{lane}.skipped")):
            # Route 5 (#128): the orchestrator's record that this stem cites
            # only script-checked clauses—compose-brief's exit 3 wrote no
            # brief for a courier to cross with, so no crossing was ever
            # dispatchable in the first place. Pinned to THIS host's lane,
            # same as route 4's waiver: a marker filed under the far lane
            # discharges nothing, because dispatch-guard.py denies a courier
            # dispatch keyed on lane, not on task, and a debt this predicate
            # clears on the wrong lane would be a debt the far host's own
            # gate never actually retired.
            continue

        # Routes 1-5 settle before the file is ever opened, on purpose:
        # routes 1/2 ARE the file a courier writes, so an unreadable record
        # treated as owing regardless would strand a debt no dispatch could
        # clear—the next courier writes a path that is already there.
        # Unreadable forecloses route 6 (below) and nothing above it.
        record = None
        try:
            with open(os.path.join(vdir, name), encoding="utf-8") as f:
                record = json.load(f)
        except Exception:
            record = None

        if not isinstance(record, dict):
            # Can't read it, can't parse it, or it's valid JSON that isn't an
            # object—any of those means route 5 can't be established, so it
            # owes (routes 1-4 already had their shot above).
            debts.append((task_id, stem, lane))
            continue

        if record.get("verdict") == "blocked":
            # checker-courier's own contract (guild-core/roles/checker-
            # courier.md:28) turns auth failure, timeout, a missing CLI, and
            # twice-malformed vendor output all into a blocked verdict at the
            # lane stem—but a blocked verdict OF RECORD means the in-family
            # check itself never ran, so there is nothing yet for a crossing
            # to compare against.
            continue

        debts.append((task_id, stem, lane))
    return debts


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
