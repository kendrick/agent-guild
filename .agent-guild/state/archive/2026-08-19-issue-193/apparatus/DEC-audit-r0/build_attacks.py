#!/usr/bin/env python3
"""DEC-audit r0 attack variants. Each one violates ONE clause's own text (or
its own failing example) while leaving the rest of the reference intact, so a
clause that stays green against its variant is a clause verifying nothing.

Usage: build_attacks.py <venue> <ref-tree> <name>
"""
import os
import shutil
import sys

LINTER = ".agent-guild/scripts/check-job-spec.py"
SUITE = ".agent-guild/scripts/test_check_job_spec.py"


def patch(tree, rel, old, new, allow=1):
    p = os.path.join(tree, rel)
    src = open(p, encoding="utf-8").read()
    if src.count(old) != allow:
        raise SystemExit(f"{rel}: anchor occurs {src.count(old)} times, expected {allow}")
    open(p, "w", encoding="utf-8").write(src.replace(old, new, 1))


ATTACKS = {}


def attack(fn):
    ATTACKS[fn.__name__] = fn
    return fn


@attack
def vC1(t):
    """C-1's failing example, modernised: a fixed modifier allowlist. Passes
    the five named adjectives, dies on a run-time nonce."""
    patch(t, LINTER, '''        if m.group(0).endswith("s"):
            return True''', '''        if m.group(0).endswith("s"):
            return True
        if m.group(0).lower() not in {"further", "key", "new", "separate", "brief", "other"}:
            return False''')


@attack
def vC2(t):
    """C-2's failing example verbatim: the relaxation reaches down the whole
    line for any plural it can find, rather than walking bounded modifiers."""
    patch(t, LINTER, """    tail = text[match.end():].lstrip()
    for _ in range(_R10_MODIFIER_LIMIT + 1):""", """    tail = text[match.end():].lstrip()
    if re.search(r"[A-Za-z][A-Za-z-]*s\\b", tail):
        return True
    for _ in range(_R10_MODIFIER_LIMIT + 1):""")


@attack
def vC3a(t):
    """CON-r0's blocker, rebuilt: R21 reads the task's own check_method
    paraphrase instead of the constitution's clause."""
    patch(t, LINTER, """        for cid in task.clauses:
            clause = ctx.clauses.get(cid)
            if clause is None:
                continue
            if clause.check_text.strip().startswith("checker-judgment:"):""",
          """        if "checker-judgment:" not in task.check_method_text:
            continue
        for cid in task.clauses:
            if True:""")


@attack
def vC3b(t):
    """R21 placed among the heuristics instead of ahead of them, so paperwork
    carrying both a routing defect and an inferred one reports the waivable
    guess rather than the unwaivable proof."""
    patch(t, LINTER, """        lambda: rule_R21(ctx, audit_id),
        lambda: rule_R4(ctx, audit_id),""", """        lambda: rule_R4(ctx, audit_id),""")
    patch(t, LINTER, """        lambda: rule_R10(ctx),""", """        lambda: rule_R10(ctx),
        lambda: rule_R21(ctx, audit_id),""")


@attack
def vC4(t):
    """C-4's failing example: R21 compares the two fields for equality rather
    than for the one harmful direction."""
    patch(t, LINTER, """        if (task.checker or "").strip() != "checker-deterministic":
            continue""", """        if (task.checker or "").strip() not in ("checker-deterministic", "checker-judgment"):
            continue""")


@attack
def vC5a(t):
    """C-5's failing example: the message keeps every number it already
    reported and never quotes the anchor. The probe's mechanical half cannot
    see this; only the rubric's reader can."""
    patch(t, LINTER, '''        f"but the quoted code is at {path}:{actual_line}. The anchor this "
        f"citation was checked against is `{anchor}`, {where}"''',
          '''        f"but the quoted code is at {path}:{actual_line} (anchor length "
        f"{len(anchor)}, {where})"''')


@attack
def vC5b(t):
    """R2's silence guard removed: an anchor absent from the WHOLE target file
    is reported as a citation defect rather than treated as evidence the span
    was never that citation's anchor."""
    patch(t, LINTER, """                # real drift case always leaves the quoted code findable
                # somewhere in the file it was quoted from.
                continue""", """                # real drift case always leaves the quoted code findable
                # somewhere in the file it was quoted from.
                return r2_anchor_message(
                    label, src_line, path, lineno, lineno,
                    anchor=anchor, anchor_line=anchor_line,
                )""")


@attack
def vC6(t):
    """C-6's failing example: the linter changes and the builder is never
    re-run, so the published trees no longer match a fresh build."""
    os.system(f"cd {t} && git checkout -- plugin plugins 2>/dev/null")


@attack
def vC7(t):
    """C-7's failing example verbatim: an unrelated edit to a hook rides
    along with the authorized change."""
    with open(os.path.join(t, ".agent-guild/hooks/dispatch-guard.py"), "a") as f:
        f.write("\n# unrelated edit this job never authorized\n")


@attack
def vC8(t):
    """C-8's failing example: the R2 work reaches for `regex` instead of
    `re`, and every guild dispatch in every consuming project fails its
    gate."""
    patch(t, LINTER, "import re\n", "import re\nimport regex\n")


@attack
def vC9_seam(t):
    """The seam exists and behaves correctly, but binds the matched text under
    a different parameter name. C-9 requires `anchor`."""
    patch(t, LINTER, "def r2_anchor_message(label, src_line, path, lineno, actual_line, anchor, anchor_line):",
          "def r2_anchor_message(label, src_line, path, lineno, actual_line, matched, anchor_line):")
    patch(t, LINTER, '''        f"citation was checked against is `{anchor}`, {where}"''',
          '''        f"citation was checked against is `{matched}`, {where}"''')
    patch(t, LINTER, """                        anchor=anchor, anchor_line=anchor_line,""",
          """                        matched=anchor, anchor_line=anchor_line,""")


@attack
def vC9_nocov(t):
    """Correct seam, correct diagnostic, but no case in the suite asserts the
    anchor TEXT is there — only that R2 fired. C-9's coverage half."""
    patch(t, SUITE, '''                check("M9: the diagnostic quotes the anchor it matched",
                      anchor in err, f"err={err!r}")
                check("M9: and says where that anchor sits",
                      "tasks/T-001.md:57" in err or "that same line" in err, f"err={err!r}")''',
          '''                check("M9: R2 still fires", rule_hit(err, "R2"), f"err={err!r}")''')


@attack
def vC9_synth(t):
    """Every case discriminates, but they are built from paperwork invented
    for the occasion rather than drawn from the archive. C-9's second half,
    and only a reader can see it — the probe goes green."""
    patch(t, SUITE, '''                os.path.join(state, "tasks", "T-005.md"),
                "checker: checker-judgment",
                "checker: checker-deterministic",
                "M8",''', '''                os.path.join(state, "tasks", "T-005.md"),
                "checker: checker-judgment",
                "checker: checker-deterministic",
                "M8 (synthetic stand-in)",''')


def main(venue, ref, name):
    dest = os.path.join(venue, name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(ref, dest, symlinks=True)
    ATTACKS[name](dest)
    print(dest)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
