#!/usr/bin/env python3
"""DEC-audit r1 apparatus: build a reference implementation of #193's three
linter changes from the constitution + T-001's excerpt alone, then build the
attack variants that test whether each clause's check discriminates.

usage: build_ref.py <base-tree> <dest-tree> <variant>

Variants
  refA   modifier walk INSIDE _governs_plural_noun, bounded at 3 modifiers;
         R21 first in run_rules, runs under both audit ids; backtick-quoted
         anchor.
  refB   modifier walk in the CALLER find_r10_violation, unbounded; R21 just
         ahead of rule_R4; SKIPPED under --audit-id CON-audit; !r-quoted
         anchor, "on that same line" when the anchor shares the citing line.
  vC1    refA with the walk keyed to a fixed six-word adjective allowlist.
  vC2    refA with the walk widened to any plural later on the line.
  vC3a   refA with R21 reading the task's own check_method paraphrase.
  vC3b   refA with R21 moved behind rule_R10 (behind two heuristics).
  vC3c   refA with R21 naming every cited clause rather than the offender.
  vC4    refA with R21 firing on both routings.
  vC5a   refA with the anchor replaced by its length (numbers all intact).
  vC5b   refA with R2's absent-anchor silence guard replaced by a report.
  vC8    refA plus a third-party import.
  vSeam  refA with r2_anchor_message's parameter renamed `matched`.
  vNoSeam refA with the R2 diagnostic built inline, no named seam.
"""
import os
import re
import shutil
import sys

LINTER = ".agent-guild/scripts/check-job-spec.py"

STRICT_PREDICATE = '''def _governs_plural_noun(text, match):
    tail = text[match.end():].lstrip()
    return re.match(r"[A-Za-z][A-Za-z-]*s\\b", tail) is not None
'''

# --- reading A: the walk lives in the predicate, bounded --------------------
PREDICATE_A = '''_R10_PLURAL_RE = re.compile(r"[A-Za-z][A-Za-z-]*s\\b")
_R10_WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]*\\b")
# Three is enough for "four further load-bearing rules" with room to spare,
# and a bound is what keeps the walk from wandering into an unrelated plural
# further down the line (C-2's failing example).
_R10_MAX_MODIFIERS = 3


def _governs_plural_noun(text, match):
    tail = text[match.end():].lstrip()
    for _ in range(_R10_MAX_MODIFIERS + 1):
        if _R10_PLURAL_RE.match(tail):
            return True
        m = _R10_WORD_RE.match(tail)
        if not m:
            return False
        tail = tail[m.end():].lstrip()
    return False
'''

# --- reading B: the walk lives in the caller, unbounded --------------------
CALLER_B_HELPER = '''class _R10EndAt:
    """A stand-in for a regex match, carrying only the end offset the strict
    predicate reads. Lets the caller re-ask the untouched predicate at each
    position past a run of modifiers."""

    def __init__(self, end):
        self._end = end

    def end(self):
        return self._end


_R10_WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]*")


def _r10_noun_reachable(text, match):
    """The count governs a plural noun, allowing any run of modifier words
    between the two. The adjacency decision is made HERE; the predicate
    itself is untouched."""
    pos = match.end()
    while True:
        if _governs_plural_noun(text, _R10EndAt(pos)):
            return True
        tail = text[pos:]
        lead = len(tail) - len(tail.lstrip())
        m = _R10_WORD_RE.match(tail.lstrip())
        if not m:
            return False
        pos += lead + m.end()
'''

# --- allowlist variant (C-1's attack) --------------------------------------
PREDICATE_VC1 = '''_R10_PLURAL_RE = re.compile(r"[A-Za-z][A-Za-z-]*s\\b")
_R10_MODIFIERS = {"further", "key", "new", "separate", "brief", "additional"}


def _governs_plural_noun(text, match):
    tail = text[match.end():].lstrip()
    for _ in range(4):
        if _R10_PLURAL_RE.match(tail):
            return True
        m = re.match(r"[A-Za-z][A-Za-z-]*\\b", tail)
        if not m or m.group(0).lower() not in _R10_MODIFIERS:
            return False
        tail = tail[m.end():].lstrip()
    return False
'''

# --- any-plural-on-the-line variant (C-2's failing example verbatim) -------
PREDICATE_VC2 = '''_R10_PLURAL_RE = re.compile(r"[A-Za-z][A-Za-z-]*s\\b")


def _governs_plural_noun(text, match):
    tail = text[match.end():]
    return _R10_PLURAL_RE.search(tail) is not None
'''

# --- R2 seam ---------------------------------------------------------------
SEAM_A = '''def r2_anchor_message(label, src_line, path, lineno, actual_line,
                      anchor, anchor_line):
    """R2's diagnostic. Named, and taking the matched text as `anchor`, so a
    check can strip the anchor while leaving R2's older assertions standing
    (the constitution's C-9 requires the seam by name)."""
    where = ("on that same line" if anchor_line == src_line
             else f"at {label}:{anchor_line}")
    return (
        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
        f"but the quoted code is at {path}:{actual_line}. "
        f"The anchor this citation was checked against is `{anchor}`, {where}"
    )
'''

SEAM_B = '''def r2_anchor_message(label, src_line, path, lineno, actual_line,
                      anchor, anchor_line):
    where = ("on that same line" if anchor_line == src_line
             else f"on {label} line {anchor_line}")
    return (
        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
        f"but the quoted code is at {path}:{actual_line}; the anchor matched "
        f"was {anchor!r}, {where}"
    )
'''

SEAM_VC5A = '''def r2_anchor_message(label, src_line, path, lineno, actual_line,
                      anchor, anchor_line):
    where = ("on that same line" if anchor_line == src_line
             else f"at {label}:{anchor_line}")
    return (
        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
        f"but the quoted code is at {path}:{actual_line}. "
        f"The anchor this citation was checked against has anchor length "
        f"{len(anchor)}, {where}"
    )
'''

SEAM_VSEAM = '''def r2_anchor_message(label, src_line, path, lineno, actual_line,
                      matched, anchor_line):
    where = ("on that same line" if anchor_line == src_line
             else f"at {label}:{anchor_line}")
    return (
        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
        f"but the quoted code is at {path}:{actual_line}. "
        f"The anchor this citation was checked against is `{matched}`, {where}"
    )
'''

SPAN_HELPER = '''def nearest_anchor_span(text, citation_offset, exclude):
    """(content, start, end) for the anchor `nearest_anchor` picks, or
    (None, None, None). Selection is byte-for-byte the #132 heuristic; this
    only keeps the offset so the diagnostic can say where the anchor sits."""
    sent_start, sent_end = sentence_bounds(text, citation_offset)
    best_dist, best = None, (None, None, None)
    for start, end, content in anchor_spans(text):
        if content == exclude or start < sent_start or end > sent_end:
            continue
        dist = start - citation_offset if start >= citation_offset else citation_offset - end
        if best_dist is None or dist < best_dist:
            best_dist, best = dist, (content, start, end)
    return best
'''

R2_OLD_LOOKUP = """                anchor = nearest_anchor(text, offset, f"{path}:{lineno}")
                if anchor is None:
                    continue  # nothing nearby to check this citation against"""

R2_NEW_LOOKUP = """                anchor, anchor_start, _anchor_end = nearest_anchor_span(
                    text, offset, f"{path}:{lineno}")
                if anchor is None:
                    continue  # nothing nearby to check this citation against"""

R2_OLD_RETURN = """                if actual_line is not None:
                    return (
                        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
                        f"but the quoted code is at {path}:{actual_line}"
                    )"""

R2_NEW_RETURN = """                if actual_line is not None:
                    return r2_anchor_message(
                        label, src_line, path, lineno, actual_line,
                        anchor, line_of(anchor_start),
                    )"""

R2_NEW_RETURN_INLINE = """                if actual_line is not None:
                    _al = line_of(anchor_start)
                    _where = ("on that same line" if _al == src_line
                              else f"at {label}:{_al}")
                    return (
                        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
                        f"but the quoted code is at {path}:{actual_line}. "
                        f"The anchor this citation was checked against is "
                        f"`{anchor}`, {_where}"
                    )"""

R2_SILENCE_GUARD = """                # The anchor text is absent from the WHOLE target file, not
                # just the cited line. That's evidence this span isn't this
                # citation's anchor at all—an unrelated excerpt sitting in
                # the same sentence—not evidence the citation is wrong; a
                # real drift case always leaves the quoted code findable
                # somewhere in the file it was quoted from.
                continue"""

R2_SILENCE_BROKEN = """                return r2_anchor_message(
                    label, src_line, path, lineno, lineno,
                    anchor, line_of(anchor_start),
                )"""

# --- R21 -------------------------------------------------------------------
R21_RULE = '''def rule_R21(ctx, audit_id):
    """The routing table assigns a checker by clause KIND. A
    checker-deterministic agent runs scripts and exercises no judgment, so a
    `checker-judgment:` rubric handed to it cannot be applied at all and the
    task comes back carrying a verdict nobody derived. Only that direction is
    harmful; the reverse has house precedent.

    The kind is read from the constitution, never from the task's own
    `check_method` paraphrase—a paraphrase can disagree with the clause it
    names, and a rule reading it reports the wrong clause on any task citing
    several.
    """
    for task in ctx.tasks:
        if (task.checker or "").strip() != "checker-deterministic":
            continue
        for cid in task.clauses:
            clause = ctx.clauses.get(cid)
            if clause is None:
                continue
            kind, _rubric = classify_check_text(clause.check_text)
            if kind == "judgment":
                return (
                    f"R21 checker-routing: {task.label} declares "
                    f"checker: checker-deterministic but cites {cid}, whose "
                    f"check is a checker-judgment: rubric that agent cannot "
                    f"apply"
                )
    return None
'''

R21_RULE_VC3A = '''def rule_R21(ctx, audit_id):
    for task in ctx.tasks:
        if (task.checker or "").strip() != "checker-deterministic":
            continue
        _pre, segments = find_segments(task.check_method_text)
        for cid, _start, value in segments:
            kind, _rubric = classify_check_text(value)
            if kind == "judgment":
                return (
                    f"R21 checker-routing: {task.label} declares "
                    f"checker: checker-deterministic but cites {cid}, whose "
                    f"check is a checker-judgment: rubric that agent cannot "
                    f"apply"
                )
    return None
'''

R21_RULE_VC3C = '''def rule_R21(ctx, audit_id):
    for task in ctx.tasks:
        if (task.checker or "").strip() != "checker-deterministic":
            continue
        judgment = [
            cid for cid in task.clauses
            if ctx.clauses.get(cid) is not None
            and classify_check_text(ctx.clauses[cid].check_text)[0] == "judgment"
        ]
        if judgment:
            named = ", ".join(task.clauses)
            return (
                f"R21 checker-routing: {task.label} declares "
                f"checker: checker-deterministic while citing {named}"
            )
    return None
'''

R21_RULE_VC4 = '''def rule_R21(ctx, audit_id):
    for task in ctx.tasks:
        checker = (task.checker or "").strip()
        for cid in task.clauses:
            clause = ctx.clauses.get(cid)
            if clause is None:
                continue
            kind, _rubric = classify_check_text(clause.check_text)
            want = "checker-judgment" if kind == "judgment" else "checker-deterministic"
            if checker and checker != want:
                return (
                    f"R21 checker-routing: {task.label} declares "
                    f"checker: {checker} but cites {cid}, which routes to "
                    f"{want}"
                )
    return None
'''

R21_SKIP_CON = '''    if audit_id == "CON-audit":
        return None
'''


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, t):
    with open(p, "w", encoding="utf-8") as f:
        f.write(t)


def sub_once(src, old, new, what):
    if src.count(old) != 1:
        raise SystemExit(f"build_ref: {what}: expected 1 occurrence, found {src.count(old)}")
    return src.replace(old, new)


def apply_r10(src, mode):
    if mode == "predicate":
        return sub_once(src, STRICT_PREDICATE, PREDICATE_A, "R10 predicate walk")
    if mode == "caller":
        src = sub_once(src, "                    and _governs_plural_noun(stripped, m)",
                       "                    and _r10_noun_reachable(stripped, m)",
                       "R10 caller call site")
        return sub_once(src, STRICT_PREDICATE, STRICT_PREDICATE + "\n\n" + CALLER_B_HELPER,
                        "R10 caller helper")
    if mode == "allowlist":
        return sub_once(src, STRICT_PREDICATE, PREDICATE_VC1, "R10 allowlist")
    if mode == "anyplural":
        return sub_once(src, STRICT_PREDICATE, PREDICATE_VC2, "R10 any-plural")
    raise SystemExit(f"unknown r10 mode {mode}")


def apply_checker_field(src):
    """TaskFile carries no `checker` today. R21 needs it, so parse it beside
    the other frontmatter scalars."""
    src = sub_once(
        src,
        "    def __init__(self, path, label, task_id, title, clauses, deps, artifacts,\n"
        "                 owns, dep_rationale, check_method_text, check_method_map,\n"
        "                 spec_excerpt_text, spec_excerpt_start_line):",
        "    def __init__(self, path, label, task_id, title, clauses, deps, artifacts,\n"
        "                 owns, dep_rationale, check_method_text, check_method_map,\n"
        "                 spec_excerpt_text, spec_excerpt_start_line, checker=\"\"):",
        "TaskFile signature",
    )
    src = sub_once(
        src,
        "        self.spec_excerpt_start_line = spec_excerpt_start_line\n",
        "        self.spec_excerpt_start_line = spec_excerpt_start_line\n"
        "        # R21 reads this against the KIND of each cited clause.\n"
        "        self.checker = checker\n",
        "TaskFile attr",
    )
    src = sub_once(
        src,
        "        spec_excerpt_text=spec_excerpt or \"\", spec_excerpt_start_line=spec_excerpt_start_line,\n",
        "        spec_excerpt_text=spec_excerpt or \"\", spec_excerpt_start_line=spec_excerpt_start_line,\n"
        "        checker=(fm.get(\"checker\") or \"\").strip(),\n",
        "TaskFile construction",
    )
    return src


def apply_r21(src, body, placement, skip_con):
    if skip_con:
        marker = "    for task in ctx.tasks:"
        body = body.replace(marker, R21_SKIP_CON + marker, 1)
    # Define the rule immediately before run_rules.
    src = sub_once(src, "def run_rules(ctx, audit_id, repo_root):",
                   body + "\n\n" + "def run_rules(ctx, audit_id, repo_root):",
                   "R21 definition")
    call = "        lambda: rule_R21(ctx, audit_id),\n"
    if placement == "first":
        src = sub_once(src, "        lambda: rule_R6(ctx, audit_id),\n",
                       call + "        lambda: rule_R6(ctx, audit_id),\n", "R21 placement first")
    elif placement == "before_r4":
        src = sub_once(src, "        lambda: rule_R4(ctx, audit_id),\n",
                       call + "        lambda: rule_R4(ctx, audit_id),\n", "R21 placement before R4")
    elif placement == "after_r10":
        src = sub_once(src, "        lambda: rule_R12(ctx),\n",
                       call + "        lambda: rule_R12(ctx),\n", "R21 placement after R10")
    else:
        raise SystemExit(f"unknown placement {placement}")
    src = sub_once(src, '    "R20": PROOF,\n', '    "R20": PROOF, "R21": PROOF,\n',
                   "RULE_CLASS entry")
    return src


def apply_r2(src, seam, inline=False, break_silence=False):
    src = sub_once(src, "def nearest_anchor(text, citation_offset, exclude):",
                   SPAN_HELPER + "\n\ndef nearest_anchor(text, citation_offset, exclude):",
                   "nearest_anchor_span")
    src = sub_once(src, R2_OLD_LOOKUP, R2_NEW_LOOKUP, "R2 lookup")
    if inline:
        src = sub_once(src, R2_OLD_RETURN, R2_NEW_RETURN_INLINE, "R2 inline return")
    else:
        src = sub_once(src, R2_OLD_RETURN, R2_NEW_RETURN, "R2 return")
        src = sub_once(src, "def check_citation_rules(regions, repo_root, want_rule):",
                       seam + "\n\ndef check_citation_rules(regions, repo_root, want_rule):",
                       "R2 seam")
    if break_silence:
        src = sub_once(src, R2_SILENCE_GUARD, R2_SILENCE_BROKEN, "R2 silence guard")
    return src


VARIANTS = {
    "refA":    dict(r10="predicate", r21=R21_RULE,      place="first",      seam=SEAM_A),
    "refB":    dict(r10="caller",    r21=R21_RULE,      place="before_r4",  seam=SEAM_B,
                    skip_con=True),
    "vC1":     dict(r10="allowlist", r21=R21_RULE,      place="first",      seam=SEAM_A),
    "vC2":     dict(r10="anyplural", r21=R21_RULE,      place="first",      seam=SEAM_A),
    "vC3a":    dict(r10="predicate", r21=R21_RULE_VC3A, place="first",      seam=SEAM_A),
    "vC3b":    dict(r10="predicate", r21=R21_RULE,      place="after_r10",  seam=SEAM_A),
    "vC3c":    dict(r10="predicate", r21=R21_RULE_VC3C, place="first",      seam=SEAM_A),
    "vC4":     dict(r10="predicate", r21=R21_RULE_VC4,  place="first",      seam=SEAM_A),
    "vC5a":    dict(r10="predicate", r21=R21_RULE,      place="first",      seam=SEAM_VC5A),
    "vC5b":    dict(r10="predicate", r21=R21_RULE,      place="first",      seam=SEAM_A,
                    break_silence=True),
    "vC8":     dict(r10="predicate", r21=R21_RULE,      place="first",      seam=SEAM_A,
                    third_party=True),
    "vSeam":   dict(r10="predicate", r21=R21_RULE,      place="first",      seam=SEAM_VSEAM),
    "vNoSeam": dict(r10="predicate", r21=R21_RULE,      place="first",      seam=None,
                    inline=True),
    "vNoR21":  dict(r10="predicate", r21=None,          place=None,         seam=SEAM_A),
    "vNoR10":  dict(r10=None,        r21=R21_RULE,      place="first",      seam=SEAM_A),
}


def main():
    if len(sys.argv) != 4 or sys.argv[3] not in VARIANTS:
        sys.stderr.write(__doc__ + "\n")
        return 3
    base, dest, name = sys.argv[1], sys.argv[2], sys.argv[3]
    cfg = VARIANTS[name]

    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(base, dest, symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__"))

    path = os.path.join(dest, LINTER)
    src = read(path)

    if cfg["r10"]:
        src = apply_r10(src, cfg["r10"])
    if cfg["r21"]:
        src = apply_checker_field(src)
        src = apply_r21(src, cfg["r21"], cfg["place"], cfg.get("skip_con", False))
    src = apply_r2(src, cfg["seam"], inline=cfg.get("inline", False),
                   break_silence=cfg.get("break_silence", False))
    if cfg.get("third_party"):
        src = sub_once(src, "import argparse\n", "import argparse\nimport regex\n",
                       "third-party import")

    write(path, src)
    print(f"built {name} at {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
