---
task: CON-audit
tier: orchestrator
retry: 0
checker: auditor
verdict: FAIL
checked_at: 2026-07-14T00:00:00Z
---

<!-- CON-audit round 0 for constitution.md (Commit The Plugin Tree, issue #21).
Every clause read against spec.md; each check run empirically against today's
pre-deliverable state (plugin/ absent, plugin-src still 0.1.0, dist/ present
locally, .gitignore still carries the dist entry). -->

## Per-clause results

| clause | method | evidence (command output / quoted artifact) | expected | actual | result |
| ------ | ------ | ------------------------------------------- | -------- | ------ | ------ |
| C-1 | `check-build.sh 'python3 scripts/build-plugin.py --check'` | ran today: `--check: /Users/.../plugin does not exist -- run a build first`, exit 1 — fails at the plugin/-absent guard, never reaches the `claude` CLI or a bug. Falsifiable (hand-edit `plugin/README.md` without rebuilding → content-drift fail). Deterministic (exit code only). | a concrete, falsifiable, deterministic drift gate | exactly that | PASS |
| C-2 | `check-build.sh '! git check-ignore -q ...'` (3 paths) | `git check-ignore -v` on all three nonexistent `plugin/` paths → exit 1 (not ignored, from patterns); combined expr exit 0. `core.excludesfile` and `.git/info/exclude` carry no `plugin/` today. Sane on nonexistent paths; falsifiable (a `plugin/` line in `~/.config/git/ignore` flips it). | nothing ignores plugin/, checkable across all three ignore sources | exactly that | PASS |
| C-3 | `check-build.sh '<python asserts> && ls-compare && grep && test -f'` | Built a stub via `--out <tmp>`: version assert correctly **fails today** (`version is '0.1.0'`), discriminating the 0.2.0 bump; `author` already `{'name': 'Kendrick Arnett'}` (object w/ name → pass); `hooks == './hooks/hooks.json'`; `SessionStart` present; `ls skills \| sort \| tr` → `audition constitution decompose init job retrospective ` == asserted string **incl. trailing space** (init/job both landed, sort order holds); working-memory grep clean; `session-nudge.py` ships. | manifest+component set, versioned, checkable and version-discriminating | exactly that | PASS |
| C-4 | `check-build.sh 'test ! -e dist && ! grep -qiE "(^\|/)dist" .gitignore'` | grep matches the `dist/` entry (line 25) but **does not match** the accompanying comment `# Build artifacts` (line 24: `printf '# Build artifacts\n' \| grep -iE "(^\|/)dist"` → no match). Clause text requires the comment removed too; the check cannot detect it. | check verifies the full stated end-state (entry AND comment gone) | check verifies only the entry; a `.gitignore` with the orphaned comment retained passes | FAIL |
| C-5 | `check-build.sh 'test -d plugin && test -z "$(git status --porcelain -- . :(exclude)... )"'` | three-exclude porcelain parses (exit 0, empty); a scratch file under `docs/` was CAUGHT; a scratch file under the excluded `scripts/plugin-src/` was correctly IGNORED; tree restored clean. Falsifiable (stray edit to a shipped doc). | footprint pinned to plugin/ + version bump + gitignore line, both directions | exactly that | PASS |

## Routing check

All five checks are exit-code / string-equality expressions with no rubric or
judgment — genuinely deterministic. Routing the build to worker-bulk (haiku)
with checker-deterministic is correct; nothing here needs a judgment checker.

## Coverage check

Every requirement the issue settles maps to a clause: guild-only content and
the six-skill set (C-3, plus C-1's fresh-build match pinning the six agents and
the four gate hooks transitively); init + job included (C-3 exact-string set);
the nudge (C-3 session-nudge.py + SessionStart); author-as-object and version
0.2.0 (C-3); dist/ retirement (C-4). No clause contradicts another. No protected
content declared (manifest lists "none"; nothing to parse). Coverage is complete.

## Diagnosis

- **file**: `.agent-guild/state/constitution.md:44-46` (clause C-4)
  **clause**: C-4—"the repo's `.gitignore` no longer carries its entry (or the accompanying staging-area comment)"
  **expected**: the check verifies the full end-state the clause text asserts — both the `dist/` entry AND its accompanying comment (`# Build artifacts`, `.gitignore:24`) removed.
  **actual**: the check is `! grep -qiE "(^|/)dist" .gitignore`, which matches the `dist/` entry but not the comment `# Build artifacts` (verified: that string contains no "dist"). A `.gitignore` where the worker deletes `dist/` (line 25) but leaves the orphaned `# Build artifacts` (line 24) passes the check while violating the clause text — a green check on a clause-violating artifact, exactly the failure this system exists to prevent. The clause's primary requirements (dist/ gone from disk, entry gone) are correctly and falsifiably checked; only the comment half of the stated requirement is unverified.
  **remedy** (orchestrator's call, either closes it): (a) broaden the check to also assert the comment is gone, e.g. append `&& ! grep -qiF "Build artifacts" .gitignore`; or (b) drop "(or the accompanying staging-area comment)" from the clause text if the comment's removal is not actually required. Then re-submit for CON-audit r1.
