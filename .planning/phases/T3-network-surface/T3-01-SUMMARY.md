---
phase: T3-network-surface
plan: 01
status: complete
---

# T3-01 Summary — Wave 0 scaffolding

## voss/harness/lifecycle.py — public API

- `register_subprocess(proc: asyncio.subprocess.Process) -> None`
- `register_session(session: object) -> None` — duck-typed contract: object exposing `async def aclose(self) -> None`. No import of `voss.harness.net` (greenfield — no predecessor per T3-RESEARCH.md / T3-PATTERNS.md).
- `async def reap_all() -> None` — per subprocess: `terminate()` → `asyncio.wait_for(proc.wait(), timeout=5.0)` → on TimeoutError `proc.kill()` + `await proc.wait()`. Per session: `await session.aclose()` wrapped in `except BaseException` so a single bad aclose never aborts the reap loop. Both registries cleared after the sweep.
- `def reset_for_tests() -> None` — test-only helper.
- `_atexit_hook()` registered via `atexit.register` at module import. Tries `asyncio.run(reap_all())` first; on `RuntimeError` (running loop) falls back to `asyncio.new_event_loop().run_until_complete(reap_all())`. All branches wrapped in try/except — atexit must never raise.

## SIGKILL fallback wall time

`test_register_subprocess_sigkill_fallback` spawns `python -u -c "<install SIG_IGN handler; print('ready'); sleep 60>"`, waits for the `ready` handshake (no race), registers the proc, runs `reap_all()`, and asserts elapsed ∈ [4.5, 6.5] s. Observed: well within the band (test passes, no flake). The handshake step was required — without it `terminate()` fires before the child installs SIG_IGN and the child dies on the first signal in ≈0 s instead of the 5 s deadline.

## 32 placeholder test ids by file

- `tests/harness/test_web_fetch.py` (5, pending T3-05): `test_registration`, `test_allow_net_gate`, `test_truncation`, `test_timeout_clamp`, `test_http_errors`
- `tests/harness/test_web_search.py` (4, pending T3-06): `test_no_key`, `test_mocked_results`, `test_count_clamp`, `test_429_handling`
- `tests/harness/test_allow_net.py` (6, pending T3-02): `test_default_false`, `test_toml_true`, `test_cli_override`, `test_cli_explicit_false`, `test_gate_before_prompt`, `test_zero_socket_invariant`
- `tests/harness/test_net_telemetry.py` (5, pending T3-03): `test_redact_url_strips`, `test_redact_url_noop`, `test_event_emission`, `test_mcp_events`, `test_run_record_roundtrip`
- `tests/harness/test_rate_limit.py` (5, pending T3-04): `test_bucket_exhaustion`, `test_replenish`, `test_toml_override_string`, `test_toml_override_table`, `test_mcp_bypasses_bucket`
- `tests/harness/mcp/test_mcp_config.py` (1, pending T3-07): `test_loader_parses_fixture`
- `tests/harness/mcp/test_mcp_client.py` (2, pending T3-07): `test_lazy_launch`, `test_sigterm_reap`
- `tests/harness/mcp/test_mcp_scope.py` (4, pending T3-07): `test_default_plan_scope`, `test_edit_scope`, `test_scope_denial`, `test_auto_does_not_override_scope`

Total = 5+4+6+5+5+1+2+4 = 32. Pytest --collect-only confirms 32 ids; full run reports `32 skipped`. Every function body is exactly `pytest.skip("pending T3-NN — placeholder created by T3-01")`.

`tests/harness/mcp/__init__.py` created (zero bytes) so pytest treats the directory as a package.

## Open questions resolved

- **A4 (pyyaml in main deps):** `grep -c pyyaml pyproject.toml` = 1 (line 21, `"pyyaml>=6.0"` in `[project].dependencies`). Resolved — no action required.

## Downstream contract

T3-02..T3-07 plans replace `pytest.skip(...)` calls with real bodies. Test function names are load-bearing — downstream `<automated>` blocks cite `pytest tests/harness/<file>.py::<name>` and rely on these exact ids collecting without ImportError. The lifecycle module is import-safe for every downstream consumer: nothing in T3-05/06's NetSession or T3-07's MCP client needs to exist yet.

## Verification artifacts

- `uv run pytest tests/harness/test_lifecycle.py -x -q` → 5 passed
- `uv run pytest tests/harness/test_web_fetch.py … tests/harness/mcp/ -q` → 32 skipped
- `uv run pytest tests/harness/ --collect-only -q` → exit 0, no ImportError
