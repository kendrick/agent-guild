# Constitution: SessionStart Nudge (Issue #23)

<!-- Spec: .agent-guild/state/spec.md (intake of kendrick/agent-guild#23).
Fully-collapsed interview — the issue plus docs/plugin-publish-plan.md
("Nudge") settle the design: session-nudge.py, SessionStart event, startup
matcher, one stdout line, exit 0, speaks only on partial init, silent on
zero-evidence projects. Orchestrator-settled details: the file lives at
.agent-guild/hooks/session-nudge.py (the build copies hooks/*.py and its
hooks.json generation appends the SessionStart registration when the file
exists — include-when-present from #20, so landing the source flips the
packaged registration on with zero build changes); the repo's own
.claude/settings.json does NOT register it (this repo is fully initialized, so
it would only ever be silent noise — the plugin's hooks.json is the delivery);
the message hardcodes /agent-guild:init since hooks ship byte-identical (no
prose transform) and the nudge only ever fires in plugin contexts. -->

## Clauses

### C-1: the predicate speaks only on partial init
- **text**: `session-nudge.py` nudges exactly when `.agent-guild/` exists in the project AND the setup is incomplete — any of the five state subdirs (`tasks`, `verdicts`, `disputes`, `notes`, `log`) missing, or the root `CLAUDE.md` missing/lacking an `@.agent-guild/CLAUDE.md` import line. It stays silent (empty stdout, exit 0) when the project has no `.agent-guild/` at all — a user-scope install must never nag unrelated repos — and when the project is fully initialized. It honors the PAUSED escape hatch and the module's fail-loud contract by running through `_lib.run()`. The nudge itself is ONE line of stdout naming what's missing and pointing at `/agent-guild:init`, exit 0.
- **check**: checker-judgment: read the script; confirm the predicate matches this clause exactly (both partial-init triggers, both silence conditions), one-line output, `/agent-guild:init` named, `_lib.run()` wrapping, and exit 0 on every non-crash path.
- **severity**: blocker
- **failing example**: the predicate nudges whenever the state dirs are missing without first requiring `.agent-guild/` to exist, so every unrelated repo with the plugin enabled gets nagged on session start.

### C-2: the silence and the nudge, proven behaviorally
- **text**: Run as a real hook process against scratch project trees: a zero-evidence tree stays silent; a tree with `.agent-guild/` but no state dirs nudges (one line, mentions init); a tree with complete state dirs but no import line nudges; a fully-initialized tree stays silent. All four exit 0.
- **check**: .agent-guild/scripts/check-build.sh 'h=.agent-guild/hooks/session-nudge.py; z=$(mktemp -d) && out=$(CLAUDE_PROJECT_DIR="$z" python3 "$h" </dev/null) && test -z "$out" && p=$(mktemp -d) && mkdir -p "$p/.agent-guild" && out=$(CLAUDE_PROJECT_DIR="$p" python3 "$h" </dev/null) && printf "%s" "$out" | grep -q "init" && test "$(printf "%s\n" "$out" | wc -l | tr -d " ")" -eq 1 && m=$(mktemp -d) && mkdir -p "$m/.agent-guild/state/tasks" "$m/.agent-guild/state/verdicts" "$m/.agent-guild/state/disputes" "$m/.agent-guild/state/notes" "$m/.agent-guild/state/log" && out=$(CLAUDE_PROJECT_DIR="$m" python3 "$h" </dev/null) && printf "%s" "$out" | grep -q "init" && printf "@.agent-guild/CLAUDE.md\n" > "$m/CLAUDE.md" && out=$(CLAUDE_PROJECT_DIR="$m" python3 "$h" </dev/null) && test -z "$out"'
- **severity**: blocker
- **failing example**: the fully-initialized tree still nudges because the import-line test greps for the literal with a leading `./` the real line doesn't carry, so every healthy project nags forever.

### C-3: fixture coverage, suite green
- **text**: `test_hooks.py` gains fixtures for the nudge in the existing style (subprocess against scratch `CLAUDE_PROJECT_DIR` trees): zero-evidence silent, partial-init (missing state dirs) nudges, partial-init (missing import line) nudges, fully-initialized silent. The full suite reports at least 58 passed, 0 failed (55 today plus at least three new).
- **check**: .agent-guild/scripts/check-build.sh 'python3 .agent-guild/hooks/test_hooks.py 2>&1 | grep -qE "(5[8-9]|[6-9][0-9]|[1-9][0-9]{2,}) passed, 0 failed"'
- **severity**: blocker
- **failing example**: only the nudging cases get fixtures, so a regression that makes the hook nag healthy projects ships green.

### C-4: the build packages and registers it, unmodified
- **text**: With `session-nudge.py` present in `.agent-guild/hooks/`, an UNMODIFIED `scripts/build-plugin.py` ships it (`hooks/session-nudge.py` in the output) and its generated `hooks.json` gains a `SessionStart` entry with matcher `startup` whose command runs the packaged script via `${CLAUDE_PLUGIN_ROOT}` — the include-when-present registration from #20 flipping on exactly as designed, with zero build-script changes in this job.
- **check**: .agent-guild/scripts/check-build.sh 'out=$(mktemp -d)/p && python3 scripts/build-plugin.py --out "$out" && test -f "$out/hooks/session-nudge.py" && OUT="$out" python3 -c "
import json, os
h = json.load(open(os.environ[\"OUT\"] + \"/hooks/hooks.json\"))
ss = h[\"hooks\"].get(\"SessionStart\")
assert ss, \"no SessionStart entry\"
e = ss[0]
assert e.get(\"matcher\") == \"startup\", \"matcher is not startup: \" + repr(e.get(\"matcher\"))
cmd = e[\"hooks\"][0][\"command\"]
assert \"CLAUDE_PLUGIN_ROOT\" in cmd and \"session-nudge.py\" in cmd, \"bad command: \" + cmd
print(\"nudge registration ok\")
" && git diff --quiet HEAD -- scripts/build-plugin.py scripts/plugin-src'
- **severity**: blocker
- **failing example**: the build ships the script but its hooks.json generator only appends the entry when a hand-maintained allowlist names the file, the allowlist wasn't updated, and the packaged plugin carries a nudge that never fires.

### C-5: the footprint is the nudge and its tests
- **text**: The job's entire working-tree footprint is the new `.agent-guild/hooks/session-nudge.py` and modifications to `.agent-guild/hooks/test_hooks.py` — nothing else modified, deleted, or added anywhere, repo-wide (porcelain with two excludes, house pattern). In particular `.claude/settings.json` gains no registration: this repo is fully initialized, so an in-repo nudge registration would be permanent silent overhead with no observable behavior.
- **check**: .agent-guild/scripts/check-build.sh 'test -f .agent-guild/hooks/session-nudge.py && test -z "$(git status --porcelain -- . ":(exclude).agent-guild/hooks/session-nudge.py" ":(exclude).agent-guild/hooks/test_hooks.py")"'
- **severity**: blocker
- **failing example**: the worker registers the nudge in `.claude/settings.json` "for completeness," and every dev session in this repo runs an extra hook that can never speak.

### C-6: reads like the house's hooks
- **text**: The script matches the hook module style: a docstring saying what and why, a why-comment on the predicate's asymmetry (why zero-evidence silence outranks discoverability — user-scope installs), `_lib` helpers reused rather than reimplemented (`project_dir()`, `state_path()`), stdlib only. Fixture labels state the behavior under test.
- **check**: checker-judgment: read next to `stop-gate.py` and `subagent-return.py`; fail on a reimplemented project-dir resolution, a missing asymmetry comment, or opaque fixture labels.
- **severity**: major
- **failing example**: the script computes the project root with its own `os.getcwd()` logic, resolving to the wrong tree the first time a session starts outside the repo root.

## Protected content

- none.

## Non-goals

- Committing the plugin tree (#21 — this was its last blocker), marketplace (#24), docs (#25), the `/job` flow-through fix (#26).
- Registering the nudge in this repo's `.claude/settings.json` (see C-5).
- Any SessionStart context injection (`additionalContext`) — persistence is undocumented; the nudge is a message, not a contract-delivery mechanism.
