#!/usr/bin/env python3
"""DEC-audit r0 reference implementation of T-002's deliverable.

Three archive-drawn mutation cases in `test_check_job_spec.py`, one per change,
each built the way T-002's excerpt describes: take real shipped paperwork from
`.agent-guild/state/archive/`, change one line, assert the rule fires. Numbered
M7/M8/M9 to continue the suite's own M1-M6 series.

Usage: patch_suite.py <tree>
"""
import sys

SUITE = ".agent-guild/scripts/test_check_job_spec.py"

INSERT_BEFORE = """        # ------------------------------------------- P1 (R2, #132 adversarial)"""

NEW_CASES = '''        # --------------------------------------------------------- M7 (R10)
        # #193's first shape. `dotfiles#22` shipped "Three further rules
        # constrain how:" over three bullets—a correct count that R10 could
        # not have checked, because an adjective between the number and the
        # noun switched the rule off entirely. Same corpus line M3 uses, with
        # a modifier inserted: the count is wrong AND the noun is displaced,
        # so a strict-adjacency predicate stays silent and this case goes red.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-006.md"),
                "record three findings",
                "record four separate findings",
                "M7",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M7 count disagrees through an adjective: exit 4 (heuristic)", rc == 4, f"rc={rc} err={err}")
                check("M7: R10 named", rule_hit(err, "R10"), f"err={err!r}")
                check("M7: names the count and the item total", "'four'" in err and "3 item" in err, f"err={err!r}")
                check("M7: no traceback", "Traceback" not in err, f"err={err!r}")

        # --------------------------------------------------------- M8 (R21)
        # #193's second shape. T-005 is a real judgment task: its only clause,
        # C-6, carries a `checker-judgment:` rubric. Flipping its own checker
        # to checker-deterministic is the misroute R21 exists to refuse—that
        # agent runs scripts and cannot apply a rubric at all.
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
                check("M8 rubric handed to a deterministic checker: exit 1 (proof)", rc == 1, f"rc={rc} err={err}")
                check("M8: R21 named", rule_hit(err, "R21"), f"err={err!r}")
                check("M8: names the task", "T-005" in err, f"err={err!r}")
                check("M8: names the offending clause", "C-6" in err, f"err={err!r}")
                check("M8: no traceback", "Traceback" not in err, f"err={err!r}")

        # ---------------------------------------------------------- M9 (R2)
        # #193's third shape, on M1's own stale citation. The diagnostic has
        # to quote the anchor it matched and say where that anchor sits, or an
        # author cannot tell a wrong citation from a wrongly-chosen anchor.
        # Asserting the anchor TEXT is what makes this case discriminate:
        # M1 already covers "R2 fired".
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
                anchor = 'val[0] == val[-1]'
                check("M9 stale citation: exit 4 (heuristic)", rc == 4, f"rc={rc} err={err}")
                check("M9: R2 named", rule_hit(err, "R2"), f"err={err!r}")
                check("M9: the diagnostic quotes the anchor it matched",
                      anchor in err, f"err={err!r}")
                check("M9: and says where that anchor sits",
                      "tasks/T-001.md:57" in err or "that same line" in err, f"err={err!r}")
                check("M9: no traceback", "Traceback" not in err, f"err={err!r}")

'''


def main(tree):
    p = f"{tree}/{SUITE}"
    with open(p, encoding="utf-8") as f:
        src = f.read()
    if src.count(INSERT_BEFORE) != 1:
        raise SystemExit("insertion anchor not unique")
    src = src.replace(INSERT_BEFORE, NEW_CASES + INSERT_BEFORE, 1)
    with open(p, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"patched suite at {p}")


if __name__ == "__main__":
    main(sys.argv[1])
