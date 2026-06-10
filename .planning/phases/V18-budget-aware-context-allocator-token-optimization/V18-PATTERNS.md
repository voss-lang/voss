# Phase V18: Budget-Aware Context Allocator (Token Optimization) — Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/context_allocator.py` | utility (pure transformer) | transform | `voss/harness/agent.py` `_serialize_iter_for_replay` + `_build_iter_rider` | role-match |
| `voss/harness/agent.py` (modify :713) | controller (agent loop) | event-driven | self — four-line replay loop at :708-716 | self-seam |
| `voss/harness/recorder.py` (add `_append_savings_record`) | utility (I/O writer) | file-I/O | `voss/eval/runner.py` `_append_row` | role-match |
| `voss/harness/config.py` (add `[context]` block) | config | request-response | self — `_parse_agent_section` / `load_agent_config` / `set_max_iterations` | self-seam |
| `voss/harness/cli.py` (add `--no-pack`; extend `_cost`) | controller (CLI) | request-response | self — `do_cmd` flag cluster; `_cost` handler at :881-918 | self-seam |
| `tests/harness/test_context_allocator.py` | test (unit) | transform | `tests/harness/test_agent_loop.py` FakeStreamingProvider + `_done_script` | role-match |
| `tests/harness/test_agent_packing.py` | test (integration) | event-driven | `tests/harness/test_agent_loop.py` full async run_turn harness | exact |
| `tests/harness/test_savings_ledger.py` | test (unit + I/O) | file-I/O | `tests/harness/test_cost_slash.py` + `tests/harness/test_harness_config.py` | role-match |
| `tests/harness/test_packing_eval_gate.py` | test (eval gate) | batch | `voss/eval/runner.py` `run_suite()` + `_append_row` | exact |

---

## Pattern Assignments

### `voss/harness/context_allocator.py` (new pure utility)

**Analogs:** `voss/harness/agent.py:431-458` (`_serialize_iter_for_replay`) and `agent.py:416-428` (`_build_iter_rider`'s digest lines)

**Imports pattern** — copy from `agent.py:1-20` style, stripped to what's needed:
```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
```
No provider import, no I/O import. Pure transform module.

**PackingProfile dataclass** — model after `IterationRecord` in `voss/harness/session.py:100-115` (plain `@dataclass` with typed defaults):
```python
# session.py:99-115 pattern — @dataclass with typed field defaults, no field()
@dataclass
class IterationRecord:
    index: int
    plan: dict = field(default_factory=dict)
    cost_usd: float = 0.0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    # ... additive defaults preserve round-trip
```
Apply the same shape for `PackingProfile`:
```python
@dataclass
class PackingProfile:
    recent_full_k: int = 8
    digest_cutoff_m: int = 20
    high_water: float = 0.80
    low_water: float = 0.60
    enabled: bool = True
```

**Full-tier rendering** — byte-copy from `agent.py:431-458`. This is the "no change to output" tier. The key detail is the `telemetry.redact_tool_args` call at :453 and the 400-char cap at :454-455:
```python
# agent.py:431-458 (VERIFIED)
def _serialize_iter_for_replay(iter_rec) -> tuple[dict, dict]:
    plan_dict = iter_rec.plan or {}
    assistant_content = json.dumps({
        "rationale": plan_dict.get("rationale", ""),
        "steps": plan_dict.get("steps", []) or [],
        "final_when_done": plan_dict.get("final_when_done", ""),
    })
    assistant_msg = {"role": "assistant", "content": assistant_content}

    lines = [f"Tool results for iteration {iter_rec.index}:"]
    for tr in iter_rec.tool_results or []:
        name = tr.get("name", "")
        args = tr.get("args", {}) or {}
        if isinstance(args, dict):
            args = telemetry.redact_tool_args(dict(args))
        args_str = str(args)[:400]
        result_str = str(tr.get("result", ""))[:400]
        lines.append(f"- {name}({args_str}) -> {result_str}")
    user_msg = {"role": "user", "content": "\n".join(lines)}
    return assistant_msg, user_msg
```
The allocator's full tier calls `_serialize_iter_for_replay` directly — no re-implementation.

**Digest-tier rendering** — copy the line format from `agent.py:418-427` (`_build_iter_rider`'s per-iteration lines), which is the existing one-line structural summary the rider already uses:
```python
# agent.py:418-427 (VERIFIED) — the rider digest pattern
for ir in prior_iters:
    plan = ir.plan or {}
    step_count = len(plan.get("steps", []) or [])
    tool_count = len(ir.tool_results or [])
    snippet_src = plan.get("final_when_done") or plan.get("rationale") or ""
    snippet = snippet_src.replace("\n", " ")[:60]
    lines.append(
        f"- Iter {ir.index}: {step_count} steps, {tool_count} tools, {snippet}"
    )
```
For the replay-tail digest tier, emit two messages (assistant + user) rather than a line, keeping the same counts + snippet content.

**Token estimation** — always use `_default_token_count` imported from `agent.py:73-80`. Never implement a second estimator:
```python
# agent.py:73-80 (VERIFIED)
def _default_token_count(text: str, *, model: str) -> int:
    if _litellm is not None:
        try:
            return int(_litellm.token_counter(model=model, text=text))
        except Exception:
            pass
    return max(len(text) // 4, 1)
```
Import it: `from voss.harness.agent import _default_token_count` (or accept it as a callable arg for testability without the import cycle — caller passes it in).

**Stable-region hysteresis** — the allocator carries internal state across calls within one run. Hash the stable region bytes to detect drift (mirrors the VOPT-03 acceptance test requirement):
```python
# Pattern: compute hash of stable serialized pairs for change detection
_stable_hash = hashlib.sha256(
    json.dumps([msg for pair in stable_pairs for msg in pair], sort_keys=True).encode()
).hexdigest()
```

**Eviction pointer extraction** — extract file paths from `tr["args"]` the same way `tools.py` accesses them (structured dict args). Cap at 5 deduplicated pointers per fold block:
```python
# Eviction pointer pattern: read tr["args"]["path"] or tr["args"]["file"]
for tr in iter_rec.tool_results or []:
    args = tr.get("args") or {}
    if isinstance(args, dict):
        path = args.get("path") or args.get("file")
        symbol = args.get("pattern") or args.get("symbol")
        if path:
            pointers.append(f'↻ re-fetch via code_search("{path}")')
        elif symbol:
            pointers.append(f'↻ re-fetch via find_definition("{symbol}")')
# dedup + cap
eviction_block = "\n".join(dict.fromkeys(pointers)[:5])
```

---

### `voss/harness/agent.py` (modify at :708-716)

**Analog:** self — the four-line loop is the insertion seam. The `--no-pack` branch IS the original loop verbatim.

**The current seam** (`agent.py:708-716`, VERIFIED):
```python
messages: list[dict] = [
    {"role": "system", "content": sys_blocks},  # cached static prefix (CACHE-01)
    {"role": "system", "content": rider},
    {"role": "user", "content": user_prompt},
]
for prior in all_iter_records:                  # UNBOUNDED growth
    a_msg, u_msg = _serialize_iter_for_replay(prior)
    messages.append(a_msg)
    messages.append(u_msg)
```

**V18 insertion shape** — wrap the four-line loop in `if/else`; the `else` branch is the original loop bytes verbatim:
```python
messages: list[dict] = [
    {"role": "system", "content": sys_blocks},
    {"role": "system", "content": rider},
    {"role": "user", "content": user_prompt},
]
if packing_enabled and all_iter_records:
    replay_pairs = _context_allocator.pack(
        all_iter_records, packing_budget, packing_profile
    )
    for a_msg, u_msg in replay_pairs:
        messages.append(a_msg)
        messages.append(u_msg)
else:
    for prior in all_iter_records:
        a_msg, u_msg = _serialize_iter_for_replay(prior)
        messages.append(a_msg)
        messages.append(u_msg)
```

**T4 prefix** — `_compose_system_blocks` (`agent.py:363-395`, VERIFIED) is called ONCE before the iteration while-loop. The allocator receives only `all_iter_records`; it never touches `sys_blocks`. The `cache_control: ephemeral` mark lives at the last element of `blocks[-1]`:
```python
# agent.py:390-394 (VERIFIED) — T4 breakpoint; NEVER repacked
if blocks:
    blocks[-1] = {
        **blocks[-1],
        "cache_control": {"type": "ephemeral"},
    }
```

**`all_iter_records` population** (`agent.py:992`, VERIFIED) — happens at the END of each iteration. At the top of iteration N, `all_iter_records` contains iterations 0..N-1:
```python
all_iter_records.append(rec._iterations[-1])  # agent.py:992
```

**Budget-halt** (`agent.py:1007-1012`, VERIFIED) — unchanged; packing reduces token consumption rate but the halt condition is the same:
```python
if (ctx.token_budget and ctx.tokens_used >= ctx.token_budget):
    exit_reason = "budget"
    break
```

---

### `voss/harness/recorder.py` (add `_append_savings_record`)

**Analog:** `voss/eval/runner.py:100-103` (`_append_row`) — the existing JSONL append pattern:
```python
# runner.py:100-103 (VERIFIED)
def _append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
```
Copy this exactly for `_append_savings_record`. The ledger path convention follows `session.py:57-58`:
```python
# session.py:57-58 (VERIFIED)
def _sessions_dir(cwd: Path) -> Path:
    return (cwd / ".voss" / "sessions").resolve()
```
Ledger path = `_sessions_dir(cwd) / session_id / "token-savings.jsonl"` (subdirectory of the sessions dir, not alongside the flat `<id>.json` session file).

**OSC surface for savings line** — reuse `_emit_context_osc` (`recorder.py:130-140`, VERIFIED) by adding a `savings` key to its free-form dict payload. The function signature is unchanged; the payload gains an optional field:
```python
# recorder.py:130-140 (VERIFIED) — shape unchanged, additive payload field
def _emit_context_osc(payload: dict) -> None:
    if not sys.stdout.isatty():
        return
    json_str = json.dumps(payload, separators=(",", ":"))
    sys.stdout.write(f"\x1b]1337;voss-context={json_str}\x07")
    sys.stdout.flush()
```
The `_emit_budget_osc` function (`recorder.py:98-127`, VERIFIED) is frozen — its five-field signature (`tokens_used`, `token_limit`, `cost_usd`, `iteration`, `model`) must not change.

**litellm cost netting** — use `litellm.model_cost.get(model)` which is already imported in `agent.py:49-52`. The key is `"claude-opus-4-8"` (verified working); fallback: `litellm.model_cost.get(f"anthropic.{model}")`. Never crash — return `None` if key not found. Both `input_cost_per_token` and `cache_read_input_token_cost` must be read to net the dollar estimate:
```python
# VERIFIED via litellm.model_cost inspection
entry = litellm.model_cost.get(model) or litellm.model_cost.get(f"anthropic.{model}")
if entry is None:
    return None  # saved_usd_est = null in ledger record
input_rate = entry.get("input_cost_per_token", 0)
cache_read_rate = entry.get("cache_read_input_token_cost", 0)
gross = saved_tokens * input_rate
cache_reduction = cache_read_tokens * (input_rate - cache_read_rate)
return max(gross - cache_reduction, 0.0)
```

---

### `voss/harness/config.py` (add `[context]` block reader)

**Analog:** self — `_parse_agent_section` / `load_agent_config` / `set_max_iterations` are the exact template. Pattern is a compiled regex + `_KV.findall` + a public `load_*` accessor:

```python
# config.py:26-27 + 56-61 + 93-102 (VERIFIED) — exact template to copy for [context]
_AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)

def _parse_agent_section(text: str) -> dict[str, str]:
    m = _AGENT_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}

def load_agent_config() -> dict[str, str]:
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_agent_section(text)
```

**V18 addition** — add `_CONTEXT_BLOCK`, `_parse_context_section`, `load_context_config`, `get_packing_profile` following the identical four-function pattern. Integer values (`recent_full_k`, `digest_cutoff_m`) use the `get_max_iterations` coercion pattern (`int(raw)` with `RuntimeWarning` fallback). Float values (`high_water`, `low_water`) use the same pattern with `float(raw)`.

**Boolean value** (`enabled`) — follow the `get_allow_net` pattern (`config.py:264-286`, VERIFIED): bare `true`/`false` via `_KV_BARE`, normalized to lowercase, warn on anything else.

For the writer, `set_max_iterations` (`config.py:342-358`) shows the upsert-or-append pattern:
```python
# config.py:342-358 (VERIFIED) — write new [agent] block or replace existing
new_block = f'[agent]\nmax_iterations = "{n}"\n'
if _AGENT_BLOCK.search(existing):
    new_text = _AGENT_BLOCK.sub(new_block, existing, count=1)
elif existing.strip():
    new_text = existing.rstrip() + "\n\n" + new_block
else:
    new_text = new_block
p.write_text(new_text)
p.chmod(0o600)
```
No writer is strictly required for V18 (user edits config.toml by hand; the config reader suffices for `--no-pack` and profile selection).

---

### `voss/harness/cli.py` (add `--no-pack` to `do_cmd`; extend `_cost`)

**Analog:** self — existing flag cluster on `do_cmd` (`cli.py:1619-1657`, VERIFIED). The `--no-unicode` and `--auth` flags show the `is_flag` and `envvar` patterns:
```python
# cli.py:1625-1630 (VERIFIED) — is_flag pattern
@click.option(
    "--no-unicode",
    "no_unicode",
    is_flag=True,
    help="Use ASCII fallback for TUI glyphs (sets VOSS_NO_UNICODE=1).",
)
# cli.py:1651-1656 (VERIFIED) — envvar-backed option
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
```

**`--no-pack` flag** — follows the `--no-unicode` is_flag shape with an envvar:
```python
@click.option(
    "--no-pack",
    "no_pack",
    is_flag=True,
    envvar="VOSS_NO_PACK",
    help="Disable context packing; messages byte-identical to pre-V18.",
)
```
Pass `packing_enabled=not no_pack` into `run_turn()`.

**`_cost` extension** (`cli.py:881-918`, VERIFIED) — append the savings line after the existing flat-total block. The pattern reads from `ctx.record` and `ctx.cwd`; the savings line reads the session-scoped `token-savings.jsonl` and aggregates:
```python
# cli.py:909-918 (VERIFIED) — existing flat-total block; savings line appends here
budget = ctx.budget_usd
if budget is not None:
    pct = (ctx.total_cost / budget * 100.0) if budget > 0 else 0.0
    click.echo(f"session cost: ${ctx.total_cost:.4f} / ${budget:.2f} ({pct:.1f}%)")
else:
    click.echo(f"session cost: ${ctx.total_cost:.4f}")
# V18 insertion: read ledger from ctx.record.id + ctx.cwd, echo savings line
```
The `test_cost_slash.py` fixture (`fake_ctx` with `SimpleNamespace(record=..., total_cost=..., cwd=...)`) shows the exact ctx shape the test will use.

---

### `tests/harness/test_context_allocator.py` (new unit tests)

**Analog:** `tests/harness/test_agent_loop.py:76-114` (`FakeStreamingProvider`, `_done_script`) for the provider double; `tests/harness/test_voss_loop_parity.py:19-55` (`FakeProvider`) for a simpler synchronous-style fake; `tests/harness/test_cache_tokens.py` for pure-function unit test structure (no fixtures, just `SimpleNamespace`).

**Pure unit test pattern** — `test_cache_tokens.py` style; no provider, no tmp_path, just constructed `IterationRecord` objects:
```python
# test_cache_tokens.py:1-27 (VERIFIED) — pattern: SimpleNamespace + assert
from types import SimpleNamespace

def test_allocator_pure() -> None:
    # Construct fake iter records as SimpleNamespace — no IterationRecord import needed
    iters = [
        SimpleNamespace(
            index=i,
            plan={"rationale": f"step {i}", "steps": [], "final_when_done": ""},
            tool_results=[{"name": "fs_read", "args": {"path": "foo.py"}, "result": "ok"}],
        )
        for i in range(50)
    ]
    # ... assert allocator.pack(iters, budget=10_000, profile=PackingProfile()) produces
    #     messages with token count <= 10_000
```

**`IterationRecord` construction in tests** — for tests that need real typed records, import and construct directly (seen throughout `test_recorder_iterations.py` pattern):
```python
from voss.harness.session import IterationRecord
rec = IterationRecord(index=0, plan={"rationale": "...", "steps": []})
```

**Async test** — for any test requiring `run_turn`, copy the `@pytest.mark.asyncio` + `FakeStreamingProvider` pattern from `test_agent_loop.py:188-207`:
```python
# test_agent_loop.py:188-207 (VERIFIED)
@pytest.mark.asyncio
async def test_done_exit_after_one_planning_iter(tmp_path: Path) -> None:
    provider = FakeStreamingProvider(scripts=[_done_script(plan=iter_done)])
    renderer = RecordingRenderer()
    result = await _run_turn_exec("do thing", tools={}, cwd=tmp_path,
                                   renderer=renderer, provider=provider, model="stub-model")
    assert result.run.exit_reason == "done"
```
Pure allocator tests do NOT need `@pytest.mark.asyncio` — only tests that call `run_turn`.

---

### `tests/harness/test_agent_packing.py` (new integration tests)

**Analog:** `tests/harness/test_agent_loop.py` — exact template. Import `_run_turn_exec` (the internal async loop function) directly, supply `FakeStreamingProvider` with a scripted multi-iteration sequence, assert on `provider.stream_calls[-1]["messages"]` for the assembled message list.

**Multi-iteration script pattern** — `_done_script` constructs a single-iter termination. For a multi-iter run, provide N scripts where iterations 0..N-2 have `steps=[ToolCall(...)]` and iteration N-1 has `steps=[], final_when_done="done"`:
```python
# test_agent_loop.py:152-164 (VERIFIED) — _done_script factory
def _done_script(*, plan: Plan, prompt_tokens=10, completion_tokens=5):
    return [
        TextDelta(text="..."),
        ParsedPlan(plan=plan),
        Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost_usd=0.001),
        Done(stop_reason="end_turn"),
    ]
```

**Byte-identity assertion** — for VOPT-06 `--no-pack` test, capture `messages` under both paths (packing enabled with K=8 on ≤8 iters, and `--no-pack`), then `assert messages_packed == messages_no_pack`. Capture via `provider.stream_calls[-1]["messages"]`.

**Cache-coherence assertion** — for VOPT-03, after a 10-iter run where no recompaction fires, read `iter_record.cache_read_input_tokens` from the returned `TurnResult.run.iterations` and assert it is > 0 in steady state (with `FakeStreamingProvider` scripted to emit a `Usage` event with `cache_read_input_tokens=200`).

---

### `tests/harness/test_savings_ledger.py` (new ledger tests)

**Analog:** `tests/harness/test_cost_slash.py` (VERIFIED) for the `fake_ctx` fixture and `capsys` pattern; `tests/harness/test_harness_config.py` for the `xdg` monkeypatch fixture to control paths.

**`fake_ctx` fixture pattern** (`test_cost_slash.py:8-30`, VERIFIED):
```python
@pytest.fixture
def fake_ctx(tmp_path):
    record = SimpleNamespace(
        id="abc123",
        name="fake-session",
        cwd=str(tmp_path),
        model="claude-sonnet-4-7",
        total_cost_usd=0.0,
        runs=[{"cost_usd": 0.008, "changed": []}],
    )
    return SimpleNamespace(
        cwd=tmp_path,
        record=record,
        total_cost=0.020,
        budget_usd=None,
    )
```
For ledger tests, `fake_ctx.cwd` is `tmp_path`; ledger path = `tmp_path / ".voss" / "sessions" / "abc123" / "token-savings.jsonl"`.

**`_cost` slash command invocation pattern** (`test_cost_slash.py:33-44`, VERIFIED):
```python
from voss.harness.cli import _build_slash_registry
registry = _build_slash_registry()
registry.lookup("/cost").handler(fake_ctx, [], "/cost")
out = capsys.readouterr().out
assert "context packed:" in out
```

**JSONL read/write test** — write a ledger row with `_append_savings_record`, read it back with `json.loads`, assert invariants:
```python
import json
from pathlib import Path
# Assert packed_tokens_est <= original_tokens_est (D-03)
row = json.loads((ledger_path).read_text().splitlines()[0])
assert row["packed_tokens_est"] <= row["original_tokens_est"]
assert row["saved_tokens_est"] >= 0
```

---

### `tests/harness/test_packing_eval_gate.py` (new eval gate)

**Analog:** `voss/eval/runner.py:260-380` (`run_suite()`) and the `_append_row` / `runs.jsonl` pipeline.

**Eval runner invocation pattern** (`runner.py:290-307`, VERIFIED):
```python
# Call run_suite() with VOSS_NO_PACK env var toggled between two runs
import os
from voss.eval.runner import run_suite

def test_quality_preservation_gate(tmp_path):
    os.environ["VOSS_NO_PACK"] = "1"
    off_out = run_suite(suite="golden", stub=True, out=tmp_path / "off")
    del os.environ["VOSS_NO_PACK"]
    on_out = run_suite(suite="golden", stub=True, out=tmp_path / "on")
    # read runs.jsonl from both, compare success_rate and mean_prompt_tokens
```

**`runs.jsonl` row schema** — `_append_row` at `runner.py:100-103` writes `{task_id, run_idx, verdict, cost_usd, ...}` rows. The `verdict` field is `"pass"` / `"fail"` from `judge_run()`. Read with:
```python
import json
rows = [json.loads(l) for l in (out / "runs.jsonl").read_text().splitlines() if l.strip()]
success_rate = sum(1 for r in rows if r.get("verdict") == "pass") / len(rows)
```

**Biting gate pattern** — run `run_suite` with `PackingProfile(recent_full_k=1, digest_cutoff_m=2)` (over-aggressive) and assert `success_rate < 1.0` to prove the gate catches regressions. Use `monkeypatch` to inject the profile.

---

## Shared Patterns

### JSONL Append (ledger write)
**Source:** `voss/eval/runner.py:100-103`
**Apply to:** `voss/harness/recorder.py` `_append_savings_record`
```python
def _append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
```

### OSC Emission (non-TTY guard)
**Source:** `voss/harness/recorder.py:130-140`
**Apply to:** any new OSC emitter; savings field extends `_emit_context_osc` payload additively
```python
def _emit_context_osc(payload: dict) -> None:
    if not sys.stdout.isatty():
        return
    json_str = json.dumps(payload, separators=(",", ":"))
    sys.stdout.write(f"\x1b]1337;voss-context={json_str}\x07")
    sys.stdout.flush()
```

### Config Section Reader (regex + _KV + public accessor)
**Source:** `voss/harness/config.py:26-27`, `:56-61`, `:93-102`
**Apply to:** `voss/harness/config.py` new `[context]` block reader
```python
_AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)

def _parse_agent_section(text: str) -> dict[str, str]:
    m = _AGENT_BLOCK.search(text)
    if not m:
        return {}
    return {k: v for k, v in _KV.findall(m.group(0))}

def load_agent_config() -> dict[str, str]:
    p = config_path()
    if not p.exists():
        return {}
    try:
        return _parse_agent_section(p.read_text())
    except OSError:
        return {}
```

### Click is_flag + envvar
**Source:** `voss/harness/cli.py:1625-1630` (`--no-unicode` pattern) and `:1638-1656` (`--allow-net` / `--auth`)
**Apply to:** `--no-pack` option on `do_cmd`
```python
@click.option(
    "--no-unicode",
    "no_unicode",
    is_flag=True,
    help="...",
)
```

### FakeStreamingProvider test double
**Source:** `tests/harness/test_agent_loop.py:76-114`
**Apply to:** `test_context_allocator.py`, `test_agent_packing.py`, `test_packing_eval_gate.py`
```python
@dataclass
class FakeStreamingProvider:
    scripts: list[list[ProviderStreamEvent]]
    stream_calls: list[dict] = field(default_factory=list)
    _stream_index: int = 0

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        script = self.scripts[self._stream_index]
        self._stream_index += 1
        async def _gen():
            for ev in script:
                yield ev
        return _gen()
```

### Pytest tmp_path + xdg monkeypatch
**Source:** `tests/harness/test_harness_config.py:12-16`
**Apply to:** `test_savings_ledger.py` (ledger path isolation)
```python
@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path
```

---

## No Analog Found

All files have analogs in the codebase. No file requires patterns from RESEARCH.md alone.

---

## Critical Pitfall Notes for Planner

These are load-bearing constraints from RESEARCH.md that cross-cut pattern assignment:

1. **`--no-pack` must be a code path, not "same output"** — the `else` branch in `agent.py:713` must literally be the original `for prior in all_iter_records: _serialize_iter_for_replay(prior)` loop bytes, not a reimplementation. RESEARCH.md Pitfall 2.

2. **Allocator must be stateful across calls** — the `_stable_region` cache must persist across iterations within one `run_turn` call. If the allocator is instantiated fresh on every call to the message-assembly block, per-turn rewriting defeats the T4 cache. RESEARCH.md Pitfall 1.

3. **`packed ≤ original` is an invariant, not an assertion** — if the fold block overhead exceeds the raw replay size (short histories), fall back to `method="full"` and record `saved_tokens=0` before writing the ledger. RESEARCH.md Pitfall 4.

4. **litellm cost netting** — both `input_cost_per_token` and `cache_read_input_token_cost` must be read for `saved_usd_est`. Gross minus cache reduction, clamped to 0. RESEARCH.md Pitfall 3.

5. **Ledger path is subdirectory** — `_sessions_dir(cwd) / session_id / "token-savings.jsonl"`, NOT `_sessions_dir(cwd) / f"{session_id}.json"` (the session JSON is a flat file). RESEARCH.md Assumption A7.

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss/eval/`, `tests/harness/`
**Files scanned:** 14 source files read directly; 6 test files examined
**Pattern extraction date:** 2026-06-10
