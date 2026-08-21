#!/usr/bin/env python3
"""PreToolUse(Task|Agent): every guild dispatch is legal, tagged, and logged.

Non-guild subagents pass through untouched. For a worker/checker/auditor
dispatch, this blocks unless:

  - the dispatch carries a `Task-ID: T-NNN` (or `Audit-ID:`), so
    subagent-return can later identify what finished—as a prompt line, or in
    `task_name` on a host that encrypts the prompt;
  - that task file exists, and names a check for the clauses it cites—a task
    with none is unverifiable, and its checker would report a pass on an empty
    check list (#109);
  - the dispatch is state-legal for the role (worker ⇒ assigned,
    checker ⇒ checking);
  - for a worker, every dep satisfies as a build input—complete, or
    needs-check/checking with all of ITS OWN deps complete (one level of
    speculation, #135)—so nothing starts building against inputs its own
    inputs haven't produced yet;
  - a worker's tier budget isn't already spent (retries within max), catching
    a forgotten escalation;
  - a worker's dispatched model matches the task's current tier, catching a
    forgotten model override after an escalation;
  - for workers, the latest CON-audit and DEC-audit rounds both PASS, and the
    CON PASS names the constitution that's on disk now—verification reaches
    the orchestrator's own work before any worker builds against it, and it
    stays reached when that work is revised (#110, #161);
  - for an auditor, .agent-guild/scripts/check-job-spec.py doesn't reject the
    paperwork first—so an opus auditor is never spent on a defect a stdlib
    script could have proven in about two seconds (#132). That script exits 1
    when a rule proved the defect and 4 when a rule inferred it; both block,
    and the block message says which, because only the second kind can be
    wrong about correct paperwork (#139).

Dispatching a CON-audit also fingerprints the constitution against the round
the auditor is about to write, which is what a later worker's gate compares.

A Codex followup, which re-tasks a running agent rather than spawning one, is
refused outright when it targets a guild agent: it carries nothing left to
check (#77).

Every passing dispatch appends one line to .agent-guild/state/log/dispatches.log
and drops an in-flight marker (_lib.mark_in_flight) under
.agent-guild/state/log/in-flight/—stop-gate.py's #111 fix, so a subagent
that's genuinely still working reads differently from a stalled loop.
subagent-return.py clears the marker once the subagent's return resolves.
"""
import importlib.util
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402


# A dispatch's own id is written as a line, per .agent-guild/CLAUDE.md ("as a
# line in the prompt"). _lib.labeled_ids/_id_in find a labeled id ANYWHERE in a
# blob of text, including mid-sentence—exactly right for dispatch_candidates'
# more forgiving return-time parse (a transcript can narrate or quote an id
# without meaning to identify the return), but wrong here: .agent-guild/CLAUDE.md
# itself quotes `Audit-ID: CON-audit` mid-sentence, and any dispatch whose prompt
# quotes the contract for context used to trip the two-kind ambiguity block
# below on text that was never trying to identify the dispatch at all. This
# module deliberately does not touch _lib.labeled_ids/_id_in—other callers
# (transcript parsing in subagent-return.py) depend on the unanchored
# behavior—and instead reuses _lib's own compiled patterns against one stripped
# line at a time, so the label/id shape stays a single source of truth while
# only a line that OPENS with the label counts.
_LEADING_MARKUP_RE = re.compile(r"^[ \t]*[-*>]*[ \t]*")


def _line_anchored_ids(text):
    """Every labeled Task-ID / Audit-ID / Audition-ID that opens a line (after
    stripping leading whitespace and a common markdown list/quote prefix—`-`,
    `*`, `>`), as (kind, id, line_no) tuples in document order. An id mentioned
    mid-sentence—including a quoted excerpt of the orchestrator contract—never
    opens a line and so is never a candidate here."""
    if not isinstance(text, str):
        return []
    found = []
    for lineno, line in enumerate(text.splitlines()):
        stripped = _LEADING_MARKUP_RE.sub("", line, count=1)
        for kind, pattern in (
            ("task", _lib.TASK_ID_RE),
            ("audit", _lib.AUDIT_ID_RE),
            ("audition", _lib.AUDITION_ID_RE),
        ):
            m = pattern.match(stripped)
            if m:
                found.append((kind, m.group(1), lineno))
                break  # a line names at most one id
    return found


def _log(agent, task, model):
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        # Use UTC with a trailing Z to match verdict and ledger timestamps.
        # dispatches.log is compared against those timestamps to establish
        # ordering, and a local-time stamp is silently wrong by the machine's offset.
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Concurrent since waves (#164): every member of a wave dispatches in
        # one message, so several copies of this hook append here in the same
        # instant. Safe by deliberate reliance on O_APPEND, which "a" mode
        # opens with: one short line, one write(2), well under PIPE_BUF, so
        # the kernel doesn't interleave it with a sibling's. No lock, because
        # fcntl buys correctness this file doesn't need at the price of NFS
        # failure modes in a best-effort logger. A torn or interleaved row in
        # here is this assumption breaking, not a hook misbehaving.
        with open(_lib.state_path("log", "dispatches.log"), "a", encoding="utf-8") as f:
            f.write(f"{ts} | {agent} | {task} | {model}\n")
    except Exception:
        # Logging is best-effort; never let it turn a legal dispatch into a block.
        pass


def _log_gate_gap(ident, timeout_s):
    """Best-effort record that check-job-spec didn't finish for `ident`, so
    the auditor dispatched with the paperwork gate un-consulted. Same path
    resolution and bare except Exception: pass posture as _log above—this is
    the one thing that makes an allow-through-on-timeout auditable instead of
    silent, so it must never itself be the reason a dispatch fails."""
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        # Same concurrent-append reliance as _log above (#164).
        with open(_lib.state_path("log", "gate-gaps.log"), "a", encoding="utf-8") as f:
            f.write(
                f"{ts} | check-job-spec | {ident} | timed out after "
                f"{timeout_s}s, auditor dispatched with the gate un-run\n"
            )
    except Exception:
        pass


def _join_sentence(lead, tail):
    """Join two sentence fragments so the result reads as prose regardless of
    whether `lead` (the linter's own stderr line) already ends in
    punctuation. Without this, a stderr line with no trailing period runs
    straight into the sentence appended after it."""
    lead = lead.rstrip()
    if lead and lead[-1] not in ".!?":
        lead += "."
    return f"{lead} {tail}"


# 20s: real headroom over the ~3s check-job-spec takes on a 7-task job today,
# while staying well clear of the PreToolUse hook's own 30s budget (see
# plugin/hooks/hooks.json)—that budget covers this subprocess plus Python
# startup plus every check_method's own work, so the gap between 20 and 30
# has to absorb all of that, not just the linter's run time.
#
# Test-only seam: production always waits the full JOB_SPEC_TIMEOUT_S below.
# The timeout test needs to actually exercise a real subprocess.run() timeout
# to prove the branch works, and waiting out a real 20s would make every run
# of this suite crawl. AGENT_GUILD_JOB_SPEC_TIMEOUT lets that one test shrink
# the wait to a fraction of a second while running the identical code path;
# no real dispatch has any reason to set it.
JOB_SPEC_TIMEOUT_S = float(os.environ.get("AGENT_GUILD_JOB_SPEC_TIMEOUT", "20"))


def _job_spec_block(ident):
    """None if the auditor may proceed for `ident`; else the message to hand
    _lib.block(). Shells out to check-job-spec.py rather than importing it,
    same reasoning as subagent-return.py's validate-verdict.py call: the CLI
    is the documented contract, and a subprocess can't drift from it.

    Missing script and a stalled linter both resolve to None (let the auditor
    through), not a block. install.py never upgrades a project's copied-in
    .agent-guild/ payload (see _working-memory/conventions.md's payload-freeze
    note), so a repo can be running hooks newer than its own scripts/—and a
    gate that hard-fails when check-job-spec.py simply isn't there yet would
    brick every auditor dispatch on that payload. A timeout gets the same
    allow-through, for the same deadlock-avoidance reason: a hard fail on a
    slow linter would block every job behind it. But it is not the same as
    "free"—an unresponsive linter is exactly the epistemic state exit 3 is,
    "the gate did not run," and unlike exit 3 it would otherwise be silent.
    That's a real gap: the auditor still runs, but nothing checked the
    paperwork first, and #132 exists because that check catches things worth
    catching. _log_gate_gap() and the stderr note below are what keep the gap
    auditable instead of invisible.
    """
    linter = os.path.join(_lib.project_dir(), ".agent-guild", "scripts", "check-job-spec.py")
    if not os.path.exists(linter):
        return None
    repo_root = _lib.project_dir()
    cmd = [sys.executable, linter, "--audit-id", ident, "--repo-root", repo_root]
    reproduce = f"python3 {linter} --audit-id {ident} --repo-root {repo_root}"
    try:
        proc = subprocess.run(
            cmd, cwd=repo_root, capture_output=True, text=True,
            timeout=JOB_SPEC_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        _log_gate_gap(ident, JOB_SPEC_TIMEOUT_S)
        sys.stderr.write(
            f"dispatch-guard: check-job-spec timed out after "
            f"{JOB_SPEC_TIMEOUT_S:g}s for {ident}—the paperwork gate did not "
            f"run for this dispatch. Logged to "
            ".agent-guild/state/log/gate-gaps.log; the auditor is dispatched "
            "unchecked.\n"
        )
        return None
    if proc.returncode == 0:
        # A pass can still carry news: a `**Lint exception**` line waived a
        # heuristic that did fire (#139). That doesn't block—the waiver is
        # the whole point—but it must not be invisible, and this gate is the
        # only place a human reliably sees the linter at all.
        if "waived" in proc.stderr:
            sys.stderr.write(f"dispatch-guard: {proc.stderr.strip()}\n")
        return None
    if proc.returncode == 3:
        return (
            f"check-job-spec couldn't read the paperwork for {ident} (exit "
            f"3): {proc.stderr.strip()}. An infra failure isn't evidence the "
            f"paperwork is sound—fix whatever check-job-spec choked on, then "
            f"reproduce with: {reproduce}"
        )
    if proc.returncode == 4:
        # A heuristic fired (#139). It still blocks—a rule that infers is
        # right more often than not, and #132 rejected making these warn-only
        # because this hook reads stderr and discards stdout, so a
        # non-blocking rule would produce output nobody ever sees. What
        # changes is what the reader is told. Three of the four inferring
        # rules produced false positives when #132's review measured them, so
        # "rewrite the artifact until the rule shuts up" is the wrong first
        # move here in a way it never is for a proof. The linter's own stderr
        # carries the waiver syntax.
        detail = proc.stderr.strip() or "check-job-spec exited 4 (heuristic)"
        return _join_sentence(
            detail,
            "That rule infers its defect rather than proving one, so it can "
            "be wrong about correct paperwork. Read the finding before you "
            f"rewrite the artifact to satisfy it. Reproduce with: {reproduce}",
        )

    detail = proc.stderr.strip() or f"check-job-spec exited {proc.returncode}"
    return _join_sentence(
        detail,
        "Fix that before spending an opus auditor on a defect a script "
        f"already proved. Reproduce with: {reproduce}",
    )


def _log_dep_gate_gap(tid, detail):
    """Best-effort record that ready-set.py couldn't be loaded, so a worker
    dispatched with the dependency gate un-consulted for `tid`. Same path
    resolution and bare except Exception: pass posture as _log_gate_gap
    above—this is what keeps an allow-through-on-missing-module auditable
    instead of silent."""
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(_lib.state_path("log", "gate-gaps.log"), "a", encoding="utf-8") as f:
            f.write(
                f"{ts} | dep-gate | {tid} | ready-set.py unavailable "
                f"({detail}); worker dispatched with the dependency gate "
                "un-run\n"
            )
    except Exception:
        pass


_READY_SET_MODULE = None
_READY_SET_LOAD_ATTEMPTED = False
_READY_SET_LOAD_REASON = None  # set only when load fails; see _load_ready_set

# The three names _dep_gate_block calls on a loaded module. All three predate
# #135 individually, but #135 is what first calls them from here—a project's
# copied-in scripts/ready-set.py can be old enough to define none of them
# (main, pre-#135, has read_task and TaskParseError but no unmet_deps at
# all), and exec_module() alone can't catch that: the file loads cleanly,
# the AttributeError only fires on the first call. Checked as a set, not
# just unmet_deps, so a script old enough to be missing all three still gets
# one clear "version skew" message instead of a coincidentally-passing
# hasattr on the one this docstring happened to name.
_REQUIRED_READY_SET_ATTRS = ("read_task", "unmet_deps", "TaskParseError")


def _load_ready_set():
    """ready-set.py, loaded by path and cached at module level so repeated
    dispatches in one process don't re-exec it. Copies the `_load_module`
    idiom ready-set.py itself uses at its own top (for check-diff-scope.py):
    the filename has a hyphen, so it can't be imported the normal way.

    Returns None—never raises—if the file is missing, it (or anything it
    transitively imports, e.g. its own check-diff-scope.py) fails to load,
    OR it loaded fine but is missing one of _REQUIRED_READY_SET_ATTRS. That
    last case is version skew, not a load failure: install.py never upgrades
    a project's copied-in .agent-guild/ payload, so a repo can run hooks
    newer than its own scripts/, and a pre-#135 ready-set.py exec_modules
    without error—it simply has no unmet_deps to call. Left unguarded, the
    very first dep-gated dispatch raises AttributeError, which _lib.run's
    fail-loud contract turns into a hard block of every worker on a task
    with deps, with nothing written to gate-gaps.log—exactly the silent,
    unrecoverable failure the missing-module case already knows how to fail
    open from. `_READY_SET_LOAD_REASON` records which case this was so the
    caller's message can name version skew specifically, rather than folding
    it into the generic "missing or failed to load."

    An old ready-set.py never proposes speculative dispatch in the first
    place, so a gate built to catch a bad speculation has nothing to catch
    there—allowing through is safe by construction, not a shortcut."""
    global _READY_SET_MODULE, _READY_SET_LOAD_ATTEMPTED, _READY_SET_LOAD_REASON
    if _READY_SET_MODULE is not None or _READY_SET_LOAD_ATTEMPTED:
        return _READY_SET_MODULE
    _READY_SET_LOAD_ATTEMPTED = True
    path = os.path.join(_lib.project_dir(), ".agent-guild", "scripts", "ready-set.py")
    try:
        spec = importlib.util.spec_from_file_location(
            "dispatch_guard_ready_set", path
        )
        if spec is None or spec.loader is None:
            _READY_SET_LOAD_REASON = "missing"
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        _READY_SET_LOAD_REASON = "missing"
        return None
    missing_attrs = [a for a in _REQUIRED_READY_SET_ATTRS if not hasattr(module, a)]
    if missing_attrs:
        _READY_SET_LOAD_REASON = "skew:" + ", ".join(missing_attrs)
        return None
    _READY_SET_MODULE = module
    return module


def _dep_gate_block(tid, task):
    """None if a worker dispatch on `tid` is legal with respect to its deps,
    else the message for _lib.block(). Worker-path only; the position in
    main() (right after the status≠assigned check, before the executor
    match) is deliberate—a wrong status is the more fundamental defect and
    its own message already tells the orchestrator how to fix it.

    Fast path: an empty or absent `deps` skips the gate entirely, so most
    tasks pay nothing for it.

    Otherwise this evaluates ready-set.py's dep_unmet_reason/unmet_deps
    (frozen interface, #135)—a dep counts as a build input once it's
    complete, or at needs-check/checking with all of ITS OWN deps
    complete (one level of speculation)—against a minimal two-level `tasks`
    dict: the dispatched task, its deps, and those deps' own deps, which is
    as deep as the predicate ever looks.

    Two failure modes get opposite postures, and that split is the point:
      - ready-set.py missing, or it (or a transitive import) failing to
        load: ALLOW the dispatch through (see _load_ready_set's docstring).
      - a dep task FILE that's missing or unparseable: BLOCK, naming the
        file. That's the orchestrator's data to fix, not an infrastructure
        gap, so conflating the two would hide a real defect behind the
        payload-freeze allowance meant for a different problem.
    """
    deps = task.get("deps")
    if isinstance(deps, str):
        deps = [deps] if deps.strip() else []
    if not deps:
        return None

    module = _load_ready_set()
    if module is None:
        if isinstance(_READY_SET_LOAD_REASON, str) and _READY_SET_LOAD_REASON.startswith("skew:"):
            attrs = _READY_SET_LOAD_REASON.split(":", 1)[1]
            situation = (
                f"loaded but is missing {attrs} (version skew: this "
                "project's copied-in scripts/ready-set.py predates #135's "
                "dependency-gate exports)"
            )
        else:
            situation = "is missing or failed to load"
        _log_dep_gate_gap(tid, situation)
        sys.stderr.write(
            f"dispatch-guard: ready-set.py {situation}—the "
            f"dependency gate did not run for {tid}. Logged to "
            ".agent-guild/state/log/gate-gaps.log; the worker is dispatched "
            "unchecked.\n"
        )
        return None

    tasks = {}
    try:
        tasks[tid] = module.read_task(_lib.task_file(tid))
        for dep_id in deps:
            if dep_id in tasks:
                continue
            dep_task = module.read_task(_lib.task_file(dep_id))
            tasks[dep_id] = dep_task
            for grand_id in dep_task.get("deps") or []:
                if grand_id not in tasks:
                    tasks[grand_id] = module.read_task(_lib.task_file(grand_id))
    except module.TaskParseError as e:
        return (
            f"{tid}'s dep graph couldn't be read: {e}. That's data to fix "
            f"in the task file, not an infrastructure gap—repair it, then "
            f"dispatch the worker on {tid} again."
        )

    unmet = module.unmet_deps(tasks[tid], tasks)
    if not unmet:
        return None
    first = unmet[0].split()[0]
    return (
        f"{tid}'s deps aren't ready to build on: {', '.join(unmet)}. A "
        "worker dispatches when every dep is complete, or is at "
        "needs-check/checking with all of ITS deps complete (one level of "
        "speculation). Wait—ready-set.py offers this task the moment that "
        f"holds; if {first} is in rework, drive its retry first."
    )


def _stamp_audited_content():
    """Fingerprint the constitution this audit is being sent to read, against
    the round the auditor is about to write (#110).

    Stamped at dispatch, which is the only moment both hosts share. A Codex
    auditor runs read-only and returns its verdict for the orchestrator to
    persist, so a stamp written when the subagent returns would never exist
    there and the gate could never open. Predicting the round costs nothing if
    the prediction is wrong: the stamp lands on a stem no verdict occupies, and
    the gate keeps refusing.

    It also means only a round that was actually commissioned carries a
    digest—an auditor that returns without writing a verdict leaves the
    previous round's stamp alone, instead of laundering unaudited text into it.

    DEC-audit gets no stamp. Task files change status all job long, so a digest
    over tasks/ would go stale on the first transition; decomposition staleness
    needs a normalized digest nobody has specified yet.

    Best-effort, like _log and mark_in_flight above: a write that fails leaves
    the round unstamped, which refuses the next worker with a message naming
    the missing stamp. Raising instead would wedge the job, since this runs on
    the one dispatch that can reopen both gates—and `verdicts/` genuinely can
    be absent here, because archiving a finished job moves it."""
    digest = _lib.file_sha256(_lib.state_path("constitution.md"))
    if digest is None:
        return
    n = _lib.next_audit_round("CON-audit")
    stamp = _lib.audit_stamp_path(_lib.state_path("verdicts", f"CON-audit-r{n}.md"))

    # Two auditors commissioned for the same round read different documents if
    # the constitution moved between them, and only one of them files the
    # verdict. Overwriting would let the second dispatch's bytes vouch for the
    # first auditor's PASS, so the earlier stamp stands and whichever verdict
    # lands is measured against the text that was audited first. Wrong-but-
    # closed: if the later auditor is the one that files, its PASS reads as
    # stale and costs another round.
    if os.path.exists(stamp) and any(
        marker.startswith("CON-audit--") for marker in _lib.in_flight()
    ):
        return

    try:
        os.makedirs(os.path.dirname(stamp), exist_ok=True)
        with open(stamp, "w", encoding="utf-8") as f:
            f.write(digest + "\n")
    except OSError:
        pass


def main(data):
    # Jurisdiction (see _lib's design rules). An auditor dispatch carries no
    # task file to check, so it clears legality in any repo and reaches _log
    # and mark_in_flight below—enough to write state/ somewhere that never ran
    # init, or that ran it and had every payload file removed since (#212). A
    # worker dispatch can't get that far; the auditor path is the reachable one.
    if not _lib.guild_initialized():
        return 0

    # Intended scope: no in_subagent no-op here, and none is needed. Unlike
    # stop-gate or orchestrator-write-guard, this hook doesn't constrain the
    # orchestrator's own turn—it constrains every Task/Agent dispatch, wherever
    # it originates. A nested guild dispatch (one subagent spinning up another)
    # has to carry the same Task-ID/Audit-ID and pass the same legality checks
    # as a top-level one, so this gate deliberately fires inside subagents too.
    ti = data.get("tool_input", {}) or {}

    # A followup re-tasks an agent that already exists, so it names no agent
    # type and carries no readable prompt: its message is encrypted like every
    # other Codex dispatch message. All it names is the target's agent path,
    # built from the `task_name` of the spawn that created it. If any segment
    # of that path parses as a guild id, work is being handed to a guild agent
    # behind this gate's back, skipping every check below. SubagentStop still
    # fires afterward, so the return gate ends up judging work no dispatch
    # gate ever authorized. Refusal is the only move left, since there's
    # nothing here to check the call against.
    target = ti.get("followup_target")
    if target is not None:
        for segment in str(target).split("/"):
            kind, ident = _lib.bare_id(segment)
            if kind is None:
                continue
            wire = ident.replace("-", "_").lower()
            return _lib.block(
                f"Re-tasking {ident}'s agent through followup_task is not "
                "allowed. This call names no agent type and its message is "
                "encrypted, so none of the dispatch checks can run against "
                "it—yet the return gate will still judge whatever comes back. "
                "Spawn a fresh agent instead, with task_name set to a name no "
                f"dispatch in this session has used yet ({wire}_r0_checker, "
                "say). One name per dispatch, not one per task."
            )
        return 0

    raw = ti.get("subagent_type", "")
    agent = _lib.bare_agent(raw)
    if agent not in _lib.GUILD_AGENTS:
        return 0

    prompt = ti.get("prompt", "") or ""
    override = (ti.get("model") or "").strip().lower()

    # Two mechanisms carry the same id, because one host makes the other
    # impossible: Codex encrypts the dispatch `message` before any hook runs,
    # so a labelled line in the prose has nothing to match against. There the
    # adapter lifts the dispatcher-set `task_name` into `dispatch_id`, which is
    # readable at dispatch and again at return (#71). The structured field wins
    # where both exist—it's the one the dispatcher set deliberately.
    kind, ident = _lib.bare_id(ti.get("dispatch_id"))
    if kind is None:
        # Line-anchored only (see _line_anchored_ids above), not
        # _lib.labeled_ids: a prompt commonly quotes the orchestrator contract
        # for context, and .agent-guild/CLAUDE.md itself contains the literal
        # `Audit-ID: CON-audit` mid-sentence. Matching that unanchored used to
        # make any dispatch whose prompt quoted the contract collide with its
        # own real Task-ID line and get refused for an "ambiguity" that was
        # never there.
        found = _line_anchored_ids(prompt)
        # Earliest-line match wins (matches _lib._id_in's earliest-position
        # rule, one level coarser—by line instead of by character offset,
        # which line-anchoring makes the natural granularity). But two or
        # more DISTINCT line-anchored ids are ambiguous on their face,
        # whether they're the same kind (two separate Task-ID: lines) or
        # different kinds (a Task-ID: line and an Audit-ID: line)—
        # positional tie-breaking would silently pick one and hide the
        # authoring mistake from the dispatcher who could still fix it.
        # "Distinct" is by (kind, id): the SAME id repeated on two lines
        # (an escalation note re-stating the dispatch's own Task-ID, say)
        # isn't a mistake and shouldn't block. This is the one place in the
        # id-resolution path where blocking on ambiguity is right: a human
        # (or the orchestrator) is about to send the dispatch, so a block
        # here is actionable in a way the same ambiguity is NOT at return
        # time (see _lib.ident_for_return / subagent-return.py, which
        # deliberately never blocks on it).
        distinct = []
        seen = set()
        for k, i, _lineno in found:
            if (k, i) not in seen:
                seen.add((k, i))
                distinct.append((k, i))
        if len(distinct) > 1:
            label = {"task": "Task-ID", "audit": "Audit-ID", "audition": "Audition-ID"}
            named = " and ".join(f"{label[k]} {i}" for k, i in distinct)
            return _lib.block(
                f"Dispatch to {agent} carries more than one labeled id as "
                f"separate lines in its prompt: {named}. A quoted or "
                "mid-sentence mention doesn't count toward this—only a line "
                "that opens with the label does. Keep exactly one labeled id "
                "per dispatch."
            )
        if found:
            kind, ident, _lineno = found[0]

    # Audition path: a tryout runs outside the lifecycle—no task file, no tier,
    # no CON-audit precondition. An Audition-ID is enough to log and pass; the
    # battery's score.py judges the output, not this gate.
    if kind == "audition":
        _log(raw, ident, override or _lib.DEFAULT_MODEL[agent])
        _lib.mark_in_flight(ident, agent)
        return 0

    # 1. The dispatch must name what it's working on.
    if kind is None:
        want = "Audit-ID: CON-audit" if agent == "auditor" else "Task-ID: T-NNN"
        if str(data.get("hook_host", "")).strip().lower() == "codex":
            # Underscores, not the canonical hyphen: this host rejects a
            # task_name outside [a-z0-9_], so quoting `T-NNN` here would send
            # the operator to fix one block by tripping a different one.
            bare = "con_audit" if agent == "auditor" else "t_nnn"
            return _lib.block(
                f"Dispatch to {agent} carries no readable id. This host "
                f"encrypts the dispatch message, so set task_name to `{bare}` "
                "instead (lowercase and underscored, which is all this host "
                "accepts there). That field survives to the return gate, "
                "which is what identifies this work when it finishes."
            )
        return _lib.block(
            f"Dispatch to {agent} has no id line. Put `{want}` in the prompt so "
            "the return gate can identify this subagent's work when it finishes."
        )

    # Auditor path: id is CON-audit / DEC-audit, no task file, no tier logic.
    if agent == "auditor":
        if kind != "audit":
            return _lib.block(
                f"Dispatch to auditor names {ident}, but the auditor takes an "
                "Audit-ID (CON-audit or DEC-audit). Workers and checkers take "
                "a Task-ID."
            )
        job_spec_msg = _job_spec_block(ident)
        if job_spec_msg:
            return _lib.block(job_spec_msg)
        if ident == "CON-audit":
            _stamp_audited_content()
        _log(raw, ident, override or _lib.DEFAULT_MODEL[agent])
        # Recorded so the return gate can refuse an auditor that filed
        # nothing at the round it was commissioned for, instead of
        # validating whatever the previous round's file still holds and
        # approving a verdict this auditor never wrote (#175). Computed here
        # rather than trusted from the return, because a read-only Codex
        # auditor's inline verdict never touches disk on its own—the round
        # has to come from something the dispatch itself pinned down.
        #
        # _stamp_audited_content() two lines up computes the same round for
        # CON, and nothing writes a verdict between the two calls, so they
        # agree. DEC gets no stamp (task files churn too fast for one to
        # mean anything) but does get this marker, which is why the marker
        # is the general mechanism and the stamp is CON-only.
        _lib.mark_in_flight(ident, agent, audit_round=_lib.next_audit_round(ident))
        return 0

    tid = ident if kind == "task" else None
    if tid is None:
        return _lib.block(
            f"Dispatch to {agent} names an Audit-ID but {agent} is not the "
            "auditor. Workers and checkers take a Task-ID."
        )

    task = _lib.read_task(tid)
    if task is None:
        return _lib.block(
            f"Dispatch to {agent} references {tid}, but .agent-guild/state/tasks/{tid}.md "
            "does not exist. Create the task before dispatching."
        )

    # Ahead of the role split on purpose: a task that cites clauses and names
    # no check is undispatchable to anyone. Sending the worker means building
    # against a standard nothing will measure; sending the checker means a
    # verdict derived from an empty check list.
    defect = _lib.unverifiable(tid, task)
    if defect:
        return _lib.block(defect)

    status = str(task.get("status", "")).strip()
    effective_model = override or _lib.DEFAULT_MODEL[agent]

    if agent in _lib.CHECKER_AGENTS:
        if status != "checking":
            return _lib.block(
                f"{tid} is '{status}', not 'checking'. Set status to checking "
                "and update the task before dispatching its checker."
            )
        # Deliberate: this branch never reads the task's `checker` field, so
        # a dispatch is legal on ANY checking-status task regardless of which
        # in-family checker is named as checker of record. That's what lets
        # an opted-in checker-courier run alongside the checker of record
        # rather than in place of it.
        #
        # The courier used to be exempt from the `checking` requirement,
        # because a crossing debt could outlive the status that created it
        # and had to stay collectable on a task the orchestrator had already
        # moved on from. #167 retired the debt, so the exemption has nothing
        # left to protect and the courier is held to the same status as every
        # other checker.
        if agent == "checker-courier":
            if override:
                return _lib.block(
                    f"Dispatch to checker-courier for {tid} carries a model "
                    f"override ({override!r}). Drop the override—the courier "
                    "runs its host-selected lane and pinned far-side model."
                )
            if "workspace-write" in prompt or "danger-full-access" in prompt:
                return _lib.block(
                    f"Dispatch to checker-courier for {tid} requests "
                    "workspace-write or danger-full-access. The lane is "
                    "read-only by contract; drop the request."
                )
            lane = _lib.courier_lane(data)
            effective_model = lane
            if _lib.lane_exhausted(lane):
                return _lib.block(
                    f"checker-courier's '{lane}' lane is exhausted "
                    f"(.agent-guild/state/exhausted/{lane} exists). Nothing is "
                    f"substituted: {tid}'s checker of record ran before the "
                    "courier went out, so its verdict already stands and no "
                    "retry budget moves. The sentinel is user-cleared, like "
                    "PAUSED."
                )
        _log(raw, tid, effective_model)
        _lib.mark_in_flight(tid, agent)
        return 0

    # Worker path. The auditor and checker paths returned above, so both gates
    # below refuse workers only—an audit whose own gate is shut can still be
    # dispatched to reopen it.
    ok, reason = _lib.audit_gate(
        "CON-audit", artifact_path=_lib.state_path("constitution.md")
    )
    if not ok:
        return _lib.block(reason)

    # No task-file check needed: the missing-task block above already refused
    # a dispatch naming one that doesn't exist, so #161's "a job that has task
    # files" precondition holds by construction here.
    ok, reason = _lib.audit_gate("DEC-audit")
    if not ok:
        return _lib.block(reason)

    if status != "assigned":
        return _lib.block(
            f"{tid} is '{status}', not 'assigned'. A worker runs only on an "
            "assigned task. If this is rework, set status back to assigned "
            "first; if it's a fresh task, move it pending → assigned."
        )

    dep_msg = _dep_gate_block(tid, task)
    if dep_msg:
        return _lib.block(dep_msg)

    executor = str(task.get("executor", "")).strip()
    if executor and agent != executor:
        return _lib.block(
            f"{tid} names executor '{executor}', but this dispatch is to "
            f"'{agent}'. Escalation bumps the model, not the agent—dispatch "
            f"'{executor}' with a model override, or fix the task's executor."
        )

    tier = str(task.get("executor_model", "")).strip().lower()
    if tier and effective_model != tier:
        return _lib.block(
            f"{tid} is at tier '{tier}', but this dispatch would run on "
            f"'{effective_model}'. Pass model:'{tier}' on the Agent call so the "
            "model matches the task's current tier (an escalation that updated "
            "executor_model but not the dispatch is the usual cause)."
        )

    try:
        retries = int(str(task.get("retries", "0")).strip() or "0")
        max_retries = int(str(task.get("max_retries", "2")).strip() or "2")
    except ValueError:
        retries, max_retries = 0, 2

    if retries > max_retries:
        if tier == "fable":
            return _lib.block(
                f"{tid} has exhausted the top (fable) tier. Do not dispatch "
                "further—surface this to the user, or enrich the spec and "
                "reset. The ladder has no rung above fable."
            )
        return _lib.block(
            f"{tid} has spent its retry budget at tier '{tier}' "
            f"(retries {retries} > max {max_retries}). Escalate: bump "
            "executor_model to the next tier, reset retries to 0, append an "
            "entry to `escalations`, and log it to .agent-guild/state/log/escalations.log."
        )

    _log(raw, tid, effective_model)
    _lib.mark_in_flight(tid, agent)
    return 0


if __name__ == "__main__":
    _lib.run("dispatch-guard", main)
