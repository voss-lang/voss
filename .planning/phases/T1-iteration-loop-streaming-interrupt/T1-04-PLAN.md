---
phase: T1-iteration-loop-streaming-interrupt
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/tui/widgets/turn_view.py
  - voss_runtime/_config.py
  - voss/harness/config.py
autonomous: true
requirements: [ITER-01, ITER-03]
must_haves:
  truths:
    - "TurnView exposes a stream_delta(text) entry point that writes incrementally via RichLog.write without inserting role/header lines"
    - "Repeated stream_delta calls accumulate into a single visible block in the live RichLog"
    - "RuntimeConfig gains a max_iterations field defaulting to 8"
    - "voss/harness/config.py exposes a getter that resolves [agent] max_iterations from ~/.config/voss/config.toml with default 8 fallback"
    - "Existing TurnView.append_turn behavior for completed turns is unchanged"
  artifacts:
    - path: "voss/harness/tui/widgets/turn_view.py"
      provides: "stream_delta(text: str) method on TurnView; finalize_stream() method to seal the streaming block"
      contains: "def stream_delta"
    - path: "voss_runtime/_config.py"
      provides: "RuntimeConfig.max_iterations: int = 8"
      contains: "max_iterations:"
    - path: "voss/harness/config.py"
      provides: "load_agent_config() / get_max_iterations() reading [agent] max_iterations from ~/.config/voss/config.toml"
      contains: "max_iterations"
  key_links:
    - from: "voss/harness/config.py"
      to: "voss_runtime/_config.py"
      via: "get_max_iterations() returns either the TOML override or the RuntimeConfig.max_iterations default"
      pattern: "RuntimeConfig\\(\\)\\.max_iterations\\|get_config\\(\\)\\.max_iterations"
---

<objective>
Land the two independent leaves that the iteration loop (T1-05) depends on:
(a) a TurnView delta-write entry point so the agent loop can stream tokens
into the UI, and (b) the `max_iterations` config knob (default 8) plumbed
into both RuntimeConfig and the harness TOML loader.

Purpose: SPEC ITER-03 acceptance requires TurnView to render incremental
deltas; CONTEXT.md locks "Append-only via RichLog.write on every TextDelta
... No in-place edits, no scroll jumps." SPEC ITER-01 + Success Criterion
4 require `max_iterations` default 8 configurable via harness TOML, with
hit-cap producing the structured "halted: max-iter" final string (T1-05
consumes the knob; this plan ships the knob).

This plan groups the two leaves because they're independent of each other
and of T1-01/02/03, so they form a small wave-1 utility plan instead of
two solo plans (each task < 15% context).

Output: TurnView gains stream_delta + finalize_stream; RuntimeConfig
gains max_iterations; voss/harness/config.py parses [agent] max_iterations.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md
@voss/harness/tui/widgets/turn_view.py
@voss_runtime/_config.py
@voss/harness/config.py
</context>

<interfaces>
Current TurnView (voss/harness/tui/widgets/turn_view.py):
```
class TurnView(RichLog):
    def __init__(self, **kw) -> None: ...
    def on_mount(self) -> None: ...
    def append_turn(self, role, body, *, confidence=None, cost_usd=None,
                    timestamp=None) -> None: ...
```
RichLog provides `.write(rich_renderable, scroll_end=True)`. No "edit
previous line" API — additive append is the only option, which is exactly
what CONTEXT.md locks.

Current RuntimeConfig (voss_runtime/_config.py):
```
@dataclass
class RuntimeConfig:
    default_model: str = "claude-sonnet-4-5"
    default_embedding_model: str = "text-embedding-3-small"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_retries: int = 1
    match_threshold: float = 0.75
    cache_dir: str = ".voss-cache"
    timeout_seconds: float = 60.0
    max_output_tokens: int = 4096
```
`configure(**kwargs)` rebuilds the singleton via dataclasses.replace.
`get_config()` returns the singleton.

Current voss/harness/config.py: parses only the `[harness]` section
(preferred_model). Uses regex-based parsing, no full TOML lib. For [agent]
section parsing we EXTEND the regex strategy (one more section block +
key/value capture) rather than introducing tomllib — keeps the file
narrow as its docstring promises ("Kept narrow on purpose").

CONTEXT.md "Claude's Discretion": "`harness.toml` schema location — [agent]
section vs. [loop] section for `max_iterations = 8`. Constraint: must be
discoverable via `voss config` and documented in M0/M1 docs." PICK:
[agent] section. Rationale: matches REQUIREMENTS naming (`ITER-*` lives
in the "agent loop" concept space), and "agent" is broader/more
expressive for future neighbors (e.g., agent.confidence_threshold, agent.
timeout). Document the choice in T1-04-SUMMARY.md.

Note on config file: SPEC refers to "harness.toml" but the actual on-disk
file is ~/.config/voss/config.toml parsed by voss/harness/config.py. This
plan extends THAT file's parser. The runtime side (voss_runtime/_config.py)
gets a default-only field; the harness TOML reader is the override source.

T1-05 will read `max_iterations` via this chain:
`get_config().max_iterations` (returns RuntimeConfig default 8) OR
`load_agent_config().get("max_iterations", get_config().max_iterations)`
— left to T1-05 which one to call. This plan exposes BOTH so T1-05 has a
clean choice (recommended: harness load_agent_config + configure() call
at cli.py boot to write the override into RuntimeConfig once, so
`get_config().max_iterations` is the single read path inside the loop).
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add TurnView.stream_delta + finalize_stream</name>
  <files>voss/harness/tui/widgets/turn_view.py, tests/harness/tui/test_turn_view_streaming.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-03 acceptance — "First visible token in TurnView ≤ 500ms after provider HTTP 200")
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (TurnView render section + Specifics "Stream backpressure / token rate limiting in TurnView — render every delta, no throttling")
    - voss/harness/tui/widgets/turn_view.py (entire file — 68 lines)
    - tests/harness/tui/ (look for existing TurnView tests — `ls tests/harness/tui/test_turn_view*` — to match fixture pattern)
  </read_first>
  <behavior>
    - tv.stream_delta("hel") + tv.stream_delta("lo") + tv.finalize_stream(role="assistant", confidence=0.92, cost_usd=0.01) results in (a) the RichLog body containing "hello" as the streaming content and (b) one trailing header line with role/cost/conf metadata appended on finalize
    - First call to stream_delta(...) on a TurnView whose _turn_count is 0 clears the empty-state heading/body (same behavior as append_turn's first-call clear)
    - Calling stream_delta after finalize_stream starts a NEW streaming block (no leakage into the previous block)
    - Existing append_turn(...) behavior is unchanged — same test file should import and exercise it with one quick assertion
    - 1000 stream_delta calls with a single character each do not raise and produce a single accumulated string (smoke test against the "no throttling" invariant)
  </behavior>
  <action>
    Add two methods to the TurnView class in voss/harness/tui/widgets/turn_view.py:

    `def stream_delta(self, text: str) -> None`:
        - If self._turn_count == 0: self.clear() and set
          self._turn_count = 0 anyway (we don't bump turn_count for
          partial streams — finalize_stream bumps it).
        - If self._streaming is False (new attribute, default False —
          initialize in __init__): set self._streaming = True; do NOT
          write a header yet (we don't know the final cost/confidence
          mid-stream).
        - Append the text via self.write(Text(text, no_wrap=False)).
          Use Text with no_wrap=False to allow soft wrapping; markup
          is disabled by the parent constructor (markup=False).

    `def finalize_stream(self, *, role: str, confidence: float | None
    = None, cost_usd: float | None = None, timestamp: str | None =
    None) -> None`:
        - If self._streaming: bump self._turn_count += 1, build a
          header Text the same way append_turn does (role bold +
          timestamp/cost/conf in dim), write the header AFTER the
          accumulated body (i.e., at the bottom of the streamed block
          — TODO note: Textual users typically expect the header
          BEFORE the body. Reconcile: prepend semantics aren't
          possible in RichLog. So the contract is "header is written
          at finalize time, below the streamed body". Document this
          in the docstring. Acceptable per CONTEXT.md's append-only
          constraint.).
        - Set self._streaming = False.

    Update __init__: `self._streaming: bool = False`.

    Write `tests/harness/tui/test_turn_view_streaming.py` covering the
    five behavior bullets. Use the textual.testing pattern from any
    existing TurnView tests (or fall back to instantiating
    TurnView() directly and calling methods if no Pilot harness is
    used today — `grep -rn "TurnView()" tests/` to find the existing
    pattern). Assert the streamed content is present in
    self._renderables (or whatever RichLog public surface exists for
    introspection — `grep -n "renderables\|lines" voss/harness/tui/`
    if uncertain).

    Do NOT change the on_mount empty-state copy. Do NOT change
    append_turn. Do NOT change SideRegion.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/tui/test_turn_view_streaming.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "def stream_delta\|def finalize_stream" voss/harness/tui/widgets/turn_view.py` returns exactly 2 matches
    - source assertion: `grep -n "_streaming" voss/harness/tui/widgets/turn_view.py` >= 3 (init + stream_delta read/write + finalize_stream read/write)
    - behavior assertion: all five pytest behaviors pass
    - regression assertion: existing TurnView tests still pass — `uv run pytest tests/harness/tui/ -k turn_view -x -q`
    - test command: `uv run pytest tests/harness/tui/test_turn_view_streaming.py tests/harness/tui/ -k turn_view -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>TurnView.stream_delta accumulates text into the RichLog without per-call header writes; finalize_stream seals the block with role/cost/confidence metadata; existing append_turn path is untouched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add RuntimeConfig.max_iterations + harness TOML [agent] reader</name>
  <files>voss_runtime/_config.py, voss/harness/config.py, tests/harness/test_agent_config.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (Success Criterion 4 "Default max iteration = 8, configurable via harness.toml")
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Claude's Discretion "harness.toml schema location — [agent] section vs. [loop] section")
    - voss_runtime/_config.py (entire 38-line file — RuntimeConfig dataclass + configure + reset_config)
    - voss/harness/config.py (entire 59-line file — current [harness] regex parser)
  </read_first>
  <behavior>
    - get_config().max_iterations == 8 by default
    - configure(max_iterations=12); get_config().max_iterations == 12; reset_config() restores 8
    - load_agent_config() with no config file returns {} (no error)
    - load_agent_config() with a config file containing `[agent]\nmax_iterations = 12` returns {"max_iterations": "12"} (string, matching existing parser convention)
    - get_max_iterations() with no config file returns 8 (the default)
    - get_max_iterations() with `[agent]\nmax_iterations = 12` returns 12 (int, coerced from the string)
    - get_max_iterations() with `[agent]\nmax_iterations = not-a-number` returns 8 (falls back to default on parse error, with a warning emitted via warnings.warn)
    - set_max_iterations(20) writes/updates `[agent]\nmax_iterations = "20"\n` to the config file, preserving any existing [harness] section
    - Existing load_harness_config() and set_preferred_model() are unchanged in behavior — write a regression test asserting they still parse a config that has BOTH [harness] and [agent] sections
  </behavior>
  <action>
    In voss_runtime/_config.py:
    - Add one field to RuntimeConfig: `max_iterations: int = 8` (place
      it after max_output_tokens; field order matters only for
      positional kwargs which we audited as none — all callers use
      keyword args).

    In voss/harness/config.py:
    - Extend the regex strategy. Currently `_HARNESS_BLOCK` matches
      `^\[harness\][^\[]*`. Add a parallel `_AGENT_BLOCK` matching
      `^\[agent\][^\[]*`. The `_KV` regex is already section-agnostic
      so it works for [agent] values.
    - Add `def _parse_agent_section(text: str) -> dict[str, str]:` —
      direct copy of `_parse_harness_section` with the block regex
      swapped.
    - Add `def load_agent_config() -> dict[str, str]:` — direct copy
      of `load_harness_config` swapping the parser call.
    - Add `def get_max_iterations() -> int:` that:
        1. Loads the agent section.
        2. Reads "max_iterations" key.
        3. Tries int(value). On ValueError or missing key, returns
           the default `RuntimeConfig().max_iterations` (== 8 — read
           from the dataclass-default singleton, NOT a hard-coded 8,
           so a future RuntimeConfig default change propagates).
        4. On parse failure (non-int string present), emit
           `warnings.warn(f"[agent] max_iterations = {value!r} is not
           an integer; falling back to default 8", RuntimeWarning)`.
    - Add `def set_max_iterations(n: int) -> Path:` mirroring
      set_preferred_model: write `[agent]\nmax_iterations = "{n}"\n`,
      preserve [harness] block via the same dual-regex re-emit pattern
      used by set_preferred_model. If both [harness] and [agent] blocks
      exist on read, both must survive on write (re-emit both).

    Write `tests/harness/test_agent_config.py` with eight tests
    matching the eight behavior bullets. Use tmp_path + monkeypatched
    XDG_CONFIG_HOME to isolate the config file. Reset RuntimeConfig
    via reset_config() in a fixture so test 2 (configure overwrite)
    doesn't bleed into test 1.

    Do NOT introduce tomllib. Do NOT remove or modify
    load_harness_config / set_preferred_model / config_path /
    _HARNESS_BLOCK / _KV. Surgical add.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_config.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "max_iterations:\s*int\s*=\s*8" voss_runtime/_config.py` returns 1 match
    - source assertion: `grep -n "_AGENT_BLOCK\|load_agent_config\|get_max_iterations\|set_max_iterations" voss/harness/config.py` returns >= 4 matches
    - behavior assertion: all eight pytest behaviors pass, including the warnings.warn fallback
    - regression assertion: `uv run pytest tests/harness/ -k "harness_config or config" -x -q` (existing config tests) still passes
    - cross-section assertion: a config file with both [harness] preferred_model and [agent] max_iterations round-trips through (load_harness_config, load_agent_config) and (set_preferred_model, set_max_iterations) without either erasing the other
    - test command: `uv run pytest tests/harness/test_agent_config.py tests/harness/ -k "config" -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>RuntimeConfig has max_iterations field default 8; voss/harness/config.py reads/writes the [agent] section; get_max_iterations resolves runtime default OR TOML override with safe int-coercion fallback; existing [harness] handling unaffected.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/tui/test_turn_view_streaming.py tests/harness/test_agent_config.py -x -q` passes
- `grep -n "max_iterations" voss_runtime/_config.py voss/harness/config.py | wc -l` >= 5 (at least one in _config.py, four in config.py)
- `uv run pytest tests/harness/ -k "config or turn_view" -x -q` passes
- TurnView still satisfies its existing layout test (M9-02 layout test should not break — `uv run pytest tests/harness/tui/ -x -q`)
</verification>

<success_criteria>
- TurnView has a delta-write entry point that the iteration loop can call from inside the streaming async-for
- `get_config().max_iterations` returns 8 by default
- A user can override max_iterations via `[agent] max_iterations = N` in ~/.config/voss/config.toml
- The chosen schema location ([agent] section) is documented in T1-04-SUMMARY.md
- No regression in existing TurnView layout or [harness] config tests
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-SUMMARY.md` when done with: TurnView API addition (signatures), RuntimeConfig field add, the chosen [agent] section schema with one example TOML snippet, and a note that the agent loop (T1-05) consumes get_max_iterations() to bootstrap the loop's cap.
</output>
