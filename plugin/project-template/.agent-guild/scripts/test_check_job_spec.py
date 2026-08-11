#!/usr/bin/env python3
"""Regression suite for check-job-spec.py (#132). Two kinds of case:

1. The real #117 corpus (`.agent-guild/state/archive/2026-08-10-issue-117/`)
   must still pass, run against a pinned fixture repo-root rather than this
   live repo. The corpus cites `conventions.md:65`, and that line still
   resolves in the live repo today, but it no longer names the bullet it
   did when #117 shipped: #117's own commit grew the file out from under
   its own citation. A test pinned to live files rots the moment someone
   edits them, so the fixture repo-root fixes the cited files' line
   numbers by construction instead.
2. Each of #117's own audit findings, reproduced as a one-line mutation of
   that same corpus, must fire the rule that would have caught it.

Every script runs as a subprocess, so these tests exercise the real CLI
contract (exit codes, stderr) rather than internals.

Run: python3 .agent-guild/scripts/test_check_job_spec.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPTS_DIR, "check-job-spec.py")
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPTS_DIR))
ARCHIVE_DIR = os.path.join(
    REPO_ROOT, ".agent-guild", "state", "archive", "2026-08-10-issue-117"
)

passed = failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {label}")
    else:
        failed += 1
        print(f"  FAIL {label}  {detail}")


def run_linter(*argv):
    proc = subprocess.run(
        [sys.executable, SCRIPT, *argv], capture_output=True, text=True
    )
    return proc.returncode, proc.stdout, proc.stderr


def rule_hit(err, rule):
    """A rule id appears as its own token, e.g. don't let a search for R1
    match inside R10 or R12."""
    return re.search(rf"(?<!\d){re.escape(rule)}(?!\d)", err) is not None


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_exec(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(path, 0o755)


def mutate(path, old, new, label):
    """Apply a one-line string replacement and prove it actually landed—a
    mutation that silently no-ops (because the corpus text moved under it)
    would make the case that follows pass for no reason."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    count = content.count(old)
    check(f"{label}: mutation string found exactly once", count == 1, f"count={count} old={old!r}")
    if count != 1:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace(old, new, 1))
    return True


def copy_corpus_state(state_dir):
    """The linter's own inputs are just constitution.md + tasks/; the rest
    of the archive (verdicts, notes, log, briefs) is run history it never
    reads."""
    os.makedirs(state_dir)
    shutil.copy(
        os.path.join(ARCHIVE_DIR, "constitution.md"),
        os.path.join(state_dir, "constitution.md"),
    )
    shutil.copytree(
        os.path.join(ARCHIVE_DIR, "tasks"), os.path.join(state_dir, "tasks")
    )


# The matching-pair quote-strip line the corpus cites twice (T-001.md:57,
# against compose-brief.py:64 and check-provenance.py:74). Built by
# concatenation rather than an escaped literal so the quoting is legible;
# verified byte-for-byte against the real compose-brief.py:64 while writing
# this suite.
MATCH_LINE = (
    "        if len(val) >= 2 and val[0] == val[-1] and val[0] in "
    + '"' + "\\" + '"' + "'" + '"' + ":"
)


def build_fixture_repo_root(root):
    """A pinned stand-in for the repo root, holding only what the corpus
    actually needs. compose-brief.py and check-provenance.py carry the
    cited snippet on the exact line the corpus cites (:64 and :74)
    regardless of what the live copies say today; conventions.md is pinned
    the same way for its :65 citations. check-build.sh and
    check-diff-scope.py are executable stubs, since R5 never runs them—it
    only checks X_OK and, for check-build.sh, that the quoted inner command
    parses—so their bodies don't need to do anything.

    Returns the line number of the fixture's "## Prose Voice" heading, which
    M2 redirects a citation onto.
    """
    scripts_dir = os.path.join(root, ".agent-guild", "scripts")
    os.makedirs(scripts_dir)
    wm_dir = os.path.join(root, "_working-memory")
    os.makedirs(wm_dir)

    write_exec(os.path.join(scripts_dir, "check-build.sh"), "#!/usr/bin/env bash\nexit 0\n")
    write_exec(
        os.path.join(scripts_dir, "check-diff-scope.py"),
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n",
    )

    # compose-brief.py: line 64 pinned to the cited snippet. Filler lines
    # avoid a leading '#'—R3's heading check is scoped to .md targets, but
    # there's no reason to hand a stray edge case a chance to misfire here.
    cb_lines = [f"x_{i} = None  # filler" for i in range(1, 64)]
    cb_lines.append(MATCH_LINE)  # line 64
    cb_lines += [f"x_{i} = None  # filler" for i in range(65, 70)]
    write_lines(os.path.join(scripts_dir, "compose-brief.py"), cb_lines)

    # check-provenance.py: same snippet, pinned at line 74.
    cp_lines = [f"x_{i} = None  # filler" for i in range(1, 74)]
    cp_lines.append(MATCH_LINE)  # line 74
    cp_lines += [f"x_{i} = None  # filler" for i in range(75, 80)]
    write_lines(os.path.join(scripts_dir, "check-provenance.py"), cp_lines)

    # conventions.md: the Prose Voice bullet pinned at line 65 (what every
    # unmutated "conventions.md:65" citation in the corpus resolves to), with
    # a real heading earlier in the file for M2 to redirect onto.
    conv_lines = [f"<!-- filler {i} -->" for i in range(1, 60)]
    prose_heading_line = 60
    conv_lines.append("## Prose Voice (docs and comments)")  # line 60
    conv_lines += [f"<!-- filler {i} -->" for i in range(61, 65)]
    conv_lines.append(
        "- Em dashes chain directly to the text on both sides—like this—never "
        "wrapped in spaces. Don't hard-wrap prose lines; let the display wrap. "
        "Headings are Title Case. Comments explain the why, not the what."
    )  # line 65
    conv_lines += [f"<!-- filler {i} -->" for i in range(66, 70)]
    write_lines(os.path.join(wm_dir, "conventions.md"), conv_lines)

    return prose_heading_line


MINIMAL_CONSTITUTION = """# Constitution: CLI fixture

## Clauses

### C-1: trivial clause
- **text**: The output file exists and is non-empty.
- **check**: checker-judgment: confirm the output file exists and has content.
- **severity**: minor
- **failing example**: the output file is empty or missing.

## Protected content

- none.

## Non-goals

- none.
"""


def raw_shell_constitution(check_line):
    return f"""# Constitution: R4 fixture

## Clauses

### C-1: build succeeds
- **text**: The build passes.
- **check**: {check_line}
- **severity**: minor
- **failing example**: the build never runs.

## Protected content

- none.

## Non-goals

- none.
"""


# --------------------------------------------------------------- CLI basics
print("CLI basics")

rc, out, err = run_linter("--self-test")
check("--self-test: exit 0", rc == 0, f"rc={rc} err={err}")

with tempfile.TemporaryDirectory() as d:
    missing_state = os.path.join(d, "does-not-exist")
    rc, out, err = run_linter(missing_state, "--repo-root", d, "--audit-id", "CON-audit")
    check("missing state dir: exit 3, not 1", rc == 3, f"rc={rc} err={err}")

with tempfile.TemporaryDirectory() as d:
    state = os.path.join(d, "state")
    os.makedirs(os.path.join(state, "tasks"))
    write_lines(os.path.join(state, "constitution.md"), MINIMAL_CONSTITUTION.splitlines())
    rc, out, err = run_linter(state, "--repo-root", d, "--audit-id", "DEC-audit")
    check("empty tasks/, DEC-audit: exit 1", rc == 1, f"rc={rc} err={err}")

    rc, out, err = run_linter(state, "--repo-root", d, "--audit-id", "CON-audit")
    check("same empty tasks/, CON-audit: exit 0, not 1", rc == 0, f"rc={rc} err={err}")

# ------------------------------------------------------- R4: #121's criterion
print("R4: inline shell in a check field (#121)")

with tempfile.TemporaryDirectory() as d:
    state = os.path.join(d, "state")
    os.makedirs(os.path.join(state, "tasks"))
    write_lines(
        os.path.join(state, "constitution.md"),
        raw_shell_constitution("bash -c 'pytest && echo ok'").splitlines(),
    )
    rc, out, err = run_linter(state, "--repo-root", d, "--audit-id", "CON-audit")
    check("bash -c wrapping a shell block: exit 1", rc == 1, f"rc={rc} err={err}")
    check("bash -c wrapping a shell block: R4 named", rule_hit(err, "R4"), f"err={err!r}")
    check("bash -c wrapping a shell block: no traceback", "Traceback" not in err, f"err={err!r}")

with tempfile.TemporaryDirectory() as d:
    state = os.path.join(d, "state")
    os.makedirs(os.path.join(state, "tasks"))
    write_lines(
        os.path.join(state, "constitution.md"),
        raw_shell_constitution("pytest && echo ok").splitlines(),
    )
    rc, out, err = run_linter(state, "--repo-root", d, "--audit-id", "CON-audit")
    check("raw pipeline, no .agent-guild/scripts/ prefix: exit 1", rc == 1, f"rc={rc} err={err}")
    check("raw pipeline: R4 named", rule_hit(err, "R4"), f"err={err!r}")

# The other side of #121's line: a shell one-liner handed to the sanctioned
# runner is NOT the defect. Every check-build.sh invocation in the corpus
# (constitution C-1/C-3, T-002, T-003's two check-build.sh segments) is
# exactly that shape, so the base corpus pass below—run unmutated—is the
# proof this side stays green. T-003.md:13 in particular wraps a bespoke
# one-liner this way and DEC-r4 passed it.

# --------------------------------------------- corpus: baseline + mutations
if not os.path.isdir(ARCHIVE_DIR):
    print(f"note: corpus archive not found at {ARCHIVE_DIR} — skipping corpus-based "
          f"cases (the archive ships via copytree into user projects, where it won't exist)")
else:
    with tempfile.TemporaryDirectory() as fixture_root:
        prose_heading_line = build_fixture_repo_root(fixture_root)

        # ------------------------------------------------------- corpus: baseline
        print("corpus: the shipped #117 state (DEC-audit-r4 PASS)")

        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
            # This single exit-0 also carries two things called out in the plan
            # that don't get their own case: R9 doesn't fire on any of T-007's
            # four load-bearing sentences (including "an absent fact is a FAIL,
            # never a pass carrying a finding"—the very fix M4 below reverts),
            # and every check-build.sh-wrapped shell block in the corpus passes
            # R4 (the other side of the #121 test above).
            check("unmutated corpus: exit 0", rc == 0, f"rc={rc} err={err}")

        # ---------------------------------------------------------- M1 (R2)
        # DEC-r0's D5: a citation stale by six lines (compose-brief.py:64 was
        # :58 by the time the auditor checked it).
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-001.md"),
                ".agent-guild/scripts/compose-brief.py:64",
                ".agent-guild/scripts/compose-brief.py:58",
                "M1",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M1 stale code citation: exit 1", rc == 1, f"rc={rc} err={err}")
                check("M1: R2 named", rule_hit(err, "R2"), f"err={err!r}")
                check("M1: no traceback", "Traceback" not in err, f"err={err!r}")

        # ---------------------------------------------------------- M2 (R3)
        # DEC-r2's D12: a citation landing on a heading rather than the prose
        # it meant to anchor.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-007.md"),
                "`_working-memory/conventions.md:65`",
                f"`_working-memory/conventions.md:{prose_heading_line}`",
                "M2",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M2 citation lands on a heading: exit 1", rc == 1, f"rc={rc} err={err}")
                check("M2: R3 named", rule_hit(err, "R3"), f"err={err!r}")
                check("M2: no traceback", "Traceback" not in err, f"err={err!r}")

        # --------------------------------------------------------- M3 (R10)
        # W3, by class rather than by instance: this fixture is invented,
        # but it exercises the same defect shape W3 was—a count word
        # disagreeing with what follows it. W3 itself (C-9 naming a file by
        # role rather than by path) isn't something R10 can parse directly;
        # the template's "list what you name" note is the other half of
        # that fix.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-006.md"),
                "record three findings",
                "record four findings",
                "M3",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M3 count disagrees with its list: exit 1", rc == 1, f"rc={rc} err={err}")
                check("M3: R10 named", rule_hit(err, "R10"), f"err={err!r}")
                check("M3: no traceback", "Traceback" not in err, f"err={err!r}")

        # ---------------------------------------------------------- M4 (R9)
        # DEC-r3's D13: T-007's check_method restoring the pass-and-report
        # instruction is the actual defect this job exists to fix. This is
        # the pair test for R9's veto set—the unmutated corpus already
        # proved the four load-bearing sentences don't fire (see baseline
        # above); this proves the real defect still does.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-007.md"),
                "On C-6 or C-9, an absent fact is a FAIL, never a pass carrying a finding. For C-9",
                "On C-6 or C-9, an absent fact is the upstream task's defect: pass this task on "
                "that clause and file the gap as a major finding. For C-9",
                "M4",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M4 pass-while-major instruction: exit 1", rc == 1, f"rc={rc} err={err}")
                check("M4: R9 named", rule_hit(err, "R9"), f"err={err!r}")
                check("M4: no traceback", "Traceback" not in err, f"err={err!r}")

        # ---------------------------------------------------------- M5 (R8)
        # DEC-r0's D1: a terminal task that isn't actually terminal. Drops
        # T-007, not T-005—T-005 stays in T-003's transitive closure via
        # T-007, so dropping it wouldn't fire this rule at all.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-003.md"),
                "deps: [T-001, T-002, T-004, T-005, T-006, T-007]",
                "deps: [T-001, T-002, T-004, T-005, T-006]",
                "M5",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M5 terminal task not terminal: exit 1", rc == 1, f"rc={rc} err={err}")
                check("M5: R8 named", rule_hit(err, "R8"), f"err={err!r}")
                check("M5: no traceback", "Traceback" not in err, f"err={err!r}")

        # -------------------------------------------------------- M6 (R12')
        # DEC-r1's D9: the "eleven" that survived the sweep—a count that
        # disagrees with the same fact stated in a different task's prose.
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state")
            copy_corpus_state(state)
            ok = mutate(
                os.path.join(state, "tasks", "T-004.md"),
                "Ten rows record",
                "Eleven rows record",
                "M6",
            )
            if ok:
                rc, out, err = run_linter(state, "--repo-root", fixture_root, "--audit-id", "DEC-audit")
                check("M6 count disagrees across artifacts: exit 1", rc == 1, f"rc={rc} err={err}")
                check("M6: R12 named", rule_hit(err, "R12"), f"err={err!r}")
                check("M6: no traceback", "Traceback" not in err, f"err={err!r}")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
