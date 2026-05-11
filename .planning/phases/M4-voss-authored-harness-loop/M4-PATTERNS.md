# Phase M4: Voss-authored Harness Loop - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 22 (15 NEW + 13 MODIFIED, ordered by Wave 0..4)
**Analogs found:** 22 / 22

Every M4 file has a direct in-tree analog. M4 is overwhelmingly mechanical extension: compiler sub-plan (Wave 0) extends existing grammar/parser/codegen shapes that already work for `use ... as` (codegen+AST) and auto-await (existing `generated_fns` condition); the remaining waves wrap `_compile_source` and `_print_diagnostics` (Wave 1), mirror the `voss/harness/agent.py:run_turn` shape in `.voss` form (Wave 2), and clone the `FakeProvider` parity pattern from `tests/harness/test_agent_integration.py` (Wave 3). Mirrors M3-PATTERNS.md structure.

---

## File Classification

### Wave 0 — compiler sub-plan (gate: blocks all `.voss` authoring)

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `voss/grammar.lark` (~line 174-175) | MODIFY | compiler grammar | static (lark rule) | self (existing `use_stmt`) + M3 D-02 `try_stmt` precedent at grammar.lark:133 | exact (in-file) |
| `voss/parser.py:714-715` | MODIFY | compiler AST builder | transform | self (existing `use_stmt` method) | exact (in-file) |
| `voss/codegen.py:441-446` | MODIFY | codegen rule (auto-await) | transform | self (existing `generated_fns` await condition) | exact (in-file) |
| `tests/parser/test_use_alias.py` | NEW | test (parser unit) | request-response (in-process parse) | `tests/codegen/test_imports.py:56-60` (alias preservation test exists; mirror its assert pattern) | exact |
| `tests/codegen/test_await_use_import.py` | NEW | test (codegen unit) | transform | `tests/codegen/test_imports.py` (in-process codegen + string assertion) | role-match |

### Wave 1 — CLI dir-walk + cache infra

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `voss/harness/cache.py` | NEW | harness module (manifest helpers) | file-I/O (sha + json) | `voss/harness/cognition.py:254-310` (build_repo_idx — sha+json manifest) | role-match |
| `voss/harness/sandbox.py` | MODIFY (+15 LOC) | harness utility | file-I/O | self (existing `jail_path` at lines 20-31) + `voss/cli.py:_write_text_atomic` at 56-72 | exact (in-file) |
| `voss/harness/diagnostics.py` | MODIFY | harness module (doctor row + exception) | request-response | self (existing `Check` dataclass + `check_project_dirs` at 158-178) | exact (in-file) |
| `voss/cli.py:check` (~line 209) | MODIFY | CLI controller | request-response | self (existing per-file body 209-228) | exact (in-file) |
| `voss/cli.py:compile` (~line 147) | MODIFY | CLI controller | request-response | self (existing per-file body 147-167) | exact (in-file) |
| `tests/harness/test_voss_check_dir.py` | NEW | test (CLI integration) | request-response (CliRunner) | `tests/cli/test_check.py:70-97` (cache-leak invariant pattern; CliRunner) | exact |
| `tests/harness/test_voss_compile_dir.py` | NEW | test (CLI integration) | request-response (CliRunner) | `tests/cli/test_check.py` + `tests/cli/test_run.py:22-58` | role-match |
| `tests/harness/test_cache_freshness.py` | NEW | test (unit) | request-response | `tests/harness/test_session.py` class-based fixture style | role-match |

### Wave 2 — `.voss` authoring + boot dispatch

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `voss/harness/agent/loop.voss` | NEW | sample (.voss source) | event-driven (async ctx) | `samples/research.voss:1-41` (agent + ctx + try) | role-match |
| `voss/harness/agent/router.voss` | NEW | sample (.voss source) | request-response | `samples/classify.voss:1-13` (probable<T> + gate) | exact |
| `voss/harness/agent/planner.voss` | NEW | sample (.voss source) | request-response | `samples/classify.voss:1-13` + `samples/research.voss` | exact |
| `voss/harness/agent/executor.voss` | NEW | sample (.voss source) | event-driven | `samples/research.voss` (use import + control flow) | role-match |
| `voss/harness/agent/reviewer.voss` | NEW | sample (.voss source) | transform | `samples/research.voss:1-41` (try/catch + yield) | role-match |
| `voss/harness/agent.py` (extract `_run_step_loop`) | MODIFY | harness service | event-driven | self (existing tool-dispatch loop at lines 184-207) | exact (in-file) |
| `voss/harness/tools.py:ToolEntry.invoke_dict` | MODIFY (+3 LOC) | model registry helper | request-response | self (existing `invoke(**kwargs)` at line 37-38) | exact (in-file) |
| `voss/harness/cli.py:_resolve_run_turn` | MODIFY | controller (dispatch) | request-response | self (existing `_resolve_auth_or_die` at 108-147) | exact (in-file) |
| `voss/harness/config.py` | MODIFY (+5 LOC) | config reader | static | self (existing `_parse_harness_section` at 22-27 already returns `{k: v}`; no change needed if caller reads `["backend"]`) | exact (in-file) |
| `tests/harness/test_boot_dispatch.py` | NEW | test (unit) | request-response | `tests/harness/test_agent_integration.py:21-50` (FakeProvider unit pattern) | role-match |

### Wave 3 — parity + DOG-07 smoke

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `tests/harness/test_voss_loop_parity.py` | NEW | test (integration) | event-driven (asyncio) | `tests/harness/test_agent_integration.py:1-180` (FakeProvider + asyncio.run pattern) | exact |
| `tests/harness/test_dog07_smoke.py` | NEW | test (e2e smoke) | request-response (subprocess) | `tests/examples/helpers.py:60-69` `run_voss` subprocess pattern + `tests/cli/test_run.py:36-78` | role-match |

### Wave 4 — CI gate + docs + doctor

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `.github/workflows/ci.yml` (add step) | MODIFY (+2 LOC) | CI config (yaml) | static | self (existing `pip install -e ".[dev]"` line 25 + `pytest` line 26) | exact (in-file) |
| `README.md` (install one-liner) | MODIFY | docs | static | self (existing install block) | exact (in-file) |
| `voss/harness/diagnostics.py` (cache-freshness row) | MODIFY (+15 LOC) | doctor row | request-response | self (existing `check_project_dirs` at 158-178) | exact (in-file) |
| `tests/harness/test_doctor.py` (assert cache row) | MODIFY | test (unit) | request-response | self (existing harness doctor test) | exact (in-file) |

---

## Pattern Assignments

### `voss/grammar.lark` (line 174-175) — Wave 0 Pattern 1a

**Analog:** Self. Existing rule already uses lark optional-suffix shape elsewhere (e.g., `try_stmt: "try" block "catch" [NAME] block` at line 133 uses `[NAME]` for an optional terminal — same idiom).

**Current shape** (grammar.lark:174-175):
```lark
use_stmt: "use" use_path
use_path: IDENT ("::" IDENT)*
```

**Target shape:**
```lark
use_stmt: "use" use_path ("as" IDENT)?
use_path: IDENT ("::" IDENT)*
```

**Adaptation notes:**
- Single-line edit. `("as" IDENT)?` is lark's optional group; mirrors `("::" IDENT)*` shape one line down.
- `"as"` is added as an anonymous string terminal; lark auto-creates it. No new terminal declaration needed (verified against grammar.lark:177-190 terminals block — only operator tokens declared there).
- Parser receives the alias as an extra child only when present; parser-side change (next section) handles both lengths.

---

### `voss/parser.py:714-715` — Wave 0 Pattern 1a

**Analog:** Self. `use_stmt` already exists, just always sets `alias=None`. AST shape (`UseStmt(path, alias)`) already supports the field — verified by `tests/codegen/test_imports.py:56-60` which asserts `alias` roundtrips.

**Current shape** (parser.py:714-715):
```python
def use_stmt(self, meta, children):
    return UseStmt(span=_span(meta, self.file), path=children[0], alias=None)
```

**Target shape** (per M4-RESEARCH §Code Examples line 873-879):
```python
def use_stmt(self, meta, children):
    path = children[0]
    alias = None
    if len(children) > 1 and children[1] is not None:
        alias = str(children[1])
    return UseStmt(span=_span(meta, self.file), path=path, alias=alias)
```

**Adaptation notes:**
- 4-line replacement. `children[0]` is the `use_path` tuple already (parser.py:711-712 `use_path` method returns `tuple(str(t) for t in children)`).
- `children[1]` when present is a `Token` for IDENT; `str(Token)` extracts the lexeme.
- No new imports.

---

### `voss/codegen.py:441-446` — Wave 0 Pattern 1b (auto-await for `use`-imported callees)

**Analog:** Self. The existing await-emission condition is the exact shape to extend.

**Current shape** (codegen.py:441-446):
```python
if (
    await_context
    and isinstance(call.callee, Identifier)
    and call.callee.name in self.generated_fns
):
    text = f"await {text}"
```

**Target shape** (per M4-RESEARCH lines 911-934):
```python
# 1) Add field to ExpressionEmitter dataclass (~line 349):
@dataclass
class ExpressionEmitter:
    ...
    generated_fns: frozenset[str] = field(default_factory=frozenset)
    use_imported_names: frozenset[str] = field(default_factory=frozenset)  # NEW
    ...

# 2) Replace the await condition at lines 441-446:
if (
    await_context
    and isinstance(call.callee, Identifier)
    and (
        call.callee.name in self.generated_fns
        or call.callee.name in self.use_imported_names  # NEW
    )
):
    text = f"await {text}"

# 3) Populate at ProgramEmitter.emit (~line 1196-1197) where ExpressionEmitter is constructed:
expr_emitter = ExpressionEmitter(
    self.imports,
    generated_fns=fn_names,
    use_imported_names=frozenset(
        stmt.alias or stmt.path[-1]
        for stmt in self.program.body
        if isinstance(stmt, UseStmt)
    ),
)
```

**Adaptation notes:**
- Three insertion points; total ~10 LOC diff in codegen.
- `stmt.alias or stmt.path[-1]` covers both `use foo::bar` (last segment is the bound name) and `use foo::bar as baz` (alias is the bound name).
- Aliased member-call (`h.run_turn(...)`) is NOT auto-awaited by this patch — see M4-RESEARCH Pitfall 1: M4 recommends NAME imports only (`use voss::harness::run_turn`), not aliased module imports. Don't try to extend the condition to `Member` callees in M4.

---

### `tests/parser/test_use_alias.py` (NEW) — Wave 0

**Analog:** `tests/codegen/test_imports.py:56-60` (`test_use_stmt_alias_is_preserved_when_ast_provides_alias` — proves codegen handles `alias` field; M4 mirrors at parser level).

**Target shape** (per M4-RESEARCH lines 883-895):
```python
# tests/parser/test_use_alias.py
from voss.parser import parse
from voss.ast import UseStmt


def test_use_with_alias_parses():
    program = parse("use foo::bar as baz\n", file="<test>")
    use = program.body[0]
    assert isinstance(use, UseStmt)
    assert use.path == ("foo", "bar")
    assert use.alias == "baz"


def test_use_without_alias_still_works():
    program = parse("use foo::bar\n", file="<test>")
    use = program.body[0]
    assert use.alias is None
```

**Adaptation notes:**
- Two tests minimum: alias present + alias absent (regression guard).
- Locate in `tests/parser/` directory (creates dir if absent; existing `tests/parser/test_examples.py` shows convention).
- No `pytest-asyncio`; plain `def` tests.

---

### `tests/codegen/test_await_use_import.py` (NEW) — Wave 0

**Analog:** `tests/codegen/test_imports.py:1-105` — uses `parse → analyze → generate_python` pipeline and asserts substrings on `result.source`.

**Target shape** (per M4-RESEARCH lines 938-947):
```python
# tests/codegen/test_await_use_import.py
from voss.parser import parse
from voss.analyzer import analyze
from voss.codegen import generate_python


def test_use_imported_async_fn_is_awaited():
    src = """
use foo::bar
fn caller() {
    bar()
}
"""
    program = parse(src, file="<test>")
    analysis = analyze(program, source_path="<test>", emit_indexes=False)
    result = generate_python(program, analysis=analysis)
    assert "await bar()" in result.source
    # Negative control: bare identifier without `use` is not awaited.
```

**Adaptation notes:**
- Use `emit_indexes=False` to keep test hermetic (M3 D-03 carry-forward; no HF encoder).
- Use source-text round-trip rather than hand-building AST (cleaner; matches existing codegen test style).

---

### `voss/harness/cache.py` (NEW, ~80 LOC) — Wave 1 Pattern 4

**Analog:** `voss/harness/cognition.py:254-310` — same shape: read-source-files-with-sha + write-JSON-manifest pattern. Uses sha1 (M2); M4 bumps to sha256 per D-14.

**Reference excerpt** (cognition.py:254-310, abbreviated):
```python
def build_repo_idx(cwd: Path, *, model: str = "...", token_count: Callable[[str], int] | None = None) -> Path:
    ...
    rows: list[dict] = []
    for p in sorted(cwd.rglob("*")):
        ...
        text = p.read_text(...)
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        rows.append({"path": rel, "sha1": digest, "tokens": tok, ...})
    payload = {"version": 1, "git_head": _git_head(cwd), "files": rows}
    target = cache_dir(cwd) / "repo.idx"
    target.write_text(json.dumps(payload, indent=2) + "\n")
    return target
```

**Target shape** (per M4-RESEARCH lines 484-565 — full module). Key constants and helpers:
```python
"""Compiled-harness cache helpers (M4 D-13/D-14/D-15)."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from voss import __version__ as VOSS_VERSION
from .sandbox import write_cache

HARNESS_AGENT_DIR = "voss/harness/agent"
CACHE_HARNESS_DIR = ".voss-cache/harness"
MANIFEST_NAME = "_manifest.json"
MANIFEST_VERSION = 1


@dataclass(frozen=True)
class ManifestEntry:
    sha256: str
    lines: int


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_source_shas(project_root: Path) -> dict[str, ManifestEntry]:
    src_dir = project_root / HARNESS_AGENT_DIR
    out: dict[str, ManifestEntry] = {}
    for p in sorted(src_dir.glob("*.voss")):
        text = p.read_text()
        out[p.name] = ManifestEntry(sha256=sha256_text(text), lines=text.count("\n") + 1)
    return out


def write_manifest(project_root: Path, entries: dict[str, ManifestEntry]) -> Path:
    payload = {
        "version": MANIFEST_VERSION,
        "voss_version": VOSS_VERSION,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "sources": {name: {"sha256": e.sha256, "lines": e.lines} for name, e in entries.items()},
    }
    return write_cache(project_root, f"{CACHE_HARNESS_DIR}/{MANIFEST_NAME}",
                       json.dumps(payload, indent=2) + "\n")


def load_manifest(project_root: Path) -> dict | None:
    path = project_root / CACHE_HARNESS_DIR / MANIFEST_NAME
    if not path.exists():
        return None
    return json.loads(path.read_text())


def assert_fresh(project_root: Path) -> None:
    """Raise StaleHarnessCacheError if cache missing or any source sha mismatches."""
    from .diagnostics import StaleHarnessCacheError
    manifest = load_manifest(project_root)
    if manifest is None:
        raise StaleHarnessCacheError(
            "compiled harness cache stale — run: voss compile voss/harness/agent/"
        )
    if manifest.get("voss_version") != VOSS_VERSION:
        raise StaleHarnessCacheError(
            "compiled harness cache stale — run: voss compile voss/harness/agent/"
        )
    current = compute_source_shas(project_root)
    for name, entry in current.items():
        record = manifest.get("sources", {}).get(name, {})
        if record.get("sha256") != entry.sha256:
            raise StaleHarnessCacheError(
                "compiled harness cache stale — run: voss compile voss/harness/agent/"
            )
```

**Adaptation notes:**
- D-10 mandates the EXACT message `compiled harness cache stale — run: voss compile voss/harness/agent/`. Test asserts on this exact string; do not embed dynamic details (sha mismatches, version values) in the message — researcher's verbose variants are illustrative but tests pin the canonical string.
- sha256 not sha1 (D-14).
- `VOSS_VERSION` import: confirm `voss/__init__.py` exports `__version__`; if not, fall back to `importlib.metadata.version("voss")`.
- All writes go through `sandbox.write_cache` (D-15) — never `Path.write_text` directly.
- `assert_fresh` is the function `_resolve_run_turn` and the doctor row both call.

---

### `voss/harness/sandbox.py` (MODIFY, +15 LOC) — Wave 1

**Analog:** Self. Existing `jail_path` (lines 20-31) gives the double-jail invariant; `voss/cli.py:_write_text_atomic` (56-72) gives the atomic-write pattern.

**Reference excerpts:**

`jail_path` (sandbox.py:20-31):
```python
def jail_path(cwd: Path, target: str | os.PathLike) -> Path:
    """Resolve target relative to cwd; reject paths that escape cwd."""
    cwd_real = cwd.resolve()
    p = Path(target)
    if not p.is_absolute():
        p = cwd_real / p
    p = p.resolve()
    try:
        p.relative_to(cwd_real)
    except ValueError as e:
        raise SandboxError(f"path escapes cwd: {p}") from e
    return p
```

`_write_text_atomic` (cli.py:56-72) — mkstemp + os.replace pattern.

**Target shape** (per M4-RESEARCH lines 466-478):
```python
def write_cache(project_root: Path, relpath: str | os.PathLike, text: str) -> Path:
    """Write text to project_root/.voss-cache/<relpath> atomically; jail enforced.

    relpath must be relative; jail_path() prevents escape from .voss-cache.
    """
    cache_root = jail_path(project_root, ".voss-cache")
    cache_root.mkdir(parents=True, exist_ok=True)
    target = jail_path(cache_root, relpath)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(target)
    return target
```

**Adaptation notes:**
- Double `jail_path`: once for `.voss-cache` (inside `project_root`), again for `relpath` (inside `.voss-cache`). Prevents both forms of escape.
- Atomic via `tmp.replace(target)` — `Path.replace` calls `os.replace` which is POSIX-atomic.
- Append at end of `voss/harness/sandbox.py`; no new imports beyond `Path` (already imported).

---

### `voss/harness/diagnostics.py` (MODIFY) — Wave 1 + Wave 4

**Analog:** Self. Existing `check_project_dirs` at 158-178 is the closest shape for the cache-freshness row (D-16 doctor integration).

**Reference excerpt** (diagnostics.py:158-178):
```python
def check_project_dirs(cwd: Path) -> Check:
    voss_dir = cwd / ".voss"
    cache_dir = cwd / ".voss-cache"
    failures: list[str] = []
    for d in (voss_dir, cache_dir):
        if d.exists():
            continue
        try:
            d.mkdir(parents=True, exist_ok=True)
            d.rmdir()
        except OSError as e:
            failures.append(f"{d.name}: {e}")
    if failures:
        return Check(
            "project dirs",
            CheckResult.WARN,
            detail="; ".join(failures),
            fix=f"(informational for M1) mkdir -p {voss_dir} {cache_dir}",
        )
    return Check("project dirs", CheckResult.OK, detail=".voss/, .voss-cache/ creatable")
```

**Target additions** (two changes, end-of-file or near existing checks):

1. **Exception class** (D-10) — add to `voss/harness/diagnostics.py` (preferred per CONTEXT D-10) OR `voss/exceptions.py` (alternative). Match existing `VossError` shape from `voss/exceptions.py:4-5`:
```python
from voss.exceptions import VossError

class StaleHarnessCacheError(VossError):
    """Raised when the compiled .voss-cache/harness/ is stale relative to sources.

    Message is fixed (D-10): always ends with the suggestion
    'run: voss compile voss/harness/agent/'. Tests pin this string.
    """
    pass
```

2. **Cache-freshness row** (D-16) — informational, never blocking:
```python
def check_harness_cache(cwd: Path) -> Check:
    """Informational (D-16): compiled harness cache freshness. WARN on stale, OK on fresh, OK on missing."""
    from . import cache as harness_cache
    src_dir = cwd / harness_cache.HARNESS_AGENT_DIR
    if not src_dir.exists():
        return Check("harness cache", CheckResult.OK, detail="no harness sources")
    try:
        harness_cache.assert_fresh(cwd)
    except StaleHarnessCacheError:
        return Check(
            "harness cache",
            CheckResult.WARN,
            detail="stale — compiled artifacts out of sync with .voss sources",
            fix="voss compile voss/harness/agent/",
        )
    return Check("harness cache", CheckResult.OK, detail=".voss-cache/harness/ fresh")
```

3. **Insert into `run_all_checks` ordering** (line 181-191) — append after `check_project_dirs(cwd)`:
```python
def run_all_checks(cwd: Path) -> list[Check]:
    return [
        check_python_version(),
        check_voss_import(),
        check_provider_auth(),
        check_git_on_path(),
        check_cwd_writable(cwd),
        check_config_dirs_creatable(),
        check_project_dirs(cwd),
        check_harness_cache(cwd),  # NEW (M4 D-16)
    ]
```

**Adaptation notes:**
- WARN not FAIL — D-16 mandates "informational only, never blocking". The `aggregate_exit_code` at line 194-198 already treats WARN as exit 0.
- Lazy import `from . import cache as harness_cache` inside the function to avoid circular import (cache.py imports `from .diagnostics import StaleHarnessCacheError`).
- The `fix=` field is the same suggestion text from D-10; tests can grep `fix == "voss compile voss/harness/agent/"`.

---

### `voss/cli.py:check` (~line 209) — Wave 1 dir-walk Pattern 3

**Analog:** Self. Current single-file body wraps `_parse_file → analyze → _print_diagnostics → _exit_for_diagnostics`. Dir mode wraps the same per-file call in a `for` loop.

**Current shape** (cli.py:204-228):
```python
@main.command("check")
@click.argument("source", type=click.Path(path_type=Path))
...
def check(source, warnings_as_errors, cache_dir, project_root):
    program = _parse_file(source)
    try:
        result = analyze(
            program,
            source_path=str(source),
            project_root=project_root,
            cache_dir=cache_dir,
            emit_indexes=False,
        )
    except VossError as exc:
        raise click.ClickException(str(exc))
    _print_diagnostics(result.diagnostics)
    _exit_for_diagnostics(result, warnings_fail=warnings_as_errors)
```

**Target shape** (per M4-RESEARCH lines 421-453):
```python
def _walk_voss_sources(source: Path) -> list[Path]:
    """Return [source] if file, else sorted([p for p in source.rglob('*.voss')])."""
    if source.is_file():
        return [source]
    if source.is_dir():
        return sorted(source.rglob("*.voss"))
    raise click.ClickException(f"not a file or directory: {source}")


def check(source, warnings_as_errors, cache_dir, project_root):
    files = _walk_voss_sources(source)
    error_count = 0
    warning_count = 0
    for f in files:
        program = _parse_file(f)
        try:
            result = analyze(
                program,
                source_path=str(f),
                project_root=project_root,
                cache_dir=cache_dir,
                emit_indexes=False,  # M3 D-03 carry-forward — MUST stay False (Pitfall 7)
            )
        except VossError as exc:
            raise click.ClickException(str(exc))
        _print_diagnostics(result.diagnostics)
        error_count += len(result.errors)
        warning_count += len(result.warnings)
    if len(files) > 1:
        click.echo(f"{error_count} errors, {warning_count} warnings across {len(files)} files")
    if error_count > 0:
        raise click.exceptions.Exit(code=1)
    if warnings_as_errors and warning_count > 0:
        raise click.exceptions.Exit(code=1)
```

**Adaptation notes:**
- `emit_indexes=False` is the M3 D-03 invariant; copy verbatim. M4 Pitfall 7 calls out the copy-paste trap where dir-walk implementer borrows `_compile_source`'s `emit_indexes=True` — DO NOT.
- Summary line only printed when `len(files) > 1` (D-07; single-file behavior unchanged).
- `Diagnostic.__str__` already renders `<file>:<line>:<col>: <severity> <message>` (verified via existing `_print_diagnostics` at cli.py:40-42).
- `_walk_voss_sources` is a top-of-file helper; reused by `compile`.

---

### `voss/cli.py:compile` (~line 147) — Wave 1 dir-walk + manifest Pattern 3+4

**Analog:** Self. Existing per-file `_compile_source` (lines 75-118) is the inner call; wrapper computes per-file cache paths and emits manifest.

**Current shape** (cli.py:147-167):
```python
@main.command("compile")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("-o", "--output", "output", type=click.Path(path_type=Path), default=None)
@click.option("--cache-dir", "cache_dir", type=click.Path(path_type=Path), default=Path(".voss-cache"))
@click.option("--project-root", "project_root", type=click.Path(path_type=Path), default=None)
@click.option("--verbose", is_flag=True, default=False)
def compile(source, output, cache_dir, project_root, verbose):
    _compile_source(source, output_path=output, project_root=project_root,
                    cache_dir=cache_dir, verbose=verbose)
```

**Target shape** (per M4-RESEARCH lines 956-967):
```python
def compile(source, output, cache_dir, project_root, verbose):
    files = _walk_voss_sources(source)
    proj = Path(project_root or Path.cwd())
    for f in files:
        if source.is_dir():
            # dir mode: per-file output under .voss-cache/harness/
            target = proj / cache_dir / "harness" / f.with_suffix(".py").name
        else:
            target = output  # single-file mode unchanged
        _compile_source(f, output_path=target, project_root=project_root,
                        cache_dir=cache_dir, verbose=verbose)
    if source.is_dir() and source.name == "agent":
        # Harness dir mode — emit manifest.
        from voss.harness import cache as harness_cache
        entries = harness_cache.compute_source_shas(proj)
        harness_cache.write_manifest(proj, entries)
        if verbose:
            click.echo(f"wrote manifest with {len(entries)} sources")
```

**Adaptation notes:**
- Single-file mode (`source.is_file()`) preserves the old `output` flag behavior.
- Cache paths MUST be inside `.voss-cache/` (Pitfall 3: do NOT let `_default_output_path` write next to source).
- Manifest only when `source.name == "agent"` (a heuristic for harness-dir mode). Alternative: an explicit `--manifest` flag; researcher recommends the heuristic for now.
- Lazy import `voss.harness.cache` to keep CLI startup fast.

---

### `tests/harness/test_voss_check_dir.py` (NEW) — Wave 1

**Analog:** `tests/cli/test_check.py:70-97` — `CliRunner + isolated_filesystem + invariant assertions on filesystem state`.

**Reference pattern** (test_check.py:70-80):
```python
def test_check_does_not_emit_indexes_or_cache_files():
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        path = _write("clean.voss", _CLEAN_SOURCE)
        result = runner.invoke(main, ["check", "--cache-dir", ".voss-cache", str(path)])
        assert result.exit_code == 0, result.output
        fs_path = Path(fs)
        assert not (fs_path / ".voss-cache").exists()
        assert not list(fs_path.glob("**/*.idx"))
```

**Target tests** (per M4-VALIDATION row `cli-check-dir-walk` + Pitfall 7 sentinel):
```python
def test_check_dir_walks_and_aggregates(tmp_path):
    """D-05 / D-07: dir mode rglobs *.voss, aggregates diagnostics, prints summary."""
    (tmp_path / "a.voss").write_text("let x = 1\n")
    sub = tmp_path / "sub"; sub.mkdir()
    (sub / "b.voss").write_text("let y = 2\n")
    runner = CliRunner()
    result = runner.invoke(main, ["check", str(tmp_path)])
    assert result.exit_code == 0
    assert "across 2 files" in result.output


def test_check_dir_does_not_load_hf_encoder(tmp_path):
    """D-06 / M3 D-03 carry-forward (Pitfall 7): dir-walk must keep emit_indexes=False."""
    (tmp_path / "a.voss").write_text("let x = 1\n")
    runner = CliRunner()
    result = runner.invoke(main, ["check", str(tmp_path)])
    assert result.exit_code == 0
    import sys
    assert "sentence_transformers" not in sys.modules


def test_check_single_file_summary_suppressed(tmp_path):
    """D-07: summary line only when len(files) > 1."""
    (tmp_path / "a.voss").write_text("let x = 1\n")
    runner = CliRunner()
    result = runner.invoke(main, ["check", str(tmp_path / "a.voss")])
    assert result.exit_code == 0
    assert "across" not in result.output


def test_check_dir_aggregates_errors_and_exits_nonzero(tmp_path):
    (tmp_path / "good.voss").write_text("let x = 1\n")
    (tmp_path / "bad.voss").write_text("???invalid syntax\n")
    runner = CliRunner()
    result = runner.invoke(main, ["check", str(tmp_path)])
    assert result.exit_code == 1
```

**Adaptation notes:**
- Mirror `tests/cli/test_check.py` style: plain `def` tests, `CliRunner`, `tmp_path`.
- The `sentence_transformers` sentinel is the Pitfall 7 regression guard — must run in this file because it asserts `sys.modules` state after a `voss check` call.

---

### `tests/harness/test_voss_compile_dir.py` (NEW) — Wave 1

**Analog:** Same `CliRunner` pattern + `tests/cli/test_run.py:22-58` (subprocess output capture).

**Target tests:**
```python
def test_compile_dir_emits_per_file_artifacts(tmp_path):
    """D-13: per-file .py artifacts under .voss-cache/harness/."""
    agent = tmp_path / "voss" / "harness" / "agent"
    agent.mkdir(parents=True)
    (agent / "loop.voss").write_text("let x = 1\n")
    (agent / "router.voss").write_text("let y = 2\n")
    runner = CliRunner()
    result = runner.invoke(main, ["compile", str(agent), "--project-root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".voss-cache" / "harness" / "loop.py").exists()
    assert (tmp_path / ".voss-cache" / "harness" / "router.py").exists()
    # Pitfall 3: must NOT write next to source
    assert not (agent / "loop.py").exists()


def test_manifest_schema(tmp_path):
    """D-13 / D-14: manifest matches schema with sha256+lines per source."""
    agent = tmp_path / "voss" / "harness" / "agent"
    agent.mkdir(parents=True)
    (agent / "loop.voss").write_text("let x = 1\n")
    runner = CliRunner()
    runner.invoke(main, ["compile", str(agent), "--project-root", str(tmp_path)])
    manifest_path = tmp_path / ".voss-cache" / "harness" / "_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["version"] == 1
    assert isinstance(data["voss_version"], str)
    assert "compiled_at" in data
    entry = data["sources"]["loop.voss"]
    assert "sha256" in entry and len(entry["sha256"]) == 64  # sha256 hex
    assert "lines" in entry and entry["lines"] >= 1


def test_voss_cache_ignored(tmp_path):
    """Pitfall 5: .voss-cache/ should be gitignored."""
    # Verify repo root .gitignore contains '.voss-cache/' — this is a repo
    # invariant test, not a tmp_path test.
    gitignore = Path(__file__).resolve().parents[2] / ".gitignore"
    assert ".voss-cache/" in gitignore.read_text() or ".voss-cache" in gitignore.read_text()
```

**Adaptation notes:**
- sha256 hex is 64 chars; assert length to catch sha1 (40) leakage.
- The `test_voss_cache_ignored` test reaches outside `tmp_path` to check repo `.gitignore` — that's intentional per Pitfall 5.

---

### `tests/harness/test_cache_freshness.py` (NEW) — Wave 1

**Analog:** `tests/harness/test_session.py` class-based + `tmp_path` fixture pattern (M2 PATTERNS already documented).

**Target tests:**
```python
def test_assert_fresh_passes_after_compile(tmp_path):
    """D-14: fresh cache validates after voss compile."""
    agent = tmp_path / "voss" / "harness" / "agent"
    agent.mkdir(parents=True)
    (agent / "loop.voss").write_text("let x = 1\n")
    runner = CliRunner()
    runner.invoke(main, ["compile", str(agent), "--project-root", str(tmp_path)])
    from voss.harness import cache as harness_cache
    harness_cache.assert_fresh(tmp_path)  # no raise


def test_stale_cache_raises_on_source_change(tmp_path):
    """D-10: sha mismatch raises StaleHarnessCacheError with canonical message."""
    agent = tmp_path / "voss" / "harness" / "agent"
    agent.mkdir(parents=True)
    (agent / "loop.voss").write_text("let x = 1\n")
    runner = CliRunner()
    runner.invoke(main, ["compile", str(agent), "--project-root", str(tmp_path)])

    # Mutate source — now sha mismatches.
    (agent / "loop.voss").write_text("let x = 2\n")

    from voss.harness import cache as harness_cache
    from voss.harness.diagnostics import StaleHarnessCacheError
    with pytest.raises(StaleHarnessCacheError) as exc:
        harness_cache.assert_fresh(tmp_path)
    assert "voss compile voss/harness/agent/" in str(exc.value)


def test_missing_manifest_raises(tmp_path):
    """D-10: missing _manifest.json raises (no silent fallback)."""
    from voss.harness import cache as harness_cache
    from voss.harness.diagnostics import StaleHarnessCacheError
    (tmp_path / "voss" / "harness" / "agent").mkdir(parents=True)
    (tmp_path / "voss" / "harness" / "agent" / "loop.voss").write_text("x\n")
    with pytest.raises(StaleHarnessCacheError):
        harness_cache.assert_fresh(tmp_path)


def test_stale_cache_raises_before_import(tmp_path, monkeypatch):
    """Pitfall 4: _resolve_run_turn calls assert_fresh BEFORE dynamic import."""
    # Setup: compile, then mutate source.
    ...
    monkeypatch.setenv("VOSS_HARNESS", "compiled")
    monkeypatch.chdir(tmp_path)
    from voss.harness.cli import _resolve_run_turn
    with pytest.raises(StaleHarnessCacheError):
        _resolve_run_turn()
    import sys
    assert "voss_compiled_harness_loop" not in sys.modules
```

**Adaptation notes:**
- Pin the exact suggestion string `"voss compile voss/harness/agent/"` in `str(exc.value)`.
- Pitfall 4 test asserts the import did NOT happen via `sys.modules` check.

---

### `voss/harness/agent/loop.voss` (NEW, ~30 LOC) — Wave 2 Pattern 2

**Analog:** `samples/research.voss:1-41` — agent + ctx + try/catch + use import. Also the pseudo-`.voss` comment block in `voss/harness/agent.py:114-125` which is the design target.

**Reference excerpt** (research.voss-style + the agent.py pseudo-comment):
```
"""
ctx(budget: token_budget) {
    let plan: probable<Plan> = ask(...)
    if plan @ p >= threshold {
        for step in plan.steps: tool.invoke(step)
        yield review(results)
    } else {
        yield clarify(plan.open_question)
    }
}
"""
```

**Target shape** (per M4-RESEARCH lines 329-361):
```voss
# loop.voss
# Demonstrates: ctx(budget: N tokens), control flow, calls into Python helpers
# (_run_step_loop), and probable<T> + confidence gate. Per M4 D-02 thin .voss.
use voss::harness::agent::TurnResult
use voss::harness::agent::_run_step_loop
use voss::harness::tools::ToolEntry
use voss::harness::permissions::PermissionGate

fn run_turn(
    task: string,
    tools: any,
    cwd: any,
    renderer: any,
    confidence_threshold: float = 0.60,
    token_budget: int = 60000,
    model: any = null,
    provider: any = null,
    history: any = null,
    permissions: any = null,
) -> any {
    ctx(budget: 60000 tokens) {
        let route = route_intent(task)
        let plan_result: probable<any> = plan_task(task, tools, route, provider, model)
        if plan_result @ p >= confidence_threshold {
            let results = _run_step_loop(plan_result.value.steps, tools, permissions, renderer)
            return review(plan_result.value, results, history, task)
        } else {
            return clarify(plan_result.value, renderer)
        }
    }
}
```

**Adaptation notes:**
- Uses NAME imports (not aliased) per Pitfall 1 recommendation.
- Calls into `_run_step_loop` (Python helper extracted from `agent.py:184-207`) per Q-2 recommendation; avoids the no-`for` problem in `.voss`.
- Top comment per M3 D-14 convention: second `#` line lists primitives.
- Uses `any` for complex Python types (`tools: dict[str, ToolEntry]` doesn't parse cleanly; `any` keeps the `.voss` thin).
- `route_intent`, `plan_task`, `review`, `clarify` are forward-references to the other `.voss` files (loaded as a single program at compile time OR each compiled separately and imported via Python — see boot dispatch).

---

### `voss/harness/agent/router.voss` (NEW, ~20 LOC) — Wave 2 Pattern 2

**Analog:** `samples/classify.voss:1-13` — `probable<string>` + confidence gate.

**Target shape** (per M4-RESEARCH lines 364-374):
```voss
# router.voss
# Demonstrates: probable<string> for intent classification, confidence gate.
fn route_intent(task: string) -> string {
    let intent: probable<string> = ask("Is this a slash command or natural-language task? " + task)
    if intent @ p >= 0.80 {
        return intent.value
    } else {
        return "natural"
    }
}
```

**Adaptation notes:**
- Pure `.voss`; no Python imports.
- Confidence gate `@ p >= 0.80` is the existing M3-validated grammar (classify.voss:8).

---

### `voss/harness/agent/planner.voss` (NEW, ~30 LOC) — Wave 2 Pattern 2

**Analog:** `samples/classify.voss` (probable<T> shape) + `samples/research.voss` (use imports).

**Target shape** (per M4-RESEARCH lines 377-385):
```voss
# planner.voss
# Demonstrates: probable<Plan>, ask-with-schema, confidence gate (handled by loop.voss).
use voss::harness::agent::Plan

fn plan_task(task: string, tools: any, route: string, provider: any, model: any) -> probable<Plan> {
    let plan: probable<Plan> = ask("Task: " + task)
    return plan
}
```

**Adaptation notes:**
- `use voss::harness::agent::Plan` imports the pydantic model (D-02 thin .voss).
- `probable<Plan>` parses with the Pattern 1b auto-await sub-plan in place (because `ask(...)` is a runtime function).

---

### `voss/harness/agent/executor.voss` (NEW, ~30 LOC) — Wave 2 Pattern 2

**Analog:** `samples/research.voss` (use imports + control flow).

**Target shape:**
```voss
# executor.voss
# Demonstrates: dispatch to Python helper (no `for` loop in .voss, per Q-2/Q-3).
# This file is intentionally thin — it forwards to _run_step_loop (Python helper
# in voss/harness/agent.py) which holds the existing tool-dispatch loop.
use voss::harness::agent::_run_step_loop

fn execute_steps(plan: any, tools: any, permissions: any, renderer: any) -> any {
    return _run_step_loop(plan.steps, tools, permissions, renderer)
}
```

**Adaptation notes:**
- `_run_step_loop` is the Python helper extracted from `agent.py:184-207` (next pattern).
- Auto-await fires on `_run_step_loop(...)` because Pattern 1b's `use_imported_names` set covers it (the imported name is `_run_step_loop`; bare-Identifier callee).
- Test sentinel: `grep -q "await " .voss-cache/harness/executor.py` (M4-VALIDATION row `executor-voss-file`).

---

### `voss/harness/agent/reviewer.voss` (NEW, ~20 LOC) — Wave 2 Pattern 2

**Analog:** `samples/research.voss:1-41` (try/catch + yield).

**Target shape** (per M4-RESEARCH lines 399-409):
```voss
# reviewer.voss
# Demonstrates: try/catch around final synthesis, history append.
use voss::harness::agent::TurnResult

fn review(plan: any, results: any, history: any, task: string) -> any {
    try {
        # Substitute {{step_N}} placeholders in plan.final_when_done.
        # (Plan field is a string template; results is list[str].)
        let final = _substitute_placeholders(plan.final_when_done, results)
        return TurnResult(plan: plan, confidence: plan.confidence, final: final, tool_results: results, cost_usd: 0.0)
    } catch e {
        return TurnResult(plan: plan, confidence: 0.0, final: "<error during review>", tool_results: results, cost_usd: 0.0)
    }
}

fn clarify(plan: any, renderer: any) -> any {
    let question = plan.open_question
    return TurnResult(plan: plan, confidence: plan.confidence, final: question, tool_results: [], cost_usd: 0.0)
}
```

**Adaptation notes:**
- `_substitute_placeholders` is a small Python helper (~5 LOC) to add in `voss/harness/agent.py` alongside `_run_step_loop`; mirrors the `.replace(f"{{{{step_{i}}}}}", r)` loop at agent.py:210-211.
- `try/catch` is M3-grammar-validated (grammar.lark:133).
- The exact `TurnResult(field: value, ...)` named-arg constructor syntax must be verified against M3's named-arg call grammar; if not supported, use a Python helper `_make_turn_result(...)` instead.

---

### `voss/harness/agent.py` (MODIFY — extract `_run_step_loop`) — Wave 2

**Analog:** Self. Existing tool-dispatch loop at lines 184-207 is the body of the new helper.

**Reference excerpt** (agent.py:182-207):
```python
# Execute steps sequentially. Phase H3 will lower this to `gather(spawn ...)`.
gate = permissions or PermissionGate(auto_yes=True)
results: list[str] = []
for i, step in enumerate(plan.steps):
    entry = tools.get(step.name)
    if entry is None:
        results.append(f"<error: unknown tool {step.name!r}>")
        renderer.show_tool_call(step.name, step.args, "<unknown tool>", "error")
        continue
    allowed, why = gate.check(step.name, step.args, is_mutating=entry.is_mutating)
    if not allowed:
        text = f"<denied: {why}>"
        renderer.show_tool_call(step.name, step.args, text, "error")
        results.append(text)
        continue
    renderer.show_tool_call(step.name, step.args, "running…", "pending")
    try:
        res = await entry.invoke(**step.args)
        text = str(res)
    except Exception as e:
        text = f"<error: {e}>"
        renderer.show_tool_call(step.name, step.args, text, "error")
        results.append(text)
        continue
    renderer.show_tool_call(step.name, step.args, _summarize(text), "ok")
    results.append(text)
```

**Target shape:**
```python
async def _run_step_loop(
    plan_steps: list,
    tools: dict,
    permissions,
    renderer,
) -> list[str]:
    """Tool-dispatch loop extracted for executor.voss to call (M4 Q-2).

    Preserves existing semantics: permission gate, error capture, renderer events.
    """
    gate = permissions or PermissionGate(auto_yes=True)
    results: list[str] = []
    for step in plan_steps:
        entry = tools.get(step.name)
        if entry is None:
            results.append(f"<error: unknown tool {step.name!r}>")
            renderer.show_tool_call(step.name, step.args, "<unknown tool>", "error")
            continue
        allowed, why = gate.check(step.name, step.args, is_mutating=entry.is_mutating)
        if not allowed:
            text = f"<denied: {why}>"
            renderer.show_tool_call(step.name, step.args, text, "error")
            results.append(text)
            continue
        renderer.show_tool_call(step.name, step.args, "running…", "pending")
        try:
            res = await entry.invoke(**step.args)
            text = str(res)
        except Exception as e:  # noqa: BLE001
            text = f"<error: {e}>"
            renderer.show_tool_call(step.name, step.args, text, "error")
            results.append(text)
            continue
        renderer.show_tool_call(step.name, step.args, _summarize(text), "ok")
        results.append(text)
    return results
```

**Adaptation notes:**
- Then replace the inline loop in `run_turn` (lines 184-207) with `results = await _run_step_loop(plan.steps, tools, permissions, renderer)`. This keeps the Python `run_turn` (parity oracle, D-09) and the compiled `loop.voss` calling the SAME helper — Pitfall 8 mitigation.
- Test in `tests/harness/test_agent_integration.py` (existing) should pass unchanged.
- D-04 invariant preserved: `.voss` does not bypass the permission gate; it calls the helper which embeds it.

---

### `voss/harness/tools.py:ToolEntry.invoke_dict` (MODIFY, +3 LOC) — Wave 2

**Analog:** Self. Existing `invoke(**kwargs)` at line 37-38.

**Reference excerpt** (tools.py:37-38):
```python
def invoke(self, **kwargs: Any) -> Any:
    return self.descriptor.invoke(**kwargs)
```

**Target addition:**
```python
def invoke_dict(self, args: dict) -> Any:
    """Spread-helper for .voss callers that lack **kwargs syntax (Pattern 2 workaround)."""
    return self.descriptor.invoke(**args)
```

**Adaptation notes:**
- Pure passthrough; no behavior change.
- `_run_step_loop` may switch to `entry.invoke_dict(step.args)` for symmetry with `.voss` callers, but `entry.invoke(**step.args)` still works since `_run_step_loop` is Python.
- Optional in M4 if executor.voss only calls `_run_step_loop` and never `tool.invoke` directly — but include for completeness (researcher recommended; cheap).

---

### `voss/harness/cli.py:_resolve_run_turn` (NEW helper) — Wave 2 Pattern 5

**Analog:** Self. Existing `_resolve_auth_or_die(preference)` at lines 108-147 is the canonical "resolve-before-run" pattern.

**Reference excerpt** (cli.py:108-120):
```python
def _resolve_auth_or_die(preference: str) -> tuple[auth_mod.Resolution, ModelProvider]:
    """Pick an auth path, build a provider for it, or exit 2."""
    res = auth_mod.resolve(preference)
    if res.source == "none":
        click.echo(
            f"no usable credentials ({res.detail}). try one of:\n"
            ...,
            err=True,
        )
        sys.exit(2)
    ...
```

**Target shape** (per M4-RESEARCH lines 575-608):
```python
def _resolve_run_turn():
    """Pick the run_turn callable based on VOSS_HARNESS env > config.toml > default.

    D-08. Returns the callable; raises StaleHarnessCacheError if compiled is
    requested but cache is stale (D-10). No silent fallback.
    """
    from . import config as harness_config
    backend = (
        os.environ.get("VOSS_HARNESS")
        or harness_config.load_harness_config().get("backend")
        or "python"
    )
    if backend not in ("python", "compiled"):
        raise click.ClickException(
            f"invalid VOSS_HARNESS={backend!r}: expected 'python' or 'compiled'"
        )
    if backend == "python":
        from .agent import run_turn  # parity oracle (D-09)
        return run_turn

    # backend == "compiled"
    from . import cache as harness_cache
    cwd = Path.cwd()
    harness_cache.assert_fresh(cwd)  # MUST be before import (Pitfall 4)
    import importlib.util
    loop_py = cwd / harness_cache.CACHE_HARNESS_DIR / "loop.py"
    spec = importlib.util.spec_from_file_location("voss_compiled_harness_loop", loop_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_turn
```

**Call-site changes** in `do_cmd` (cli.py:235-244) and `chat_cmd`:
```python
# OLD:
result = asyncio.run(run_turn(text, tools=tools, ...))
# NEW:
run_turn = _resolve_run_turn()
result = asyncio.run(run_turn(text, tools=tools, ...))
```

Drop the module-top `from .agent import run_turn` at cli.py:23 to prevent eager Python wiring (or keep as `_python_run_turn` alias for internal callers — researcher's preference: keep alias).

**Adaptation notes:**
- Resolution order: env > config.toml > default (D-08).
- `assert_fresh` BEFORE import (Pitfall 4 sentinel test guards this).
- No try/except around `assert_fresh` — D-10 mandates loud propagation.
- `Path.cwd()` is the project_root assumption (Q-4 documented in install one-liner).

---

### `voss/harness/config.py` (MODIFY) — Wave 2

**Analog:** Self. `_parse_harness_section` at lines 22-27 already returns a dict; callers just read `.get("backend")`.

**Current shape:** `load_harness_config()` returns `dict[str, str]`. No code change needed — `_resolve_run_turn` reads `.get("backend")` which returns `None` when absent.

**Optional ergonomic addition:**
```python
def get_backend() -> str:
    """Read [harness] backend or default to 'python'."""
    return load_harness_config().get("backend") or "python"
```

**Adaptation notes:**
- No required code change if `_resolve_run_turn` calls `load_harness_config().get("backend")` directly.
- Optional `get_backend()` helper is purely for readability; researcher recommends inline `.get("backend")` to minimize diff.

---

### `tests/harness/test_boot_dispatch.py` (NEW) — Wave 2

**Analog:** `tests/harness/test_agent_integration.py:21-50` (FakeProvider unit pattern) + monkeypatch fixture.

**Target tests:**
```python
def test_resolve_python_by_default(monkeypatch):
    """D-08 default: VOSS_HARNESS unset → python backend."""
    monkeypatch.delenv("VOSS_HARNESS", raising=False)
    from voss.harness.cli import _resolve_run_turn
    fn = _resolve_run_turn()
    from voss.harness.agent import run_turn as python_run_turn
    assert fn is python_run_turn


def test_resolve_compiled_via_env(monkeypatch, tmp_path):
    """D-08: VOSS_HARNESS=compiled → compiled backend (requires fresh cache)."""
    # Pre-compile the harness sources into tmp_path.
    ...
    monkeypatch.setenv("VOSS_HARNESS", "compiled")
    monkeypatch.chdir(tmp_path)
    from voss.harness.cli import _resolve_run_turn
    fn = _resolve_run_turn()
    assert fn is not None
    assert fn.__name__ == "run_turn"


def test_invalid_backend_raises(monkeypatch):
    monkeypatch.setenv("VOSS_HARNESS", "rust")
    from voss.harness.cli import _resolve_run_turn
    with pytest.raises(click.ClickException):
        _resolve_run_turn()


def test_config_fallback(monkeypatch, tmp_path):
    """D-08: env unset, config.toml sets backend=compiled → compiled selected."""
    monkeypatch.delenv("VOSS_HARNESS", raising=False)
    # Monkeypatch load_harness_config to return {"backend": "compiled"}.
    monkeypatch.setattr(
        "voss.harness.config.load_harness_config",
        lambda: {"backend": "compiled"},
    )
    # Pre-compile cache, then call _resolve_run_turn.
    ...
```

**Adaptation notes:**
- Use `monkeypatch.delenv("VOSS_HARNESS", raising=False)` defensively — dev shells may have it set.
- Cache pre-compile setup is shared with parity test (Wave 3); extract to a `conftest.py` session-scoped fixture per Q-5.

---

### `tests/harness/test_voss_loop_parity.py` (NEW) — Wave 3 Pattern 6

**Analog:** `tests/harness/test_agent_integration.py:21-50` (`FakeProvider` + canned `Plan` + `asyncio.run` + `make_toolset`).

**Reference excerpt** (test_agent_integration.py:21-50):
```python
class FakeProvider:
    """Returns a canned Plan once, then echoes."""

    def __init__(self, plan: Plan, cost: float = 0.001):
        self.plan = plan
        self.cost = cost
        self.calls: list[dict] = []

    async def complete(self, *, messages, model, response_format=None, ...) -> ProviderResponse:
        self.calls.append({"model": model, "messages": messages, "schema": response_format})
        text = self.plan.model_dump_json()
        return ProviderResponse(
            text=text, model=model, prompt_tokens=50, completion_tokens=50,
            cost_usd=self.cost, raw={"fake": True},
            parsed=self.plan if response_format is Plan else None,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)
```

**Target shape** (per M4-RESEARCH lines 630-710):
```python
# tests/harness/test_voss_loop_parity.py
"""M4 D-11: same fixture, two backends, identical TurnResult.final + tool sequence."""
import asyncio
from pathlib import Path
import pytest

from voss.harness.agent import Plan, ToolCall
from voss.harness.permissions import PermissionGate
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset


# Pattern 6 / Pitfall 6: use FakeProvider (canned Plan), NOT StubProvider — parity
# is on TurnResult + tool sequence, not on prompt-fingerprint.
class FakeProvider:
    def __init__(self, plan: Plan):
        self.plan = plan; self.calls = []
    async def complete(self, *, messages, model, response_format=None, **_):
        from voss_runtime.providers.base import ProviderResponse
        self.calls.append({"model": model, "messages": messages})
        return ProviderResponse(
            text=self.plan.model_dump_json(),
            model=model, prompt_tokens=10, completion_tokens=10,
            cost_usd=0.0, raw={"fake": True},
            parsed=self.plan if response_format is Plan else None,
        )
    def count_tokens(self, *, text, model): return 1


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "fixture.md").write_text("noop fixture body\n")
    return tmp_path


def _fixture_plan() -> Plan:
    return Plan(
        rationale="read the noop fixture",
        steps=[ToolCall(name="fs_read", args={"path": "fixture.md"})],
        confidence=0.95,
        final_when_done="contents: {{step_0}}",
    )


def _run(project: Path, run_turn):
    return asyncio.run(run_turn(
        "noop summary of fixture.md",
        tools=make_toolset(project),
        cwd=project,
        renderer=PlainRenderer(),
        provider=FakeProvider(_fixture_plan()),
        permissions=PermissionGate(auto_yes=True),
    ))


def test_python_and_compiled_backends_agree(project: Path):
    """D-11: same task, same Plan, same tool sequence, same final."""
    from voss.harness.agent import run_turn as python_run_turn

    # Compiled backend: assert fresh, then dynamic import.
    from voss.harness import cache as harness_cache
    harness_cache.assert_fresh(project)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "voss_compiled_harness_loop_test",
        project / harness_cache.CACHE_HARNESS_DIR / "loop.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    compiled_run_turn = mod.run_turn

    py_result = _run(project, python_run_turn)
    voss_result = _run(project, compiled_run_turn)

    assert py_result.final == voss_result.final
    assert [s.name for s in py_result.plan.steps] == [s.name for s in voss_result.plan.steps]
    assert [s.args for s in py_result.plan.steps] == [s.args for s in voss_result.plan.steps]
```

**Adaptation notes:**
- FakeProvider not StubProvider (Pitfall 6).
- Session-scoped pre-compile fixture in `tests/harness/conftest.py` (Q-5):
  ```python
  @pytest.fixture(scope="session")
  def precompiled_harness(tmp_path_factory):
      project = tmp_path_factory.mktemp("voss-project")
      # Copy voss/harness/agent/*.voss into project/voss/harness/agent/
      # Run: python -m voss.cli compile <agent_dir> --project-root <project>
      ...
      return project
  ```
- Or simpler: have `project` fixture trigger the compile via `subprocess.run([sys.executable, "-m", "voss.cli", "compile", ...])`.

---

### `tests/harness/test_dog07_smoke.py` (NEW) — Wave 3

**Analog:** `tests/examples/helpers.py:60-69` `run_voss` subprocess pattern + M3 stub-hermetic env (`VOSS_HERMETIC=1`).

**Reference pattern** (helpers.py:60-69-ish, run_voss subprocess):
```python
def run_voss(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "voss.cli", *args],
        cwd=str(cwd), capture_output=True, text=True, env=env,
    )
```

**Target shape:**
```python
def test_dog07_voss_do_through_compiled_harness(tmp_path, monkeypatch):
    """DOG-07 / D-12: VOSS_HARNESS=compiled voss do '<fixture>' exits 0 + non-empty final."""
    # Setup project root: copy voss/harness/agent/ sources + write fixture.md.
    ...
    # Pre-compile.
    subprocess.run([sys.executable, "-m", "voss.cli", "compile",
                    "voss/harness/agent/", "--project-root", str(tmp_path)],
                   cwd=tmp_path, check=True)

    # Boot through compiled backend.
    env = os.environ.copy()
    env["VOSS_HARNESS"] = "compiled"
    env["VOSS_HERMETIC"] = "1"  # force StubProvider (M3 D-01)
    result = subprocess.run(
        [sys.executable, "-m", "voss.harness.cli", "do", "noop summary of fixture.md"],
        cwd=tmp_path, capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()  # non-empty TurnResult.final
```

**Adaptation notes:**
- Uses subprocess (not in-process) to test the real CLI dispatch path.
- `VOSS_HERMETIC=1` forces StubProvider — required because CI has no creds (M3 D-01).
- Subprocess inherits the parent env via `env=env`.

---

### `.github/workflows/ci.yml` (MODIFY) — Wave 4

**Analog:** Self. Existing `stub` job at lines 14-26.

**Reference excerpt** (ci.yml:14-26):
```yaml
jobs:
  stub:
    if: github.event_name == 'push' || github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing
```

**Target addition** (per M4-RESEARCH lines 970-976):
```yaml
      - run: pip install -e ".[dev]"
      - name: voss check harness sources (M4 DOG-06)
        run: python -m voss.cli check voss/harness/agent/
      - run: pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing
```

**Adaptation notes:**
- Insert AFTER `pip install -e ".[dev]"` and BEFORE `pytest`.
- Step fails CI on non-zero exit (default GH Actions behavior).
- M4-VALIDATION row `ci-gate` greps `grep -F "voss.cli check voss/harness/agent/" .github/workflows/ci.yml`.

---

### `README.md` (MODIFY) — Wave 4 D-16

**Analog:** Self. Existing install section.

**Target addition** (per M4-VALIDATION row `install-doc`):
- Append to the install section a one-liner:
  ```bash
  voss compile voss/harness/agent/
  ```
  with a sentence framing it as eager-compile for `VOSS_HARNESS=compiled` users.

**Adaptation notes:**
- M4-VALIDATION row `install-doc` greps `grep -F "voss compile voss/harness/agent/" README.md`.
- No script — pure docs edit.

---

### `tests/harness/test_doctor.py` (MODIFY) — Wave 4

**Analog:** Self (existing harness doctor test). Asserts on output of `run_all_checks(cwd)`.

**Target addition:**
```python
def test_doctor_reports_harness_cache_row(tmp_path):
    """D-16: doctor output includes a harness-cache freshness row."""
    from voss.harness.diagnostics import run_all_checks
    results = run_all_checks(tmp_path)
    names = [c.name for c in results]
    assert "harness cache" in names
```

**Adaptation notes:**
- Asserts row PRESENT (M4-VALIDATION row `doctor-cache-row`).
- Does NOT assert WARN/OK — that depends on whether `.voss-cache/harness/` exists in `tmp_path`. Smallest contract.

---

## Shared Patterns

### Loud-fail stale cache (D-10 mirror of M1 D-13 diagnose-don't-fix)
**Source:** `voss/harness/cache.py:assert_fresh` (new) + `voss/exceptions.py:VossError`.
**Apply to:** Boot-path dispatch (`_resolve_run_turn`), parity test setup, doctor row.
**Concrete:** Always raise `StaleHarnessCacheError` with the exact message `compiled harness cache stale — run: voss compile voss/harness/agent/`. Never silent fallback to Python. Tests pin the exact string.

### Sandboxed cache write (D-15 + M2 D-06)
**Source:** `voss/harness/sandbox.py:jail_path` (existing) + `write_cache` (new wrapper).
**Apply to:** Every write under `.voss-cache/harness/` — compile manifest, per-file `.py` artifacts.
**Concrete:**
```python
target = sandbox.write_cache(project_root, ".voss-cache/harness/loop.py", source_text)
```
Never `Path.write_text(...)` directly. Atomic via `tmp.replace(target)`.

### Schema-versioned manifest JSON
**Source:** `voss/harness/cognition.py:build_repo_idx` (lines 254-310) — same shape: `{"version": int, "files": [...]}`.
**Apply to:** `voss/harness/cache.py:write_manifest`.
**Concrete:** Top-level `"version": 1` is the loud-fail key — version mismatch raises `StaleHarnessCacheError`. sha256 (D-14), not sha1.

### Click-CliRunner test pattern
**Source:** `tests/cli/test_check.py:70-97` + `tests/cli/test_run.py:22-58`.
**Apply to:** `test_voss_check_dir.py`, `test_voss_compile_dir.py`.
**Concrete:**
```python
runner = CliRunner()
result = runner.invoke(main, ["check", str(tmp_path)])
assert result.exit_code == 0
```
Capture stderr separately via `CliRunner(mix_stderr=False)` if testing diagnostics output routing.

### Hermetic provider for parity (M3 D-01 carry-forward)
**Source:** `voss_runtime/providers/__init__.py:get()` (M3 auto-fallback) + `tests/harness/test_agent_integration.py:FakeProvider`.
**Apply to:** Parity test (Wave 3), DOG-07 smoke test.
**Concrete:** Either pass `FakeProvider(_fixture_plan())` explicitly (parity test — recommended per Pitfall 6) OR set `VOSS_HERMETIC=1` to force StubProvider (smoke test — for the CLI dispatch path).

### Per-file diagnostic aggregation
**Source:** `voss/diagnostics.py:Diagnostic.__str__` already formats `<file>:<line>:<col>: <severity> <message>`.
**Apply to:** `voss/cli.py:check` dir-mode (D-07).
**Concrete:** Iterate `_print_diagnostics(result.diagnostics)` per file. Track running totals. Emit summary line only when `len(files) > 1`.

### `emit_indexes=False` carry-forward (M3 D-03)
**Source:** `voss/cli.py:check` existing call at line 223.
**Apply to:** Dir-walk `check` (Pitfall 7 sentinel).
**Concrete:** ALWAYS `emit_indexes=False` in the dir-walk loop. Copy-paste from `_compile_source` is the trap — that function uses `emit_indexes=True`. Sentinel test: `assert "sentence_transformers" not in sys.modules` after a `check` invocation.

### Resolve-before-run controller pattern
**Source:** `voss/harness/cli.py:_resolve_auth_or_die` (lines 108-147).
**Apply to:** `_resolve_run_turn` (new, D-08).
**Concrete:** Function pre-computes the runtime callable + raises on misconfiguration. No silent defaults; loud `click.ClickException` on invalid backend. Called by `do_cmd` / `chat_cmd` before `asyncio.run(...)`.

### NAME-imports-only in `.voss` (Pitfall 1 mitigation)
**Source:** `voss/codegen.py:142-148` (`from foo.bar import baz` codegen) + Wave 0 Pattern 1b (auto-await).
**Apply to:** All five `.voss` files in `voss/harness/agent/`.
**Concrete:** Always `use voss::harness::run_turn` (NOT `use voss::harness as h` + `h.run_turn(...)`). The aliased-module form is a future hardening; M4 stays on the NAME form.

### `.voss` thin (D-02)
**Source:** CONTEXT D-02 + M4-RESEARCH §"Pattern 2 caveats".
**Apply to:** All five `.voss` files.
**Concrete:** No pydantic models, no prompt strings, no tool registration in `.voss`. Only `ctx`, `probable<T>`, gates, `try/catch`, `fallback`, `use ... as`, and calls into Python helpers. The reviewer checks the `.voss` files manually (M4-VALIDATION Manual-Only row).

### Header comment convention (M3 D-14 carry-forward)
**Source:** `samples/research.voss:1-2`, `samples/classify.voss:1-2`, `samples/support.voss:1-2`.
**Apply to:** All five `.voss` files.
**Concrete:** Two `#` lines at file top: filename + one-line primitive summary.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | Every M4 file mirrors an in-tree analog. The closest call is `voss/harness/cache.py` (new module) — its sha+manifest shape mirrors `voss/harness/cognition.py:build_repo_idx`, so this is role-match, not greenfield. |

The only genuinely-new design surface is the Wave 0 compiler sub-plan (grammar `("as" IDENT)?` + codegen `use_imported_names` set). Both extend existing structures (lark optional-group idiom; `generated_fns` condition expansion). Per M4-RESEARCH §"Don't Hand-Roll" key insight: "Every M4 problem has an in-tree analog. The compiler-gap sub-plan (Pattern 1) is the ONLY new design surface. Everything else is mechanical extension."

---

## Metadata

**Analog search scope:** `voss/`, `voss_runtime/`, `tests/`, `samples/`, `.github/workflows/`, `.planning/phases/M1`, `.planning/phases/M2`, `.planning/phases/M3`.
**Files scanned:** 18 source/test files + 4 prior-phase docs.
**Pattern extraction date:** 2026-05-11.
**Cross-references checked:** M1-CONTEXT (D-05 permission gate, D-13 diagnose-don't-fix), M2-CONTEXT (D-06 sandbox cache writes), M3-CONTEXT (D-01 auto-stub, D-03 static-only check, D-12 parity oracle), M3-PATTERNS.md (header comment convention, raw-Python parity oracle pattern), M4-CONTEXT D-01..D-16, M4-RESEARCH Patterns 1-6 + Pitfalls 1-8, M4-VALIDATION per-task rows.

**Open assumptions flagged for planner:**
- A1 (M4-RESEARCH): Codegen auto-await extension (Pattern 1b) stays under ~20 LOC of diff. Verified by reading codegen.py:349, 441-446, 1196-1197 — but planner should budget the sub-plan as 1 plan with 3-5 tasks and monitor scope if test fixtures fan out.
- A2: `.voss` lacks `for` and `**kwargs`; executor.voss forwards to Python helper `_run_step_loop`. Verified against grammar.lark:88-98 stmt rules.
- `voss/__init__.py` exports `__version__`: NEEDS VERIFICATION before `cache.py` lands. Fallback: `importlib.metadata.version("voss")`.
- Named-arg constructor syntax `TurnResult(plan: plan, ...)` in `.voss`: NEEDS VERIFICATION against M3 grammar. If absent, reviewer.voss uses a Python `_make_turn_result(...)` helper.

---

## PATTERN MAPPING COMPLETE

**Phase:** M4 - Voss-authored Harness Loop
**Files classified:** 22
**Analogs found:** 22 / 22

### Coverage
- Files with exact in-file analog: 13 (modifications)
- Files with role-match analog: 9 (new files mirroring an existing module's shape)
- Files with no analog: 0

### Key Patterns Identified
- **Sub-plan-then-extend ordering:** Wave 0 (grammar + codegen) MUST land before Wave 2 (.voss authoring). Without Pattern 1b auto-await, executor.voss compiles but returns coroutine objects (Pitfall 2).
- **NAME imports only:** `use voss::harness::run_turn` works today + Pattern 1b. Aliased module imports (`use voss::harness as h`) are cosmetic and deferred from M4 even though the grammar extension lands.
- **Python helpers for control flow .voss can't express:** `_run_step_loop` (no `for` in .voss), `ToolEntry.invoke_dict` (no `**kwargs` spread). Documented in Q-2/Q-3 + Pattern 2 caveats.
- **`.voss-cache/harness/` cache key = sha256(source) + voss_version:** Not git-head, not mtime. Manifest is the single source of truth for freshness.
- **Loud failure on stale cache:** D-10 mandates exact message; no silent fallback. Mirror of M1 D-13 diagnose-don't-fix.
- **FakeProvider not StubProvider for parity:** Pattern 6 + Pitfall 6 — parity test asserts on TurnResult fields, not prompt fingerprints.
- **emit_indexes=False sentinel:** M3 D-03 carry-forward; Pitfall 7 sentinel test in `test_voss_check_dir.py`.
- **`_run_step_loop` extraction:** Pitfall 8 mitigation — Python `run_turn` and compiled `loop.voss` call the SAME helper, ensuring shared `EpisodicMemory`/`ContextScope`/`PermissionGate`.

### File Created
`/Users/benjaminmarks/Projects/Voss/.planning/phases/M4-voss-authored-harness-loop/M4-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference per-file analogs (with file:line citations) when writing each PLAN.md's action sections. Wave 0 compiler sub-plan is the explicit gate; Waves 1-4 are mechanical extensions with exact in-file analogs.
