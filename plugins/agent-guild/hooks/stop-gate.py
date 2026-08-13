#!/usr/bin/env python3
"""Stop: the orchestrator can't end its turn while tasks are unfinished.

SubagentStop can validate that a worker followed protocol, but a hook can't
dispatch the checker that has to run next. This gate is what compels it: while
any task is non-terminal, the main session is blocked from stopping and handed
the exact next move for each open task. That closes the loop—worker returns,
gate refuses to let the turn end until the checker is dispatched and its verdict
acted on.

Livelock guard: if the same open-task state blocks three times in a row while
stop_hook_active is set, the gate gives up loudly—it writes .agent-guild/state/STALLED.md
naming the stuck tasks and lets the turn end, rather than spinning forever. Any
real progress resets the counter: a status change, a retry change, or a verdict
landing.

A subagent that's genuinely still working is not real progress by that
definition, but it isn't a stall either (#111). _lib.in_flight() names every
dispatch still inside its freshness TTL, and its fresh names ride in the
digest alongside the task/verdict/debt state. A task whose dispatch is still
fresh holds the counter rather than advancing it—dispatching again would
duplicate a subagent already running, and declaring the loop stuck would be
just as wrong. A marker that outlives its TTL is worth nothing: staleness is
what lets the backstop resume on a dead agent without anyone clearing state
by hand.

Waves also fire this gate twice for ONE real blocked turn when both the
plugin's hooks.json and a copy-in settings.json are registered (#41): same
task state, same verdict set, same markers, because nothing has actually
happened between the two firings. The digest alone can't tell that apart from
a genuine second strike, so the state file also persists the main
transcript's byte size. Two firings against an unchanged transcript are one
real block, not two, and the counter holds rather than advancing.

A debt (a courier crossing owed against a verdict of record—see
_lib.second_opinion_debts) held the turn open before whether or not a
courier was actually running against it, which could stall the loop on a
second opinion that, by contract, can never itself decide complete vs.
rework (#124). _partition_debts splits debts into held and in-flight using
the same reservation record dispatch-guard.py/subagent-return.py already
write and promote (_lib.reserve_crossing/crossing_reservation): a FRESH
reservation means a courier is plausibly still running, so that debt drops
out of the block message, STALLED.md, and the early-return check entirely.
Everything else—no reservation, or one gone stale—is held exactly as
before. #100's guarantee weakens deliberately here, from "the crossing
landed" to "the crossing was started."

Presentation, separately from all of the above: this gate shells out to
.agent-guild/scripts/ready-set.py to group ready tasks into one wave, fed
`--running` from the fresh in-flight markers this gate already computes
(#125)—that script is the single host-neutral source of the wave decision,
so a Claude host and a Codex host announce the identical wave from the
identical inputs. This changes only how the block message reads, never
whether it blocks: the underlying open-tasks/debts computation is untouched,
and if ready-set.py is missing, times out, or exits non-zero, the gate
degrades straight back to _next_move's per-task advice for every open
task—the same posture dispatch-guard.py's _job_spec_block takes toward a
stale or slow check-job-spec.py.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

STALL_LIMIT = 3

# A courier crossing's reservation (_lib.reserve_crossing, written at
# dispatch time) counts as "a courier is genuinely running" only within this
# many seconds of its reserved_at stamp—past that, a debt whose courier died
# mid-flight must not stay permanently exempt from blocking the turn.
# AGENT_GUILD_CROSSING_STALE_S is the test seam, same shape as _lib.in_flight's
# AGENT_GUILD_INFLIGHT_STALE_S: it lets a test zero this out instantly instead
# of waiting out a real hour to prove a dead courier's reservation goes stale.
CROSSING_STALE_S_DEFAULT = 3600.0

# Short on purpose (#125): ready-set.py only parses a handful of small task
# files, nothing like check-job-spec.py's full paperwork lint, so there's no
# reason to hold the gate open anywhere near dispatch-guard's 20s budget.
# AGENT_GUILD_READY_SET_TIMEOUT is the same test-only seam as
# AGENT_GUILD_JOB_SPEC_TIMEOUT: it lets one test exercise a real
# subprocess.run() timeout without a real 5s wait for every run of this
# suite.
READY_SET_TIMEOUT_S = float(os.environ.get("AGENT_GUILD_READY_SET_TIMEOUT", "5"))


def _crossing_status(stem, lane, ttl=None):
    """'fresh', 'stale', or 'none' for stem/lane's courier-crossing
    reservation (_lib.reserve_crossing / _lib.crossing_reservation).

    'fresh' means a checker-courier was legally dispatched for this EXACT
    crossing within `ttl` seconds and hasn't necessarily returned yet—so a
    courier is plausibly still running, and the debt shouldn't hold the
    orchestrator's turn open on a check that, by the dual-check regime, can
    never itself decide complete vs. rework. 'stale' means one was
    dispatched but that window lapsed: whatever ran never came back, and the
    debt is held again exactly like 'none' (nothing was ever reserved).

    A record missing `reserved_at`, or carrying a value that won't parse,
    reads as 'none' rather than raising or being treated as perpetually
    fresh—fail toward holding the debt, the same posture
    second_opinion_debts() itself takes on a malformed record.
    """
    record = _lib.crossing_reservation(stem, lane)
    if not record:
        return "none"
    if ttl is None:
        try:
            ttl = float(os.environ.get(
                "AGENT_GUILD_CROSSING_STALE_S", str(CROSSING_STALE_S_DEFAULT)))
        except ValueError:
            ttl = CROSSING_STALE_S_DEFAULT
    try:
        reserved_at = datetime.strptime(
            record["reserved_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
    except Exception:
        return "none"
    age = (datetime.now(timezone.utc) - reserved_at).total_seconds()
    return "fresh" if age <= ttl else "stale"


def _partition_debts(debts):
    """Split second_opinion_debts()'s (task_id, stem, lane) list into
    (held, in_flight). A FRESH reservation means a courier is plausibly
    running against that exact crossing right now, so counting it against
    the orchestrator's turn would stall the loop on a check that can never
    itself decide complete vs. rework. Everything else—no reservation at
    all, or one gone stale—is held: #100's original guarantee weakens
    deliberately here, from "the crossing landed" to "the crossing was
    started," but an unreserved (or abandoned) debt still blocks exactly as
    before.
    """
    held, in_flight = [], []
    for d in debts:
        _tid, stem, lane = d
        if _crossing_status(stem, lane) == "fresh":
            in_flight.append(d)
        else:
            held.append(d)
    return held, in_flight


def _next_move(tid, status, retries, debts, marker_state=None, marker_ts=None):
    # A task can sit at `checking` with its checker of record already landed
    # and only the courier crossing still missing. The generic "act on the
    # verdict" line in `moves` lets a well-behaved orchestrator walk straight
    # past that and call the task complete before the debt registers
    # anywhere, and the debt list in the block message only catches it after
    # the fact—so name the courier here instead. Matched to THIS retry round
    # (not just this task) because an older round's still-open debt from a
    # prior FAIL survives a rework cycle and shouldn't be mistaken for the
    # current round's own crossing. Takes precedence over the marker-based
    # wording below on purpose: a task can reach this branch with its own
    # in-flight marker already cleared (the checker of record already
    # returned), and the debt is still the more specific, more actionable
    # thing to say.
    #
    # `debts` here MUST already be held_debts (main() passes only that): a
    # FRESH courier reservation means one is plausibly still running, and
    # telling the orchestrator to "dispatch checker-courier" against a
    # crossing already in flight would open a duplicate-dispatch window.
    if status == "checking" and any(
        d_tid == tid and d_stem.endswith(f"-r{retries}")
        for d_tid, d_stem, _lane in debts
    ):
        return (
            f"  {tid} [{status}] → its checker of record has landed but the "
            "second opinion hasn't; dispatch checker-courier before "
            "completing."
        )
    # #111: `assigned` and `checking` are exactly the two statuses a task
    # sits at WHILE something is dispatched against it, so they're the two
    # statuses where "nothing has changed" is ambiguous between "nobody has
    # dispatched anything yet" and "a worker/checker is still running." The
    # in-flight marker (see _lib.mark_in_flight/in_flight) disambiguates:
    # fresh means don't dispatch again, absent means dispatch, stale means
    # whatever ran never came back.
    if status in ("assigned", "checking"):
        role = "executor" if status == "assigned" else "checker"
        if marker_state == "fresh":
            return (
                f"  {tid} [{status}] → mid-flight (dispatched {marker_ts}); "
                "do not dispatch another."
            )
        if marker_state == "stale":
            return (
                f"  {tid} [{status}] → its {role} never returned; investigate, "
                "then re-dispatch."
            )
        # An absent marker does NOT mean "nobody has run yet"—subagent-return
        # clears the marker on the way out, so a checker that has already
        # landed its verdict leaves exactly the same absence as one nobody
        # dispatched. The two are told apart by the verdict itself. Only
        # `checking` needs this: the CHECKER writes the verdict but the
        # ORCHESTRATOR moves the status off `checking`, so verdict-landed-and-
        # status-unmoved is the ordinary state of every checked task, and
        # telling the orchestrator to dispatch a second checker there would
        # duplicate a check that already passed. (`assigned` has no such
        # window—the worker moves itself to `needs-check`.)
        if status == "checking" and _verdict_landed_for(tid, retries):
            return (
                f"  {tid} [{status}] → its checker has landed a verdict; act "
                "on it (complete, or copy the diagnosis into rework)."
            )
        return f"  {tid} [{status}] → dispatch the {role}."
    moves = {
        "pending": "assign it and dispatch its executor.",
        "needs-check": "set status to checking and dispatch its checker.",
        "rework": f"copy the checker's diagnosis into ## Rework diagnosis, set "
                  f"status back to assigned (retries {retries}), and re-dispatch "
                  "the same worker.",
        "disputed": "read the dispute, verdict, and artifact yourself and rule; "
                    "append the ruling and set the task to complete or rework.",
    }
    return f"  {tid} [{status}] → {moves.get(status, 'resolve this task.')}"


def _running_ids(fresh_markers):
    """Task/Audit ids behind fresh in-flight markers, deduped and order-
    preserved. A marker stem is `<ident>--<agent>`; ready-set.py wants only
    the ids, since it's the caller's job (not ready-set.py's) to say what's
    already dispatched."""
    out = []
    seen = set()
    for m in fresh_markers:
        ident = m.split("--", 1)[0]
        if ident not in seen:
            seen.add(ident)
            out.append(ident)
    return out


def _compute_wave(fresh_markers):
    """ready-set.py's parsed JSON result, or None on any failure to
    produce one—missing script, timeout, non-zero exit, or unparseable
    stdout. None means "degrade to _next_move for everything," never
    "block less than before": every caller of this treats None exactly
    like an empty wave, so a broken ready-set.py can only ever make the
    message plainer, not the gate looser."""
    script = os.path.join(
        _lib.project_dir(), ".agent-guild", "scripts", "ready-set.py"
    )
    if not os.path.exists(script):
        return None
    cmd = [
        sys.executable,
        script,
        _lib.state_path(),
        "--running",
        *_running_ids(fresh_markers),
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=_lib.project_dir(),
            capture_output=True,
            text=True,
            timeout=READY_SET_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(result, dict) or "wave" not in result:
        return None
    return result


def _wave_block(wave):
    """The unmissable header for a computed wave, or None if it's empty.
    Two or more members is #125's headline case—independent tasks that
    used to get dispatched one at a time purely because nothing said
    otherwise—so that case gets an explicit, hard-to-miss instruction to
    fire them together in a single message."""
    if not wave:
        return None
    lines = []
    if len(wave) >= 2:
        lines.append(
            f"READY WAVE: {len(wave)} tasks have no unmet dependency on each "
            "other right now. Dispatch ALL of them in this ONE message, as "
            "parallel Task tool calls, before doing anything else:"
        )
    else:
        lines.append("Ready to dispatch now:")
    for w in wave:
        lines.append(f"  {w['id']} → dispatch {w['agent']} ({w['reason']}).")
    return "\n".join(lines)


def _state_file():
    return _lib.state_path("log", "stop-gate.state")


def _verdict_landed_for(tid, retries):
    """True if a verdict of record for `tid` at THIS retry round is on disk.

    Round-scoped on purpose, matching the courier-debt branch above: an older
    round's verdict survives a rework cycle, and treating it as this round's
    would tell the orchestrator to act on a verdict that judged a different
    artifact. Lane-suffixed files (`...-r0-codex.json`) are second opinions,
    never the verdict of record, so they don't count.
    """
    for name in _verdicts_landed():
        if not name.startswith(f"{tid}-"):
            continue
        stem = name.rsplit(".", 1)[0]
        if stem.endswith(f"-r{retries}"):
            return True
    return False


def _marker_info(tid, fresh_markers, all_markers):
    """(marker_state, dispatched_at) for tid's in-flight marker: 'fresh' with
    a timestamp, 'stale' with None, or (None, None) if no marker exists at
    all. `fresh_markers`/`all_markers` are pre-computed _lib.in_flight()
    results (default TTL, and an effectively-infinite TTL) so a caller
    walking every open task pays for exactly two directory scans total, not
    one per task. The timestamp comes from opening the named marker directly
    rather than re-listing the directory, which is what keeps that promise."""
    prefix = f"{tid}--"
    hit = next((m for m in sorted(fresh_markers) if m.startswith(prefix)), None)
    if hit is not None:
        try:
            path = _lib.state_path("log", "in-flight", f"{hit}.json")
            with open(path, encoding="utf-8") as f:
                return "fresh", json.load(f).get("dispatched_at")
        except Exception:
            # The marker was fresh a moment ago, so it existed; a read that
            # fails now means a concurrent return cleared it. Still report
            # fresh (the digest already counted it) and just lose the stamp.
            return "fresh", None
    if any(m.startswith(prefix) for m in all_markers):
        return "stale", None
    return None, None


def _transcript_size(data):
    """Byte size of the main-session transcript this Stop event names, or
    None if it's absent/unreadable. The #41 double-registration seam: the
    SAME real Stop event firing this gate twice (once per registered copy)
    hands both firings the identical file at the identical size, which is
    what tells that apart from a genuine second blocked turn (where the
    orchestrator did something in between and the transcript grew)."""
    path = data.get("transcript_path")
    if not isinstance(path, str) or not path:
        return None
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _verdicts_landed():
    """Verdict filenames, which move whenever a check finishes.

    (id, status, retries) can hold still across real work: a task sits at
    `checking` through its checker of record AND its courier second opinion, so
    two verdicts can land without the task tuple changing at all. Counting that
    as "no progress" is what wrote a spurious STALLED.md during the #78 run, and
    it's the same blindness behind #81—on Codex checkers hand their verdicts to
    the parent to write, which stretches the window between status changes and
    trips the backstop sooner. A stem carries task, tier, retry, and lane, so
    the set is a faithful progress signal without reading any file.
    """
    try:
        return sorted(os.listdir(_lib.state_path("verdicts")))
    except OSError:
        # No verdicts dir yet is a legitimate state, not an error—fall back to
        # the task tuple alone rather than letting the gate crash open.
        return []


def _load_state():
    try:
        with open(_state_file(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"digest": None, "count": 0, "transcript_size": None}


def _save_state(digest, count, transcript_size=None):
    try:
        os.makedirs(_lib.state_path("log"), exist_ok=True)
        with open(_state_file(), "w", encoding="utf-8") as f:
            json.dump(
                {"digest": digest, "count": count, "transcript_size": transcript_size},
                f,
            )
    except Exception:
        pass


def main(data):
    # Supported hosts stamp agent_id on a subagent-scoped stop input. A
    # subagent's turn ending is subagent-return's jurisdiction, not this gate's—
    # this gate exists to hold open the ORCHESTRATOR's turn, and a subagent has
    # no say over the orchestrator's open-task picture. No-op unconditionally,
    # before touching open_tasks() or the livelock state file: a subagent Stop
    # must never increment (or reset) the counter that's tracking main-session
    # livelock, or parallel subagents finishing in sequence would trip a
    # spurious STALLED.md with nothing actually stuck.
    if _lib.in_subagent(data):
        return 0

    # Computed before open_tasks()'s early exit below, on purpose: that call
    # drops terminal tasks, so a task the orchestrator already moved to
    # `complete` is invisible to everything past this line—exactly the state
    # the 2026-08-02 Claude run ended in, a completed T-001 with no crossing,
    # and the gate said nothing because nothing here ever looked. A debt
    # survives status changes the open-task picture doesn't, so it has to be
    # checked independently of whether any task is still open.
    debts = _lib.second_opinion_debts(data)
    # A debt whose courier reservation is still FRESH is in-flight, not
    # stuck—see _partition_debts. It never holds the turn, never lands in
    # STALLED.md, and never gets its own debt line; only held_debts does any
    # of that below. in_flight_debts is unused past this line by design: its
    # whole job is to be the set held_debts excludes.
    held_debts, _in_flight_debts = _partition_debts(debts)
    tasks = _lib.open_tasks()
    if not tasks and not held_debts:
        # Clean slate—clear any stale block counter and let the turn end.
        _save_state(None, 0)
        return 0

    # Fresh markers ride in the digest itself, so a dispatch, a return, or a
    # staleness transition (nothing renewing a marker before its TTL lapses)
    # each change it exactly like a status or retry change would (#111).
    fresh_markers = _lib.in_flight()
    digest = json.dumps([sorted(tasks), _verdicts_landed(), held_debts, fresh_markers])
    prev = _load_state()
    stop_active = bool(data.get("stop_hook_active"))
    transcript_size = _transcript_size(data)

    same_digest = digest == prev.get("digest")
    # Held, not reset: a fresh marker on any open task means something is
    # genuinely still running, so an unchanged digest is expected, not a
    # symptom of being stuck. Advancing here would race a legitimate
    # long-running dispatch toward STALLED.md; resetting to 1 would hide a
    # REAL stall that happens to start the moment a marker goes fresh.
    has_fresh_marker_on_open_task = any(
        any(m.startswith(f"{t[0]}--") for m in fresh_markers) for t in tasks
    )
    # Held for a second, distinct reason (#41): the identical transcript size
    # across two firings with an otherwise-unchanged digest means the same
    # real Stop event fired this gate twice (double registration), not that
    # the orchestrator blocked, did nothing, and got blocked again. Only
    # compared when both sides are known—an absent transcript_path (most of
    # this test suite, and any host that doesn't supply one) must fall
    # through to the ordinary advance-or-hold-by-marker logic below, not
    # silently freeze the counter on None == None.
    same_transcript_size = (
        transcript_size is not None
        and prev.get("transcript_size") is not None
        and transcript_size == prev.get("transcript_size")
    )

    if same_digest:
        if has_fresh_marker_on_open_task or same_transcript_size:
            count = int(prev.get("count", 0))  # held: no increment, no reset
        else:
            count = int(prev.get("count", 0)) + 1
    else:
        count = 1

    # Livelock backstop: same unfinished state, already in a continuation loop,
    # tripped the limit. Give up loudly instead of blocking forever.
    if stop_active and same_digest and count >= STALL_LIMIT:
        lines = [
            "# STALLED",
            "",
            f"The stop gate blocked {count} times with no change to these tasks "
            f"and no verdict landing:",
            "",
        ] + [f"- {t[0]} [{t[1]}] retries={t[2]}" for t in tasks] + [
            f"- {d_tid}: second opinion outstanding for {d_stem}-{d_lane}.json"
            for d_tid, d_stem, d_lane in held_debts
        ] + [
            "",
            "The gate has stood down so the turn can end. Investigate by hand: a "
            "checker owing a verdict, a dispute needing a ruling, a second "
            "opinion nobody dispatched, or a task that should be marked "
            "abandoned. Delete this file once resolved.",
        ]
        try:
            with open(_lib.state_path("STALLED.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
        _save_state(digest, count, transcript_size)
        return 0

    _save_state(digest, count, transcript_size)

    all_markers = _lib.in_flight(ttl=float("inf"))

    # Presentation only (#125): ready_result/wave_ids never change which
    # tasks are open or which debts are outstanding—only which of them get
    # folded into the wave announcement instead of an ordinary per-task
    # line. wave_ids stays empty whenever ready-set.py degrades, which
    # collapses this whole block straight back to the pre-#125 behavior:
    # every task gets its _next_move line, nothing gets a wave header.
    ready_result = _compute_wave(fresh_markers)
    wave = ready_result["wave"] if ready_result else []
    wave_ids = {w["id"] for w in wave}

    task_lines = [
        _next_move(*t, held_debts, *_marker_info(t[0], fresh_markers, all_markers))
        for t in tasks
        if t[0] not in wave_ids
    ]
    # Named by the missing FILE, not the bare stem: a debt's `stem` is the
    # verdict-of-record's own name (T-001-sonnet-r0), and printing that alone
    # would point the orchestrator at the file that already exists instead of
    # the lane-suffixed one (T-001-sonnet-r0-codex.json) that's actually
    # missing. A STALE reservation gets different advice than a never-started
    # one: re-dispatch is what actually collects #34's comparison data, so
    # that's offered first, with the waiver named only as the fallback for a
    # dispatch that genuinely can't succeed.
    debt_lines = []
    for d_tid, d_stem, d_lane in held_debts:
        if _crossing_status(d_stem, d_lane) == "stale":
            debt_lines.append(
                f"  {d_tid}: second opinion outstanding—its earlier "
                f"checker-courier dispatch for {d_stem}-{d_lane}.json went "
                "stale before returning; re-dispatch checker-courier, or "
                f"write {d_stem}-{d_lane}.denied if the dispatch cannot "
                "succeed."
            )
        else:
            debt_lines.append(
                f"  {d_tid}: second opinion outstanding—dispatch checker-courier "
                f"to write {d_stem}-{d_lane}.json."
            )
    wave_block = _wave_block(wave)
    body_sections = ([wave_block] if wave_block else []) + [
        "\n".join(task_lines + debt_lines)
    ]
    body = "\n".join(body_sections)
    return _lib.block(
        f"{len(tasks)} task(s) still open and {len(held_debts)} second "
        "opinion(s) outstanding—the turn can't end yet. Next move for each:\n"
        f"{body}\n"
        "Do the next move, then stop again. If you need to hand control back to "
        "the user mid-job, the user can `touch .agent-guild/state/PAUSED`."
    )


if __name__ == "__main__":
    _lib.run("stop-gate", main)
