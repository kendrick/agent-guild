#!/usr/bin/env python3
"""Lint `.agent-guild/state/constitution.md` and `state/tasks/*.md` for the
defects an opus auditor would otherwise have to find by reading—the
mechanical eleven-rules-deep sweep #132 exists to take off an auditor's
plate before it ever gets dispatched.

    .agent-guild/scripts/check-job-spec.py [STATE] [--repo-root PATH]
                                            [--audit-id CON-audit|DEC-audit]
    .agent-guild/scripts/check-job-spec.py --self-test

STATE defaults to `.agent-guild/state`. `--repo-root` (default: cwd) is the
root every citation and script invocation resolves against—not
necessarily where STATE lives, since a fixture in tests points STATE at a
corpus copy while citations still need to resolve against a real tree.

Rules run in this order—proofs before heuristics, so a heuristic never
masks something provable—and only the FIRST violation found is reported:

    R6 clause wiring        R1 citation resolves     R9 verdict contradiction
    R7 dependency DAG       R3 citation shape         R10 count vs list
    R4 check form           R8 build ordering         R12' cross-artifact count
    R5 check runnable       R2 citation anchor

`--audit-id CON-audit`: `state/tasks/` is expected empty (nothing to wire,
depend on, or order yet), so R6, R7, and R8 are skipped; every other rule
runs over constitution.md alone. `--audit-id DEC-audit`: everything runs,
and an empty `tasks/` is itself an R6 failure—a decomposition that
produced no tasks decomposed nothing.

Every prose rule (R1 through R4, R9, R10, R12') reads only two kinds of
text: a task's frontmatter (in practice, only `check_method` carries prose)
plus its `## Spec excerpt`, and a constitution clause's own block. Everything
else—`## Rework diagnosis`, `## Courier comparison`, `## Routing`, fenced
code blocks, HTML comments—is a historical record or literal script text,
not paperwork under review, and scanning it produced six of the false
positives this linter was measured against before that scope was drawn.

Exit codes: 0 pass; 1 a rule is violated (one line on stderr, prefixed
`job-spec: `, naming the rule first—e.g. `job-spec: R2 citation-anchor:
tasks/T-001.md:57 cites compose-brief.py:58 but the quoted code is at
compose-brief.py:64`); 3 infra (state dir missing, a file unreadable, a task
file with no frontmatter, or validate-verdict.py/compose-brief.py not
importable)—an infra failure is not evidence the paperwork is sound, so
dispatch-guard treats it as a distinct, non-passing outcome.

--self-test runs an embedded fixture battery in temp directories and exits
0 only if every fixture behaves as documented.

Stdlib only, so the kit stays copy-in portable—see compose-brief.py and
check-provenance.py for the same constraint and the same reasons. Imports
`parse_frontmatter`, `extract_clause`, and `extract_section` from
compose-brief.py, and `DEFECT_SEVERITIES` from validate-verdict.py, via
importlib (the `render-verdict.py:33-39` idiom for a hyphenated filename),
rather than reimplementing them: a linter whose job is to prove the
paperwork is readable by the tools that consume it has to call the same
parser those tools call, not a lookalike that could bless a file
`compose-brief.py` itself chokes on. The block-sequence `artifacts:` form
and the folded `check_method: >-` scalar are parsed here instead, because
no other script in the kit reads either field programmatically—there is
nothing downstream for compose-brief.py's parser to stay honest against.
"""
import argparse
import difflib
import glob
import graphlib
import importlib.util
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(name, filename):
    path = os.path.join(SCRIPT_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Frontmatter parsing: the base parser plus the two extensions the plan
# calls for.
# ---------------------------------------------------------------------------

FM_KEY_RE = re.compile(r"^([A-Za-z0-9_]+):\s*(.*)$")
LIST_ITEM_LINE_RE = re.compile(r"^\s*-\s+(.*)$")


def raw_frontmatter_lines(lines):
    """(fm_lines, body_start)—the lines strictly between the two `---`
    fences, 0-indexed against the original file, and the index of the first
    body line. None, None if there's no closed frontmatter block."""
    if not lines or lines[0].strip() != "---":
        return None, None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:i], i + 1
    return None, None


def parse_clause_list(raw):
    """`clauses: [C-1, C-4]` (or `deps: [T-001]`, or `[]`) -> a list of the
    bracketed, comma-separated ids. Same bracket format for both fields, so
    one parser covers `clauses:` and `deps:`."""
    raw = (raw or "").strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return []
    inner = raw[1:-1].strip()
    if not inner:
        return []
    return [c.strip() for c in inner.split(",") if c.strip()]


def parse_artifacts(fm_lines, key_idx, flat_value):
    """`artifacts:` comes two ways in the corpus: flat `[a, b]` on the key's
    own line, or a block sequence—`artifacts:` with nothing after the
    colon, then `  - path` on each following line. Three of the seven
    corpus tasks (T-001, T-006, T-007) use the block form, which
    compose-brief.py's flat-only parser silently drops to an empty list—
    fine for compose-brief.py, which never reads `artifacts`, but fatal for
    R8 here, which needs every artifact path to classify a task as a build
    input or a generated-tree write."""
    flat_value = flat_value.strip()
    if flat_value.startswith("["):
        return parse_clause_list(flat_value)
    items = []
    for line in fm_lines[key_idx + 1:]:
        m = LIST_ITEM_LINE_RE.match(line)
        if m is None:
            break
        val = m.group(1).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        items.append(val)
    return items


def fold_check_method(fm_lines, key_idx, file_start_line):
    """Fold the `check_method: >-` scalar's continuation lines into one
    prose string, the way YAML folding joins them for a real parser, and
    build a same-length `offset -> physical source line` map alongside it.

    Every rule that scans check_method text needs to report *where* in the
    task file a problem sits, not just "somewhere in check_method"—a
    diagnostic pointing at the `check_method:` key line on a task whose
    value runs forty lines is barely better than no line number at all.
    `file_start_line` is the 1-indexed physical line of `fm_lines[0]` in the
    original file, so the map comes out in file coordinates, not
    block-relative ones.
    """
    parts = []
    line_map = []
    first = True
    i = key_idx + 1
    while i < len(fm_lines):
        raw = fm_lines[i]
        # A folded scalar's continuation lines are indented; the first line
        # back at column 0 is the next frontmatter key, which ends the value.
        if raw.strip() != "" and not raw[0].isspace():
            break
        content = raw.strip()
        physical = file_start_line + i
        if content:
            if not first:
                parts.append(" ")
                line_map.append(physical)
            parts.append(content)
            line_map.extend([physical] * len(content))
            first = False
        i += 1
    return "".join(parts), line_map, i


class TaskFile:
    """Everything a rule needs about one `tasks/T-NNN.md`, extracted once.

    `check_method_text` / `check_method_map` are the folded scalar and its
    offset->line map (see `fold_check_method`). `spec_excerpt_text` /
    `spec_excerpt_start_line` describe the verbatim `## Spec excerpt`
    section and the physical line its first character sits on, so a rule
    that finds an offset within it can add a newline count to get a real
    line number.
    """

    def __init__(self, path, label, task_id, title, clauses, deps, artifacts,
                 check_method_text, check_method_map,
                 spec_excerpt_text, spec_excerpt_start_line):
        self.path = path
        self.label = label
        self.id = task_id
        self.title = title
        self.clauses = clauses
        self.deps = deps
        self.artifacts = artifacts
        self.check_method_text = check_method_text
        self.check_method_map = check_method_map
        self.spec_excerpt_text = spec_excerpt_text
        self.spec_excerpt_start_line = spec_excerpt_start_line

    def line_for_excerpt_offset(self, offset):
        return self.spec_excerpt_start_line + self.spec_excerpt_text.count("\n", 0, offset)

    def line_for_check_method_offset(self, offset):
        if 0 <= offset < len(self.check_method_map):
            return self.check_method_map[offset]
        return self.check_method_map[-1] if self.check_method_map else 0


def load_task_file(path, compose_brief):
    """(TaskFile, None) on success, (None, error) on an infra-level parse
    failure (no frontmatter at all—compose-brief.py itself couldn't read
    this task, so nothing downstream of it could either)."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return None, f"cannot read {path}: {e}"

    fm, body = compose_brief.parse_frontmatter(text)
    if fm is None:
        return None, f"{path}: no YAML frontmatter header found"

    lines = text.splitlines()
    fm_lines, body_start = raw_frontmatter_lines(lines)
    if fm_lines is None:
        return None, f"{path}: frontmatter block never closes"

    clauses = parse_clause_list(fm.get("clauses"))
    deps = parse_clause_list(fm.get("deps"))

    artifacts = []
    check_method_text, check_method_map = "", []
    for i, line in enumerate(fm_lines):
        m = FM_KEY_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        if key == "artifacts":
            artifacts = parse_artifacts(fm_lines, i, val)
        elif key == "check_method":
            check_method_text, check_method_map, _ = fold_check_method(fm_lines, i, 2)

    spec_excerpt = compose_brief.extract_section(body, "## Spec excerpt")
    spec_excerpt_start_line = 0
    if spec_excerpt is not None:
        idx = text.find(spec_excerpt)
        if idx >= 0:
            spec_excerpt_start_line = text.count("\n", 0, idx) + 1

    label = os.path.join("tasks", os.path.basename(path))
    task = TaskFile(
        path=path, label=label,
        task_id=fm.get("id", "").strip(), title=fm.get("title", "").strip(),
        clauses=clauses, deps=deps, artifacts=artifacts,
        check_method_text=check_method_text, check_method_map=check_method_map,
        spec_excerpt_text=spec_excerpt or "", spec_excerpt_start_line=spec_excerpt_start_line,
    )
    return task, None


# ---------------------------------------------------------------------------
# Constitution parsing.
# ---------------------------------------------------------------------------

CLAUSE_HEADING_RE = re.compile(r"(?m)^### (C-\d+):.*$")
CLAUSE_FIELD_RE = re.compile(r"^- \*\*([a-zA-Z ]+)\*\*:\s?(.*)$")


class Clause:
    def __init__(self, clause_id, block_text, block_start_line,
                 check_text, check_line, severity):
        self.id = clause_id
        self.block_text = block_text
        self.block_start_line = block_start_line
        self.check_text = check_text
        self.check_line = check_line
        self.severity = severity


def parse_constitution(text):
    """{clause_id: Clause}, keyed off every `### C-N:` heading. A clause's
    field values (`- **check**:`, `- **severity**:`, ...) are one physical
    line each in every corpus example, so no folding logic is needed here—
    only tasks' `check_method` gets that treatment."""
    clauses = {}
    headings = list(CLAUSE_HEADING_RE.finditer(text))
    for idx, m in enumerate(headings):
        clause_id = m.group(1)
        start = m.start()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        block = text[start:end].rstrip("\n")
        block_start_line = text.count("\n", 0, start) + 1

        check_text, check_line, severity = "", 0, None
        offset = start
        for line in block.split("\n"):
            fm = CLAUSE_FIELD_RE.match(line.strip())
            if fm:
                field, val = fm.group(1).strip().lower(), fm.group(2).strip()
                if field == "check":
                    check_text = val
                    check_line = text.count("\n", 0, offset) + 1
                elif field == "severity":
                    severity = val
            offset += len(line) + 1
        clauses[clause_id] = Clause(clause_id, block, block_start_line, check_text, check_line, severity)
    return clauses


# ---------------------------------------------------------------------------
# Section-scope exclusion: fenced code blocks and HTML comments are blanked
# (not deleted) so every offset computed before this step still lines up
# with a physical line afterward.
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"```.*?```", re.S)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def _blank(pattern, text):
    def repl(m):
        return "".join(ch if ch == "\n" else " " for ch in m.group(0))
    return pattern.sub(repl, text)


def scoped(text):
    return _blank(HTML_COMMENT_RE, _blank(FENCE_RE, text))


# ---------------------------------------------------------------------------
# R1 / R2 / R3: citations.
# ---------------------------------------------------------------------------

# No whitespace around the colon (so a folded scalar's word-wrap can't turn
# unrelated neighbours into a fake citation), and the path half must contain
# a `/`—that's what keeps `retries: 0`, a bare `ref.py:74` mentioned by
# name alone, and an ISO timestamp like `2026-08-08T14:47:08Z` from ever
# reaching the regex's file-existence check in the first place.
CITATION_RE = re.compile(r"([~\w./#@-]*[\w-]\.[A-Za-z0-9]+):(\d+)\b")
ATX_HEADING_RE = re.compile(r"^#{1,6}\s")
SETEXT_UNDERLINE_RE = re.compile(r"^(=+|-+)\s*$")

# An anchor span has to be long enough, and word-shaped enough, to be an
# excerpt of real code rather than a path fragment: T-001.md:57 alone carries
# five backtick spans, and the 3-character `` `ref` `` one matches 18 lines
# of check-provenance.py that have nothing to do with the cited line. Length
# 24 plus "contains a space" leaves exactly one span standing in the whole
# corpus—the 52-char quote-stripping excerpt that's the actual point of
# that citation. Without this filter R2 fails the corpus it has to pass.
def anchor_spans(text):
    spans = []
    for m in re.finditer(r"`([^`]*)`", text):
        content = m.group(1)
        if len(content) >= 24 and " " in content:
            spans.append((m.start(), m.end(), content))
    return spans


def is_excluded_citation_path(path):
    return path.startswith("/") or path.startswith("~") or "/" not in path


def find_citations(text):
    """[(offset, path, lineno_str)] for every CITATION_RE match whose path
    is a resolvable repo-relative path—filters out absolute paths,
    `~`-paths, and bare basenames up front, same as the plan requires."""
    out = []
    for m in CITATION_RE.finditer(text):
        path = m.group(1)
        if is_excluded_citation_path(path):
            continue
        out.append((m.start(), path, m.group(2)))
    return out


def check_citation_rules(regions, repo_root, want_rule):
    """Runs R1 (resolves), R3 (shape), or R2 (anchor)—`want_rule` in
    {"R1", "R3", "R2"}—over every citation in `regions`, in file order,
    and returns the first violation's diagnostic or None.

    `regions` is a list of (source_label, text, line_of_offset) triples,
    already scope-filtered (fenced/HTML-comment blanked). Bundling the three
    citation rules into one scan keeps them sharing one citation-finding
    pass rather than three, and R2 needs R1's resolved target line anyway.
    """
    for label, text, line_of in regions:
        for offset, path, lineno_str in find_citations(text):
            src_line = line_of(offset)
            lineno = int(lineno_str)
            target_path = os.path.join(repo_root, path)

            if not os.path.isfile(target_path):
                if want_rule == "R1":
                    return f"R1 citation-resolves: {label}:{src_line} cites {path}:{lineno} but that file does not exist under --repo-root"
                continue
            try:
                with open(target_path, encoding="utf-8") as f:
                    target_lines = f.read().splitlines()
            except OSError as e:
                if want_rule == "R1":
                    return f"R1 citation-resolves: {label}:{src_line} cites {path}:{lineno} but the file can't be read: {e}"
                continue

            if lineno < 1 or lineno > len(target_lines):
                if want_rule == "R1":
                    return f"R1 citation-resolves: {label}:{src_line} cites {path}:{lineno} but {path} only has {len(target_lines)} line(s)"
                continue

            target_line = target_lines[lineno - 1]

            if want_rule == "R3":
                if target_line.strip() == "":
                    return f"R3 citation-shape: {label}:{src_line} cites {path}:{lineno} but that line is blank"
                if path.endswith(".md"):
                    if ATX_HEADING_RE.match(target_line.strip()):
                        return f"R3 citation-shape: {label}:{src_line} cites {path}:{lineno} but that line is a heading ({target_line.strip()!r})"
                    if SETEXT_UNDERLINE_RE.match(target_line.strip()):
                        return f"R3 citation-shape: {label}:{src_line} cites {path}:{lineno} but that line is a setext heading underline"
                continue

            if want_rule == "R2":
                # The citation's own backtick-wrapped form never counts as
                # its own anchor—excluded so a long relative path can't
                # accidentally "confirm" itself.
                candidates = [c for _, _, c in anchor_spans(text) if c != f"{path}:{lineno}"]
                if not candidates:
                    continue  # nothing to check this citation against
                target_stripped = " ".join(target_line.split())
                anchor = candidates[0]
                anchor_norm = " ".join(anchor.split())
                if anchor_norm in target_stripped:
                    continue
                # It's wrong, but say where it's actually right: scan the
                # whole target file for the quoted code so the diagnostic
                # names the true line, not just the false one.
                actual_line = None
                for i, cand_line in enumerate(target_lines, start=1):
                    if anchor_norm in " ".join(cand_line.split()):
                        actual_line = i
                        break
                if actual_line is not None:
                    return (
                        f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
                        f"but the quoted code is at {path}:{actual_line}"
                    )
                return (
                    f"R2 citation-anchor: {label}:{src_line} cites {path}:{lineno} "
                    f"but the quoted code {anchor!r} does not appear anywhere in {path}"
                )
    return None


# ---------------------------------------------------------------------------
# check_method segmentation, shared by R4, R5, R6, and R9.
# ---------------------------------------------------------------------------

# The colon is required. A bare `\bC-\d+\b` mis-segments T-007, whose C-9
# text says "On C-6 or C-9, an absent fact is a FAIL"—the second mention
# has no colon and isn't a new segment, but a colon-less pattern would split
# there anyway and hand R4 half a sentence to judge on its own. The `(?:^|\s)`
# guard keeps a mid-word "abc-9:" from counting, and the optional `(N)`
# prefix matches T-003's numbered "(1) C-3: ...".
SEGMENT_RE = re.compile(r"(?:^|\s)(?:\(\d+\)\s*)?(C-\d+):\s")


def find_segments(text):
    """(preamble, [(clause_id, value_start_offset, value_text)])—one entry
    per `C-N:` key found, in order. `value_text` runs up to the next key or
    end of string, so it may carry trailing debris from a following `(N) `
    numbering prefix; that's harmless for every rule that reads it."""
    matches = list(SEGMENT_RE.finditer(text))
    if not matches:
        return text, []
    preamble = text[:matches[0].start(1)]
    segments = []
    for i, m in enumerate(matches):
        seg_start = m.end()
        seg_end = matches[i + 1].start(1) if i + 1 < len(matches) else len(text)
        segments.append((m.group(1), seg_start, text[seg_start:seg_end]))
    return preamble, segments


def classify_check_text(text):
    """("script", invocation) | ("judgment", rubric) | (None, None)."""
    t = text.strip()
    if t.startswith("checker-judgment:"):
        return "judgment", t[len("checker-judgment:"):].strip()
    if re.match(r"^\.agent-guild/scripts/\S+", t):
        return "script", t
    return None, None


# ---------------------------------------------------------------------------
# R4: check form. Closes #121—a check that isn't a script invocation or a
# named judgment rubric is unverifiable prose masquerading as a check.
# ---------------------------------------------------------------------------

# The #121 evasion: word a check_method's free-text preamble to *describe*
# running a script, ahead of the real `C-N:` segments, so nothing keyed to a
# clause ever has to name it. This catches any script-shaped token sitting
# outside a segment, so the evasion has nowhere left to hide it.
SCRIPT_TOKEN_RE = re.compile(r"\S+\.(sh|py|mjs)\b")


def rule_R4(ctx, audit_id):
    for cid in sorted(ctx.clauses, key=lambda c: int(c[2:])):
        clause = ctx.clauses[cid]
        kind, _ = classify_check_text(clause.check_text)
        if kind is None:
            return (
                f"R4 check-form: constitution.md:{clause.check_line} clause {cid}'s "
                "check is neither a .agent-guild/scripts/ invocation nor "
                "checker-judgment: <rubric>"
            )
    for task in ctx.tasks:
        text = scoped(task.check_method_text)
        preamble, segments = find_segments(text)
        m = SCRIPT_TOKEN_RE.search(preamble)
        if m:
            line = task.line_for_check_method_offset(m.start())
            return (
                f"R4 check-form: {task.label}:{line} check_method names "
                f"{m.group(0)!r} outside any C-N: segment"
            )
        for cid, seg_start, seg_text in segments:
            kind, _ = classify_check_text(seg_text)
            if kind is None:
                line = task.line_for_check_method_offset(seg_start)
                return (
                    f"R4 check-form: {task.label}:{line} {cid}: segment is neither a "
                    ".agent-guild/scripts/ invocation nor checker-judgment: <rubric>"
                )
    return None


# ---------------------------------------------------------------------------
# R5: check runnable.
# ---------------------------------------------------------------------------

def _collect_script_checks(ctx):
    """[(label, line, invocation_text)] for every check classified "script"
    by R4—constitution clauses first, then task check_method segments."""
    checks = []
    for cid in sorted(ctx.clauses, key=lambda c: int(c[2:])):
        clause = ctx.clauses[cid]
        kind, val = classify_check_text(clause.check_text)
        if kind == "script":
            checks.append(("constitution.md", clause.check_line, val))
    for task in ctx.tasks:
        text = scoped(task.check_method_text)
        _, segments = find_segments(text)
        for cid, seg_start, seg_text in segments:
            kind, val = classify_check_text(seg_text)
            if kind == "script":
                line = task.line_for_check_method_offset(seg_start)
                checks.append((task.label, line, val))
    return checks


def rule_R5(ctx, repo_root):
    for label, line, invocation in _collect_script_checks(ctx):
        try:
            tokens = shlex.split(invocation)
        except ValueError as e:
            return f"R5 check-runnable: {label}:{line} check invocation can't be shell-parsed: {e}"
        if not tokens:
            return f"R5 check-runnable: {label}:{line} check invocation is empty"
        script_rel = tokens[0]
        script_path = os.path.join(repo_root, script_rel)
        if not os.path.isfile(script_path):
            return f"R5 check-runnable: {label}:{line} {script_rel} does not exist under --repo-root"
        if not os.access(script_path, os.X_OK):
            return f"R5 check-runnable: {label}:{line} {script_rel} is not executable (missing X_OK)"
        if os.path.basename(script_rel) == "check-build.sh":
            if len(tokens) < 2:
                return f"R5 check-runnable: {label}:{line} check-build.sh is given no quoted command"
            inner = tokens[1]
            # Syntax-check only—never execute. Executing a build/test
            # command from a linter that runs before every auditor dispatch
            # would make the linter itself part of the thing under test.
            try:
                proc = subprocess.run(
                    ["bash", "-n", "-c", inner], capture_output=True, text=True, timeout=10,
                )
            except (OSError, subprocess.TimeoutExpired) as e:
                return f"R5 check-runnable: {label}:{line} could not syntax-check check-build.sh's command: {e}"
            if proc.returncode != 0:
                detail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else f"exit {proc.returncode}"
                return f"R5 check-runnable: {label}:{line} check-build.sh's quoted command fails `bash -n`: {detail}"
    return None


# ---------------------------------------------------------------------------
# R6: clause wiring.
# ---------------------------------------------------------------------------

def rule_R6(ctx, audit_id):
    if audit_id == "CON-audit":
        return None
    if not ctx.tasks:
        return (
            "R6 clause-wiring: tasks/ is empty under --audit-id DEC-audit; "
            "a decomposition that produced no tasks decomposed nothing"
        )
    cited_by = {}
    for task in ctx.tasks:
        for cid in task.clauses:
            cited_by.setdefault(cid, []).append(task)
            if cid not in ctx.clauses:
                return (
                    f"R6 clause-wiring: {task.label} cites {cid} in clauses:, "
                    "which is not a clause in constitution.md"
                )
    for cid in sorted(ctx.clauses, key=lambda c: int(c[2:])):
        if cid not in cited_by:
            return f"R6 clause-wiring: constitution.md clause {cid} is never cited by any task"
    for task in ctx.tasks:
        text = scoped(task.check_method_text)
        _, segments = find_segments(text)
        keyed = {cid for cid, _, _ in segments}
        for cid in task.clauses:
            if cid not in keyed:
                return (
                    f"R6 clause-wiring: {task.label} cites {cid} in clauses: but "
                    f"check_method has no {cid}: segment"
                )
    return None


# ---------------------------------------------------------------------------
# R7: dependency DAG.
# ---------------------------------------------------------------------------

def rule_R7(ctx, audit_id):
    if audit_id == "CON-audit":
        return None
    by_id = {t.id: t for t in ctx.tasks}
    graph = {}
    for task in ctx.tasks:
        for dep in task.deps:
            if dep not in by_id:
                return f"R7 dag: {task.label} depends on {dep}, which is not a task in tasks/"
        graph[task.id] = set(task.deps)
    try:
        graphlib.TopologicalSorter(graph).prepare()
    except graphlib.CycleError as e:
        involved = e.args[1] if len(e.args) > 1 else e.args
        return f"R7 dag: dependency cycle among {', '.join(str(x) for x in involved)}"
    return None


# ---------------------------------------------------------------------------
# R8: build ordering.
# ---------------------------------------------------------------------------

# Read off scripts/build-plugin.py's own source tree, not restated from
# memory: guild-core/ and these five .agent-guild/ subpaths are what it
# copies INTO the shipped trees. .agent-guild/state/ is deliberately absent
#—it's job bookkeeping, not a build input, and without this exclusion
# T-007's own commit-message.md (under .agent-guild/state/) would count as
# an input it regenerates from, making it a trivial self-dependency.
BUILD_INPUT_PREFIXES = (
    "guild-core/",
    ".agent-guild/CLAUDE.md",
    ".agent-guild/scripts",
    ".agent-guild/templates",
    ".agent-guild/schemas",
    ".agent-guild/hooks",
    "scripts/plugin-src/",
    "docs/plugin-readme.md",
    "CHANGELOG.md",
)
GENERATED_TREE_PREFIXES = ("plugin/", "plugins/", ".claude/")


def _is_build_input(path):
    if path.startswith(".agent-guild/state/"):
        return False
    return any(path == p or path.startswith(p) for p in BUILD_INPUT_PREFIXES)


def _is_generated(path):
    return any(path.startswith(p) for p in GENERATED_TREE_PREFIXES)


def _transitive_deps(task_id, by_id, seen=None):
    seen = seen if seen is not None else set()
    for dep in by_id[task_id].deps:
        if dep not in seen:
            seen.add(dep)
            _transitive_deps(dep, by_id, seen)
    return seen


def rule_R8(ctx, audit_id):
    if audit_id == "CON-audit" or not ctx.tasks:
        return None  # empty tasks/ under DEC-audit is already an R6 failure
    by_id = {t.id: t for t in ctx.tasks}
    inputs = {t.id for t in ctx.tasks if any(_is_build_input(a) for a in t.artifacts)}
    generated = {t.id for t in ctx.tasks if any(_is_generated(a) for a in t.artifacts)}
    if not generated:
        return None  # nothing in this job regenerates a shipped tree
    universe = inputs | generated
    # Existence, not universal ordering: "every input precedes every
    # generator" self-fires on T-007, whose own artifacts are both an input
    # (the schema, ledger-append.py) and a generated-tree write (the copies
    # under plugin/, .claude/)—it would have to be transitively upstream
    # of itself. What actually has to hold is that SOME regenerating task
    # runs last, after every other input and generator it needs to capture.
    for t in sorted(generated):
        if universe - {t} <= _transitive_deps(t, by_id):
            return None
    return (
        "R8 build-ordering: no generated-tree task ("
        + ", ".join(sorted(generated))
        + ") is downstream of every build-input and generated-tree task in "
        + "this job (" + ", ".join(sorted(universe)) + "); a regeneration "
        "could run before the last edit it needs to capture"
    )


# ---------------------------------------------------------------------------
# Section scope for the remaining prose rules (R9, R10, R12'): every region
# R1/R2/R3 already scan, reused so the "what counts as paperwork" boundary
# lives in one place.
# ---------------------------------------------------------------------------

def gather_prose_regions(ctx):
    """[(artifact_key, label, text, line_of_offset_fn)]. `artifact_key` is
    what "different artifacts" means for R12'—one key per file, so a
    task's own spec excerpt and check_method don't cross-compare against
    each other, only against a DIFFERENT file's regions."""
    regions = []
    for task in ctx.tasks:
        regions.append((task.path, task.label, scoped(task.spec_excerpt_text), task.line_for_excerpt_offset))
        regions.append((task.path, task.label, scoped(task.check_method_text), task.line_for_check_method_offset))
    for cid, clause in ctx.clauses.items():
        text = scoped(clause.block_text)

        def line_of(offset, _start=clause.block_start_line, _text=text):
            return _start + _text.count("\n", 0, offset)

        regions.append(("constitution.md", "constitution.md", text, line_of))
    return regions


def citation_regions(ctx):
    """Regions for R1/R2/R3, which additionally need `## Spec excerpt` and
    check_method kept separate from clause blocks (constitution.md carries
    its own line numbers directly, no offset function needed beyond what
    gather_prose_regions already builds)—same shape, so just reuse it."""
    return [(label, text, line_of) for _key, label, text, line_of in gather_prose_regions(ctx)]


# ---------------------------------------------------------------------------
# R9: verdict contradiction.
# ---------------------------------------------------------------------------

PASS_TOKEN_RE = re.compile(r"\b(pass|passes|passing)\b", re.I)
DEFECT_TOKEN_RE = re.compile(r"\b(major|blocker|defect|finding|gap)\b", re.I)

# The veto list IS the rule. Without it, T-007's own fix for the defect R9
# exists to catch—"an absent fact is a FAIL, never a pass carrying a
# finding"—reads as an instance of it: "pass" and "finding" sit five words
# apart. Every entry below is a word the corpus actually uses to negate a
# pass+defect co-occurrence; add a veto token and a real instruction reads
# as clean, drop one and a fix like this one reads as a violation of itself.
VETO_TOKENS = (
    "never", "not", "no", "nothing", "refuses", "rejects", "forbid",
    "anyway", "instead of", "rather than", "would accept", "cannot", "fails",
)
VETO_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in VETO_TOKENS) + r")", re.I)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def sentences(text):
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]


def r9_fires(sentence):
    # All three conjuncts required, biased toward false negatives: a false
    # positive here deadlocks a job on a sentence ABOUT the rule rather than
    # a violation of it, and an auditor still catches a real miss downstream.
    return bool(
        PASS_TOKEN_RE.search(sentence)
        and DEFECT_TOKEN_RE.search(sentence)
        and not VETO_RE.search(sentence)
    )


def rule_R9(ctx):
    for cid in sorted(ctx.clauses, key=lambda c: int(c[2:])):
        clause = ctx.clauses[cid]
        if clause.severity not in DEFECT_SEVERITIES:
            continue
        for s in sentences(clause.check_text):
            if r9_fires(s):
                return (
                    f"R9 verdict-contradiction: constitution.md:{clause.check_line} "
                    f"clause {cid} ({clause.severity}) check text instructs a pass "
                    f"alongside a defect: {s!r}"
                )
    for task in ctx.tasks:
        text = scoped(task.check_method_text)
        _, segments = find_segments(text)
        for cid, seg_start, seg_text in segments:
            clause = ctx.clauses.get(cid)
            if clause is None or clause.severity not in DEFECT_SEVERITIES:
                continue
            for s in sentences(seg_text):
                if r9_fires(s):
                    local_offset = seg_text.find(s)
                    line = task.line_for_check_method_offset(seg_start + max(local_offset, 0))
                    return (
                        f"R9 verdict-contradiction: {task.label}:{line} {cid}: instructs "
                        f"a pass alongside a defect: {s!r}"
                    )
    return None


# ---------------------------------------------------------------------------
# R10: count vs list.
# ---------------------------------------------------------------------------

WORD2NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
NUMBER_TOKEN_RE = re.compile(r"\b(\d+|" + "|".join(WORD2NUM) + r")\b", re.I)


def number_value(tok):
    if tok.isdigit():
        return int(tok)
    return WORD2NUM.get(tok.lower())


# "one" is the one number word that's usually not a number: constitution.md's
# own C-4 text reads "Every one of the 18 rows..."—a false "1" sitting one
# word from a real count ("18") that made R12' fire on the unmutated corpus,
# comparing it against T-006's genuine "Ten of the 18 rows...". Every other
# WORD2NUM entry is unambiguous; only "one" doubles as a pronoun, and only
# behind one of these four words. Filtering just that combination keeps
# genuine counts like T-006's "One row's `started_at` carries fractional
# seconds" intact.
_ONE_IDIOM_GUARD = ("every", "any", "no", "some")


def is_real_number_match(text, match):
    """False for a NUMBER_TOKEN_RE match that's "one" used as a pronoun
    rather than a count, given the text it's matched within."""
    if match.group(1).lower() != "one":
        return True
    before = text[:match.start()].rstrip()
    prev_word = before.rsplit(None, 1)[-1].lower() if before.split() else ""
    return prev_word not in _ONE_IDIOM_GUARD


LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
FENCE_LINE_RE = re.compile(r"^\s*```")
BLOCKQUOTE_LINE_RE = re.compile(r"^\s*>")
TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]+\|?\s*$")


def find_r10_violation(text, line_of, label):
    lines = text.split("\n")
    offsets = []
    pos = 0
    for l in lines:
        offsets.append(pos)
        pos += len(l) + 1
    n = len(lines)
    in_fence = False
    i = 0
    while i < n:
        raw = lines[i]
        if FENCE_LINE_RE.match(raw):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence or BLOCKQUOTE_LINE_RE.match(raw) or TABLE_ROW_RE.match(raw) or LIST_ITEM_RE.match(raw):
            i += 1
            continue
        stripped = raw.rstrip()
        if stripped.endswith(":"):
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            m0 = LIST_ITEM_RE.match(lines[j]) if j < n else None
            if m0 and not TABLE_SEP_RE.match(lines[j]):
                top_indent = len(m0.group(1))
                count = 0
                k = j
                while k < n:
                    if lines[k].strip() == "":
                        k2 = k + 1
                        while k2 < n and lines[k2].strip() == "":
                            k2 += 1
                        mk2 = LIST_ITEM_RE.match(lines[k2]) if k2 < n else None
                        if mk2 and len(mk2.group(1)) >= top_indent:
                            k = k2
                            continue
                        break
                    mk = LIST_ITEM_RE.match(lines[k])
                    if not mk:
                        break
                    indent = len(mk.group(1))
                    if indent < top_indent:
                        break
                    if indent == top_indent:
                        count += 1
                    k += 1
                matches = [m for m in NUMBER_TOKEN_RE.finditer(stripped) if is_real_number_match(stripped, m)]
                if matches:
                    tok = matches[-1].group(1)
                    val = number_value(tok)
                    if val is not None and val != count:
                        line = line_of(offsets[i])
                        return (
                            f"R10 count-vs-list: {label}:{line} says {tok!r} ({val}) but "
                            f"the following list has {count} item(s)"
                        )
        i += 1
    return None


def rule_R10(ctx):
    for _key, label, text, line_of in gather_prose_regions(ctx):
        msg = find_r10_violation(text, line_of, label)
        if msg:
            return msg
    return None


# ---------------------------------------------------------------------------
# R12': cross-artifact count.
# ---------------------------------------------------------------------------

WORD_RE = re.compile(r"\S+")


def strip_numbers_with_map(text):
    """(stripped_text, index_map)—number tokens deleted outright (not
    blanked), with index_map[i] giving stripped_text[i]'s offset in the
    original. Deletion, not same-length blanking, is what makes this safe:
    "Ten" (3 chars) and "Eleven" (6 chars) blank to runs of different
    length, and SequenceMatcher is free to align the last 3 of Eleven's 6
    blanked characters against all of Ten's 3—a match that starts
    mid-token, with no word boundary left for the backward number scan to
    anchor on. Deleting the token leaves nothing there to partially match:
    the two stripped strings either agree from the word right after the
    number, or they don't."""
    out_chars = []
    index_map = []
    i = 0
    for m in NUMBER_TOKEN_RE.finditer(text):
        while i < m.start():
            out_chars.append(text[i])
            index_map.append(i)
            i += 1
        i = m.end()
    while i < len(text):
        out_chars.append(text[i])
        index_map.append(i)
        i += 1
    return "".join(out_chars), index_map


def nearest_preceding_number(text, offset):
    """The value of the closest number token within 5 words before
    `offset` in `text`, or None. Scans NUMBER_TOKEN_RE matches directly
    (rather than per-word) so `is_real_number_match` sees the real text
    around each candidate, not an isolated word."""
    prefix = text[:offset]
    words = list(WORD_RE.finditer(prefix))
    window_start = words[-5].start() if len(words) >= 5 else 0
    for m in reversed(list(NUMBER_TOKEN_RE.finditer(prefix))):
        if m.start() < window_start:
            break
        if is_real_number_match(prefix, m):
            return number_value(m.group(1))
    return None


def rule_R12(ctx):
    regions = gather_prose_regions(ctx)
    entries = []  # (region_index, sentence_text, start_offset_in_region_text)
    for ri, (_key, _label, text, _line_of) in enumerate(regions):
        for s in sentences(text):
            if len(s) < 20:
                continue
            start = text.find(s)
            if start >= 0:
                entries.append((ri, s, start))

    for i, (ri_a, sa, off_a) in enumerate(entries):
        akey_a = regions[ri_a][0]
        ssa, map_a = strip_numbers_with_map(sa)
        for ri_b, sb, off_b in entries[i + 1:]:
            akey_b = regions[ri_b][0]
            if akey_a == akey_b:
                continue
            ssb, map_b = strip_numbers_with_map(sb)
            match = difflib.SequenceMatcher(None, ssa, ssb, autojunk=False).find_longest_match(
                0, len(ssa), 0, len(ssb)
            )
            # 60 is a measured floor, not a round number: this corpus's own
            # noise ceiling is 38 (two sentences about DIFFERENT counts that
            # happen to share "record absolute artifact paths under"), and
            # its one real duplicated-count pair shares 93. 60 sits with
            # better than 2x margin over the noise and well under the signal
            #—SequenceMatcher.ratio() has no such gap anywhere (see the
            # module docstring's design notes for the numbers that ruled it out).
            if match.size < 60:
                continue
            orig_a = map_a[match.a] if match.a < len(map_a) else len(sa)
            orig_b = map_b[match.b] if match.b < len(map_b) else len(sb)
            num_a = nearest_preceding_number(sa, orig_a)
            num_b = nearest_preceding_number(sb, orig_b)
            if num_a is None or num_b is None or num_a == num_b:
                continue
            label_a, label_b = regions[ri_a][1], regions[ri_b][1]
            line_a = regions[ri_a][3](off_a + orig_a)
            line_b = regions[ri_b][3](off_b + orig_b)
            excerpt = ssa[match.a:match.a + match.size].strip()
            return (
                f"R12' cross-artifact-count: {label_a}:{line_a} says {num_a} where "
                f"{label_b}:{line_b} says {num_b} for the same restated fact ({excerpt!r})"
            )
    return None


# ---------------------------------------------------------------------------
# Context assembly and rule ordering.
# ---------------------------------------------------------------------------

class Context:
    def __init__(self, clauses, tasks):
        self.clauses = clauses
        self.tasks = tasks


def load_context(state_dir, compose_brief):
    """(Context, None) on success, (None, error) on an infra-level failure—
    a missing constitution, or any task file compose-brief.py itself
    couldn't read."""
    const_path = os.path.join(state_dir, "constitution.md")
    try:
        with open(const_path, encoding="utf-8") as f:
            const_text = f.read()
    except OSError as e:
        return None, f"cannot read {const_path}: {e}"

    clauses = parse_constitution(const_text)

    task_paths = sorted(glob.glob(os.path.join(state_dir, "tasks", "*.md")))
    tasks = []
    for p in task_paths:
        task, err = load_task_file(p, compose_brief)
        if err:
            return None, err
        tasks.append(task)

    return Context(clauses, tasks), None


def run_rules(ctx, audit_id, repo_root):
    """First violation across all rules, evaluated in the plan's order—
    proofs before heuristics—or None if every rule passes."""
    regions = citation_regions(ctx)
    steps = (
        lambda: rule_R6(ctx, audit_id),
        lambda: rule_R7(ctx, audit_id),
        lambda: rule_R4(ctx, audit_id),
        lambda: rule_R5(ctx, repo_root),
        lambda: check_citation_rules(regions, repo_root, "R1"),
        lambda: check_citation_rules(regions, repo_root, "R3"),
        lambda: rule_R8(ctx, audit_id),
        lambda: check_citation_rules(regions, repo_root, "R2"),
        lambda: rule_R9(ctx),
        lambda: rule_R10(ctx),
        lambda: rule_R12(ctx),
    )
    for step in steps:
        msg = step()
        if msg:
            return msg
    return None


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

_FIXTURE_CHECK_BUILD_SH = """#!/usr/bin/env bash
set -uo pipefail
bash -c "$*"
exit $?
"""

_FIXTURE_MYTOOL_PY = """#!/usr/bin/env python3
print("ok")
"""

_FIXTURE_HELPER_PY = """# helper module



def other():
def helper(): return True

# padding
# padding
# padding
"""

_FIXTURE_NOTES_MD = """# Notes

- an ordinary line here for citations

## A heading
body
"""

_FIXTURE_CONSTITUTION = """# Constitution: self-test fixture

### C-1: first clause
- **text**: The build must stay green.
- **check**: .agent-guild/scripts/check-build.sh 'echo ok'
- **severity**: major
- **failing example**: n/a

### C-2: second clause
- **text**: The helper function must match its documented contract.
- **check**: checker-judgment: read lib/helper.py and confirm it matches.
- **severity**: major
- **failing example**: n/a
"""

_FIXTURE_T001 = """---
id: T-001
title: First task
spec: .agent-guild/state/spec.md#one
clauses: [C-1]
executor: worker-standard
executor_model: sonnet
checker: checker-deterministic
check_method: >-
  C-1: .agent-guild/scripts/check-build.sh 'echo ok'
status: pending
retries: 0
max_retries: 2
deps: []
escalations: []
artifacts:
  - .agent-guild/scripts/mytool.py
---

## Spec excerpt

The build must stay green.

See `lib/helper.py:6` for the reference implementation (`def helper(): return True`).

Three things matter here:

- correctness
- clarity
- speed

Ten widgets ship broken from the factory floor before anyone notices the defect in the packaging line.
"""

_FIXTURE_T002 = """---
id: T-002
title: Second task
spec: .agent-guild/state/spec.md#two
clauses: [C-2]
executor: worker-standard
executor_model: sonnet
checker: checker-judgment
check_method: >-
  C-2: checker-judgment: read lib/helper.py and confirm it matches. An
  absent fact must never pass with a major finding.
status: pending
retries: 0
max_retries: 2
deps: [T-001]
escalations: []
artifacts:
  - plugin/generated.md
---

## Spec excerpt

Reads and confirms the helper.

Ten widgets ship broken from the factory floor before anyone notices the defect in the packaging line, according to the audit.
"""


def _fixture_files(mutation=None):
    """The base fixture, or the base fixture with one substring replaced—
    every mutation changes exactly one thing, so a fixture that's meant to
    fail only R9 (say) doesn't happen to also fail R1 first and mask it."""
    files = {
        ".agent-guild/scripts/check-build.sh": _FIXTURE_CHECK_BUILD_SH,
        ".agent-guild/scripts/mytool.py": _FIXTURE_MYTOOL_PY,
        "lib/helper.py": _FIXTURE_HELPER_PY,
        "lib/notes.md": _FIXTURE_NOTES_MD,
        ".agent-guild/state/constitution.md": _FIXTURE_CONSTITUTION,
        ".agent-guild/state/tasks/T-001.md": _FIXTURE_T001,
        ".agent-guild/state/tasks/T-002.md": _FIXTURE_T002,
    }
    if mutation is not None:
        path, find, replace = mutation
        assert find in files[path], f"self-test fixture bug: {find!r} not found in {path}"
        files[path] = files[path].replace(find, replace, 1)
    return files


def _write_fixture(root, mutation=None):
    for rel, content in _fixture_files(mutation).items():
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    for rel in (".agent-guild/scripts/check-build.sh", ".agent-guild/scripts/mytool.py"):
        p = os.path.join(root, rel)
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# (name, mutation, expect_ok, needle-required-in-stderr-on-failure)
_SELF_TEST_CASES = [
    ("valid base fixture", None, True, None),
    (
        "R6 clauses: id not in constitution",
        (".agent-guild/state/tasks/T-002.md", "clauses: [C-2]", "clauses: [C-3]"),
        False, "R6",
    ),
    (
        "R7 dep on a nonexistent task",
        (".agent-guild/state/tasks/T-002.md", "deps: [T-001]", "deps: [T-999]"),
        False, "R7",
    ),
    (
        "R4 check_method segment neither script nor judgment",
        (
            ".agent-guild/state/tasks/T-001.md",
            "C-1: .agent-guild/scripts/check-build.sh 'echo ok'",
            "C-1: bash -c 'echo ok'",
        ),
        False, "R4",
    ),
    (
        "R5 check_method script does not exist",
        (
            ".agent-guild/state/tasks/T-001.md",
            "C-1: .agent-guild/scripts/check-build.sh 'echo ok'",
            "C-1: .agent-guild/scripts/does-not-exist.sh 'echo ok'",
        ),
        False, "R5",
    ),
    (
        "R1 citation line past end of file",
        (".agent-guild/state/tasks/T-001.md", "lib/helper.py:6", "lib/helper.py:999"),
        False, "R1",
    ),
    (
        "R3 citation lands on a heading",
        (".agent-guild/state/tasks/T-001.md", "lib/helper.py:6", "lib/notes.md:5"),
        False, "R3",
    ),
    (
        "R8 no generated-tree task downstream of its inputs",
        (".agent-guild/state/tasks/T-002.md", "deps: [T-001]", "deps: []"),
        False, "R8",
    ),
    (
        "R2 citation line doesn't carry the quoted code",
        (".agent-guild/state/tasks/T-001.md", "lib/helper.py:6", "lib/helper.py:1"),
        False, "R2",
    ),
    (
        "R9 pass instructed alongside a major finding, no veto",
        (".agent-guild/state/tasks/T-002.md", "must never pass", "may still pass"),
        False, "R9",
    ),
    (
        "R10 count word disagrees with its list",
        (".agent-guild/state/tasks/T-001.md", "Three things matter here:", "Four things matter here:"),
        False, "R10",
    ),
    (
        "R12' the same restated fact carries two different counts",
        (".agent-guild/state/tasks/T-001.md", "Ten widgets ship broken", "Eleven widgets ship broken"),
        False, "R12",
    ),
]


def self_test():
    failures = []
    for name, mutation, expect_ok, needle in _SELF_TEST_CASES:
        with tempfile.TemporaryDirectory(prefix="check-job-spec-fixture-") as root:
            _write_fixture(root, mutation)
            proc = subprocess.run(
                [sys.executable, __file__, "--audit-id", "DEC-audit"],
                cwd=root, capture_output=True, text=True,
            )
            got_ok = proc.returncode == 0
            combined = proc.stdout + proc.stderr

            if got_ok != expect_ok:
                failures.append(
                    f"{name}: expected {'pass' if expect_ok else 'fail'}, got exit "
                    f"{proc.returncode} (stdout={proc.stdout!r} stderr={proc.stderr!r})"
                )
                continue

            if not expect_ok:
                if not combined.strip():
                    failures.append(f"{name}: failed with NO diagnostic message at all")
                    continue
                if "job-spec:" not in combined:
                    failures.append(f"{name}: diagnostic missing the 'job-spec:' prefix (got {combined!r})")
                    continue
                if needle not in combined:
                    failures.append(
                        f"{name}: diagnostic did not name the expected rule "
                        f"(expected {needle!r} in {combined!r})"
                    )
                    continue

    if failures:
        sys.stderr.write("SELF-TEST FAILED:\n")
        for m in failures:
            sys.stderr.write(f"  - {m}\n")
        return 1

    print(f"OK: self-test passed ({len(_SELF_TEST_CASES)} fixtures)")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Lint a guild job's constitution and task decomposition before an auditor is dispatched."
    )
    ap.add_argument("state", nargs="?", default=".agent-guild/state", help="path to the state directory")
    ap.add_argument("--repo-root", default=None, help="root citations and scripts resolve against (default: cwd)")
    ap.add_argument("--audit-id", choices=["CON-audit", "DEC-audit"], default="DEC-audit")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not os.path.isdir(args.state):
        sys.stderr.write(f"job-spec: state directory not found: {args.state}\n")
        return 3

    try:
        compose_brief = _load_module("compose_brief_cjs", "compose-brief.py")
        validate_verdict = _load_module("validate_verdict_cjs", "validate-verdict.py")
    except Exception as e:
        sys.stderr.write(f"job-spec: cannot import a kit script this linter depends on: {e}\n")
        return 3

    global DEFECT_SEVERITIES
    DEFECT_SEVERITIES = validate_verdict.DEFECT_SEVERITIES

    ctx, err = load_context(args.state, compose_brief)
    if err:
        sys.stderr.write(f"job-spec: {err}\n")
        return 3

    repo_root = args.repo_root or os.getcwd()
    msg = run_rules(ctx, args.audit_id, repo_root)
    if msg:
        sys.stderr.write(f"job-spec: {msg}\n")
        return 1

    print(f"OK: {args.state} passes check-job-spec ({args.audit_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
