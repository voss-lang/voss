---
phase: T3-network-surface
plan: 04
status: complete
---

# T3-04 Summary — TokenBucket + [net.rate_limits] loader

## TokenBucket primitive

`voss/harness/rate_limit.py:20` — `@dataclass class TokenBucket`. Stdlib only.

```python
@dataclass
class TokenBucket:
    rate_per_min: int
    burst: int
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        if self.rate_per_min <= 0:
            raise ValueError("rate_per_min must be positive")
        if self.burst <= 0:
            raise ValueError("burst must be positive")
        self._tokens = float(self.burst)
        self._last = time.monotonic()

    def acquire(self) -> tuple[bool, float]:
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(float(self.burst), self._tokens + elapsed * (self.rate_per_min / 60.0))
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True, 0.0
        retry_after = (1.0 - self._tokens) / (self.rate_per_min / 60.0)
        return False, retry_after
```

`time` is module-level imported (line 14) so tests monkeypatch `voss.harness.rate_limit.time.monotonic` per RESEARCH Pitfall 7.

## DEFAULT_SPECS + factory

`voss/harness/rate_limit.py:46–49`:

```python
DEFAULT_SPECS = {
    "web_fetch": (30, 30),
    "web_search": (10, 10),
}
```

`voss/harness/rate_limit.py:55` — `make_default_bucket(tool_name)` returns a fresh `TokenBucket` per call (RESEARCH Pitfall 7: NetSession owns per-instance buckets, never module-level shared state). `KeyError` on unknown tool — callers enumerate the keys they care about.

## `_NET_RATE_BLOCK` regex (Pitfall 6)

`voss/harness/config.py:31`:

```python
_NET_RATE_BLOCK = re.compile(r"^\[net\.rate_limits\][^\[]*", re.MULTILINE)
```

The escaped dot (`\.`) is load-bearing. Without it the regex would also match `[netXrate_limits]` (the `.` in a regex is any-char). `test_toml_dot_regex_correctness` proves the adjacent-bogus-section rejection.

Companion regexes (lines 33–39):
- `_RATE_STR` — quoted string form `web_fetch = "60/min"`.
- `_RATE_TABLE` — inline table form `web_fetch = { rate = N, burst = M }`.
- `_RATE_TABLE_KV` — inside-braces kv parser (rate / burst only).

`_parse_net_rate_limits_section` + `get_net_rate_limits` mirror the `get_max_iterations` / `get_allow_net` pattern: missing file / section → `{}`; bogus rows emit `RuntimeWarning` and are dropped so the caller falls back to `DEFAULT_SPECS`.

## pytest output

```
$ uv run pytest tests/harness/test_rate_limit.py -x -q
..........s                                                              [100%]
10 passed, 1 skipped
```

| Test | Coverage |
|---|---|
| `test_bucket_exhaustion` | NET-07a — burst drains, retry_after ≈ 1 s at 60/min |
| `test_replenish` | NET-07b — wall-clock refill scales with elapsed; burst caps |
| `test_spec_defaults` | guard — `DEFAULT_SPECS` locked to (30,30) / (10,10) |
| `test_factory_isolation` | RESEARCH Pitfall 7 — `b1 is not b2` |
| `test_factory_unknown_tool_raises` | guard — `KeyError` on unknown tool |
| `test_invalid_rate_raises` | guard — `ValueError` on rate=0 / burst=0 |
| `test_toml_override_string` | NET-07c — `web_fetch = "60/min"` → `{rate:60, burst:60}` |
| `test_toml_override_table` | NET-07d — inline table form parses both `rate` and `burst` |
| `test_toml_dot_regex_correctness` | Pitfall 6 — `[netXrate_limits]` adjacent block ignored |
| `test_toml_warns_on_bad_table` | bogus table content emits `RuntimeWarning`; key omitted |
| `test_mcp_bypasses_bucket` | **skipped — pending T3-05** (NetSession.acquire + MCP-bypass wire) |

Regression (T3 bundle + telemetry/permissions): `73 passed, 1 skipped`.

## Downstream contract for T3-05

`voss/harness/net.py` (created in T3-05) constructs `NetSession` and populates its per-instance bucket registry:

```python
from voss.harness.rate_limit import DEFAULT_SPECS, make_default_bucket
from voss.harness.config import get_net_rate_limits

class NetSession:
    def __init__(self) -> None:
        overrides = get_net_rate_limits()
        self._buckets = {}
        for name in DEFAULT_SPECS:
            spec = overrides.get(name)
            if spec is None:
                self._buckets[name] = make_default_bucket(name)
            else:
                self._buckets[name] = TokenBucket(rate_per_min=spec["rate"], burst=spec["burst"])
```

T3-05 also un-skips `test_mcp_bypasses_bucket` once `NetSession.acquire(tool_name)` exists, asserting that MCP tools never route through the bucket registry (D-16 + NET-07e). The pytest.skip message points there explicitly.
