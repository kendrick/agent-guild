#!/usr/bin/env python3
"""Classify #34's courier-crossing corpus by what produced each in-family finding.

#34 asks whether a cross-family checker finds what a same-family one misses. Its
headline measure is the unique-finding rate, and that measure is confounded: the
checker of record has repository access and can run things, while the courier is
blind by contract. A unique in-family finding might mean the family saw more, or
it might mean the checker ran a command the lane structurally cannot.

Hand-classification of one run put every classifiable unique finding in the
second bucket, but eleven tasks could not be classified from their comparison
prose at all. This recovers what the prose lost, from the verdicts, which carry
an `evidence` field per finding whose SHAPE says what produced it:

    "tests/lint.bats:50"                  a citation
    "$ bats tests/ -> 5 passed"           command output, so execution happened

Reading a file the brief never inlined also needs access, so a citation is
indeterminate rather than access-free. The courier's prompt (brief plus inlined
artifacts) is not persisted, so nothing on disk can settle which citations the
far side could have checked itself. That makes execution-derived a floor, not a
count, and this script reports it as one.

    scripts/classify-crossings.py [REPO ...]      (default: the three known repos)
    scripts/classify-crossings.py --json          machine-readable, for backfill

For a task whose comparison block records `unique_checker: N`, the script bounds
how many of those N were access-derived rather than guessing:

    every finding execution-derived   -> exactly N
    no finding execution-derived     -> exactly 0
    mixed                            -> a range, reported as a range

Stdlib only. Read-only: it never edits a task file. Backfilling
`unique_checker_access_derived` from a bound is a separate, deliberate step.
"""
import argparse
import glob
import json
import os
import re
import sys

DEFAULT_REPOS = [
    os.path.expanduser("~/repos/agent-guild"),
    os.path.expanduser("~/repos/skills"),
    os.path.expanduser("~/repos/dotfiles"),
]

# A citation is a bare path with a line or line range and nothing else. Anything
# with output shape in it -- a shell prompt, a TAP line, a traceback, a counted
# result, more than one line -- means something ran. Deliberately conservative:
# an ambiguous string counts as a citation, so the execution figure stays a floor.
CITATION = re.compile(r"^[\w./@-]+:\d+(-\d+)?$")
RAN_SOMETHING = re.compile(
    r"\$ |\n|exit code|passed|failed|\bok \d|not ok|Traceback|stdout|stderr|"
    r"-> |=> |returns? \d|Counter\(|\bwc -l\b|\bgrep\b|\bdiff\b",
    re.I,
)

UNIQUE_CHECKER = re.compile(r"^unique_checker:\s*(\S+)", re.M)
ACCESS_FIELD = re.compile(r"^unique_checker_access_derived:\s*(\S+)", re.M)


def evidence_kind(evidence):
    """'execution' | 'citation'. Ambiguity resolves to citation on purpose:
    this feeds a floor on access-derived findings, and a floor that guesses
    upward is not a floor."""
    ev = (evidence or "").strip()
    if not ev:
        return "citation"
    if CITATION.match(ev):
        return "citation"
    return "execution" if RAN_SOMETHING.search(ev) else "citation"


def bound(unique, total, execution):
    """(low, high) on how many of `unique` findings were execution-derived, or
    (None, None) when the corpus contradicts itself.

    Which specific findings were unique is a human judgment recorded in prose,
    not something the verdict files mark, so this brackets rather than resolves.
    The two ends meet when every finding shares one kind.

    A comparison block claiming more unique findings than its verdict of record
    carries is not a bound to compute, it is a discrepancy to report: the prose
    counted something the verdict never recorded, so neither number can be
    trusted for that task."""
    if unique in (None, 0):
        return 0, 0
    if unique > total:
        return None, None
    citations = total - execution
    return max(0, unique - citations), min(unique, execution)


def read_task_block(path):
    """(unique_checker, access_derived_already_recorded) from a task file."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return None, None
    m = UNIQUE_CHECKER.search(text)
    a = ACCESS_FIELD.search(text)
    to_int = lambda x: int(x) if x and x.isdigit() else None
    return to_int(m.group(1) if m else None), to_int(a.group(1) if a else None)


def scan(repo):
    """Every task in `repo`'s archives that has both a verdict of record and a
    recorded courier comparison."""
    rows = []
    pattern = os.path.join(repo, ".agent-guild/state/archive/*/tasks/*.md")
    for task_path in sorted(glob.glob(pattern)):
        run = os.path.basename(os.path.dirname(os.path.dirname(task_path)))
        tid = os.path.basename(task_path)[:-3]
        unique, recorded = read_task_block(task_path)
        vdir = os.path.join(os.path.dirname(os.path.dirname(task_path)), "verdicts")
        total = execution = 0
        seen_verdict = False
        for vpath in sorted(glob.glob(os.path.join(vdir, f"{tid}-*.json"))):
            # the verdict of record only; a lane suffix is the courier's own
            if vpath.endswith(("-codex.json", "-claude.json")):
                continue
            try:
                data = json.load(open(vpath, encoding="utf-8"))
            except Exception:
                continue
            seen_verdict = True
            for finding in data.get("findings") or []:
                total += 1
                if evidence_kind(finding.get("evidence")) == "execution":
                    execution += 1
        if not seen_verdict:
            continue
        low, high = bound(unique, total, execution)
        rows.append({
            "inconsistent": low is None,
            "repo": os.path.basename(os.path.realpath(repo)),
            "run": run, "task": tid,
            "findings": total, "execution_derived": execution,
            "unique_checker": unique,
            "access_derived_recorded": recorded,
            "access_derived_low": low, "access_derived_high": high,
            "resolved": low is not None and low == high,
        })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos", nargs="*", default=DEFAULT_REPOS)
    ap.add_argument("--json", action="store_true", help="emit rows as JSON")
    args = ap.parse_args(argv)

    rows = []
    for repo in (args.repos or DEFAULT_REPOS):
        if not os.path.isdir(repo):
            sys.stderr.write(f"classify-crossings: no such repo: {repo}\n")
            return 3
        rows.extend(scan(repo))

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    if not rows:
        print("no archived tasks with a verdict of record found")
        return 0

    print(f"{'repo':<12} {'run':<24} {'task':<7} {'find':>5} {'exec':>5} "
          f"{'uniq':>5} {'access-derived':>15}")
    for r in rows:
        if r["inconsistent"]:
            span = "INCONSISTENT"
        elif r["resolved"]:
            span = str(r["access_derived_low"])
        else:
            span = f'{r["access_derived_low"]}-{r["access_derived_high"]}' 
        print(f'{r["repo"]:<12} {r["run"]:<24} {r["task"]:<7} '
              f'{r["findings"]:>5} {r["execution_derived"]:>5} '
              f'{str(r["unique_checker"] if r["unique_checker"] is not None else "-"):>5} '
              f'{span:>15}')

    total = sum(r["findings"] for r in rows)
    execution = sum(r["execution_derived"] for r in rows)
    bad = [r for r in rows if r["inconsistent"]]
    with_unique = [r for r in rows if r["unique_checker"] and not r["inconsistent"]]
    resolved = [r for r in with_unique if r["resolved"]]
    print(f"\n{len(rows)} tasks, {total} in-family findings, "
          f"{execution} execution-derived ({execution / total * 100:.0f}% floor)")
    print(f"{len(with_unique)} tasks recorded a unique checker finding; "
          f"{len(resolved)} resolve to an exact count from evidence shape alone")
    if with_unique:
        lo = sum(r["access_derived_low"] for r in with_unique)
        hi = sum(r["access_derived_high"] for r in with_unique)
        uniq = sum(r["unique_checker"] for r in with_unique)
        print(f"of {uniq} unique in-family findings, "
              f"{lo}-{hi} were access-derived")
    if bad:
        print(f"\n{len(bad)} task(s) claim more unique findings than their verdict "
              f"of record carries, so neither number is usable for them:")
        for r in bad:
            print(f'  {r["repo"]}/{r["run"]}/{r["task"]}: '
                  f'unique_checker={r["unique_checker"]} but '
                  f'{r["findings"]} finding(s) in the verdict')
    return 0


if __name__ == "__main__":
    sys.exit(main())
