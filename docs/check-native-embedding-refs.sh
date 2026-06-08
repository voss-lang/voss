#!/bin/sh
# check-native-embedding-refs.sh — references-resolve gate for docs/native-embedding.md (VSDK-C-06).
#
# Enumerates every path the doc cites and verifies it resolves:
#   - ALWAYS-EXPECTED-NOW  : .planning/PROTOCOL.md, docs/sdk.md  -> missing = hard FAIL (exit 1).
#   - UPSTREAM-GATED       : contracts/openapi.json + contracts/events.schema.json (V13.1),
#                            docs/ORCHESTRATION_LAYERS.md (V13)  -> while any is absent, WARN-SKIP (exit 0),
#                            because the doc is authored against to-be-committed artifacts (D-02/D-04).
# Once ALL upstream-gated paths are present, the doc's stability-tier terms must be defined in
# docs/ORCHESTRATION_LAYERS.md (at minimum: generated-from-protocol, deferred) — missing = hard FAIL.
#
# Pure POSIX builtins (test/grep/echo). No dependencies, no code.

set -u
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/.." && pwd))
cd "$root" || { echo "FATAL: cannot cd to repo root"; exit 2; }

always_expected=".planning/PROTOCOL.md docs/sdk.md"
upstream_gated="contracts/openapi.json contracts/events.schema.json docs/ORCHESTRATION_LAYERS.md"

fail=0
pending=0

echo "references-resolve check for docs/native-embedding.md"
echo "--- always-expected ---"
for p in $always_expected; do
  if [ -e "$p" ]; then
    echo "OK       $p"
  else
    echo "MISSING  $p   (hard fail: always-expected path absent)"
    fail=1
  fi
done

echo "--- upstream-gated (V13.1 / V13) ---"
for p in $upstream_gated; do
  if [ -e "$p" ]; then
    echo "OK       $p"
  else
    echo "SKIP     $p   (pending upstream: V13.1 contracts/ or V13 ORCHESTRATION_LAYERS.md unshipped)"
    pending=1
  fi
done

if [ "$pending" -eq 0 ]; then
  echo "--- tier terms in docs/ORCHESTRATION_LAYERS.md ---"
  for term in generated-from-protocol deferred; do
    if grep -q "$term" docs/ORCHESTRATION_LAYERS.md; then
      echo "OK       tier term: $term"
    else
      echo "MISSING  tier term: $term   (the doc maps to a tier the taxonomy must define)"
      fail=1
    fi
  done
fi

echo "--- summary ---"
if [ "$fail" -ne 0 ]; then
  echo "FAIL: one or more required references did not resolve."
  exit 1
fi
if [ "$pending" -ne 0 ]; then
  echo "WARN-SKIP: always-expected refs resolve; some upstream-gated refs pending — not blocking (exit 0)."
  exit 0
fi
echo "PASS: all cited references resolve and tier terms are defined."
exit 0
