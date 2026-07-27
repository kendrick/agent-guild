---
name: init
description: Finishes a guild plugin install inside a project by copying the per-project payload (the orchestrator contract, check-script tooling, and templates) that a plugin can't ship as always-on config. Explicit-only — the model never invokes this on its own; the user runs it by name. Use when the user says "finish the guild install here" or "set up this project for the guild".
disable-model-invocation: false
---

# Finish The Guild Install

Use the host command appended to this skill to run Agent Guild's packaged project installer. The dependency-free installer is the sole implementation for both plugin setup and direct IDE bootstrap; this skill does not reproduce its file-copy logic.

The installer is idempotent and fail-closed:

- Pass the actual project root; never guess a checkout or write into a user/global configuration directory.
- Preserve existing project guidance outside Agent Guild's marked sections.
- Preserve unrelated project agents, skills, and host configuration.
- If the installer reports malformed ownership markers, a redirected path, or a conflict with locally edited payload content, stop and give the user its exact diagnostic.
- Never hand-edit host configuration to imitate a successful install.

After a successful run, tell the user which host entrypoint is now available for `job` intake and which invocation syntax that host uses.


## Codex Plugin Command

Resolve `<skill-directory>` to the directory containing this `SKILL.md`, resolve `<project-root>` to the current repository root, then run the shared installer:

```sh
python3 "<skill-directory>/../../project-template/install.py" codex "<project-root>"
```

Do not add `--project-skills` for plugin setup—the installed plugin already supplies them. Codex does not automatically trust plugin hooks: after the installer succeeds, open `/hooks`, review the exact Agent Guild definitions, and ask the user to trust them explicitly. Never imply that installing or initializing the plugin granted trust. Then start existing work with `$agent-guild:job <issue|file|url>` or author a fresh spec with `$agent-guild:constitution`.
