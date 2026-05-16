---
phase: T3-network-surface
plan: 04
type: execute
wave: 2
depends_on: [T3-01, T3-02]
files_modified:
  - voss/harness/rate_limit.py
  - voss/harness/config.py
  - tests/harness/test_rate_limit.py
autonomous: true
requirements: [NET-07]
must_haves:
  truths:
    - "voss/harness/rate_limit.py exists as a pure-stdlib module exporting TokenBucket dataclass and AcquireResult"
    - "TokenBucket(rate_per_min, burst) constructor initializes _tokens = burst and _last = time.monotonic() at __post_init__"
    - "TokenBucket.acquire() returns (True, 0.0) when a token is available and decrements _tokens by 1.0"
    - "TokenBucket.acquire() returns (False, retry_after_s) when _tokens < 1.0 with retry_after_s computed as (1.0 - _tokens) / (rate_per_min / 60.0)"
    - "Token replenishment scales with elapsed wall time on each acquire() call: refill = elapsed * (rate_per_min / 60.0); _tokens capped at burst"
    - "voss/harness/config.py adds _NET_RATE_BLOCK regex with ESCAPED dot (r'^\\[net\\.rate_limits\\][^\\[]*') and a get_net_rate_limits() loader returning dict[str, dict]"
    - "get_net_rate_limits() parses both string form (web_fetch = \"60/min\") and table form (web_fetch = {rate = 60, burst = 120}) into a canonical dict {tool_name: {rate: int, burst: int}}"
    - "Bogus values in [net.rate_limits] emit RuntimeWarning + fall back to omitting the key (downstream NetSession uses SPEC defaults)"
    - "All 5 NET-07 acceptance tests pass: bucket exhaustion, replenish via monkeypatched monotonic, TOML string-form override, TOML table-form override, MCP bypass invariant"
  artifacts:
    - path: "voss/harness/rate_limit.py"
      provides: "TokenBucket dataclass with acquire() -> (bool, float); SPEC defaults web_fetch=TokenBucket(30,30) and web_search=TokenBucket(10,10) exported as DEFAULTS dict"
      contains: "class TokenBucket"
    - path: "voss/harness/config.py"
      provides: "_NET_RATE_BLOCK regex + get_net_rate_limits() loader (mirror of get_max_iterations pattern)"
      contains: "def get_net_rate_limits"
    - path: "tests/harness/test_rate_limit.py"
      provides: "5 NET-07 acceptance tests replace T3-01 pytest.skip stubs"
      contains: "def test_bucket_exhaustion"
  key_links:
    - from: "voss/harness/rate_limit.py:TokenBucket.acquire"
      to: "time.monotonic()"
      via: "module-attribute import of time at top; tests monkeypatch voss.harness.rate_limit.time.monotonic for deterministic clock"
      pattern: "time\\.monotonic"
    - from: "voss/harness/config.py:get_net_rate_limits"
      to: "voss/harness/rate_limit.py:DEFAULTS"
      via: "missing key in TOML → caller (NetSession in T3-05) falls back to DEFAULTS[tool_name]; loader returns only what the TOML explicitly declares"
      pattern: "DEFAULTS"
---

<objective>
Land the rate-limiting primitive (NET-07) and the `[net.rate_limits]` TOML config block that overrides SPEC defaults. Pure stdlib `TokenBucket` dataclass with deterministic-clock testability. Config loader extends `voss/harness/config.py` with the regex pattern T3-RESEARCH.md Pitfall 6 specifically calls out (the escaped-dot trap).

Purpose: NET-07 enforces fail-fast on rate-limit exhaustion — agent loops calling `web_fetch` in a tight loop must not block on sleep; instead the tool returns `<error: rate limit: retry after Ns>` and the agent observes it in the next turn. The bucket primitive is consumed by T3-05 (NetSession.acquire) at every web_fetch / web_search entry. MCP tools intentionally bypass (D-16 + NET-07e). This plan is Wave 2 (depends on T3-02 for the `voss/harness/config.py` merge order — T3-02 owns `[tools] allow_net`; T3-04 owns `[net.rate_limits]`; sequencing prevents merge conflicts on the same file).

Output: rate_limit.py (~60 lines including docstring); config.py extension (~30 lines); 5 NET-07 acceptance tests un-skipped.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T3-network-surface/T3-SPEC.md
@.planning/phases/T3-network-surface/T3-CONTEXT.md
@.planning/phases/T3-network-surface/T3-RESEARCH.md
@.planning/phases/T3-network-surface/T3-PATTERNS.md
@.planning/phases/T3-network-surface/T3-02-PLAN.md
@voss/harness/config.py
@voss/harness/telemetry.py
</context>

<interfaces>
TokenBucket dataclass spec (from T3-RESEARCH.md Pattern 5):

```
@dataclass
class TokenBucket:
    rate_per_min: int
    burst: int
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
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

`AcquireResult` is structurally `tuple[bool, float]` per RESEARCH; SPEC NET-07's NetSession.acquire(tool_name) wrapper (in T3-05) is the higher-level surface. T3-04 ships the primitive; T3-05 wraps it. Optionally add a thin `@dataclass class AcquireResult: ok: bool; retry_after_s: float` if the tuple shape gets unwieldy at NetSession callsites — pick tuple for T3-04 (matches RESEARCH Pattern 5 verbatim).

SPEC defaults: `web_fetch = TokenBucket(rate_per_min=30, burst=30)`, `web_search = TokenBucket(10, 10)`. Export as a module-level dict:
```
DEFAULTS: dict[str, TokenBucket] = {}  # filled lazily by factory to avoid module-import-time monotonic capture
def make_default_bucket(tool_name: str) -> TokenBucket: ...
```
Lazy factory matters: if DEFAULTS is initialized at module import time, the _last timestamp is captured then — test_bucket_exhaustion would see all-tokens-already-replenished by the time it runs. Lazy factory (called at NetSession construction in T3-05) ensures each NetSession instance gets fresh buckets per RESEARCH Pitfall 7.

PITFALL 6 from T3-RESEARCH (load-bearing): `[net.rate_limits]` regex MUST escape the dot: `r"^\[net\.rate_limits\][^\[]*"`. T3-PATTERNS confirms (line 440). An unescaped regex matches `[netXrate_limits]` etc. Test the regex against a fixture string before relying on it.

TOML formats to support:
- String form: `web_fetch = "60/min"` — the existing _KV regex (matches double-quoted strings) catches this; parse the value as `r"^(\d+)/min$"` and treat burst = rate when only rate is specified.
- Table form: `web_fetch = { rate = 60, burst = 120 }` — needs a parallel regex `_KV_RATE_TABLE = re.compile(r'^\s*(\w+)\s*=\s*\{([^}]+)\}', re.MULTILINE)` and a sub-parser for `rate = N, burst = M` inside the braces.

Bogus value handling: if a value parses as neither form, emit `RuntimeWarning(f'[net.rate_limits] {tool}={raw!r} is not a valid rate spec; falling back to SPEC default')` and omit the key from the returned dict (so the caller falls back to DEFAULTS).

Test framework: pyproject pytest-asyncio mode = "auto", so no async needed. Use monkeypatch to patch `voss.harness.rate_limit.time.monotonic` per RESEARCH Pitfall 7 + Assumptions Log A3. Per-test fresh-bucket fixture (function scope) ensures order independence.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create voss/harness/rate_limit.py with TokenBucket + DEFAULTS factory + 2 unit tests</name>
  <files>voss/harness/rate_limit.py, tests/harness/test_rate_limit.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-07 — full text including 30/min and 10/min defaults; MCP unlimited)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-16 — bucket registry; per-session reset)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 5 — TokenBucket complete shape; Common Pitfall 7 — per-session reset; Assumptions Log A3 — monotonic monkeypatch)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/rate_limit.py" — analog to telemetry.py stdlib-only shape)
    - voss/harness/telemetry.py (top 20 lines — module docstring + stdlib import pattern to mirror)
    - tests/harness/test_rate_limit.py (T3-01 scaffold — 5 pytest.skip stubs; this task replaces 2 of them — test_bucket_exhaustion and test_replenish)
  </read_first>
  <action>
    Create voss/harness/rate_limit.py. Top of file:
    - `"""Per-tool token-bucket rate limiting. Pure stdlib. T3-04 / NET-07. Tests monkeypatch voss.harness.rate_limit.time.monotonic for deterministic clocks (RESEARCH Pitfall 7). NetSession owns the per-tool registry; this module owns the primitive only."""`
    - `from __future__ import annotations`
    - `import time` (module-level — tests monkeypatch the attribute on the module, not via time.monotonic global)
    - `from dataclasses import dataclass, field`
    - `import warnings`

    Define `@dataclass class TokenBucket` with fields exactly per the interfaces block above (rate_per_min, burst, _tokens=field(init=False), _last=field(init=False)). __post_init__ initializes _tokens = float(burst) and _last = time.monotonic(). acquire() implements the math per RESEARCH Pattern 5 verbatim:
    - now = time.monotonic()
    - elapsed = now - self._last
    - self._last = now
    - self._tokens = min(float(self.burst), self._tokens + elapsed * (self.rate_per_min / 60.0))
    - if self._tokens >= 1.0: self._tokens -= 1.0; return True, 0.0
    - retry_after = (1.0 - self._tokens) / (self.rate_per_min / 60.0)
    - return False, retry_after

    Edge case: if rate_per_min <= 0, raise ValueError in __post_init__ with message "rate_per_min must be positive". Same for burst.

    Add SPEC defaults as a module-level dict-of-callables (lazy):
    ```
    DEFAULT_SPECS: dict[str, tuple[int, int]] = {
        "web_fetch": (30, 30),     # NET-07 SPEC
        "web_search": (10, 10),    # NET-07 SPEC
    }

    def make_default_bucket(tool_name: str) -> TokenBucket:
        """Construct a fresh TokenBucket with SPEC default rate/burst for tool_name.
        Returns a NEW bucket every call (each NetSession owns its own bucket per
        RESEARCH Pitfall 7). KeyError if tool_name is unknown — callers (T3-05's
        NetSession constructor) must enumerate the keys they care about."""
        rate, burst = DEFAULT_SPECS[tool_name]
        return TokenBucket(rate_per_min=rate, burst=burst)
    ```

    Edit tests/harness/test_rate_limit.py:
    - Remove pytest.skip from test_bucket_exhaustion and test_replenish (leave the other 3 stubs in place — Task 2 of THIS plan handles test_toml_override_string / test_toml_override_table; test_mcp_bypasses_bucket stays skipped for T3-05 to un-skip when NetSession.acquire is wired).
    - Imports: `import time; import pytest; from voss.harness.rate_limit import TokenBucket, make_default_bucket, DEFAULT_SPECS`
    - `test_bucket_exhaustion(monkeypatch)`: monkeypatch clock — `clock = [0.0]; monkeypatch.setattr('voss.harness.rate_limit.time.monotonic', lambda: clock[0])`. Construct `bucket = TokenBucket(rate_per_min=60, burst=60)`. Call `acquire()` 60 times in a tight Python loop (clock unchanged at 0.0). Assert each of the first 60 calls returns (True, 0.0). On call 61, assert returns (False, retry_after) where retry_after > 0 and `pytest.approx(1.0, abs=0.05)` (one token at 60/min = 1 sec).
    - `test_replenish(monkeypatch)`: same clock setup. Construct `bucket = TokenBucket(rate_per_min=60, burst=60)`. Drain bucket via 60 calls; assert call 61 returns (False, ...). Advance clock: `clock[0] += 1.0`. Call acquire(); assert (True, 0.0). Advance clock by 30.0; call acquire 30 more times (within burst cap); assert all succeed; on the 31st within-burst call assert (False, ...) — proves burst cap holds.
    - SPEC default assertions: `assert DEFAULT_SPECS == {"web_fetch": (30, 30), "web_search": (10, 10)}` (one-line guard test — call it test_spec_defaults).
    - Factory assertion: `b1 = make_default_bucket("web_fetch"); b2 = make_default_bucket("web_fetch"); assert b1 is not b2` (proves new instances per call per Pitfall 7). Add as one-line guard test_factory_isolation.
    - Unknown tool: `with pytest.raises(KeyError): make_default_bucket("unknown_tool")` — one-line guard.
    - Validation: `with pytest.raises(ValueError): TokenBucket(rate_per_min=0, burst=10)` — one-line guard.

    Total tests after Task 1: 6 tests (2 NET-07 acceptance + 4 micro guards). Task 2 adds 2 more (toml override variants). test_mcp_bypasses_bucket stays skipped for T3-05.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_rate_limit.py -x -q -k "bucket_exhaustion or replenish or spec_defaults or factory_isolation or KeyError or ValueError" 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^class TokenBucket" voss/harness/rate_limit.py` returns 1 match
    - source assertion: `grep -nE "DEFAULT_SPECS\s*=" voss/harness/rate_limit.py` returns 1 match
    - source assertion: `grep -nE "def make_default_bucket" voss/harness/rate_limit.py` returns 1 match
    - source assertion: `grep -nE "import time" voss/harness/rate_limit.py` returns 1 match (module-level import, not `from time import monotonic` — the test monkeypatch path needs `voss.harness.rate_limit.time.monotonic`)
    - source assertion: `grep -E "min\(float\(self\.burst\)" voss/harness/rate_limit.py | wc -l` returns 1 (burst-cap math present)
    - stdlib-only: `grep -nE "^(import|from)" voss/harness/rate_limit.py | grep -vE "from __future__|import (time|warnings)|from dataclasses" | wc -l` returns 0 (no non-stdlib imports)
    - default values: `python -c "from voss.harness.rate_limit import DEFAULT_SPECS; assert DEFAULT_SPECS == {'web_fetch': (30,30), 'web_search': (10,10)}; print('OK')"` prints OK
    - behavior: test_bucket_exhaustion and test_replenish pass + 4 guard tests pass (6 tests total in this Task)
    - regression: `uv run pytest tests/harness/ -k "lifecycle or rate_limit" -x -q` exits 0 (T3-01 tests unaffected)
  </acceptance_criteria>
  <done>rate_limit.py exports TokenBucket + DEFAULT_SPECS + make_default_bucket; pure stdlib; deterministic-clock-testable; 2 NET-07 acceptance tests (bucket_exhaustion + replenish) green + 4 micro guards; per-instance isolation per Pitfall 7 enforced via factory; KeyError on unknown tool; ValueError on invalid rate/burst.</done>
</task>

<task type="auto">
  <name>Task 2: Add [net.rate_limits] TOML parser to voss/harness/config.py + 2 NET-07 TOML tests</name>
  <files>voss/harness/config.py, tests/harness/test_rate_limit.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-07 acceptance c + d — TOML string form and table form)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-16 — config override per-`[net.rate_limits]`)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/config.py (extend)" — _NET_RATE_BLOCK regex with ESCAPED dot pitfall)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Common Pitfall 6 — escaped-dot trap)
    - voss/harness/config.py (entire file as it stands AFTER T3-02 — `grep -n "_TOOLS_BLOCK\|_AGENT_BLOCK\|_HARNESS_BLOCK" voss/harness/config.py` to confirm T3-02 merged cleanly)
    - tests/harness/test_rate_limit.py (after Task 1 of this plan — 3 stubs still skipped: test_toml_override_string, test_toml_override_table, test_mcp_bypasses_bucket)
    - .planning/phases/T3-network-surface/T3-02-PLAN.md (loader pattern for booleans — mirror for rate specs)
  </read_first>
  <action>
    Edit voss/harness/config.py:
    - After the existing _TOOLS_BLOCK regex (T3-02 added), add:
      ```
      # T3-04: PITFALL — escape the dot. r"^\[net.rate_limits\]" matches [netXrate_limits] which is wrong.
      _NET_RATE_BLOCK = re.compile(r"^\[net\.rate_limits\][^\[]*", re.MULTILINE)
      # String form: web_fetch = "60/min"
      _RATE_STR = re.compile(r'^\s*(\w+)\s*=\s*"(\d+)/min"\s*$', re.MULTILINE)
      # Table form: web_fetch = { rate = 60, burst = 120 }   (one-line braces; nested braces not supported)
      _RATE_TABLE = re.compile(r'^\s*(\w+)\s*=\s*\{([^}]+)\}\s*$', re.MULTILINE)
      # Inside-braces kv: rate = 60 and burst = 120
      _RATE_TABLE_KV = re.compile(r'\s*(rate|burst)\s*=\s*(\d+)\s*,?')
      ```
    - Add a helper `def _parse_net_rate_limits_section(text: str) -> dict[str, dict[str, int]]:` returning `{tool_name: {"rate": int, "burst": int}}`. Implementation:
      - m = _NET_RATE_BLOCK.search(text). If not m: return {}.
      - block = m.group(0).
      - result: dict[str, dict[str, int]] = {}.
      - For each match of _RATE_STR.findall(block): name, rate = match; result[name] = {"rate": int(rate), "burst": int(rate)} (string form: burst defaults to rate).
      - For each match of _RATE_TABLE.findall(block): name, inner = match; kv_pairs = dict(_RATE_TABLE_KV.findall(inner)); try: rate = int(kv_pairs["rate"]); burst = int(kv_pairs.get("burst", rate)); result[name] = {"rate": rate, "burst": burst}; except (KeyError, ValueError): warnings.warn(f'[net.rate_limits] {name} table form invalid: {inner!r}', RuntimeWarning, stacklevel=2); continue.
      - Return result.
    - Add `def get_net_rate_limits() -> dict[str, dict[str, int]]:` mirroring get_max_iterations / get_allow_net structure:
      - p = config_path(); if not p.exists(): return {}.
      - try: text = p.read_text(); except OSError: return {}.
      - return _parse_net_rate_limits_section(text).

    Edit tests/harness/test_rate_limit.py:
    - Remove pytest.skip from test_toml_override_string and test_toml_override_table.
    - Add imports: `from voss.harness.config import get_net_rate_limits, _parse_net_rate_limits_section` plus the existing xdg fixture pattern from tests/harness/test_agent_config.py.
    - `test_toml_override_string(xdg)`: write `[net.rate_limits]\nweb_fetch = "60/min"\nweb_search = "5/min"\n` to xdg/voss/config.toml. Call `result = get_net_rate_limits()`. Assert `result == {"web_fetch": {"rate": 60, "burst": 60}, "web_search": {"rate": 5, "burst": 5}}`.
    - `test_toml_override_table(xdg)`: write `[net.rate_limits]\nweb_fetch = { rate = 60, burst = 120 }\nweb_search = { rate = 10, burst = 20 }\n`. Assert `result == {"web_fetch": {"rate": 60, "burst": 120}, "web_search": {"rate": 10, "burst": 20}}`.
    - Bonus test_toml_dot_regex_correctness: write a config.toml with `[net.rate_limits]\nweb_fetch = "60/min"\n\n[netXrate_limits]\nfoo = "bad"\n` (an adjacent bogus section that would match an UN-escaped regex). Assert `get_net_rate_limits() == {"web_fetch": {"rate": 60, "burst": 60}}` and the bogus block is ignored. This is the load-bearing Pitfall 6 proof.
    - Bonus test_toml_warns_on_bad_table: write `[net.rate_limits]\nweb_fetch = { rate = oops }\n`. Use `pytest.warns(RuntimeWarning, match="invalid")`; assert result excludes web_fetch.

    Confirm test_mcp_bypasses_bucket REMAINS skipped (its pytest.skip stays — T3-05 un-skips when NetSession.acquire and MCP-bypass are wired).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_rate_limit.py -x -q -k "toml_override or dot_regex or warns_on_bad" 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "_NET_RATE_BLOCK\s*=" voss/harness/config.py` returns 1 match
    - escaped-dot assertion: `grep -nE "_NET_RATE_BLOCK = re\.compile\(r\"\^\\\\\[net\\\\\.rate_limits\\\\\]" voss/harness/config.py` returns 1 match (the regex literal contains the escaped-dot sequence; if the grep is finicky use a simpler grep `grep -F 'net\.rate_limits' voss/harness/config.py` and expect at least 1 hit)
    - functional regex assertion: `python -c "from voss.harness.config import _NET_RATE_BLOCK; assert _NET_RATE_BLOCK.search('[net.rate_limits]\nweb_fetch = \"60/min\"'); assert not _NET_RATE_BLOCK.search('[netXrate_limits]\nfoo = 1'); print('OK')"` prints OK
    - loader assertion: `grep -nE "def get_net_rate_limits|def _parse_net_rate_limits_section" voss/harness/config.py | wc -l` returns 2
    - behavior: test_toml_override_string + test_toml_override_table + test_toml_dot_regex_correctness + test_toml_warns_on_bad_table all pass (4 tests)
    - mcp_bypass remains skipped: `grep -A2 "def test_mcp_bypasses_bucket" tests/harness/test_rate_limit.py | grep -c "pytest.skip"` returns 1 (still skipped)
    - skip count delta: `grep -c "pytest.skip" tests/harness/test_rate_limit.py` returns 1 (only test_mcp_bypasses_bucket remains skipped)
    - regression: `uv run pytest tests/harness/test_rate_limit.py tests/harness/test_agent_config.py tests/harness/test_allow_net.py -x -q` exits 0
  </acceptance_criteria>
  <done>voss/harness/config.py exports _NET_RATE_BLOCK (escaped-dot regex) + _parse_net_rate_limits_section + get_net_rate_limits; both TOML string form ("60/min") and table form ({rate=N, burst=M}) parse to canonical dict; Pitfall 6 escaped-dot trap proved via adjacent-bogus-section test; bogus table content warns + omits the key; 4 acceptance tests green; test_mcp_bypasses_bucket left skipped for T3-05 wave to un-skip.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent issuing repeated network calls → outbound HTTP rate | TokenBucket is the single guard against runaway agent loops exhausting downstream backend quotas (Brave: 1 q/s tier-free; arbitrary fetches: webmaster goodwill). Fail-fast (no in-tool sleep) keeps the agent loop responsive. |
| User TOML edits → in-process bucket parameters | `[net.rate_limits]` block is user-authored; malformed table content must not crash bootstrap. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-03 | DoS (outbound) | Unbounded web_fetch / web_search calls flood downstream | mitigate | TokenBucket(30, 30) and (10, 10) defaults enforce the SPEC limits; failed acquire returns fail-fast retry-after envelope; NET-07a/b prove exhaustion + replenish |
| T-T3-04-01 | DoS | bogus `[net.rate_limits]` syntax crashes cli.py boot | mitigate | get_net_rate_limits wraps all parse in OSError/regex guards; bogus rows emit RuntimeWarning + are silently skipped; rate_limit.py defaults still apply for unmatched tools |
| T-T3-04-02 | Tampering | regex un-escaped dot lets `[netXrate_limits]` poison the bucket config | mitigate | _NET_RATE_BLOCK uses `r"\\[net\\.rate_limits\\]"` (escaped dot); test_toml_dot_regex_correctness proves the adjacent-bogus-section is rejected |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_rate_limit.py -x -q` shows 4 of 5 NET-07 cases passing + 4 micro guards passing; test_mcp_bypasses_bucket explicitly skipped with reason "pending T3-05"
- `python -c "from voss.harness.rate_limit import TokenBucket, DEFAULT_SPECS, make_default_bucket; b = make_default_bucket('web_fetch'); print(b.rate_per_min, b.burst)"` prints `30 30`
- `python -c "from voss.harness.config import get_net_rate_limits; print(get_net_rate_limits())"` prints `{}` (no TOML at default location)
- `grep -F 'net\.rate_limits' voss/harness/config.py` returns >= 1 hit (escaped-dot present)
</verification>

<success_criteria>
- TokenBucket primitive ships with deterministic-clock-testable acquire()
- DEFAULT_SPECS dict locks SPEC values web_fetch=30/30, web_search=10/10
- make_default_bucket factory produces fresh instances (Pitfall 7 satisfied)
- _NET_RATE_BLOCK regex escapes the dot (Pitfall 6 satisfied)
- TOML string form "N/min" and table form {rate=N, burst=M} both parse
- Bogus table content emits RuntimeWarning + falls back silently
- 4 NET-07 acceptance tests pass; test_mcp_bypasses_bucket awaits T3-05
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-04-SUMMARY.md` when done: report TokenBucket class signature + DEFAULT_SPECS contents + make_default_bucket factory; _NET_RATE_BLOCK literal text with the escaped dot called out; pytest output for the 8 tests this plan runs (6 unit + 2 TOML + 2 bonus regex/warning); note that NetSession in T3-05 imports `make_default_bucket` to populate its per-instance registry.
</output>
