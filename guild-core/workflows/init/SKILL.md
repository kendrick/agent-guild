# Finish The Guild Install

Use the host command appended to this skill to run Agent Guild's packaged project installer. The dependency-free installer is the sole implementation for both plugin setup and direct IDE bootstrap; this skill does not reproduce its file-copy logic.

The installer is idempotent and fail-closed:

- Pass the actual project root; never guess a checkout or write into a user/global configuration directory.
- Preserve existing project guidance outside Agent Guild's marked sections.
- Preserve unrelated project agents, skills, and host configuration.
- If the installer reports malformed ownership markers, a redirected path, or a conflict with locally edited payload content, stop and give the user its exact diagnostic.
- Never hand-edit host configuration to imitate a successful install.

After a successful run, tell the user which host entrypoint is now available for `job` intake and which invocation syntax that host uses.
