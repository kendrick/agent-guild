# Guild Core

This directory is the only authored home for host-neutral Guild behavior. `roles/` contains the complete nine-agent roster—three worker tiers, deterministic and judgment checkers, the checker courier, auditor, hydrator, and working-memory synchronizer—without Claude frontmatter or Codex TOML. `workflows/` contains skill bodies and their assets without host invocation metadata. Shared payload scripts, schemas, templates, and scenario definitions remain canonical under `.agent-guild/` where the repository dogfoods them.

Host-bound metadata lives under `scripts/plugin-src/adapters/`. `scripts/build-plugin.py` combines these sources into complete host packages; generated package content is never edited as behavior.
