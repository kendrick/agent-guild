# Open Questions

Unresolved and shouldn't be guessed at. Answers move to [[decisionLog]] when settled.

## Claude Max-subscription quota shape, pending a live encounter

Issue #52 verified the Claude Code 2.1.212 process contract with a controlled Anthropic-shaped 429: a terminal no-retry response exits 1 with `api_error_status: 429`, while the default path retries silently up to 11 attempts. The maintainer's live Max subscription was not deliberately exhausted, so its exact provider payload and whether it disables retry remain unobserved. The reciprocal courier must classify the structured 429 and own a wall-clock bound; tune any wording fallback on the first live encounter.

## Does cross-family checking pay against a model that isn't `gpt-5.6-terra`?

The general question was settled no on 2026-08-13 and the answer lives in [[decisionLog]]; what remains open is the part #34's corpus could not reach. Every one of its 85 ledger rows records `model: gpt-5.6-terra`, so the ruling covers one non-Claude model rather than cross-family checking. #167 kept the lane's plumbing wired for exactly that reason. Two data points worth carrying into any such experiment: both real far-family defects landed on judgment clauses, and the corpus's single `changed_verdict: yes` came from a crossing that blocked rather than one that returned a judgment. Tracked as #147, whose entry condition is a lane running against some other vendor.

## Cache the audit apparatus, or diff it? — parked on a written entry condition

#122 wants the reference implementation cached so rounds stop rebuilding it. #198 wants the opposite: keep rebuilding, then diff against the predecessor and file every material divergence as a finding against the clause the two readings turn on. Both read the same two-job evidence base, and the two jobs disagree — `dotfiles#19` diverged twice with both divergences real blockers, `dotfiles#22` converged. `skills#27`, which supplies the six-rebuilds headline, predates both #119 and #191.

The condition, in order. **#196 lands first**, because `## DEC-audit` carries no execution requirement at all and a DEC round that does not build gives neither issue anything to compare; on `#22` the DEC auditors built past their charter on their own initiative, which is the only reason that data exists. **Then a job that qualifies**: two or more consecutive DEC rounds against a byte-identical `constitution.md` (verifiable from the `CON-audit-r<N>.md.sha256` stamp that already exists), carrying at least one clause whose check needs a reference implementation, with both rounds' artifacts preserved rather than deleted at teardown. About a third of archived runs have that shape, so it is not a long wait.

Divergences that turn out to be real clause defects settle it for #198; convergence every time settles it for #122; divergence only on naming and formatting means neither earns its complexity and the cheap answer is caching. Full write-up on #122. Note that PR #199 made the evidence harder to collect on purpose, by stating that apparatus is deleted at teardown — a run gathering this has to opt out and say so.

## Is `cached_input_tokens` a subset of `input_tokens`, or disjoint from it?

The ledger has never recorded cached input. `codex-courier.py:190-202` names the field and declines to read it, with a comment asserting it is "reported alongside input_tokens but is not added into it" — which, if true, means `tokens_in` **undercounts** total input rather than merely mispricing it. The usual vendor convention is the opposite: cached is a subset of the reported input count. Nobody has checked which, and the answer changes the size of the problem by a factor of two on some rows.

What the three surviving raw streams show (retention is `onissue`, so these are the crossings that went wrong and are a biased sample): `input_tokens` 79,566 with `cached_input_tokens` 56,576; 19,119 with 15,104; and 20,455 with 0. Whatever the relationship, the variance is large enough that no cost-per-crossing figure derived from the current ledger converts to money reliably. Token counts as recorded are accurate and comparisons between crossings hold; only the conversion is unsafe.

Filed as #157, timeboxed to half a day, closing with a written answer on #34. `reasoning_output_tokens` sits in the same usage block and is also uncaptured. Capturing either going forward is separate work; the seam is `optional_ledger_fields` in `subagent-return.py`, which T-009 left for exactly this.

## Codex quota failure shape, pending a live encounter

The `codex exec` flags, sandbox modes, output mechanisms, and usage reporting were all verified live on 2026-07-24 (issue #2's closing comment is the reference). The identity half of this note is settled and moved to [[decisionLog]]. The one remaining unknown: the quota/rate-limit failure shape — exit code and stderr wording — that the courier's exhaustion detection must match. Nothing triggered it cheaply; tune on the first real quota event.

**2026-08-11: what a rejected turn looks like.** #142's probe sent `-m definitely-not-a-model` and drew a structured refusal rather than a bare exit. `codex exec` exits 1, writes no `-o` file, and emits two things worth matching on: a top-level `{"type":"error","message":…}` event, and a `turn.failed` whose `error.message` is a JSON *string* wrapping `{"type":"error","status":400,…}`. Stderr carried nothing but `Reading additional input from stdin...`. If a 429 arrives the same way, and there's no reason to think it wouldn't, then exhaustion detection has to read a status out of that nested string. The wording it was written to match sat on a stream that stayed empty.

## Does `sandbox_mode: read-only` deny a write inside the workspace?

Half answered on 2026-07-31. Outside the workspace it denies nothing: two read-only agents, `checker-deterministic` and `checker-courier`, wrote to `/private/tmp` on their own initiative in a normal run and both writes landed. So the mode constrains the project directory at most, and #76's "read-only checkers return their verdict instead of writing it" is a protocol the agents follow because the role prompt tells them to, not a boundary the host enforces.

The half that matters to the org chart is still open, because three probes failed to test it. The generated read-only protocol says *do not write or edit any project, artifact, task, state, ledger, or verdict file*, so a compliant checker never attempts the in-workspace write, and `/private/tmp` satisfies the letter of the instruction. Testing the sandbox rather than the instruction needs a prompt that explicitly overrides the role protocol, the way the `followup_task` probe eventually did.

## Ledger Defects #117 Recorded and Left Alone

Backfilling `job` meant reading all 18 rows of `~/repos/skills/.agent-guild/state/archive/2026-08-08-issue-27/log/vendor-calls.jsonl` closely, which turned up five things wrong with them. #117 fixed none of it on purpose. A job that is already editing every row is the wrong place to also start correcting them, because afterward nobody can tell a repair from a rewrite. They're recorded here so "reported" is an artifact rather than something someone remembers to mention.

Three are in the archived data:

- **Ten of the 18 rows record artifact paths under a home directory that doesn't exist.** Rows at indices 1, 3, 4, 6, 8, 12, 13, 14, 15, and 16 carry absolute paths under `/Users/karnett/` rather than `/Users/k.arnett/`, so none of them resolve on this machine. Every one was written under courier obligation 2 in `docs/vendor-ledger.md`, which says to list only what you verified on disk, so these are exactly the paths that were supposed to have been checked. Whether the courier checked a real path and mangled the string on the way out or checked nothing at all isn't recoverable from the row.
- **One `started_at` carries fractional seconds.** Index 2 reads `2026-08-08T00:15:45.686223Z`; the other 17 are whole seconds. Nothing catches it, because the schema types `started_at` as a plain string. It only bites a collector that compares timestamps as text.
- **Four rows are duplicated across two archives.** Indices 7 through 10 are also the entire contents of `2026-08-08-issue-32/log/vendor-calls.jsonl`, identical but for the `job` key the backfill added to the #27 copies. Count crossings by walking the archive tree and those four get counted twice. The #32 archive's own four rows carry no `job` key at all, and an absent key means unattributed rather than attributed to #32. The backfill deleted neither copy, since a run against one archive has no business rewriting another run's record. So grouping by `job` doesn't double-count these four—it counts the #27 copies toward #32 and leaves the #32 archive's own rows in no job at all.

Two more surfaced in this repo during #117's own run. Both are about the courier writing the row rather than about the ledger's shape:

- **A courier appended its row to the wrong file.** One crossing landed in `.agent-guild/state/log/calls.jsonl` instead of `vendor-calls.jsonl`, where nothing reads it; the row was moved back by hand. `ledger-append.py` validates the line exhaustively and the destination not at all, since `--ledger` takes any path and creates it on demand. A path one character wrong therefore produces a perfectly valid line in a file nobody opens.
- **A `started_at` about 25 hours off from the crossing it stamps.** T-004's courier row in this repo's own ledger reads `2026-08-10T00:15:00Z` for a call whose verdict file landed at `2026-08-11T01:16:01Z`. #117 lists this as a non-goal, being a defect in the writing agent rather than in the ledger format, but it's the same reason the archived rows were hard to attribute: a timestamp that can't be trusted can't order a job's crossings either. The backfill had to attribute one row by append position for exactly that reason.

## Why four probes recorded no `SubagentStop` while the event fires

Verified 2026-07-31: `SubagentStop` fires on codex-cli 0.145.0 at agent completion, about a second after `SubagentStart`, with a complete payload. Four earlier probes across two projects captured nothing, under both a no-matcher catch-all and the guild's own agent-name matcher, while `SessionStart`, `PreToolUse`, and `Stop` all landed in the same directories through the same recorder. The one asymmetry noticed but not tested: those capture directories sat under `/private/tmp`, and Codex's sandbox denies writes there, though the parent's `PreToolUse` captures reached them anyway. Until this is understood, treat an absent capture as weak evidence and register a control event known to fire in the same session before concluding anything from silence.

That method earned itself on 2026-08-12. #134's step 0 spike concluded that guild hooks never fire for workflow-spawned agents, and the finding only holds because the same dispatch was run through the ordinary Agent path in the same session and was refused. Silence alone would have proven nothing. The question here stays open; what's settled is that the control is worth the extra minute.

## Should a Gating Heuristic Announce Itself?

`check-job-spec.py` refuses an auditor dispatch on the first rule that fires, and eleven rules all block identically. Seven of them prove: a cited line exists, a script is executable, the graph is acyclic. Four infer, each carrying constants tuned against a single seven-task corpus. `run_rules` already orders them proofs-first and its docstring says so, but nothing downstream carries the distinction.

The failure modes are not symmetric. A proof that fires means the paperwork is wrong; an inferring rule that fires may mean the rule misread the prose, and on a misread the job stops with no recourse short of `PAUSED`, which stands down every gate rather than the one that misfired. #132's adversarial review produced false positives in R2, R10, R4's preamble scan, and R9. Three are fixed; R9's is documented at the rule as a deliberate trade, because the only fix that closes it re-blinds the rule on three real sentences.

So the original worry runs in both directions. #132 warned that approximating judgment gives false confidence; the measured cost so far is the reverse, where a misfire deadlocks rather than under-catches. Tracked as #139, which lays out three directions and picks none, because choosing needs evidence about how often heuristics misfire in real jobs and there is exactly one corpus so far. Warn-only is already ruled out (see [[antipatterns]]).
