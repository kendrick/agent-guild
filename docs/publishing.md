# Publishing

This file collects the policies for shipping this repo as a Claude Code plugin marketplace.

## Version Bumps

Claude Code detects plugin updates through the `version` field in `plugin/.claude-plugin/plugin.json`. That file is a build output, though, not something you edit directly. The authored source is `scripts/plugin-src/plugin.json`, and `build-plugin.py` copies it into the committed `plugin/` tree. Bump the source.

Bumping the build output instead is the classic mistake: it looks like it worked, `--check` stays green, but the next rebuild copies the un-bumped source back over it and silently reverts your change. Every existing install keeps running the old code until someone notices.

Bump the version whenever you publish a change to the `plugin/` tree. The marketplace manifest points at `./plugin`, so that version string is the only signal an installed copy watches.

## Release Checklist

1. **Bump the version** in `scripts/plugin-src/plugin.json`. This is the authored source; see [Version Bumps](#version-bumps) above for why it has to be this file, not the build output.
2. **Rebuild**: `python3 scripts/build-plugin.py`. This assembles the committed `plugin/` tree from the in-repo sources.
3. **Verify**: `python3 scripts/build-plugin.py --check`. This rebuilds into a temp directory, diffs it against the committed tree in both directions, and runs `claude plugin validate --strict`. It has to exit 0 before anything ships.
4. **Commit** the bumped source, the rebuilt `plugin/` tree, and whatever source change prompted the release, together in one commit. That way no push ever carries a stale tree.
