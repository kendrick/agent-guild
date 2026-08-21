---
source: github-issue
ref: kendrick/agent-guild#183
issue: 183
title: fix(install): a project's payload is pinned to whatever version last ran init, and re-running it aborts instead of upgrading
fetched_at: 2026-08-20T22:37:54Z
---

# fix(install): a project's payload is pinned to whatever version last ran init, and re-running it aborts instead of upgrading

## Problem

The plugin auto-updates at the host level. `.agent-guild/` does not. It is a per-project payload that `/agent-guild:init` copies in once, and nothing re-syncs it afterward, so every plugin bump leaves each initialized repo pinned to whatever version last ran init there. Nothing records which version that was, and nothing notices the gap.

That much is a missing feature. The part that is a defect: re-running init does not close the gap, and its failure blames the user.

`_preflight_payload` (`scripts/plugin-src/install-project.py:195`, called at `:452`) compares every existing payload file against the *current* source and aborts the whole install if any of them differ. A project pinned to an older version differs by definition. So the one action the docs recommend is the one that cannot work, and the diagnostic it prints reads as an accusation of local editing:

> local Agent Guild payload differs; preserved without writes: .agent-guild/CLAUDE.md

The installer has no way to tell "you edited this" from "the guild moved," because it has no record of what it shipped. Both states look identical to a byte comparison against today's source.

The abort also lands before any copying, so `_copy_missing` (`:212`, called at `:484`) never runs. Files the newer version adds do not land either. `ready-set.py` is the live instance: `kendrick/dotfiles` and `kendrick/skills` both hold pre-wave kits that predate it, and re-running init there will not deliver it while any older payload file remains.

And `_copy_missing` is additive by design, adding absent files and never touching existing ones. So even with the preflight satisfied there is no code path that updates a payload file in place. `_copy_owned` (`:226`) does overwrite, but it is wired only to agents, skills, and Codex hooks.

## Steps to Reproduce

Verified on `be2c862` (v0.6.0).

```sh
# 1. a clean project, freshly initialized
mkdir /tmp/drift-repro && cd /tmp/drift-repro && git init -q .
echo "# demo" > README.md && git add -A && git commit -qm init
python3 <agent-guild>/plugin/project-template/install.py claude /tmp/drift-repro
# OK: ... payload=36 updated/0 unchanged ...

# 2. re-running it unchanged is genuinely idempotent
python3 <agent-guild>/plugin/project-template/install.py claude /tmp/drift-repro
# OK: ... payload=0 updated/36 unchanged ...

# 3. now make two payload files differ, standing in for an older release's bytes
echo "# older release shipped different bytes" >> .agent-guild/scripts/ready-set.py
echo "# older contract text" >> .agent-guild/CLAUDE.md
python3 <agent-guild>/plugin/project-template/install.py claude /tmp/drift-repro
# install.py: local Agent Guild payload differs; preserved without writes: .agent-guild/CLAUDE.md, .agent-guild/scripts/ready-set.py
# exit 1

# 4. and the abort blocks net-new files too
rm .agent-guild/scripts/ready-set.py   # stands in for a file the older kit never had
python3 <agent-guild>/plugin/project-template/install.py claude /tmp/drift-repro
# install.py: local Agent Guild payload differs; preserved without writes: .agent-guild/CLAUDE.md
test -f .agent-guild/scripts/ready-set.py; echo "landed? $?"   # 1, it did not
```

Step 3 is what a version bump produces. Step 4 is what makes it bite: one stale file anywhere in the payload withholds every new file the release ships.

## Observed vs. Expected

**Observed:** a project silently runs an old kit forever. Re-running init exits 1 without writing anything, naming files the user never touched. Nothing at any point compares the project's version against the plugin's, because the project has no version to compare.

**Expected:** the payload records the version that installed it. A session in a project stamped older than the running plugin says so, once, with both numbers. Re-running init upgrades the guild-owned payload to the current release, and still refuses, file by file, when a file differs from **what was shipped at install time** rather than from whatever source happens to be current.

That distinction is what the fix turns on, and it needs provenance the installer does not keep today: a version stamp plus per-file hashes of what was written, so a later run can separate the two states the current preflight collapses into one.

## Error Output

```
install.py: local Agent Guild payload differs; preserved without writes: .agent-guild/CLAUDE.md, .agent-guild/scripts/ready-set.py
```

Exit 1. The message is accurate about what it did and wrong about why.

## Acceptance Criteria

- [ ] Install writes a provenance record under `.agent-guild/` naming the plugin version and a hash per payload file as shipped.
- [ ] Re-running init on a project whose payload matches its recorded hashes but trails the current version upgrades those files and reports how many it moved.
- [ ] Re-running init still refuses a file whose bytes differ from its recorded hash, since that is a real local edit, and the diagnostic names only those files.
- [ ] A locally edited file no longer withholds the rest of the release. Files that are clean against their recorded hashes upgrade, and net-new files land, in the same run that refuses the edited one.
- [ ] A project with no provenance record (every kit installed before this ships) is handled explicitly rather than crashing, and the chosen behavior is stated in `docs/installing.md`.
- [ ] A session in a project stamped older than the running plugin surfaces it once, naming both versions and the command that fixes it. `session-nudge.py` already owns this shape of warning for double registration.
- [ ] The provenance record is gitignored or tracked deliberately, not left to land untracked in `git status`. `#98` is the precedent for caring.
- [ ] `python3 .agent-guild/hooks/test_hooks.py`, `python3 scripts/test_build_plugin.py`, and `python3 scripts/build-plugin.py --check` all pass, with coverage for the upgrade path, the refusal path, and a mixed run where both fire.

## Open questions for whoever picks this up

- **Where does the stamp live?** A file under `.agent-guild/` is the obvious answer and it is also payload, so it has to be excluded from its own comparison.
- **Does the nudge prompt or just report?** `/agent-guild:init` is already the fix, so the warning could name it and stop. Auto-running it would write to a project on session start, which is the pattern `#98` is arguing against.
- **What happens to a pre-provenance kit?** Trusting it wholesale overwrites real local edits. Refusing it wholesale leaves every currently installed project stuck exactly where it is now. A one-time "adopt at current version" step is a third option.

## Non-goals

Version-pinning a project to an older guild on purpose, or supporting more than one payload version per repo. The payload tracks the plugin; this issue is about noticing when it has stopped and being able to catch it up.

