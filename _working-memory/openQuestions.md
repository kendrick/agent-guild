# Open Questions

Unresolved and shouldn't be guessed at. Answers move to [[decisionLog]] when settled.

## Codex quota failure shape, pending a live encounter

The `codex exec` flags, sandbox modes, output mechanisms, and usage reporting were all verified live on 2026-07-24 (issue #2's closing comment is the reference; default model pinned to `gpt-5.6-terra` in `~/.codex/config.toml`). The one remaining unknown: the quota/rate-limit failure shape — exit code and stderr wording — that the courier's exhaustion detection must match. Nothing triggered it cheaply; tune on the first real quota event.
