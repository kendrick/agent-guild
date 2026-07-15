#!/usr/bin/env python3
"""Score a candidate's audition run. Stdlib only.

    score.py <run-dir>

<run-dir> holds A-001.txt, A-002.sh, A-003.txt, A-004.md as produced by the
candidate. Prints per-task pass/fail with reasons; exits 0 iff all four pass.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BANNED = ["unleash", "elevate", "seamless", "revolutionary", "game-changing",
          "empower", "transform", "journey"]


def score_a001(run):
    path = os.path.join(run, "A-001.txt")
    if not os.path.exists(path):
        return False, "A-001.txt missing"
    expected = open(os.path.join(HERE, "tasks", "A-001.expected")).read().split()
    got = open(path).read().split()
    if got == expected:
        return True, "exact sort match"
    return False, f"expected {expected}, got {got}"


def score_a002(run):
    path = os.path.join(run, "A-002.sh")
    if not os.path.exists(path):
        return False, "A-002.sh missing"
    want = "\n".join(
        "FizzBuzz" if n % 15 == 0 else "Fizz" if n % 3 == 0
        else "Buzz" if n % 5 == 0 else str(n)
        for n in range(1, 16)
    )
    try:
        out = subprocess.run(["bash", path], capture_output=True, text=True, timeout=15)
    except Exception as e:
        return False, f"script did not run: {e}"
    if out.stdout.strip() == want:
        return True, "fizzbuzz 1..15 correct"
    return False, f"output mismatch:\n{out.stdout.strip()}"


def score_a003(run):
    path = os.path.join(run, "A-003.txt")
    if not os.path.exists(path):
        return False, "A-003.txt missing"
    lines = [ln.strip() for ln in open(path).read().splitlines() if ln.strip()]
    if len(lines) != 5:
        return False, f"need exactly 5 lines, got {len(lines)}"
    for ln in lines:
        if len(ln.split()) > 10:
            return False, f"line over 10 words: {ln!r}"
        low = ln.lower()
        for w in BANNED:
            if w in low:
                return False, f"banned word {w!r} in: {ln!r}"
    return True, "5 lines, all within limits, no banned words"


def score_a004(run):
    path = os.path.join(run, "A-004.md")
    if not os.path.exists(path):
        return False, "A-004.md missing"
    text = open(path).read()
    m = re.search(r"^verdict:\s*(\w+)", text, re.MULTILINE)
    if not m:
        return False, "no verdict field"
    verdict = m.group(1).upper()
    if verdict == "ERROR":
        return True, "correctly returned ERROR for a check that can't run"
    return False, f"returned {verdict}; a missing check must be ERROR, not improvised"


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: score.py <run-dir>\n")
        return 3
    run = sys.argv[1]
    if not os.path.isdir(run):
        sys.stderr.write(f"not a directory: {run}\n")
        return 3

    scorers = [("A-001", score_a001), ("A-002", score_a002),
               ("A-003", score_a003), ("A-004", score_a004)]
    all_pass = True
    for name, fn in scorers:
        ok, reason = fn(run)
        all_pass = all_pass and ok
        print(f"  {'PASS' if ok else 'FAIL'} {name}  {reason}")
    print(f"\n{'ALL PASS' if all_pass else 'SOME FAILED'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
