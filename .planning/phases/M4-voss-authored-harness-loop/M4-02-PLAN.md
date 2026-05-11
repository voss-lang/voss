---
phase: M4
plan: 02
type: execute
wave: 1
depends_on: [M4-01]
files_modified:
  - voss/harness/sandbox.py
  - voss/harness/cache.py
  - voss/harness/diagnostics.py
  - voss/cli.py
  - tests/harness/test_voss_check_dir.py
  - tests/harness/test_voss_compile_dir.py
  - tests/harness/test_cache_freshness.py
autonomous: true
requirements:
  - DOG-06
  - DOG-08
tags:
  - cli
  - cache
  - sandbox
  - diagnostics
  - wave-1

must_haves:
  truths:
    - "`voss check <dir>` rglobs *.voss, parses + analyzes each file with emit_indexes=False, prints per-file `<file>:<line>:<col>: <severity> <message>` diagnostics grouped by file, and a final summary `N errors, M warnings across K files` when K > 1."
    - "`voss check <dir>` exits non-zero on any error; --warnings-as-errors still applies."
    - "`voss check voss/harness/agent/` does NOT import `sentence_transformers` (Pitfall 7 / M3 D-03 carry-forward)."
    - "Single-file `voss check <file>` behavior is unchanged — no summary line, same exit semantics."
    - "`voss compile <dir>` emits one `.py` per source `.voss` under `.voss-cache/harness/<name>.py` (and NEVER next to the source per Pitfall 3)."
    - "`voss compile <dir>` writes `.voss-cache/harness/_manifest.json` matching the D-13 schema when the source dir name is `agent`."
    - "Manifest schema: `{version: 1, voss_version: str, compiled_at: ISO-8601 str, sources: {<name>.voss: {sha256: <64-hex>, lines: <int>}}}`."
    - "`voss/harness/sandbox.write_cache(project_root, relpath, text)` writes to `project_root/.voss-cache/<relpath>` via double `jail_path` + atomic `tmp.replace(target)`."
    - "`voss/harness/cache.assert_fresh(project_root)` raises `StaleHarnessCacheError` on missing manifest, voss_version mismatch, or any source sha256 mismatch."
    - "The `StaleHarnessCacheError` message contains the exact suggestion text `voss compile voss/harness/agent/` so tests can pin it."
    - "`.voss-cache/` remains git-ignored (M2 D-09 carry-forward — Pitfall 5 sentinel)."
  artifacts:
    - path: "voss/harness/sandbox.py"
      provides: "write_cache(project_root, relpath, text) helper; D-15 cache write path"
      contains: "def write_cache"
    - path: "voss/harness/cache.py"
      provides: "Manifest helpers — sha256_text, compute_source_shas, write_manifest, load_manifest, assert_fresh; D-13/D-14 schema"
      contains: "MANIFEST_VERSION"
    - path: "voss/harness/diagnostics.py"
      provides: "StaleHarnessCacheError exception class (D-10); no doctor row yet — that lands in M4-05 Wave 4"
      contains: "class StaleHarnessCacheError"
    - path: "voss/cli.py"
      provides: "_walk_voss_sources helper + dir-mode in check (line ~209) and compile (line ~147) + manifest emission on harness-dir compile"
      contains: "_walk_voss_sources"
    - path: "tests/harness/test_voss_check_dir.py"
      provides: "Wave-1 sentinel: dir walk, per-file aggregation, single-file no-summary, HF-encoder regression guard, error-exit code"
      contains: "test_check_dir_does_not_load_hf_encoder"
    - path: "tests/harness/test_voss_compile_dir.py"
      provides: "Wave-1 sentinel: per-file artifacts under .voss-cache/harness/, manifest schema, no-leak-next-to-source, gitignore presence"
      contains: "test_manifest_schema"
    - path: "tests/harness/test_cache_freshness.py"
      provides: "Wave-1 sentinel: assert_fresh OK after compile, raises on sha mismatch, raises on missing manifest, canonical error message"
      contains: "StaleHarnessCacheError"
  key_links:
    - from: "voss/cli.py:check (line ~209 dir branch)"
      to: "voss/cli.py:_walk_voss_sources + voss.analyzer.analyze(emit_indexes=False)"
      via: "for loop iterating rglob('*.voss')"
      pattern: "rglob"
    - from: "voss/cli.py:compile (line ~147 dir branch)"
      to: "voss/harness/cache.compute_source_shas + write_manifest"
      via: "harness-dir heuristic (source.name == 'agent')"
      pattern: "source.name == \"agent\""
    - from: "voss/harness/cache.write_manifest + write per-file .py"
      to: "voss/harness/sandbox.write_cache"
      via: "double jail_path + atomic tmp.replace"
      pattern: "write_cache"
    - from: "voss/harness/cache.assert_fresh"
      to: "voss/harness/diagnostics.StaleHarnessCacheError"
      via: "lazy import to break cache→diagnostics circular dep"
      pattern: "from .diagnostics import StaleHarnessCacheError"
---

<objective>
Land the directory-walking + per-file cache infra that DOG-06 and DOG-08 depend on. Five mechanical extensions, all with exact in-tree analogs (M4-PATTERNS.md):

1. **`voss/harness/sandbox.py`** gains `write_cache(project_root, relpath, text)` — double `jail_path` + atomic `tmp.replace`. Mirrors `voss/cli.py:_write_text_atomic` (lines 56-72).
2. **`voss/harness/cache.py`** NEW (~80 LOC) — manifest writer + freshness check. Mirrors `voss/harness/cognition.py:build_repo_idx` (lines 254-310) which is the sha+JSON-manifest analog from M2.
3. **`voss/harness/diagnostics.py`** gains `StaleHarnessCacheError(VossError)` class. (The doctor-row `check_harness_cache(cwd)` lands in M4-05 Wave 4 to keep this plan ~50% context.)
4. **`voss/cli.py:check` (line ~209)** gets a directory branch via new `_walk_voss_sources(source)` helper. Per-file diagnostics aggregated; summary `N errors, M warnings across K files` only when K > 1. `emit_indexes=False` invariant preserved (M3 D-03; Pitfall 7).
5. **`voss/cli.py:compile` (line ~147)** mirrors the dir branch; per-file output computed to `.voss-cache/harness/<name>.py`; writes `_manifest.json` via `cache.write_manifest` when `source.name == "agent"`.

Purpose: This plan unblocks both DOG-06 (CI gate `voss check voss/harness/agent/`) and DOG-08 (compiled artifacts under `.voss-cache/harness/`). Wave 0 must already have landed (M4-01) so the codegen auto-await is in place before any compiled output is exercised. All cache writes route through `sandbox.write_cache` per D-15.

Output:
- `voss/harness/sandbox.py` — +~15 LOC (`write_cache` helper appended).
- `voss/harness/cache.py` — NEW, ~80 LOC (constants + `ManifestEntry` + `sha256_text` + `compute_source_shas` + `write_manifest` + `load_manifest` + `assert_fresh`).
- `voss/harness/diagnostics.py` — +~5 LOC (`StaleHarnessCacheError(VossError)` class near the top of the module after existing imports).
- `voss/cli.py` — +~40 LOC (`_walk_voss_sources` helper + dir branches in `check` and `compile` + manifest emission tail).
- `tests/harness/test_voss_check_dir.py` — NEW (4 tests).
- `tests/harness/test_voss_compile_dir.py` — NEW (3 tests).
- `tests/harness/test_cache_freshness.py` — NEW (3 tests).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md
@.planning/phases/M4-voss-authored-harness-loop/M4-RESEARCH.md
@.planning/phases/M4-voss-authored-harness-loop/M4-PATTERNS.md
@.planning/phases/M4-voss-authored-harness-loop/M4-VALIDATION.md
@.planning/phases/M4-voss-authored-harness-loop/M4-01-PLAN.md
@voss/harness/sandbox.py
@voss/harness/cognition.py
@voss/harness/diagnostics.py
@voss/exceptions.py
@voss/cli.py
@tests/cli/test_check.py

<interfaces>
<!-- Key contracts extracted from the tree at commit 99d292e. -->

From voss/harness/sandbox.py (current 49 LOC; jail_path lines 20-31):
- `SandboxError(Exception)` already declared at line 16-17.
- `jail_path(cwd: Path, target: str | os.PathLike) -> Path` — resolves target relative to cwd; raises SandboxError on escape.
- No file-write helper today. M2 D-06 anticipated this; M4 adds it.

From voss/cli.py:_write_text_atomic (lines 56-72) — atomic-write reference pattern using `tempfile.NamedTemporaryFile` + `os.replace`.

From voss/cli.py:_compile_source (lines 75-118) — per-file compile primitive; takes `output_path`, `project_root`, `cache_dir`, `verbose` kwargs.

From voss/cli.py:check (lines 204-228) — current per-file body. Key invariant: `analyze(..., emit_indexes=False)` (M3 D-03).

From voss/cli.py:compile (lines 147-167) — current per-file body. Forwards to `_compile_source`. Default `cache_dir = Path(".voss-cache")`.

From voss/exceptions.py (lines 1-22):
- `class VossError(Exception): pass` at line 4-5.
- `class VossParseError(VossError)` at line 7+.
- StaleHarnessCacheError subclasses VossError (A5 assumption).

From voss/harness/diagnostics.py:
- `from voss.exceptions import VossError` is already imported (verify on read).
- `Check` dataclass + `CheckResult` enum + `run_all_checks` at lines 181-191.
- `aggregate_exit_code` at lines 194-198 (WARN = exit 0; D-16 informational).
- M4-02 only adds the exception class; the doctor row lands in M4-05.

From voss/harness/cognition.py:254-310 (build_repo_idx — sha1 + JSON manifest analog):
- Pattern: `digest = hashlib.sha1(text.encode("utf-8")).hexdigest()`; payload `{"version": 1, "git_head": ..., "files": [...]}`; `target.write_text(json.dumps(payload, indent=2) + "\n")`.
- M4 uses sha256 not sha1 (D-14); writes via `sandbox.write_cache` not direct `write_text` (D-15).

From voss/__init__.py:1 (verified):
- `__version__ = "0.1.0"` — directly importable as `from voss import __version__`.

From tests/cli/test_check.py:70-97 (CliRunner pattern):
- `runner = CliRunner()` + `runner.invoke(main, ["check", str(path)])` + `result.exit_code` + `result.output` assertions.
- `runner.isolated_filesystem()` is used by existing tests; `tmp_path` is an alternative for the new dir tests.

D-13 manifest schema (canonical):
```
{
  "version": 1,
  "voss_version": "<voss.__version__>",
  "compiled_at": "<datetime.now(UTC).isoformat()>",
  "sources": {
    "loop.voss": {"sha256": "<64-hex>", "lines": <int>},
    ...
  }
}
```

D-10 canonical error message (tests pin this):
- Must contain substring `voss compile voss/harness/agent/`.
- M4-PATTERNS.md §"voss/harness/cache.py" notes: "Tests assert on this exact string; do not embed dynamic details (sha mismatches, version values) in the message — researcher's verbose variants are illustrative but tests pin the canonical string." Use the canonical short form: `compiled harness cache stale — run: voss compile voss/harness/agent/`.

.gitignore (repo root) — verify `.voss-cache/` is present per M2 D-09 / Pitfall 5. If absent, this plan does NOT add it (out of scope; the test asserts presence and fails loudly if M2 dropped the line).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: sandbox.write_cache + cache.py manifest module + StaleHarnessCacheError</name>
  <files>voss/harness/sandbox.py, voss/harness/cache.py, voss/harness/diagnostics.py, tests/harness/test_cache_freshness.py</files>
  <read_first>
    - voss/harness/sandbox.py (entire 49 LOC; `jail_path` at lines 20-31, `SandboxError` at line 16, `shell_allowed` at lines 34-49)
    - voss/cli.py:56-72 (_write_text_atomic — atomic-write reference)
    - voss/harness/cognition.py:254-310 (build_repo_idx — sha+manifest analog M4 mirrors with sha256)
    - voss/exceptions.py:1-22 (VossError base; StaleHarnessCacheError subclasses VossError)
    - voss/harness/diagnostics.py:1-30 (imports + Check + CheckResult — confirm `from voss.exceptions import VossError` is present; if not, add it alongside the exception class)
    - voss/__init__.py (confirm `__version__ = "0.1.0"` at line 1)
    - M4-RESEARCH.md §"Pattern 4: Cache writer + manifest" (lines ~462-565)
    - M4-PATTERNS.md §"voss/harness/cache.py (NEW, ~80 LOC) — Wave 1 Pattern 4" and §"voss/harness/sandbox.py (MODIFY, +15 LOC) — Wave 1"
    - M4-PATTERNS.md §"tests/harness/test_cache_freshness.py (NEW) — Wave 1"
    - M4-RESEARCH.md §"Pitfall 4" — `assert_fresh` is called BEFORE the dynamic import (relevant for the Pitfall-4 sentinel test in this task)
  </read_first>
  <behavior>
    - `sandbox.write_cache(project_root, "harness/loop.py", "content")` writes to `project_root/.voss-cache/harness/loop.py` atomically (tmp file + rename).
    - `sandbox.write_cache` with a relpath that escapes `.voss-cache` (e.g. `"../escape.txt"`) raises `SandboxError`.
    - `cache.sha256_text("foo")` returns the 64-hex sha256 of `"foo"`.
    - `cache.compute_source_shas(project_root)` returns `dict[str, ManifestEntry]` for all `*.voss` files under `project_root/voss/harness/agent/`, sorted by name.
    - `cache.write_manifest(project_root, entries)` emits a JSON file at `project_root/.voss-cache/harness/_manifest.json` matching the D-13 schema; written via `sandbox.write_cache`.
    - `cache.load_manifest(project_root)` returns the dict (parsed JSON) or `None` if absent.
    - `cache.assert_fresh(project_root)` raises `StaleHarnessCacheError` on (a) missing manifest, (b) `voss_version` mismatch, (c) any source sha256 mismatch. Returns `None` on success.
    - The raised error's `str(exc.value)` contains `"voss compile voss/harness/agent/"` (canonical suggestion).
    - `StaleHarnessCacheError` is a subclass of `voss.exceptions.VossError` and importable from `voss.harness.diagnostics`.
  </behavior>
  <action>
    Append to `voss/harness/sandbox.py` (after the existing `shell_allowed` function): a new `write_cache(project_root: Path, relpath: str | os.PathLike, text: str) -> Path` function. Inside: call `jail_path(project_root, ".voss-cache")` to obtain `cache_root`; ensure it exists via `cache_root.mkdir(parents=True, exist_ok=True)`. Then call `jail_path(cache_root, relpath)` to obtain `target`. Ensure `target.parent` exists. Write atomically: `tmp = target.with_suffix(target.suffix + ".tmp")`; `tmp.write_text(text)`; `tmp.replace(target)`. Return `target`. No new imports beyond `Path` (already imported). Per D-15 + Pitfall 3.

    Add `StaleHarnessCacheError` to `voss/harness/diagnostics.py`. Add it near the top of the module after the existing imports. If `from voss.exceptions import VossError` is not already present, add it. Class body is `pass` plus a one-line docstring referencing D-10. Do NOT add the doctor row in this task — that lands in M4-05 (Wave 4) to keep this plan within context budget.

    Create `voss/harness/cache.py` (NEW) per Pattern 4 in M4-RESEARCH. Module-level constants: `HARNESS_AGENT_DIR = "voss/harness/agent"`; `CACHE_HARNESS_DIR = ".voss-cache/harness"`; `MANIFEST_NAME = "_manifest.json"`; `MANIFEST_VERSION = 1`. Imports: `hashlib`, `json`, `from dataclasses import dataclass`, `from datetime import datetime, timezone`, `from pathlib import Path`, `from voss import __version__ as VOSS_VERSION`, `from .sandbox import write_cache`. Define `@dataclass(frozen=True) class ManifestEntry: sha256: str; lines: int`. Define `sha256_text(text: str) -> str` returning `hashlib.sha256(text.encode("utf-8")).hexdigest()`. Define `compute_source_shas(project_root: Path) -> dict[str, ManifestEntry]` that iterates `sorted((project_root / HARNESS_AGENT_DIR).glob("*.voss"))` and returns `{p.name: ManifestEntry(sha256=sha256_text(text), lines=text.count("\n") + 1)}`. Define `write_manifest(project_root, entries) -> Path` that builds the payload dict per D-13 schema and routes through `write_cache(project_root, f"{CACHE_HARNESS_DIR}/{MANIFEST_NAME}", json.dumps(payload, indent=2) + "\n")`. Define `load_manifest(project_root) -> dict | None` returning `json.loads(path.read_text())` if `project_root / CACHE_HARNESS_DIR / MANIFEST_NAME` exists, else `None`. Define `assert_fresh(project_root) -> None`: lazy-import `StaleHarnessCacheError` from `.diagnostics` to avoid the circular; load manifest; if `None`, raise with message `"compiled harness cache stale — run: voss compile voss/harness/agent/"`; if `manifest.get("voss_version") != VOSS_VERSION`, raise with the SAME canonical message; otherwise compare `compute_source_shas(project_root)` to `manifest["sources"]` per-name and raise with the canonical message on any mismatch. All three raise paths use the EXACT same message text so the M4-PATTERNS.md-noted "tests pin the canonical string" invariant holds.

    Create `tests/harness/test_cache_freshness.py` (NEW) per M4-PATTERNS.md target tests. Three tests minimum: (1) `test_assert_fresh_passes_after_compile(tmp_path)` — write a fake voss/harness/agent/loop.voss, run a small inline compile by calling `compute_source_shas` + `write_manifest` directly (do NOT invoke the CLI yet — that's the next task; this isolates cache.py from cli.py), then call `assert_fresh(tmp_path)` and assert no raise. (2) `test_stale_cache_raises_on_source_change(tmp_path)` — same setup, then mutate the source file text, then expect `StaleHarnessCacheError` whose `str(exc.value)` contains `"voss compile voss/harness/agent/"`. (3) `test_missing_manifest_raises(tmp_path)` — create the source dir but never write the manifest; expect `StaleHarnessCacheError`. Use `pytest.raises` per CliRunner-free style (no CLI integration here — that's Task 3).

    Decision references: D-10 (loud stale-cache failure; canonical message); D-13 (manifest schema); D-14 (sha256 + voss_version key); D-15 (cache writes via sandbox).
  </action>
  <verify>
    <automated>pytest tests/harness/test_cache_freshness.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_cache_freshness.py -q` exits 0 with 3 passed.
    - `python -c "from voss.harness.diagnostics import StaleHarnessCacheError; from voss.exceptions import VossError; assert issubclass(StaleHarnessCacheError, VossError)"` exits 0.
    - `python -c "from voss.harness.sandbox import write_cache; import tempfile, pathlib; r=pathlib.Path(tempfile.mkdtemp()); write_cache(r, 'harness/x.py', 'hi'); assert (r/'.voss-cache/harness/x.py').read_text()=='hi'"` exits 0.
    - `python -c "from voss.harness.sandbox import write_cache, SandboxError; import tempfile, pathlib, pytest; r=pathlib.Path(tempfile.mkdtemp()); 
try: write_cache(r, '../escape.txt', 'x'); raise SystemExit('expected SandboxError')
except SandboxError: pass"` exits 0.
    - `grep -n 'MANIFEST_VERSION = 1' voss/harness/cache.py` returns 1 match.
    - `grep -n 'class StaleHarnessCacheError' voss/harness/diagnostics.py` returns 1 match.
    - All raise paths in `assert_fresh` use the identical canonical message text: `grep -c "voss compile voss/harness/agent/" voss/harness/cache.py` returns 3.
  </acceptance_criteria>
  <done>sandbox.write_cache + cache.py manifest module + StaleHarnessCacheError land with 3 passing cache-freshness tests. No CLI changes yet — Task 2 wires the CLI; Task 3 adds CLI-integration tests.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: voss/cli.py dir-walk for check + compile (with manifest emission on harness dir)</name>
  <files>voss/cli.py, tests/harness/test_voss_check_dir.py, tests/harness/test_voss_compile_dir.py</files>
  <read_first>
    - voss/cli.py (entire file; specifically `_compile_source` at 75-118, `_default_output_path` at ~52-53, `_print_diagnostics` at 40-42, `_exit_for_diagnostics`, `compile` at 147-167, `check` at 204-228, `_parse_file` at 32-37)
    - voss/diagnostics.py (confirm `Diagnostic.__str__` formats `<file>:<line>:<col>: <severity> <message>` — used by `_print_diagnostics`)
    - voss/analyzer.py (confirm `analyze(..., emit_indexes=False)` signature)
    - voss/harness/cache.py (just landed in Task 1; this task imports `compute_source_shas`, `write_manifest`)
    - voss/codegen.py:218-235 (`_resolve_cache_root` jail; cache root must be named `.voss-cache` — Pitfall 3)
    - tests/cli/test_check.py (entire; CliRunner pattern, isolated_filesystem usage)
    - tests/cli/test_run.py:22-58 (subprocess + tmp_path pattern; M4 dir tests adopt `tmp_path` + CliRunner)
    - M4-RESEARCH.md §"Pattern 3: voss check <dir> + voss compile <dir>" (lines ~417-460)
    - M4-PATTERNS.md §"voss/cli.py:check (~line 209) — Wave 1 dir-walk Pattern 3" and §"voss/cli.py:compile (~line 147) — Wave 1 dir-walk + manifest Pattern 3+4"
    - M4-RESEARCH.md §"Pitfall 3" (writes outside .voss-cache) + §"Pitfall 7" (HF encoder load on dir check)
    - .gitignore at repo root (verify `.voss-cache/` line present per M2 D-09; Pitfall 5)
  </read_first>
  <behavior>
    - `voss check <dir>` succeeds on a directory containing valid `.voss` files, exit 0, prints `0 errors, 0 warnings across N files` summary when N > 1.
    - `voss check <file>` (single file) prints diagnostics with NO summary line (D-07 invariant).
    - `voss check <dir>` with a mixed valid+invalid set exits 1 and prints per-file diagnostics for the broken file.
    - `voss check <dir>` does NOT import `sentence_transformers` (Pitfall 7 / M3 D-03 carry-forward — `emit_indexes=False` is invariant).
    - `voss compile <dir>` (where `<dir>.name == "agent"`) emits one `.py` per source under `project_root/.voss-cache/harness/<name>.py` and writes `_manifest.json` per Task 1 cache module.
    - `voss compile <dir>` does NOT write `.py` files next to the `.voss` sources (Pitfall 3 sentinel).
    - `voss compile <file>` (single file) preserves current behavior — uses the `-o`/`--output` flag if provided.
    - `.voss-cache/` is git-ignored at the repo root (Pitfall 5 sentinel — assertion only; this task does NOT modify .gitignore).
    - The CliRunner-driven tests cover all five behaviors above.
  </behavior>
  <action>
    Edit `voss/cli.py` near the top of the file (alongside the existing helpers like `_parse_file`, `_print_diagnostics`, `_write_text_atomic`). Add `_walk_voss_sources(source: Path) -> list[Path]`: if `source.is_file()`, return `[source]`; if `source.is_dir()`, return `sorted(source.rglob("*.voss"))`; else raise `click.ClickException(f"not a file or directory: {source}")`.

    Edit `voss/cli.py:check` (~line 209). Replace the per-file body with a loop over `_walk_voss_sources(source)`. Inside the loop: call `_parse_file(f)`; wrap `analyze(program, source_path=str(f), project_root=project_root, cache_dir=cache_dir, emit_indexes=False)` in `try/except VossError` (preserving the existing `raise click.ClickException(str(exc))` behavior); call `_print_diagnostics(result.diagnostics)`; accumulate `error_count += len(result.errors)` and `warning_count += len(result.warnings)`. After the loop, if `len(files) > 1`, print `click.echo(f"{error_count} errors, {warning_count} warnings across {len(files)} files")`. If `error_count > 0`, raise `click.exceptions.Exit(code=1)`. If `warnings_as_errors and warning_count > 0`, raise `click.exceptions.Exit(code=1)`. **CRITICAL: keep `emit_indexes=False` — copy-paste from `_compile_source` is the Pitfall 7 trap.**

    Edit `voss/cli.py:compile` (~line 147). Replace the body with: `files = _walk_voss_sources(source)`; `proj = Path(project_root or Path.cwd())`. Loop over files: if `source.is_dir()`, compute `target = proj / cache_dir / "harness" / f.with_suffix(".py").name`; else `target = output`. Call `_compile_source(f, output_path=target, project_root=project_root, cache_dir=cache_dir, verbose=verbose)`. After the loop, if `source.is_dir() and source.name == "agent"`: lazy-import `from voss.harness import cache as harness_cache`; call `entries = harness_cache.compute_source_shas(proj)`; call `harness_cache.write_manifest(proj, entries)`; if `verbose`, echo `f"wrote manifest with {len(entries)} sources"`.

    Create `tests/harness/test_voss_check_dir.py` (NEW) per M4-PATTERNS.md target tests. Four tests: (1) `test_check_dir_walks_and_aggregates(tmp_path)` — write two valid `.voss` files (one in a subdir), invoke `runner.invoke(main, ["check", str(tmp_path)])`, assert exit 0 and `"across 2 files"` in output. (2) `test_check_dir_does_not_load_hf_encoder(tmp_path)` — write one trivial `.voss` file, invoke check, then `import sys; assert "sentence_transformers" not in sys.modules`. (3) `test_check_single_file_summary_suppressed(tmp_path)` — write one file, invoke check on the file (not the dir), assert `"across"` NOT in output. (4) `test_check_dir_aggregates_errors_and_exits_nonzero(tmp_path)` — mix one valid + one syntactically-invalid `.voss` file, expect exit 1. Use the existing `tests/cli/test_check.py` style (plain `def`, `CliRunner`, `tmp_path`).

    Create `tests/harness/test_voss_compile_dir.py` (NEW). Three tests: (1) `test_compile_dir_emits_per_file_artifacts(tmp_path)` — create `tmp_path/voss/harness/agent/{loop,router}.voss` with trivial content, run `runner.invoke(main, ["compile", str(agent_dir), "--project-root", str(tmp_path)])`, assert exit 0, both `tmp_path/.voss-cache/harness/loop.py` and `tmp_path/.voss-cache/harness/router.py` exist, AND `tmp_path/voss/harness/agent/loop.py` does NOT exist (Pitfall 3). (2) `test_manifest_schema(tmp_path)` — same setup, assert `_manifest.json` exists, `data["version"] == 1`, `isinstance(data["voss_version"], str)`, `"compiled_at" in data`, every entry has `sha256` of length 64 (sha256 hex) and `lines >= 1`. (3) `test_voss_cache_ignored()` — read repo-root `.gitignore` (`Path(__file__).resolve().parents[2] / ".gitignore"`); assert `.voss-cache/` substring present (M2 D-09 carry-forward; Pitfall 5 sentinel — test fails loudly if M2 dropped the line).

    Decision references: D-05 (dir walk both check + compile); D-06 (static-only CI gate, emit_indexes=False preserved); D-07 (per-file diagnostic format + summary); D-13 (per-file artifacts under .voss-cache/harness/); D-15 (cache writes via sandbox.write_cache — already routed through cache.write_manifest).

    Per Q-4: project_root defaults to `Path.cwd()` (existing behavior). Manifest emission heuristic is `source.name == "agent"` per M4-PATTERNS.md (alternative would be an explicit `--manifest` flag; the heuristic is sufficient for M4 success bar D-12).
  </action>
  <verify>
    <automated>pytest tests/harness/test_voss_check_dir.py tests/harness/test_voss_compile_dir.py tests/cli/test_check.py tests/cli/test_run.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_voss_check_dir.py -q` exits 0 with 4 passed.
    - `pytest tests/harness/test_voss_compile_dir.py -q` exits 0 with 3 passed.
    - `pytest tests/cli/ -q` exits 0 (no regressions in single-file CLI behavior).
    - `grep -n '_walk_voss_sources' voss/cli.py` returns at least 3 matches (helper definition, check use, compile use).
    - `grep -n 'emit_indexes=False' voss/cli.py` returns at least 1 match within the check function body (Pitfall 7 invariant).
    - `grep -n 'source.name == "agent"' voss/cli.py` returns 1 match (manifest heuristic).
    - From repo root, `python -c "from click.testing import CliRunner; from voss.cli import main; import sys, pathlib, tempfile; r=pathlib.Path(tempfile.mkdtemp()); (r/'a.voss').write_text('let x = 1\n'); print(CliRunner().invoke(main, ['check', str(r)]).exit_code)"` prints `0`.
  </acceptance_criteria>
  <done>voss check + voss compile both accept directories; per-file diagnostics aggregated; manifest emitted for harness dir; HF-encoder regression guard passes; single-file behavior unchanged; 7 new tests green; full tests/cli/ suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Filesystem path arg (`voss check <path>`, `voss compile <path>`) | User-supplied; `_walk_voss_sources` validates file-or-dir. Subsequent `rglob` operates within that boundary. |
| `.voss-cache/` writes | Routed through `sandbox.write_cache` with double `jail_path`; prevents path-escape via crafted relpath. |
| `_manifest.json` consumed by `assert_fresh` | Read with `json.loads` (no `pickle`, no `eval`); shape validated by canonical-message raise on any mismatch. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M4-W1-write-escape | Tampering | `sandbox.write_cache` | mitigate | Double `jail_path`: once to confirm `.voss-cache` is inside `project_root`, again to confirm `relpath` is inside `.voss-cache`. Sentinel test in Task 1 acceptance criteria covers `../escape.txt` rejection. |
| T-M4-W1-cache-tamper | Tampering | `.voss-cache/harness/*.py` between compile and boot | mitigate (partial) | sha256 in `_manifest.json` is on the SOURCE `.voss` text (D-14). Hand-edit of a compiled `.py` is NOT detected by sha alone — by-design per D-14 (cache key is sources, not artifacts). Future hardening could add `.py` sha; out of scope for M4 (M4-RESEARCH §Known Threat Patterns). |
| T-M4-W1-stale-silent | Spoofing / Repudiation | `voss compile` writing partial manifest after error | mitigate | `write_manifest` writes the full payload in one `write_cache` call (atomic `tmp.replace`). Partial writes either succeed or fail; the `_manifest.json` mtime + content are coherent. |
| T-M4-W1-hf-load | Availability | `voss check <dir>` CI gate runtime | mitigate | `emit_indexes=False` invariant preserved in the dir-walk branch (Pitfall 7). Sentinel test asserts `sentence_transformers` absent from `sys.modules` after check. Keeps CI gate < 5s. |
| T-M4-W1-gitignore-leak | Tampering / Repudiation | Compiled `.py` artifacts accidentally committed | mitigate | `test_voss_cache_ignored` reads repo-root `.gitignore` and asserts `.voss-cache/` presence (M2 D-09 carry-forward; Pitfall 5). Loud failure if M2's line was removed. |
| T-M4-W1-manifest-injection | Tampering | `_manifest.json` parsed at boot | mitigate | `assert_fresh` validates `version == 1`, `voss_version` string-compare, and every source `sha256`. Manifest is internal artifact (not user-supplied); attack surface is limited to filesystem write access (covered by `write_cache` jail). |
</threat_model>

<verification>
After both tasks land:
1. `pytest tests/harness/test_voss_check_dir.py tests/harness/test_voss_compile_dir.py tests/harness/test_cache_freshness.py -q` exits 0 (10 tests across the three files).
2. `pytest tests/cli/ -q` exits 0 (single-file CLI behavior preserved).
3. `python -m voss.cli check voss/harness/agent/` runs without the `voss/harness/agent/` dir existing — should exit 0 with empty file list AND print no summary (zero files). (Optional: if rglob returns empty, the loop is skipped and `if error_count > 0` is false; verify behavior.)
4. M4-VALIDATION rows `sandbox-write-cache`, `cli-check-dir-walk`, `cli-compile-dir-walk`, `manifest-shape`, `stale-cache-error`, `check-dir-static-only` flip from ❌ to ✓.
</verification>

<success_criteria>
- `voss check <dir>` and `voss compile <dir>` both work; single-file behavior unchanged.
- All cache writes route through `sandbox.write_cache`.
- `_manifest.json` matches the D-13 schema exactly.
- `StaleHarnessCacheError` raised on missing manifest, version mismatch, or sha mismatch — with the canonical suggestion text.
- `voss check <dir>` does NOT trigger the HF encoder load.
- `.voss-cache/` is git-ignored (verified, not modified).
- All 10 new tests pass; full tests/cli/ and tests/harness/ suites green.
</success_criteria>

<output>
After completion, create `.planning/phases/M4-voss-authored-harness-loop/M4-02-SUMMARY.md` documenting:
- Exact LOC additions per file.
- Confirmation that `emit_indexes=False` is in the dir-walk branch.
- Manifest schema as emitted (sample JSON).
- Any deviation from M4-PATTERNS.md (e.g., if the manifest heuristic shifted or if Pitfall 5 sentinel needed adjustment because `.voss-cache/` was missing from .gitignore).
- All 10 new tests passing; tests/cli/ + tests/harness/ green.
</output>
