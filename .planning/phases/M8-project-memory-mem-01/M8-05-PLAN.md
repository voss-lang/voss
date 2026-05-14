---
phase: M8
plan: 05
type: execute
wave: 4
depends_on: [M8-03, M8-04]
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_slash_recall.py
  - tests/harness/test_slash_forget.py
  - tests/harness/test_slash_memory.py
  - tests/harness/test_slash_save_note.py
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [MEM-05]
tags: [memory, slash-commands, repl]
must_haves:
  truths:
    - "/recall <query> [--top N] [--source turn|decision|convention|ledger|note] dispatches to ctx.memory_store.recall and prints top-N tagged hits"
    - "/forget <pattern> [--yes] dispatches to ctx.memory_store.forget; mutating=True; non-interactive mode (sys.stdin.isatty() == False) requires --yes or errors out"
    - "/memory [--source <s>] dispatches to ctx.memory_store.summary and prints markdown summary"
    - "/save <note> dispatches to ctx.memory_store.write_note (NOT the old _save_session handler; that was renamed in M8-00)"
    - "All four commands have a `help` field on their SlashCommand registration, surfaced by /help"
    - "ctx.memory_store is bound to the session in _run_repl boot (M8-03 wire) so handlers can dispatch without re-instantiating"
    - "Pitfall 1 regression test: /save <note> writes a note file and does NOT mutate record.name (separate from /save-session handler)"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "4 new slash handlers (_recall, _forget, _memory, _save_note) + 4 SlashCommand registrations in _build_slash_registry; ctx.memory_store binding in _run_repl boot"
    - path: "tests/harness/test_slash_*.py"
      provides: "4 integration test files covering each slash command's effect on stdout/file system"
  key_links:
    - from: "voss/harness/cli.py::_build_slash_registry"
      to: "SlashCommand('/recall'|'/forget'|'/memory'|'/save', ...)"
      via: "tuple registration"
      pattern: "SlashCommand\\(\"/(recall|forget|memory|save)\""
    - from: "voss/harness/cli.py::_run_repl"
      to: "ctx.memory_store = MemoryStore(cwd).bind(session_id=record.id)"
      via: "boot-time bind adjacent to voss_md.read_and_inject (M8-01 wire site)"
      pattern: "MemoryStore\\(cwd\\)\\.bind"
    - from: "/save handler"
      to: "ctx.memory_store.write_note"
      via: "args joined to text via ' '.join(args)"
      pattern: "memory_store\\.write_note"
---

<objective>
Land MEM-05: four new slash commands wired into the existing slash registry. `/recall` queries the memory store; `/forget` tombstones matching IDs with `--yes` gate; `/memory` prints a per-source markdown summary; `/save` writes a manual note. Bind ctx.memory_store at REPL boot so handlers can dispatch without re-instantiation.

Pitfall 1 (resolved at M8-00 by renaming the old `/save` handler to `/save-session`) means the bare `/save` slot is now free for the new memory-note handler. This plan re-claims it and adds a regression test pinning the no-rename-record invariant.

Purpose: The slash registry is the v0.1 UX for memory; M9 TUI will replace this with panels but the M8 surface must work standalone for pre-M9 dogfood.
Output: 4 SlashCommand registrations + 4 handler functions + 4 integration test files + 1 extension of test_repl_slash.py + ctx.memory_store binding in _run_repl boot.
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
@voss/harness/cli.py
@voss/harness/slash.py
@voss/harness/memory_store.py

<interfaces>
<!-- M8-00 already delivered: -->
- /save renamed to /save-session at cli.py:473 (handler _save_session)
- Bare /save slot is unclaimed
- 4 test stub files exist as module-skipped placeholders (Wave 0)

<!-- M8-03 already delivered: -->
- MemoryStore.recall(query, *, top_k=5, source=None) -> list[Hit]
- MemoryStore.forget(pattern, *, confirm=False) -> int
- MemoryStore.summary(*, source=None) -> str
- MemoryStore.write_note(text, *, session_id) -> Path
- Hit dataclass: source, locator, score, excerpt, session_id, ts

<!-- Existing slash patterns reused: -->
- SlashCommand signature from voss/harness/slash.py: name (str), help (str), handler (Callable[[ctx, args, raw_line], None]), aliases (tuple), mutating (bool), hidden (bool)
- Handler signature: def _foo(ctx: ReplContext, args: list[str], _line: str) -> None — args is already shlex.split via SlashRegistry.dispatch (slash.py:56)
- Existing pattern: argument flag checks via "in args" (cli.py:398 — "/mode auto --confirm" pattern)
- Existing pattern: click.echo for output (every existing slash handler uses click.echo)
- Existing pattern: click.echo(..., err=True) for error/warning lines
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Bind ctx.memory_store at REPL boot + implement 4 slash handlers + register in _build_slash_registry</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py lines 380-484 (existing slash handlers + _build_slash_registry tuple)
    - voss/harness/cli.py lines 688-834 (_run_repl REPL loop + boot init — M8-01 already inserted voss_md.read_and_inject; this plan adds memory_store binding adjacent)
    - voss/harness/cli.py the ReplContext dataclass (locate via grep — it's likely near top of the REPL section)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/cli.py" §"Slash command registration block" + §"Argument parsing for slash flags"
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §"Claude's Discretion" (slash-command argument parsing — shlex.split + /top + --source)
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Open Question 3" (top-N default = 5)
    - voss/harness/memory_store.py (M8-03; verify Hit fields + method signatures)
  </read_first>
  <action>
    (a) Extend ReplContext dataclass (locate via `grep -n "class ReplContext" voss/harness/cli.py`) — add field `memory_store: "MemoryStore | None" = None` adjacent to the existing voss_md_text field added by M8-01. Use string-quoted forward ref to avoid circular imports at module-load time. Top-of-file: ensure `from .memory_store import MemoryStore` is imported (or use TYPE_CHECKING block + runtime import inside _run_repl).

    (b) In _run_repl boot (around the M8-01 voss_md.read_and_inject insertion, after `bundle = cognition_mod.load(...)`): insert `memory_store = MemoryStore(cwd).bind(session_id=record.id)` and attach as `ctx.memory_store = memory_store`. Adjacent to (NOT replacing) the existing voss_md wire.

    (c) Implement 4 slash handlers in cli.py adjacent to existing handlers (e.g. after _save_session). Use the standard `(ctx, args, _line) -> None` signature.

    _recall: parse args via positional + flag parsing:
    - If no args: click.echo("usage: /recall <query> [--top N] [--source turn|decision|convention|ledger|note]", err=True); return.
    - top_k = 5 (RESEARCH Open Q3); source = None.
    - Iterate args to extract --top <N> and --source <s> flags; if "--top" in args: idx = args.index("--top"); top_k = int(args[idx+1]); args = args[:idx] + args[idx+2:] (or use a more robust mini-parser). Same for "--source".
    - query = " ".join(args).strip(); if not query: click.echo("usage: /recall <query> ...", err=True); return.
    - hits = ctx.memory_store.recall(query, top_k=top_k, source=source).
    - If not hits: click.echo("(no hits)"); return.
    - For each hit: click.echo(f"[{h.source}] {h.locator}  (score {h.score:.2f})"); click.echo(f"  {h.excerpt[:160]}").

    _forget: arg parsing:
    - If no args: click.echo("usage: /forget <pattern> [--yes]", err=True); return.
    - pattern = args[0]; confirm = "--yes" in args.
    - import sys; non_interactive = not sys.stdin.isatty(); if non_interactive and not confirm: click.echo("/forget requires --yes in non-interactive mode", err=True); return.
    - n = ctx.memory_store.forget(pattern, confirm=confirm); click.echo(f"tombstoned: {n} entries").

    _memory: arg parsing:
    - source = None; if "--source" in args: idx = args.index("--source"); source = args[idx+1] if idx+1 < len(args) else None.
    - summary = ctx.memory_store.summary(source=source); click.echo(summary).

    _save_note: handler for the bare /save name (after M8-00 rename, this slot is free):
    - If no args: click.echo("usage: /save <note text>", err=True); return.
    - text = " ".join(args).strip(); if not text: click.echo("usage: /save <note text>", err=True); return.
    - try: path = ctx.memory_store.write_note(text, session_id=ctx.record.id); except Exception as exc: click.echo(f"failed: {exc}", err=True); return.
    - click.echo(f"note saved: {path.relative_to(ctx.cwd) if hasattr(ctx, 'cwd') and ctx.cwd in path.parents else path}").
    - CRITICAL Pitfall 1 invariant: this handler MUST NOT mutate ctx.record.name (that was the OLD /save behavior, now /save-session). Add a comment: `# Pitfall 1 invariant: do NOT mutate ctx.record.name — that is /save-session's job.`

    (d) Register the 4 commands in _build_slash_registry's tuple (cli.py:464-483). Insert AFTER the existing _save_session registration (which lives at the position the old _save used to occupy) in this order:
    - SlashCommand("/recall", "search memory (top-N hits across sources)", _recall)
    - SlashCommand("/forget", "delete memory entries matching <pattern>", _forget, mutating=True)
    - SlashCommand("/memory", "summarize current memory store", _memory)
    - SlashCommand("/save",   "append a manual note to memory", _save_note, mutating=True)
  </action>
  <verify>
    <automated>python -c "from voss.harness.cli import _recall, _forget, _memory, _save_note; print('handlers importable')" && pytest tests/harness/test_repl_slash.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - All 4 handlers (_recall, _forget, _memory, _save_note) defined and importable from voss.harness.cli.
    - `grep -nE 'SlashCommand\("/(recall|forget|memory|save)"' voss/harness/cli.py` returns exactly 4 matches.
    - `grep -nE 'SlashCommand\("/save-session"' voss/harness/cli.py` returns 1 match (from M8-00; still present, NOT removed).
    - `grep -nE "MemoryStore\\(cwd\\)\\.bind" voss/harness/cli.py` returns ≥ 1 match in _run_repl boot.
    - ReplContext dataclass contains a `memory_store` field (`grep -nE "memory_store:" voss/harness/cli.py` returns ≥ 1).
    - Pre-existing test_repl_slash.py is GREEN.
    - Pre-existing tests still GREEN: `pytest tests/harness/ -x --timeout=120 -k "not test_slash_recall and not test_slash_forget and not test_slash_memory and not test_slash_save_note"`.
  </acceptance_criteria>
  <done>
    4 slash handlers + 4 SlashCommand registrations + ctx.memory_store binding all landed. Existing slash registry tests still pass. /save and /save-session coexist with distinct behaviors.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Un-skip and implement 4 slash integration tests + extend test_repl_slash.py</name>
  <files>tests/harness/test_slash_recall.py, tests/harness/test_slash_forget.py, tests/harness/test_slash_memory.py, tests/harness/test_slash_save_note.py, tests/harness/test_repl_slash.py</files>
  <read_first>
    - tests/harness/test_slash_*.py (Wave-0 stubs)
    - tests/harness/test_repl_slash.py (existing — has test_memory_commands_not_yet_registered placeholder from M8-00)
    - voss/harness/cli.py (Task 1 of this plan landed; handlers exist)
    - voss/harness/slash.py (SlashRegistry.dispatch contract — handlers receive shlex-split args)
    - tests/harness/conftest.py (fake_session_corpus + tmp_voss_repo from M8-03)
  </read_first>
  <behavior>
    - test_slash_recall.py: dispatching "/recall snake_case" against a seeded MemoryStore prints at least one hit line to stdout with the source tag prefix (e.g. "[turn] turn:s1:000").
    - test_slash_recall with --source turn: only turn-sourced hits appear in output.
    - test_slash_forget: dispatching "/forget turn:s1:*" with --yes in non-interactive mode tombstones matching entries (returns count > 0); reading the .voss/memory/.tombstones.jsonl file shows the tombstoned IDs.
    - test_slash_forget without --yes in non-interactive mode: prints error to stderr, does NOT tombstone.
    - test_slash_memory: dispatching "/memory" prints markdown including the substring "turns:" (or per-source count rows).
    - test_slash_save_note: dispatching "/save my rate-limiter idea" writes a file under .voss/memory/notes/ whose body contains "my rate-limiter idea"; the session record.name is UNCHANGED (Pitfall 1 invariant).
    - test_slash_save_note variant: dispatching "/save" with no args prints usage to stderr and does NOT write any file.
  </behavior>
  <action>
    (a) For each of the 4 test files, remove the module-level `pytestmark = pytest.mark.skip(...)`. Implement each test using a shared helper: build a ReplContext-like SimpleNamespace with .memory_store (real MemoryStore against tmp_voss_repo, bind session_id="test-sess"), .record (SimpleNamespace with .id="test-sess", .name="original-name", .runs=[]), .cwd (tmp_voss_repo). Use the M8-00 fake_session_corpus fixture to seed memory store for recall + memory tests.

    Tests to implement:

    test_slash_recall.py:
    - test_recall_command_registered: import the registry via `from voss.harness.cli import _build_slash_registry; reg = _build_slash_registry()`; assert "/recall" is in reg (use the public lookup method on SlashRegistry — likely `reg.get("/recall")` or iteration over .commands; verify by reading slash.py). Assert the command's help string is non-empty.
    - test_recall_returns_top_n_with_source_filter: seed via fake_session_corpus; build ctx; call _recall(ctx, ["snake_case", "--top", "3", "--source", "turn"], "/recall snake_case --top 3 --source turn"); use capsys (pytest fixture) to capture stdout; assert "[turn]" appears in captured output; assert "[decision]" does NOT appear (source filter honored); assert at most 3 result lines.

    test_slash_forget.py:
    - test_forget_tombstones_matching_ids: seed with one turn at composite id "turn:test-sess:000"; build ctx; monkeypatch sys.stdin.isatty to return True; call _forget(ctx, ["turn:test-sess:*", "--yes"], "..."); assert .voss/memory/.tombstones.jsonl exists; its content includes a JSON line with "turn:test-sess:000" (or similar matching id).
    - test_forget_requires_yes_noninteractive: same setup but monkeypatch sys.stdin.isatty to return False; call _forget(ctx, ["turn:test-sess:*"], "...") WITHOUT --yes; use capsys; assert stderr contains "requires --yes"; assert .voss/memory/.tombstones.jsonl is empty OR not present (no tombstones written).

    test_slash_memory.py:
    - test_memory_summary_renders_counts_per_source: seed memory store with one turn + one note + one convention; build ctx; call _memory(ctx, [], "/memory"); capsys; assert captured stdout contains substring "turns" and "conventions" and "notes" (or per-source row markers — match whatever MemoryStore.summary actually emits per M8-03).

    test_slash_save_note.py:
    - test_save_note_writes_to_memory_notes_dir: build ctx with record.name="original-name"; call _save_note(ctx, ["my", "rate-limiter", "idea"], "/save my rate-limiter idea"); assert exactly one new file under (tmp_voss_repo/".voss/memory/notes/").glob("*.md"); its body contains "my rate-limiter idea".
    - test_save_note_does_not_rename_session (Pitfall 1 regression): same setup; capture ctx.record.name BEFORE the call; call _save_note(ctx, ["a", "new", "note"], "/save a new note"); assert ctx.record.name == "original-name" (UNCHANGED). This is the key regression — if /save accidentally invokes the old _save_session behavior, this test fails loudly.
    - test_save_with_no_args_errors: call _save_note(ctx, [], "/save"); capsys; assert stderr contains "usage:"; assert no new file under .voss/memory/notes/.

    (b) Extend tests/harness/test_repl_slash.py: replace the existing skipped `test_memory_commands_not_yet_registered` (M8-00 placeholder) with `def test_memory_commands_registered():` body asserting all 4 names ("/recall", "/forget", "/memory", "/save") are present in `_build_slash_registry()`. Also assert "/save-session" is still present (M8-00 rename intact).
  </action>
  <verify>
    <automated>pytest tests/harness/test_slash_recall.py tests/harness/test_slash_forget.py tests/harness/test_slash_memory.py tests/harness/test_slash_save_note.py tests/harness/test_repl_slash.py -x -q && pytest tests/harness/ -x --timeout=120 -q</automated>
  </verify>
  <acceptance_criteria>
    - All tests in the 4 new test files GREEN.
    - test_repl_slash.py::test_memory_commands_registered GREEN (asserts all 4 + /save-session present).
    - Full harness suite green (no regression in M8-01..04 tests or pre-existing tests).
    - `grep -v '^#' tests/harness/test_slash_save_note.py | grep -c "pytestmark.*skip"` returns 0 (module-level skip removed).
    - `grep -c "record\\.name == \"original-name\"" tests/harness/test_slash_save_note.py` returns ≥ 1 (Pitfall 1 regression assertion in place).
    - At least 7 distinct test function definitions exist across the 4 new slash test files: `grep -cE "^def test_" tests/harness/test_slash_recall.py tests/harness/test_slash_forget.py tests/harness/test_slash_memory.py tests/harness/test_slash_save_note.py` returns ≥ 7.
  </acceptance_criteria>
  <done>
    All 4 slash commands have integration tests asserting stdout/file effect. Pitfall 1 regression test in place. /forget --yes gate exercised in non-interactive mode. Full Req 5 acceptance criteria covered.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user-typed slash args -> handler (shlex.split) | shlex handles quoting safely; no shell interpretation; args remain Python strings |
| /forget pattern -> MemoryStore.forget | pattern is fnmatch-glob; never path-traversal capable (operates on composite IDs + relative paths only — see M8-03 threat model) |
| /save arbitrary text -> .voss/memory/notes/<slug>.md | text becomes file body; slug derived via cognition.slug() which strips traversal chars |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M8-05-01 | Tampering | /save args collision with old /save-session behavior | mitigate | test_save_note_does_not_rename_session pinned; M8-00 rename gates the /save bare name; handler explicitly comments invariant |
| T-M8-05-02 | Information Disclosure | /memory output reveals tombstoned content | mitigate | MemoryStore.summary excludes tombstoned entries (M8-03 contract); /memory output reflects active state |
| T-M8-05-03 | DoS | /forget * with no pattern wipes the store | mitigate | M8-03 MemoryStore.forget paranoid-default returns 0 for unconfirmed wildcard; --yes flag required |
| T-M8-05-04 | DoS | /recall on unbounded query string causes excessive scan | accept | v0.1 corpus bounded by 100MB cap; M8-06 enforces; M8-05 imposes no separate cap |
| T-M8-05-05 | Information Disclosure | /save text containing secrets persisted to .voss/memory/notes | accept | matches existing /save-session and EpisodicMemory data-handling; user-typed content is user-trusted; chmod 0o600 limits scope |
</threat_model>

<verification>
- `pytest tests/harness/test_slash_recall.py tests/harness/test_slash_forget.py tests/harness/test_slash_memory.py tests/harness/test_slash_save_note.py tests/harness/test_repl_slash.py -x`
- `pytest tests/harness/ -x --timeout=120` (no regression)
- `grep -nE 'SlashCommand\("/(recall|forget|memory|save)"' voss/harness/cli.py | wc -l` returns 4
- `grep -nE 'SlashCommand\("/save-session"' voss/harness/cli.py | wc -l` returns 1
</verification>

<success_criteria>
- /recall, /forget, /memory, /save all registered with help text in _build_slash_registry.
- ctx.memory_store bound at REPL boot.
- /forget enforces --yes in non-interactive mode.
- /save writes a note file and does NOT rename the session (Pitfall 1 regression test green).
- /save-session still works (M8-00 rename preserved).
- All 4 slash integration test files green + test_repl_slash.py updated assertion green.
- Full harness suite green.
</success_criteria>

<output>
After completion, create `.planning/phases/M8-project-memory-mem-01/M8-05-SUMMARY.md` summarizing:
- 4 slash commands wired with argument shapes (/recall query, /forget pattern --yes, /memory --source, /save text)
- ctx.memory_store binding at REPL boot
- Pitfall 1 invariant pinned via regression test
- /forget --yes gate behavior
- Test count: 4 new files + test_repl_slash.py extension
- Deviations from plan
</output>
