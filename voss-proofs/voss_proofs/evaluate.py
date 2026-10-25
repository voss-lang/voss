"""Deterministic evaluators: checks, hidden acceptance checks, scope, verdict."""
from __future__ import annotations

import fnmatch
import json
import os
import signal
import subprocess
from pathlib import Path

from .spec import AnyCheck, CheckResult, CmdCheck, FileContainsCheck, FileExistsCheck, Judge
from .store import Store

EVALUATOR_VERSION = "deterministic.v1"


def run_check(check: AnyCheck, repo: Path, env: dict[str, str], kind: str, store: Store) -> CheckResult:
    if isinstance(check, CmdCheck):
        p = subprocess.Popen(
            check.run, shell=True, cwd=repo, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
        try:
            out, err = p.communicate(timeout=check.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            return CheckResult(name=check.run, kind=kind, passed=False, detail=f"timeout {check.timeout}s")
        log = store.put(f"$ {check.run}\n[exit {p.returncode}]\n{out}\n{err}")
        return CheckResult(
            name=check.run, kind=kind, passed=p.returncode == 0,
            detail=f"exit {p.returncode}", log=log,
        )
    target = repo / check.path
    if isinstance(check, FileExistsCheck):
        return CheckResult(name=f"exists:{check.path}", kind=kind, passed=target.exists())
    assert isinstance(check, FileContainsCheck)
    ok = target.is_file() and check.text in target.read_text(errors="replace")
    return CheckResult(name=f"contains:{check.path}", kind=kind, passed=ok)


def scope_check(changed: list[str], allowed: list[str]) -> CheckResult | None:
    if not allowed:
        return None
    outside = [p for p in changed if not any(fnmatch.fnmatch(p, pat) for pat in allowed)]
    return CheckResult(
        name="scope", kind="scope", passed=not outside,
        detail=("outside allowed_paths: " + ", ".join(outside)) if outside else "",
    )


def verdict(checks: list[CheckResult]) -> bool | None:
    """Verified only when every deterministic check passed. No checks -> unknown."""
    return all(c.passed for c in checks) if checks else None


def jev_review(criteria: list[str], visible: list[CheckResult], repo: Path, scratch: Path,
               env: dict[str, str], voss_bin: str, store: Store) -> tuple[Judge, str | None]:
    """`voss judge review` on the working tree. Runs before hidden checks exist and sees only visible ones."""
    if not criteria:
        return Judge(verdict="failed", error="scenario has no acceptance criteria"), None
    (scratch / "criteria.txt").write_text("\n".join(criteria) + "\n")
    (scratch / "checks.json").write_text(json.dumps(
        [{"name": c.name, "status": "passed" if c.passed else "failed"} for c in visible]))
    try:
        p = subprocess.run(
            [voss_bin, "judge", "review", "--criteria-file", str(scratch / "criteria.txt"),
             "--checks", str(scratch / "checks.json"), "--json"],
            cwd=repo, env=env, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return Judge(verdict="failed", error="voss judge review timed out"), None
    if p.returncode != 0:
        return Judge(verdict="failed", error=(p.stderr.strip() or f"exit {p.returncode}")[:300]), None
    receipt = json.loads(p.stdout)
    ref = store.put(p.stdout)
    if receipt.get("status") != "answered":
        return Judge(verdict="failed", model=receipt.get("model_returned"), cost_usd=receipt.get("cost_usd"),
                     error=f"status {receipt.get('status')}: {receipt.get('fallback_reason')}"), ref
    labels = receipt["detail"]["labels"]
    return Judge(
        verdict="accept" if all(v == "supported" for v in labels.values()) else "reject",
        model=receipt.get("model_returned"), labels=labels, cost_usd=receipt.get("cost_usd"),
        probabilities={c: a["probabilities"] for c, a in receipt["answers"].items() if a.get("probabilities")},
    ), ref
