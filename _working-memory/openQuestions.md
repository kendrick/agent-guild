# Open Questions

Unresolved and shouldn't be guessed at. Answers move to [[decisionLog]] when settled.

## Claude Max-subscription quota shape, pending a live encounter

Issue #52 verified the Claude Code 2.1.212 process contract with a controlled Anthropic-shaped 429: a terminal no-retry response exits 1 with `api_error_status: 429`, while the default path retries silently up to 11 attempts. The maintainer's live Max subscription was not deliberately exhausted, so its exact provider payload and whether it disables retry remain unobserved. The reciprocal courier must classify the structured 429 and own a wall-clock bound; tune any wording fallback on the first live encounter.

## Does cross-family checking actually pay?

The whole multi-provider arc rests on the claim that a checker from a different model family catches what same-family checking can't see. #34 tests it over 10 dual-checked tasks. As of 2026-07-24: **6 crossings — 5 agreements, 1 blocked, and zero unique findings in either direction.** Four more crossings decide it. A near-zero unique-finding rate closes v0.6.0 through v0.8.0 as won't-do, which is the evaluation succeeding, not failing — the gate exists so the answer can be no. Note the board can't advance itself: every open issue is downstream of this question, so the crossings have to come from ungated work.

## Codex quota failure shape, pending a live encounter

The `codex exec` flags, sandbox modes, output mechanisms, and usage reporting were all verified live on 2026-07-24 (issue #2's closing comment is the reference; default model pinned to `gpt-5.6-terra` in `~/.codex/config.toml`). The one remaining unknown: the quota/rate-limit failure shape — exit code and stderr wording — that the courier's exhaustion detection must match. Nothing triggered it cheaply; tune on the first real quota event.

## Does `sandbox_mode: read-only` deny a write inside the workspace?

Half answered on 2026-07-31. Outside the workspace it denies nothing: two read-only agents, `checker-deterministic` and `checker-courier`, wrote to `/private/tmp` on their own initiative in a normal run and both writes landed. So the mode constrains the project directory at most, and #76's "read-only checkers return their verdict instead of writing it" is a protocol the agents follow because the role prompt tells them to, not a boundary the host enforces.

The half that matters to the org chart is still open, because three probes failed to test it. The generated read-only protocol says *do not write or edit any project, artifact, task, state, ledger, or verdict file*, so a compliant checker never attempts the in-workspace write, and `/private/tmp` satisfies the letter of the instruction. Testing the sandbox rather than the instruction needs a prompt that explicitly overrides the role protocol, the way the `followup_task` probe eventually did.

## Why four probes recorded no `SubagentStop` while the event fires

Verified 2026-07-31: `SubagentStop` fires on codex-cli 0.145.0 at agent completion, about a second after `SubagentStart`, with a complete payload. Four earlier probes across two projects captured nothing, under both a no-matcher catch-all and the guild's own agent-name matcher, while `SessionStart`, `PreToolUse`, and `Stop` all landed in the same directories through the same recorder. The one asymmetry noticed but not tested: those capture directories sat under `/private/tmp`, and Codex's sandbox denies writes there, though the parent's `PreToolUse` captures reached them anyway. Until this is understood, treat an absent capture as weak evidence and register a control event known to fire in the same session before concluding anything from silence.
