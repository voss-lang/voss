"""Read recorded acceptance evidence for an explicitly linked worker attempt."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..decision_review import candidate_review_path, parse_criteria
from .task_graph import now

Outcome = Literal['passed', 'failed', 'skipped', 'not_run', 'unavailable', 'stale']


class Check(BaseModel):
    name: str
    status: Outcome


class Criterion(BaseModel):
    id: str
    text: str


class Link(BaseModel):
    v: Literal[1]
    swarm_id: str
    task_id: str
    attempt_id: str
    candidate_revision: str
    criteria: list[Criterion]
    criteria_source: str
    checks: list[Check]


class Evidence(BaseModel):
    id: str
    label: str
    reference: str
    summary: str


class Row(BaseModel):
    id: str
    text: str
    test_outcome: Outcome = 'unavailable'
    test_scope: str = 'task'
    reviewer_outcome: Literal['supported', 'contradicted', 'insufficient_evidence', 'abstained', 'no_answer', 'unavailable', 'stale'] = 'unavailable'
    reviewer_mode: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


class Bundle(BaseModel):
    v: Literal[1] = 1
    status: Literal['available', 'partial', 'unavailable', 'stale'] = 'unavailable'
    message: str | None = None
    session_id: str
    run_id: str | None = None
    task_id: str
    attempt_id: str
    plan_id: str | None = None
    plan_revision: str | None = None
    candidate_revision: str | None = None
    base_revision: str | None = None
    worktree: str | None = None
    branch: str | None = None
    current_head: str | None = None
    clean: bool = False
    evidence_revision: str = ''
    checked_at: str = Field(default_factory=now)
    criteria_source: str = 'plan'
    rows: list[Row] = Field(default_factory=list)
    checks: list[Check] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(snapshot, node_id: str, attempt_id: str) -> Bundle:
    bundle = Bundle(session_id=snapshot.session_id, task_id=node_id, attempt_id=attempt_id)
    graph = snapshot.graph
    node = next((node for node in graph.nodes if node.id == node_id), None) if graph else None
    attempt = next((a for a in node.attempts if a.id == attempt_id), None) if node else None
    if attempt is None:
        bundle.message = 'No recorded worker attempt matches this selection.'
        return bundle
    bundle.run_id, bundle.plan_id, bundle.plan_revision = attempt.run_id, graph.plan_id, attempt.plan_revision
    bundle.candidate_revision, bundle.base_revision = attempt.candidate_revision, attempt.base_revision
    bundle.worktree, bundle.branch = attempt.worktree, attempt.branch
    bundle.rows = [Row(id=c.id, text=c.text) for c in parse_criteria(node.criteria)]
    bundle.unresolved = list(attempt.blockers)
    bundle.status = 'partial'
    raw_revision = 'missing'
    try:
        if graph.source != 'swarm' or not attempt.repository:
            bundle.message = 'No board/reviewer artifact is linked to this managed attempt.'
        else:
            root = Path(attempt.repository).resolve()
            path = candidate_review_path(root, graph.plan_id, node.id)
            if not path.resolve().is_relative_to(root) or path.stat().st_size > 1024 * 1024:
                raise ValueError('artifact path or size')
            with path.open('rb') as source:
                raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError('artifact size')
            raw_revision = hashlib.sha256(raw).hexdigest()
            payload = json.loads(raw)
            link = Link.model_validate(payload.get('task_review'))
            if (link.swarm_id, link.task_id, link.attempt_id) != (graph.plan_id, node.id, attempt.id):
                raise ValueError('artifact ownership')
            if not link.criteria or len({c.id for c in link.criteria}) != len(link.criteria):
                raise ValueError('criterion identity')
            bundle.criteria_source = link.criteria_source
            bundle.rows = [Row(id=c.id, text=c.text) for c in link.criteria]
            bundle.checks = link.checks
            expected = [Criterion(id=c.id, text=c.text) for c in parse_criteria(node.goal)]
            stale = link.candidate_revision != attempt.candidate_revision or attempt.plan_revision != graph.revision or link.criteria != expected
            bundle.status = 'stale' if stale else 'available'
            tests = [c.status for c in link.checks if c.name == 'tests']
            test_result = next((status for status in ('failed', 'stale', 'unavailable', 'not_run', 'skipped', 'passed') if status in tests), 'not_run')
            receipts = payload.get('receipts', [])
            if not isinstance(receipts, list):
                raise ValueError('receipt format')
            for row_index, row in enumerate(bundle.rows):
                row.test_outcome = 'stale' if stale else test_result
                matches = [(index, receipt) for index, receipt in enumerate(receipts)
                           if receipt.get('purpose') == 'review.requirements'
                           and row.id in (receipt.get('detail') or {}).get('criterion_ids', [])]
                if matches:
                    index, receipt = matches[-1]
                    detail = receipt.get('detail') or {}
                    recorded = (detail.get('candidate') or {}).get('head')
                    outcome = (detail.get('labels') or {}).get(row.id, 'unavailable') if receipt.get('status') == 'answered' else 'unavailable'
                    row = Row.model_validate({**row.model_dump(), 'reviewer_outcome': outcome, 'reviewer_mode': receipt.get('mode')})
                    bundle.rows[row_index] = row
                    if recorded != attempt.candidate_revision:
                        stale = True
                    row.evidence.append(Evidence(id=f'receipt-{index}-{row.id}', label='Requirement assessment', reference=str(path.relative_to(root)),
                        summary=f"{row.id}: {outcome}; mode: {row.reviewer_mode}; recorded status: {receipt.get('status')}; {receipt.get('fallback_reason') or ''}"))
                if row.reviewer_outcome != 'supported':
                    row.unresolved.append(f'Reviewer: {row.reviewer_outcome}')
                if row.test_outcome != 'passed':
                    row.unresolved.append(f'Task tests: {row.test_outcome}')
            bundle.unresolved.extend(f'{check.name}: {check.status}' for check in link.checks if check.status != 'passed')
            if stale:
                bundle.status = 'stale'
                bundle.message = 'Candidate or acceptance criteria changed. Review the new revision.'
    except FileNotFoundError:
        bundle.message = 'No review artifact has been recorded for this attempt.'
    except (OSError, ValueError, TypeError, AttributeError):
        bundle.status = 'partial'
        bundle.message = 'Review artifact is unavailable, malformed or lacks exact attempt linkage.'
        bundle.checks = []
        bundle.criteria_source = 'plan'
        bundle.unresolved = list(attempt.blockers)
        bundle.rows = [Row(id=c.id, text=c.text) for c in parse_criteria(node.criteria)]
    if attempt.worktree:
        try:
            def git(*args):
                return subprocess.check_output(['git', '--no-optional-locks', '-C', attempt.worktree, *args], stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            bundle.current_head = git('rev-parse', 'HEAD')
            bundle.clean = not git('status', '--porcelain', '--untracked-files=normal')
            git('cat-file', '-e', f'{attempt.base_revision}^{{commit}}')
        except (OSError, subprocess.SubprocessError):
            bundle.message = 'Candidate worktree or recorded base is unavailable.'
            bundle.status = 'unavailable'
    if not attempt.candidate_revision or not attempt.base_revision or not attempt.worktree:
        bundle.status = 'unavailable'
        bundle.message = bundle.message or 'No committed candidate and base are recorded for this attempt.'
    elif bundle.status != 'unavailable' and (bundle.current_head != attempt.candidate_revision or not bundle.clean):
        bundle.status = 'stale'
        bundle.message = 'Candidate worktree changed. New candidate evidence and approval are required.'
    if bundle.status == 'stale':
        for row in bundle.rows:
            row.test_outcome = 'stale' if row.test_outcome != 'unavailable' else 'unavailable'
            row.reviewer_outcome = 'stale' if row.evidence else 'unavailable'
    bundle.evidence_revision = digest({'bundle': bundle.model_dump(exclude={'checked_at', 'evidence_revision'}), 'artifact': raw_revision})
    return bundle
