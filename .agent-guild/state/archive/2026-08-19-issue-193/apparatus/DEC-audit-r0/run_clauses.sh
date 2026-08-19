#!/usr/bin/env bash
# Run every script-checked clause of the #193 constitution against one tree,
# plus the two rubric probes (whose exit code is the mechanical half a checker
# is told to settle on before reading anything).
#
#   run_clauses.sh <tree> [clause-ids...]
#
# Each clause's command is transcribed verbatim from constitution.md. `cd`
# lives inside the invocation so nothing ever runs anywhere but <tree>.
set -uo pipefail
TREE="$1"; shift
WANT="${*:-C-1 C-2 C-3 C-4 C-5 C-6 C-7 C-8 C-9}"

run() {
  local id="$1"; shift
  case " $WANT " in *" $id "*) ;; *) return 0 ;; esac
  local out rc
  out=$(cd "$TREE" && eval "$*" 2>&1)
  rc=$?
  echo "### $id rc=$rc"
  echo "$out" | tail -25
  echo
}

run C-1 ".agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r10-adjective'"
run C-2 ".agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r10-corpus'"
run C-3 ".agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r21-unsafe'"
run C-4 ".agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r21-safe'"
run C-5 "python3 .agent-guild/state/checks/probe.py r2-anchor"
run C-6 ".agent-guild/scripts/check-build.sh 'python3 .agent-guild/scripts/test_check_job_spec.py && python3 .agent-guild/scripts/check-job-spec.py --self-test && python3 .agent-guild/hooks/test_hooks.py && python3 scripts/build-plugin.py --check'"
run C-7 ".agent-guild/scripts/check-diff-scope.py .agent-guild/scripts/check-job-spec.py .agent-guild/scripts/test_check_job_spec.py plugin/ plugins/ --ignore .agent-guild/state/"
run C-9 "python3 .agent-guild/state/checks/probe.py suite-coverage"
