#!/usr/bin/env bash
# Run every script-checked clause of #193's constitution against one tree and
# print a one-line-per-clause result. The clause commands are transcribed
# verbatim from constitution.md's `- **check**:` fields.
#
#   run_clauses.sh <tree> [clause...]
set -uo pipefail
TREE="$1"; shift
WANT="${*:-C-1 C-2 C-3 C-4 C-5 C-6 C-7 C-8 C-9}"
cd "$TREE" || exit 3

run() {
  local id="$1"; shift
  case " $WANT " in *" $id "*) ;; *) return ;; esac
  out=$("$@" 2>&1); rc=$?
  printf '%-4s rc=%-3s %s\n' "$id" "$rc" "$(echo "$out" | grep -Ei 'FAILED|failed|out of scope|OK:|passed|difference' | tail -1)"
}

run C-1 .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r10-adjective'
run C-2 .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r10-corpus'
run C-3 .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r21-unsafe'
run C-4 .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r21-safe'
run C-5 .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py r2-anchor'
run C-6 .agent-guild/scripts/check-build.sh 'python3 .agent-guild/scripts/test_check_job_spec.py && python3 .agent-guild/scripts/check-job-spec.py --self-test && python3 .agent-guild/hooks/test_hooks.py && python3 scripts/build-plugin.py --check'
run C-7 .agent-guild/scripts/check-diff-scope.py .agent-guild/scripts/check-job-spec.py .agent-guild/scripts/test_check_job_spec.py plugin/ plugins/ --ignore .agent-guild/state/
run C-8 .agent-guild/scripts/check-build.sh 'python3 -X importtime -c "import importlib.util,sys; s=importlib.util.spec_from_file_location(\"m\",\".agent-guild/scripts/check-job-spec.py\"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)" >/dev/null 2>&1 && python3 -c "import ast,sys; t=ast.parse(open(\".agent-guild/scripts/check-job-spec.py\").read()); mods={(n.module or \"\").split(\".\")[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom)} | {a.name.split(\".\")[0] for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names}; bad=sorted(m for m in mods if m and m not in sys.stdlib_module_names); sys.exit(1 if bad else 0)"'
run C-9 .agent-guild/scripts/check-build.sh 'python3 .agent-guild/state/checks/probe.py suite-coverage'
