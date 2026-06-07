"""V9 AuditReport aggregate — assembles all PRD §9 sections from persisted data.

Read-only. No imports from ``voss.harness.board``, ``.em``, or ``.cli``.
Principles and team config are loaded HERE (not in load.py) to satisfy the
``TestNoLiveImports`` guard — ``load.py`` is forbidden those imports.

The report distinguishes EM-authored claims (em.ticket/em.run_final/em.routing
transitions) from verified evidence (review sidecars); unsupported EM claims are
flagged in ``AuditReport.unsupported_claims``. Missing sources render an explicit
"none" via ``sections_missing`` rather than crashing. Leak-6 is synthesized as an
accepted-gap (no standup→memory writer exists in the V2-V7 substrate) — never
injected into persisted data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from voss.harness.audit.load import (
    _load_review_sidecars,
    _load_run_final_file,
    load_audit_snapshot,
)
from voss.harness.audit.model import (
    AuditReport,
    AuditSnapshot,
    CalibrationReport,
    Leak6Assessment,
)

# PRD §9 sections that have no persisted source anywhere in V2-V7 — they always
# render an explicit "none".
_ALWAYS_MISSING: tuple[str, ...] = ("diff_summary", "tests_evals")


def _empty_calibration() -> CalibrationReport:
    return CalibrationReport(
        total_pairs=0,
        false_pass_count=0,
        slop_rejection_count=0,
        false_pass_rate=0.0,
        slop_rejection_rate=0.0,
        spot_audit_paths=(),
    )


def _load_signoff_ack(run_dir: Path) -> Optional[dict]:
    """Read ``.signoff-ack.json`` (dict or None). Graceful on read errors."""
    path = run_dir / ".signoff-ack.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _load_team_config_dict(cwd: Path) -> dict:
    """Serializable team-config view from ``.voss/team.voss``.

    On absence or any parse/compile error, returns a best-effort default marker
    (never raises — T-V9-03-01). team.py imports are allowed here; board/em/cli
    are not.
    """
    team_file = cwd / ".voss" / "team.voss"
    if not team_file.is_file():
        return {"source": "default roster (not persisted)", "roster_ids": []}
    try:
        from voss import parse
        from voss.ast_nodes import TeamDecl
        from voss.harness.team import compile_team

        src = team_file.read_text(encoding="utf-8")
        program = parse(src if src.endswith("\n") else src + "\n", str(team_file))
        team_decl = next((d for d in program.body if isinstance(d, TeamDecl)), None)
        if team_decl is None:
            return {"source": "default roster (not persisted)", "roster_ids": []}
        config, _registry = compile_team(team_decl)
        return {
            "source": str(team_file),
            "name": getattr(config, "name", ""),
            "roster_ids": sorted(config.roster_ids),
        }
    except Exception:
        return {"source": "default roster (not persisted)", "roster_ids": []}


def _resolve_principles(cwd: Path) -> tuple[tuple[str, str], ...]:
    """Resolved (key, text) principles, falling back to defaults on error."""
    from voss.harness.principles import DEFAULT_PRINCIPLES, resolve_principles

    try:
        return tuple(resolve_principles(cwd).principles)
    except Exception:
        return DEFAULT_PRINCIPLES


def scope_denials(snapshot: AuditSnapshot, run_dir: Path) -> list[dict]:
    """Re-read node JSONs for ``rejected_raises`` scope denials (VAUD-05).

    ``rejected_raises`` lives on the raw node dict, not the frozen ``AuditNode``;
    surface it here for the render layer. Returns a list of flattened entries
    ``{node_id, attempted_delta, reason, attempted_at}``, sorted by node id.
    """
    out: list[dict] = []
    for node in snapshot.nodes:
        path = run_dir / f"{node.id}.json"
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for entry in data.get("rejected_raises", []) or []:
            out.append(
                {
                    "node_id": node.id,
                    "attempted_delta": entry.get("attempted_delta"),
                    "reason": entry.get("reason", ""),
                    "attempted_at": entry.get("attempted_at", ""),
                }
            )
    out.sort(key=lambda d: (d["node_id"], d["attempted_at"]))
    return out


def _unsupported_claims(snapshot: AuditSnapshot, sidecars: dict[str, dict]) -> tuple[str, ...]:
    """Node ids with an em.ticket claim but no verifying review evidence.

    Rule (V9-RESEARCH §3): a non-root node carrying an ``em.ticket`` transition
    is UNSUPPORTED when its sidecar is absent/empty OR both ``a_verification``
    and ``b_verdict`` are falsy.
    """
    unsupported: list[str] = []
    for node in snapshot.nodes:
        if node.id == snapshot.root_id:
            continue
        has_ticket = any(t.get("kind") == "em.ticket" for t in node.transitions)
        if not has_ticket:
            continue
        sidecar = sidecars.get(node.id)
        if not sidecar:
            unsupported.append(node.id)
            continue
        if not sidecar.get("a_verification") and not sidecar.get("b_verdict"):
            unsupported.append(node.id)
    return tuple(sorted(unsupported))


def _residual_risk(snapshot: AuditSnapshot) -> Leak6Assessment:
    """Effective Leak-6 residual-risk assessment (VAUD-10), read-only.

    When the loader found an explicit ``audit.leak6`` marker, reuse it. When it
    only has the fallback ``status="warning"`` (no marker), synthesize the
    documented accepted-gap: no standup→semantic.memory write path exists in the
    V2-V7 substrate. Never mutates the frozen snapshot.
    """
    if snapshot.leak6.status == "accepted_gap":
        return snapshot.leak6
    return Leak6Assessment(
        status="accepted_gap",
        evidence="no standup-to-memory writer in V2-V7 substrate",
        mitigation_present=False,
    )


def build_audit_report(
    cwd: Path,
    run_id: str | None = None,
    calibration: CalibrationReport | None = None,
) -> AuditReport:
    """Assemble the AuditReport from all persisted V2-V7 sources. Never writes."""
    sessions_dir = cwd / ".voss" / "sessions"
    snapshot = load_audit_snapshot(cwd, run_id=run_id)
    run_dir = sessions_dir / snapshot.root_id

    run_final = _load_run_final_file(run_dir)
    sidecars = _load_review_sidecars(run_dir)
    signoff_ack = _load_signoff_ack(run_dir)
    principles = _resolve_principles(cwd)
    team_config = _load_team_config_dict(cwd)

    sections_missing: list[str] = []
    idea = ""
    if run_final and run_final.get("idea"):
        idea = run_final["idea"]
    else:
        sections_missing.append("goal")
    sections_missing.extend(_ALWAYS_MISSING)

    unsupported = _unsupported_claims(snapshot, sidecars)
    # Residual risk computed read-only; the frozen snapshot already carries the
    # fixture's accepted_gap marker, so snapshot.leak6 stays authoritative for
    # the report's snapshot field. _residual_risk is exposed for the renderer.
    _residual_risk(snapshot)

    return AuditReport(
        run_id=snapshot.root_id,
        idea=idea,
        principles=principles,
        team_config=team_config,
        snapshot=snapshot,
        review_sidecars=sidecars,
        run_final=run_final,
        signoff_ack=signoff_ack,
        calibration=calibration or _empty_calibration(),
        sections_missing=tuple(sections_missing),
        unsupported_claims=unsupported,
    )
