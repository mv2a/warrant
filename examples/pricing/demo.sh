#!/usr/bin/env bash
# A walkthrough of Warrant on a small shop's checkout pricing.
# Both candidates were written by coding agents. Nobody needs to read either one.
set -uo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$(cd ../.. && pwd)${PYTHONPATH:+:$PYTHONPATH}"
PY="${PYTHON:-python3}"
unexpected=0

step() { printf '\n\033[1m%s\033[0m\n' "$1"; }
run() {  # run EXPECTED-EXIT-STATUS WARRANT-ARGUMENTS...
  local want=$1 shown="" arg
  shift
  for arg in "$@"; do
    case "$arg" in *" "*) shown+=" \"$arg\"" ;; *) shown+=" $arg" ;; esac
  done
  printf '\n$ warrant%s\n' "$shown"
  "$PY" -m warrant "$@"
  local got=$?
  if [ "$got" -ne "$want" ]; then
    printf '!! expected exit status %s, got %s\n' "$want" "$got"
    unexpected=1
  fi
}

rm -rf ledger

step "1. The principal wrote intent.md and an examiner drafted checks. The principal approves them."
run 0 check
run 0 approve --by dana --note "Pricing rules for the autumn launch"

step "2. The builder gets a brief. It never includes the hidden checks."
run 0 brief

step "3. Candidate A passes every check it can see..."
run 1 verify --workspace candidates/overfit --audience builder
run 1 gate merge --workspace candidates/overfit

step "4. Candidate B keeps every promise."
run 0 verify --workspace candidates/honest --audience builder
run 0 gate merge --workspace candidates/honest
run 0 gate release --workspace candidates/honest

step "5. What the principal reads instead of code."
run 0 report --workspace candidates/overfit

step "6. A problem in production stops releases until it becomes a check."
run 0 incident add INC-1 "Checkout took 9 seconds during the flash sale" --by dana
run 1 gate release --workspace candidates/honest

step "7. The ledger records every step and shows whether it has been edited."
run 0 log
run 0 log --verify

if [ "$unexpected" -ne 0 ]; then
  printf '\nThe demo did not go as expected.\n'
  exit 1
fi
