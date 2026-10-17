from __future__ import annotations

import asyncio
from collections.abc import Sequence
import concurrent.futures
import dataclasses
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from typing import Literal
import uuid

from voss.harness import config, judgments
from voss.harness.board.reviewer_b import build_repo_context
from voss.harness.code.rerank import TIMEOUT_MESSAGES, request_size
from voss_runtime.judgments import (
    KILLED_MESSAGE, MISSING_KEY_MESSAGE, SAFE_ID, ChoiceQuestion, JudgmentError, JudgmentLedger, JudgmentReceipt,
    is_killed,
)

PURPOSE = "review.requirements"
RUBRIC_VERSION = "review.requirements.v2"
THRESHOLD = 0.80
OPTIONS = {
    "supported": "The requirement is specific enough to check, and the diff, code, or recorded checks show it is met.",
    "contradicted": "The diff, code, or recorded checks show this requirement is not met.",
    "insufficient_evidence": (
        "The requirement is too vague to check, or the diff, code, and recorded checks do not show either way."
    ),
}
HEADING = "Requirement assessments (advisory)"
STALE_TEXT = "stale: work changed since this was checked"
CHECK_STATUSES = ("passed", "failed", "skipped", "not_run", "stale")
NO_CHECKS = "no checks recorded"
VERIFICATION_NOTE_CHARS = 2000
CHECK_NAME_CHARS = 100

_MARKER_RE = re.compile(r"^(?:[-*+•]|\d+[.)])\s+")
_EXPLICIT_ID_RE = re.compile(r"(?P<id>[A-Z]{1,6}-?\d+(?:\.\d+)*)(?:\s*[:)]|\.|\s+[-–])\s+(?P<text>\S.*)")
_TOUCHED_RE = re.compile(r"^(?:\+\+\+ b|--- a)/(.+)$", re.MULTILINE)
_EXCLUDE_VOSS = ("--", ".", ":(exclude).voss")


@dataclasses.dataclass(frozen=True)
class Criterion:
    id: str
    text: str


def parse_criteria(source: str | Sequence[str]) -> tuple[Criterion, ...]:
    items = source.splitlines() if isinstance(source, str) else list(source)
    used: set[str] = set()
    out: list[Criterion] = []
    for raw in items:
        line = raw.strip()
        if not line:
            continue
        body = _MARKER_RE.sub("", line, count=1)
        match = _EXPLICIT_ID_RE.fullmatch(body)
        cid, text = (match["id"], match["text"].strip()) if match and SAFE_ID.fullmatch(match["id"]) else (None, body)
        if cid is None or cid in used:
            n = len(out) + 1
            while f"AC-{n}" in used:
                n += 1
            cid = f"AC-{n}"
        used.add(cid)
        out.append(Criterion(cid, text))
    return tuple(out)


@dataclasses.dataclass(frozen=True)
class CheckResult:
    name: str
    status: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or len(self.name) > CHECK_NAME_CHARS:
            raise ValueError(f"check name must be 1-{CHECK_NAME_CHARS} characters")
        if self.status not in CHECK_STATUSES:
            raise ValueError(f"unknown check status: {self.status!r}")


def checks_from_artifact(artifact: object | None) -> tuple[CheckResult, ...]:
    if artifact is None:
        return ()
    tests = getattr(artifact, "tests_passed", None)
    checks = [CheckResult("tests", "passed" if tests is True else "failed" if tests is False else "not_run")]
    if hasattr(artifact, "scope_violations"):
        checks.append(CheckResult("scope", "failed" if artifact.scope_violations else "passed"))
    return tuple(checks)


def load_checks(data: object) -> tuple[CheckResult, ...]:
    if not isinstance(data, list):
        raise ValueError("checks must be a JSON list")
    out = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each check must be an object")
        if "status" in item:
            out.append(CheckResult(item.get("name"), item["status"]))
        elif isinstance(item.get("pass"), bool):
            out.append(CheckResult(item.get("type"), "passed" if item["pass"] else "failed"))
        else:
            raise ValueError("each check needs a status or a boolean pass")
    return tuple(out)


def _safe_path(p: str) -> bool:
    pure = PurePosixPath(p)
    return bool(p) and not pure.is_absolute() and ".." not in pure.parts


def touched_paths(diff: str) -> tuple[str, ...]:
    return tuple(sorted({p for p in _TOUCHED_RE.findall(diff) if _safe_path(p)}))


def tree_digest(root: Path, paths: Sequence[str]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        try:
            content = hashlib.sha256((Path(root) / p).read_bytes()).hexdigest()
        except OSError:
            content = "<absent>"
        h.update(f"{p}\0{content}\n".encode())
    return h.hexdigest()[:16]


def candidate_from_diff(root: Path, diff: str) -> dict:
    paths = touched_paths(diff)
    return {"kind": "working_tree", "touched_paths": list(paths), "tree_digest": tree_digest(root, paths)}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def collect_working_tree(repo: Path) -> tuple[str, dict]:
    tracked = _git(repo, "diff", "HEAD", *_EXCLUDE_VOSS)
    if tracked.returncode != 0:
        raise ValueError(f"git diff HEAD failed: {tracked.stderr.strip()}")
    parts = [tracked.stdout]
    others = _git(repo, "ls-files", "--others", "--exclude-standard", "-z", *_EXCLUDE_VOSS)
    for path in filter(None, others.stdout.split("\0")):
        rendered = _git(repo, "diff", "--no-index", "--", "/dev/null", path)
        if rendered.returncode in (0, 1):
            parts.append(rendered.stdout)
    diff = "".join(parts)
    return diff, candidate_from_diff(repo, diff)


def collect_commit(repo: Path, ref: str) -> tuple[str, str, dict]:
    if not ref or ref.startswith("-"):
        raise ValueError(f"invalid ref: {ref!r}")
    resolved = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ValueError(f"unknown commit: {ref!r}")
    sha = resolved.stdout.strip()
    merge_base = _git(repo, "merge-base", sha, "HEAD")
    base = merge_base.stdout.strip()
    if merge_base.returncode != 0 or base == sha:
        base = f"{sha}^"
    result = _git(repo, "diff", base, sha, *_EXCLUDE_VOSS)
    if result.returncode != 0:
        raise ValueError(f"git diff {base} {sha} failed: {result.stderr.strip()}")
    diff = result.stdout
    paths = touched_paths(diff)
    with tempfile.TemporaryDirectory() as tmp:
        for p in paths:
            shown = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{p}"], capture_output=True)
            if shown.returncode != 0:
                continue
            target = Path(tmp) / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(shown.stdout)
        code = build_repo_context(Path(tmp), diff)
    return diff, code, {"kind": "commit", "head": sha, "touched_paths": list(paths)}


@dataclasses.dataclass(frozen=True)
class EvidencePacket:
    criteria: tuple[Criterion, ...]
    diff: str
    code: str
    checks: tuple[CheckResult, ...]
    candidate: dict
    verification_note: str
    packet_id: str


def build_packet(
    criteria: str | Sequence[str] | tuple[Criterion, ...],
    *,
    diff: str,
    code: str,
    checks: Sequence[CheckResult],
    candidate: dict,
    verification_note: str = "",
) -> EvidencePacket:
    if isinstance(criteria, str) or not all(isinstance(c, Criterion) for c in criteria):
        criteria = parse_criteria(criteria)
    criteria = tuple(criteria)
    checks = tuple(checks)
    canonical = json.dumps(
        {
            "criteria": [[c.id, c.text] for c in criteria],
            "diff": diff,
            "checks": [[c.name, c.status] for c in checks],
            "candidate": candidate.get("head") or candidate.get("tree_digest"),
        },
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    packet_id = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    return EvidencePacket(criteria, diff, code, checks, candidate, verification_note[:VERIFICATION_NOTE_CHARS], packet_id)


def is_stale(root: Path, detail: dict) -> bool:
    candidate = detail.get("candidate") if isinstance(detail, dict) else None
    if not isinstance(candidate, dict) or candidate.get("kind") != "working_tree":
        return False
    paths = candidate.get("touched_paths")
    digest = candidate.get("tree_digest")
    if not isinstance(paths, list) or not all(isinstance(p, str) and _safe_path(p) for p in paths) or not isinstance(digest, str):
        return True
    return tree_digest(root, paths) != digest


def state_for(packet: EvidencePacket, *, code_limit: int | None = None, diff_limit: int | None = None) -> dict:
    state: dict = {
        "criteria": [{"id": c.id, "text": c.text} for c in packet.criteria],
        "checks": [{"name": c.name, "status": c.status} for c in packet.checks] or NO_CHECKS,
    }
    if packet.verification_note:
        state["verification_note"] = packet.verification_note
    state["diff"] = packet.diff[:diff_limit]
    state["code"] = packet.code[:code_limit]
    return state


def questions_for(criteria: Sequence[Criterion]) -> dict[str, ChoiceQuestion]:
    return {
        c.id: ChoiceQuestion(
            f"Requirement {c.id}: {c.text!r}. Does the evidence in state.diff, state.code, and state.checks "
            f"show that this one requirement is met? Judge only requirement {c.id}.",
            dict(OPTIONS),
        )
        for c in criteria
    }


def _largest(fits, hi: int) -> int:
    lo = 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def build_request(packet: EvidencePacket, *, model: str, max_bytes: int) -> tuple[dict, dict, dict] | None:
    questions = questions_for(packet.criteria)

    def fits(code_limit: int | None, diff_limit: int | None) -> bool:
        state = state_for(packet, code_limit=code_limit, diff_limit=diff_limit)
        return request_size(model, state, questions) <= max_bytes

    if fits(None, None):
        return state_for(packet), questions, {"code": False, "diff": False}
    if fits(0, None):
        code_limit = _largest(lambda n: fits(n, None), len(packet.code))
        return state_for(packet, code_limit=code_limit), questions, {"code": True, "diff": False}
    if fits(0, 0):
        diff_limit = _largest(lambda n: fits(0, n), len(packet.diff))
        return state_for(packet, code_limit=0, diff_limit=diff_limit), questions, {"code": bool(packet.code), "diff": True}
    return None


def label_for(answer, threshold: float) -> str:
    assert 0.5 < threshold <= 1
    probabilities = answer.probabilities
    if probabilities.get("supported", 0.0) >= threshold:
        return "supported"
    if probabilities.get("contradicted", 0.0) >= threshold:
        return "contradicted"
    return "abstained"


def _finish(
    ledger: JudgmentLedger, call_id: str, packet: EvidencePacket, *, mode: str, reason: str | None,
    status: str = "unavailable", labels: dict | None = None, trimmed: dict | None = None, request_bytes: int = 0,
    threshold: float = THRESHOLD,
) -> JudgmentReceipt:
    detail = {
        "packet_id": packet.packet_id,
        "criterion_ids": [c.id for c in packet.criteria],
        "labels": labels or {},
        "threshold": threshold,
        "trimmed": trimmed or {"code": False, "diff": False},
        "request_bytes": request_bytes,
        "candidate": dict(packet.candidate),
        "checks": {s: sum(c.status == s for c in packet.checks) for s in CHECK_STATUSES},
    }
    for n, receipt in enumerate(ledger.receipts):
        if receipt.call_id == call_id:
            ledger.receipts[n] = dataclasses.replace(receipt, mode=mode, fallback_reason=reason, detail=detail)
            return ledger.receipts[n]
    receipt = JudgmentReceipt(
        call_id, PURPOSE, RUBRIC_VERSION, config.get_judgments_config()["model"], None, mode, status, reason,
        0, None, None, None, 0.0, 0.0, {}, packet.packet_id, detail=detail,
    )
    ledger.receipts.append(receipt)
    return receipt


async def assess(
    packet: EvidencePacket, *, mode: Literal["explicit", "shadow"], ledger: JudgmentLedger,
    call_id: str | None = None, threshold: float = THRESHOLD,
) -> JudgmentReceipt:
    call_id = uuid.uuid4().hex if call_id is None else call_id

    def fallback(reason: str, status: str = "unavailable", error: Exception | None = None, **sizes) -> JudgmentReceipt:
        receipt = _finish(ledger, call_id, packet, mode=mode, reason=reason, status=status, threshold=threshold, **sizes)
        if mode == "explicit" and error is not None:
            raise error
        return receipt

    if not packet.criteria:
        return fallback("no_criteria", error=ValueError("no acceptance criteria to assess"))
    if is_killed():
        return fallback("disabled", "disabled", JudgmentError("disabled", KILLED_MESSAGE))
    resolved = judgments.resolve_api_key()
    if resolved is None:
        return fallback("no_key", error=JudgmentError("unavailable", MISSING_KEY_MESSAGE))
    key, _ = resolved
    cfg = config.get_judgments_config()
    built = build_request(packet, model=cfg["model"], max_bytes=cfg["max_request_bytes"])
    if built is None:
        return fallback("oversize", error=JudgmentError("budget_exhausted", "criteria and check results exceed max_request_bytes"))
    state, questions, trimmed = built
    sizes = {"trimmed": trimmed, "request_bytes": request_size(cfg["model"], state, questions)}
    client = judgments.make_client(key, ledger=ledger)
    try:
        async with client:
            result = await client.evaluate(
                state, questions, call_id=call_id, purpose=PURPOSE, rubric_version=RUBRIC_VERSION,
                artifact_revision=packet.packet_id, partial=True,
            )
    except JudgmentError as err:
        return fallback("timeout" if str(err) in TIMEOUT_MESSAGES else err.outcome, err.outcome, err, **sizes)
    except asyncio.CancelledError:
        _finish(ledger, call_id, packet, mode=mode, reason="cancelled", status="cancelled", threshold=threshold, **sizes)
        raise
    labels = {
        c.id: label_for(result.answers[c.id], threshold) if c.id in result.answers else "no_answer"
        for c in packet.criteria
    }
    return _finish(ledger, call_id, packet, mode=mode, reason=None, status="answered", labels=labels, threshold=threshold, **sizes)


def run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def assess_candidate(
    *, cwd: Path, criteria: str | Sequence[str], head: str | None = None, worktree: Path | None = None,
    checks: Sequence[CheckResult] = (), ledger: JudgmentLedger, mode: Literal["explicit", "shadow"] = "explicit",
) -> JudgmentReceipt:
    if head is None:
        diff, candidate = collect_working_tree(cwd)
        code = build_repo_context(cwd, diff)
    else:
        repo = worktree if worktree is not None and Path(worktree).is_dir() else cwd
        diff, code, candidate = collect_commit(repo, head)
    packet = build_packet(criteria, diff=diff, code=code, checks=checks, candidate=candidate)
    return await assess(packet, mode=mode, ledger=ledger)


def candidate_review_path(repo_root: Path, swarm_id: str, task_id: str) -> Path:
    for value in (swarm_id, task_id):
        if not SAFE_ID.fullmatch(value) or ".." in value:
            raise ValueError(f"unsafe id: {value!r}")
    return Path(repo_root) / ".voss" / "swarm" / swarm_id / "reviews" / f"{task_id}.json"


def write_candidate_review(path: Path, ledger: JudgmentLedger) -> Path | None:
    if not ledger.receipts:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "judgments_cost_usd": ledger.observed_usd,
        "held_usd": ledger.held_usd,
        "receipts": [dataclasses.asdict(r) for r in ledger.receipts],
    }
    path.write_text(json.dumps(payload, indent=2))
    path.chmod(0o600)
    return path


def _assessment_line(cid: str, label: object, probabilities: dict, status: str) -> str:
    if label in ("supported", "contradicted"):
        return f"  {cid}  {label}  P({label})={probabilities[label]:.2f}  {status}"
    if label == "abstained":
        top = max(probabilities, key=probabilities.get)
        return f"  {cid}  unclear (abstained)  P({top})={probabilities[top]:.2f}  {status}"
    return f"  {cid}  no answer  {status}"


def assessment_lines(receipt: dict, *, stale: bool) -> list[str]:
    status = STALE_TEXT if stale else "current"
    try:
        detail = receipt["detail"]
        if not isinstance(detail, dict):
            raise TypeError
        if receipt["status"] != "answered":
            return [HEADING, f"  not available: {receipt['fallback_reason'] or receipt['status']}"]
        labels, answers = detail["labels"], receipt["answers"]
        return [HEADING] + [
            _assessment_line(cid, labels.get(cid), (answers.get(cid) or {}).get("probabilities") or {}, status)
            for cid in detail["criterion_ids"]
        ]
    except (AttributeError, KeyError, TypeError, ValueError):
        return [HEADING, "  not available: malformed receipt"]
