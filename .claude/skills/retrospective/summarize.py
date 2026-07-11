#!/usr/bin/env python3
"""Tally a guild run from state/ for the retrospective. Stdlib only.

    summarize.py [--project DIR]

Reads verdicts, tasks, disputes, and logs; prints counts the retrospective
turns into prose. Read-only—it never edits state.
"""
import argparse
import os
import re
import sys


def fm(text, key):
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.environ.get("CLAUDE_PROJECT_DIR"))
    args = ap.parse_args()
    root = args.project or os.getcwd()
    state = os.path.join(root, "state")
    if not os.path.isdir(state):
        sys.stderr.write(f"no state/ under {root}\n")
        return 3

    def readdir(sub):
        d = os.path.join(state, sub)
        if not os.path.isdir(d):
            return []
        out = []
        for n in sorted(os.listdir(d)):
            if n.endswith(".md"):
                with open(os.path.join(d, n)) as f:
                    out.append((n, f.read()))
        return out

    # Verdicts
    verdicts = readdir("verdicts")
    counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}
    fails_by_checker = {}
    for name, text in verdicts:
        v = fm(text, "verdict").upper()
        if v in counts:
            counts[v] += 1
        if v == "FAIL":
            c = fm(text, "checker") or "unknown"
            fails_by_checker[c] = fails_by_checker.get(c, 0) + 1

    # Tasks
    tasks = readdir("tasks")
    task_rows = []
    for name, text in tasks:
        tid = fm(text, "id") or name[:-3]
        status = fm(text, "status")
        retries = fm(text, "retries")
        esc = fm(text, "escalations")
        escalated = bool(esc) and esc not in ("[]", "")
        task_rows.append((tid, status, retries, escalated))

    # Disputes
    disputes = readdir("disputes")
    dispute_rows = [(name[:-3], fm(text, "status") or "open") for name, text in disputes]

    # Logs
    esc_log = os.path.join(state, "log", "escalations.log")
    esc_lines = sum(1 for _ in open(esc_log)) if os.path.exists(esc_log) else 0
    stalled = os.path.exists(os.path.join(state, "STALLED.md"))

    # Report
    print("=== guild run summary ===")
    print(f"tasks: {len(task_rows)}   verdicts: {len(verdicts)}   "
          f"disputes: {len(dispute_rows)}")
    print(f"verdicts: PASS={counts['PASS']} FAIL={counts['FAIL']} "
          f"ERROR={counts['ERROR']}")
    print(f"catches (FAIL verdicts): {counts['FAIL']}")
    if fails_by_checker:
        for c, n in sorted(fails_by_checker.items()):
            print(f"  by {c}: {n}")
    print(f"escalations logged: {esc_lines}")
    if counts["ERROR"]:
        print(f"check-infra debt: {counts['ERROR']} ERROR verdict(s)—checks that could not run")
    if stalled:
        print("STALL: state/STALLED.md present—the stop gate gave up on a stuck loop")

    strained = [r for r in task_rows if (r[2] not in ("", "0")) or r[3]]
    if strained:
        print("strained tasks:")
        for tid, status, retries, escalated in strained:
            tag = " escalated" if escalated else ""
            print(f"  {tid} [{status}] retries={retries or 0}{tag}")

    if dispute_rows:
        print("disputes:")
        for did, status in dispute_rows:
            print(f"  {did}: {status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
