# V15 Spike: `voss serve` sidecar + handshake — PROVEN

**Date:** 2026-06-09 · **Verdict:** keystone de-risked, no blockers.

## What was proven

`crates/voss-app-core/src/sidecar.rs` (production home, not throwaway) + gated integration test (`VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core spike_spawn`):

1. **Spawn** `python -m voss.cli serve --port 0` as an app-owned child from the Tauri-side crate (tokio, `kill_on_drop`, stdin-pipe heartbeat).
2. **Handshake**: parsed the one-line `{"v":1,"port":…,"token":…}` from stdout; server log lines do NOT false-parse; `v` ignored (forward-compatible).
3. **Authed request**: raw HTTP/1.1 `GET /session` with `Authorization: Bearer <token>` → **200**.
4. **Auth enforced**: same GET without the header → **401/403** rejected.
5. **Reap**: `shutdown()` kills + waits; `kill -0 <pid>` confirms no orphan.

## Measurements

- **Warm boot → handshake: ~1.5s** on this machine (dev venv, pycs compiled). The 60s budget + `LITELLM_LOCAL_MODEL_COST_MAP=true` (V13.2-06 findings) are kept for cold-start safety — both already encoded in the module.
- Zero new dependencies: runtime uses existing tokio/serde/anyhow; the test's HTTP client is a raw `TcpStream`.

## Ported knowledge (from `crates/voss-sdk/src/supervisor.rs`)

- `LITELLM_LOCAL_MODEL_COST_MAP=true` (litellm fetches its cost map over the network at import otherwise; case-sensitive "true", `"1"` does NOT work) + `PYDANTIC_DISABLE_PLUGINS=1`.
- 60s handshake timeout (cold `.pyc` compile ~45s; warm ~1.5–15s).
- stderr drained continuously (full pipe blocks the server) and surfaced in the timeout error; stdout drained post-handshake.
- stdin held open as heartbeat — EOF terminates the server if the app dies.
- Interpreter resolution: `VOSS_PYTHON` > repo `.venv/bin/python` > `python3`.

## What remains for the phase (now plumbing, not risk)

1. **Tauri command** `start_voss_serve(cwd)` in src-tauri: call `spawn_voss_serve`, hold `VossServe` in managed state (one per workspace, reuse-if-alive), return `ServeHandshake` (already `Serialize`); kill on app exit (`kill_on_drop` covers crash paths).
2. **Frontend**: `invoke('start_voss_serve', {cwd})` → construct the V13.1 TS client → plug the V14 sockets (RunCommandBar `client`, drawer `followUpClient`, `sseClient` stream).
3. Interpreter resolution UX for non-dev installs (bundled python vs PATH `voss`) — a SPEC question, not a spike question.

## Spec inputs

- The sidecar is per-`cwd` (server writes `.voss/sessions` under its cwd) — workspace switch ⇒ per-workspace server instance or single-server-with-cwd question for SPEC.
- Boot is fast enough warm (~1.5s) to spawn lazily on first native-run intent rather than at app launch; cold-start (rare) may want a "starting Voss…" affordance.
