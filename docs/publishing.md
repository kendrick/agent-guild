# Publishing

This file collects the policies for shipping this repo as a Claude Code plugin marketplace. It starts with the one policy this job owns; issue #25 will grow it into the full checklist.

## Version Bumps

Claude Code detects plugin updates through the `version` field in `plugin/.claude-plugin/plugin.json`, currently `0.2.0`. The marketplace manifest points at `./plugin`, so that version string is the only signal an installed copy watches.

Bump it whenever you publish a change to the `plugin/` tree. Skip the bump and the republish looks fine from here, but every existing install keeps running the old code until someone notices.
