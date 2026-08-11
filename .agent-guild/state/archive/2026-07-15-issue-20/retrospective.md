# Retrospective: build-plugin.py (Issue #20)

Third guild run, first consumed through `/job` intake, and the first with zero FAIL verdicts anywhere: CON-audit, DEC-audit, and the single task all passed at round 0. Three verdicts, three PASSes, no disputes, no escalations.

## Catches

None on the record, but one worth counting honestly: the orchestrator caught its own defect before audit. The C-3 check command's first draft embedded a broken inline-python artifact and a nested-quoting scheme that would have exploded in `check-build.sh`; it was rewritten (single-quote outer, env-var handoff for the temp path) before the auditor saw it. The auditor then dry-ran the corrected command against a stub build and confirmed it discriminates. Two jobs of auditor catches at Phase 0 appear to have taught the clause-writer what the auditor will do to sloppy checks — the verification pressure moved upstream, which is the system working, not the system idle.

## The Deviation Ruling

The one genuinely new event: the worker deviated from the spec excerpt's literal wording ("all of `.agent-guild/scripts/`") by filtering `__pycache__`, `node_modules`, and `package-lock.json` out of the project-template payload, and flagged the call in its notes. The checker ruled on it rather than rubber-stamping or reflexively failing: it confirmed every git-tracked source ships byte-for-byte and that the filter removes only untracked, gitignored debris, then judged the clause text and intent satisfied. That is the dispute machinery's cheaper cousin — a flagged deviation resolved by the checker against the constitution — and it worked without a rework cycle.

## Strain

None. A one-task job with a heavily pre-verified constitution left nothing to strain against. The `--check` battery (drift, absence, missing-CLI) and the platform validator all passed on the first artifact.

## What Feeds The Epic

`scripts/build-plugin.py` and `scripts/plugin-src/plugin.json` unblock every other child of #19: #21 commits the build's output, #22 and #23 add components the build already knows to include when they appear, #24 adds the marketplace file the manifest is ready for. The include-when-present rule means none of those need build-script changes — they land sources and rerun the build. Standing pattern, three jobs strong: the auditor's leverage is at Phase 0, checks assert sources not ambient state, and the platform's own validator (`claude plugin validate --strict`) is the manifest standard.
