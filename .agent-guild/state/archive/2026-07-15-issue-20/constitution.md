# Constitution: build-plugin.py (Issue #20)

<!-- Spec: .agent-guild/state/spec.md (intake of kendrick/agent-guild#20).
Collapsed interview settled three open calls with the user: components not yet
built (#22 init, #23 nudge) are included-when-present; --check hard-fails when
the claude CLI is missing; the manifest lives in a checked-in scripts/plugin-src/
directory, version untouched until #24 owns the bump. CLI contract for checks:
`build-plugin.py [--out DIR] [--check]` — default output dir is plugin/, --out
redirects for tests, --check rebuilds to temp and compares against plugin/. -->

## Clauses

### C-1: one stdlib script plus a checked-in manifest source
- **text**: The deliverable is `scripts/build-plugin.py` (python3, stdlib imports only, executable, `--help` that documents build/--out/--check) plus `scripts/plugin-src/plugin.json` — the checked-in manifest source the build copies through (kebab-case `name: agent-guild`, `author` as an object, `hooks: ./hooks/hooks.json`, version left at 0.1.0). No other new top-level surface.
- **check**: checker-judgment: read the script's imports (stdlib only), confirm the executable bit and a usable `--help`, and confirm `scripts/plugin-src/plugin.json` carries exactly those manifest properties. Fail on any third-party import or a manifest embedded in the script instead of the source dir.
- **severity**: blocker
- **failing example**: the script imports `yaml` to parse settings, which breaks the repo's dependency-free rule on any machine without PyYAML.

### C-2: the build assembles exactly the guild-only component set
- **text**: A build into a fresh `--out` dir produces: the six guild agents byte-identical to `.claude/agents/` (auditor, checker-deterministic, checker-judgment, worker-bulk, worker-craft, worker-standard); the five guild skills present today (constitution, decompose, retrospective, audition, job) as directories under `skills/`; all six hook files from `.agent-guild/hooks/` byte-identical under `hooks/` plus a generated `hooks/hooks.json`; `project-template/.agent-guild/` holding `CLAUDE.md`, `scripts/`, and `templates/` copies; and `.claude-plugin/plugin.json`. Working-memory content ships nowhere in the output: no `hydrate-*` or `update-working-memory` skills, no `hydrator.md` or `working-memory-synchronizer.md` agents. Init (#22) and the nudge (#23) join automatically when their sources exist — today they don't, so today they're absent.
- **check**: .agent-guild/scripts/check-build.sh 'out=$(mktemp -d)/p && python3 scripts/build-plugin.py --out "$out" && for a in auditor checker-deterministic checker-judgment worker-bulk worker-craft worker-standard; do cmp -s .claude/agents/$a.md "$out/agents/$a.md" || exit 1; done && for s in constitution decompose retrospective audition job; do test -d "$out/skills/$s" || exit 1; done && for h in _lib.py dispatch-guard.py orchestrator-write-guard.py stop-gate.py subagent-return.py test_hooks.py; do cmp -s .agent-guild/hooks/$h "$out/hooks/$h" || exit 1; done && test -f "$out/hooks/hooks.json" && test -f "$out/project-template/.agent-guild/CLAUDE.md" && test -d "$out/project-template/.agent-guild/scripts" && test -d "$out/project-template/.agent-guild/templates" && test -f "$out/.claude-plugin/plugin.json" && ! ls "$out/skills" | grep -qE "hydrate|update-working-memory" && ! ls "$out/agents" | grep -qE "hydrator|working-memory"'
- **severity**: blocker
- **failing example**: the build sweeps all of `.claude/skills/` and ships `hydrate-extract`, repeating the overbundling the first dogfood staged into `dist/`.

### C-3: generated hooks.json is derived, rewired, and dangling-free
- **text**: `hooks/hooks.json` in the build output is generated from `.claude/settings.json` (not hand-copied from the dist-era file): valid JSON registering all four gates on their events (Stop → stop-gate; SubagentStop → subagent-return; PreToolUse → dispatch-guard and orchestrator-write-guard), every command using `"${CLAUDE_PLUGIN_ROOT}"/hooks/`, zero `CLAUDE_PROJECT_DIR` references, and every referenced script file actually present in the built `hooks/` dir (no dangling registration — the include-when-present rule means a nudge entry may only appear once `session-nudge.py` ships).
- **check**: .agent-guild/scripts/check-build.sh 'out=$(mktemp -d)/p && python3 scripts/build-plugin.py --out "$out" && OUT="$out" python3 -c "
import json, os, re
out = os.environ[\"OUT\"]
h = json.load(open(out + \"/hooks/hooks.json\"))
cmds = [x[\"command\"] for ev in h[\"hooks\"].values() for e in ev for x in e[\"hooks\"]]
assert cmds, \"no hook commands\"
assert all(\"CLAUDE_PLUGIN_ROOT\" in c for c in cmds), \"unrewired command\"
assert not any(\"CLAUDE_PROJECT_DIR\" in c for c in cmds), \"project-dir leak\"
for c in cmds:
    m = re.search(r\"hooks/([A-Za-z0-9_.-]+[.]py)\", c)
    assert m, \"unparseable command: \" + c
    assert os.path.exists(out + \"/hooks/\" + m.group(1)), \"dangling: \" + m.group(1)
joined = \" \".join(cmds)
for g in [\"stop-gate.py\", \"subagent-return.py\", \"dispatch-guard.py\", \"orchestrator-write-guard.py\"]:
    assert g in joined, \"missing gate: \" + g
print(\"hooks.json ok\")
"'
- **severity**: blocker
- **failing example**: hooks.json registers `session-nudge.py` before #23 exists, so a plugin install fires a Stop-adjacent hook whose script 404s and every session start errors.

### C-4: namespacing lands on plugin-bound prose only
- **text**: The build rewrites bare guild invocations (`/constitution`, `/decompose`, `/retrospective`, `/audition`, `/job`) to `/agent-guild:<name>` in plugin-bound prose — the `project-template/.agent-guild/CLAUDE.md` contract and the packaged skill bodies — while leaving file paths (e.g. `.claude/skills/constitution/`) untouched and never modifying the in-repo sources. The transform map lives in the script, explicit and greppable.
- **check**: checker-judgment: build to a temp dir; confirm the packaged contract's phase instructions invoke `/agent-guild:constitution`, `/agent-guild:decompose`, `/agent-guild:retrospective` (deterministic spot-check: grep), then read the transformed files for overreach — a path or heading mangled by the rewrite fails; an untransformed invocation in packaged prose fails; any change to the repo-side sources (git status) fails.
- **severity**: blocker
- **failing example**: the rewrite turns the literal path `.agent-guild/state/tasks/` reference "run /decompose to produce task files" into prose that names `/agent-guild:decompose` but also rewrites the neighboring directory path `skills/decompose/` into `skills/agent-guild:decompose/`, breaking the packaged skill's own link.

### C-5: --check catches drift, absence, and a missing CLI
- **text**: `--check` rebuilds into a temp dir and compares against the committed-location `plugin/` tree: exit 0 when they match; nonzero with a naming message when any file differs, when `plugin/` is absent, or when the `claude` CLI is missing from PATH (hard-fail — a skipped validation must never read as green). On match it also runs `claude plugin validate --strict` against the built plugin and propagates a failure.
- **check**: .agent-guild/scripts/check-build.sh 'python3 scripts/build-plugin.py && python3 scripts/build-plugin.py --check && printf x >> plugin/hooks/_lib.py && ! python3 scripts/build-plugin.py --check && rm -rf plugin && ! python3 scripts/build-plugin.py --check && python3 scripts/build-plugin.py && python3 scripts/build-plugin.py --check; rc=$?; rm -rf plugin; exit $rc'
- **severity**: blocker
- **failing example**: with `plugin/` deleted, `--check` treats "nothing to compare" as success and exits 0, so CI stays green while the published tree is gone.

### C-6: the built manifest passes the platform's own validator
- **text**: A fresh build passes `claude plugin validate --strict` (the plugin manifest validates in isolation — the marketplace file lives at the repo root per #24, not inside the plugin, so no manifest shadowing occurs). This uses Anthropic's validator as the standard, not a hand-rolled rubric — the author-string bug shipped precisely because a hand-rolled check validated less than the platform does.
- **check**: .agent-guild/scripts/check-build.sh 'out=$(mktemp -d)/p && python3 scripts/build-plugin.py --out "$out" && claude plugin validate --strict "$out"'
- **severity**: blocker
- **failing example**: `plugin-src/plugin.json` regresses `author` to a plain string; the build copies it through and `--strict` rejects it at install time on a colleague's machine.

### C-7: sources are read-only to the build; the job adds only its declared surface
- **text**: Building never mutates its inputs. After any number of builds, `git diff` is clean across `.claude/settings.json`, `.claude/agents`, `.claude/skills`, `.agent-guild/hooks`, `.agent-guild/scripts`, and `.agent-guild/templates`. The job's tracked additions are exactly `scripts/build-plugin.py` and `scripts/plugin-src/`.
- **check**: .agent-guild/scripts/check-build.sh 'out=$(mktemp -d)/p && python3 scripts/build-plugin.py --out "$out" && git diff --quiet HEAD -- .claude/settings.json .claude/agents .claude/skills .agent-guild/hooks .agent-guild/scripts .agent-guild/templates'
- **severity**: blocker
- **failing example**: the namespacing transform edits `.claude/skills/job/SKILL.md` in place instead of transforming the copy, silently renaming the live repo's invocations.

### C-8: the script reads like this repo's tooling
- **text**: `build-plugin.py` matches the house code style: a module docstring saying what and why, why-comments at the non-obvious spots (the include-when-present rule, the isolation reasoning, the transform map's path-vs-prose distinction), small functions over one long main, and error messages that name the actual problem. Comparable reference: `.agent-guild/scripts/check-provenance.py` and `new-task.py`.
- **check**: checker-judgment: read the script next to `check-provenance.py` and `new-task.py`; fail on an uncommented transform map, a monolithic main, or errors like "check failed" with no subject.
- **severity**: major
- **failing example**: `--check`'s mismatch path prints `sys.exit(1)` after a bare "differs" with no file name, leaving CI logs useless for diagnosing drift.

## Protected content

- none — tooling job, no authored copy to protect.

## Non-goals

- Committing the `plugin/` tree (#21), the init skill (#22), the nudge (#23), the root marketplace file (#24), and all docs/README/SMOKE work (#25).
- Version bump to 0.2.0 — #24's publish flow owns it.
- The `/job` handoff fix (#26).
