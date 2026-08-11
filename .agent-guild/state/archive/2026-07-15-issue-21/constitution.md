# Constitution: Commit The Plugin Tree (Issue #21)

<!-- Spec: .agent-guild/state/spec.md (intake of kendrick/agent-guild#21).
Fully-collapsed interview: the issue settles content (guild-only, init + job
included, nudge + four gates, author-as-object, version 0.2.0) and the
retirement of dist/. Orchestrator-settled details: "retire dist/" means delete
the local staging tree AND drop its .gitignore entry (dead weight once plugin/
is the committed artifact); the version bump edits scripts/plugin-src/
plugin.json (the issue supersedes #20's leave-at-0.1.0, which had deferred the
bump to publish time); the git commit itself is the orchestrator's post-verdict
act, so the clauses verify a commit-READY tree, not a commit. Every clause is
deterministic — this is mechanical work, so it routes to worker-bulk (haiku)
with checker-deterministic, the first job to exercise that lane. -->

## Clauses

### C-1: the committed-location tree is exactly a fresh build
- **text**: `python3 scripts/build-plugin.py --check` exits 0 against the `plugin/` tree: a fresh rebuild matches it file for file, and `claude plugin validate --strict` passes on the build. This is the standing drift gate — from this job on, any hand edit to `plugin/` or unrebuilt source change fails it.
- **check**: .agent-guild/scripts/check-build.sh 'python3 scripts/build-plugin.py --check'
- **severity**: blocker
- **failing example**: someone hand-tweaks `plugin/README.md` wording without touching the sources, and the derived tree silently stops being derived.

### C-2: nothing ignores the plugin tree (it can actually be committed)
- **text**: No ignore source — the repo's `.gitignore`, `.git/info/exclude`, or a machine-local global excludes file — matches anything under `plugin/`. Without this, `git add` silently skips files and the "committed" plugin serves an incomplete tree; the first dogfood's C-9 lesson (a machine-local global can mask the real state) applies verbatim.
- **check**: .agent-guild/scripts/check-build.sh '! git check-ignore -q plugin/.claude-plugin/plugin.json && ! git check-ignore -q plugin/hooks/hooks.json && ! git check-ignore -q plugin/skills/job/SKILL.md'
- **severity**: blocker
- **failing example**: a leftover `plugin/` line in someone's `~/.config/git/ignore` hides the whole tree from `git status`, and the push publishes a marketplace pointing at an empty directory.

### C-3: the tree carries exactly the guild-only component set, versioned for release
- **text**: `plugin/.claude-plugin/plugin.json` parses with `version` exactly `0.2.0`, `author` an object with a name, and `hooks` declaring `./hooks/hooks.json`; the generated `hooks.json` includes a `SessionStart` entry; `plugin/skills/` is exactly the six guild skills (audition, constitution, decompose, init, job, retrospective); no working-memory content anywhere (`hydrate-*`, `update-working-memory`, `hydrator`, `working-memory-synchronizer`); `plugin/hooks/session-nudge.py` ships.
- **check**: .agent-guild/scripts/check-build.sh 'python3 -c "
import json
m = json.load(open(\"plugin/.claude-plugin/plugin.json\"))
assert m[\"version\"] == \"0.2.0\", \"version is \" + repr(m[\"version\"])
assert isinstance(m[\"author\"], dict) and m[\"author\"].get(\"name\"), \"author must be an object with a name\"
assert m[\"hooks\"] == \"./hooks/hooks.json\", \"hooks not declared\"
h = json.load(open(\"plugin/hooks/hooks.json\"))
assert \"SessionStart\" in h[\"hooks\"], \"no SessionStart registration\"
print(\"manifest ok\")
" && test "$(ls plugin/skills | sort | tr "\n" " ")" = "audition constitution decompose init job retrospective " && ! ls plugin/skills plugin/agents | grep -qE "hydrate|update-working-memory|hydrator|working-memory" && test -f plugin/hooks/session-nudge.py'
- **severity**: blocker
- **failing example**: `scripts/plugin-src/plugin.json` still says `0.1.0`, so installed copies never see the update that carries init and the nudge.

### C-4: dist/ is retired
- **text**: The `dist/` staging tree no longer exists on disk, and the repo's `.gitignore` no longer carries its entry (or the accompanying staging-area comment). The committed `plugin/` is the one packaging artifact.
- **check**: .agent-guild/scripts/check-build.sh 'test ! -e dist && ! grep -qiE "(^|/)dist" .gitignore && ! grep -qiF "Build artifacts" .gitignore'
- **severity**: major
- **failing example**: `dist/plugin/` lingers with the stale pre-#20 package, and the next person to debug an install reads the wrong tree.

### C-5: the footprint is the plugin tree, the version bump, and the gitignore line
- **text**: The job's entire working-tree footprint is: the new `plugin/` directory, the modified `scripts/plugin-src/plugin.json` (version bump), and the modified `.gitignore` (dist entry removed) — nothing else modified, deleted, or added anywhere, repo-wide (porcelain with three excludes, house pattern).
- **check**: .agent-guild/scripts/check-build.sh 'test -d plugin && test -z "$(git status --porcelain -- . ":(exclude)plugin" ":(exclude)scripts/plugin-src" ":(exclude).gitignore")"'
- **severity**: blocker
- **failing example**: the worker "fixes" a stray typo in `docs/plugin-publish-plan.md` on the way past, changing a shipped doc under a job that never cited it.

## Protected content

- none.

## Non-goals

- The git commit itself — the orchestrator commits after the PASS verdict, per the established lifecycle.
- The marketplace file (#24), docs/README/SMOKE (#25), the `/job` flow-through fix (#26).
- Any hand edit inside `plugin/` — the tree is derived; C-1 exists to keep it that way.
