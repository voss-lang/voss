---
phase: T3-network-surface
plan: 02
status: complete
---

# T3-02 Summary — allow_net gate + CLI flag + NET-05 acceptance

## (a) Exact source line numbers

| Edit | File | Line(s) |
|---|---|---|
| `is_network: bool = False` on `ToolEntry` | `voss/harness/tools.py` | 32 |
| `TYPE_CHECKING` block importing `NetSession` | `voss/harness/tools.py` | 14–15 |
| `make_toolset(cwd, *, renderer=None, net: "NetSession \| None" = None)` | `voss/harness/tools.py` | 72–77 |
| `RuntimeConfig.allow_net: bool = False` | `voss_runtime/_config.py` | 29 |
| `_TOOLS_BLOCK` regex | `voss/harness/config.py` | 27 |
| `_KV_BARE` regex (bare-token unquoted values) | `voss/harness/config.py` | 33 |
| `_parse_tools_section` | `voss/harness/config.py` | 52–67 |
| `load_tools_config` | `voss/harness/config.py` | 94–102 |
| `get_allow_net` | `voss/harness/config.py` | 161–183 |
| `PermissionGate.check` signature `is_network` kwarg | `voss/harness/permissions.py` | 169–180 |
| `PermissionGate._check_impl` signature `is_network` kwarg | `voss/harness/permissions.py` | 187–205 |
| Net-gate insertion (between project-policy and mode-tier) | `voss/harness/permissions.py` | 223–231 |
| Denial envelope `"net disabled: set tools.allow_net = true in harness.toml or pass --allow-net"` | `voss/harness/permissions.py` | 228–230 |
| `--allow-net/--no-allow-net` flag on `do_cmd` | `voss/harness/cli.py` | 992–1004 |
| `do_cmd` body branch (`configure(allow_net=True/False)`) | `voss/harness/cli.py` | 1032–1036 |
| `--allow-net/--no-allow-net` flag on `chat_cmd` | `voss/harness/cli.py` | 1145–1157 |
| `chat_cmd` body branch | `voss/harness/cli.py` | 1180–1184 |
| Bootstrap configure wire-in | `voss/harness/cli.py` | 60–66 |

## (b) cli.py bootstrap `configure()` post-extension

`voss/harness/cli.py` lines 60–66:

```python
from .config import get_allow_net, get_max_iterations, get_max_parallel_reads

configure(
    max_iterations=get_max_iterations(),
    max_parallel_reads=get_max_parallel_reads(),
    allow_net=get_allow_net(),
)
```

The T1-04 / T2-02 bootstrap already existed inside `_bootstrap_runtime_config()` — this plan extended the existing call (and the existing import) rather than adding a new one.

## (c) pytest output — 6 NET-05 tests green

```
$ uv run pytest tests/harness/test_allow_net.py -x -q
......                                                                   [100%]
6 passed
```

Tests, in order:
1. `test_default_false` — NET-05a (no config file → False)
2. `test_toml_true` — NET-05b (`[tools] allow_net = true` → True after bootstrap)
3. `test_cli_override` — NET-05c (`--allow-net` recognized by both `do_cmd` and `chat_cmd`; override semantics proved at the configure() level)
4. `test_cli_explicit_false` — NET-05d (both `--allow-net` and `--no-allow-net` recognized; all three CLI cases proved at configure() level; SPEC `--allow-net=false` is the click-idiomatic `--no-allow-net`)
5. `test_gate_before_prompt` — NET-05e (net-gate denies before mode-tier and before the prompt; `_fail_prompt` confirms no prompt fired)
6. `test_zero_socket_invariant` — NET-05f (sentinel counter stays at 0 when gate denies; httpx MockTransport variant deferred to T3-05 per plan note)

Regression: `uv run pytest tests/harness/test_permissions_modes.py tests/harness/test_agent_config.py tests/harness/test_allow_net.py tests/harness/test_lifecycle.py -x -q` → 53 passed. Broader harness run (excluding tools/tui subdirs that depend on external services) → `594 passed, 28 skipped, 1 xfailed`.

## (d) `gate.check(...)` call-site audit

Only one production caller exists in `voss/harness/`:

- `voss/harness/agent.py:1018` — `allowed, why = gate.check(step.name, step.args, is_mutating=entry.is_mutating)`

**T3-05 must update this call to forward the network axis:**

```python
allowed, why = gate.check(
    step.name,
    step.args,
    is_mutating=entry.is_mutating,
    is_network=entry.is_network,
)
```

Until that change lands, network tools registered by T3-05/06/07 will fall through the gate as `is_network=False` (default kwarg) and bypass the allow_net check — relying entirely on the structural test coverage in this phase. T-T3-02-03 in the threat register documents this acceptance: the audit task is T3-05's responsibility.

Test callers of `gate.check(..., is_network=True, ...)` already exist in `tests/harness/test_allow_net.py` (this plan) and exercise the gate directly, so the NET-05f zero-socket invariant remains proven at the gate level even before T3-05 wires the dispatch site.

## Open question A4 (pyyaml)

Already resolved in T3-01-SUMMARY.md. `pyproject.toml:21` contains `"pyyaml>=6.0"`. Not relevant to this plan but noted for closure tracking.

## Regex pitfall note

The plan called for a `_KV_BOOL` regex matching `true|false` only. Implementation widened to `_KV_BARE` (`r"^\s*(\w+)\s*=\s*([^\s\"#]+)\s*$"`) so that bogus values like `allow_net = yes` are captured and surface in the parsed dict — letting `get_allow_net()` emit the required RuntimeWarning rather than silently returning the default. The strict `true|false` form would have left `yes` unmatched and skipped the warn path (NET-05 acceptance d's "bogus warns" sub-case). The change is internal to `_parse_tools_section` and does not affect any other section's parsing.
