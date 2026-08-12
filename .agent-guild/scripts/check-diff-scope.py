#!/usr/bin/env python3
"""The standard scoped-diff check: fail loud if the working tree touches a
path outside an explicit allowlist.

Nearly every guild constitution carries a "the job's diff touches only these
paths" clause. Hand-rolled as judgment prose, it's opus-tier spend on a
listing rule, re-phrased—and occasionally mis-phrased—per job. This makes it
mechanical, so the clause routes to checker-deterministic (haiku) instead.

    .agent-guild/scripts/check-diff-scope.py ALLOWED... [--ignore PATH]...

ALLOWED arguments: an exact file path, or a directory prefix if the argument
ends with `/` (covers everything under it, e.g. `plugin/` covers
`plugin/hooks/hooks.json`).

--ignore PATH, repeatable: a known user-owned path (typically untracked)
excluded from judgment—the honest escape hatch for files the job legitimately
didn't create but shouldn't be held to the allowlist either.

--task-file tasks/T-NNN.md: scope the check to a task's own `owns:`
frontmatter instead of (or in addition to) the ALLOWED positional
arguments—#133's per-task ownership list, the thing that makes concurrent
dispatch safe. `owns:` entries are the same two shapes as ALLOWED: an exact
file path, or a directory prefix ending in `/`. A missing or empty `owns:`
fails closed—exit 3, not a silent pass—because a task with no declared
ownership has nothing this flag can verify.

Paths under `.agent-guild/state/` are always permitted (job bookkeeping the
kit itself writes) and need no allowlist entry.

Run from the repo root, like the kit's other scripts—git's relative paths
only line up against ALLOWED/--ignore/--task-file arguments when cwd is the
toplevel.

The path set is the union of `git status --porcelain` and
`git diff --name-only`. Rename syntax (`old -> new`, which `git status`
emits for a detected rename) resolves to the new path—a rename that lands
back in scope shouldn't trip the check on its own history.

Exit codes: 0 every changed path is in scope, one `OK:` line to stdout; 1 one
or more paths are out of scope, each named on stderr as
`check-diff-scope: out of scope: <path>`; 3 usage/infra error (not a git
repo, a git command itself failed, or --task-file names a task with a
missing/empty `owns:`).

`paths_overlap(a, b)` below is the single home for "do these two ownership
paths overlap" semantics—check-job-spec.py's R13 ownership-overlap rule
imports it via the `_load_module` importlib idiom (see that script's own
docstring), rather than re-deriving the same exact/prefix logic a second
time.

Stdlib only, so the kit stays copy-in portable.
"""
import argparse
import re
import subprocess
import sys


def _resolve_rename(raw):
    """A git status/diff path token, with rename syntax ('old -> new')
    resolved to just the new path—scope is about where the file ends up,
    not what it used to be called."""
    if " -> " in raw:
        return raw.split(" -> ", 1)[1]
    return raw


def _parse_porcelain(text):
    """Parse `git status --porcelain` (v1) output. Each line is a 2-char
    XY status, a space, then a path (or 'orig -> new' for a detected
    rename/copy)—so the path always starts at index 3."""
    paths = []
    for line in text.splitlines():
        if not line:
            continue
        paths.append(_resolve_rename(line[3:]))
    return paths


def _parse_name_only(text):
    """Parse `git diff --name-only` output: one path per line. Rename
    syntax isn't normally emitted here, but resolving it too costs nothing
    and keeps both parsers honest about the same contract."""
    return [_resolve_rename(line) for line in text.splitlines() if line]


def _in_git_repo():
    proc = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _run_git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def collect_changed_paths():
    """Union of `git status --porcelain` and `git diff --name-only`,
    deduplicated, order preserved (first-seen wins)—stable output makes the
    OK:/offender lines reproducible run to run.

    --untracked-files=all is not optional: git's default collapses a wholly
    new directory into a single `dir/` entry instead of listing the files
    inside it, which would silently defeat directory-prefix matching (and
    the .agent-guild/state/ carve-out) the moment a job's first file in a
    new directory lands."""
    paths = _parse_porcelain(_run_git("status", "--porcelain", "--untracked-files=all"))
    paths += _parse_name_only(_run_git("diff", "--name-only"))
    seen = set()
    unique = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def paths_overlap(a, b):
    """True if ownership paths `a` and `b` denote overlapping territory.
    Each is either an exact file path or a directory prefix ending in
    '/'—the same two shapes ALLOWED and `owns:` entries both take. Two
    directories overlap if either is nested inside (or equal to) the
    other; a directory and a file overlap if the file sits under it; two
    files overlap only if they're the same path. `a` and `b` are
    interchangeable—the check is symmetric—which matters to a caller like
    R13 comparing two tasks' owns lists pairwise without caring which one
    it read first."""
    a_is_dir = a.endswith("/")
    b_is_dir = b.endswith("/")
    if a_is_dir and b_is_dir:
        return a.startswith(b) or b.startswith(a)
    if a_is_dir:
        return b.startswith(a)
    if b_is_dir:
        return a.startswith(b)
    return a == b


def in_scope(path, allowed_files, allowed_dirs, ignored):
    if path in allowed_files:
        return True
    if path in ignored:
        return True
    if path.startswith(".agent-guild/state/"):
        return True
    return any(paths_overlap(path, prefix) for prefix in allowed_dirs)


TASK_OWNS_KEY_RE = re.compile(r"^owns:\s*(.*)$")
TASK_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")


def _strip_matching_quotes(s):
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def read_task_owns(task_path):
    """Parse a task file's `owns:` frontmatter field: the flat `[a, b]`
    form on the key's own line, or a block `- path` sequence beneath it—
    the same two shapes check-job-spec.py's parse_artifacts handles for
    `artifacts:`, since the template documents `owns:` in that same
    frontmatter convention. Returns a list of path strings (possibly
    empty if the key is present but blank, or absent altogether—the
    caller is what turns "empty" into the fail-closed exit 3, not this
    function). Raises OSError if the file can't be read."""
    with open(task_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    fm_lines = []
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        fm_lines.append(line)
    if not closed:
        return []
    for i, line in enumerate(fm_lines):
        m = TASK_OWNS_KEY_RE.match(line)
        if not m:
            continue
        val = m.group(1).strip()
        if val.startswith("["):
            inner = val[1:-1] if val.endswith("]") else val[1:]
            inner = inner.strip()
            if not inner:
                return []
            return [_strip_matching_quotes(p.strip()) for p in inner.split(",") if p.strip()]
        items = []
        for later in fm_lines[i + 1:]:
            m2 = TASK_LIST_ITEM_RE.match(later)
            if m2 is None:
                break
            items.append(_strip_matching_quotes(m2.group(1).strip()))
        return items
    return []


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=(
            "Fail if the working tree's diff touches a path outside an "
            "explicit allowlist."
        )
    )
    ap.add_argument(
        "allowed",
        nargs="*",
        metavar="ALLOWED",
        help="an exact file path, or a directory prefix ending in '/'",
    )
    ap.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATH",
        help="a known user-owned path to exclude from judgment (repeatable)",
    )
    ap.add_argument(
        "--task-file",
        default=None,
        metavar="PATH",
        help="scope the check to this task's own `owns:` frontmatter",
    )
    args = ap.parse_args(argv)

    if not _in_git_repo():
        sys.stderr.write("check-diff-scope: not inside a git repository\n")
        return 3

    allowed_files = {p for p in args.allowed if not p.endswith("/")}
    allowed_dirs = tuple(p for p in args.allowed if p.endswith("/"))
    ignored = set(args.ignore)

    if args.task_file:
        try:
            owns = read_task_owns(args.task_file)
        except OSError as e:
            sys.stderr.write(f"check-diff-scope: cannot read --task-file {args.task_file}: {e}\n")
            return 3
        if not owns:
            sys.stderr.write(
                f"check-diff-scope: --task-file {args.task_file} has a missing or empty "
                "`owns:` field\n"
            )
            return 3
        allowed_files |= {p for p in owns if not p.endswith("/")}
        allowed_dirs = allowed_dirs + tuple(p for p in owns if p.endswith("/"))

    try:
        paths = collect_changed_paths()
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"check-diff-scope: git command failed: {e}\n")
        return 3

    offenders = [
        p for p in paths if not in_scope(p, allowed_files, allowed_dirs, ignored)
    ]

    if offenders:
        for p in offenders:
            sys.stderr.write(f"check-diff-scope: out of scope: {p}\n")
        return 1

    print(f"OK: {len(paths)} path(s) in scope")
    return 0


if __name__ == "__main__":
    sys.exit(main())
