# Publishing

This file collects the policies for shipping this repo as a Claude Code plugin marketplace.

## Version Bumps

Claude Code detects plugin updates through the `version` field in `plugin/.claude-plugin/plugin.json`. That file is a build output, though, not something you edit directly. The authored source is `scripts/plugin-src/plugin.json`, and `build-plugin.py` copies it into the committed `plugin/` tree. Bump the source.

Bumping the build output instead is the classic mistake: it looks like it worked, `--check` stays green, but the next rebuild copies the un-bumped source back over it and silently reverts your change. Every existing install keeps running the old code until someone notices.

Ordinary work commits never touch this field. Only the release commit bumps it, in the checklist below.

## Release Checklist

A release is one mechanical commit, separate from the work that earns it. Everything that changes plugin behavior lands as its own ordinary commit first, version untouched. Only when you're ready to cut a release do you run the five steps below, in order, to produce that one commit.

1. **Bump the version** in `scripts/plugin-src/plugin.json`, in your working tree only; don't commit yet. See [Version Bumps](#version-bumps) above for why it's this file and not the build output.
2. **Generate the changelog section**: `python3 scripts/make-changelog.py <version>`. Because that bump isn't committed yet, the script takes its in-flight path: it covers every commit back to the last release, dated today, instead of looking for a boundary commit that doesn't exist. Rerun it as often as you like while more work lands before you commit; each run replaces the provisional section instead of duplicating it.
3. **Rebuild**: `python3 scripts/build-plugin.py`. This assembles the committed `plugin/` tree from the in-repo sources.
4. **Verify**: `python3 scripts/build-plugin.py --check`. This rebuilds into a temp directory, diffs it against the committed tree in both directions, runs `claude plugin validate --strict`, and fails if `CHANGELOG.md` has no section for the bumped version. It has to exit 0 before anything ships.
5. **Commit** the bumped source, the generated changelog section, and the rebuilt `plugin/` tree together, and nothing else. The changelog was generated before this commit existed, so the release commit itself never shows up in its own section—that's expected, not a bug to chase.

## Tagging a Release

Once the release commit lands, tag it and cut a GitHub release with notes pulled from the changelog section instead of retyped by hand:

```sh
git tag vX.Y.Z
git push origin vX.Y.Z
gh release create vX.Y.Z --notes "$(python3 scripts/make-changelog.py --notes X.Y.Z)"
```

`make-changelog.py --notes` prints the existing `X.Y.Z` section verbatim, or exits nonzero if one is missing. That's the tag-side backstop for the same mistake `--check` catches on the source side: a release cut from this flow can't ship without notes.
