---
name: job
description: Phase 0 intake for a guild job. Turns an existing GitHub issue or a BYO spec ($ARGUMENTS — issue number, owner/repo#N, issue URL, local file path, or other URL) into .agent-guild/state/spec.md with a provenance header, then flows straight into /agent-guild:constitution. Use when starting a job from an issue or an existing document — "build issue #12", "kick off a job from this spec".
---

# Intake a spec or issue

`/agent-guild:job` is the guild's front door for work that already exists somewhere — a GitHub issue, a doc on disk, a page at a URL — instead of being authored fresh in the constitution interview. Its only artifact is one file, `.agent-guild/state/spec.md`, and its governing rule is **never fabricate**: every byte of spec content comes verbatim from the source, and a fetch failure produces an honest error, not a guess.

## 1. Classify `$ARGUMENTS`

Match `$ARGUMENTS` against these forms, in order, and take the first that fits:

1. **Bare number or `#N`** (e.g. `15`, `#15`) — a GitHub issue in the current repo.
2. **`owner/repo#N`** (e.g. `acme/widgets#42`) — a GitHub issue in another repo.
3. **A GitHub issue URL** (`https://github.com/<owner>/<repo>/issues/<N>`).
4. **An existing local file path** — check with a quick existence test (e.g. `test -f "$ARGUMENTS"`) before treating it as one.
5. **Any other URL** (starts with `http://` or `https://` but isn't a GitHub issue URL).
6. **No argument at all.**

Don't guess between these — if `$ARGUMENTS` doesn't cleanly match one, treat it as unrecognized input and tell the user what you saw and which forms are supported, rather than picking the closest one.

## 2. Fetch the content

**Forms 1–3 (GitHub issue).** Run one of:

```
gh issue view N --json number,title,body,url                # form 1 (current repo)
gh issue view N -R owner/repo --json number,title,body,url   # form 2
gh issue view <url> --json number,title,body,url             # form 3
```

Before trusting the result, handle failure honestly:
- `gh` not installed (command not found) → tell the user `gh` is missing and how intake depends on it. Write nothing.
- `gh` unauthenticated (auth error in stderr) → surface that exact error and tell the user to run `gh auth login`. Write nothing.
- Issue not found / repo not found (nonzero exit) → surface `gh`'s actual error text. Write nothing.

On success, parse the JSON's `title`, `body`, and `url` fields. Derive `owner/repo#N` from the `url` field (matches `github\.com/([^/]+/[^/]+)/issues/(\d+)`) so `ref` is consistent no matter which of the three forms was used to invoke `gh`.

**Form 4 (local file).** Read the file's raw content — that content is the entire spec body, unmodified. `ref` is the path as given in `$ARGUMENTS`.

**Form 5 (other URL).** Fetch it (the `WebFetch` tool if available, otherwise `curl -sL <url>`) and use the response body as the spec content verbatim — no summarizing, no reformatting. `ref` is the URL.

**Form 6 (no argument).** Do not guess and do not fetch anything. Tell the user there are two ways forward: point `/agent-guild:job` at an issue, a file, or a URL to intake existing work, or skip intake entirely and run `/agent-guild:constitution`, whose interview authors the spec from scratch. Stop here — write no file.

## 3. Write `.agent-guild/state/spec.md`

Exactly one file, and nothing else. Structure: the provenance header first, then the spec content, in that order — never the reverse, never interleaved.

The header is flat YAML frontmatter, matching `.agent-guild/scripts/check-provenance.py` exactly:

```
---
source: github-issue | file | url
ref: <owner/repo#N | path | URL>
issue: <N>                # only when source is github-issue
title: <issue title>      # only when source is github-issue
fetched_at: <ISO-8601 UTC, e.g. 2026-07-14T18:00:00Z>
---
```

- `source` is `github-issue` for forms 1–3, `file` for form 4, `url` for form 5.
- `fetched_at` is the current UTC time in that exact format (e.g. `date -u +%Y-%m-%dT%H:%M:%SZ`) — a trailing `Z` is required, not an offset.
- `issue` and `title` are present only when `source: github-issue`; omit both keys entirely for `file` and `url`.

Content, after the closing `---`:
- **Issues**: the issue title as a Markdown heading (`# <title>`), a blank line, then the full issue body exactly as `gh` returned it — its own Markdown (code fences, lists, links) preserved untouched. Do not summarize, trim, or editorialize.
- **File and URL sources**: the fetched/read content as-is, with no synthesized heading and no edits.

## 4. Self-check the header

Run the validator against what you just wrote:

```
.agent-guild/scripts/check-provenance.py .agent-guild/state/spec.md
```

Add `--issue N` when intake came from an issue (forms 1–3), so the validator also confirms the recorded `issue` matches the one you fetched. A nonzero exit means the header you wrote doesn't match the contract — fix it and re-run the check before moving on; don't leave a spec.md that fails its own validator.

## 5. Flow into `/agent-guild:constitution`

Once step 4's validator exits `0`, tell the user in one line that `.agent-guild/state/spec.md` is ready and validated — then, in that same turn, invoke `/agent-guild:constitution` yourself via the Skill tool. The turn that validates the spec is the turn that starts Phase 0.

`/agent-guild:constitution` collapses its interview into a confirm-and-adjust step when `spec.md` already exists. That step belongs to the user: invoke the skill and let its interview run as designed — carry the baton to the confirm step, not past it.

This flow-through is conditional on a successful, validated write. Every failure path in steps 1–2 already stops with an honest message and no `spec.md` on disk; none of them reaches this step or invokes `/agent-guild:constitution`.
