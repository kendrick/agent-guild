# Open Questions

Unresolved and shouldn't be guessed at. Answers move to [[decisionLog]] when settled.

## Does cross-family checking actually pay?

The whole multi-provider arc rests on the claim that a checker from a different model family catches what same-family checking can't see. #34 tests it over 10 dual-checked tasks. As of 2026-07-24: **6 crossings — 5 agreements, 1 blocked, and zero unique findings in either direction.** Four more crossings decide it. A near-zero unique-finding rate closes v0.6.0 through v0.8.0 as won't-do, which is the evaluation succeeding, not failing — the gate exists so the answer can be no. Note the board can't advance itself: every open issue is downstream of this question, so the crossings have to come from ungated work.

## Codex quota failure shape, pending a live encounter

The `codex exec` flags, sandbox modes, output mechanisms, and usage reporting were all verified live on 2026-07-24 (issue #2's closing comment is the reference; default model pinned to `gpt-5.6-terra` in `~/.codex/config.toml`). The one remaining unknown: the quota/rate-limit failure shape — exit code and stderr wording — that the courier's exhaustion detection must match. Nothing triggered it cheaply; tune on the first real quota event.
