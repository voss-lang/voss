# Phase V21: Global Cross-Project Memory - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 6 new/modified files
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/memory_store.py` | service | CRUD | self (additive param) | exact |
| `voss/harness/memory_cli.py` | utility/CLI | request-response | self (additive commands) | exact |
| `voss/harness/config.py` | config | request-response | self (`_parse_model_tiers_section` / `get_allow_net`) | exact |
| `voss/harness/tools.py` | service | request-response | self (`attach_memory_tools` existing) | exact |
| `voss/harness/cli.py` | controller | request-response | `voss/harness/cli.py` AGENT_COMMANDS + `do_cmd`/`chat_cmd` MemoryStore sites | exact |
| `tests/harness/test_memory_global.py` + conftest | test | CRUD | `tests/harness/test_memory_vacuum.py`, `test_memory_store.py`, `conftest.py` | exact |

---

## Pattern Assignments

### `voss/harness/memory_store.py` — `root_override` param + `_global_memory_root()` helper

**Analog:** `voss/harness/memory_store.py` (self — additive change)

**Current `__init__` signature** (lines 72–79):
```python
class MemoryStore:
    def __init__(self, cwd: Path, *, cap_bytes: int = DEFAULT_CAP_BYTES) -> None:
        self.cwd = cwd
        self.cap_bytes = cap_bytes
        self.root = cwd / ".voss" / "memory"
        self._chroma: Optional[SemanticMemory] = None
        self._chroma_unavailable = False
        self._size_cache: dict[str, int] = {}
        self._session_id: Optional[str] = None
```

**V21 change — add `root_override`** (replace line 72, touch nothing else):
```python
def __init__(
    self,
    cwd: Path,
    *,
    cap_bytes: int = DEFAULT_CAP_BYTES,
    root_override: Path | None = None,          # V21: global store path
) -> None:
    self.cwd = cwd
    self.cap_bytes = cap_bytes
    self.root = root_override if root_override is not None else cwd / ".voss" / "memory"
    # ... rest unchanged
```

**`_lock()` pattern to copy for promote** (lines 128–144) — note LOCK_NB causes silent-skip; promote must use blocking variant:
```python
@contextmanager
def _lock(self, source: str):
    """Per-source advisory lock via portalocker; yields None on contention."""
    self.root.mkdir(parents=True, exist_ok=True)
    (self.root / ".locks").mkdir(parents=True, exist_ok=True)
    lock_path = self.root / ".locks" / f"{source}.lock"
    try:
        with portalocker.Lock(
            str(lock_path),
            mode="a",
            flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
            timeout=0,
        ) as fh:
            yield fh
    except portalocker.exceptions.LockException:
        print(f"memory.{source} busy — skipping write", file=sys.stderr)
        yield None
```
PITFALL: for `promote`, use `LOCK_EX` without `LOCK_NB` (blocking, `timeout=5`) so a concurrent promote waits rather than silently drops the write.

**`write_note` file + chroma pattern to mirror for promote copy** (lines 322–357):
```python
def write_note(self, text: str, *, session_id: str) -> Path:
    from .cognition import reserve_filename, slug
    notes_dir = self.root / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = reserve_filename(notes_dir, slug(text[:40]))
    composite_id = make_id("note", path.stem)
    body = (
        "---\n"
        f"id: {path.stem}\n"
        f"related_session: {session_id}\n"
        f"created_at: {ts}\n"
        "---\n\n"
        f"{text}\n"
    )
    with self._lock("notes") as lock:
        if lock is None:
            return path
        self._maybe_evict("notes", est_bytes=len(body.encode()))
        path.write_text(body)
        path.chmod(0o600)          # <-- security: 0o600 on every written file
    chroma = self._maybe_chroma()
    if chroma is not None:
        chroma.add(
            text=text,
            metadata={
                "source_type": "note",
                "session_id": session_id,
                "path": str(path),
                "ts": ts,
                "tombstoned": False,
            },
            id=composite_id,
        )
    return path
```
Promote adds `"promoted_from": f"{repo_id}/{locator}"` to the metadata dict — that is the only difference from a normal write.

**`_locator_from_path` — decision locator uses `relative_to(self.root.parent)`** (lines 623–636):
```python
def _locator_from_path(self, source_dir: str, path: Path) -> str:
    stem = path.stem
    if source_dir == "turns":
        return make_id("turn", stem, seq=0)
    if source_dir == "ledgers":
        return make_id("ledger", stem, seq=0)
    if source_dir == "decisions":
        return make_id("decision", str(path.relative_to(self.root.parent)))
    if source_dir == "conventions":
        return make_id("convention", stem)
    if source_dir == "notes":
        return make_id("note", stem)
    return f"{source_dir}:{stem}"
```
PITFALL: for the global store, `self.root.parent = ~/.voss`, so a decision at `~/.voss/memory/decisions/foo.md` produces locator `decision:memory/decisions/foo.md`. This is different from project locators. Accept it — locators are internal IDs, and the original project locator is in `promoted_from` metadata.

**`_rrf_merge` static method** (lines 425–440):
```python
@staticmethod
def _rrf_merge(rankings: list[list[Hit]], *, top_k: int, k: int = 60) -> list[Hit]:
    scores: dict[str, float] = {}
    carriers: dict[str, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            carriers.setdefault(hit.locator, hit)
            scores[hit.locator] = scores.get(hit.locator, 0.0) + (1.0 / (k + rank))
    fused: list[Hit] = []
    for locator, score in scores.items():
        carrier = carriers[locator]
        fused.append(dataclasses.replace(carrier, score=score))
    fused.sort(key=lambda hit: (-hit.score, hit.locator))
    return fused[:top_k]
```
PITFALL: dedup is by `hit.locator`. Global hits MUST be namespaced (`global:note:foo`) before calling `_rrf_merge`, or a project note and a promoted global note with the same stem silently collapse to one hit.

**New `_global_memory_root()` module-level helper — add near top of `memory_store.py`:**
```python
import os  # already imported

def _global_memory_root() -> Path | None:
    """Resolve global memory root; returns None if HOME unavailable."""
    voss_home_env = os.environ.get("VOSS_HOME")
    if voss_home_env:
        return Path(voss_home_env).resolve() / "memory"
    try:
        return Path.home() / ".voss" / "memory"
    except RuntimeError:
        return None   # CI / container with no $HOME — treat as globally disabled
```

**New `make_global_store()` factory — add near `_global_memory_root()`:**
```python
def make_global_store() -> "MemoryStore | None":
    """Create a global MemoryStore; returns None when disabled or HOME absent."""
    from voss.harness.config import get_global_memory_enabled
    if not get_global_memory_enabled():
        return None
    root = _global_memory_root()
    if root is None:
        return None
    try:
        home = Path.home()
    except RuntimeError:
        return None
    return MemoryStore(home, root_override=root)
```

**New `_repo_id()` helper — add near `make_id()`:**
```python
import hashlib   # already imported in tools.py; add to memory_store.py imports

def _repo_id(cwd: Path) -> str:
    """Stable, human-readable repo identifier for provenance metadata (D-10)."""
    h = hashlib.sha256(str(cwd.resolve()).encode()).hexdigest()[:8]
    return f"{cwd.resolve().name}-{h}"
```

---

### `voss/harness/memory_cli.py` — `promote`, `forget --global`, `vacuum --global`

**Analog:** `voss/harness/memory_cli.py` (self — additive commands)

**Existing command registration pattern** (lines 1–19):
```python
from __future__ import annotations
import hashlib
import sys
from pathlib import Path
import click
from . import voss_md
from .memory_store import MemoryStore

@click.group("memory")
def memory_group() -> None:
    """Manage Voss project memory store."""
```

**Existing `vacuum` command — copy shape for new commands** (lines 23–40):
```python
@memory_group.command("vacuum")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
def memory_vacuum_cmd(cwd_str: str) -> None:
    """Compact chroma + delete tombstoned entries; report bytes reclaimed."""
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)
    if not store.root.exists():
        click.echo(f"no memory store at {store.root}", err=True)
        sys.exit(1)
    store.bind(session_id="vacuum")
    reclaimed = store.vacuum()
    click.echo(f"reclaimed: {reclaimed} bytes")
```

**Existing `size` command — copy iteration pattern for `promote --list`** (lines 82–109):
```python
@memory_group.command("size")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
def memory_size_cmd(cwd_str: str) -> None:
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)
    root = store.root
    if not root.exists():
        click.echo("no memory store", err=True); sys.exit(1)
    total = 0
    for source in ("turns", "ledgers", "decisions", "conventions", "notes"):
        src_dir = root / source
        size = (
            sum(p.stat().st_size for p in src_dir.rglob("*") if p.is_file())
            if src_dir.exists() else 0
        )
        total += size
        click.echo(f"  {source}: {size:>10} bytes")
```
For `promote --list`, iterate `("notes", "decisions", "conventions")` only (D-02: turns/ledgers excluded), print `<locator>: <first-line-of-excerpt>`.

**New `vacuum --global` flag — extend existing `vacuum` command:**
```python
@memory_group.command("vacuum")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--global", "use_global", is_flag=True, help="Compact global store (~/.voss/memory/).")
def memory_vacuum_cmd(cwd_str: str, use_global: bool) -> None:
    if use_global:
        from .memory_store import make_global_store
        store = make_global_store()
        if store is None:
            click.echo("global store disabled or unavailable", err=True); sys.exit(1)
    else:
        cwd = Path(cwd_str).resolve()
        store = MemoryStore(cwd)
        if not store.root.exists():
            click.echo(f"no memory store at {store.root}", err=True); sys.exit(1)
    store.bind(session_id="vacuum")
    reclaimed = store.vacuum()
    click.echo(f"reclaimed: {reclaimed} bytes")
```

**New `promote` command skeleton:**
```python
@memory_group.command("promote")
@click.argument("locator")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--list", "list_only", is_flag=True, help="List promotable entries instead of promoting.")
def memory_promote_cmd(locator: str, cwd_str: str, list_only: bool) -> None:
    """Copy a project memory entry into the global store with provenance tag."""
    cwd = Path(cwd_str).resolve()
    if list_only:
        store = MemoryStore(cwd)
        for source in ("notes", "decisions", "conventions"):
            src_dir = store.root / source
            if not src_dir.exists(): continue
            for p in sorted(src_dir.rglob("*.md")):
                from .memory_store import _locator_from_path  # or inline
                loc = store._locator_from_path(source, p)
                try:
                    first = p.read_text(errors="ignore").splitlines()
                    excerpt = next((l for l in first if l and not l.startswith("---")), "")[:80]
                except OSError:
                    excerpt = ""
                click.echo(f"{loc}: {excerpt}")
        return
    source_prefix = locator.split(":")[0]
    if source_prefix in ("turn", "ledger"):
        click.echo(f"error: turns and ledgers cannot be promoted (got: {source_prefix})", err=True)
        sys.exit(1)
    # ... resolve file in project store, copy to global, chroma.add with promoted_from
```

**New `forget --global` command:**
```python
@memory_group.command("forget")
@click.argument("locator")
@click.option("--global", "use_global", is_flag=True, help="Tombstone from global store.")
@click.option("--yes", "confirm", is_flag=True, help="Skip confirmation prompt.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
def memory_forget_cmd(locator: str, use_global: bool, confirm: bool, cwd_str: str) -> None:
    """Tombstone memory entries. --global targets the global store."""
    if use_global:
        from .memory_store import make_global_store
        store = make_global_store()
        if store is None:
            click.echo("global store disabled or unavailable", err=True); sys.exit(1)
        store.root.mkdir(parents=True, exist_ok=True)  # ensure layout before forget
    else:
        cwd = Path(cwd_str).resolve()
        store = MemoryStore(cwd)
    n = store.forget(locator, confirm=confirm)
    click.echo(f"tombstoned: {n} entries")
```

---

### `voss/harness/config.py` — `_parse_memory_section` + `get_global_memory_enabled`

**Analog:** `voss/harness/config.py` — `_parse_model_tiers_section` (lines 233–239) and `get_allow_net` (lines 344–366)

**Exact pattern to copy from `_parse_model_tiers_section`** (lines 233–239):
```python
_MODEL_TIERS_BLOCK = re.compile(r"^\[model_tiers\][^\[]*", re.MULTILINE)

def _parse_model_tiers_section(text: str) -> dict[str, str]:
    """Parse `[model_tiers]` quoted-string entries → ``{tier: model_id}``."""
    m = _MODEL_TIERS_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}
```

**New `_parse_memory_section` — copy `_parse_tools_section` shape** (lines 77–91) because `global = false` is a bare boolean like `allow_net = true`:
```python
_MEMORY_BLOCK = re.compile(r"^\[memory\][^\[]*", re.MULTILINE)

def _parse_memory_section(text: str) -> dict[str, str]:
    """Parse `[memory]` section: bare booleans like `global = false`."""
    m = _MEMORY_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    out: dict[str, str] = {}
    for k, v in _KV.findall(block):
        out[k] = v
    for k, v in _KV_BARE.findall(block):
        out.setdefault(k, v)   # don't overwrite quoted match with bare token
    return out
```

**New `get_global_memory_enabled` — copy `get_allow_net` shape** (lines 344–366):
```python
def get_global_memory_enabled() -> bool:
    """Returns True unless [memory] global = false in config.toml."""
    p = config_path()
    if not p.exists():
        return True
    try:
        text = p.read_text()
    except OSError:
        return True
    section = _parse_memory_section(text)
    raw = section.get("global")
    if raw is None:
        return True
    normalized = raw.strip().lower()
    if normalized == "false":
        return False
    if normalized == "true":
        return True
    import warnings
    warnings.warn(
        f"[memory] global = {raw!r} is not a boolean; defaulting to enabled",
        RuntimeWarning,
        stacklevel=2,
    )
    return True
```

**NOTE:** `config_path()` resolves to `~/.config/voss/config.toml` (line 20–21). The `[memory] global = false` switch lives there — NOT in `.voss/config.yml` (the project-local YAML for memory quotas). Do not mix them.

```python
def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "config.toml"
```

---

### `voss/harness/tools.py` — `attach_memory_tools` dual-store fusion

**Analog:** `voss/harness/tools.py` lines 159–215 (self — additive `global_store` parameter)

**Current signature and body** (lines 159–215):
```python
def attach_memory_tools(tools: dict[str, "ToolEntry"], *, store, session_id: str) -> None:
    @tool(name="memory_recall", description="...")
    async def memory_recall(query: str, top_k: int = 5, source: str | None = None) -> str:
        query = query.strip()
        if not query:
            return "<error: empty query>"
        try:
            hits = store.recall(query, top_k=top_k, source=source)
        except Exception as exc:
            return f"<error: recall failed: {exc}>"
        if not hits:
            return "(no hits)"
        lines: list[str] = []
        for h in hits:
            lines.append(f"[{h.source}] {h.locator} (score {h.score:.2f})")
            excerpt = (h.excerpt or "").replace("\n", " ")[:160]
            if excerpt:
                lines.append(f"  {excerpt}")
        return "\n".join(lines)

    @tool(name="memory_remember", description="...")
    async def memory_remember(text: str) -> str:
        ...
        path = store.write_note(text, session_id=session_id)
        return f"remembered: {path.name}"

    tools["memory_recall"] = ToolEntry(descriptor=memory_recall, is_mutating=False, group="memory", scope_requirements=("memory",))
    tools["memory_remember"] = ToolEntry(descriptor=memory_remember, is_mutating=True, group="memory", scope_requirements=("memory",))
```

**V21 change — add `global_store=None` and fuse in `memory_recall`:**
```python
def attach_memory_tools(
    tools: dict[str, "ToolEntry"],
    *,
    store,
    session_id: str,
    global_store=None,           # V21: MemoryStore | None; None when disabled
) -> None:
    @tool(name="memory_recall", description="...")
    async def memory_recall(query: str, top_k: int = 5, source: str | None = None) -> str:
        query = query.strip()
        if not query:
            return "<error: empty query>"
        try:
            proj_hits = store.recall(query, top_k=top_k * 3, source=source)
        except Exception as exc:
            return f"<error: recall failed: {exc}>"
        if global_store is not None:
            try:
                g_hits_raw = global_store.recall(query, top_k=top_k * 3, source=source)
                # Namespace global locators to prevent _rrf_merge dedup collision
                g_hits = [
                    dataclasses.replace(h, source="[global]", locator=f"global:{h.locator}")
                    for h in g_hits_raw
                ]
                from .memory_store import MemoryStore as _MS
                hits = _MS._rrf_merge([proj_hits, g_hits], top_k=top_k)
            except Exception as exc:
                hits = proj_hits[:top_k]
                print(f"memory: global recall failed ({exc}); using project-only", file=sys.stderr)
        else:
            hits = proj_hits[:top_k]
        # ... format hits as before (no change to output format logic)
```

**D-08 guard:** `global_store` is NEVER passed to `memory_remember` / `write_note`. The global store reference is read-only in `attach_memory_tools`. All write paths remain project-only.

**`dataclasses` import** is already at line 4 of `memory_store.py`; `tools.py` must add `import dataclasses` at the top if not already present.

---

### `voss/harness/cli.py` — `recall_cmd` extension + global store init in `do_cmd`/`chat_cmd`

**Analog:** `voss/harness/cli.py` — existing `AGENT_COMMANDS` tuple (lines 4642–4678) and `MemoryStore(cwd).bind(...)` sites (lines 1861–1862, 2157, 3386–3388)

**`AGENT_COMMANDS` tuple — append `recall_cmd` here** (line 4664 vicinity):
```python
AGENT_COMMANDS = (
    do_cmd,
    serve_cmd,
    chat_cmd,
    ...
    memory_group,
    recall_cmd,          # V21 addition (V19-04 planned this; V21 extends it)
    config_cmd,
    ...
)
```

**Existing `attach_memory_tools` call pattern in `do_cmd`** (lines 1861–1862):
```python
do_memory_store = MemoryStore(cwd).bind(session_id=do_record.id)
attach_memory_tools(tools, store=do_memory_store, session_id=do_record.id)
```

**V21 change — pass `global_store` to `attach_memory_tools`:**
```python
from .memory_store import make_global_store     # import at top of file
...
do_memory_store = MemoryStore(cwd).bind(session_id=do_record.id)
_global_store = make_global_store()
if _global_store is not None:
    _global_store.bind(session_id="global")    # creates layout dirs
attach_memory_tools(
    tools,
    store=do_memory_store,
    session_id=do_record.id,
    global_store=_global_store,                # None when disabled
)
```
Apply the same three-line change at all three `attach_memory_tools` call sites (lines 1862, 2171, 3386–3388).

**`recall_cmd` registration (V19-04 owns the implementation; V21 extends with global corpus):**
V19-04 PLAN defines `recall_cmd` as `voss recall <query> [--json] [--top N] [--cwd PATH]` fusing code + memory hits via `_rrf_merge`. V21 adds a third ranking:
```python
# Inside recall_cmd body (V19's code; V21 adds these lines):
mem_hits = store.recall(query_str, top_k=top_k * 3)
g_hits_raw = (global_store.recall(query_str, top_k=top_k * 3) if global_store else [])
g_hits = [
    dataclasses.replace(h, source="[global]", locator=f"global:{h.locator}")
    for h in g_hits_raw
]
all_mem = MemoryStore._rrf_merge([mem_hits, g_hits], top_k=top_k * 3) if g_hits else mem_hits
# Then fuse all_mem with code_hits as V19 does:
fused = MemoryStore._rrf_merge([code_hits, all_mem], top_k=top_k)
```
Source label for display: `"[global]"` if `hit.source == "[global]"`, `"[code]"` if `hit.source.startswith("code")`, else `"[memory]"`.

---

### `tests/harness/test_memory_global.py` + `conftest.py` amendment

**Analog:** `tests/harness/test_memory_vacuum.py`, `test_memory_store.py`, `conftest.py`

**Test file header pattern** (copy from `test_memory_vacuum.py` lines 1–12):
```python
"""V21 global memory tests (VGMEM-* requirements)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from voss.harness.memory_store import MemoryStore, make_global_store, _global_memory_root
```

**Standard test body pattern** (copy from `test_memory_vacuum.py` lines 21–36):
```python
def test_root_override(tmp_path: Path) -> None:
    override = tmp_path / "custom" / "memory"
    store = MemoryStore(tmp_path, root_override=override)
    assert store.root == override
    assert store.cwd == tmp_path     # cwd unchanged

def test_voss_home_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOSS_HOME", str(tmp_path / "voss_home"))
    root = _global_memory_root()
    assert root == tmp_path / "voss_home" / "memory"
```

**`conftest.py` fixture to add — `tmp_voss_global`** (mirrors `tmp_voss_repo` lines 92–104):
```python
@pytest.fixture
def tmp_voss_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tmp global memory root with VOSS_HOME monkeypatched.

    Sets VOSS_HOME so _global_memory_root() resolves to a controlled tmp dir.
    Creates the same layout as tmp_voss_repo but under tmp_path/global_home.
    """
    global_home = tmp_path / "global_home" / "voss"
    monkeypatch.setenv("VOSS_HOME", str(global_home))
    mem = global_home / "memory"
    for sub in ("turns", "ledgers", "decisions", "conventions", "notes", "chroma", ".locks"):
        (mem / sub).mkdir(parents=True, exist_ok=True)
    return mem
```

**CLI subprocess test pattern** (copy from `test_memory_store.py` lines 58–70 for `chroma_disabled_env` usage):
```python
def test_promote_rejects_turn_ledger(tmp_voss_repo: Path, tmp_voss_global: Path) -> None:
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "memory", "promote", "turn:s1:000"],
        cwd=str(tmp_voss_repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "cannot be promoted" in result.stderr
```

**`isolated_state` fixture** is autouse (conftest.py lines 28–31) — every test gets XDG sandbox automatically. No need to request it explicitly.

---

## Shared Patterns

### File write + chmod 0o600
**Source:** `voss/harness/memory_store.py` lines 343, 384 (`write_note`, `write_convention`)
**Apply to:** Every file written by `promote` in the global store
```python
path.write_text(body)
path.chmod(0o600)
```

### portalocker per-source lock
**Source:** `voss/harness/memory_store.py` lines 128–144 (`_lock` context manager)
**Apply to:** `promote` command (use blocking `LOCK_EX` without `LOCK_NB`), `forget --global`, `vacuum --global`
```python
# For promote: blocking lock so concurrent promotes wait, not silently drop
with portalocker.Lock(str(lock_path), mode="a", flags=portalocker.LOCK_EX, timeout=5) as fh:
    ...
# For vacuum/forget: LOCK_NB (existing pattern) is acceptable — user can retry
```

### `_KV` + `_KV_BARE` regex parsers
**Source:** `voss/harness/config.py` lines 44–50
**Apply to:** `_parse_memory_section` in `config.py`
```python
_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
_KV_BARE = re.compile(r"^\s*(\w+)\s*=\s*([^\s\"#]+)\s*$", re.MULTILINE)
```
These are module-level in `config.py` and shared across all section parsers.

### `make_id` composite ID format
**Source:** `voss/harness/memory_store.py` lines 56–60
**Apply to:** All chroma `id=` arguments in promote's global store write
```python
def make_id(source: str, locator: str, seq: int | None = None) -> str:
    if seq is None:
        return f"{source}:{locator}"
    return f"{source}:{locator}:{seq:03d}"
```

### Error handling in CLI commands
**Source:** `voss/harness/memory_cli.py` lines 35–38 (root existence check + `sys.exit(1)`)
**Apply to:** All new CLI commands
```python
if not store.root.exists():
    click.echo(f"no memory store at {store.root}", err=True)
    sys.exit(1)
```

### Defensive global recall fallback in `attach_memory_tools`
**Source:** `voss/harness/tools.py` lines 183–186 (existing recall exception handler)
**Apply to:** Global recall branch in the extended `memory_recall` tool
```python
except Exception as exc:  # noqa: BLE001 — recall must not crash the turn
    return f"<error: recall failed: {exc}>"
```
For the global branch specifically: catch and log, fall back to project-only hits (never crash the tool on global store failure).

---

## No Analog Found

All V21 files have close analogs in the codebase. No files require research-only patterns.

| File | Role | Data Flow | Note |
|------|------|-----------|------|
| — | — | — | All files have exact or near-exact analogs |

---

## Key Pitfalls (extracted from RESEARCH.md for planner)

1. **Locator namespace collision:** global locators must be prefixed `global:` before `_rrf_merge`; the static method deduplicates by `hit.locator`, which causes silent hit loss without namespacing.
2. **promote uses blocking lock:** `_lock()` uses `LOCK_NB` (non-blocking, silent-skip); promote must use `LOCK_EX` without `LOCK_NB` so concurrent promotes wait up to 5s rather than silently dropping the write.
3. **`_locator_from_path` for decisions:** global store decisions produce `decision:memory/decisions/foo.md` (relative to `~/.voss`), not `decision:decisions/foo.md`. Accept this; the original locator is in `promoted_from` metadata.
4. **`Path.home()` in CI:** wrap every call to `Path.home()` in `try/except RuntimeError`; treat as "global disabled" and log a warning.
5. **config file confusion:** `[memory] global = false` → `~/.config/voss/config.toml` (TOML, `config_path()`). Memory quota overrides → `.voss/config.yml` (YAML, `_load_memory_config()`). Never mix.
6. **`bind()` session_id for global store:** use a synthetic session_id like `"global"` or `"promote"`; turn/ledger write paths are structurally unreachable on the global instance, but `bind()` requires a non-None session_id.

---

## Metadata

**Analog search scope:** `voss/harness/`, `tests/harness/`, `tests/memory/`
**Files scanned:** 8 source files + 3 test files read in full; V19-04-PLAN.md grep for recall_cmd interface
**Pattern extraction date:** 2026-06-11
