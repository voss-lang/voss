---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 03
type: execute
wave: 3
depends_on: ["V18-02-budget-aware-context-allocator-token-optimization"]
files_modified:
  - voss/harness/agent.py
  - voss/harness/config.py
  - voss/harness/cli.py
autonomous: true
requirements: [VOPT-03, VOPT-06]
must_haves:
  truths:
    - "When packing is disabled (--no-pack / VOSS_NO_PACK / config enabled=false), the assembled messages list is BYTE-IDENTICAL to the pre-V18 path because the disabled branch IS the original four-line for-loop verbatim, not a reimplementation"
    - "The T4 cache_control static prefix (sys_blocks, built once pre-loop at agent.py:363-395) is never passed to the allocator and never repacked — messages[0] is byte-identical whether packing is on or off"
    - "When packing is enabled, the allocator is instantiated ONCE per run_turn (not per iteration) so its stable-region state persists, and steady-state turns show cache_read_input_tokens dominating in IterationRecord"
    - "A [context] config block (enabled, recent_full_k, digest_cutoff_m, high_water, low_water) is read via the existing config.py regex pattern; the default profile is conservative (recent_full_k=8) so runs at or below 8 iterations are unchanged"
    - "packing_budget is derived as token_budget - reserve(cached_prefix_est + rider_est + user_prompt_est + completion_headroom); the ctx.token_budget halt at agent.py:1009-1011 is unchanged"
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "if/else seam at :713 — allocator branch + verbatim original loop; packing_enabled param on run_turn/_run_turn_exec; allocator instantiated once; packing_budget computation"
      contains: "packing_enabled"
    - path: "voss/harness/config.py"
      provides: "[context] block reader: _CONTEXT_BLOCK regex, _parse_context_section, load_context_config, get_packing_profile"
      contains: "_CONTEXT_BLOCK"
    - path: "voss/harness/cli.py"
      provides: "--no-pack flag (is_flag, envvar VOSS_NO_PACK) on do_cmd threaded as packing_enabled=not no_pack into run_turn"
      contains: "no-pack"
  key_links:
    - from: "voss/harness/agent.py:713"
      to: "voss.harness.context_allocator.ContextAllocator"
      via: "if packing_enabled and all_iter_records: allocator.pack(...); else: verbatim original loop"
      pattern: "packing_enabled and all_iter_records"
    - from: "voss/harness/cli.py do_cmd"
      to: "run_turn(packing_enabled=...)"
      via: "--no-pack flag → packing_enabled=not no_pack"
      pattern: "packing_enabled"
    - from: "voss/harness/config.py get_packing_profile"
      to: "PackingProfile"
      via: "reads [context] keys into the dataclass; conservative defaults when absent"
      pattern: "PackingProfile"
---

<objective>
Wire the pure allocator into the agent loop at the single chokepoint (agent.py:713) behind an if/else seam where the disabled branch is the original four-line replay loop verbatim — guaranteeing byte-identity by construction (VOPT-06), not by golden match. Preserve the T4 cached prefix untouched and instantiate the allocator once per run so its hysteresis state delivers cache-coherent steady-state replay (VOPT-03). Add the `[context]` config surface and the `--no-pack` escape hatch with a conservative default profile.

Purpose: This is the load-bearing correctness plan. If --no-pack is "same output" rather than "same code path", or if the allocator is re-instantiated per iteration, the two headline guarantees (byte-identical disable, warm prompt cache) silently break.

Output: agent.py seam + config.py [context] reader + cli.py --no-pack, turning the VOPT-06 byte-identity and VOPT-03 steady-state integration tests GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-SPEC.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md

<interfaces>
<!-- VERIFIED source seams. -->

agent.py:708-716 (the chokepoint — VERIFIED current bytes):
  messages: list[dict] = [
      {"role": "system", "content": sys_blocks},  # cached static prefix (CACHE-01)
      {"role": "system", "content": rider},
      {"role": "user", "content": user_prompt},
  ]
  for prior in all_iter_records:
      a_msg, u_msg = _serialize_iter_for_replay(prior)
      messages.append(a_msg)
      messages.append(u_msg)
  # NOTE: immediately after this loop is the M13-03 synthetic-steer block — do NOT disturb it.

agent.py other VERIFIED anchors:
  :73-80   _default_token_count(text, *, model)   — bind model via functools.partial to inject into the allocator
  :363-395 _compose_system_blocks → sys_blocks    — T4 prefix, built ONCE before the while-loop; NEVER an allocator input
  :493     async def run_turn(...) -> TurnResult   — add `packing_enabled: bool = True` kwarg
  :499     token_budget: int = 60_000
  :564     async def _run_turn_exec(...)           — add `packing_enabled: bool = True`; instantiate allocator ONCE here, before the while-loop
  :676     all_iter_records: list[IterationRecord] = []
  :713     the for-loop to wrap in if/else
  :760     max_tokens=cfg.max_output_tokens        — completion_headroom source
  :791     getattr(this_iter_usage,"cache_read_input_tokens",0)  — populates IterationRecord (VOPT-03 proof)
  :1009-1011  ctx.tokens_used >= ctx.token_budget → exit_reason="budget"  — UNCHANGED

config.py VERIFIED template (copy the [agent] pattern):
  :26  _AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)
  :39  _KV  (quoted-string values)   :45  _KV_BARE (bare tokens, for booleans/numbers)
  :56  _parse_agent_section / :93 load_agent_config / :209 get_max_iterations (int coerce) / :264 get_allow_net (bool)

cli.py VERIFIED anchors:
  :1626 "--no-unicode" is_flag pattern    :1658 def do_cmd    :1739 run_turn(...) call inside do_cmd
  run_turn is also invoked at :2136 and :2227 (REPL paths) — those keep the default packing_enabled=True (no flag plumbed there in V18)

From Plan 02 — voss/harness/context_allocator.py:
  class ContextAllocator(token_count); PackingProfile(recent_full_k=8, digest_cutoff_m=20, high_water=0.80, low_water=0.60, enabled=True)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: [context] config reader + get_packing_profile</name>
  <read_first>
    - voss/harness/config.py:25-45 (block regexes + _KV + _KV_BARE), :56-61 (_parse_agent_section template), :93-105 (load_agent_config template), :209-230 (get_max_iterations int-coerce pattern), :264-286 (get_allow_net bool pattern)
    - voss/harness/context_allocator.py (PackingProfile dataclass from Plan 02 — the target shape)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md (config.py section: the four-function pattern + Pitfall 7 confirming no [context] collision)
  </read_first>
  <action>
    In voss/harness/config.py add, mirroring the [agent] template exactly:
    - `_CONTEXT_BLOCK = re.compile(r"^\[context\][^\[]*", re.MULTILINE)` near the other block regexes (~:26-32).
    - `_parse_context_section(text) -> dict[str,str]`: search _CONTEXT_BLOCK; merge _KV.findall (quoted) then _KV_BARE.findall (bare numbers/bools via setdefault) so `recent_full_k = 8` and `enabled = false` both parse.
    - `load_context_config() -> dict[str,str]`: config_path() exists-guard + read_text + _parse_context_section (verbatim load_agent_config shape).
    - `get_packing_profile() -> PackingProfile`: import PackingProfile from voss.harness.context_allocator; read load_context_config(); coerce recent_full_k/digest_cutoff_m via int() (RuntimeWarning + default on failure, per get_max_iterations), high_water/low_water via float(), enabled via the get_allow_net bool normalization (true/false lowercased). Missing keys fall back to PackingProfile() defaults (conservative). Never raise — warn and default.
    No config WRITER is required (user hand-edits config.toml; reader suffices for --no-pack and profile selection).
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -c "from voss.harness.config import get_packing_profile, load_context_config, _parse_context_section; p=get_packing_profile(); assert p.recent_full_k==8 and p.high_water==0.80 and p.enabled is True, p"` exits 0 (conservative defaults when no [context] block present).
    - `.venv/bin/python -c "from voss.harness.config import _parse_context_section; d=_parse_context_section('[context]\nenabled = false\nrecent_full_k = 4\nhigh_water = 0.9\n'); assert d.get('enabled')=='false' and d.get('recent_full_k')=='4' and d.get('high_water')=='0.9', d"` exits 0.
    - `grep -n "_CONTEXT_BLOCK\|def get_packing_profile\|def load_context_config" voss/harness/config.py` shows all three present.
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.config import get_packing_profile; p=get_packing_profile(); print('k=',p.recent_full_k,'hw=',p.high_water,'en=',p.enabled); assert p.recent_full_k==8 and p.enabled is True"</automated>
  </verify>
  <done>[context] block reads via the existing regex pattern; get_packing_profile returns conservative defaults when absent and parses overrides; never raises (warn+default on bad values).</done>
</task>

<task type="auto">
  <name>Task 2: agent.py if/else seam + once-per-run allocator + packing_budget + run_turn threading</name>
  <read_first>
    - voss/harness/agent.py:708-720 (the chokepoint for-loop + the M13-03 synthetic-steer block right after it — must remain a sibling of the replay messages, undisturbed)
    - voss/harness/agent.py:493-520 (run_turn signature + token_budget=60_000), :564-580 (_run_turn_exec signature + where the while-loop begins — allocator must be instantiated BEFORE the loop, once)
    - voss/harness/agent.py:73-80 (_default_token_count — bind via functools.partial(model=model) to inject into ContextAllocator)
    - voss/harness/agent.py:363-395 (sys_blocks T4 prefix — confirm it is built once and is NOT an allocator input), :760 (cfg.max_output_tokens for completion_headroom)
    - voss/harness/context_allocator.py (ContextAllocator/PackingProfile from Plan 02)
    - voss/harness/config.py get_packing_profile (Task 1)
    - tests/harness/test_agent_packing.py (test_no_pack_byte_identical, test_cached_prefix_unchanged, test_cache_coherence_steady_state — the targets)
  </read_first>
  <action>
    In voss/harness/agent.py:
    - Add `packing_enabled: bool = True` to both `run_turn` (:493) and `_run_turn_exec` (:564) signatures; thread it through the run_turn → _run_turn_exec call.
    - In _run_turn_exec, BEFORE the while-loop, resolve the profile: `_packing_profile = get_packing_profile()` (import from voss.harness.config); compute effective enable = `packing_enabled and _packing_profile.enabled`. Instantiate the allocator ONCE: `_allocator = ContextAllocator(token_count=functools.partial(_default_token_count, model=<resolved model string>))`. Do NOT instantiate inside the loop (RESEARCH Pitfall 1 — per-turn re-instantiation defeats the stable region and the T4 cache).
    - At the seam (:713), wrap the four-line loop in if/else. The ELSE branch must be the EXISTING four lines verbatim (`for prior in all_iter_records: a_msg,u_msg=_serialize_iter_for_replay(prior); messages.append(a_msg); messages.append(u_msg)`) — copy them unchanged (RESEARCH Pitfall 2; PATTERNS critical note 1). The IF branch (`if effective_enable and all_iter_records:`) computes packing_budget then calls `_allocator.pack(all_iter_records, packing_budget, _packing_profile)` and appends each (a_msg,u_msg) pair.
    - Compute packing_budget once per iteration head: `reserve = cached_prefix_est + rider_est + user_est + completion_headroom` where cached_prefix_est = sum(_default_token_count(b["text"], model=...) for b in sys_blocks if isinstance(b,dict) and isinstance(b.get("text"),str)), rider_est/user_est via _default_token_count on rider/user_prompt, completion_headroom = cfg.max_output_tokens; `packing_budget = max(token_budget - reserve, 0)`.
    - Leave the M13-03 synthetic-steer block, the ctx.token_budget halt (:1009-1011), and both all_iter_records.append sites (:941, :992) UNCHANGED.
    Add `import functools` if not already imported.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_agent_packing.py::test_no_pack_byte_identical tests/harness/test_agent_packing.py::test_cached_prefix_unchanged -x` exits 0 (byte-identical messages + unchanged T4 prefix when toggled).
    - `.venv/bin/python -m pytest tests/harness/test_agent_packing.py::test_cache_coherence_steady_state -x` exits 0 (cache_read_input_tokens dominates in steady state).
    - `grep -n "for prior in all_iter_records:" voss/harness/agent.py` still shows the verbatim loop present (inside the else branch).
    - `.venv/bin/python -c "import ast; t=ast.parse(open('voss/harness/agent.py').read()); fns={n.name for n in ast.walk(t) if isinstance(n,ast.AsyncFunctionDef)}; assert 'run_turn' in fns and '_run_turn_exec' in fns" && grep -n "packing_enabled" voss/harness/agent.py` shows packing_enabled on the signatures.
    - `.venv/bin/python -m pytest tests/harness/test_agent_loop.py tests/harness/test_voss_loop_parity.py -q` exits 0 (no regression in the existing loop/parity suites).
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_agent_packing.py -x -q && .venv/bin/python -m pytest tests/harness/test_agent_loop.py tests/harness/test_voss_loop_parity.py -q</automated>
  </verify>
  <done>Seam wired as if/else with the else branch verbatim; allocator instantiated once before the loop; packing_budget computed with the reserve formula; --no-pack/off path byte-identical and T4 prefix unchanged; existing loop+parity suites still green; M13 steer block + budget halt untouched.</done>
</task>

<task type="auto">
  <name>Task 3: --no-pack CLI flag on do_cmd</name>
  <read_first>
    - voss/harness/cli.py:1620-1660 (do_cmd flag cluster; "--no-unicode" is_flag at :1626; the do_cmd def at :1658)
    - voss/harness/cli.py:1737-1755 (the run_turn(...) call inside do_cmd — where packing_enabled must be threaded)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md (cli.py section: --no-pack follows --no-unicode is_flag+envvar)
  </read_first>
  <action>
    In voss/harness/cli.py on do_cmd (:1658), add a click option mirroring --no-unicode:
    `@click.option("--no-pack", "no_pack", is_flag=True, envvar="VOSS_NO_PACK", help="Disable context packing; messages byte-identical to pre-V18.")`
    Add `no_pack: bool` to the do_cmd signature. At the run_turn(...) call inside do_cmd (:1739), pass `packing_enabled=not no_pack`.
    Do NOT plumb the flag into the REPL run_turn calls at :2136/:2227 in V18 (those default to packing_enabled=True; the env var VOSS_NO_PACK still disables via config/agent default if the executor chooses to honor it there — but the required surface is the do_cmd flag only).
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m voss.harness.cli do --help 2>&1 | grep -- "--no-pack"` shows the flag with its help text.
    - `grep -n "no-pack\|no_pack\|packing_enabled=not no_pack" voss/harness/cli.py` shows the option, the signature param, and the threaded call.
    - `VOSS_NO_PACK=1 .venv/bin/python -m voss.harness.cli do --help` exits 0 (envvar binding does not break parsing).
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m voss.harness.cli do --help 2>&1 | grep -- "--no-pack"</automated>
  </verify>
  <done>--no-pack flag present on `voss do` (is_flag + VOSS_NO_PACK envvar), threaded as packing_enabled=not no_pack into the do_cmd run_turn call.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI flag / env / config → assembly path | The --no-pack escape hatch must fail CLOSED to byte-identity; the T4 cached prefix must never enter the allocator |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V18-06 | Tampering (escape-hatch fails open) | agent.py:713 if/else seam | mitigate | The disabled branch IS the verbatim original four-line loop (not a reimplementation); test_no_pack_byte_identical asserts equality of stream_calls[-1]["messages"]; grep gate confirms the verbatim loop persists |
| T-V18-07 | Tampering (T4 prefix corruption) | sys_blocks immutability | mitigate | sys_blocks built once at :363-395 and passed as messages[0] directly; the allocator only receives all_iter_records; test_cached_prefix_unchanged asserts messages[0] byte-identical on toggle (VOPT-08 cached-prefix golden) |
| T-V18-08 | Tampering (cache defeat via re-instantiation) | allocator lifecycle | mitigate | Allocator instantiated ONCE before the while-loop so stable-region state persists (Pitfall 1); test_cache_coherence_steady_state asserts cache_read_input_tokens dominates |
| T-V18-09 | DoS (reserve underestimate) | packing_budget formula | accept | If reserve underestimates, packed messages may slightly overflow the model context, but the ctx.token_budget halt (:1009-1011, unchanged) still bounds the run; estimate drift is labeled (Pitfall 5) and reconciled by the ledger (Plan 04); low realistic impact |
| T-V18-SC | Tampering | npm/pip/cargo installs | accept | No new packages; only stdlib + existing imports (functools). No install task. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_agent_packing.py -x -q` GREEN (byte-identity, prefix-unchanged, steady-state cache coherence).
- `.venv/bin/python -m pytest tests/harness/test_agent_loop.py tests/harness/test_voss_loop_parity.py tests/harness/test_harness_config.py -q` GREEN (no regression).
- `voss do --help` lists `--no-pack`.
- The verbatim original for-loop persists in the else branch; sys_blocks never enters the allocator.
</verification>

<success_criteria>
- agent.py has the if/else seam at :713 with a verbatim disabled branch; run_turn/_run_turn_exec carry packing_enabled; allocator instantiated once per run.
- config.py reads the [context] block; conservative default profile (recent_full_k=8).
- cli.py do_cmd exposes --no-pack (VOSS_NO_PACK).
- VOPT-06 byte-identity and VOPT-03 steady-state integration tests are GREEN; existing harness loop/parity/config suites remain green.
</success_criteria>

<output>
Create `.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-03-SUMMARY.md` when done.
</output>
