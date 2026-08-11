---
task: CON-audit
tier: orchestrator
retry: 1
checker: auditor
verdict: PASS
checked_at: 2026-07-14T00:00:00Z
---

<!-- CON-audit round 1 for constitution.md (Commit The Plugin Tree, issue #21).
r0 FAILed C-4 alone: the check asserted the dist/ entry gone but could not see
the orphaned `# Build artifacts` comment the clause text also requires removed.
The clause text is unchanged; the check now appends `&& ! grep -qiF "Build
artifacts" .gitignore`. This round re-verifies C-4 empirically against three
scratch .gitignore variants and confirms the other four clauses are unchanged
from what r0 reviewed (checks quoted verbatim in r0's method column match the
current file line-for-line: C-1 @19, C-2 @25, C-3 @31-40, C-5 @52). -->

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | `check-build.sh 'python3 scripts/build-plugin.py --check'` | Unchanged from r0 (byte-identical check + text). Concrete, falsifiable (hand-edit `plugin/README.md` without rebuild → drift fail), deterministic (exit code only). | drift gate, unchanged | unchanged | PASS |
| C-2 | `check-build.sh '! git check-ignore -q ...'` (3 plugin/ paths) | Unchanged from r0. Falsifiable (a `plugin/` line in `~/.config/git/ignore` flips it), spans all three ignore sources, sane on nonexistent paths. | ignore-source gate, unchanged | unchanged | PASS |
| C-3 | `check-build.sh '<python asserts> && ls-compare && grep && test -f'` | Unchanged from r0. Version assert discriminates the 0.2.0 bump, author-object, `hooks` decl, `SessionStart`, exact six-skill set (incl. trailing space), working-memory grep clean, `session-nudge.py`. | manifest+component gate, unchanged | unchanged | PASS |
| C-4 | `check-build.sh 'test ! -e dist && ! grep -qiE "(^\|/)dist" .gitignore && ! grep -qiF "Build artifacts" .gitignore'` | Amended check simulated against three scratch copies (real `.gitignore` untouched): **A/today** (comment @24 + `dist/` @25 both present) → grep-half FAIL; **B/orphan** (`dist/` removed, `# Build artifacts` left — the exact artifact r0 caught) → grep-half **FAIL** (now caught); **C/both removed** → grep-half **PASS**. Full check via the real script on today's repo → exit **1** (correct FAIL; `dist/` exists on disk), no crash, not exit 3. Only the two intended lines match; regex `(^\|/)dist` and fixed string `Build artifacts` produce no false positives elsewhere in the file. | check verifies the full stated end-state (dist/ gone from disk, entry gone, AND accompanying comment gone) | check now asserts all three; text and check agree; orphan-comment artifact is falsifiable and rejected | PASS |
| C-5 | `check-build.sh 'test -d plugin && test -z "$(git status --porcelain -- . :(exclude)... )"'` | Unchanged from r0. Three-exclude porcelain caught a scratch `docs/` file, ignored a scratch `scripts/plugin-src/` file; falsifiable via a stray edit to a shipped doc. | footprint gate, unchanged | unchanged | PASS |

## C-4 re-verification detail

The clause text ("the repo's `.gitignore` no longer carries its entry (or the
accompanying staging-area comment)") requires both the `dist/` entry and the
`# Build artifacts` comment gone. The r0 check asserted only the entry, so a
`.gitignore` with the orphaned comment retained passed while violating the text
— a green check on a clause-violating artifact. The appended `&& ! grep -qiF
"Build artifacts" .gitignore` closes that gap: scenario B (entry removed, comment
left) now fails, and only the fully-retired state (scenario C) passes. Text and
check are in agreement, and the failing example is concrete and reproducible.

## Routing / coverage / contradictions

Unchanged from r0 and re-confirmed: all five checks are exit-code / string-equality
expressions with no rubric — genuinely deterministic, correctly routed to
checker-deterministic (haiku). Coverage complete — every requirement the issue
settles maps to a clause (guild-only six-skill set + agents + gates via C-1/C-3,
init + job + nudge via C-3, author-object + version 0.2.0 via C-3, dist/ retirement
via C-4, footprint pin via C-5). No clause contradicts another. Protected content
declares "none" — nothing to parse.

## Diagnosis

<!-- No FAIL this round. -->
