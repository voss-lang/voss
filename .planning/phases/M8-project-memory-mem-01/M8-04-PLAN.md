---
phase: M8
plan: 04
type: execute
wave: 3
depends_on: [M8-03]
files_modified:
  - voss/harness/conventions.py
  - voss/harness/cli.py
  - tests/harness/test_conventions.py
autonomous: true
requirements: [MEM-04]
tags: [memory, conventions, llm-extraction]
must_haves:
  truths:
    - "conventions.has_signal(turns) returns True only when ≥1 user turn matches _SIGNAL_RE OR repeat-edit-same-target detected from run.changed (D-09)"
    - "When has_signal returns False, run_on_clean_exit skips the LLM call AND the review prompt entirely (Req 4 acceptance: zero candidates skips prompt)"
    - "extract_conventions wraps the LLM call in asyncio.wait_for(timeout=8.0); on TimeoutError returns [] silently (D-12)"
    - "extract_conventions validates LLM output via ConventionCandidate.model_validate; ValidationError returns [] silently — no crash, no partial results"
    - "review_candidates(candidates, interactive=True) prints numbered list per D-11 and reads a single stdin line; empty input returns [] (declining all)"
    - "review_candidates(candidates, interactive=False, selection='1 3') returns [0, 2] (1-based input parsed to 0-based indices)"
    - "Each persisted convention writes one .voss/memory/conventions/YYYY-MM-DD-<slug>.md via memory_store.write_convention (existing M8-03 API)"
    - "run_on_clean_exit is wired into _run_repl's EOFError/KeyboardInterrupt exit branch AND into do_cmd's post-run_turn path (per A6 — both clean-exit paths)"
    - "Exceptions inside run_on_clean_exit are caught and emit a stderr one-liner; REPL exit is never blocked by extraction failure"
  artifacts:
    - path: "voss/harness/conventions.py"
      provides: "has_signal / extract_conventions / review_candidates / run_on_clean_exit implementations replacing Wave-0 NotImplementedError stubs"
    - path: "voss/harness/cli.py"
      provides: "Exit-hook wiring: _run_repl exit branch + do_cmd post-run call run_on_clean_exit(ctx, history=..., record=..., memory_store=...)"
  key_links:
    - from: "voss/harness/cli.py::_run_repl (EOFError/KeyboardInterrupt branch)"
      to: "conventions.run_on_clean_exit"
      via: "try/except wrapping; never blocks exit"
      pattern: "conventions\\.run_on_clean_exit"
    - from: "voss/harness/cli.py::do_cmd (post-run_turn)"
      to: "conventions.run_on_clean_exit"
      via: "single-call invocation after the one-shot turn completes"
      pattern: "conventions\\.run_on_clean_exit"
    - from: "voss/harness/conventions.py::run_on_clean_exit"
      to: "memory_store.write_convention"
      via: "per-selected-candidate write loop"
      pattern: "memory_store\\.write_convention"
---

<objective>
Land MEM-04: conventions extraction at session end with user confirmation. Replace Wave-0 NotImplementedError stubs in voss/harness/conventions.py with the D-09 pre-filter + D-10 strict-JSON LLM extraction + D-11 numbered-list review UX + D-12 8-second timeout. Wire run_on_clean_exit into both clean-exit paths (REPL EOFError/KeyboardInterrupt branch AND do_cmd post-run-turn) per RESEARCH A6.

Purpose: Without this plan, the harness has no mechanism to surface candidate user conventions for persistence — the MEM-03 store can be written to manually via /save but the auto-curated conventions corpus stays empty. This plan delivers the auto-extraction pipeline that makes the convention source-type useful at scale.
Output: Working conventions.py (4 functions + helpers), exit-hook wired into 2 cli.py sites, 5 conventions tests green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M8-project-memory-mem-01/M8-SPEC.md
@.planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md
@.planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md
@.planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md
@.planning/phases/M8-project-memory-mem-01/M8-03-SUMMARY.md
@voss/harness/conventions.py
@voss/harness/cli.py
@voss/harness/skills/analyze.py
@voss/harness/agent.py

<interfaces>
<!-- M8-00 already defines (this plan fills behavior): -->
- ConventionCandidate(BaseModel) with statement (1..500), confidence (0..1), evidence_quote (≥1 char), evidence_turn_idx (≥0)
- _SIGNAL_RE = re.compile pattern for D-09 starters
- DEFAULT_EXTRACTION_TIMEOUT_SECONDS = 8.0
- has_signal / extract_conventions / review_candidates / run_on_clean_exit (NotImplementedError stubs to be replaced)

<!-- M8-03 already delivered: -->
- MemoryStore.write_convention(candidate, *, session_id) -> Path

<!-- Existing patterns reused: -->
- voss/harness/skills/analyze.py asyncio.run(run_turn(...)) pattern (analyze.py:44-57)
- voss/harness/agent.py run_turn signature — accepts provider, model, history, tools — sufficient for a one-shot LLM call
- voss/harness/cli.py EOFError/KeyboardInterrupt exit branch in _run_repl (around cli.py:773-778); do_cmd post-run path (around cli.py:540-547)
- ReplContext dataclass — extended by M8-01 to hold voss_md_text; this plan adds memory_store handle (or threads it through as a parameter to run_on_clean_exit)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement has_signal + extract_conventions + review_candidates</name>
  <files>voss/harness/conventions.py, tests/harness/test_conventions.py</files>
  <read_first>
    - voss/harness/conventions.py (Wave-0 skeleton — _SIGNAL_RE + ConventionCandidate concrete; 4 function stubs)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/conventions.py (NEW)"
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §D-09, §D-10, §D-11, §D-12
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §Pitfall 5 (tight signal threshold recommendation)
    - voss/harness/skills/analyze.py:44-57 (asyncio.run(run_turn(...)) idiom for one-shot LLM calls)
    - voss/harness/agent.py run_turn signature (verify provider+model+history+tools kwargs for the extraction call)
    - voss/harness/cli.py lines 773-778 (EOFError/KeyboardInterrupt input pattern for review UI; pattern E from PATTERNS.md)
    - tests/harness/test_conventions.py (Wave-0 stub — remove module-level skip)
  </read_first>
  <behavior>
    - has_signal([{"role": "user", "content": "no use 2 spaces"}, ...]) -> True (matches _SIGNAL_RE on first user turn).
    - has_signal([{"role": "user", "content": "summarize the repo"}]) -> False (no signal).
    - has_signal([], runs=[]) -> False; has_signal(turns, runs=[run_with_changed=["a.py","a.py"]]) -> True (repeat-edit-same-target signal hit — same file in two run.changed lists).
    - Pitfall 5 tightening: has_signal returns True only when (a) _SIGNAL_RE hits ≥1 user turn AND total user-turn count ≥ 2, OR (b) repeat-edit-same-target detected with ≥ 2 runs sharing a changed file. This avoids firing on every single-turn "use X" prompt.
    - extract_conventions(history, provider, model, *, timeout=8.0) returns list[ConventionCandidate] when the LLM call returns within timeout and JSON validates; returns [] on asyncio.TimeoutError; returns [] on pydantic ValidationError; returns [] on provider exceptions (logged to stderr).
    - The extraction prompt explicitly asks the LLM to emit a JSON array conforming to ConventionCandidate's fields; the function parses provider response text as JSON and runs ConventionCandidate.model_validate on each element.
    - review_candidates([cand1, cand2], interactive=True) prints to click.echo numbered list per D-11 format ("[1] <statement>  (conf 0.NN)\n      evidence: \"<quote>\" (turn N)"); reads one line from input(); empty/EOFError/KeyboardInterrupt -> returns []; "1" -> returns [0]; "1 3" -> returns [0, 2] (1-based to 0-based; out-of-range indices silently dropped).
    - review_candidates(candidates, interactive=False, selection="1 3") returns [0, 2] without touching stdin.
    - review_candidates(candidates, interactive=False, selection=None) returns [] (non-interactive mode without explicit selection persists nothing — Req 4 acceptance for piped/CI use).
  </behavior>
  <action>
    (a) In voss/harness/conventions.py replace the four stub functions:
    - has_signal(turns, *, runs=None) -> bool: enumerate user turns (filter turn.role == "user" OR turn["role"] == "user" — tolerate both Turn dataclass and dict forms via getattr-with-fallback); signal_a = any(_SIGNAL_RE.search(t.content if hasattr(t,'content') else t.get("content","")) for t in user_turns); signal_b = False; if runs: from collections import Counter; changed_files = Counter(); for run in runs: changed = getattr(run, "changed", None) or (run.get("changed") if isinstance(run, dict) else []) or []; for f in changed: changed_files[f] += 1; signal_b = any(c >= 2 for c in changed_files.values()); return (signal_a and len(user_turns) >= 2) or signal_b. (Pitfall 5 tightening.)
    - extract_conventions(history, provider, model, *, timeout=DEFAULT_EXTRACTION_TIMEOUT_SECONDS) -> list[ConventionCandidate]: async function. Build an extraction prompt that instructs the LLM to read the conversation and emit a strict JSON array of candidate conventions, each with {statement, confidence (0..1), evidence_quote (verbatim user quote), evidence_turn_idx (int)}. The prompt should require the LLM to respond ONLY with the JSON array, no prose. Render the history turns into the prompt body (use existing EpisodicMemory.render() if history is an EpisodicMemory; else format turns by hand). Call asyncio.wait_for(provider.complete(prompt, model=model), timeout=timeout). On TimeoutError return []. On any exception, log to stderr and return []. Parse the response text as JSON via json.loads (wrap in try/except json.JSONDecodeError -> []); validate each element via ConventionCandidate.model_validate (wrap in try/except ValidationError -> []); return the validated list.
    - review_candidates(candidates, *, interactive=True, selection=None) -> list[int]: if not candidates: return []. If not interactive: if selection is None: return []; else parse selection: indices = [int(x) - 1 for x in selection.split() if x.strip().isdigit()]; return [i for i in indices if 0 <= i < len(candidates)]. If interactive: print header "Candidate conventions from this session:" via click.echo; for i, c in enumerate(candidates, start=1): click.echo(f"  [{i}] {c.statement}  (conf {c.confidence:.2f})"); click.echo(f'      evidence: "{c.evidence_quote}" (turn {c.evidence_turn_idx})'); try: raw = input('Persist which? (e.g. "1 3", or empty for none): '); except (EOFError, KeyboardInterrupt): click.echo(); return []. Parse same as non-interactive selection path.

    (b) In tests/harness/test_conventions.py remove module-level pytestmark.skip. Implement 5 tests:
    - test_scripted_signal_session_surfaces_candidate: build a fake history with 3 turns including user content "no use snake_case in Python" (signal hits) AND 2 user turns total (signal_a quorum); mock provider.complete via AsyncMock returning a JSON string `'[{"statement": "Use snake_case in Python", "confidence": 0.82, "evidence_quote": "no use snake_case in Python", "evidence_turn_idx": 0}]'`; call await extract_conventions(history, provider, "fake-model"); assert returned list has 1 ConventionCandidate with .statement == "Use snake_case in Python".
    - test_decline_writes_nothing: build candidates list with 1 item; call review_candidates(candidates, interactive=False, selection=None); assert returned == [].
    - test_accept_writes_one_file_with_evidence: use tmp_voss_repo + MemoryStore from M8-03; build 1 ConventionCandidate; call review_candidates(candidates, interactive=False, selection="1"); assert returned == [0]; then call memory_store.write_convention(candidates[0], session_id="s1"); assert resulting file exists, contains the statement, contains "Evidence" section, contains evidence_quote verbatim, has frontmatter with related_session and evidence_turn_idx and confidence fields.
    - test_no_signal_skips_llm_entirely: build a history with 1 user turn "summarize the repo" (no signal, no quorum); assert has_signal(turns) returns False. Patch extract_conventions to fail loudly if called; call has_signal-gated code path explicitly: if not has_signal(turns): result = []; assert result == [].
    - test_extraction_timeout_returns_empty: mock provider.complete via AsyncMock with a side_effect of asyncio.sleep(2.0) (longer than the override timeout); call await extract_conventions(history, provider, "fake-model", timeout=0.1); assert returned == []; assert no exception escaped.

    Use pytest-asyncio (asyncio_mode=auto per RESEARCH §Validation Architecture) for async tests; verify the project uses pytest-asyncio by reading pyproject.toml or existing async test files (tests/harness/ likely has analog patterns — grep for "pytestmark = pytest.mark.asyncio" or "@pytest.mark.asyncio").
  </action>
  <verify>
    <automated>pytest tests/harness/test_conventions.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - All 5 tests in test_conventions.py GREEN.
    - `grep -v '^#' voss/harness/conventions.py | grep -c "NotImplementedError"` returns 0 except inside run_on_clean_exit (still owned by Task 2 of this plan).
    - Actually: by end of Task 2, that count must be 0; for Task 1 acceptance, count must be ≤ 1 (only run_on_clean_exit remains).
    - `python -c "from voss.harness.conventions import has_signal; assert has_signal([{'role':'user','content':'no use 2 spaces'}, {'role':'user','content':'always use them'}]) is True"` succeeds.
    - `python -c "from voss.harness.conventions import has_signal; assert has_signal([{'role':'user','content':'summarize'}]) is False"` succeeds.
    - `python -c "from voss.harness.conventions import review_candidates; assert review_candidates([], interactive=False, selection='1') == []"` succeeds (empty input is empty output).
  </acceptance_criteria>
  <done>
    Pre-filter has D-09 + Pitfall 5 tightening; extract_conventions handles timeout and validation failures silently; review_candidates supports both interactive and non-interactive selection. 5 conventions tests green.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement run_on_clean_exit + wire into _run_repl and do_cmd exit paths</name>
  <files>voss/harness/conventions.py, voss/harness/cli.py, tests/harness/test_conventions.py</files>
  <read_first>
    - voss/harness/conventions.py (Task 1 of this plan filled; only run_on_clean_exit stub remains)
    - voss/harness/cli.py lines 773-778 (REPL EOFError/KeyboardInterrupt exit branch — clean-exit path)
    - voss/harness/cli.py lines 540-547 (do_cmd post-run_turn path — A6 says this also gets the hook)
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §D-12 (timeout config), §D-11 (review UX)
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §A6 (RESOLVED — both REPL and do_cmd get the hook)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/cli.py" §"REPL exit hook for conventions"
    - voss/harness/session.py SessionRecord shape (for record.runs access)
  </read_first>
  <behavior>
    - run_on_clean_exit(ctx, *, history, record, memory_store) -> int: returns count of conventions persisted (0..N).
    - When has_signal(history.turns, runs=record.runs) returns False: function returns 0 immediately; no LLM call, no review prompt, no stdout output.
    - When has_signal returns True: function calls asyncio.run(extract_conventions(history, ctx.provider, ctx.model, timeout=ctx.config.memory_extraction_timeout if available else DEFAULT_EXTRACTION_TIMEOUT_SECONDS)); on empty list, return 0; on non-empty list, call review_candidates(candidates, interactive=sys.stdin.isatty()); for each selected index, call memory_store.write_convention(candidates[idx], session_id=record.id); return len(selected).
    - The configuration toggle `memory.extract_conventions: false` (set in .voss/config.yml if present) short-circuits to return 0 before any work. Reading config: gracefully handle absence — if .voss/config.yml doesn't exist OR doesn't contain the memory section, default to enabled. Use pyyaml.safe_load.
    - Any exception inside run_on_clean_exit is caught and logged to stderr with one line "conventions extraction skipped: <reason>"; the function returns 0; the REPL exit is NEVER blocked.
    - In _run_repl's EOFError/KeyboardInterrupt branch, the call is wrapped in try/except so a thrown exception still allows the REPL to return cleanly.
    - In do_cmd post-run_turn path, run_on_clean_exit is called after the run_turn awaitable completes successfully (NOT in the exception branch — error-exit skips per Req 4 acceptance).
  </behavior>
  <action>
    (a) In voss/harness/conventions.py implement run_on_clean_exit:
    - Imports: import asyncio, sys, click, from pathlib import Path; defensive import of yaml inside the function for the config read (handles pyyaml missing — though it's a core dep, defensive is cheap).
    - Read config: cwd = getattr(ctx, "cwd", None) or Path("."); config_path = cwd / ".voss" / "config.yml"; if config_path.exists(): try: cfg = yaml.safe_load(config_path.read_text()) or {}; except Exception: cfg = {}; else: cfg = {}. extract_enabled = cfg.get("memory", {}).get("extract_conventions", True); timeout = float(cfg.get("memory", {}).get("extraction_timeout_seconds", DEFAULT_EXTRACTION_TIMEOUT_SECONDS)).
    - If not extract_enabled: return 0.
    - turns = list(getattr(history, "turns", history) or []); runs = list(getattr(record, "runs", []) or []); if not has_signal(turns, runs=runs): return 0.
    - Resolve provider + model from ctx: provider = getattr(ctx, "provider", None); model = getattr(ctx, "model", None) or getattr(ctx, "default_model", None); if provider is None or model is None: click.echo("conventions extraction skipped: no provider/model on ctx", err=True); return 0.
    - candidates = asyncio.run(extract_conventions(history, provider, model, timeout=timeout)); if not candidates: return 0.
    - interactive = sys.stdin.isatty(); selected_idxs = review_candidates(candidates, interactive=interactive, selection=getattr(ctx, "persist_conventions_selection", None));
    - persisted = 0; for idx in selected_idxs: try: memory_store.write_convention(candidates[idx], session_id=record.id); persisted += 1; except Exception as exc: click.echo(f"conventions write failed for [{idx+1}]: {exc}", err=True). Return persisted.
    - Wrap the WHOLE body inside a top-level try/except Exception that emits "conventions extraction skipped: <exc>" to stderr and returns 0. Never re-raise.

    (b) In voss/harness/cli.py:
    - Add `from . import conventions` to top-of-file imports if not present.
    - In _run_repl, locate the EOFError/KeyboardInterrupt exit branch (cli.py:773-778). Replace the bare `return` after the click.echo() with: try: conventions.run_on_clean_exit(ctx, history=ctx.history, record=record, memory_store=ctx.memory_store); except Exception as exc: click.echo(f"conventions extraction skipped: {exc}", err=True); finally: return. The ctx already has memory_store attached via M8-03's _run_repl boot wires (verify: M8-03 should have set ctx.memory_store; if not yet wired, this plan adds `ctx.memory_store = MemoryStore(cwd).bind(session_id=record.id)` before the REPL loop starts — it's a one-line add adjacent to the existing M8-01 voss_md.read_and_inject line).
    - In do_cmd, locate the path AFTER the successful run_turn completion (around cli.py:540-547; specifically AFTER the asyncio.run(run_turn(...)) call returns and the run is recorded). Insert: try: conventions.run_on_clean_exit(do_ctx_or_namespace, history=do_history, record=do_record, memory_store=do_memory_store); except Exception as exc: click.echo(f"conventions extraction skipped: {exc}", err=True). The do_cmd local variable names may differ from the REPL — read cli.py:511-547 to identify the actual local names; thread them in equivalently. Build a SimpleNamespace if the do_cmd doesn't have a ctx-like object; the run_on_clean_exit signature only needs .provider, .model, .cwd as attributes.
    - In do_cmd, the do_cmd also needs a memory_store binding (parallel to M8-03's REPL wiring) — add `do_memory_store = MemoryStore(cwd).bind(session_id=do_record.id)` adjacent to the M8-01 voss_md.read_and_inject(cwd) call in do_cmd.

    (c) Extend tests/harness/test_conventions.py with one additional test test_run_on_clean_exit_smoke:
    - Use tmp_voss_repo + MemoryStore + a SimpleNamespace ctx with .provider=AsyncMock returning a valid 1-candidate JSON array, .model="fake", .cwd=tmp_voss_repo;
    - Build a fake history with 2 user turns, one containing "no use 2 spaces";
    - Build a fake record with .id = "test-session", .runs = [];
    - Call run_on_clean_exit(ctx, history=history, record=record, memory_store=store) with monkeypatched sys.stdin.isatty() -> False AND ctx.persist_conventions_selection="1";
    - Assert returned == 1; assert one file landed under tmp_voss_repo/.voss/memory/conventions/.
  </action>
  <verify>
    <automated>pytest tests/harness/test_conventions.py -x -q && pytest tests/harness/ -x --timeout=120 -q</automated>
  </verify>
  <acceptance_criteria>
    - All 6 tests in test_conventions.py GREEN (5 from Task 1 + smoke test).
    - `grep -v '^#' voss/harness/conventions.py | grep -c "NotImplementedError"` returns 0 (all stubs replaced).
    - `grep -nE "conventions\\.run_on_clean_exit" voss/harness/cli.py` returns ≥ 2 matches (one in _run_repl exit branch, one in do_cmd post-run).
    - `python -c "from voss.harness.conventions import run_on_clean_exit; import inspect; assert 'memory_store' in inspect.signature(run_on_clean_exit).parameters"` succeeds.
    - Full harness suite green: `pytest tests/harness/ -x --timeout=120`.
    - Manual smoke (NOT part of automated verify but documented): running `voss chat` and exiting via Ctrl-D in a tmp repo with a signal-bearing user turn produces the candidate review prompt; declining returns 0; accepting writes the convention file.
  </acceptance_criteria>
  <done>
    run_on_clean_exit fully implemented with config-driven enable/timeout, both REPL and do_cmd clean-exit paths wired, robust try/except wrapping to never block REPL exit. MEM-04 acceptance criteria all met.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM JSON output -> ConventionCandidate.model_validate | pydantic V5 input validation guarantees no path-traversal or other malformed content flows through; ValidationError treated as silent skip |
| stdin selection input -> review_candidates parser | only int parsing; out-of-range indices dropped; no shell interpolation |
| .voss/config.yml -> extract_enabled + timeout | safe_load (no Python object instantiation); defaults to safe values when key missing or file unreadable |
| extraction LLM call -> token cost | Pitfall 5 risk: every clean exit fires a paid call; mitigated by tightened has_signal quorum |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M8-04-01 | Information Disclosure | LLM call sends full session history to provider | accept | matches existing voss do/voss chat data-flow; user is already opted in by running voss; user can disable via memory.extract_conventions: false |
| T-M8-04-02 | Denial of Service | malformed LLM output (non-JSON) crashes extraction | mitigate | json.JSONDecodeError caught -> returns [] |
| T-M8-04-03 | Denial of Service | extraction LLM call hangs indefinitely, blocks REPL exit | mitigate | asyncio.wait_for(timeout=8.0) — Pitfall 5 + D-12; on TimeoutError returns [] |
| T-M8-04-04 | Tampering | path traversal via candidate.statement -> slug | mitigate | cognition.slug() strips non-alphanumeric and bounds length; reserve_filename always rooted at conventions/ dir |
| T-M8-04-05 | Repudiation | extraction failure swallows reason, user doesn't know why no candidates | accept | stderr one-liner "conventions extraction skipped: <reason>"; not blocking REPL is the higher priority |
| T-M8-04-06 | Denial of Service | Pitfall 5: every clean exit burns tokens | mitigate | has_signal quorum tightening (≥2 user turns AND signal match, OR repeat-edit ≥2); review_candidates default in non-interactive mode is "persist none" |
</threat_model>

<verification>
- `pytest tests/harness/test_conventions.py -x` (6 tests green)
- `pytest tests/harness/ -x --timeout=120` (no regression)
- `grep -v '^#' voss/harness/conventions.py | grep -c "NotImplementedError"` returns 0
- `grep -nE "conventions\\.run_on_clean_exit" voss/harness/cli.py` returns ≥ 2 matches
</verification>

<success_criteria>
- has_signal honors D-09 + Pitfall 5 quorum.
- extract_conventions wraps LLM call in asyncio.wait_for(8.0); returns [] on timeout, JSON-decode error, validation error, provider exception.
- review_candidates implements D-11 numbered-list UX; interactive AND non-interactive selection modes; declining returns [].
- run_on_clean_exit reads .voss/config.yml for memory.extract_conventions + extraction_timeout_seconds; defaults sane.
- Both _run_repl exit branch AND do_cmd post-run wire run_on_clean_exit (A6 resolved).
- Exceptions inside run_on_clean_exit never block REPL exit (defensive try/except wraps whole body).
- 6 conventions tests + full harness suite GREEN.
</success_criteria>

<output>
After completion, create `.planning/phases/M8-project-memory-mem-01/M8-04-SUMMARY.md` summarizing:
- has_signal quorum (≥2 user turns + regex match, OR repeat-edit ≥2)
- extract_conventions failure modes (timeout, JSON-decode, validation, provider exception) all return []
- review_candidates interactive/non-interactive parity
- run_on_clean_exit config-driven enable/timeout; defensive try/except
- Wire points: _run_repl exit branch + do_cmd post-run + memory_store binding in do_cmd
- Pitfall 5 mitigation
- Deviations from plan
</output>
