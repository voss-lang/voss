---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 05
type: execute
wave: 3
depends_on: ["M15-04"]
files_modified:
  - voss/harness/skill/adapter.py
  - voss/harness/skill_registry.py
  - voss/harness/cli.py
  - voss/harness/recorder.py
  - voss/cli.py
  - tests/harness/skill/test_registry.py
autonomous: true
requirements: [SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05]
user_setup: []

must_haves:
  truths:
    - "An installed bundle's .voss program registers into skill_registry and runs via /skill <id> like a built-in"
    - "Before install, the third-party id does NOT resolve in the registry"
    - "The .voss skill runs under a scope-limited gate and via the EXISTING .voss runtime (no new interpreter)"
    - "voss skill add/list/remove/update/trust top-level CLI verbs work; installs/grants/denials/runs are recorded via the existing RunRecorder"
  artifacts:
    - path: "voss/harness/skill/adapter.py"
      provides: "make_voss_skill_handler — SkillEntry-compatible handler: compile + subprocess-run bundle .voss under a scoped gate"
      exports: ["make_voss_skill_handler"]
      min_lines: 50
    - path: "voss/harness/skill_registry.py"
      provides: "load_voss_skills — discover installed bundles and register VossSkill handlers"
      contains: "load_voss_skills"
    - path: "voss/harness/cli.py"
      provides: "voss skill add/list/remove/update/trust subcommands on skill_group"
      contains: "skill_add_cmd"
    - path: "voss/harness/recorder.py"
      provides: "skill install/deny/run audit events"
      contains: "skill_events"
  key_links:
    - from: "voss/harness/skill/adapter.py"
      to: "voss.cli.compile_voss_file"
      via: "compile bundle .voss → tmp .py then subprocess.run([sys.executable, generated]) (the existing voss run path)"
      pattern: "subprocess.run"
    - from: "voss/harness/skill/adapter.py"
      to: "voss.harness.skill.scope.scoped_gate"
      via: "third-party .voss runs under scoped_gate(spec, ctx.gate), never the base gate"
      pattern: "scoped_gate"
    - from: "voss/harness/cli.py"
      to: "voss.harness.skill.install.install_bundle"
      via: "skill_add_cmd → install_bundle; skill_group auto-registers via AGENT_COMMANDS"
      pattern: "install_bundle"
---

<objective>
Wire third-party `.voss` skill execution and the headless CLI surface. Add `voss/harness/skill/adapter.py` (`make_voss_skill_handler` — a `SkillEntry`-compatible handler that compiles the bundle `.voss` and runs it via the EXISTING `voss run` subprocess path under a `scoped_gate`), extend `skill_registry.py` with `load_voss_skills()` (discover installed bundles → register), add `voss skill add/list/remove/update/trust` subcommands to the existing `skill_group` in `cli.py`, expose a public `compile_voss_file()` wrapper over `voss.cli._compile_source` (RESEARCH Open Question 1 — avoid private cross-module coupling, M7 SDK discipline), and add install/deny/run audit events to `recorder.py` (CONTEXT audit-trail constraint).

This is the FIRST wave where third-party `.voss` code executes — correctly placed AFTER the W1 trust+scope spine and W2 install gating are proven (RESEARCH/CONTEXT hard-prerequisite ordering).

Purpose: SKILL-02 (`.voss` skill registers + runs via `/skill <id>` like built-ins; before install the id does not resolve). Completes the headless CLI for SKILL-01/03/05 and the audit trail for all verbs. SKILL-04 enforcement is exercised end-to-end here via the scoped gate at dispatch.

Output: `adapter.py`, extended `skill_registry.py`/`cli.py`/`recorder.py`, public `compile_voss_file`; the SKILL-02 RED tests turn GREEN.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-SPEC.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-PATTERNS.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-04-SUMMARY.md

<interfaces>
voss/harness/skill/adapter.py:
- make_voss_skill_handler(voss_path: Path, spec: ScopeSpec, *, skill_id: str) -> SkillHandler
  returns handler(ctx, args: list[str]) -> None that:
  1 scoped = scoped_gate(spec, ctx.gate)
  2 compile_voss_file(voss_path, generated_py, project_root=ctx.cwd, cache_dir=ctx.cwd/".voss-cache")
  3 env = skill subprocess env; net disabled unless spec.net (existing _check_impl is_network branch denies)
  4 subprocess.run([sys.executable, generated_py, *args], capture_output=True, text=True, env=env)
  5 echo stdout/stderr (mirrors voss/cli.py:run lines 261-264)
  6 record skill.run + any scope.deny via ctx.record (RunRecorder)

voss/harness/skill_registry.py (extend):
- load_voss_skills(cwd: Path, registry: SkillRegistry) -> None
  for each enabled installed bundle (load_plugins / user_plugin_dir scan) with voss_entry set:
    spec = scope_spec_from_manifest(...); registry.register(SkillEntry(
      id=skill_id, description=..., handler=make_voss_skill_handler(bundle_dir/voss_entry, spec, skill_id=...),
      mutating=skill_mutating))
  called from default_skill_registry() AFTER built-ins so built-in ids are not shadowed

voss/cli.py (extend — public compile wrapper, RESEARCH OQ1):
- compile_voss_file(source: Path, output: Path, *, project_root: Path | None, cache_dir: Path, verbose: bool = False) -> Path
  thin public wrapper delegating to existing _compile_source (no behavior change; removes the
  voss.harness→private voss.cli symbol coupling — M7 SDK Polish discipline)

voss/harness/cli.py (extend skill_group, lines 2389-2415):
- @skill_group.command("add")    arg source; --cwd; --allow-tofu flag → install_bundle
- @skill_group.command("list")   enumerate installed third-party skills (skill_registry + load_plugins)
- @skill_group.command("remove") arg skill_id → remove_bundle
- @skill_group.command("update") arg skill_id → update_bundle (re-verify)
- @skill_group.command("trust")  arg pub_key_b64; --identity; prints key_fingerprint, confirms, pin_key
- skill_group already in AGENT_COMMANDS (line ~2894) → register() auto-picks up new subcommands

voss/harness/recorder.py (extend, lines 20-23/28-81/192-225):
- SKILL_EVENTS = {"skill_install","skill_remove","skill_update"}
- RunRecorder: skill_events: list[dict] = field(default_factory=list); scope_denials: list[dict] = field(default_factory=list)
- observe_skill_event(self, action, skill_id, source, *, ok, error="") -> None
- observe_scope_denial(self, skill_id, tool, reason) -> None
- forwarded into RunRecord in finalize() exactly as inspected/changed are (lines ~210)

Consume: install_bundle/remove_bundle/update_bundle (M15-04); verify_manifest/is_key_trusted/pin_key/key_fingerprint (M15-02); ScopeSpec/scope_spec_from_manifest/scoped_gate (M15-03).
Reuse (existing): voss/cli.py:run lines 232-265 (TemporaryDirectory + _compile_source + subprocess.run + stdout/stderr echo + Exit(returncode)); voss/harness/cli.py `_extension_context` (2310-2356), `skill_group`/`skill_run_cmd` (2389-2415), `AGENT_COMMANDS`/`register` (2878-2908), `default_skill_registry` (skill_registry.py:35); mcp/server_skills.py make_skill_dispatch prior art (M15-PATTERNS).
</interfaces>

<analog>
voss run subprocess (the .voss runtime — reuse exactly, no new interpreter): voss/cli.py:220-265.
SkillEntry registration: voss/harness/skill_registry.py:10-32, default_skill_registry:35+ (register built-ins; append load_voss_skills AFTER).
Click group subcommand + AGENT_COMMANDS auto-register: voss/harness/cli.py:2363-2415, 2878-2908 (M15-PATTERNS "Click group + subcommand registration").
RunRecorder event extension: voss/harness/recorder.py:20-23 (tool-set constants), 56-81 (observe dispatch), 192-225 (finalize aggregation) — new lists added as `field(default_factory=list)`, forwarded in finalize like `inspected`/`changed` (M15-PATTERNS recorder section + RESEARCH §RunRecorder Event Shape).
.voss dispatch prior art: voss/harness/mcp/server_skills.py make_skill_dispatch (M15-PATTERNS lines 416-454).
</analog>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: public compile_voss_file + VossSkillAdapter (scoped, existing .voss runtime)</name>
  <read_first>
    - voss/cli.py (lines 84-140 `_compile_source`; lines 220-265 `run` subprocess path — files being modified)
    - voss/harness/skill/scope.py (scoped_gate, ScopeSpec — W1 surface consumed)
    - voss/harness/skill_registry.py (SkillHandler signature `Callable[[Any,list[str]],None]` — adapter must match)
    - voss/harness/mcp/server_skills.py (make_skill_dispatch prior art — ctx construction + stdout capture)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Pattern 4 VossSkillAdapter; §Pitfall 2 no interactive gate; Open Question 1)
  </read_first>
  <behavior>
    - compile_voss_file delegates to _compile_source with identical behavior (a .voss compiles to the same .py as `voss run` would)
    - make_voss_skill_handler returns a callable matching SkillHandler signature `(ctx, args) -> None`
    - The handler compiles the bundle .voss to a tmpdir and subprocess-runs it (the existing voss run path — no new interpreter / no in-process exec of third-party code)
    - The subprocess runs under scoped_gate(spec, ctx.gate) semantics; net disabled unless spec.net
    - stdout/stderr of the skill subprocess are echoed; non-zero subprocess exit surfaces as stderr (mirrors voss/cli.py:run)
  </behavior>
  <action>
    In `voss/cli.py` add a module-level public `compile_voss_file(source, output, *, project_root, cache_dir, verbose=False) -> Path` that calls the existing `_compile_source(source, output_path=output, project_root=project_root, cache_dir=cache_dir, verbose=verbose)` and returns its result — no behavior change; removes the private cross-module import (RESEARCH OQ1, M7 SDK discipline). Create `voss/harness/skill/adapter.py` with `make_voss_skill_handler(voss_path, spec, *, skill_id) -> SkillHandler`: inner `handler(ctx, args)` builds `scoped = scoped_gate(spec, ctx.gate)`, opens a `TemporaryDirectory(prefix="voss-skill-")`, calls `compile_voss_file(...)` into it, builds the subprocess `env` (copy of os.environ; set the harness net-disable flag unless `spec.net` so the existing `_check_impl` is_network branch denies net — reuse the same env mechanism `voss/cli.py:run` uses for VOSS_HERMETIC), `subprocess.run([sys.executable, str(generated), *args], capture_output=True, text=True, env=env)`, echo stdout/stderr exactly as voss/cli.py:run lines 261-264, and record the run via `getattr(ctx.record, "observe_skill_event", lambda *a, **k: None)("skill_run", skill_id, "", ok=<rc==0>)` (guarded so this task is independently testable before Task 3). Do NOT exec third-party `.voss` in-process — subprocess only (the confinement boundary per RESEARCH Pattern 4 key constraint).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "from voss.cli import compile_voss_file; from voss.harness.skill.adapter import make_voss_skill_handler; import inspect; print('PARAMS', list(inspect.signature(make_voss_skill_handler).parameters)); print('HAS_COMPILE', callable(compile_voss_file))" && grep -nc "subprocess.run" voss/harness/skill/adapter.py && grep -nc "scoped_gate" voss/harness/skill/adapter.py</automated>
  </verify>
  <acceptance_criteria>
    - `compile_voss_file` is importable from `voss.cli` and callable; the inline check prints `HAS_COMPILE True`
    - `make_voss_skill_handler` parameters are `['voss_path', 'spec', 'skill_id']` (the inline check prints them)
    - `grep -c "subprocess.run" voss/harness/skill/adapter.py` ≥ 1 AND `grep -c "scoped_gate" voss/harness/skill/adapter.py` ≥ 1 (subprocess path + scoped gate both present)
    - `grep -n "exec(\|exec (" voss/harness/skill/adapter.py` returns nothing (no in-process exec of third-party code)
    - No private `from voss.cli import _compile_source` anywhere under `voss/harness/` (grep: `grep -rn "_compile_source" voss/harness/` returns nothing)
  </acceptance_criteria>
  <done>A public compile wrapper exists; the adapter runs bundle .voss via the existing subprocess runtime under a scoped gate; no in-process third-party exec, no private cross-module coupling.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: load_voss_skills registry extension + skill_group add/list/remove/update/trust CLI</name>
  <read_first>
    - voss/harness/skill_registry.py (lines 10-32 SkillEntry/SkillRegistry; lines 35+ default_skill_registry — file being modified)
    - voss/harness/cli.py (lines 2389-2415 skill_group/skill_run_cmd; 2363-2379 plugin_group pattern; 2878-2908 AGENT_COMMANDS/register; 2310-2356 _extension_context — file being modified)
    - voss/harness/skill/install.py (install_bundle/remove_bundle/update_bundle — M15-04 surface consumed)
    - voss/harness/trust.py (pin_key/key_fingerprint — for skill trust subcommand)
    - tests/harness/skill/test_registry.py (`test_voss_skill_dispatch`, `test_unknown_skill_not_found` — RED tests being satisfied)
  </read_first>
  <behavior>
    - Before any install, default_skill_registry().get("voss-git-summary") is None (third-party id does not resolve — SKILL-02 pre-add)
    - After install_bundle, load_voss_skills registers the id; default_skill_registry().get(id) returns a SkillEntry whose handler runs the .voss and produces its declared effect (SKILL-02 register)
    - Built-in skill ids (analyze, rename-symbol, voss-lint-as-skill) are never shadowed (load_voss_skills runs AFTER built-ins; a third-party manifest reusing a built-in id does not override the built-in)
    - `voss skill add ./<bundle>` then `voss skill list` shows the id; `voss skill remove <id>` then `voss skill list` omits it and get(id) is None; `voss skill trust <b64> --identity x` prints the fingerprint and pins the key
  </behavior>
  <action>
    Extend `skill_registry.py`: add `load_voss_skills(cwd, registry)` that calls `load_plugins(cwd, ...)` / scans `user_plugin_dir()` for installed bundle subdirs with `voss_entry` set + `enabled`, builds `spec = scope_spec_from_manifest(...)`, and `registry.register(SkillEntry(id=skill_id, description=..., handler=make_voss_skill_handler(bundle_dir/voss_entry, spec, skill_id=skill_id), mutating=skill_mutating))`. Call `load_voss_skills(Path.cwd(), registry)` at the END of `default_skill_registry()` (after built-ins are registered) so built-in ids win on collision (RESEARCH anti-pattern "hardcoding skill IDs" — enumerate via registry). Extend `voss/harness/cli.py` `skill_group` with `skill_add_cmd` (`add <source>` `--cwd` `--allow-tofu` → `install_bundle`; on `SkillTrustError` echo the fingerprint + "run: voss skill trust <key>" and exit non-zero), `skill_list_cmd` (`list` → enumerate installed third-party skills from `load_plugins`/registry, print id + scopes + the gate-only-confinement caveat line), `skill_remove_cmd` (`remove <id>` → `remove_bundle`), `skill_update_cmd` (`update <id>` → `update_bundle`; on failure echo error + exit non-zero, prior version intact), `skill_trust_cmd` (`trust <pub_key_b64>` `--identity` → print `key_fingerprint`, `click.confirm`, `pin_key`). `skill_group` is already in `AGENT_COMMANDS` so `register()` auto-exposes the new subcommands (no AGENT_COMMANDS edit needed beyond confirming membership). Record install/remove/update through the RunRecorder (Task 3 method) via the ctx record.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest tests/harness/skill/test_registry.py -x -q 2>&1 | tail -3 && python3 -c "from click.testing import CliRunner; from voss.harness.cli import skill_group; r=CliRunner().invoke(skill_group, ['--help']); print('SUBCMDS', sorted(c for c in ['add','list','remove','update','trust','run') if c in r.output))"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/skill/test_registry.py -x` — `test_voss_skill_dispatch` AND `test_unknown_skill_not_found` PASS (were RED in W0)
    - The inline check prints `SUBCMDS ['add', 'list', 'remove', 'run', 'trust', 'update']` (all five new verbs registered on skill_group alongside the existing `run`)
    - Before install, `default_skill_registry().get("voss-git-summary")` is `None`; after `install_bundle`, it is a `SkillEntry` (test asserts both)
    - A third-party manifest declaring `skill.id = "analyze"` does NOT override the built-in `analyze` (load_voss_skills runs after built-ins — test asserts the built-in handler still resolves)
  </acceptance_criteria>
  <done>SKILL-02: installed .voss bundles register and dispatch via /skill <id>; the full headless CLI verb set (add/list/remove/update/trust) is wired and auto-registered; built-ins are not shadowed.</done>
</task>

<task type="auto">
  <name>Task 3: RunRecorder skill install/deny/run audit events</name>
  <read_first>
    - voss/harness/recorder.py (lines 20-23 tool-set constants; lines 28-81 RunRecorder + observe; lines 192-225 finalize — file being modified)
    - voss/harness/skill/install.py (call sites for observe_skill_event — M15-04 surface)
    - voss/harness/skill/adapter.py (call site for observe_skill_event/observe_scope_denial — Task 1 guarded call)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§RunRecorder Event Shape)
  </read_first>
  <action>
    Extend `voss/harness/recorder.py` per `<interfaces>`: add `SKILL_EVENTS = {"skill_install","skill_remove","skill_update"}` near the existing tool-set constants (lines 20-23); add `skill_events: list[dict] = field(default_factory=list)` and `scope_denials: list[dict] = field(default_factory=list)` to the `RunRecorder` dataclass exactly as `inspected`/`changed` are declared; add `observe_skill_event(self, action, skill_id, source, *, ok, error="") -> None` (append `{"action":..., "skill_id":..., "source":..., "ok":..., "error": error[:200]}`) and `observe_scope_denial(self, skill_id, tool, reason) -> None`; forward both new lists into the `RunRecord` in `finalize()` (lines ~192-225) exactly as `inspected`/`changed`/`failures` are forwarded (mirror the existing aggregation, add the two `RunRecord` fields with default `field(default_factory=list)` for back-compat). Wire the call sites: `install_bundle`/`remove_bundle`/`update_bundle` (M15-04 — add the observe calls if a recorder is in scope; pass-through optional recorder param if not already threaded) and the adapter's guarded `observe_skill_event` from Task 1 now resolves to the real method. Existing `observe()` dispatch and existing call sites are byte-unchanged (additive only — M2/recorder back-compat discipline).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "from voss.harness.recorder import RunRecorder, SKILL_EVENTS; r=RunRecorder(); r.observe_skill_event('skill_install','x','./b',ok=True); r.observe_scope_denial('x','fs_write','denied by mode plan'); print('EVENTS', r.skill_events, 'DENY', r.scope_denials, 'SET', sorted(SKILL_EVENTS))" && python3 -m pytest tests/harness/test_recorder.py -x -q 2>&1 | tail -2 && python3 -m pytest tests/harness/skill/ -q -m "not live" 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - The inline check prints a populated `EVENTS` list, a populated `DENY` list, and `SET ['skill_install', 'skill_remove', 'skill_update']`
    - `pytest tests/harness/test_recorder.py -x` PASSES (existing recorder behavior unchanged — additive only)
    - `pytest tests/harness/skill/ -q -m "not live"` — all of test_trust/test_scope/test_install/test_registry/test_lifecycle GREEN (full per-wave gate; only the e2e fixture test remains for M15-06)
    - `finalize()` forwards `skill_events` + `scope_denials` into the RunRecord (grep shows both forwarded alongside `inspected`/`changed`)
  </acceptance_criteria>
  <done>Install/remove/update + scope denials + skill runs are recorded through the existing RunRecorder additively; the full SKILL-01..05 harness suite is GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| installed .voss → harness process | Third-party code first EXECUTES here (subprocess); the scoped gate is the only confinement (OS sandbox deferred) |
| third-party manifest id → registry | A bundle could claim a built-in id to shadow trusted behavior |
| skill run → audit log | Every third-party invocation must be attributable (CONTEXT audit constraint) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M15-05-01 | Elevation of Privilege | Third-party .voss runs with full authority | mitigate | adapter runs the subprocess under `scoped_gate(spec, ctx.gate)`; net disabled unless `spec.net`; default-deny (plan) when undeclared (W1 scope spine) |
| T-M15-05-02 | Spoofing | Third-party manifest shadows a built-in skill id | mitigate | `load_voss_skills` runs AFTER built-ins in `default_skill_registry()`; built-in id wins on collision (acceptance test asserts `analyze` not overridden) |
| T-M15-05-03 | Elevation of Privilege | In-process exec of third-party .voss | mitigate | adapter uses `subprocess.run([sys.executable, generated])` only — never in-process `exec`; acceptance grep forbids `exec(` |
| T-M15-05-04 | Elevation of Privilege | Direct Python `open()`/`urllib` in subprocess bypasses gate | accept | DOCUMENTED limitation (SPEC-accepted, OS sandbox deferred); surfaced in `voss skill list` caveat line + M15-06 README/`voss doctor`; gate confines harness tool calls only |
| T-M15-05-05 | Repudiation | Untracked third-party skill invocation | mitigate | `observe_skill_event`/`observe_scope_denial` record install/remove/update/run/deny through the existing RunRecorder (CONTEXT audit-trail constraint); forwarded into RunRecord |
| T-M15-05-06 | Tampering | Interactive prompt / store persistence from skill subprocess | mitigate | scoped gate is `auto_yes=True, store=None` (W1 Pitfall 2); subprocess cannot prompt-bypass or persist an "always allow" |
| T-M15-05-SC | Tampering | No new package introduced | accept | Reuses stdlib subprocess + existing compiler; no package-manager install in this wave |
</threat_model>

<verification>
- `pytest tests/harness/skill/test_registry.py -x -q` — 2/2 SKILL-02 tests GREEN
- `pytest tests/harness/skill/ -q -m "not live"` — SKILL-01..05 all GREEN (only e2e fixture test remains for M15-06)
- `pytest tests/harness/test_recorder.py -x` + `pytest tests/harness/test_extensions.py -x` — no regression (additive recorder/registry changes)
- adapter uses subprocess (not in-process exec) under a scoped gate; no private `_compile_source` import under voss/harness/
- `voss skill --help` lists add/list/remove/update/trust + the existing run
</verification>

<success_criteria>
SKILL-02 satisfied: third-party `.voss` skills register and run via `/skill <id>` like built-ins (and not before install), executed through the existing `.voss` subprocess runtime under a scope-limited gate; the full headless CLI verb set is wired; every install/grant/deny/run is audited through the existing RunRecorder; no built-in shadowing, no in-process third-party exec, no private cross-module coupling.
</success_criteria>

<output>
Create `.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-05-SUMMARY.md` when done
</output>
