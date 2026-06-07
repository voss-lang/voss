# Phase V9: Audit Product (supersedes O6) — Research

**Researched:** 2026-06-06
**Domain:** Python CLI / read-only audit aggregation / sign-off forcing function / reviewer calibration
**Confidence:** HIGH — all claims verified against live codebase

---

## Critical Finding: SPEC Says "Greenfield" — Code Says Otherwise

The V9-SPEC Background says "O6 planned but not executed; no audit code; no `voss audit`."
**This is partially wrong.** `voss/harness/audit/` is a 4-file package with 37 passing tests:

| File | What it does | Status |
|------|-------------|--------|
| `model.py` | Frozen audit dataclasses (`AuditSnapshot`, `AuditCard`, `AuditNode`, `KillRecord`, `RescopeRecord`, `RoutingRationale`, `ReviewerAssessment`, `LivenessEvent`, `Leak6Assessment`) | SHIPPED — 37 tests green |
| `load.py` | `load_audit_snapshot(root)` — reads node JSONs from a single session tree, assembles `AuditSnapshot` | SHIPPED — but missing key fields (see delta below) |
| `preflight.py` | `run_o6_preflight()` — verifies V2–V5 surfaces are importable | SHIPPED — passes with current codebase |
| `__init__.py` | Exports all model + preflight symbols | SHIPPED |

**However:** `voss audit` is NOT registered in `AGENT_COMMANDS` (confirmed grep). The existing code covers the session-tree node loading layer only. V9's delta is substantial. [VERIFIED: live codebase grep]

---

## Summary

V9 builds a complete read-only audit CLI (`voss audit <run_id>`) on top of data persisted by V2–V7. The existing `voss/harness/audit/` package gives a useful foundation — frozen dataclasses, a working node-JSON loader, and 37 green tests — but is missing 9 of the 15 PRD §9 sections, has no CLI registration, reads no `.review.json` sidecars or `run-final.json` file, covers none of the V2/V3 metadata (principles/team config), performs no calibration telemetry, and has no sign-off forcing function.

The architectural pattern for V9 is already established in the codebase: `voss review` and `voss board` are both registered read-only CLI commands that read only persisted files with no live Board/Manager construction. V9's `voss audit` follows this exact pattern, extending it with an aggregator that pulls from all persisted sources into a single `AuditReport` (a V9-level aggregate above the existing `AuditSnapshot`).

**Primary recommendation:** Build a new `voss/harness/audit/report.py` `AuditReport` aggregate (extending, not replacing, `AuditSnapshot`) and a `voss/harness/audit/render.py` Markdown/JSON exporter. Add `audit_cmd` to `AGENT_COMMANDS` in `cli.py`. Extend `load.py` to accept `run_id` + read `.review.json` sidecars, `run-final.json`, and principles/team config. The sign-off forcing function is a separate concern requiring a new acknowledgement sidecar written to disk but isolated from all audited records.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Audit data aggregation | `voss/harness/audit/` pkg | `cli.py` (thin dispatch) | audit/ already owns the domain; no live board/manager imports allowed |
| CLI registration + routing | `cli.py` (AGENT_COMMANDS) | — | All commands registered here; mirrors `board_cmd`, `review_cmd` pattern |
| `.review.json` sidecar reading | Extended `audit/load.py` | — | Per-card A+B verdicts are separate files from node JSONs |
| `run-final.json` reading | Extended `audit/load.py` | — | run-final is a separate file, not embedded in node transitions |
| Principles + team config reading | Extended `audit/load.py` | `principles.py`, `team.py` | V2/V3 sources; audit must not import live board/EM modules |
| Markdown + JSON rendering | New `audit/render.py` | — | Keep rendering separate from data model |
| Sign-off acknowledgement write | `cli.py` (team_run_cmd) + new `audit_cmd` | New `.ack.json` sidecar | Acknowledgement is a NEW record; never mutates audited run data |
| Calibration telemetry | New `audit/calibration.py` | Extended `load.py` | Compute from persisted B-verdict vs A-verification pairs |
| Leak-6 assessment | `audit/model.py` (existing) | Documented accepted gap | No standup→semantic.memory write path exists in V2–V7 substrate |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VAUD-01 | `voss audit <run_id>` CLI, deterministic, read-only | `audit_cmd` in AGENT_COMMANDS, mirrors `board_cmd`/`review_cmd` pattern; `_latest_root_id` helper already exists |
| VAUD-02 | Full audit content surface per PRD §9 (15 sections) | Existing `load.py` covers ~6 sections; 9 sections need new loaders |
| VAUD-03 | EM claims vs verified evidence, source-tagged | `em.ticket`/`em.run_final` = claims; `.review.json` A+B + `evidence_refs` = verified; new `source_tag` field on `AuditReport` items |
| VAUD-04 | Per-node budget accounting (limit/spent) | `envelope` dict on each node JSON; `rejected_raises[]` list; already in `AuditNode.envelope` |
| VAUD-05 | Scope violations + denied attempts | `rejected_raises[]` on node JSON (each entry has `attempted_delta`, `reason`); `scope`/`role` fields; not yet surfaced in `AuditSnapshot` |
| VAUD-06 | Reviewer-A and Reviewer-B outputs separately | `.review.json` sidecars have `a_verification` + `b_verdict` as distinct keys; load.py does NOT read these yet |
| VAUD-07 | Kill/rescope lineage + routing rationale | `em.kill`/`em.rescope`/`em.routing` transitions in node JSONs; already extracted by `load.py` |
| VAUD-08 | Markdown + JSON export | New `audit/render.py`; JSON must use `dataclasses.asdict` recursively; determinism via sorted keys |
| VAUD-10 | Residual-risk section + Leak-6 mitigate-or-accept | `Leak6Assessment` exists; no standup→semantic.memory path exists → accepted gap |
| VAUD-SIGNOFF | Hard gate: approve blocked until killed-card+misroute ack | V7 sign-off is a plain `click.prompt(Choice[approve,reject])` with no gate; V9 adds forced-ack step + new `.signoff-ack.json` sidecar |
| VAUD-CAL | Reviewer calibration telemetry: false-pass / slop-rejection rate | New `audit/calibration.py`; data source = `.review.json` sidecars across all runs in sessions dir |
</phase_requirements>

---

## Existing Audit Package — Complete Inventory

### What Is Already Shipped (do not rebuild)

**`voss/harness/audit/model.py`** [VERIFIED: live codebase]

Frozen dataclasses. All use `frozen=True, slots=True`. Zero board/EM/CLI imports.

- `AuditSnapshot` — top-level aggregate: `root_id`, `nodes`, `cards`, `kills`, `rescopes`, `routings`, `verdicts`, `liveness`, `leak6`, `run_final` (optional dict)
- `AuditNode` — per-node: `id`, `root_id`, `parent_run_id`, `envelope` (dict), `terminal_state`, `created_at`, `ended_at`, `transitions` (tuple of dicts), `cards`, `liveness_events`
- `AuditCard` — per card: `node_id`, `column`, `risk_tier`, `retry_count`, `is_killed`, `kill_record`, `is_rescoped`, `rescope_record`, `routing`, `verdicts`, `retry_notes`
- `KillRecord`, `RescopeRecord`, `RoutingRationale`, `ReviewerAssessment`, `LivenessEvent`, `Leak6Assessment` — normalized value objects

**`voss/harness/audit/load.py`** [VERIFIED: live codebase]

`load_audit_snapshot(root: Path) -> AuditSnapshot`

- Reads `<root>/.voss/sessions/<FIRST_dir_found>/*.json` (alphabetical by dir name)
- Extracts from transitions: `em.kill`, `em.rescope`, `em.routing`, `board.transition` (for verdicts and last-column), `em.run_final`, `audit.leak6`
- Sorts nodes deterministically by `id`
- Extracts `run_final` from root node transitions (NOT from `run-final.json` file)

**`voss/harness/audit/preflight.py`** — `run_o6_preflight()` verifies V2–V5 surfaces importable

**37 green tests** in `tests/harness/audit/` (fixtures, preflight, snapshot loader, read-only, determinism, no-board-imports invariant)

### What Is Missing (V9 must build)

| PRD §9 Section | Source | Gap in existing code |
|----------------|--------|---------------------|
| §1 Goal | `run-final.json` `idea` field | `load.py` looks for `em.run_final` in transitions; `run-final.json` is a SEPARATE file not read |
| §2 Active Team | `.voss/team.voss` via `compile_team` | Not read at all |
| §3 Principles | `.voss/principles.yml` via `load_principles` | Not read at all |
| §4 Scope and Budget | node `envelope` + `rejected_raises` | `AuditNode.envelope` is there; `rejected_raises` NOT surfaced in `AuditSnapshot` |
| §5 Board Timeline | node `transitions[]` board.transition entries | Partial — verdicts extracted; full board timeline sequence not exposed |
| §6 Work Cards | `AuditCard` | Present |
| §7 Agent Actions | `em.ticket` transitions (EM-authored claims) | Ticket content extracted indirectly; no dedicated `AgentAction` type |
| §8 Diff Summary | No diff storage in V2–V7 | Gap: no diff persisted; section renders "none" |
| §9 Tests and Evals | No test-result persistence in V2–V7 | Gap: no test results persisted; section renders "none" |
| §10 Reviewer-A Verification | `.review.json` sidecar `a_verification` | NOT read at all — `load.py` only reads node JSONs |
| §11 Reviewer-B Verdict | `.review.json` sidecar `b_verdict` | NOT read at all |
| §12 Blocked/Killed/Rescoped | `KillRecord`, `RescopeRecord` | Present via load.py |
| §13 Evidence References | `ReviewerAssessment.evidence_refs` | Present but only from transitions; sidecar evidence_refs not read |
| §14 Residual Risks | `Leak6Assessment` | Present; accepted-gap path documented |
| §15 Final Human Decision | `run-final.json` `sign_off` key | NOT read — run-final is a file, not a transition |

### Critical Structural Gap: `run-final.json` vs Node Transitions

`_persist_run_final()` in `cli.py:3979` writes a SEPARATE file:
`.voss/sessions/<root_id>/run-final.json`

This file is NOT a node JSON and is NOT picked up by `load_audit_snapshot()` which only globs `*.json`. Since `run-final.json` ends in `.json` it WILL be included in the glob — but it lacks the `id` field required by `_read_node_file`, which means it will raise `AuditLoadError`. [VERIFIED: live codebase — `_read_node_file` line 47: `if "id" not in data: raise AuditLoadError`]

**Landmine:** `load_audit_snapshot` will crash on any real `voss team run` directory because `run-final.json` has no `id` field.

Fix: `load_audit_snapshot` must skip `run-final.json` (by name) and read it separately.

### Critical Structural Gap: `load_audit_snapshot` has no `run_id` parameter

Current signature: `load_audit_snapshot(root: Path) -> AuditSnapshot`

This loads the FIRST directory alphabetically, not the most-recent or a named run. VAUD-01 requires `voss audit <run_id>` to render a specific run. The function must be extended to accept an optional `run_id: str | None` and implement latest-by-mtime fallback (matching `_latest_root_id` in cli.py).

### Critical Structural Gap: `.review.json` sidecars not read

VAUD-06 requires separate Reviewer-A and Reviewer-B sections. The sidecar format (shipped V6) is:
```json
{
  "a_verification": {"test_path_or_rubric": ..., "result": ..., "notes": ...},
  "b_verdict": {"conf": ..., "source": "B", "tier": ..., "verdict": ..., "notes": ..., "evidence_refs": [...], "domain_inferred": ...},
  "final_outcome": "Done" | "Blocked"
}
```

Files live at `.voss/sessions/<root_id>/<node_id>.review.json`. The existing `load.py` only reads `*.json` node files and currently does not filter out `.review.json` sidecars (they will fail the `id` check). Fix: filter sidecar files by name pattern before loading node JSONs.

---

## Source Map — Complete Audit Section → File/Field/Loader

| PRD §9 Section | Persisted File | Key/Field | Loader Action |
|----------------|----------------|-----------|---------------|
| §1 Goal | `run-final.json` | `idea` | Read file separately by name; skip in node glob |
| §2 Active Team | `.voss/team.voss` (if exists) | `compile_team` → `TeamConfig.roster_ids`, `ceiling` | Import `compile_team` from `voss.harness.team`; graceful fallback if absent |
| §3 Principles | `.voss/principles.yml` (optional) | `load_principles` → `PrinciplesConfig.principles` | Import `load_principles` from `voss.harness.principles`; fallback to `DEFAULT_PRINCIPLES` if absent |
| §4 Budget (per-node) | `<node_id>.json` | `envelope.limit`, `envelope.spent` | Already in `AuditNode.envelope` |
| §4 Scope denials | `<node_id>.json` | `rejected_raises[]` (list of `{attempted_delta, reason, attempted_at}`) | Read from node JSON; not currently surfaced in AuditSnapshot |
| §5 Board Timeline | `<node_id>.json` | `transitions[]` where `kind="board.transition"` | Sequence of all board moves across all cards, sorted by `at` field |
| §6 Work Cards | `<node_id>.json` | `AuditCard` | Already in load.py |
| §7 Agent Actions | `<node_id>.json` | transitions where `kind` in `{"em.ticket","em.routing","em.kill","em.rescope"}` | Already partially extracted; expose as tagged claim records |
| §8 Diff Summary | (none persisted in V2–V7) | — | Render "none — diff not persisted" |
| §9 Tests and Evals | (none persisted in V2–V7) | — | Render "none — test results not persisted" |
| §10 Reviewer-A | `<node_id>.review.json` | `a_verification` dict | Read sidecar files separately from node JSONs |
| §11 Reviewer-B | `<node_id>.review.json` | `b_verdict` dict | Same sidecar; separate section in AuditReport |
| §12 Killed/Rescoped/Blocked | node JSON `em.kill`/`em.rescope` transitions | `KillRecord`, `RescopeRecord` | Already in load.py |
| §13 Evidence References | `b_verdict.evidence_refs` + `ReviewerAssessment.evidence_refs` | tuple[str,...] | Present; needs unified evidence index |
| §14 Residual Risks | `audit.leak6` in root node transitions | `Leak6Assessment` | Already in load.py |
| §15 Final Human Decision | `run-final.json` | `sign_off` dict (`decision`, `ts`) | Read from `run-final.json`; NOT from node transitions |
| New: Sign-off ack | `<root_id>.signoff-ack.json` (new V9 sidecar) | `{ack_ts, killed_count, misroute_count}` | Written by V9 forcing function; read back by `voss audit` |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deterministic JSON serialization | Custom serializer | `json.dumps(data, sort_keys=True, indent=2)` | stdlib; consistent |
| Deep dict serialization of frozen dataclasses | Manual to-dict | `dataclasses.asdict(obj)` | stdlib; handles nested; consistent with `_persist_run_final` |
| Latest-run discovery | Custom glob logic | Reuse `_latest_root_id(sessions_dir)` already in `cli.py` | Already tested by V7 tests |
| CLI command pattern | New click infrastructure | Mirror `board_cmd` pattern exactly: `@click.command("audit")`, `@click.argument("run_id", required=False)`, `AGENT_COMMANDS` entry | V5/V6/V7 precedent |
| Team config loading | Re-implementing team parsing | `compile_team(team_decl)` from `voss.harness.team` | Frozen; audited runs were created with this config |
| Principles loading | Re-implementing YAML parse | `load_principles(cwd)` from `voss.harness.principles` | Frozen; returns `PrinciplesConfig` |

---

## Architecture Patterns

### System Architecture Diagram

```
voss audit <run_id>
        │
        ▼
   cli.py: audit_cmd
   (read-only, no live Board/Manager)
        │
        ├──► AuditLoader.load(cwd, run_id=None)
        │        ├── read .voss/sessions/<run_id>/*.json    (node JSONs, skip run-final.json + *.review.json)
        │        ├── read .voss/sessions/<run_id>/run-final.json   (separate read)
        │        ├── read .voss/sessions/<run_id>/*.review.json    (sidecar glob)
        │        ├── read .voss/team.voss → compile_team()    (team config)
        │        ├── read .voss/principles.yml → load_principles()   (principles)
        │        └── assemble AuditReport (extends AuditSnapshot)
        │
        ├──► CalibrationEngine.compute(sessions_dir)
        │        └── glob all *.review.json across all runs → false-pass + slop-rejection rates
        │
        ├──► render_markdown(report) → stdout / --output file
        ├──► render_json(report) → stdout / --output file
        │
        └──► (optional --signoff) ForcingFunction.gate_approve(report)
                 ├── display killed-card + misroute diff
                 ├── require explicit ack
                 └── write .voss/sessions/<run_id>/.signoff-ack.json
```

### Recommended Project Structure

The existing `voss/harness/audit/` package is the home for all new code:

```
voss/harness/audit/
├── __init__.py          # update exports
├── model.py             # EXISTING — extend AuditSnapshot or add AuditReport
├── load.py              # EXISTING — extend: run_id param, .review.json, run-final.json, principles/team
├── preflight.py         # EXISTING — unchanged
├── report.py            # NEW — AuditReport aggregate (V9-level; wraps AuditSnapshot + new sections)
├── render.py            # NEW — markdown_render(report) + json_render(report)
└── calibration.py       # NEW — CalibrationReport, compute_calibration(sessions_dir)

tests/harness/audit/
├── test_o6_fixtures.py       # EXISTING — keep; extend build_fixture_tree with review sidecars
├── test_preflight.py         # EXISTING — unchanged
├── test_snapshot_loader.py   # EXISTING — extend for run_id param + sidecar reading
├── test_audit_report.py      # NEW — AuditReport aggregate + all 15 PRD §9 sections
├── test_audit_render.py      # NEW — Markdown/JSON export round-trip, determinism
├── test_audit_cli.py         # NEW — `voss audit` CLI (CliRunner), unknown run exits non-zero
├── test_calibration.py       # NEW — false-pass / slop-rejection rate formula
└── test_signoff_forcing.py   # NEW — forcing function gate + ack sidecar
```

### Pattern 1: Read-Only CLI Command (established by `board_cmd`, `review_cmd`)

```python
# Source: voss/harness/cli.py (V5 board_cmd, V6 review_cmd pattern)
@click.command("audit")
@click.argument("run_id", required=False)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--format", "fmt", type=click.Choice(["text", "json", "markdown"]), default="text")
@click.option("--output", "output_path", default=None, type=click.Path())
def audit_cmd(run_id: str | None, cwd_str: str, fmt: str, output_path: str | None) -> None:
    """Show complete audit for a run (latest if no run_id). Read-only."""
    cwd = Path(cwd_str).resolve()
    sessions_dir = cwd / ".voss" / "sessions"
    if run_id is None:
        run_id = _latest_root_id(sessions_dir)
        if run_id is None:
            click.echo("(no runs found)", err=True)
            raise SystemExit(1)
    run_dir = sessions_dir / run_id
    if not run_dir.is_dir():
        click.echo(f"unknown run_id: {run_id}", err=True)
        raise SystemExit(1)
    # ...load report, render, emit
```

### Pattern 2: `run-final.json` Separate Read + Node JSON Filtering

```python
# Source: derived from _persist_run_final (cli.py:3979) and _read_node_file (load.py:35)
def _load_run_final(run_dir: Path) -> dict | None:
    path = run_dir / "run-final.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

# In load_audit_snapshot, filter node glob:
node_files = [
    p for p in sorted(run_dir.glob("*.json"))
    if p.name != "run-final.json" and not p.name.endswith(".review.json")
]
```

### Pattern 3: `.review.json` Sidecar Loading

```python
# Source: review_persistence.py + cli.py review_cmd
def _load_review_sidecars(run_dir: Path) -> dict[str, dict]:
    """Returns {node_id: sidecar_dict}."""
    result = {}
    for path in sorted(run_dir.glob("*.review.json")):
        node_id = path.name[: -len(".review.json")]
        try:
            data = json.loads(path.read_text())
            result[node_id] = data
        except (OSError, json.JSONDecodeError):
            result[node_id] = {}  # graceful — section renders "none"
    return result
```

### Pattern 4: Calibration Telemetry Derivation

Data source: `.review.json` sidecars across all `sessions/<run_id>/` directories.

```python
# Each sidecar has: a_verification.result ("pass"/"fail") + b_verdict.verdict ("pass"/"fail"/"block")
# False-pass: A says "pass" AND B says "fail" or "block"
# Slop-rejection: B says "block" (B's Residual-2 authority)

for sidecar in all_sidecars:
    a_result = sidecar.get("a_verification", {}).get("result", "")
    b_verdict = sidecar.get("b_verdict", {}).get("verdict", "")
    if a_result == "pass" and b_verdict in ("fail", "block"):
        false_pass_count += 1
    if b_verdict == "block":
        slop_rejection_count += 1
    total += 1
false_pass_rate = false_pass_count / total if total > 0 else 0.0
slop_rejection_rate = slop_rejection_count / total if total > 0 else 0.0
```

The spot-audit hook is a deterministic sampler: given a random seed (or the run_id as seed), select `min(k, total)` sidecars for human review. k=3 is a reasonable default.

### Pattern 5: Sign-Off Forcing Function (VAUD-SIGNOFF)

The V7 sign-off in `team_run_cmd` is a plain `click.prompt(Choice[approve,reject])` — NO gate. V9 must change this to:

1. Compute the "killed-card + misroute diff" from the in-memory `RunFinal` before the prompt:
   - killed_count > 0: show killed card summaries
   - misroute candidates: routing entries with `confidence_hint < 0.7` (threshold is Claude's discretion)
2. Display the diff
3. Require `click.prompt("Acknowledge killed/misroute risks? [yes]")` — only accepts "yes"
4. After ack: write `.voss/sessions/<root_id>/.signoff-ack.json`:
   ```json
   {"ack_ts": "...", "killed_count": N, "misroute_count": M}
   ```
5. Then display the approve/reject prompt

For `voss audit`, the forcing function reads back the `.signoff-ack.json` — if absent and killed_count > 0 or misroutes present, `--approve` is refused with a clear message.

**Key constraint:** The `.signoff-ack.json` is a NEW file (not modifying any existing node JSON, `run-final.json`, or `SessionTreeNode`). This satisfies "read-only audit" — the ack is a separate governance record alongside the audited data. [ASSUMED: `.signoff-ack.json` naming and exact schema — confirm with planner]

### Anti-Patterns to Avoid

- **Importing board/EM modules in `model.py` or `load.py`:** `test_snapshot_loader.py::TestNoLiveImports` enforces this with a source-text scan. Any import of `voss.harness.board`, `.em`, or `.cli` in these files will fail the test.
- **Modifying `RunRecord`/`SessionRecord`/`BudgetScope`:** Acceptance criterion 10 requires `git diff` to show zero field changes.
- **Modifying `SessionTreeNode` fields:** The audit package must be a read-only consumer; adding fields to the node schema violates the "no persistence schema changes" constraint.
- **Writing to the audited run directory (except the new `.signoff-ack.json`):** The ack sidecar is the ONLY new write. All other `audit_cmd` paths are read-only.
- **Using mtime as a sort key for determinism:** Node files must be sorted by `id` (alphabetically), not by mtime, to guarantee two loads of identical data produce identical output.
- **Encoding `run-final.json` as a node JSON:** It has no `id` field and will crash the existing `_read_node_file`. Must be read separately and filtered from the node glob.

---

## Integration Questions — Answers for Planner

### 1. Existing audit/ delta

The V9 delta on top of the existing package:

| Component | Existing | V9 Delta |
|-----------|----------|----------|
| `model.py` | `AuditSnapshot` + 7 sub-types | Add `AuditReport` (or extend) with principles, team, calibration sections |
| `load.py` | Loads first tree, transitions only | Add `run_id` param, skip `run-final.json`+`.review.json` from node glob, read them separately, read principles + team config |
| `preflight.py` | O1–O5 surface check | Unchanged |
| `report.py` | Does not exist | NEW: `AuditReport` with all 15 PRD §9 sections |
| `render.py` | Does not exist | NEW: `markdown_render`, `json_render` |
| `calibration.py` | Does not exist | NEW: `CalibrationReport`, `compute_calibration` |
| `cli.py` `audit_cmd` | Not registered | NEW: `audit_cmd` added to `AGENT_COMMANDS` |
| Sign-off forcing | Plain prompt, no gate | Extend `team_run_cmd` with ack step; add ack-check to `audit_cmd` |

### 2. Audit data model

Recommend a two-layer model:

- `AuditSnapshot` (existing) — low-level node/card/verdict data from session-tree JSONs
- `AuditReport` (new V9 type in `report.py`) — high-level PRD §9 sections:

```python
@dataclass(frozen=True, slots=True)
class AuditReport:
    run_id: str
    idea: str                          # from run-final.json
    principles: tuple[tuple[str,str], ...]  # from principles.yml
    team_config: dict                  # from team.voss (serializable form)
    snapshot: AuditSnapshot            # existing node/card data
    review_sidecars: dict[str, dict]   # {node_id: sidecar_dict}
    run_final: dict | None             # from run-final.json (full)
    signoff_ack: dict | None           # from .signoff-ack.json (new)
    calibration: "CalibrationReport"   # from calibration.py
    sections_missing: tuple[str, ...]  # sections with no data
```

Determinism: `AuditReport` is assembled from sorted/frozen inputs; `json_render` uses `sort_keys=True`.

### 3. Claims vs evidence (VAUD-03)

Mechanical distinction:

- **EM-authored claims:** transitions where `kind` in `{"em.ticket", "em.run_final", "em.routing"}` — these are what the EM said, not what was independently verified
- **Verified evidence:** `.review.json` sidecar `a_verification` (A ran or authored the test/rubric) + `b_verdict` (B assessed independently) + `evidence_refs` (explicit file/test references)

An EM claim is "unsupported" when: the node has an `em.ticket` transition AND the corresponding `.review.json` sidecar is either absent OR has both `a_verification: null` and `b_verdict: null`.

The render shows claims and evidence in distinct sections (§7 Agent Actions = claims; §10+§11 = evidence). Flagging uses a `[UNSUPPORTED CLAIM]` tag inline.

### 4. Markdown + JSON export (VAUD-08)

Markdown: section headers map 1:1 to PRD §9 sections; code blocks for JSON sub-data. Missing sections render as `_none_` explicitly. Output to stdout by default; `--output FILE` writes to disk.

JSON: `dataclasses.asdict(report)` is not directly applicable to `AuditReport` since it contains `AuditSnapshot` (which uses `tuple` for immutable fields). Use a recursive `_to_dict` helper that handles frozen dataclasses, tuples of dicts, and Nones. `json.dumps(data, sort_keys=True, indent=2)` for determinism.

Round-trip guarantee: all fields in `AuditReport` are primitives, dicts, or tuples of primitives/dicts. No custom types that cannot serialize to JSON.

### 5. Sign-off forcing function (VAUD-SIGNOFF)

**Where V7's approve/reject lives:** `cli.py:4114` — `click.prompt("Sign off on this run (approve/reject)", type=click.Choice(["approve", "reject"]))` with no gate.

**V9 change to `team_run_cmd`:**
1. After the run summary, compute killed count + misroute count from `rf`
2. If `killed_count > 0` or `misroute_count > 0`:
   - Display killed-card summaries + misroute items
   - Prompt: `click.prompt("Acknowledge risks above? Type 'yes' to continue")` — anything other than "yes" exits non-zero
   - Write `.signoff-ack.json`
3. Then display approve/reject prompt (unchanged)

**Reconciling "read-only audit" + "writes acknowledgement":** The ack sidecar is a GOVERNANCE record written by the operator, not a mutation of audited run data. The audited run data (`run-final.json`, node JSONs, `.review.json` sidecars) remains untouched. This is the same architectural pattern as `run-final.json` itself — a record of what the human decided, alongside but not part of the agent-produced data.

**In `audit_cmd`:** An `--approve` flag (or separate `voss audit approve <run_id>`) checks for `.signoff-ack.json` before permitting approval. If killed_count > 0 or misroutes present AND ack absent → error with helpful message.

### 6. Calibration telemetry (VAUD-CAL)

**Data location:** All `.review.json` sidecars across `sessions/<any_run_id>/` — not just the current run. Calibration is aggregate.

**Formula (from SPEC + O6-CONTEXT):**
```
false_pass_rate = |{cards: A=pass AND B in {fail,block}}| / |{cards with both A+B verdicts}|
slop_rejection_rate = |{cards: B=block}| / |{cards with B verdict}|
```

**Spot-audit hook:** A function `select_spot_audit(sessions_dir, k=3, seed=None)` that returns `k` sidecar paths selected pseudorandomly (deterministic given `seed`). The planner can wire this to a human-review prompt.

**Where the data is:** Each `.review.json` has `a_verification.result` ("pass"/"fail"/None) and `b_verdict.verdict` ("pass"/"fail"/"block"/None). Missing or null = not enough data, excluded from rate calculation.

### 7. Leak-6 (VAUD-10)

**`semantic.memory` write paths in V2–V7:**

Grep result: `voss/harness/memory_store.py` has `write_turn`, `write_ledger`, `write_decision`, `write_convention` — all write to `.voss/memory/` filesystem mirror AND optionally to ChromaDB (`chroma.add`). [VERIFIED: live codebase]

The O6-CONTEXT noted: "no standup-to-memory writer exists in O1-O5 substrate." This is confirmed — there is no automatic injection of EM-generated content into ChromaDB from the session-tree substrate. `memory_store` writes are triggered explicitly by the harness at specific call sites (turn writing, etc.), not automatically from EM/board transitions.

**Recommendation: documented accepted gap.** The threat scenario (EM-generated session summaries automatically poison semantic.memory, biasing future agent recall) does not have a write path in the shipped V2–V7 code. V9 should document this as an accepted gap with a clear statement: "No standup-to-memory writer exists in the V2–V7 substrate; Leak-6 is an accepted risk pending V10+ language-layer integration." The `Leak6Assessment` dataclass and the `audit.leak6` transition kind in fixtures are already designed for exactly this outcome. The existing test fixture (`_leak6_accepted_gap()`) covers this.

### 8. Frozen-schema guard

RunRecord, SessionRecord, BudgetScope, SessionTreeNode — V9 touches zero fields on these. The sign-off ack writes to a NEW `.signoff-ack.json` file in the run directory. The existing `test_session_redaction.py` guard (UNMODIFIED requirement) covers schema freeze.

### 9. Test invocation

```bash
.venv/bin/python -m pytest tests/harness/audit/ -x -v
.venv/bin/python -m pytest tests/harness/audit/ tests/harness/test_team_run_cli.py -v
```

Full suite (per project conventions with `.venv`):
```bash
.venv/bin/python -m pytest tests/harness/ -x
```

---

## Common Pitfalls

### Pitfall 1: `run-final.json` in node glob crashes `AuditLoadError`

**What goes wrong:** `load_audit_snapshot` globs `*.json` in the run dir. `run-final.json` (written by `_persist_run_final`) has no `id` field → `_read_node_file` raises `AuditLoadError("missing required 'id' field")`.

**Why it happens:** The existing loader was designed before `run-final.json` existed (O6-era code; V7 shipped run-final later).

**How to avoid:** Filter `run-final.json` and `*.review.json` explicitly from the node glob:
```python
node_files = [p for p in sorted(run_dir.glob("*.json"))
              if p.name != "run-final.json" and not p.name.endswith(".review.json")]
```

**Warning signs:** `AuditLoadError` mentioning "missing required 'id' field" on a path ending in `run-final.json`.

### Pitfall 2: `AuditSnapshot` model.py import guard in existing tests

**What goes wrong:** `test_snapshot_loader.py::TestNoLiveImports` scans the source of `model.py` and `load.py` for forbidden imports (`voss.harness.board`, `.em`, `.cli`). Adding `import voss.harness.principles` or `import voss.harness.team` to `load.py` will fail this guard.

**How to avoid:** Import principles and team config in `report.py` (the new aggregator), not in `load.py`. Keep `load.py` stdlib-only for node JSON parsing. Pass principles/team config into the loader as optional pre-loaded data, or assemble them in `report.py`.

**Warning signs:** `assert forbidden not in src` failure in `TestNoLiveImports`.

### Pitfall 3: `load_audit_snapshot` loads the first tree, not the latest

**What goes wrong:** `root_dirs = sorted(d for d in sessions_dir.iterdir() if d.is_dir())` then `tree_dir = root_dirs[0]`. This is alphabetical, not mtime-based. If there are multiple run directories, the loader may return the wrong one.

**How to avoid:** Extend the loader to accept `run_id: str | None`. When `None`, use mtime-based latest (matching `_latest_root_id` in `cli.py`). Expose both paths.

### Pitfall 4: `dataclasses.asdict` on frozen+slots dataclasses with tuple fields

**What goes wrong:** `dataclasses.asdict` works on frozen dataclasses but converts tuples to lists. If the JSON round-trip test asserts `isinstance(x.evidence_refs, tuple)`, re-hydrating from JSON will give a list.

**How to avoid:** JSON serialization → output. For round-trip guarantee, the JSON schema uses lists (not tuples). Hydration from JSON → AuditReport accepts lists and coerces to tuples. Document this: "JSON round-trip returns list where AuditReport uses tuple; both are ordered sequences."

### Pitfall 5: Sign-off forcing function must not crash if zero kills/misroutes

**What goes wrong:** The forcing function checks `rf.killed_count > 0 or misroute_count > 0`. If both are 0 (a clean run), the ack step must be skipped, not prompt and require "yes" for an empty diff.

**How to avoid:** Gate the entire ack step: `if rf.killed_count > 0 or _has_misroutes(rf): ...`. When neither, proceed directly to approve/reject prompt. Write the ack file with `killed_count=0, misroute_count=0` to signal a clean run — approve is not blocked.

### Pitfall 6: `accepted_gap` vs `warning` in Leak6Assessment default

**What goes wrong:** The existing `_extract_leak6` fallback (when no `audit.leak6` transition is found) returns `Leak6Assessment(status="warning", ...)`. But the Leak-6 accepted-gap decision means real runs should return `"accepted_gap"`. Test fixtures use `"accepted_gap"`.

**How to avoid:** The fallback `"warning"` is correct for runs without an explicit marker — it signals "assess Leak-6 status". Real V9 runs should add an `audit.leak6` transition with `status="accepted_gap"` to the root node at run time (or V9's `report.py` infers this from the absence of a write path). The planner must decide: inject the marker at `voss team run` time, or let the audit report synthesize it from the absence of a semantic.memory write path.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| O6 planned as primary audit | V9 supersedes O6 — re-plan fresh | 2026-06-05 | O6 plans = reference only; persistence contracts changed under V-track |
| `load_audit_snapshot` takes project root, loads first tree | Must be extended to take `run_id` | V9 | Non-breaking API extension |
| Sign-off: plain Choice prompt | Hard gate: ack-before-approve | V9 | `team_run_cmd` modification |
| No `voss audit` command | `audit_cmd` in `AGENT_COMMANDS` | V9 | New CLI surface |

**Deprecated/outdated:**
- O6-CONTEXT.md references "O1-O5 surfaces" — V-track renamed to V1–V7. `preflight.py` checks O1–O5 module paths which still resolve correctly under V-track names (the module paths did not change).
- `audit/__init__.py` docstring says "O6 audit product" — should be updated to V9 but this is cosmetic.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 (Python 3.13.12) |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/bin/python -m pytest tests/harness/audit/ -x -v` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAUD-01 | `voss audit` CLI exists, exits 0 for latest, non-zero for unknown run_id | CLI smoke | `.venv/bin/python -m pytest tests/harness/audit/test_audit_cli.py -x` | ❌ Wave 0 |
| VAUD-01 | Identical persisted data → identical audit output | determinism | `.venv/bin/python -m pytest tests/harness/audit/test_audit_render.py::test_determinism -x` | ❌ Wave 0 |
| VAUD-02 | All 15 PRD §9 sections present (missing → "none", no crash) | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py -x` | ❌ Wave 0 |
| VAUD-03 | EM claims tagged; unsupported claims flagged | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_claims_vs_evidence -x` | ❌ Wave 0 |
| VAUD-04 | Per-node budget (limit/spent) shown | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_budget_section -x` | ❌ Wave 0 |
| VAUD-05 | Scope denials (rejected_raises) shown with reasons | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_scope_denials -x` | ❌ Wave 0 |
| VAUD-06 | Reviewer-A and Reviewer-B in separate sections | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_reviewer_sections_separate -x` | ❌ Wave 0 |
| VAUD-07 | Kill/rescope lineage + routing rationale shown | unit | (existing `test_killed_card_present` covers kills; extend for lineage display) | Partial ✅ |
| VAUD-08 | Markdown export is valid; JSON round-trips | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_render.py -x` | ❌ Wave 0 |
| VAUD-10 | Residual-risk section present; Leak-6 documented | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_residual_risk -x` | ❌ Wave 0 |
| VAUD-SIGNOFF | Approve blocked until ack; ack is recorded | unit | `.venv/bin/python -m pytest tests/harness/audit/test_signoff_forcing.py -x` | ❌ Wave 0 |
| VAUD-CAL | Calibration report computes rates; spot-audit hook exists | unit | `.venv/bin/python -m pytest tests/harness/audit/test_calibration.py -x` | ❌ Wave 0 |
| All | No changes to RunRecord/SessionRecord/BudgetScope | regression | `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x` | ✅ |
| All | No board/EM imports in model.py/load.py | regression | (existing `TestNoLiveImports` — must extend for new modules) | ✅ |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/audit/ -x`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/ -x`
- **Phase gate:** `.venv/bin/python -m pytest tests/harness/ -x` green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/audit/test_audit_report.py` — covers VAUD-02/03/04/05/06/07/10
- [ ] `tests/harness/audit/test_audit_render.py` — covers VAUD-08 (Markdown + JSON, determinism, round-trip)
- [ ] `tests/harness/audit/test_audit_cli.py` — covers VAUD-01 (CLI, exit codes, latest-default)
- [ ] `tests/harness/audit/test_signoff_forcing.py` — covers VAUD-SIGNOFF
- [ ] `tests/harness/audit/test_calibration.py` — covers VAUD-CAL
- [ ] Extend `tests/harness/audit/test_o6_fixtures.py::build_fixture_tree` to add `.review.json` sidecars to the fixture tree (needed by all new tests)
- [ ] Extend `tests/harness/audit/test_snapshot_loader.py` — add tests for `run_id` parameter + `run-final.json` separate read + `.review.json` sidecar loading

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | Path-traversal guard on `run_id` (reject `..`, absolute paths; same as `cli_view.py` board precedent) |
| V5 Input Validation | yes | `run_id` validated as a directory name (no `/` or `..`); unknown run exits non-zero with stderr |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `run_id` arg | Spoofing/Tampering | Reject `run_id` containing `/` or `..` before any `sessions_dir / run_id` path join; mirror `cli_view.py` traversal guard at machine.py lines referenced in V5 |
| Reading from outside `.voss/sessions/` | Tampering | Validate that resolved path starts with `sessions_dir.resolve()` |
| `.signoff-ack.json` race (two audit processes writing simultaneously) | Tampering | Write atomically (write to tmp, rename); 0o600 permissions |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | all | ✓ | 3.13.12 | — |
| pytest | tests | ✓ | 8.4.2 | — |
| `.venv` | tests | ✓ | active | bare python3 lacks deps — always use `.venv/bin/python` |
| `voss.harness.audit` package | core | ✓ | shipped (37 tests green) | — |
| `voss.harness.principles` | principles section | ✓ | shipped V2 | — |
| `voss.harness.team` / `compile_team` | team section | ✓ | shipped V3 | — |
| `click` | CLI | ✓ | existing dep | — |
| `dataclasses` | serialization | ✓ | stdlib | — |

No new dependencies. All required surfaces are importable (confirmed by `run_o6_preflight()` passing).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `.signoff-ack.json` naming and exact schema fields | Sign-off forcing function pattern | Alternative name or schema shape; planner should confirm |
| A2 | Misroute threshold: `confidence_hint < 0.7` constitutes a misroute for forcing-function purposes | Sign-off forcing function | Threshold too strict/lenient; planner or operator should set explicitly |
| A3 | Calibration spot-audit default k=3 | Calibration telemetry | Different k preferred; expose as parameter |
| A4 | `audit_cmd` uses a standalone `--approve` flag or separate subcommand for the forcing-function gate in `voss audit` | Sign-off forcing function | Could be a separate `voss audit approve <run_id>` subcommand; planner should decide |

---

## Open Questions

1. **`AuditReport` vs extending `AuditSnapshot`**
   - What we know: `AuditSnapshot` is a frozen dataclass with 11 fields covering node/card/verdict data
   - What's unclear: Should V9 extend `AuditSnapshot` with new fields (breaking the existing test baseline) or introduce a new `AuditReport` wrapper that embeds `AuditSnapshot`?
   - Recommendation: Introduce `AuditReport` in a new `report.py` that wraps `AuditSnapshot` — avoids breaking the 37 existing tests and maintains the no-live-imports invariant in `model.py`

2. **`voss audit approve <run_id>` vs `voss audit <run_id> --approve`**
   - What we know: The forcing function needs a gated approve action reachable from `voss audit`
   - What's unclear: Whether this is a flag, a subgroup, or a separate interactive prompt within `audit_cmd`
   - Recommendation: Add an interactive forcing-function display to `audit_cmd` (read-only; shows the ack status). A separate `voss audit approve <run_id>` subcommand that writes the ack sidecar and then persists approval. This keeps `audit_cmd` truly read-only.

3. **Forcing function in `team_run_cmd` vs `audit_cmd`**
   - What we know: SPEC requires the gate in BOTH `voss team run` sign-off AND `voss audit`
   - What's unclear: Whether `team_run_cmd` must check for an existing ack before allowing approve, or writes it fresh every run
   - Recommendation: `team_run_cmd` writes the ack fresh (it has the live `rf` data). `voss audit approve` checks the ack; if absent and risks exist, refuses and instructs user to run `voss audit approve <run_id>` which displays and prompts.

4. **Principles and team config in `AuditReport` when `.voss/team.voss` absent**
   - What we know: `team_run_cmd` falls back to `_default_team_config()` when no `.voss/team.voss` exists
   - What's unclear: How to represent the default config in the audit (it is never persisted separately)
   - Recommendation: When `.voss/team.voss` is absent, read the `run-final.json` `idea` field and reconstruct a best-effort team summary from the node `role` fields; explicitly mark as "default roster (not persisted)"

5. **`audit.leak6` transition injection**
   - What we know: The existing fixture injects `_leak6_accepted_gap()` as a root-node transition; real `voss team run` does NOT inject this
   - What's unclear: Should V9 inject the `audit.leak6` transition at `team_run_cmd` time, or should `AuditReport` synthesize the accepted-gap from the absence of a write path?
   - Recommendation: V9's `report.py` synthesizes it: if no `audit.leak6` transition found in root node, and no standup-to-memory write path exists in the codebase, set `Leak6Assessment(status="accepted_gap", evidence="no standup-to-memory writer in V2–V7", mitigation_present=False)`. No injection at run time.

---

## Sources

### Primary (HIGH confidence)
- `voss/harness/audit/model.py` — complete dataclass inventory [VERIFIED: live codebase]
- `voss/harness/audit/load.py` — full loader logic, gaps identified [VERIFIED: live codebase]
- `voss/harness/audit/preflight.py` — surface check; all required surfaces pass [VERIFIED: live codebase]
- `voss/harness/cli.py:3979–4120` — `_persist_run_final`, `team_run_cmd`, `review_cmd`, `AGENT_COMMANDS` [VERIFIED: live codebase]
- `voss/harness/board/review_persistence.py` — `.review.json` sidecar schema [VERIFIED: live codebase]
- `voss/harness/session_tree.py` — `SessionTreeNode` fields, `rejected_raises`, `mutate_envelope` [VERIFIED: live codebase]
- `voss/harness/em/tickets.py` — `RunFinal`, `KillRecord`, `RescopeRecord`, `RoutingRationale`, `Ticket` [VERIFIED: live codebase]
- `tests/harness/audit/` — 37 passing tests [VERIFIED: `.venv/bin/python -m pytest tests/harness/audit/` → 37 passed]
- `.planning/docs/ORCHESTRATION_LAYERS.md §9` — PRD 15-section audit structure [VERIFIED: live codebase]
- `voss/harness/principles.py` — `load_principles`, `DEFAULT_PRINCIPLES` [VERIFIED: live codebase]

### Secondary (MEDIUM confidence)
- `.planning/phases/O6-audit-calibration-liveness/O6-CONTEXT.md` — calibration formula design, Leak-6 framing [CITED: planning docs]
- `voss/harness/memory_store.py` — confirms no standup→semantic.memory write path in V2–V7 [VERIFIED: live codebase grep]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages are existing stdlib/project code; no new deps
- Architecture: HIGH — pattern established by board_cmd/review_cmd; existing audit package confirmed live
- Pitfalls: HIGH — confirmed by reading actual load.py code (run-final.json crash, glob ordering, import guard)
- Sign-off forcing function: MEDIUM — V7 prompt location verified; ack sidecar schema is ASSUMED (A1)
- Calibration formula: MEDIUM — formula derived from O6-CONTEXT + sidecar schema; not yet implemented

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (stable stdlib/codebase; no external deps to drift)
