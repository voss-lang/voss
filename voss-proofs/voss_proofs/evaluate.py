"""Deterministic evaluators: checks, hidden acceptance checks, scope, verdict."""
from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from .spec import AnyCheck, CheckResult, CmdCheck, FileContainsCheck, FileExistsCheck
from .store import Store

EVALUATOR_VERSION = "deterministic.v1"


def run_check(check: AnyCheck, repo: Path, env: dict[str, str], kind: str, store: Store) -> CheckResult:
    if isinstance(check, CmdCheck):
        try:
            p = subprocess.run(
                check.run, shell=True, cwd=repo, env=env, capture_output=True,
                text=True, timeout=check.timeout,
            )
        except subprocess.TimeoutExpired:
            return CheckResult(name=check.run, kind=kind, passed=False, detail=f"timeout {check.timeout}s")
        log = store.put(f"$ {check.run}\n[exit {p.returncode}]\n{p.stdout}\n{p.stderr}")
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
