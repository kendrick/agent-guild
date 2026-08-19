#!/usr/bin/env python3
"""DEC-audit r1 apparatus: T-002's deliverable, built to the constitution's
C-9 and T-002's excerpt. Three cases in `test_check_job_spec.py`, each drawn
from the archived #117 corpus in the M1-M6 mutation style.

usage: patch_suite.py <tree> [nocov]

`nocov` builds the vC9_nocov attack: M9 keeps asserting R2 fired and drops
the assertion that the diagnostic quotes the anchor.
"""
import sys
import os

SUITE = ".agent-guild/scripts/test_check_job_spec.py"

ANCHOR = ("        if len(val) >= 2 and val[0] == val[-1] and val[0] in "
          "\"\\\"'\":")

NEW_CASES = '''
        # --------------------------------------------------------- M7 (R10)
        # #193's first change. The corpus line already carries a count over
        # its own list; putting a modifier between the count and its noun is
        # what the shipped predicate cannot see through, so this case is red
        # on the strict adjacency and green only on the relaxation.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-006.md"),
                "record three findings",
                "record four further findings",
                "M7",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M7 count separated from its noun by a modifier: exit 4 (heuristic)",
                      rc == 4, f"rc={rc} err={err}")
                check("M7: R10 named", rule_hit(err, "R10"), f"err={err!r}")
                check("M7: names the count and the item total",
                      "four" in err.lower() and re.search(r"\\b3\\b", err) is not None,
                      f"err={err!r}")
                check("M7: no traceback", "Traceback" not in err, f"err={err!r}")

        # --------------------------------------------------------- M8 (R21)
        # #193's second change. T-005 cites C-6, whose check is a
        # `checker-judgment:` rubric, and routes it to a judgment checker.
        # Flipping that one line is the misrouting the routing table has
        # never had a rule for.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-005.md"),
                "checker: checker-judgment",
                "checker: checker-deterministic",
                "M8",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M8 deterministic checker holding a rubric: exit 1 (proof)",
                      rc == 1, f"rc={rc} err={err}")
                check("M8: R21 named", rule_hit(err, "R21"), f"err={err!r}")
                check("M8: names the task", "T-005" in err, f"err={err!r}")
                check("M8: names the offending clause", "C-6" in err, f"err={err!r}")
                check("M8: no traceback", "Traceback" not in err, f"err={err!r}")

        # ---------------------------------------------------------- M9 (R2)
        # #193's third change, on M1's own mutation: the same stale citation,
        # asserting what the diagnostic now has to say. Numbers alone were
        # never the problem—the author could already see both of those.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-001.md"),
                ".agent-guild/scripts/compose-brief.py:64",
                ".agent-guild/scripts/compose-brief.py:58",
                "M9",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M9 stale citation still fires R2", rule_hit(err, "R2"), f"err={err!r}")
                r2 = next((l for l in err.splitlines() if rule_hit(l, "R2")), "")
ANCHOR_ASSERTIONS
                check("M9: no traceback", "Traceback" not in err, f"err={err!r}")
'''

ANCHOR_ASSERTIONS = '''                check("M9: the diagnostic quotes the anchor it matched",
                      M9_ANCHOR in r2 or repr(M9_ANCHOR)[1:-1] in r2,
                      f"r2={r2!r}")
                check("M9: and says where that anchor sits in the citing document",
                      re.search(r"tasks/T-001\\.md[: ]\\D{0,12}57\\b", r2) is not None
                      or "same line" in r2,
                      f"r2={r2!r}")'''

NOCOV_ASSERTIONS = '''                check("M9: exit 4, the heuristic code", rc == 4, f"rc={rc}")'''

ANCHOR_CONST = '''
# The anchor `nearest_anchor` picks for T-001's compose-brief.py citation,
# quoted verbatim off the corpus at
# archive/2026-08-10-issue-117/tasks/T-001.md:57.
M9_ANCHOR = (
    "if len(val) >= 2 and val[0] == val[-1] and val[0] in "
    + '"' + "\\\\" + '"' + "'" + '"'
)
'''


def main():
    tree = sys.argv[1]
    nocov = len(sys.argv) > 2 and sys.argv[2] == "nocov"
    path = os.path.join(tree, SUITE)
    with open(path, encoding="utf-8") as f:
        src = f.read()

    marker = "        # ------------------------------------------- P1 (R2, #132 adversarial)"
    if src.count(marker) != 1:
        raise SystemExit(f"patch_suite: marker not found once ({src.count(marker)})")

    body = NEW_CASES.replace(
        "ANCHOR_ASSERTIONS", NOCOV_ASSERTIONS if nocov else ANCHOR_ASSERTIONS)
    src = src.replace(marker, body + "\n" + marker, 1)

    # Module-scope constant, above the corpus block.
    head = "def mutate(path, old, new, label):"
    if src.count(head) != 1:
        raise SystemExit("patch_suite: no place for the anchor constant")
    src = src.replace(head, ANCHOR_CONST.strip("\n") + "\n\n\n" + head, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"patched {path} ({'nocov' if nocov else 'full'})")


if __name__ == "__main__":
    main()
