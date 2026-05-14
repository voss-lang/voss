# Phase M8: Project Memory (MEM-01) — Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 9 (4 new + 5 modified)
**Analogs found:** 9 / 9 (all matched)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/voss_md.py` (NEW) | utility / parser | file-I/O + transform | `voss/harness/cognition.py` (FRONTMATTER_RE + `_load_arch`) | exact (file-format owner) |
| `voss/harness/memory_store.py` (NEW) | service | CRUD + transform | `voss_runtime/memory/semantic.py` (chroma client) + `voss/harness/recorder.py` (FS mirror) | role-match (composes runtime types) |
| `voss/harness/conventions.py` (NEW) | service | request-response (LLM) + file-I/O | `voss/harness/skills/analyze.py` (asyncio LLM call) + `voss/harness/recorder.py::write_decisions_md` (per-entry FS mirror) | role-match |
| `voss/harness/memory_cli.py` (NEW) | controller / CLI group | request-response | `voss/harness/cli.py::plugin_group` / `skill_group` / `agent_group` | exact (click.Group pattern) |
| `voss/harness/cli.py` (MOD) | controller | request-response | self — slash registration block at lines 464–483 | exact (self-modify) |
| `voss/harness/agent.py` (MOD) | service | request-response | self — `_compose_cognition_prompt` + `sys_prompt` assembly | exact (self-modify) |
| `voss/harness/cognition.py` (MOD) | service / loader | file-I/O | self — `_load_arch` at line 101 | exact (rewire read path) |
| `voss/harness/skills/analyze.py` (MOD) | skill | request-response + file-I/O | self — `arch_path` + `arch_backup` logic | exact (rewire write target) |
| `voss/harness/recorder.py` (UNCHANGED but reused) | service | file-I/O | self — `write_decisions_md` at line 135 is the pattern source for conventions/notes mirroring | source-of-pattern |

---

## Pattern Assignments

### `voss/harness/voss_md.py` (NEW — utility / file-format owner)

**Analog:** `voss/harness/cognition.py` (FRONTMATTER regex parse + preserve-if-exists writes)

**Imports pattern** (copy from `cognition.py` lines 8–22):
```python
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
```

**Regex constants** (analog: `cognition.py:38`):
```python
# cognition.py:38 — frontmatter regex pattern: compile once at module level
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

# COPY THIS STYLE for fence markers:
FENCE_BEGIN = re.compile(r"<!-- voss:begin id=([\w-]+) -->")
FENCE_HASH  = re.compile(r"<!-- voss:hash ([0-9a-f]{64}) -->")
FENCE_END   = re.compile(r"<!-- voss:end id=([\w-]+) -->")
```

**Frozen dataclass for parsed structure** (analog: `cognition.py:41–46`):
```python
# cognition.py:41-46 — frozen dataclass for parsed file
@dataclass(frozen=True)
class ArchitectureFrontmatter:
    git_head: str
    analyzed_at: str
    file_count: int
    analyzer_version: int
```
Mirror this with a `Block(kind, id, body, recorded_hash)` dataclass.

**Never-raises loader pattern** (analog: `cognition.py:101–134` `_load_arch`):
```python
# cognition.py:101-114 — file-format loader that NEVER raises; appends to errors list
def _load_arch(path: Path, errors: list[str]):
    """Return (body_str, ArchitectureFrontmatter | None). Never raises."""
    if not path.exists():
        return None, None
    try:
        text = path.read_text()
    except OSError as e:
        errors.append(f"{path}: read error: {e}")
        return None, None

    m = FRONTMATTER_RE.match(text)
    if not m:
        return text, None
    fm_text, body = m.group(1), m.group(2)
    ...
```
**Apply to:** `voss_md.read_and_inject(cwd) -> str | None` (Req 1 — absence degrades silently to `None`). Use try/except + early-return-on-missing; never raise out of the loader.

**Preserve-if-exists write pattern** (analog: `cognition.py:597–604`):
```python
# cognition.py:597-604 — preserve-if-exists scaffold under .voss/
def write_voss_gitignore(cwd: Path) -> bool:
    target = voss_dir(cwd) / ".gitignore"
    voss_dir(cwd).mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    target.write_text("# voss session state and rebuildable cache\nsessions/\n")
    return True
```
**Apply to:** `voss_md.ensure_migrated(cwd)` — preserve-if-`VOSS.md`-exists, archive-byte-identical the old `.voss/architecture.md`, write fenced VOSS.md.

**Archive byte-identity pattern** (synthesized — Req 2(a) acceptance demands `sha256(archive) == sha256(pre-migration)`):
```python
# Use stdlib only — no special analog. Read bytes, write bytes, sha256 both, assert equal.
import shutil
src_bytes = arch_path.read_bytes()
archive_path.write_bytes(src_bytes)
assert hashlib.sha256(archive_path.read_bytes()).hexdigest() \
    == hashlib.sha256(src_bytes).hexdigest()
```

---

### `voss/harness/memory_store.py` (NEW — orchestrator / CRUD service)

**Analog (primary):** `voss_runtime/memory/semantic.py` (SemanticMemory lifecycle)
**Analog (secondary):** `voss/harness/recorder.py::write_decisions_md` (per-source FS mirror)

**Imports pattern** (copy from `recorder.py` lines 8–17):
```python
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
```

**Soft-dependency catch with friendly fallback** (analog: `voss_runtime/memory/semantic.py:21–31` — REUSE VERBATIM; do not reinvent):
```python
# semantic.py:21-31 — try/except ImportError, raise ModuleNotFoundError with hint
def __post_init__(self):
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as e:
        raise ModuleNotFoundError(
            "chromadb is not installed. Semantic memory is an optional "
            "Voss feature. Install it with:\n"
            "    pip install 'voss[search]'\n"
            "(or, with the npm wrapper, `voss extras install search`)."
        ) from e
```
**Apply to:** `memory_store.MemoryStore.bind()` — catch `ModuleNotFoundError` from `SemanticMemory.__post_init__` at the **call site**, set `self._chroma = None`, route subsequent `recall()` to `_keyword_scan()`. Do NOT reinvent the friendly-error message — bubble it up from runtime.

**Lazy init (Pitfall 4)** — DO NOT eagerly instantiate `SemanticMemory` in `bind()`. Defer until first `add()`/`recall()` call (cold-start latency concern). Pattern: store `self._cwd` only; build chroma on first access via `@property` or `_ensure_chroma()` helper.

**Composition (NOT subclassing) of runtime types** (Req 7 — grep gate forbids `class .*Memory` in `voss/harness/`):
```python
# WRONG: class MemoryStore(SemanticMemory): ...  ← grep gate fails
# RIGHT: instantiate + compose
from voss_runtime.memory import SemanticMemory, EpisodicMemory

class MemoryStore:
    def __init__(self, cwd: Path, *, cap_bytes: int = 100 * 1024 * 1024):
        self.root = cwd / ".voss" / "memory"
        self.cap_bytes = cap_bytes
        self._chroma: SemanticMemory | None = None
        self._size_cache: dict[str, int] = {}
```

**Per-source-dir FS mirror pattern** (analog: `recorder.py:135–167` `write_decisions_md` — COPY THE SLUG+FRONTMATTER+RESERVE_FILENAME idiom):
```python
# recorder.py:135-167 — pattern for per-entry markdown mirror under .voss/<source>/
def write_decisions_md(cwd: Path, run, session_id: str) -> list[Path]:
    from .cognition import reserve_filename, slug

    if not run.decisions:
        return []
    decisions_dir = cwd / ".voss" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for d in run.decisions:
        title = d.get("title") or "untitled"
        body = d.get("body", "")
        path = reserve_filename(decisions_dir, slug(title))
        id_str = path.stem
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        content = (
            "---\n"
            f"id: {id_str}\n"
            "status: active\n"
            f"related_session: {session_id}\n"
            f"created_at: {created_at}\n"
            "---\n\n"
            f"# {title}\n\n{body}\n"
        )
        path.write_text(content)
        paths.append(path)
    return paths
```
**Apply to:** `MemoryStore.write_note(cwd, text, session_id)` (for `/save` notes) and convention writer in `conventions.py`. Reuse `cognition.slug()` + `cognition.reserve_filename()` (cognition.py:354, 359) — do NOT reinvent slug logic.

**JSONL append pattern** (synthesized — no direct analog; closest is `session.py:143` `path.write_text(json.dumps(...))`):
```python
# For turns/<session>.jsonl and ledgers/<run_id>.jsonl — append, one JSON object per line
with path.open("a") as f:
    f.write(json.dumps({"ts": ts, "role": role, "content": content, "turn_idx": idx}) + "\n")
path.chmod(0o600)  # session.py:144 pattern — sensitive content
```

**Filesystem permissions on sensitive writes** (analog: `session.py:144`):
```python
# session.py:143-144 — chmod 0o600 on session JSON (contains user prompts)
path.write_text(json.dumps(asdict(record), indent=2))
path.chmod(0o600)
```
**Apply to:** `turns/*.jsonl`, `ledgers/*.jsonl`, `notes/*.md` — all may contain user content per SPEC §V8.

**Composite ID format** (per D-04, no codebase analog — locked by decision):
```python
# D-04 format: <source>:<locator>:<seq>
# turn:01HX...session...:042
# decision:.voss/decisions/2026-05-14-foo.md
# convention:2026-05-14-naming
# ledger:<run_id>:042
def make_id(source: str, locator: str, seq: int | None = None) -> str:
    return f"{source}:{locator}" + (f":{seq:03d}" if seq is not None else "")
```

**Chroma add/retrieve with metadata** (analog: `semantic.py:73–91`):
```python
# semantic.py:73-86 — pattern for chroma add with metadata
def add(self, text: str, *, metadata: Optional[dict] = None, id: Optional[str] = None) -> None:
    kwargs = {"documents": [text], "ids": [id or str(uuid.uuid4())]}
    if metadata:
        kwargs["metadatas"] = [metadata]
    self._collection.add(**kwargs)
```
**Apply to:** All four source types. Metadata schema: `{source_type, session_id, path, ts, tombstoned}` per D-02.

---

### `voss/harness/conventions.py` (NEW — LLM-driven extraction service)

**Analog (primary):** `voss/harness/skills/analyze.py` (asyncio LLM call pattern + backup-and-restore)
**Analog (secondary):** `voss/harness/recorder.py::write_decisions_md` (per-entry markdown mirror)

**Imports pattern** (synthesized from analyze.py + recorder.py):
```python
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError
```

**Pydantic schema pattern** (analog: `voss/harness/cognition_schemas.py` — `BaseModel` subclasses validated via `model_validate`):
```python
# Pattern in use throughout cognition_schemas — pydantic BaseModel with constrained fields
class ConventionCandidate(BaseModel):
    statement: str = Field(..., min_length=1, max_length=500)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_quote: str = Field(..., min_length=1)
    evidence_turn_idx: int = Field(..., ge=0)
```
**Validation usage pattern** (analog: `cognition.py:146` `model.model_validate(raw)`):
```python
try:
    candidates = [ConventionCandidate.model_validate(c) for c in raw_list]
except ValidationError as e:
    # Skip silently per D-12 — log to session record, do not raise
    return []
```

**LLM call via provider with asyncio.wait_for timeout** (analog: `voss/harness/skills/analyze.py:44–57` — `asyncio.run(run_turn(...))` — note we wrap in `wait_for` per D-12):
```python
# analyze.py:44-57 — asyncio.run drives a single LLM round-trip
asyncio.run(
    run_turn(
        prompt,
        tools=tools,
        cwd=cwd,
        ...
    )
)

# CONVENTIONS pattern (D-12: 8s soft timeout, skip silently on timeout):
try:
    candidates = asyncio.run(
        asyncio.wait_for(_extract(history, provider, model), timeout=8.0)
    )
except asyncio.TimeoutError:
    return []  # D-12: skip review entirely; no error
```

**Pre-filter (D-09)** — signal regex check **before** LLM call:
```python
# D-09 recommended starters — apply against ctx.history.turns user turns
import re
_SIGNAL_RE = re.compile(r"\b(?:no,? use|always|never|prefer|let'?s|don'?t)\b", re.IGNORECASE)

def has_signal(turns: list) -> bool:
    return any(
        _SIGNAL_RE.search(t.content) for t in turns if t.role == "user"
    )
```

**Per-candidate file write** (analog: `recorder.py:135–167`, see code block in memory_store.py section above). Use `cognition.slug()` + `cognition.reserve_filename()`. Frontmatter shape per D-11:
```python
content = (
    "---\n"
    f"id: {id_str}\n"
    "status: active\n"
    f"related_session: {session_id}\n"
    f"evidence_turn_idx: {candidate.evidence_turn_idx}\n"
    f"confidence: {candidate.confidence:.2f}\n"
    f"created_at: {created_at}\n"
    "---\n\n"
    f"# {candidate.statement}\n\n"
    f"## Evidence\n\n> {candidate.evidence_quote}\n"
)
```

**Numbered-list review UX** (D-11) — copy `click.echo` + `input()` idiom from `cli.py:773–778`:
```python
# cli.py:773-778 — input() with EOFError/KeyboardInterrupt protection
while True:
    try:
        line = input("▌ ")
    except (EOFError, KeyboardInterrupt):
        click.echo()
        return
```
**Apply to** `conventions.review()`:
```python
click.echo("Candidate conventions from this session:")
for i, c in enumerate(candidates, start=1):
    click.echo(f"  [{i}] {c.statement}  (conf {c.confidence:.2f})")
    click.echo(f'      evidence: "{c.evidence_quote}" (turn {c.evidence_turn_idx})')
try:
    raw = input("Persist which? (e.g. \"1 3\", or empty for none): ")
except (EOFError, KeyboardInterrupt):
    return []
# Empty input = persist none (D-11)
selected_idxs = [int(x) - 1 for x in raw.split() if x.isdigit()]
```

---

### `voss/harness/memory_cli.py` (NEW — Click subcommand group)

**Analog:** `voss/harness/cli.py::plugin_group` (cli.py:1064–1080) — exact same shape

**Click group skeleton** (copy verbatim, rename):
```python
# cli.py:1064-1080 — plugin_group pattern
@click.group("plugin")
def plugin_group() -> None:
    """Manage plugin manifest enablement."""


@plugin_group.command("enable")
@click.argument("plugin_id")
def plugin_enable_cmd(plugin_id: str) -> None:
    path = set_plugin_enabled(plugin_id, True)
    click.echo(f"plugin {plugin_id} enabled: {path}")
```
**Apply to:**
```python
@click.group("memory")
def memory_group() -> None:
    """Manage Voss project memory store."""

@memory_group.command("vacuum")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def memory_vacuum_cmd(cwd_str: str) -> None:
    """Compact chroma + delete tombstoned entries; report bytes reclaimed."""
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)
    bytes_reclaimed = store.vacuum()
    click.echo(f"reclaimed: {bytes_reclaimed} bytes")
```

**Register with main CLI** (analog: `cli.py:1263–1279` AGENT_COMMANDS tuple + `register()` function):
```python
# cli.py:1263-1285 — tuple of commands + register helper attached to click.Group
AGENT_COMMANDS = (
    do_cmd,
    chat_cmd,
    ...
    plugin_group,
    skill_group,
    agent_group,
    ...
)

def register(group: click.Group) -> None:
    for cmd in AGENT_COMMANDS:
        group.add_command(cmd)
```
**Apply:** Add `memory_group` to the `AGENT_COMMANDS` tuple at cli.py:1263.

**`--cwd` option pattern** (analog: `cli.py:1098, 1134, 845`):
```python
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
```
**Apply to every** `voss memory <sub>` command — matches existing `doctor_cmd`, `do_cmd`, `chat_cmd` convention.

---

### `voss/harness/cli.py` (MODIFIED — slash registration + REPL hooks)

**Analog:** self — slash registration block at cli.py:464–483 and `_run_repl` REPL loop at cli.py:688–834

**Slash command registration block** (cli.py:464–483) — extend the tuple:
```python
# cli.py:464-483 — registry registration is a flat loop over a tuple of SlashCommand
for command in (
    SlashCommand("/help", "show this list", _help),
    ...
    SlashCommand("/save", "persist session snapshot", _save, mutating=True),  # ← COLLISION (Pitfall 1)
    SlashCommand("/analyze", "refresh project cognition (.voss/ + .voss-cache/)", _analyze, mutating=True),
    ...
):
    registry.register(command)
```
**Apply (resolve Pitfall 1):** Rename existing `/save` → `/save-session` (matches `/save-plan` convention at cli.py:475), then add four M8 commands:
```python
SlashCommand("/save-session", "persist session snapshot", _save_session, mutating=True),  # was /save
SlashCommand("/recall", "search memory (top-N hits across sources)", _recall),
SlashCommand("/forget", "delete memory entries matching <pattern>", _forget, mutating=True),
SlashCommand("/memory", "summarize current memory store", _memory),
SlashCommand("/save",   "append a manual note to memory", _save_note, mutating=True),
```

**Slash handler signature** (analog: every existing `_<name>` in cli.py:411–460):
```python
# cli.py:411-417 — slash handler signature: (ctx, args, raw_line) -> None
def _save(ctx: ReplContext, args: list[str], _line: str) -> None:
    if args:
        ctx.record.name = " ".join(args).strip()
    ctx.record.total_cost_usd = ctx.total_cost
    ...
    click.echo(f"saved: {path}")
```
**Apply to:** All 4 new handlers `_recall`, `_forget`, `_memory`, `_save_note`. Use `shlex.split`-pre-split args; output via `click.echo`.

**Argument parsing for slash flags** (analog: `cli.py:398` `if new_mode == "auto" and "--confirm" not in args`):
```python
# cli.py:398 — manual flag check on slash args
if new_mode == "auto" and "--confirm" not in args:
    click.echo("...requires --confirm", err=True)
    return
```
**Apply to** `/forget`:
```python
def _forget(ctx: ReplContext, args: list[str], _line: str) -> None:
    if not args:
        click.echo("usage: /forget <pattern> [--yes]", err=True)
        return
    pattern = args[0]
    confirm = "--yes" in args
    if not sys.stdin.isatty() and not confirm:
        click.echo("/forget requires --yes in non-interactive mode", err=True)
        return
    n = ctx.memory_store.forget(pattern, confirm=confirm)
    click.echo(f"tombstoned: {n} entries")
```

**REPL boot wire points in `_run_repl()`** (analog: cli.py:705 `slash_registry = _build_slash_registry()`, cli.py:717 `bundle = cognition_mod.load(cwd, ...)`):
```python
# cli.py:705, 717 — REPL boot init pattern: build registries + load durable state
slash_registry = _build_slash_registry()
...
bundle = cognition_mod.load(cwd, token_count=_tok_count)
```
**Apply:** Insert three new boot lines after cli.py:717:
```python
# M8 wires (insert ~ cli.py:717)
voss_md_text = voss_md.read_and_inject(cwd)              # Req 1
voss_md.ensure_migrated(cwd)                             # Req 2 (idempotent)
memory_store = MemoryStore(cwd).bind(session_id=record.id)  # Req 3 (lazy chroma)
```
Attach `voss_md_text` and `memory_store` to `ctx: ReplContext` (new fields).

**Pass-through to `run_turn`** (analog: cli.py:809–822):
```python
# cli.py:809-822 — run_turn invocation in the REPL loop
result = asyncio.run(
    run_turn(
        line,
        tools=tools,
        cwd=cwd,
        renderer=renderer,
        model=cfg.default_model,
        history=ctx.history,
        permissions=gate,
        provider=provider,
        session_id=record.id,
        cognition=bundle,
        prior_context=ctx.prior_context,
    )
)
```
**Apply:** Add `voss_md_text=voss_md_text` kwarg (passed through every turn, no re-read).

**Per-turn ledger write** (analog: cli.py:829–830):
```python
# cli.py:829-830 — record run on history
if result.run is not None:
    record.runs.append(asdict(result.run))
```
**Apply:** Add memory write after this line:
```python
if result.run is not None:
    record.runs.append(asdict(result.run))
    ctx.memory_store.write_ledger(result.run, session_id=record.id)  # M8
    ctx.memory_store.write_turn(role="assistant", content=result.final,
                                 session_id=record.id, turn_idx=len(ctx.history.turns))
```

**REPL exit hook for conventions** (analog: cli.py:773–778 — EOFError/KeyboardInterrupt is the clean-exit path):
```python
# cli.py:773-778 — clean exit detected via EOFError/KeyboardInterrupt
while True:
    try:
        line = input("▌ ")
    except (EOFError, KeyboardInterrupt):
        click.echo()
        return
```
**Apply:** Replace the bare `return` with a hook call:
```python
except (EOFError, KeyboardInterrupt):
    click.echo()
    try:
        conventions.run_on_clean_exit(ctx, history=ctx.history, record=record)
    except Exception as exc:  # noqa: BLE001 — never break exit
        click.echo(f"conventions extraction skipped: {exc}", err=True)
    return
```

**`voss do` boot wire points** (analog: cli.py:540 `do_bundle = cognition_mod.load(cwd)`):
```python
do_bundle = cognition_mod.load(cwd)
# M8 additions (synthesized, same shape):
voss_md_text = voss_md.read_and_inject(cwd)
memory_store = MemoryStore(cwd).bind(session_id=record.id)
```
Pass `voss_md_text` to `run_turn` and call `conventions.run_on_clean_exit(...)` after the `do_cmd` completes (per A6 RESOLVED in RESEARCH.md).

---

### `voss/harness/agent.py` (MODIFIED — sys_prompt assembly)

**Analog:** self — `_compose_cognition_prompt` (agent.py:52–80) + sys_prompt join at agent.py:297–299

**sys_prompt composition pattern** (agent.py:297–299):
```python
# agent.py:297-299 — sys_prompt = join of optional non-empty blocks
sys_prompt = "\n\n".join(
    s for s in (cognition_text, prior_context_text, PLAN_SYSTEM) if s
)
```
**Apply:** Insert `voss_md_block` at the **head** of the tuple (D-08: full bytes, before cognition):
```python
voss_md_block = (
    f"# VOSS.md\n{voss_md_text}" if voss_md_text else ""
)
sys_prompt = "\n\n".join(
    s for s in (voss_md_block, cognition_text, prior_context_text, PLAN_SYSTEM) if s
)
```

**New keyword arg on `run_turn`** (analog: existing `cognition=None, prior_context=None` kwargs at agent.py:249–250):
```python
# agent.py:236-250 — run_turn signature with optional kwargs defaulting to None
async def run_turn(
    task: str,
    *,
    tools: dict[str, ToolEntry],
    cwd: Path,
    ...
    cognition=None,
    prior_context: dict | None = None,
) -> TurnResult:
```
**Apply:** Add `voss_md_text: str | None = None`.

---

### `voss/harness/cognition.py` (MODIFIED — rewire `_load_arch` read path)

**Analog:** self — `_load_arch` at cognition.py:101–134 (Pitfall 2 — read path must follow write path)

**Current loader** (cognition.py:101–114):
```python
def _load_arch(path: Path, errors: list[str]):
    """Return (body_str, ArchitectureFrontmatter | None). Never raises."""
    if not path.exists():
        return None, None
    try:
        text = path.read_text()
    except OSError as e:
        errors.append(f"{path}: read error: {e}")
        return None, None

    m = FRONTMATTER_RE.match(text)
    ...
```
**Apply:** New helper signature `_load_arch_from_voss_md(cwd, errors)`. Reads `cwd/VOSS.md`, extracts `id=architecture` fence body via `voss_md.parse()`, returns the same `(body, ArchitectureFrontmatter)` tuple. The existing `FRONTMATTER_RE.match()` continues to work because the fence body still begins with `---\n...\n---\n` (Pitfall 2 + A8). Update `load()` at cognition.py:207–229 to call the new helper instead of reading `root / "architecture.md"`.

**Critical preserve:** `FRONTMATTER_RE` (cognition.py:38) stays unchanged. Don't drop the frontmatter when migrating; copy it into the head of the fence body.

---

### `voss/harness/skills/analyze.py` (MODIFIED — rewire write target)

**Analog:** self — write target + backup-and-restore logic at analyze.py:36–80

**Current write-target wiring** (analyze.py:36–42):
```python
# analyze.py:36-42 — current architecture.md path resolution + backup
arch_path = cognition.voss_dir(cwd) / "architecture.md"
arch_backup: str | None = None
if arch_path.exists():
    try:
        arch_backup = arch_path.read_text()
    except (OSError, UnicodeDecodeError):
        arch_backup = None
```
**Apply:** Replace with VOSS.md fence-body resolution:
```python
from .. import voss_md

voss_md_path = cwd / "VOSS.md"
fence_id = "architecture"

# Read current fence body for backup
arch_backup: str | None = None
if voss_md_path.exists():
    try:
        arch_backup = voss_md.read_fence_body(voss_md_path, fence_id=fence_id)
    except (OSError, UnicodeDecodeError, voss_md.HashMismatch):
        arch_backup = None
```

**Single-fs_write contract** (analyze.py:44–57) — keep unchanged. The agent still emits ONE `fs_write`, but the target is now derived from `voss_md.machine_fence_path_or_marker(...)` and the post-write step folds the agent's output into the fence body with hash recompute. **Key constraint:** preserve the "one write" contract — the planner may need to add a post-skill step that reads the agent's fs_write output, validates frontmatter, and rewrites it into the VOSS.md fence with hash header.

**Post-write schema check + rollback** (analyze.py:59–80) — preserve the pattern:
```python
# analyze.py:59-80 — schema check via FRONTMATTER_RE, rollback to backup on failure
arch_ok = False
if arch_path.exists():
    try:
        text = arch_path.read_text()
    except OSError:
        text = ""
    if cognition.FRONTMATTER_RE.match(text):
        arch_ok = True

if not arch_ok:
    if arch_backup is not None:
        arch_path.write_text(arch_backup)
        click.echo("warning: architecture.md regeneration failed schema check; rolled back", err=True)
```
**Apply:** Replace `arch_path.read_text()` and `arch_path.write_text(arch_backup)` with `voss_md.read_fence_body(...)` and `voss_md.write_fence_body(..., id="architecture", body=arch_backup)`. The `FRONTMATTER_RE.match(text)` check stays identical (fence body still starts with `---\n`).

---

## Shared Patterns

### Pattern A: Soft-dependency catch (chroma → keyword fallback)

**Source:** `voss_runtime/memory/semantic.py:21–31`
**Apply to:** `memory_store.py::bind()`, `memory_store.py::recall()`

```python
# semantic.py:21-31 — catch ImportError at the use site, surface friendly hint via ModuleNotFoundError
try:
    import chromadb
    from chromadb.config import Settings
except ImportError as e:
    raise ModuleNotFoundError(
        "chromadb is not installed. Semantic memory is an optional "
        "Voss feature. Install it with:\n"
        "    pip install 'voss[search]'\n"
    ) from e
```
**Important:** at the harness layer, catch the `ModuleNotFoundError` and route to keyword fallback. Do NOT let it propagate to the user — per SPEC constraint "Recall degrades to keyword path without raising ImportError when chromadb is uninstalled."

---

### Pattern B: Preserve-if-exists scaffold writes under `.voss/`

**Source:** `voss/harness/cognition.py:597–604` (`write_voss_gitignore`)
**Apply to:** `voss_md.ensure_migrated()`, `memory_store.ensure_layout()`

```python
def write_X(cwd: Path) -> bool:
    target = cwd / ".voss" / "..." / "file"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    target.write_text("...content...")
    return True
```
Returns `True` if newly written, `False` if already existed. Idempotent on repeated invocations.

---

### Pattern C: Slug + reserve_filename for human-readable date-stamped paths

**Source:** `voss/harness/cognition.py:354–367`
**Apply to:** Conventions, notes, archive filenames

```python
# cognition.py:354-367 — slug strips path-traversal chars; reserve_filename ensures unique YYYY-MM-DD-<slug>.md
def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60] or "untitled"

def reserve_filename(dir_: Path, base: str, ext: str = ".md") -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = dir_ / f"{today}-{base}{ext}"
    n = 2
    while p.exists():
        p = dir_ / f"{today}-{base}-{n}{ext}"
        n += 1
    return p
```
**Reuse verbatim** — already strips path-traversal (`[^a-z0-9]+` collapses to `-`). Security §V10/V12 compliant per RESEARCH.

---

### Pattern D: Slash command (handler signature + registry registration)

**Source:** `voss/harness/slash.py:11–19` + `voss/harness/cli.py:464–483`
**Apply to:** All four new slash handlers in `cli.py`

```python
# slash.py:11-19 — frozen dataclass; handler signature (ctx, args, raw_line) -> None
@dataclass(frozen=True)
class SlashCommand:
    name: str
    help: str
    handler: SlashHandler         # Callable[[Any, list[str], str], None]
    aliases: tuple[str, ...] = ()
    mutating: bool = False
    hidden: bool = False
```
- `/forget` and `/save` get `mutating=True` (matches existing `_save`, `_analyze` flags).
- All four use `shlex.split` via `SlashRegistry.dispatch` (slash.py:56) — no separate parser needed.

---

### Pattern E: Backup-and-restore on schema-failed agent writes

**Source:** `voss/harness/skills/analyze.py:38–80`
**Apply to:** Any future single-fs_write skill, and to VOSS.md fence writes specifically

```python
# analyze.py:38-80 — read backup BEFORE agent call, validate AFTER, rollback if invalid
arch_backup: str | None = None
if path.exists():
    try:
        arch_backup = path.read_text()
    except (OSError, UnicodeDecodeError):
        arch_backup = None

# ... LLM call ...

if not validates(text):
    if arch_backup is not None:
        path.write_text(arch_backup)
        click.echo("warning: ...rolled back", err=True)
```
**For M8:** the rollback semantics extend to VOSS.md fence-body writes. If the agent's fs_write output fails `FRONTMATTER_RE` validation, restore the previous fence body and emit a one-line warning. Hash mismatch (D-07) is a separate error path — refuse + diff, do NOT auto-rollback.

---

### Pattern F: Click subcommand group with `--cwd` flag

**Source:** `voss/harness/cli.py:1064–1080` (plugin_group), :1083–1116 (skill_group)
**Apply to:** `voss memory` subcommand group in `memory_cli.py`

```python
@click.group("plugin")
def plugin_group() -> None:
    """Manage plugin manifest enablement."""

@plugin_group.command("enable")
@click.argument("plugin_id")
def plugin_enable_cmd(plugin_id: str) -> None:
    ...
```
- Register the group in `AGENT_COMMANDS` tuple at cli.py:1263.
- Always include `--cwd` option (`default=".", type=click.Path(file_okay=False)`) — matches doctor_cmd, do_cmd convention.

---

### Pattern G: File permissions on sensitive writes

**Source:** `voss/harness/session.py:144`
**Apply to:** `turns/*.jsonl`, `notes/*.md`, `ledgers/*.jsonl` — all writes that may contain user content

```python
# session.py:143-144 — chmod 0o600 after write for files containing user prompts
path.write_text(json.dumps(asdict(record), indent=2))
path.chmod(0o600)
```

---

## No Analog Found

Files with no close existing match. Planner should follow RESEARCH.md patterns directly:

| File / Capability | Reason | RESEARCH.md guidance |
|-------------------|--------|----------------------|
| Per-source advisory lockfile (D-13) | No existing `fcntl.flock` usage in `voss/harness/` (grep returns 0) | RESEARCH Pitfall 3 — recommend `portalocker>=2.8` as core dep |
| Per-source size accounting + inline eviction (D-16) | No existing size-cap accounting pattern; `path.stat().st_size` summation is novel | RESEARCH Pattern 3 (`write_with_quota`) |
| Chroma `where`-filtered `.delete()` (D-15 vacuum) | No existing chroma admin usage at harness layer | RESEARCH "Don't Hand-Roll" table — `collection.delete(where={"tombstoned": True})` cited from chroma docs |
| VOSS.md fence parser + hash guard (D-05, D-07) | Net-new file format | RESEARCH Pattern 1 (synthesized; closest is `FRONTMATTER_RE`) |
| Keyword-fallback scoring for recall | No existing in-codebase keyword scorer | RESEARCH Pattern 2 (synthesized; `Path.rglob` + substring count) |

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss_runtime/memory/`, `voss/harness/skills/`
**Files scanned:** 9 primary analogs read in full or relevant sections:
- `voss/harness/slash.py` (full)
- `voss/harness/cli.py` (lines 380–484, 600–834, 1064–1130, 1240–1315)
- `voss/harness/agent.py` (lines 1–80, 220–340)
- `voss/harness/cognition.py` (lines 1–230, 350–370, 580–660)
- `voss/harness/recorder.py` (full)
- `voss/harness/session.py` (lines 110–200)
- `voss/harness/skills/analyze.py` (full)
- `voss_runtime/memory/semantic.py` (full)
- `voss_runtime/memory/episodic.py` (full)

**Pattern extraction date:** 2026-05-14
**Output file:** `.planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md`
