---
phase: M8
plan: 01
type: execute
wave: 2
depends_on: [M8-00]
files_modified:
  - voss/harness/voss_md.py
  - voss/harness/cli.py
  - voss/harness/agent.py
  - tests/harness/test_voss_md_fence.py
  - tests/harness/test_voss_md_injection.py
autonomous: true
requirements: [MEM-01]
tags: [memory, voss-md, system-context]
must_haves:
  truths:
    - "voss_md.parse() splits VOSS.md into human + machine Block sequences with id and recorded_hash extracted"
    - "voss_md.read_and_inject(cwd) returns the verbatim bytes of cwd/VOSS.md or None if missing (silent degradation per D-08)"
    - "voss_md.read_fence_body(path, fence_id) raises HashMismatch when recorded hash != computed sha256 of fence body (D-07)"
    - "voss_md.write_fence_body(path, fence_id, body) preserves all human-owned content outside the targeted fence and rewrites the hash header"
    - "voss chat / voss do / voss resume all inject `# VOSS.md\\n<bytes>` as the head block of sys_prompt before cognition_text (D-08)"
    - "Absence of VOSS.md on disk produces no error, no section, no log line (Req 1 silent-degradation acceptance)"
  artifacts:
    - path: "voss/harness/voss_md.py"
      provides: "Behavior for parse, read_and_inject, read_fence_body, write_fence_body, machine_fence_path_or_marker, HashMismatch"
    - path: "voss/harness/cli.py"
      provides: "REPL boot wires: voss_md_text = voss_md.read_and_inject(cwd); passed through to run_turn; do_cmd path also calls read_and_inject"
    - path: "voss/harness/agent.py"
      provides: "run_turn accepts voss_md_text kwarg; sys_prompt assembly prepends '# VOSS.md\\n<text>' block when text is non-None"
  key_links:
    - from: "voss/harness/cli.py::_run_repl"
      to: "voss_md.read_and_inject"
      via: "boot-time read; passed through run_turn calls in REPL loop"
      pattern: "voss_md\\.read_and_inject\\(cwd\\)"
    - from: "voss/harness/cli.py::do_cmd"
      to: "voss_md.read_and_inject"
      via: "one-shot read before run_turn"
      pattern: "voss_md\\.read_and_inject\\(cwd\\)"
    - from: "voss/harness/agent.py::run_turn"
      to: "sys_prompt"
      via: "f-string prepend of '# VOSS.md\\n{voss_md_text}' onto join tuple"
      pattern: "# VOSS\\.md"
---

<objective>
Land MEM-01: VOSS.md loader + system-context injection on every harness entry (`voss chat`, `voss do`, `voss resume`). Convert the Wave-0 NotImplementedError skeleton in voss/harness/voss_md.py into a working parser (Block list, hash-guarded fence read/write) and a `read_and_inject(cwd) -> str | None` function. Wire `_run_repl` + `do_cmd` to read VOSS.md once at boot and pass the bytes through to `run_turn`, where sys_prompt assembly prepends a `# VOSS.md\n<bytes>` block before the existing cognition_text block.

Purpose: Without this plan, the agent never sees the human-curated project guide. With it, every session starts with the same bytes the human reads — D-08 contract.
Output: Working voss_md.py (parse / read_and_inject / read_fence_body / write_fence_body / machine_fence_path_or_marker / HashMismatch), 2 REPL boot edits in cli.py, 1 sys_prompt assembly edit in agent.py, two test files un-skipped and asserting against the new behavior.
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
@.planning/phases/M8-project-memory-mem-01/M8-00-SUMMARY.md
@voss/harness/voss_md.py
@voss/harness/cli.py
@voss/harness/agent.py
@voss/harness/cognition.py

<interfaces>
<!-- Required identifiers/signatures established by M8-00 (Wave 0) and existing code. -->

voss/harness/voss_md.py (Wave-0 skeleton — this plan fills behavior):
- FENCE_BEGIN, FENCE_HASH, FENCE_END (re.compile patterns already defined as constants in Wave 0)
- @dataclass(frozen=True) class Block(kind: str, id: str | None, body: str, recorded_hash: str | None)
- class HashMismatch(Exception) constructed via HashMismatch(fence_id, *, recorded, actual, on_disk)
- Function signatures (NotImplementedError bodies replaced in this plan):
  - parse(text: str) -> list[Block]
  - read_and_inject(cwd: Path) -> str | None
  - read_fence_body(path: Path, *, fence_id: str) -> str | None
  - write_fence_body(path: Path, *, fence_id: str, body: str) -> None
  - machine_fence_path_or_marker(cwd: Path, *, fence_id: str) -> Path
  - ensure_migrated(cwd: Path) -> bool   # remains NotImplementedError after this plan — owned by M8-02

voss/harness/agent.py existing run_turn signature (extend with new kwarg):
- async def run_turn(task: str, *, tools, cwd, renderer, model, history, permissions, provider, session_id, cognition=None, prior_context=None) -> TurnResult
- sys_prompt assembly at ~agent.py:297-299: sys_prompt = "\n\n".join(s for s in (cognition_text, prior_context_text, PLAN_SYSTEM) if s)

voss/harness/cli.py wire points (per PATTERNS.md):
- _run_repl boot init around cli.py:705-717 (slash_registry build + cognition_mod.load call)
- do_cmd one-shot path around cli.py:511-547 (calls run_turn directly, not via _run_repl)
- run_turn invocation in REPL loop around cli.py:809-822 (existing kwargs cognition, prior_context, etc.)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement voss_md.parse + read_and_inject + read_fence_body + write_fence_body</name>
  <files>voss/harness/voss_md.py, tests/harness/test_voss_md_fence.py</files>
  <read_first>
    - voss/harness/voss_md.py (Wave-0 skeleton — signatures + regex constants)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/voss_md.py" (full — Block dataclass + parse loop + write helpers)
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Pattern 1: VOSS.md fence parse + hash guard"
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §"VOSS.md sections + COG-02 rewrite" (D-05, D-07, D-08)
    - voss/harness/cognition.py lines 30-50 (FRONTMATTER_RE precedent + never-raises loader idiom)
    - tests/harness/test_voss_md_fence.py (Wave-0 skipped stub — remove module-level skip in this task)
  </read_first>
  <behavior>
    - parse("hello") -> [Block(kind="human", id=None, body="hello", recorded_hash=None)]
    - parse with a single machine fence `<!-- voss:begin id=architecture -->\n<!-- voss:hash <64hex> -->\nbody\n<!-- voss:end id=architecture -->\n` -> two Blocks: human prefix (possibly empty) + machine Block(id="architecture", body="body\n", recorded_hash="<64hex>")
    - parse interleaved human + machine blocks preserves order and never drops bytes (sum of body lengths equals input length modulo fence markers)
    - read_and_inject(cwd) returns cwd/VOSS.md bytes verbatim when file exists; returns None when absent (no exception, no log)
    - read_fence_body(path, fence_id="architecture") returns body string when fence exists; returns None when fence id absent in the file; raises HashMismatch(fence_id, recorded, actual, on_disk) when recorded hash != sha256(body)
    - write_fence_body(path, fence_id="architecture", body="new body") preserves all human-owned content outside the fence; rewrites the hash header to sha256(new body); appends a new fence at EOF when fence id does not yet exist in the file
    - HashMismatch raised by read_fence_body on a tampered file is catchable; .recorded, .actual, .on_disk, .fence_id attributes all populated
    - machine_fence_path_or_marker(cwd, fence_id="architecture") returns cwd / "VOSS.md" (Path) regardless of fence existence — caller decides what to do with absence
  </behavior>
  <action>
    Implement the six functions in voss/harness/voss_md.py per behavior block. Constraints:
    - parse() must use a line-by-line scan with FENCE_BEGIN / FENCE_HASH / FENCE_END regexes matching the LINE.STRIP() form (machine markers can appear with or without trailing whitespace). The accumulator pattern from PATTERNS.md `def parse` is the template — copy its structure.
    - read_and_inject() must use Path.exists() guard + Path.read_text() in a try/except (OSError, UnicodeDecodeError) returning None on any read error. NO exception escapes.
    - read_fence_body() must call parse(), iterate blocks, return body for matching id. If block.recorded_hash is not None, compute hashlib.sha256(block.body.encode()).hexdigest() and compare; raise HashMismatch on inequality.
    - write_fence_body() implements the D-07 contract: parse current text; if fence exists, validate hash on the existing body BEFORE writing (raise HashMismatch if drifted); render replacement fence (with new hash header) into the block list; serialize blocks back to text via a `_render` helper; write atomically (write to <path>.tmp then os.replace(<path>.tmp, <path>) — match the atomic-write idiom from RESEARCH §"Don't Hand-Roll" `sandbox.write`). If fence does not exist, append a new fully-formed fence (`<!-- voss:begin id=<id> -->\n<!-- voss:hash <hash> -->\n<body>\n<!-- voss:end id=<id> -->\n`) to EOF.
    - machine_fence_path_or_marker() is a one-liner: `return cwd / "VOSS.md"`.
    - HashMismatch must store fence_id, recorded, actual, on_disk as instance attributes (not just positional args). __str__ returns a developer-readable summary mentioning fence_id and short hashes (first 16 chars).

    In tests/harness/test_voss_md_fence.py: remove the module-level `pytestmark = pytest.mark.skip(...)` line. Fill in the four test bodies:
    - test_parse_human_blocks: parse plain markdown, assert single Block(kind="human", id=None, body=<original text>).
    - test_parse_machine_blocks: parse a string containing one valid fence, assert list of 2 or 3 Blocks (human prefix, machine block, optional human suffix), assert machine block id, body, recorded_hash.
    - test_hash_mismatch_raises: write a VOSS.md fence with body "X" but record hash of "Y"; call read_fence_body, assert HashMismatch raised with .fence_id, .recorded, .actual populated; .actual must equal sha256("X").hexdigest().
    - test_write_fence_body_round_trip: start from a VOSS.md with one human prose paragraph + one machine fence (body "original"); call write_fence_body(path, fence_id=<id>, body="updated"); re-read file; assert human paragraph preserved verbatim; assert read_fence_body returns "updated"; assert sha256("updated") matches the new recorded hash.
  </action>
  <verify>
    <automated>pytest tests/harness/test_voss_md_fence.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - All 4 tests in test_voss_md_fence.py are GREEN (module-level skip removed).
    - `python -c "from voss.harness.voss_md import parse; assert parse('hi') == [__import__('voss.harness.voss_md', fromlist=['Block']).Block(kind='human', id=None, body='hi', recorded_hash=None)]"` succeeds.
    - `python -c "from pathlib import Path; from voss.harness.voss_md import read_and_inject; assert read_and_inject(Path('/nonexistent-path-zzz')) is None"` succeeds (silent degradation invariant).
    - `python -c "from voss.harness.voss_md import HashMismatch; e = HashMismatch('architecture', recorded='a'*64, actual='b'*64, on_disk='body'); assert e.fence_id == 'architecture' and e.recorded == 'a'*64 and e.actual == 'b'*64 and e.on_disk == 'body'"` succeeds.
    - `grep -v '^#' voss/harness/voss_md.py | grep -c "NotImplementedError"` returns at most 1 (only ensure_migrated remains a stub for M8-02).
    - Atomic-write invariant: `grep -nE "os\\.replace|\\.rename\\(" voss/harness/voss_md.py` returns ≥ 1 match in write_fence_body.
  </acceptance_criteria>
  <done>
    parse / read_and_inject / read_fence_body / write_fence_body / machine_fence_path_or_marker / HashMismatch all behave per D-05/D-07/D-08. ensure_migrated remains NotImplementedError (owned by M8-02). Four fence-parser tests green. Atomic writes guaranteed via temp + os.replace.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire voss_md.read_and_inject into _run_repl + do_cmd + run_turn sys_prompt</name>
  <files>voss/harness/cli.py, voss/harness/agent.py, tests/harness/test_voss_md_injection.py</files>
  <read_first>
    - voss/harness/cli.py lines 511-547 (do_cmd one-shot path)
    - voss/harness/cli.py lines 688-834 (_run_repl boot init + REPL loop + run_turn invocation)
    - voss/harness/agent.py lines 230-320 (run_turn signature + _compose_cognition_prompt + sys_prompt join)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/cli.py (MODIFIED)" + §"voss/harness/agent.py (MODIFIED)"
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §Pitfall 5 ("loose extraction trigger" — N/A here) + A2 (single REPL entry confirmed)
    - tests/harness/test_voss_md_injection.py (Wave-0 stub — remove module-level skip)
  </read_first>
  <behavior>
    - run_turn(..., voss_md_text="# guide\nproject rules") composes sys_prompt with "# VOSS.md\n# guide\nproject rules" as the FIRST joined block (before cognition_text, before prior_context_text, before PLAN_SYSTEM).
    - run_turn(..., voss_md_text=None) composes sys_prompt without any VOSS.md block (existing behavior preserved exactly — Pitfall 6 backward-compat).
    - When _run_repl boots in a cwd containing VOSS.md with bytes "alpha", the provider call inside the first turn receives a system message whose body contains the substring "# VOSS.md\nalpha".
    - When _run_repl boots in a cwd WITHOUT VOSS.md, the provider call's system message does NOT contain "# VOSS.md" at all.
    - When do_cmd("summarize", cwd=<cwd-with-VOSS.md>) runs, the same injection fires (per A3 + A6).
    - VOSS.md is read ONCE at boot (before the REPL loop starts), not per-turn. The same voss_md_text string is passed through every run_turn call for the session lifetime.
  </behavior>
  <action>
    (a) In voss/harness/agent.py: extend run_turn signature with `voss_md_text: str | None = None` as a new keyword-only argument (place it adjacent to existing `cognition` / `prior_context` kwargs to preserve alphabetical / logical grouping). In the sys_prompt assembly join (currently `sys_prompt = "\n\n".join(s for s in (cognition_text, prior_context_text, PLAN_SYSTEM) if s)`), prepend a voss_md_block computed as `f"# VOSS.md\n{voss_md_text}" if voss_md_text else ""` to the tuple — new order: `(voss_md_block, cognition_text, prior_context_text, PLAN_SYSTEM)`. The `if s` filter handles the None-block case (empty string falsy, gets dropped).

    (b) In voss/harness/cli.py::_run_repl (around cli.py:717, after `bundle = cognition_mod.load(cwd, token_count=_tok_count)`): insert `voss_md_text = voss_md.read_and_inject(cwd)` and attach to the ReplContext (add a new field `voss_md_text: str | None = None` to the ReplContext dataclass — locate the dataclass definition via grep first). In the run_turn call inside the REPL loop (around cli.py:809-822), add `voss_md_text=ctx.voss_md_text` to the kwargs.

    (c) In voss/harness/cli.py::do_cmd (around cli.py:540, where `do_bundle = cognition_mod.load(cwd)` lives): insert `voss_md_text = voss_md.read_and_inject(cwd)` after the bundle load. Add `voss_md_text=voss_md_text` to the run_turn call inside do_cmd.

    (d) Add `from . import voss_md` to the imports at the top of voss/harness/cli.py if not already present.

    (e) In tests/harness/test_voss_md_injection.py: remove the module-level pytestmark.skip. Implement the two tests:
    - test_voss_md_loaded_in_system_context: use tmp_voss_repo fixture to create a VOSS.md at the repo root with bytes "alpha-marker-XYZ". Drive a one-turn run_turn via a FakeProvider that captures the system message it receives (FakeProvider pattern lives in tests/harness/ — grep for "FakeProvider" to find the helper; if none exists use unittest.mock.AsyncMock on the provider.complete method to capture call kwargs). Assert "# VOSS.md\nalpha-marker-XYZ" is a substring of the captured system message.
    - test_missing_file_degrades_silently: same setup but do NOT create VOSS.md. Drive run_turn the same way. Assert no exception raised; assert captured system message does NOT contain the literal "# VOSS.md" anywhere; assert no stderr output mentions "VOSS.md".
  </action>
  <verify>
    <automated>pytest tests/harness/test_voss_md_injection.py -x -q && pytest tests/harness/test_voss_md_fence.py tests/harness/test_repl_slash.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Both tests in test_voss_md_injection.py GREEN.
    - `grep -n "voss_md_text" voss/harness/agent.py` returns ≥ 2 matches (signature + assembly).
    - `grep -n "voss_md.read_and_inject" voss/harness/cli.py` returns ≥ 2 matches (one in _run_repl, one in do_cmd).
    - `grep -n "voss_md_text=" voss/harness/cli.py` returns ≥ 2 matches (passed through both run_turn calls).
    - `python -c "import inspect; from voss.harness.agent import run_turn; sig = inspect.signature(run_turn); assert 'voss_md_text' in sig.parameters and sig.parameters['voss_md_text'].default is None"` succeeds.
    - Pre-existing test_repl_slash.py is still GREEN (no regression in slash registry).
    - `grep -nE "^# VOSS\\.md" voss/harness/agent.py` returns ≥ 1 match in the voss_md_block construction.
  </acceptance_criteria>
  <done>
    All three entry points (`voss chat`, `voss do`, `voss resume`) inject VOSS.md as the head sys_prompt block via a single shared `read_and_inject` call at boot. Backward compat preserved when file absent. Injection test exercised end-to-end via captured provider call.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| disk file VOSS.md -> agent sys_prompt | human-edited content crosses into the LLM context; user-owned, treated as trusted (matches existing .voss/architecture.md trust model from M2) |
| disk fence body bytes -> sha256 hash | recorded hash header is integrity-not-authenticity; protects against accidental clobber, not against malicious local actors |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M8-01-01 | Tampering | partial write of VOSS.md crashes mid-write | mitigate | write_fence_body uses temp file + os.replace (atomic rename); grep gate in acceptance_criteria enforces presence |
| T-M8-01-02 | Information Disclosure | VOSS.md contents may include sensitive project details | accept | content is user-curated and user-readable; same risk model as M2 architecture.md; no new persistence created |
| T-M8-01-03 | Tampering | corrupted hash header tricks loader into trusting drifted body | mitigate | D-07 contract: read_fence_body raises HashMismatch when recorded != actual; test_hash_mismatch_raises pins this from Task 1 |
| T-M8-01-04 | Denial of Service | giant VOSS.md inflates sys_prompt and blows provider context budget | accept | budget enforcement is the provider's job; v0.1 has no automatic truncation; document in future M8.x if signals surface |
| T-M8-01-05 | Spoofing | symlink at VOSS.md points outside cwd | accept | path jail is .voss/ + tool-call scoped per CTRL-06; root-level VOSS.md is part of the user's own repo by definition |
</threat_model>

<verification>
- `pytest tests/harness/test_voss_md_fence.py tests/harness/test_voss_md_injection.py -x` (M8-01 acceptance)
- `pytest tests/harness/ -x --timeout=60` (full harness regression — no regression in existing tests)
- `python -c "from voss.harness.voss_md import parse, read_and_inject, read_fence_body, write_fence_body, machine_fence_path_or_marker, HashMismatch"` (full surface importable)
</verification>

<success_criteria>
- voss/harness/voss_md.py implements parse, read_and_inject, read_fence_body, write_fence_body, machine_fence_path_or_marker, HashMismatch with behavior matching D-05/D-07/D-08.
- ensure_migrated remains a NotImplementedError stub awaiting M8-02.
- _run_repl and do_cmd both call voss_md.read_and_inject(cwd) at boot.
- run_turn accepts voss_md_text kwarg and prepends "# VOSS.md\n<text>" to sys_prompt when non-None.
- All four fence parser tests + both injection tests are green.
- Pre-existing tests/harness/ tests still green (no slash-registry regression, no session-load regression).
- File-absent path produces NO error and NO "# VOSS.md" section.
- Hash-mismatch raises HashMismatch with all four attributes populated.
</success_criteria>

<output>
After completion, create `.planning/phases/M8-project-memory-mem-01/M8-01-SUMMARY.md` summarizing:
- voss_md.py public-API behavior (parse, read_and_inject, read_fence_body, write_fence_body, machine_fence_path_or_marker, HashMismatch)
- Wire points landed: _run_repl boot, do_cmd boot, run_turn sys_prompt prepend
- Atomic-write strategy used (temp + os.replace)
- Backward-compat invariants preserved (file-absent silent degradation; existing run_turn callers unbroken since voss_md_text defaults to None)
- Surface ready for M8-02 (ensure_migrated, read_fence_body, write_fence_body all live; M8-02 fills ensure_migrated and rewires cognition.py + analyze.py)
- Deviations from plan (expected: none)
</output>
