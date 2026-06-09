"""V9 audit renderers — deterministic text / Markdown / JSON exporters (VAUD-08).

Pure functions: no ``datetime.now()``, no ``random``, no mtime-derived values.
Identical persisted data always renders byte-identical output. JSON uses
``sort_keys=True``. Collections are sorted by a stable key before emission.

Note: ``render_json`` round-trips tuples as JSON lists — ``dataclasses.asdict``
coerces every tuple to a list. Round-trip consumers see ordered lists, not
tuples; both are ordered sequences.

Stdlib only. The single project import is the audit model (no board/em/cli).
"""
from __future__ import annotations

import dataclasses
import json

from voss.harness.audit.model import AuditReport
from voss.template_render import render_package_template

# PRD §9 audit sections, in fixed order (ORCHESTRATION_LAYERS.md §9).
_SECTIONS: tuple[tuple[int, str], ...] = (
    (1, "Goal"),
    (2, "Active Team"),
    (3, "Principles"),
    (4, "Scope and Budget"),
    (5, "Board Timeline"),
    (6, "Work Cards"),
    (7, "Agent Actions"),
    (8, "Diff Summary"),
    (9, "Tests and Evals"),
    (10, "Reviewer-A Verification"),
    (11, "Reviewer-B Verdict"),
    (12, "Blocked/Killed/Rescoped Items"),
    (13, "Evidence References"),
    (14, "Residual Risks"),
    (15, "Final Human Decision"),
)

# Section number -> the sections_missing key the report uses for it.
_MISSING_KEY = {1: "goal", 8: "diff_summary", 9: "tests_evals"}

_NONE = "_none_"


def _to_dict(obj):
    """Recursively convert dataclasses/tuples to JSON-friendly dict/list."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def render_json(report: AuditReport) -> str:
    """Deterministic JSON export (sort_keys). Same data -> same bytes."""
    return json.dumps(_to_dict(report), sort_keys=True, indent=2)


# ---------------------------------------------------------------------------
# Section body builders (deterministic, stable-sorted)
# ---------------------------------------------------------------------------


def _principles_body(report: AuditReport) -> list[str]:
    return [f"- {k}: {text}" for k, text in report.principles]


def _team_body(report: AuditReport) -> list[str]:
    tc = report.team_config or {}
    roster = ", ".join(sorted(tc.get("roster_ids", []))) or _NONE
    return [f"source: {tc.get('source', _NONE)}", f"roster: {roster}"]


def _budget_body(report: AuditReport) -> list[str]:
    lines: list[str] = []
    for node in sorted(report.snapshot.nodes, key=lambda n: n.id):
        env = node.envelope or {}
        lines.append(f"- {node.id}: spent {env.get('spent', 0)}/{env.get('limit', 0)}")
    return lines or [_NONE]


def _cards_body(report: AuditReport) -> list[str]:
    unsupported = set(report.unsupported_claims)
    lines: list[str] = []
    for card in sorted(report.snapshot.cards, key=lambda c: c.node_id):
        tag = "  [UNSUPPORTED CLAIM]" if card.node_id in unsupported else ""
        lines.append(f"- {card.node_id} [{card.column}]{tag}")
    return lines or [_NONE]


def _board_timeline_body(report: AuditReport) -> list[str]:
    lines: list[str] = []
    for node in sorted(report.snapshot.nodes, key=lambda n: n.id):
        for t in node.transitions:
            if t.get("kind") == "board.transition":
                lines.append(
                    f"- {node.id}: {t.get('from')} -> {t.get('to')} ({t.get('outcome')})"
                )
    return lines or [_NONE]


def _agent_actions_body(report: AuditReport) -> list[str]:
    lines: list[str] = []
    for node in sorted(report.snapshot.nodes, key=lambda n: n.id):
        kinds = [t.get("kind", "?") for t in node.transitions]
        if kinds:
            lines.append(f"- {node.id}: {', '.join(kinds)}")
    return lines or [_NONE]


def _reviewer_body(report: AuditReport, key: str) -> list[str]:
    lines: list[str] = []
    for node_id in sorted(report.review_sidecars):
        entry = (report.review_sidecars[node_id] or {}).get(key)
        if not entry:
            continue
        if key == "a_verification":
            lines.append(
                f"- {node_id}: result={entry.get('result', '?')} "
                f"({entry.get('test_path_or_rubric') or 'no rubric'})"
            )
        else:
            lines.append(
                f"- {node_id}: verdict={entry.get('verdict', '?')} "
                f"conf={entry.get('conf', '?')} tier={entry.get('tier', '?')}"
            )
    return lines or [_NONE]


def _bkr_body(report: AuditReport) -> list[str]:
    snap = report.snapshot
    lines: list[str] = []
    for k in sorted(snap.kills, key=lambda r: r.killed_node_id):
        lines.append(f"- killed: {k.killed_node_id} ({k.rationale_text})")
    for r in sorted(snap.rescopes, key=lambda r: r.predecessor_card_id):
        lines.append(f"- rescoped: {r.predecessor_card_id} -> {r.successor_card_id}")
    return lines or [_NONE]


def _evidence_body(report: AuditReport) -> list[str]:
    refs: set[str] = set()
    for v in report.snapshot.verdicts:
        refs.update(v.evidence_refs)
    return [f"- {r}" for r in sorted(refs)] or [_NONE]


def _residual_body(report: AuditReport) -> list[str]:
    leak6 = report.snapshot.leak6
    return [f"Leak-6: {leak6.status} — {leak6.evidence}"]


def _decision_body(report: AuditReport) -> list[str]:
    if report.signoff_ack:
        ack = report.signoff_ack
        return [
            f"acknowledged: killed={ack.get('killed_count', 0)} "
            f"misroute={ack.get('misroute_count', 0)}"
        ]
    sign_off = (report.run_final or {}).get("sign_off")
    if sign_off:
        return [f"decision: {sign_off.get('decision', '?')}"]
    return [_NONE]


def _section_body(report: AuditReport, num: int) -> list[str]:
    # Explicitly-missing sections render _none_.
    missing_key = _MISSING_KEY.get(num)
    if missing_key and missing_key in report.sections_missing:
        return [_NONE]
    builders = {
        1: lambda: [report.idea] if report.idea else [_NONE],
        2: lambda: _team_body(report),
        3: lambda: _principles_body(report),
        4: lambda: _budget_body(report),
        5: lambda: _board_timeline_body(report),
        6: lambda: _cards_body(report),
        7: lambda: _agent_actions_body(report),
        10: lambda: _reviewer_body(report, "a_verification"),
        11: lambda: _reviewer_body(report, "b_verdict"),
        12: lambda: _bkr_body(report),
        13: lambda: _evidence_body(report),
        14: lambda: _residual_body(report),
        15: lambda: _decision_body(report),
    }
    builder = builders.get(num)
    return builder() if builder else [_NONE]


def render_markdown(report: AuditReport) -> str:
    """Markdown export: one ``## §N <Section>`` header per PRD §9 section."""
    sections = [
        {"num": num, "name": name, "body": _section_body(report, num)}
        for num, name in _SECTIONS
    ]
    return render_package_template(
        "voss",
        "templates/audit/markdown.md.jinja",
        {"run_id": report.run_id, "sections": sections},
    )


def render_text(report: AuditReport) -> str:
    """Compact plain-text export (default --format text)."""
    lines: list[str] = [f"Audit: {report.run_id}"]
    for num, name in _SECTIONS:
        lines.append(f"[{num}] {name}")
        for body in _section_body(report, num):
            lines.append(f"    {body}")
    return "\n".join(lines)
