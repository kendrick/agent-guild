---
audit: CON-audit
round: 9
auditor: auditor
vendor: anthropic
model: claude-opus-5
artifact: .agent-guild/state/constitution.md
verdict: PASS
checked_at: 2026-08-20T23:59:00Z
---

## Scope and method

`constitution.md` at `229ac266…`, which is the digest
`CON-audit-r9.md.sha256` binds, so this verdict covers the text the gate
commissioned. `check-job-spec.py --audit-id CON-audit` exits 0, so R1–R22 —
including R17/R18 on the weight line and R20 on lint exceptions — are already
proven and are not re-litigated here.

All nine clauses were read this round. Two carry `checker-judgment:` rubrics
(C-7, C-9) and have nothing to execute. Of the seven with runnable checks, C-8
was executed in all three directions this round; C-1 through C-6 were executed
against the tree as found only. **This round was scoped**, deliberately and on
instruction, and the scope is stated rather than papered over — see "What this
round did not run."

**Which tree.** No worker has built: `dispatch-guard` holds every one behind
this verdict, and `git status --porcelain` was empty at the start and is empty
now. The baseline sweep's report is read straight, not as a post-Phase-2 scope
note.

```
python3 .agent-guild/scripts/check-baselines.py .agent-guild/state --repo-root .
check-baselines: ran 7 (6 red, 1 green), skipped 2 (2 judgment, 0 no-baseline)
exit 0
```

Every declared baseline held. Scope note on coverage: the sweep reached 7 of 9
clauses; the 2 it skipped (C-7, C-9) are the two with nothing to run, 0 were
skipped for having no baseline, and 0 were unclassifiable.

**The venue.** One whole-tree copy at `/tmp/con9-qVrgZj`, made with
`git archive HEAD | tar -x` and `git init`-ed there and nowhere else. It was
patched in place with `git show HEAD:<path>` between variants rather than
re-cloned, and removed by that exact printed path before filing. The 54
`probe183-*` directories the baseline sweep left under
`/var/folders/zz/…/T/` were removed by the same rule. `PYTHONDONTWRITEBYTECODE`
was set on every run; C-8's check clears the three `__pycache__` paths itself
and I read that `rm -rf` before running it — all three targets are untracked
build byproducts, and the tree was verified clean after.

**Apparatus.** `.agent-guild/state/apparatus/CON-audit-r9/`, carrying
`SOURCE.sha256` over `constitution.md`, `spec.md`, `probe-183.py`,
`docs/installing.md`, and all four task files, plus the two run logs this
round produced (`c8-variant-red.log`, `c8-docs-mutation-green.log`). That
directory also holds a partial reference implementation left by the dispatch
of this same round that died on machine headroom. I did not read any of it.
The one file I opened there before building was its `SOURCE.sha256`, a digest
manifest that carries no reading of any clause, and I opened it to confirm the
stalled dispatch had been commissioned against the same bytes.

**Comparand: none, and the diff step is a no-op.** `CON-audit-r8`'s
`SOURCE.sha256` records `ba971fec…` for the constitution and `DEC-audit-r0`'s
records the same. Mine reads `229ac266…`. No earlier round's recorded source
matches this document, so nothing here is a legitimate comparand and no
divergence is filed. My own work on C-8 was whole — the venue built, the
faithful run green, both variants run — before I listed any predecessor
directory's contents, and I never opened a predecessor's implementation at
all.

## Per-clause results

Each cell records what ran and the assertion that decided it.

| clause | severity | tree as found (baseline) | conforming side | variant built to violate it | finding |
| ------ | -------- | ------------------------ | --------------- | --------------------------- | ------- |
| C-1 | blocker | **ran this round**: red as declared (`provenance record missing`) | not re-run this round — see scope | not re-run this round — see scope | none |
| C-2 | blocker | **ran this round**: red as declared | not re-run this round | not re-run this round | none |
| C-3 | blocker | **ran this round**: red as declared | not re-run this round | not re-run this round | none |
| C-4 | blocker | **ran this round**: red as declared | not re-run this round | not re-run this round | none |
| C-5 | major | **ran this round**: red as declared | not re-run this round | not re-run this round | none |
| C-6 | major | **ran this round**: red as declared | not re-run this round | not re-run this round | none |
| C-7 | major | judgment rubric, nothing to execute; judged by reading | — | — | **F1** (minor) |
| C-8 | blocker | **green as declared**: `371 passed, 0 failed`; `50 passed, 0 failed`; `--check` OK, rc=0 | **green** — the tree as found *is* a faithful implementation of C-8's own contract, and the same command run in the isolated venue returns rc=0 | **red**, rc=1: a T-002-shaped case appended to `scripts/test_build_plugin.py` → `FAIL install writes a provenance record covering the payload  no provenance record at .agent-guild/provenance.json`, `50 passed, 1 failed`. It reached C-8's own logic: `test_hooks.py` had already returned `371 passed, 0 failed` | none |
| C-9 | major | judgment rubric, nothing to execute; judged by reading | — | — | none |

Nothing is `blocked`. No check was stopped by its environment; what did not run
was not run on instruction, which is a scope limit rather than a blocked
clause.

### C-8, the revision that this round exists to test

**The clause discriminates, and the new sentence closes DEC-r0's F1.**

C-8 now carries two halves. The first — the three commands pass — is what the
`check:` command verifies, and it verifies it in both directions: green on the
faithful tree, red on the variant, with the failing assertion named rather than
the exit code alone. The variant I built is precisely the artifact F1 measured:
an otherwise finished tree carrying a red `scripts/test_build_plugin.py`.

The second half — "Every task that writes an input to any of those three
commands cites this clause" — is a constraint on the decomposition rather than
on the tree, and the DEC-audit is its reader. It is falsifiable: a
decomposition where the owner of `scripts/test_build_plugin.py` omits C-8
violates it on inspection. I confirmed it is also **satisfiable and satisfied**
against the schedule as cut. T-001, T-004 and T-002 each cite C-8 and each
carries the full invocation in its `check_method`; T-002 is last and owns
`scripts/test_build_plugin.py`.

The one task that does not cite C-8 is T-003, which owns `docs/installing.md`,
so I measured rather than assumed that the omission is correct. In the venue I
deleted the split sentence from `docs/installing.md` outright and re-ran C-8's
command: **rc=0, `371 passed, 0 failed`, `50 passed, 0 failed`, `--check` OK**.
`docs/installing.md` is an input to none of C-8's three commands, so T-003
cannot break C-8 and correctly does not cite it. Half (b) and the schedule
agree.

The clause is determinate enough to schedule against. "An input to any of those
three commands" is an enumerable set a decomposer can read off
`build-plugin.py` (`guild-core/`, `.agent-guild/`, `scripts/plugin-src/`,
`docs/plugin-readme.md`, `CHANGELOG.md`, both marketplaces, `plugin/`,
`plugins/`) and settle empirically the way I just did. That is strictly more
determinate than "the finished tree," which is the wording it replaced.

It also survives the schedule's harder shapes. Two C-8-citing tasks in one wave
would not create a hole, because each one's check runs after both workers have
written; and a rework of T-004 after T-002 has been checked triggers
invalidation, which re-dispatches T-002's checker and therefore C-8 again.

The preamble's delegating note — "a task is not done until the build is
regenerated — C-8's `--check` holds that" — was DEC-r0's F1 in its other form.
It now holds: every build-input writer in the schedule carries C-8.

### C-7, the revision, and what it still leaves open

The added requirement is right and the artifact it names is real:
`docs/installing.md:137` carries the sentence verbatim, and I confirmed why the
requirement is needed rather than decorative — with that sentence deleted, C-8's
three commands stay green and `probe-183.py` still passes, because the probe
cites the sentence only in a docstring. **Nothing mechanical in this job catches
its removal. C-7 is the only thing standing between that sentence and deletion**,
which makes it worth getting exactly right. Two things about it are not yet
exactly right — F1, below.

I also checked the pair the revision creates for a contradiction and did not
find one. C-7 requires the doc to state that clean-against-record files upgrade
(C-2) *and* to keep the Codex-hooks contrast. Both can be true of the same
document, because the contrast is between an unconditional overwrite and a
record-gated one, and because the split sentence and the now-false drift
sentence beside it are separate sentences — a worker can rewrite the second
without touching the first.

### The rest of the document, read this round

**Payload scope, the preamble against C-1 and C-7.** The definition survives
the reading. I checked the fork I expected to find here and it is not one: on
the Claude package `plugin/project-template/.agent-guild/` ships no `hooks/`
directory at all, and the `host == "codex"` split at
`install-project.py:350-360` only fires where one exists. So "the payload set
`install()` computes" and "`.agent-guild/` minus `state/`, minus the record,
minus the Codex repo-local `hooks/`" name the same set on all three install
shapes, and `payload_files()` in `probe-183.py` excluding `hooks/`
unconditionally is exactly right rather than a claude-shape bug. Both manifest
paths C-1 names exist where it says (`plugin/.claude-plugin/plugin.json`,
`plugins/agent-guild/.codex-plugin/plugin.json`).

**Falsifiability sweep.** Every clause carries a failing example I can restate
as a concrete artifact, and none is unfalsifiable.

**Contradiction sweep.** No two clauses contradict. The one pair worth checking
is C-2 against C-7's new contrast, treated above.

**Text-versus-check sweep, by enumeration rather than where the wording caught
my eye.** Eight of nine clauses have a check that names the same artifact their
text does. C-7 is the exception and is F1. C-8's check verifies half of its
text by design, with the other half addressed to the decomposer and read by the
DEC-audit; that is a clause naming two different readers, not a check pointed
at a different artifact, and it is the shape the F1 repair required.

**Weight.** `deep`, corrected by the user on r4. The recorded reason is true as
written: verification did require building an instrument — `probe-183.py` is
840 lines driving three install shapes and four nudge deployments, and it is
not a suite the repo already had. Nine clauses under a ceiling of none, so no
`**Ceiling overrun**:` line is owed, and none is present. No `**Lint
exception**:` line is present, so R20 has nothing to second-guess.

**Protected content.** `manifest: none`, with the reason stated. Nothing to
parse.

**One thing the revisions improved that is worth recording.** DEC-r0 noted that
C-9's rubric asks a checker to reason about whether a case *would fail against
pre-job behavior* and never asks whether it *passes now*. C-8 landing on T-002
closes that: the same dispatch that judges C-9 by reading also runs C-8 against
the suite the worker just wrote.

## What this round did not run

Said plainly, because a verdict silent on its gaps cannot be told from one that
ran everything.

**C-1 through C-6 got one of their three runs this round.** They were executed
against the tree as found, through the baseline sweep, and every declared red
held. They were **not** re-run against a fresh reference implementation and
**not** re-run against clause-violating variants, and no reference
implementation was built this round.

Why: four dispatches on this job have died to machine resource exhaustion,
including one dispatch of this round that died partway through building exactly
that reference implementation. The orchestrator scoped this round to the two
revised clauses on that measured basis, and a filed verdict naming its gaps is
worth more than a fifth dead round.

What stands behind those six clauses instead: their checks are unchanged —
`probe-183.py` hashes `5c65bb9b…`, identical to what `CON-audit-r8` and
`DEC-audit-r0` recorded — and both of those rounds ran all six in all three
directions against that same instrument and found each one discriminating in
both directions. This round re-read all six texts and re-ran their baselines.
What it did not do is re-measure their discrimination.

The honest limit on that inheritance: `.agent-guild/state/` is gitignored and
no archived copy of the r8-era constitution exists, so I could not
cryptographically verify that C-1 through C-6's *bytes* are unchanged. I read
the current text of all six and judge it sound; the inherited evidence covers
their checks' discrimination, and the checks are provably the same bytes.

Two more limits worth stating: I did not re-derive `probe-183.py`'s internals
clause by clause — I confirmed structurally that the pinned-manifest
falsification (`9.9.9`) and the mutation-landed asserts C-1 and C-5 depend on
are present — and, this being a Claude host, no clause went unexecuted for the
Codex lane's reason.

## Why this passes

The two revisions do what they were made to do. C-8's new sentence is
falsifiable, satisfiable, satisfied by the schedule as cut, and its check
discriminates in both directions on runs made this round. C-7's new requirement
names a real and load-bearing sentence, and creates no contradiction with C-2.
The one finding is minor and its practical harm in this job is already zero,
because T-003's `check_method` carries the missing requirement verbatim.

Per the charter, a PASS is not withheld over a minor. F1 should be folded into
the next amendment of C-7 whenever one happens for another reason — it does not
justify a round of its own, since amending the bytes to fix it would re-close
this gate and cost a full round to reopen for a defect nothing in this job can
trip over.

## Findings

- **C-7** (minor, F1): the clause's `check:` is narrower than its text, and the
  gap falls exactly on the requirement this round's revision added.

  The text now names five things `docs/installing.md` must state: the four
  behaviors in its first sentence, plus the payload versus `_copy_owned` split
  line in its second. The check says: "confirm each of **the four behaviors**
  in the clause text is stated accurately against the shipped implementation,
  and that the re-init table from #214 still tells the truth about which files
  upgrade." The count "four" actively excludes the fifth, and the #214 table
  (`docs/installing.md:132-135`) is not the split sentence (`:137`) — they are
  different lines making different claims. So a checker following C-7's own
  check method is never asked about the requirement C-7 was revised to carry.

  This is DEC-r0's F3 moved up one level rather than closed: there, the
  requirement lived in T-003's excerpt but not in what the checker checked
  against; here it lives in C-7's text but not in C-7's check. What makes it
  minor rather than a repeat is that the operative path is already covered —
  T-003's `check_method` carries the requirement verbatim, and a checker is
  dispatched against the task's `check_method`. The cost is borne by the next
  decomposition, which would regenerate `check_method` from a clause whose
  check does not ask.

  I measured the harm the requirement guards against rather than inferring it:
  with the split sentence deleted from `docs/installing.md`, C-8's three
  commands return rc=0 and `probe-183.py` is unaffected, so the preamble's
  payload-scope definition, C-1's own text, and `payload_files()`'s docstring
  would all become dangling references on the shipped tree with nothing to
  catch it.

  **Repair** (one phrase, for whenever C-7 is next amended): change "each of the
  four behaviors in the clause text" to "each behavior the clause text names,"
  and add the split line to the check's own enumeration beside the #214 table.

  **Second, smaller thing in the same clause.** C-7 describes the line it wants
  kept as "they upgrade on every re-init while payload files do not." After C-2
  lands, a payload file clean against its recorded hash *does* upgrade on
  re-init. The sentence survives on a narrow reading — payload files do not
  upgrade *unconditionally* — but the clause is instructing a worker on what a
  document must say, and a worker or checker taking that phrase at face value
  would be steered toward preserving a contrast C-2 has made misleading. Worth
  rewording alongside the repair above, to something like "so they upgrade on
  every re-init, where a payload file's upgrade is gated on its recorded hash."
