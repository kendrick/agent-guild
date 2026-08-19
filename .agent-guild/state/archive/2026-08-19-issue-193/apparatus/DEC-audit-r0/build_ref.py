#!/usr/bin/env python3
"""DEC-audit r0 reference implementation builder.

Built from `constitution.md` (C-1..C-9) and the three task excerpts, and from
nothing inferred beyond them. Two readings of the R10 relaxation are produced,
because C-9 blesses both factorings explicitly and T-002's checker will face
whichever one T-001's worker picks:

    refA - relaxation bounded inside `_governs_plural_noun`
    refB - relaxation in the caller, `find_r10_violation`

Usage: build_ref.py <base-tree> <dest-tree> [refA|refB]
"""
import os
import re
import shutil
import sys

LINTER = ".agent-guild/scripts/check-job-spec.py"


def sub_once(text, needle, replacement, what):
    if text.count(needle) != 1:
        raise SystemExit(f"anchor for {what} occurs {text.count(needle)} times, expected 1")
    return text.replace(needle, replacement)


# --- 1. TaskFile learns its `checker` field -------------------------------
# R21 reads the routing declaration; nothing in the shipped parser kept it.

TASKFILE_SIG_OLD = """    def __init__(self, path, label, task_id, title, clauses, deps, artifacts,
                 owns, dep_rationale, check_method_text, check_method_map,
                 spec_excerpt_text, spec_excerpt_start_line):
        self.path = path"""
TASKFILE_SIG_NEW = """    def __init__(self, path, label, task_id, title, clauses, deps, artifacts,
                 owns, dep_rationale, check_method_text, check_method_map,
                 spec_excerpt_text, spec_excerpt_start_line, checker=""):
        self.checker = checker
        self.path = path"""

LOADER_OLD = """        spec_excerpt_text=spec_excerpt or "", spec_excerpt_start_line=spec_excerpt_start_line,
    )"""
LOADER_NEW = """        spec_excerpt_text=spec_excerpt or "", spec_excerpt_start_line=spec_excerpt_start_line,
        checker=(fm.get("checker") or "").strip(),
    )"""

# --- 2. R21 -----------------------------------------------------------------

R21_BODY = '''

# ---------------------------------------------------------------------------
# R21: checker routing. The routing table in `.agent-guild/CLAUDE.md` assigns
# a checker by CLAUSE KIND, and nothing enforced it. Only one direction is
# harmful: a `checker-deterministic` agent runs scripts and exercises no
# judgment, so a rubric handed to one cannot be applied at all. The reverse—a
# `checker-judgment` carrying script clauses—is safe and has house precedent,
# so it gets no rule.
#
# The kind is read from the CONSTITUTION's clause, never from the task's own
# `check_method` paraphrase of it: a task citing several clauses interpolates
# them all into one folded scalar, and a rule reading the paraphrase names
# whichever clause the prose happens to mention rather than the one that
# actually cannot be checked.
# ---------------------------------------------------------------------------

def rule_R21(ctx, audit_id):
    if audit_id == "CON-audit" or not ctx.tasks:
        return None
    for task in ctx.tasks:
        if (task.checker or "").strip() != "checker-deterministic":
            continue
        for cid in task.clauses:
            clause = ctx.clauses.get(cid)
            if clause is None:
                continue
            if clause.check_text.strip().startswith("checker-judgment:"):
                return (
                    f"R21 checker-routing: {task.label} declares "
                    f"checker: checker-deterministic but cites {cid}, whose "
                    "check is a checker-judgment: rubric; that agent runs "
                    "scripts and exercises no judgment, so the rubric cannot "
                    "be applied at all—route this task to checker-judgment, "
                    "or give " + cid + " a script check"
                )
    return None

'''

R21_INSERT_AFTER = """def rule_R8(ctx, audit_id):"""

RULE_CLASS_OLD = '''    "R20": PROOF,
}'''
RULE_CLASS_NEW = '''    "R20": PROOF, "R21": PROOF,
}'''

RUNRULES_OLD = """        lambda: rule_R14(ctx, audit_id),
        lambda: rule_R4(ctx, audit_id),"""
RUNRULES_NEW = """        lambda: rule_R14(ctx, audit_id),
        lambda: rule_R21(ctx, audit_id),
        lambda: rule_R4(ctx, audit_id),"""

# --- 3. R2 anchor diagnostic ------------------------------------------------

NEAREST_OLD = """    sent_start, sent_end = sentence_bounds(text, citation_offset)
    best_dist, best_content = None, None
    for start, end, content in anchor_spans(text):
        if content == exclude or start < sent_start or end > sent_end:
            continue
        dist = start - citation_offset if start >= citation_offset else citation_offset - end
        if best_dist is None or dist < best_dist:
            best_dist, best_content = dist, content
    return best_content
"""
NEAREST_NEW = '''    span = nearest_anchor_span(text, citation_offset, exclude)
    return span[2] if span else None


def nearest_anchor_span(text, citation_offset, exclude):
    """`nearest_anchor`'s pick, with its (start, end) offsets kept so the
    diagnostic can say WHERE in the citing document the anchor sits. The
    selection is #132's, untouched—only what it returns changed."""
    sent_start, sent_end = sentence_bounds(text, citation_offset)
    best_dist, best = None, None
    for start, end, content in anchor_spans(text):
        if content == exclude or start < sent_start or end > sent_end:
            continue
        dist = start - citation_offset if start >= citation_offset else citation_offset - end
        if best_dist is None or dist < best_dist:
            best_dist, best = dist, (start, end, content)
    return best


def r2_anchor_message(label, src_line, path, lineno, actual_line, anchor, anchor_line):
    """R2's diagnostic. Named seam, `anchor` named parameter: C-9 needs to
    remove the anchor text from this message while leaving every older R2
    case standing, and a blunt stub takes those down too."""
    if anchor_line == src_line:
        where = "on that same line"
    else:
        where = f"at {label}:{anchor_line}"
    return (
        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
        f"but the quoted code is at {path}:{actual_line}. The anchor this "
        f"citation was checked against is `{anchor}`, {where}"
    )
'''

R2_CALL_OLD = """                anchor = nearest_anchor(text, offset, f"{path}:{lineno}")
                if anchor is None:
                    continue  # nothing nearby to check this citation against"""
R2_CALL_NEW = """                anchor_span = nearest_anchor_span(text, offset, f"{path}:{lineno}")
                if anchor_span is None:
                    continue  # nothing nearby to check this citation against
                anchor = anchor_span[2]
                anchor_line = line_of(anchor_span[0])"""

R2_MSG_OLD = """                if actual_line is not None:
                    return (
                        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
                        f"but the quoted code is at {path}:{actual_line}"
                    )"""
R2_MSG_NEW = """                if actual_line is not None:
                    return r2_anchor_message(
                        label, src_line, path, lineno, actual_line,
                        anchor=anchor, anchor_line=anchor_line,
                    )"""

# --- 4. R10 adjacency -------------------------------------------------------

R10_PRED_OLD = '''def _governs_plural_noun(text, match):
    tail = text[match.end():].lstrip()
    return re.match(r"[A-Za-z][A-Za-z-]*s\\b", tail) is not None
'''

# refA: the modifier walk lives inside the predicate.
R10_PRED_REFA = '''# Adjectives may sit between the count and the noun it governs: `Four further
# rules constrain how:` counts the same three bullets `Four rules constrain
# how:` does. The walk is BOUNDED (at most three modifiers, letters and
# hyphens only, no punctuation crossed) so the rule still refuses to reach
# down a whole line for any plural it can find—that over-relaxation is what
# C-2's archive sweep exists to catch.
_R10_MODIFIER_LIMIT = 3
_R10_WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]*")


def _governs_plural_noun(text, match):
    tail = text[match.end():].lstrip()
    for _ in range(_R10_MODIFIER_LIMIT + 1):
        m = _R10_WORD_RE.match(tail)
        if not m:
            return False
        if m.group(0).endswith("s"):
            return True
        rest = tail[m.end():]
        if not rest[:1].isspace():
            return False
        tail = rest.lstrip()
    return False
'''

# refB: the predicate stays strict; the caller walks the modifiers and re-asks.
R10_PRED_REFB = '''_R10_MODIFIER_LIMIT = 3
_R10_WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]*")


def _governs_plural_noun(text, match):
    tail = text[match.end():].lstrip()
    return re.match(r"[A-Za-z][A-Za-z-]*s\\b", tail) is not None


class _ShiftedMatch:
    """A stand-in for a regex match whose `end()` has been advanced past one
    modifier, so the strict predicate can be re-asked from the next word."""

    def __init__(self, end):
        self._end = end

    def end(self):
        return self._end


def _governs_plural_noun_through_modifiers(text, match):
    """C-1's relaxation, factored into R10's caller rather than into the
    predicate. The spec's own "Start here" names both sites and C-9 accounts
    for each; this is the second one."""
    if _governs_plural_noun(text, match):
        return True
    end = match.end()
    for _ in range(_R10_MODIFIER_LIMIT):
        tail = text[end:]
        lead = len(tail) - len(tail.lstrip())
        m = _R10_WORD_RE.match(tail, lead)
        if not m:
            return False
        end = end + m.end()
        if _governs_plural_noun(text, _ShiftedMatch(end)):
            return True
    return False
'''

R10_CALL_OLD = """                    and _governs_plural_noun(stripped, m)"""
R10_CALL_REFB = """                    and _governs_plural_noun_through_modifiers(stripped, m)"""


def build(base, dest, flavor):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(base, dest, symlinks=True)
    p = os.path.join(dest, LINTER)
    with open(p, encoding="utf-8") as f:
        src = f.read()

    src = sub_once(src, TASKFILE_SIG_OLD, TASKFILE_SIG_NEW, "TaskFile signature")
    src = sub_once(src, LOADER_OLD, LOADER_NEW, "load_task_file")
    src = sub_once(src, R21_INSERT_AFTER, R21_BODY.lstrip("\n") + R21_INSERT_AFTER, "R21 body")
    src = sub_once(src, RULE_CLASS_OLD, RULE_CLASS_NEW, "RULE_CLASS")
    src = sub_once(src, RUNRULES_OLD, RUNRULES_NEW, "run_rules")
    src = sub_once(src, NEAREST_OLD, NEAREST_NEW, "nearest_anchor")
    src = sub_once(src, R2_CALL_OLD, R2_CALL_NEW, "R2 call site")
    src = sub_once(src, R2_MSG_OLD, R2_MSG_NEW, "R2 message")

    if flavor == "refA":
        src = sub_once(src, R10_PRED_OLD, R10_PRED_REFA, "R10 predicate (refA)")
    elif flavor == "refB":
        src = sub_once(src, R10_PRED_OLD, R10_PRED_REFB, "R10 predicate (refB)")
        src = sub_once(src, R10_CALL_OLD, R10_CALL_REFB, "R10 call site (refB)")
    else:
        raise SystemExit(f"unknown flavor {flavor}")

    with open(p, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"built {flavor} at {dest}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "refA")
