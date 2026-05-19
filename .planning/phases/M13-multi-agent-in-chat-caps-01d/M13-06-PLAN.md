---
phase: M13-multi-agent-in-chat-caps-01d
plan: 06
type: execute
wave: 4
depends_on: [M13-04, M13-05]
files_modified:
  - voss/harness/cli.py
  - tests/e2e/test_multiagent_chat_e2e.py
autonomous: true
requirements: [MAG-08]
must_haves:
  truths:
    - "A single voss chat --plain NL request fans out to >=2 concurrent SubAgentPanels under the stub provider"
    - "Each child's BudgetMeter leaves the em-dash placeholder and ticks >=1 time before collapse"
    - "The autonomous parent injects >=1 mid-run course-correction into a running child and the child observably acts on it"
    - "The even-split reserve rebalances >=1 time when a child finishes (a survivor's allotment increases)"
    - "gather aggregates all child results into the parent chat turn output"
    - "After gather, zero SubAgentPanels remain mounted and the M9-08 side-region pin/owner state is restored"
    - "Existing attach_subagent_tool / /agent spawn / voss agent spawn paths are byte-stable (back-compat)"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "attach_multiagent_tools wired into the chat _run_repl toolset immediately after the chat-site attach_subagent_tool call (cli.py:1634)"
      contains: "attach_multiagent_tools"
    - path: "tests/e2e/test_multiagent_chat_e2e.py"
      provides: "Green headline e2e asserting all 6 MAG-08 acceptance signals in one stub-provider voss chat run"
      contains: "def test_"
  key_links:
    - from: "voss/harness/cli.py (chat _run_repl tool wiring)"
      to: "voss.harness.multiagent.attach_multiagent_tools"
      via: "additive call immediately after the attach_subagent_tool block at cli.py:1634"
      pattern: "attach_multiagent_tools\\("
    - from: "tests/e2e/test_multiagent_chat_e2e.py"
      to: "voss chat --plain (subprocess via CliRunner stub provider)"
      via: "CliRunner.run('chat','--plain', stdin=..., env_overrides/responses) -> stub-scripted parent fan-out"
      pattern: "cli_runner\\.run\\("
---

<objective>
Wire the M13 multi-agent toolset into the `voss chat` REPL and bring the headline end-to-end transcript test green — closing MAG-08 and rolling up MAG-01..MAG-07 through one stub-provider proof.

This is the Wave 4 integration plan. All machinery already exists by the time this runs: the `M13Allocator`/`ChildRegistry`/four tools/`PanelBridgeRenderer` (M13-02, M13-03), the `agent.py` steer-inbox drain (M13-03), the TUI bridge + `ctrl+o` reveal + region restore (M13-04), and the slice-scoped recursive sub-allocator (M13-05). The only production change here is a single additive call site in `cli.py`; the only test change is making the M13-01-scaffolded `tests/e2e/test_multiagent_chat_e2e.py` pass deterministically.

Purpose: prove the full orchestrator UX (NL request → concurrent fan-out → live quiet panels → mid-run correction → budget rebalance → gather → clean teardown) in one hermetic transcript — the phase's "done" scenario.

Output: `voss/harness/cli.py` additively imports and calls `attach_multiagent_tools` in the chat path; `tests/e2e/test_multiagent_chat_e2e.py` passes under the stub provider with no live network.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-SPEC.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-CONTEXT.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md

<read_first>
<!-- Executor: read these specific anchors BEFORE editing. Do not explore beyond them. -->

1. `voss/harness/cli.py:1634-1643` — the CHAT-site `attach_subagent_tool(...)` call. This is the
   one in `_run_repl` (followed immediately by the `jobs_root = jail_path(...) / "jobs"` /
   `.active-session` write block). The `attach_multiagent_tools(...)` call goes IMMEDIATELY AFTER
   this block, BEFORE the `jobs_root = ...` line. Exact current block:

   attach_subagent_tool(
       tools,
       registry=subagent_registry,
       cwd=cwd,
       renderer=renderer,
       provider=provider,
       model=lambda: get_config().default_model,
       gate=gate,
       cognition=bundle,
   )

   THERE ARE THREE `attach_subagent_tool` CALL SITES (cli.py:1337 `voss do`, cli.py:1634 chat
   `_run_repl`, cli.py:2342 resume). M13-06 touches ONLY the 1634 chat site. Do NOT add
   `attach_multiagent_tools` at 1337 or 2342 — that is out of scope for this plan/phase (chat
   integration only, per outline Wave 4).

2. `voss/harness/cli.py:43-48` — the existing `from .subagents import (...)` import block.
   Add a sibling `from .multiagent import attach_multiagent_tools` import near it (alphabetical
   placement after `.skill_registry`/`.slash` and before/after `.subagents` is fine; match the
   existing relative-import grouping).

3. `tests/e2e/test_chat_e2e.py:1-40` — the CliRunner stdin-script precedent
   (`cli_runner.run("chat", "--plain", stdin="...\n/exit\n", timeout=...)`,
   assert `r.returncode == 0`, assert substrings in `r.stdout`).

4. `tests/e2e/runner.py` — `CliRunner`: `run(*args, stdin=, timeout=, env_overrides=, cwd=)`;
   `responses` dict / `default_response` → `VOSS_TEST_STUB_RESPONSES`/`VOSS_TEST_STUB_RESPONSE`
   env (StubProvider fingerprint-keyed scripting); `extra_sitecustomize` hook for installing a
   scripted multi-agent stub script in the subprocess. `cli_runner` fixture
   (`tests/e2e/conftest.py`) is rooted at the `minimal` fixture project with stub auth patched.

5. `voss_runtime/providers/stub.py:23-170` — `StubProvider`: `fingerprint(messages)` (sha256 of
   sorted-json messages, 16 hex), `responses.get(fp, default_response)`, `complete`/`stream`.
   This is how the e2e scripts deterministic parent/child turns.

6. The M13-01 Wave-0 scaffold of `tests/e2e/test_multiagent_chat_e2e.py` (RED/xfail). M13-06 OWNS
   making it pass — read it first to learn the exact assertion contract M13-01 froze (the 6
   MAG-08 signals). DO NOT redesign the test's assertions; supply the production wiring + any
   stub-script/sitecustomize plumbing the scaffold left as a TODO so its frozen assertions go
   green. If the scaffold left the e2e as a thin xfail placeholder (no concrete assertions),
   implement the 6-signal assertion body per MAG-08 / M13-VALIDATION.md row MAG-08.

7. M13-03 / M13-05 SUMMARYs (`*-SUMMARY.md` in this phase dir) — read to learn the FINAL tool
   names (`subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather` were working
   names; M13-03 finalized them) and the `attach_multiagent_tools` signature M13-03 shipped.
   The call kwargs below assume the analog signature; reconcile against the actual M13-03 export.
</read_first>

<interfaces>
<!-- Contracts the executor needs. attach_multiagent_tools is shipped by M13-03 (Wave 2A). -->

From voss/harness/multiagent.py (created M13-02, tools added M13-03 — VERIFY exact signature
against the M13-03 SUMMARY before wiring; this mirrors attach_subagent_tool's parameter list
per M13-PATTERNS Analog A):

```
def attach_multiagent_tools(
    tools: dict[str, ToolEntry],
    *,
    registry,            # subagent_registry (same object passed to attach_subagent_tool)
    cwd: Path,
    renderer: Renderer,
    provider,
    model,               # lambda: get_config().default_model
    gate: PermissionGate,
    cognition=None,
) -> None: ...
```

From voss/harness/cli.py (chat-site locals in scope at line 1634, VERIFIED present):
  - `tools` (dict[str, ToolEntry] being assembled for the chat turn)
  - `subagent_registry`
  - `cwd`
  - `renderer`
  - `provider`
  - `get_config` (callable; `get_config().default_model`)
  - `gate`
  - `bundle` (cognition)

From tests/e2e/runner.py CliRunner:
  - `cli_runner` fixture (conftest) — rooted at `minimal` fixture project, stub auth patched.
  - `cli_runner.run("chat", "--plain", stdin=..., timeout=...) -> Result`
  - `Result.returncode`, `Result.stdout`, `Result.stderr`, `Result.output`
  - For scripted multi-turn: construct a dedicated `CliRunner(project_root=, state_home=,
    responses={fp: reply}, default_response=, extra_sitecustomize=...)` OR pass
    `env_overrides={"VOSS_TEST_STUB_RESPONSES": json.dumps({...})}` to `run`. Prefer the
    mechanism the M13-01 scaffold already established — match it, do not invent a parallel one.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire attach_multiagent_tools into the chat REPL toolset (additive, chat site only)</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    cli.py:43-48 (.subagents import block); cli.py:1634-1643 (chat-site attach_subagent_tool
    call + the immediately-following jobs_root/.active-session block); M13-03 SUMMARY for the
    final attach_multiagent_tools export name + signature.
  </read_first>
  <acceptance_criteria>
    PASS when ALL hold:
    - `grep -n "from .multiagent import attach_multiagent_tools" voss/harness/cli.py` → exactly 1 match.
    - `grep -c "attach_multiagent_tools(" voss/harness/cli.py` → exactly 1 call site (the chat site).
    - The new call appears AFTER the cli.py:1634 `attach_subagent_tool(` block and BEFORE the
      `jobs_root = jail_path(cwd, ".voss-cache") / "jobs"` line in the same function.
    - `grep -c "attach_subagent_tool(" voss/harness/cli.py` is UNCHANGED from pre-edit (3 call
      sites: 1337, 1634, 2342 — all still present, none altered).
    - Back-compat byte-stable: `git diff voss/harness/cli.py` shows ONLY (a) one added import
      line and (b) one added `attach_multiagent_tools(...)` call block — no edits to any
      `attach_subagent_tool` call, no edits near cli.py:1117 (`/agent spawn` slash) or
      cli.py:2437 (`agent_spawn_cmd` / `voss agent spawn` CLI).
    - `python -m py_compile voss/harness/cli.py` exits 0.
    - `python -c "import voss.harness.cli"` exits 0 (import-time wiring resolves).
  </acceptance_criteria>
  <action>
    Add `from .multiagent import attach_multiagent_tools` to cli.py's relative-import section
    near the existing `from .subagents import (...)` block (cli.py:43-48), matching the existing
    import grouping/ordering style.

    In the chat `_run_repl` path, immediately AFTER the `attach_subagent_tool(...)` call block
    that ends at cli.py:1643 (the one followed by `jobs_root = jail_path(cwd, ".voss-cache") /
    "jobs"`), add an additive `attach_multiagent_tools(...)` call passing the SAME kwargs the
    adjacent `attach_subagent_tool` call uses, sourced from the in-scope chat locals:
    `tools` (positional), `registry=subagent_registry`, `cwd=cwd`, `renderer=renderer`,
    `provider=provider`, `model=lambda: get_config().default_model`, `gate=gate`,
    `cognition=bundle`. Use the EXACT exported name + signature M13-03 shipped (verify against
    the M13-03 SUMMARY — `subagent_spawn`/`steer`/`status`/`gather` were working names that
    M13-03 finalized; the attach function name may have been finalized too).

    Do NOT remove, reorder, or alter the existing `attach_subagent_tool` call (back-compat: the
    serial single-shot `subagent_run` tool stays attached alongside the new non-blocking tools —
    D-02). Do NOT touch the 1337 (`voss do`) or 2342 (resume) `attach_subagent_tool` sites — M13
    integration is chat-path only (outline Wave 4). Do NOT touch the `/agent spawn` slash
    handler (~cli.py:1117) or `agent_spawn_cmd` (~cli.py:2437). No code blocks, no refactor —
    one import line + one call block, mirroring the analog at M13-PATTERNS "cli.py (MOD)".

    Per D-02: this is additive. Per M13-PATTERNS "subagents.py (MOD — but effectively
    UNCHANGED)": `subagents.py` and `SPAWN_TOOL_NAME` stay byte-stable; you are not editing them
    here, only attaching an additional toolset in the chat wiring.
  </action>
  <verify>
    <automated>python -m py_compile voss/harness/cli.py && python -c "import voss.harness.cli" && grep -c "from .multiagent import attach_multiagent_tools" voss/harness/cli.py | grep -qx 1 && grep -c "attach_multiagent_tools(" voss/harness/cli.py | grep -qx 1 && grep -c "attach_subagent_tool(" voss/harness/cli.py | grep -qx 3 && echo WIRED_OK</automated>
  </verify>
  <done>
    cli.py chat path attaches both `attach_subagent_tool` (unchanged) and the new
    `attach_multiagent_tools` toolset; back-compat anchors (`attach_subagent_tool` x3, `/agent
    spawn`, `voss agent spawn`) byte-stable; module imports cleanly.
  </done>
</task>

<task type="auto">
  <name>Task 2: Bring the headline e2e (tests/e2e/test_multiagent_chat_e2e.py) green — all 6 MAG-08 signals</name>
  <files>tests/e2e/test_multiagent_chat_e2e.py</files>
  <read_first>
    The M13-01-scaffolded `tests/e2e/test_multiagent_chat_e2e.py` (currently RED/xfail) — read
    it FIRST to learn the exact frozen assertion contract. `tests/e2e/test_chat_e2e.py:1-40`
    (CliRunner stdin-script pattern). `tests/e2e/runner.py` (`CliRunner.run`, `responses`/
    `default_response`/`extra_sitecustomize`, env keys). `tests/e2e/conftest.py` (`cli_runner`
    fixture). `voss_runtime/providers/stub.py:23-170` (fingerprint-keyed scripting).
    M13-VALIDATION.md row MAG-08 (the 6-signal contract). M13-03 + M13-05 SUMMARYs (final tool
    names + recursion behavior the stub script must drive).
  </read_first>
  <acceptance_criteria>
    PASS when `pytest tests/e2e/test_multiagent_chat_e2e.py -x -q` passes and the test asserts
    ALL SIX MAG-08 signals (objective pass/fail, derived from the one stub `voss chat --plain`
    run's stdout/transcript — exact assertion seams as frozen by the M13-01 scaffold; if the
    scaffold left them as TODO, implement per this list):

    1. CONCURRENT PANELS (>=2): the transcript shows >=2 distinct `SubAgentPanel`s in flight
       from the single NL request (>=2 distinct child handle/panel ids observed before any
       gather/collapse marker — overlap, not serial).
    2. BUDGET TICK (>=1 per child): each child's `BudgetMeter` left the em-dash placeholder and
       incremented >=1 time before its panel collapsed (meter shows a non-em-dash used/total;
       >=1 update per child).
    3. APPLIED CORRECTION (>=1): the scripted parent injected >=1 mid-run steer into a running
       child and the child's output observably differs from a no-correction control branch
       (the steer-branching child stub from the M13-01 contract).
    4. REBALANCE (>=1): a still-running child's allotment increased after another child
       finished (the meter/total reflects the freed-slice credit exactly once).
    5. AGGREGATED MULTI-CHILD TURN: the final parent chat turn output aggregates results
       referencing all spawned children (not a single child's result).
    6. CLEAN POST-GATHER REGION: after gather, zero `SubAgentPanel`s remain and the M9-08
       side-region pin/owner state matches the pre-spawn contract (per the scaffold's seam —
       `--plain` transcript marker or the documented region-clean assertion).

    AND: `r.returncode == 0` for the `voss chat --plain` subprocess run; the test runs under
    the StubProvider with NO live network (no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` dependency —
    `cli_runner` already strips them); deterministic (passes on 3 consecutive runs).
  </acceptance_criteria>
  <action>
    Open the M13-01-scaffolded `tests/e2e/test_multiagent_chat_e2e.py`. It was created RED/xfail
    in Wave 0 with the MAG-08 assertion contract frozen by M13-01 (per the outline coverage
    audit: "tests/e2e/test_multiagent_chat_e2e.py (headline transcript)"). Your job is to make
    it pass WITHOUT changing its assertion intent — supply the deterministic stub script and any
    `extra_sitecustomize`/`responses` plumbing the scaffold left as a TODO, and remove the
    xfail/skip marker.

    Drive it with the `tests/e2e/test_chat_e2e.py` precedent: `cli_runner.run("chat", "--plain",
    stdin="<one NL request>\n/exit\n", timeout=...)`. The NL request must, via the scripted
    StubProvider, cause the parent to: (a) call the M13-03 fan-out spawn tool >=2 times
    (>=2 concurrent children), (b) call the steer tool >=1 time into a still-running child
    scripted to BRANCH on guidance presence (M13-01's correction-vs-control child stub), (c)
    let one child finish so the even-split allocator rebalances (M13-05 / M13-02 behavior), then
    (d) call the gather tool to aggregate and trigger `collapse_subagent` M9-08 restore.

    Script determinism: the StubProvider keys replies by `fingerprint(messages)` (sha256 of
    sorted-json messages, 16 hex) with a `default_response` fallback. Use the SAME scripting
    mechanism the M13-01 scaffold established (the per-message `responses` map and/or an
    `extra_sitecustomize`-injected scripted multi-agent stub script that scripts parent + each
    child's turns). Match it exactly — do not introduce a parallel scripting mechanism. If the
    scaffold left a fixture/helper stub (e.g. a scripted multi-agent provider sitecustomize
    fragment) referenced-but-empty, fill it so the 6 signals are observable in the `--plain`
    transcript. Child stubs must be scripted for >=2 iterations so the agent.py:830 steer drain
    (M13-03) is observably hit (per M13-PATTERNS: "tests must script >=2 child iterations").

    Boundaries (LOCKED — assert these stay true; do not violate while making the test pass):
    no live network (D-11), no disk persistence of sub-agent sessions (O1 owns that — the
    transcript must not write `.voss/sessions/`), no `VossAgent.spawn` routing, no child↔child,
    no human-redirect, recursion bounded by viable-floor only (no `depth`/`max_depth` constant).
    Keep `tests/harness/test_subagent_recursion.py` green (regression guard) — you are not
    editing it, but if your stub script or wiring trips it, the wiring is wrong, not the test.

    Do NOT modify `voss/harness/multiagent.py`, `agent.py`, `cli.py` (beyond Task 1), or any
    M13-04 TUI file to make this pass — if a signal can't be observed, the gap is in the stub
    script / e2e plumbing, OR a real defect to surface to the orchestrator (do not paper over
    it by weakening an assertion). The 6 MAG-08 assertions are the phase gate; weakening them is
    prohibited (scope-reduction prohibition).
  </action>
  <verify>
    <automated>python -m pytest tests/e2e/test_multiagent_chat_e2e.py -x -q && python -m pytest tests/harness/test_subagent_recursion.py -x -q</automated>
  </verify>
  <done>
    `tests/e2e/test_multiagent_chat_e2e.py` passes deterministically under the stub provider,
    asserting all 6 MAG-08 signals from one `voss chat --plain` run; the back-compat recursion
    regression guard stays green; no live network, no disk persistence, no boundary violation.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| chat REPL turn → harness toolset wiring (cli.py:1634) | Adds a second sub-agent toolset to the in-process chat turn. No new external input crosses here — the parent LLM (already trusted, behind `_resolve_auth_or_die`) is the only caller of the new tools. |
| e2e subprocess → StubProvider | Deterministic scripted provider; no live network egress. Trust boundary is closed by the existing `CliRunner` cred-strip + stub-auth patch. |

M13 adds no auth/session/crypto/network/persistence surface. M13-06 specifically is a single
additive wiring call + a hermetic test — the narrowest possible blast radius in the phase. The
e2e itself is the regression seam that PROVES blast radius stays in-memory + UI only.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M13-06-orphan | Denial of Service | `attach_multiagent_tools` children spawned in the chat turn that outlive the turn | mitigate | Relies on M13-03's `subagent_gather` defensive gather/cancel-on-teardown safety net; this plan's e2e Task 2 asserts zero `SubAgentPanel`s + clean M9-08 region after gather (MAG-07 roll-up) — proves no orphan leak through the integrated chat path. |
| T-M13-06-egress | Information Disclosure | e2e network egress | mitigate | `CliRunner` strips `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` and patches `_resolve_auth_or_die` to the StubProvider via generated `sitecustomize.py`; Task 2 acceptance asserts hermetic (no live network, D-11). |
| T-M13-06-persist | Tampering | sub-agent session disk persistence (O1's domain, must NOT appear in M13) | accept/verify | Task 2 boundary check asserts the transcript does not write `.voss/sessions/` — M13 budget/fan-out stays M13-local + in-memory; O1 owns persistence. Low risk: M13-02..05 already keep `ChildRegistry` in-memory; this plan only wires + tests. |
| T-M13-06-backcompat | Tampering | accidental edit to `attach_subagent_tool` / `/agent spawn` / `voss agent spawn` while adding the new call | mitigate | Task 1 acceptance: `grep -c "attach_subagent_tool(" == 3` unchanged + `git diff` shows ONLY 1 import + 1 call block; no edits near cli.py:1117 / cli.py:2437. |
| T-M13-06-priv | Elevation of Privilege | child sub-agents gaining broader permission scope than the parent | accept | The new toolset is wired with the SAME `gate=gate` the chat parent uses (identical kwarg to the adjacent `attach_subagent_tool`); child reuses parent `PermissionGate` unchanged — same posture as existing `run_subagent` (M13-VALIDATION T-M13 priv). No new scope introduced by this wiring. |
| T-M13-06-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan (stdlib + existing project deps only — `asyncio`, `json`, existing test harness). RESEARCH confirms zero new third-party dependencies for M13. No legitimacy gate required. |

All threats have a disposition. No `high`-severity unmitigated threat → no blocking checkpoint.
Blast radius: in-memory + UI only (M13-VALIDATION §"Security Domain": "No new secret material,
no new network egress, no new persisted data").
</threat_model>

<verification>
- `python -m py_compile voss/harness/cli.py` exits 0.
- `python -c "import voss.harness.cli"` exits 0.
- `grep -c "from .multiagent import attach_multiagent_tools" voss/harness/cli.py` == 1.
- `grep -c "attach_multiagent_tools(" voss/harness/cli.py` == 1 (chat site only).
- `grep -c "attach_subagent_tool(" voss/harness/cli.py` == 3 (unchanged back-compat anchors).
- `git diff voss/harness/cli.py` = exactly one added import + one added call block (no other hunks).
- `python -m pytest tests/e2e/test_multiagent_chat_e2e.py -x -q` passes.
- `python -m pytest tests/harness/test_subagent_recursion.py -x -q` passes (regression guard, unmodified).
- Headline e2e asserts all 6 MAG-08 signals (>=2 concurrent panels, >=1 budget tick/child,
  >=1 applied correction, >=1 rebalance, aggregated multi-child turn, clean post-gather region).
- Deterministic: e2e passes on 3 consecutive runs (no live network).
</verification>

<success_criteria>
- MAG-08 satisfied: one stub-provider `voss chat --plain` e2e proves the full headline scenario
  (fan-out + live quiet panels + mid-run correction + budget rebalance + gather + clean
  teardown) with all 6 acceptance signals asserted in one test.
- Chat integration is purely additive: `attach_subagent_tool` (x3 sites), `/agent spawn`,
  `voss agent spawn`, and `subagents.py`/`SPAWN_TOOL_NAME` remain byte-stable.
- No boundary violation: no live network, no disk persistence of sub-agent sessions, no
  `VossAgent.spawn` routing, no child↔child, no human-redirect, no depth constant.
- Back-compat regression guard (`test_subagent_recursion.py`) green unmodified.
</success_criteria>

<output>
Create `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-06-SUMMARY.md` when done.
</output>
