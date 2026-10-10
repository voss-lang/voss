from __future__ import annotations

from collections.abc import Sequence
import dataclasses
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

from voss.harness.board.reviewer_b import build_repo_context
from voss_runtime.judgments import SAFE_ID

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
