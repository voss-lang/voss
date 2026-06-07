# Phase V9: Audit Product — Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 9 (3 modified, 6 created)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/audit/load.py` (modify) | loader | file-I/O | itself (existing); `voss/harness/board/cli_view.py` for run_id/traversal guard | exact (self-extension) |
| `voss/harness/audit/model.py` (modify) | model | transform | itself (existing `AuditSnapshot` + sub-types) | exact (self-extension) |
| `voss/harness/cli.py` — `audit_cmd` (modify) | controller | request-response | `review_cmd` (lines 2487–2516); `board_cmd` (lines 3847–3862) | exact |
| `voss/harness/audit/report.py` (new) | service | transform | `voss/harness/audit/load.py` (assembly pattern); `voss/harness/board/cli_view.py` (render_board assembly) | role-match |
| `voss/harness/audit/render.py` (new) | utility | transform | `voss/harness/board/cli_view.py` (text render); `review_cmd`'s `_render_review_card` (lines 2462–2484) | role-match |
| `voss/harness/audit/calibration.py` (new) | service | batch | `voss/harness/board/review_persistence.py` (sidecar schema); `_load_review_sidecars` pattern in RESEARCH.md | partial-match |
| sign-off forcing function in `team_run_cmd` (modify) | controller | request-response | `team_run_cmd` lines 4114–4120 (plain prompt, no gate); `_persist_run_final` lines 3979–4000 (0o600 sidecar write) | exact (self-extension) |
| `tests/harness/audit/` new test files (new) | test | — | `tests/harness/audit/test_o6_fixtures.py`; `test_snapshot_loader.py` | exact |
| `tests/harness/audit/test_o6_fixtures.py` (modify) | test-fixture | — | itself (`build_fixture_tree`) | exact (self-extension) |

---

## Pattern Assignments

### `voss/harness/audit/load.py` (modify — self-extension)

**Analog:** itself (`voss/harness/audit/load.py` lines 243–343) + `voss/harness/board/cli_view.py` lines 81–128 (run_id resolution + traversal guard)

**Three changes:**

**1. Filter landmines from node glob** (analog: load.py line 263, cli_view.py line 132):
```python
# BEFORE (line 263):
node_files = sorted(tree_dir.glob("*.json"))

# AFTER — filter run-final.json and *.review.json before _read_node_file:
node_files = [
    p for p in sorted(run_dir.glob("*.json"))
    if p.name != "run-final.json" and not p.name.endswith(".review.json")
]
```

**2. run_id parameter + latest-by-mtime fallback** (analog: `_latest_root_id` lines 2451–2459, `cli_view.py` lines 117–128):
```python
# Current signature (line 243):
def load_audit_snapshot(root: Path) -> AuditSnapshot:

# New signature:
def load_audit_snapshot(root: Path, run_id: str | None = None) -> AuditSnapshot:
    sessions_dir = root / ".voss" / "sessions"
    ...
    if run_id is not None:
        tree_dir = sessions_dir / run_id
        if not tree_dir.is_dir():
            raise AuditLoadError(sessions_dir, f"unknown run_id: {run_id}")
    else:
        root_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
        if not root_dirs:
            raise AuditLoadError(sessions_dir, "no session tree directories found")
        tree_dir = max(root_dirs, key=lambda d: d.stat().st_mtime)
```

**3. Separate `run-final.json` read** (analog: `_persist_run_final` lines 3979–4000 shows the file's location and shape):
```python
def _load_run_final_file(run_dir: Path) -> dict | None:
    path = run_dir / "run-final.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
```

**4. `.review.json` sidecar load** (analog: `review_cmd` lines 2506–2516):
```python
def _load_review_sidecars(run_dir: Path) -> dict[str, dict]:
    """Returns {node_id: sidecar_dict}. Graceful on read errors."""
    result = {}
    for path in sorted(run_dir.glob("*.review.json")):
        node_id = path.name[: -len(".review.json")]
        try:
            result[node_id] = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            result[node_id] = {}
    return result
```

**Import guard constraint** (from `TestNoLiveImports` in `test_snapshot_loader.py` lines 175–200):
`load.py` must NOT import `voss.harness.board`, `.em`, or `.cli`. Principles and team config must be loaded in `report.py`, not here.

---

### `voss/harness/audit/model.py` (modify — add `AuditReport` dataclass)

**Analog:** existing `AuditSnapshot` (lines 110–122) and all sub-types in the same file.

**Existing frozen dataclass pattern** (lines 16–26, representative):
```python
@dataclass(frozen=True, slots=True)
class RoutingRationale:
    """Normalized snapshot of an EM routing decision."""
    id: str
    card_id: str
    chosen_role: str
    candidates_considered: tuple[str, ...]
    rationale_text: str
    ts: str
    confidence_hint: Optional[float] = None
```

**New `AuditReport` type to add** (same pattern as `AuditSnapshot`):
```python
@dataclass(frozen=True, slots=True)
class AuditReport:
    """Complete V9 audit report: wraps AuditSnapshot + all PRD §9 sections."""
    run_id: str
    idea: str                               # from run-final.json["idea"]
    principles: tuple[tuple[str, str], ...]  # from principles.yml via report.py
    team_config: dict                        # from team.voss (serializable form)
    snapshot: "AuditSnapshot"               # existing node/card/verdict data
    review_sidecars: dict[str, dict]        # {node_id: sidecar_dict}
    run_final: Optional[dict]               # from run-final.json (full file)
    signoff_ack: Optional[dict]             # from .signoff-ack.json
    calibration: "CalibrationReport"        # from calibration.py
    sections_missing: tuple[str, ...]       # sections with no persisted data
```

**`CalibrationReport` dataclass** (same pattern):
```python
@dataclass(frozen=True, slots=True)
class CalibrationReport:
    total_pairs: int
    false_pass_count: int
    slop_rejection_count: int
    false_pass_rate: float
    slop_rejection_rate: float
    spot_audit_paths: tuple[str, ...]
```

All types: `frozen=True, slots=True`, primitives/tuples/dicts only — no board/EM/CLI imports. Use `Optional` from `typing` (consistent with existing imports at line 11).

---

### `voss/harness/cli.py` — `audit_cmd` (add to AGENT_COMMANDS)

**Analog:** `review_cmd` (lines 2487–2516) — read-only from persisted files, `run_id` optional arg, `_latest_root_id` fallback, `SystemExit(1)` on unknown run.

**`review_cmd` pattern to replicate** (lines 2487–2516):
```python
@click.command("review")
@click.argument("run_id", required=False)
def review_cmd(run_id: str | None) -> None:
    """Show per-card A + B review for a run (latest if no run_id).

    Read-only from the `.review.json` sidecars written by the board; no live
    Board / SessionTreeManager / provider is constructed (VREV-10, D-11).
    """
    cwd = Path.cwd()
    sessions_dir = cwd / ".voss" / "sessions"
    if run_id is None:
        run_id = _latest_root_id(sessions_dir)
        if run_id is None:
            click.echo("(no review runs found)", err=True)
            raise SystemExit(1)
    sidecar_dir = sessions_dir / run_id
    if not sidecar_dir.is_dir():
        click.echo(f"unknown run_id: {run_id}", err=True)
        raise SystemExit(1)
```

**`board_cmd` decorators to mirror** (lines 3847–3855):
```python
@click.command("board")
@click.argument("root_id", required=False, default=None)
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
```

**`audit_cmd` signature** (extend review_cmd with --format and --output options):
```python
@click.command("audit")
@click.argument("run_id", required=False)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--format", "fmt", type=click.Choice(["text", "json", "markdown"]), default="text")
@click.option("--output", "output_path", default=None, type=click.Path())
def audit_cmd(run_id: str | None, cwd_str: str, fmt: str, output_path: str | None) -> None:
    """Show complete audit for a run (latest if no run_id). Read-only."""
```

**Path-traversal guard** (analog: `cli_view.py` lines 97–116 — copy this pattern for `run_id`):
```python
if run_id is not None:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        click.echo(f"<error: invalid run_id {run_id!r}>", err=True)
        raise SystemExit(1)
    candidate = (sessions_dir / run_id).resolve()
    if candidate.parent != sessions_dir.resolve():
        click.echo(f"<error: invalid run_id {run_id!r}>", err=True)
        raise SystemExit(1)
```

**AGENT_COMMANDS registration** (lines 4163–4197 — add `audit_cmd` alongside `review_cmd` and `board_cmd`):
```python
AGENT_COMMANDS = (
    ...
    review_cmd,
    ...
    board_cmd,
    audit_cmd,    # <-- add here
)
```

---

### `voss/harness/audit/report.py` (new)

**Analog:** `voss/harness/audit/load.py` (assembly loop pattern, lines 286–333) + `voss/harness/board/cli_view.py` `render_board` (lines 81–157, shows how to aggregate persisted data without live Board/EM imports).

**Module header pattern** (mirror `load.py` lines 1–23):
```python
"""V9 AuditReport aggregate — assembles all PRD §9 sections from persisted data.

Read-only. No imports from voss.harness.board, .em, or .cli.
Principles and team config are loaded HERE (not in load.py) to satisfy the
TestNoLiveImports guard.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from voss.harness.audit.load import AuditLoadError, _load_review_sidecars, load_audit_snapshot
from voss.harness.audit.model import AuditReport, AuditSnapshot, CalibrationReport
```

**Assembly function shape** (analog: `load_audit_snapshot` lines 243–343):
```python
def build_audit_report(
    cwd: Path,
    run_id: str | None = None,
    calibration: CalibrationReport | None = None,
) -> AuditReport:
    """Assemble AuditReport from all persisted V2–V7 sources. Never writes."""
    sessions_dir = cwd / ".voss" / "sessions"
    snapshot = load_audit_snapshot(cwd, run_id=run_id)
    run_dir = sessions_dir / snapshot.root_id

    run_final = _load_run_final_file(run_dir)       # run-final.json
    sidecars = _load_review_sidecars(run_dir)        # *.review.json
    signoff_ack = _load_signoff_ack(run_dir)         # .signoff-ack.json

    # Principles — import allowed here (not in load.py)
    from voss.harness.principles import DEFAULT_PRINCIPLES, load_principles
    try:
        layer = load_principles(cwd)
        principles = tuple(layer.items) or DEFAULT_PRINCIPLES
    except Exception:
        principles = DEFAULT_PRINCIPLES

    # Team config — import allowed here
    team_config = _load_team_config_dict(cwd)

    sections_missing = _compute_missing_sections(run_final, sidecars, snapshot)

    return AuditReport(
        run_id=snapshot.root_id,
        idea=run_final.get("idea", "") if run_final else "",
        principles=principles,
        team_config=team_config,
        snapshot=snapshot,
        review_sidecars=sidecars,
        run_final=run_final,
        signoff_ack=signoff_ack,
        calibration=calibration or _empty_calibration(),
        sections_missing=sections_missing,
    )
```

**Graceful missing-section pattern** (analog: `load.py` line 325–330 fallback for `leak6`):
Missing sources render `""` / `{}` / `()` — never `None` that crashes a renderer. `sections_missing` tuple tracks which sections had no data.

**Claims-vs-evidence tagging** (per RESEARCH.md §VAUD-03):
EM-authored claims = transitions where `kind` in `{"em.ticket", "em.run_final", "em.routing"}`.
Verified evidence = sidecar `a_verification` (A ran/authored) + `b_verdict` (B assessed independently).
Unsupported claim: node has `em.ticket` AND sidecar is absent or has `a_verification: null` AND `b_verdict: null`.

---

### `voss/harness/audit/render.py` (new)

**Analog:** `_render_review_card` in `cli.py` lines 2462–2484 (card-level text rendering); `cli_view.py` lines 148–157 (section-by-section emit with `click.echo`); `_persist_run_final` lines 3998–3999 (`json.dumps(data, indent=2)` + stdlib only).

**Text render pattern** (analog: `cli_view.py` lines 148–157):
```python
def render_text(report: "AuditReport") -> str:
    lines: list[str] = []
    lines.append(f"# Audit: {report.run_id}")
    lines.append(f"## §1 Goal\n{report.idea or '_none_'}")
    # ... one section per PRD §9 entry
    # Missing sections: `_none_` (never skip, never crash)
    return "\n".join(lines)
```

**JSON render pattern** (`json.dumps(sort_keys=True)` for determinism):
```python
def render_json(report: "AuditReport") -> str:
    """Deterministic JSON. Uses sort_keys=True — same data → same bytes."""
    data = _to_dict(report)   # recursive helper; tuples → lists for JSON
    return json.dumps(data, sort_keys=True, indent=2)
```

**`_to_dict` helper** (analog: `review_persistence.py` line 57 `dataclasses.asdict(verdict_b)`; `_persist_run_final` line 3992 `asdict(rf)`):
```python
import dataclasses

def _to_dict(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    return obj
```
Note: `dataclasses.asdict` converts tuples to lists internally — that is acceptable for JSON export. Document in module docstring: "JSON round-trip yields lists where `AuditReport` uses tuples; both are ordered sequences."

**Markdown render** (section headers map 1:1 to PRD §9; code blocks for JSON sub-data):
```python
def render_markdown(report: "AuditReport") -> str:
    """Markdown export. Each PRD §9 section is a ## header. Missing → _none_."""
    sections = []
    sections.append(f"## §1 Goal\n\n{report.idea or '_none_'}\n")
    sections.append(f"## §3 Active Principles\n\n" + _format_principles(report.principles))
    # ... etc.
    return "\n".join(sections)
```

**Determinism requirement:** render functions must be pure — no `datetime.now()`, no random, no mtime-derived values in output. Sort all lists by a stable key before rendering.

---

### `voss/harness/audit/calibration.py` (new)

**Analog:** `voss/harness/board/review_persistence.py` (sidecar schema — `a_verification.result`, `b_verdict.verdict`); `review_cmd` lines 2506–2516 (sidecar glob pattern).

**Sidecar schema** (from `review_persistence.py` lines 55–65):
```python
payload = {
    "a_verification": {        # or None
        "test_path_or_rubric": ...,
        "result": "pass" | "fail",
        "notes": ...,
    },
    "b_verdict": {             # or None; this is dataclasses.asdict(verdict_b)
        "conf": float,
        "source": "B",
        "tier": "fast" | "strong",
        "verdict": "pass" | "fail" | "block",
        "notes": str,
        "evidence_refs": [...],
        "domain_inferred": ...,
    },
    "final_outcome": "Done" | "Blocked",
}
```

**Calibration function shape** (formulas from RESEARCH.md §6):
```python
@dataclass(frozen=True, slots=True)
class CalibrationReport:
    total_pairs: int
    false_pass_count: int
    slop_rejection_count: int
    false_pass_rate: float          # false_pass_count / total_pairs (0.0 if 0)
    slop_rejection_rate: float      # slop_rejection_count / |B verdicts| (0.0 if 0)
    spot_audit_paths: tuple[str, ...]


def compute_calibration(sessions_dir: Path, spot_k: int = 3, seed: int | None = None) -> CalibrationReport:
    """Aggregate across ALL runs in sessions_dir — not just one run."""
    all_sidecars: list[Path] = sorted(sessions_dir.rglob("*.review.json"))
    false_pass = slop_reject = total = b_total = 0
    for path in all_sidecars:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        a_result = (data.get("a_verification") or {}).get("result", "")
        b_verdict = (data.get("b_verdict") or {}).get("verdict", "")
        if a_result and b_verdict:
            total += 1
            if a_result == "pass" and b_verdict in ("fail", "block"):
                false_pass += 1
        if b_verdict:
            b_total += 1
            if b_verdict == "block":
                slop_reject += 1
    spot = _select_spot_audit(all_sidecars, k=spot_k, seed=seed)
    return CalibrationReport(
        total_pairs=total,
        false_pass_count=false_pass,
        slop_rejection_count=slop_reject,
        false_pass_rate=false_pass / total if total > 0 else 0.0,
        slop_rejection_rate=slop_reject / b_total if b_total > 0 else 0.0,
        spot_audit_paths=tuple(str(p) for p in spot),
    )
```

**Spot-audit hook** (deterministic given seed — use `random.Random(seed)`):
```python
import random

def _select_spot_audit(paths: list[Path], k: int, seed: int | None) -> list[Path]:
    rng = random.Random(seed)
    population = list(paths)
    return rng.sample(population, min(k, len(population)))
```

No board/EM/CLI imports. Stdlib only except `from voss.harness.audit.model import CalibrationReport`.

---

### Sign-off forcing function in `voss/harness/cli.py` — `team_run_cmd` (modify)

**Analog:** existing `team_run_cmd` lines 4114–4120 (the plain prompt that V9 replaces with a gate); `_persist_run_final` lines 3979–4000 (0o600 sidecar write pattern to copy for `.signoff-ack.json`).

**Existing plain prompt** (lines 4114–4120 — what V9 replaces):
```python
decision = click.prompt(
    "Sign off on this run (approve/reject)",
    type=click.Choice(["approve", "reject"]),
)
_persist_run_final(rf, cwd, decision=decision)
click.echo(f"sign-off recorded: {decision}")
raise click.exceptions.Exit(0)
```

**V9 gate to insert before the approve/reject prompt** (new code at same location):
```python
# Compute risk summary from rf
killed_count = rf.killed_count
misroute_count = sum(
    1 for r in snapshot.routings
    if r.confidence_hint is not None and r.confidence_hint < 0.7
)
if killed_count > 0 or misroute_count > 0:
    click.echo(f"\nRisk summary: {killed_count} killed card(s), {misroute_count} misroute candidate(s).")
    # ... display card summaries ...
    ack = click.prompt("Acknowledge killed/misroute risks? Type 'yes' to continue")
    if ack.strip().lower() != "yes":
        click.echo("Sign-off aborted — acknowledgement required.", err=True)
        raise click.exceptions.Exit(1)
    _write_signoff_ack(cwd, rf.root_id, killed_count=killed_count, misroute_count=misroute_count)
```

**`_write_signoff_ack` sidecar write** (analog: `_persist_run_final` lines 3987–3999 — same mkdir+write+chmod pattern):
```python
def _write_signoff_ack(cwd: Path, root_id: str, *, killed_count: int, misroute_count: int) -> Path:
    from datetime import datetime, timezone
    run_dir = cwd / ".voss" / "sessions" / root_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / ".signoff-ack.json"
    data = {
        "ack_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "killed_count": killed_count,
        "misroute_count": misroute_count,
    }
    path.write_text(json.dumps(data, indent=2))
    path.chmod(0o600)
    return path
```

**Key constraint:** `.signoff-ack.json` is a NEW file, not a mutation of `run-final.json` or any node JSON. This is the same pattern as `run-final.json` itself — a governance record alongside the audited data.

---

### `tests/harness/audit/` — new test files

**Analog:** `tests/harness/audit/test_snapshot_loader.py` (class-per-concern, `fixture_root` pytest fixture that calls `build_fixture_tree`); `test_o6_fixtures.py` (fixture tree builder pattern).

**Test module header pattern** (copy from `test_snapshot_loader.py` lines 1–24):
```python
"""<description>.

Verifies <what>. Uses tmp_path; never writes to the real .voss/ directory.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.harness.audit.test_o6_fixtures import build_fixture_tree
from voss.harness.audit.<module> import <symbols>
```

**Standard pytest fixture** (analog: `test_snapshot_loader.py` lines 27–30):
```python
@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    build_fixture_tree(tmp_path)
    return tmp_path
```

**`build_fixture_tree` extension** (analog: `test_o6_fixtures.py` lines 178–326 — add `.review.json` sidecar files alongside each node JSON):
The extension adds sidecar creation after each `path.write_text(...)` call:
```python
# In build_fixture_tree, after writing node_ab_block:
sidecar_path = sessions_dir / f"node_ab_block1.review.json"
sidecar_path.write_text(json.dumps({
    "a_verification": {"test_path_or_rubric": "test_ab", "result": "pass", "notes": "A passed"},
    "b_verdict": {"conf": 0.30, "source": "B", "tier": "strong", "verdict": "block",
                  "notes": "B blocked", "evidence_refs": ["ev_b_1"], "domain_inferred": "backend"},
    "final_outcome": "Blocked",
}, indent=2))
sidecar_path.chmod(0o600)
paths["node_ab_block_review"] = sidecar_path
```

**CLI test pattern** (analog: `test_snapshot_loader.py` class structure; use `click.testing.CliRunner`):
```python
from click.testing import CliRunner
from voss.harness.cli import audit_cmd

class TestAuditCli:
    def test_exits_0_for_latest(self, fixture_root: Path):
        runner = CliRunner()
        result = runner.invoke(audit_cmd, ["--cwd", str(fixture_root)])
        assert result.exit_code == 0

    def test_exits_nonzero_for_unknown_run(self, fixture_root: Path):
        runner = CliRunner()
        result = runner.invoke(audit_cmd, ["nonexistent_run_id", "--cwd", str(fixture_root)])
        assert result.exit_code != 0
        assert "unknown" in (result.output + (result.stderr or "")).lower()
```

**Determinism test pattern** (analog: `TestDeterminism` in `test_snapshot_loader.py` lines 158–172):
```python
class TestDeterminism:
    def test_two_renders_identical(self, fixture_root: Path):
        out1 = render_text(build_audit_report(fixture_root))
        out2 = render_text(build_audit_report(fixture_root))
        assert out1 == out2

    def test_json_sort_keys_stable(self, fixture_root: Path):
        out1 = render_json(build_audit_report(fixture_root))
        out2 = render_json(build_audit_report(fixture_root))
        assert out1 == out2
```

**No-live-imports guard extension** (analog: `TestNoLiveImports` lines 175–200 — extend to cover `report.py`, `render.py`, `calibration.py`):
```python
def test_report_module_has_no_board_imports(self):
    import voss.harness.audit.report as rpt
    src = Path(rpt.__file__).read_text()
    for forbidden in ("from voss.harness.board", "from voss.harness.em"):
        assert forbidden not in src
```

**Test invocation:**
```bash
.venv/bin/python -m pytest tests/harness/audit/ -x -v
```

---

## Shared Patterns

### Read-Only CLI Command Pattern
**Source:** `voss/harness/cli.py` `review_cmd` lines 2487–2516 + `board_cmd` lines 3847–3862
**Apply to:** `audit_cmd`
```python
# 1. Optional run_id arg, --cwd option, no live Board/Manager construction
# 2. _latest_root_id(sessions_dir) when run_id is None
# 3. SystemExit(1) with click.echo(..., err=True) on unknown run
# 4. raise click.exceptions.Exit(0) on success
```

### 0o600 Sidecar Write Pattern
**Source:** `voss/harness/session_tree.py` `_write_node_file` lines 107–112; `_persist_run_final` lines 3987–3999; `review_persistence.py` lines 61–65
**Apply to:** `_write_signoff_ack` in `cli.py`
```python
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2))
path.chmod(0o600)
```

### Path-Traversal Guard
**Source:** `voss/harness/board/cli_view.py` lines 97–116
**Apply to:** `audit_cmd` `run_id` validation
```python
if "/" in run_id or "\\" in run_id or ".." in run_id:
    click.echo(f"<error: invalid run_id {run_id!r}>", err=True)
    raise SystemExit(1)
candidate = (sessions_dir / run_id).resolve()
if candidate.parent != sessions_dir.resolve():
    ...
```

### Frozen Dataclass + No-Live-Imports
**Source:** `voss/harness/audit/model.py` lines 7–122 + `test_snapshot_loader.py` `TestNoLiveImports` lines 175–200
**Apply to:** all new `audit/` module files
- All dataclasses: `frozen=True, slots=True`, primitives/tuples/dicts only
- `model.py`, `load.py`, `calibration.py`: zero imports from `voss.harness.board`, `.em`, `.cli`
- `report.py`: MAY import `voss.harness.principles` and `voss.harness.team` (these are not forbidden)

### Deterministic Sort
**Source:** `voss/harness/audit/load.py` lines 272 (`raw_nodes.sort(key=lambda d: d["id"])`)
**Apply to:** all data assembly in `report.py`; all render output in `render.py`
- Node/card sorting: by `id` (string sort), never by mtime
- JSON export: `json.dumps(data, sort_keys=True, indent=2)`
- Sidecar dict: keyed by `node_id` string — sort keys before iterating

### Graceful Missing-Source Handling
**Source:** `voss/harness/audit/load.py` lines 325–330 (`if leak6 is None: leak6 = Leak6Assessment(...)`)
**Apply to:** all 15 PRD §9 sections in `report.py` and `render.py`
- Missing data → empty tuple/dict/string, never `None` that crashes renderer
- Render output for missing section: `_none_` (explicit, per VAUD-02 acceptance criteria)

---

## No Analog Found

All files have analogs in the existing codebase. No entries.

---

## Landmines (planner must address)

1. **`run-final.json` in node glob** (`load.py` line 263): crashes `_read_node_file` with `AuditLoadError("missing required 'id' field")`. Fix is the filter in the load.py modification above.
2. **`.review.json` sidecars in node glob** (`load.py` line 263): will also fail the `id` check. Same filter fix.
3. **`load.py` import guard**: `TestNoLiveImports` forbids `voss.harness.principles` and `voss.harness.team` imports in `load.py`. Principles/team loading must live in `report.py`.
4. **`load_audit_snapshot` loads first tree alphabetically** (line 255–257): not latest. `run_id` parameter + mtime fallback required.
5. **`dataclasses.asdict` converts tuples to lists**: JSON round-trip yields lists, not tuples. Document in `render.py`; do not assert `isinstance(x, tuple)` in round-trip tests.

---

## Metadata

**Analog search scope:** `voss/harness/audit/`, `voss/harness/cli.py`, `voss/harness/board/cli_view.py`, `voss/harness/board/review_persistence.py`, `voss/harness/session_tree.py`, `voss/harness/principles.py`, `tests/harness/audit/`
**Files scanned:** 10
**Pattern extraction date:** 2026-06-06
