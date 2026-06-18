#!/usr/bin/env bash
# DIAG-B (task-mqh1sbc7-c961c077): server-side repro for the "plan turn idles
# with no plan/tool/final" bug. Drives `voss serve` over real HTTP/SSE and
# captures BOTH server stderr (/tmp/voss_repro/*_serve.log) and the SSE stream
# (*_sse.log) for several scenarios, then prints a verdict per hypothesis.
#
# Scratch/diagnostic only — does NOT touch voss/ source. Re-runnable.
#
# Usage:  bash scripts/repro_server.sh
# Requires: repo .venv, codex-oauth creds (~/.codex/auth.json), curl.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
PY=".venv/bin/python"
OUT="/tmp/voss_repro"
mkdir -p "$OUT"

# Track background pids for cleanup.
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null; done; }
trap cleanup EXIT

# --- start a fresh server; sets PORT, TOKEN globals -------------------------
# args: <logfile> [extra env assignments...]
start_server() {
  local logfile="$1"; shift
  rm -f "$logfile"
  # `< <(sleep 120)` holds stdin open (piped, not a tty) so the EOF heartbeat
  # in serve.py auto-terminates the server after 120s if we leak it. Both
  # stdout (handshake JSON) and stderr (tracebacks) land in $logfile.
  env "$@" "$PY" -m voss.cli serve --port 0 < <(sleep 120) > "$logfile" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  SERVER_PID="$pid"
  # Wait for the handshake line.
  local i
  for i in $(seq 1 60); do
    if grep -q '"port"' "$logfile" 2>/dev/null; then break; fi
    sleep 0.25
  done
  local hs
  hs="$(grep -m1 '"port"' "$logfile" 2>/dev/null)"
  if [ -z "$hs" ]; then
    echo "!! server failed to hand shake; log tail:"; tail -20 "$logfile"; return 1
  fi
  PORT="$(printf '%s' "$hs" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["port"])')"
  TOKEN="$(printf '%s' "$hs" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["token"])')"
  return 0
}

stop_server() { kill "${SERVER_PID:-}" 2>/dev/null; wait "${SERVER_PID:-}" 2>/dev/null; }

# --- run one scenario -------------------------------------------------------
# args: <tag> <session_body_json> <msg_body_json> <max_wait_s> [env...]
run_scenario() {
  local tag="$1"; local sbody="$2"; local mbody="$3"; local maxwait="$4"; shift 4
  local slog="$OUT/${tag}_serve.log"
  local sse="$OUT/${tag}_sse.log"
  rm -f "$sse"

  echo
  echo "============================================================"
  echo "SCENARIO: $tag"
  echo "  session body: $sbody"
  echo "  message body: $mbody"
  echo "  env: $*"
  echo "============================================================"

  start_server "$slog" "$@" || { echo "  [skip] no server"; return; }

  # Create session.
  local cresp sid asrc
  cresp="$(curl -s -X POST "http://127.0.0.1:$PORT/session" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      -d "$sbody")"
  sid="$(printf '%s' "$cresp" | "$PY" -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d.get("id",""))
except Exception: print("")' )"
  asrc="$(printf '%s' "$cresp" | "$PY" -c 'import sys,json
try: print(json.load(sys.stdin).get("auth",""))
except Exception: print("")' )"
  if [ -z "$sid" ]; then
    echo "  [fail] POST /session -> $cresp"; stop_server; return
  fi
  echo "  session id: $sid   auth: $asrc"

  # Attach the single SSE consumer BEFORE posting the message.
  ( curl -sN "http://127.0.0.1:$PORT/session/$sid/events" \
      -H "Authorization: Bearer $TOKEN" > "$sse" 2>/dev/null ) &
  local ssepid=$!
  PIDS+=("$ssepid")
  sleep 0.7

  # Fire the turn.
  local mresp
  mresp="$(curl -s -X POST "http://127.0.0.1:$PORT/session/$sid/message" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      -d "$mbody")"
  echo "  POST /message -> $mresp"

  # Wait for session.idle (turn end) or timeout.
  local i
  for i in $(seq 1 "$maxwait"); do
    grep -q '^event: session.idle' "$sse" 2>/dev/null && break
    sleep 1
  done
  kill "$ssepid" 2>/dev/null

  # ---- report ----
  echo "  --- SSE events (in order) ---"
  grep '^event:' "$sse" 2>/dev/null | sed 's/^/    /' || echo "    (none)"
  local has_tool has_plan has_final has_clar
  has_tool=$(grep -qc '^event: tool' "$sse" 2>/dev/null && echo yes || echo no)
  grep -q '^event: tool'    "$sse" 2>/dev/null && has_tool=YES  || has_tool=no
  grep -q '^event: plan'    "$sse" 2>/dev/null && has_plan=YES  || has_plan=no
  grep -q '^event: final'   "$sse" 2>/dev/null && has_final=YES || has_final=no
  grep -q '^event: clarify' "$sse" 2>/dev/null && has_clar=YES  || has_clar=no
  echo "  --- presence: plan=$has_plan tool=$has_tool clarify=$has_clar final=$has_final ---"
  if [ "$has_final" = "YES" ]; then
    echo "  --- final event payload ---"
    grep -A1 '^event: final' "$sse" 2>/dev/null | grep '^data:' | sed 's/^/    /' | head -3
  fi
  echo "  --- serve.log: exceptions / 4xx / warnings ---"
  grep -inE "traceback|runtimeerror|\[400\]|\[401\]|not supported|task exception|error" "$slog" 2>/dev/null \
      | sed 's/^/    /' | head -25 || echo "    (none)"

  stop_server
}

REPO_JSON="$REPO_ROOT"   # used as cwd in session bodies

echo "Repo: $REPO_ROOT"
echo "Outputs in: $OUT"

# S1: THE BUG — mode=plan, default model (config: claude-sonnet-4-5), codex auth.
run_scenario "s1_plan_default" \
  "{\"cwd\":\"$REPO_JSON\"}" \
  '{"mode":"plan","parts":[{"type":"text","text":"Analyze the codebase in depth"}]}' \
  15

# S2: protocol sanity — canned full turn over the real SSE path.
run_scenario "s2_fake_turn" \
  "{\"cwd\":\"$REPO_JSON\"}" \
  '{"mode":"plan","parts":[{"type":"text","text":"Analyze the codebase in depth"}]}' \
  10 VOSS_SERVE_FAKE_TURN=1

# S3: edit mode, default model — same model bug fires regardless of mode.
run_scenario "s3_edit_default" \
  "{\"cwd\":\"$REPO_JSON\"}" \
  '{"mode":"edit","parts":[{"type":"text","text":"list the files in the repo root"}]}' \
  15

# S4: edit mode w/ a WORKING model (gpt-5.5) — does the loop EVER emit a tool?
#     Isolates hypothesis 3 (mode short-circuit) from the model-mismatch bug.
run_scenario "s4_edit_gpt55" \
  "{\"cwd\":\"$REPO_JSON\",\"model\":\"gpt-5.5\"}" \
  '{"mode":"edit","parts":[{"type":"text","text":"list the files in the repo root"}]}' \
  60

# S5: plan mode w/ gpt-5.5 — does the real task now yield plan+tools+final?
#     Isolates hypothesis 2 (structured output) from the model bug.
run_scenario "s5_plan_gpt55" \
  "{\"cwd\":\"$REPO_JSON\",\"model\":\"gpt-5.5\"}" \
  '{"mode":"plan","parts":[{"type":"text","text":"Analyze the codebase in depth"}]}' \
  90

echo
echo "============================================================"
echo "DONE. Raw evidence: $OUT/*_serve.log  and  $OUT/*_sse.log"
echo "============================================================"
