"""Single-shot LLM critique of diffs against natural-language constraints.

Reads `.voss/constraints.yml`, captures a git diff, sends a single
provider.complete call, and returns structured violations.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

from voss.template_render import render_package_template

MAX_DIFF_CHARS = 30_000


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class Violation(BaseModel):
    model_config = {"extra": "ignore"}

    constraint: str
    file: str = ""
    line: Optional[int] = None
    explanation: str = ""


class CritiqueSummary(BaseModel):
    model_config = {"extra": "ignore"}

    total_checked: int = 0
    violation_count: int = 0


class CritiqueResponse(BaseModel):
    model_config = {"extra": "ignore"}

    violations: list[Violation] = Field(default_factory=list)
    summary: CritiqueSummary = CritiqueSummary()


class ConstraintsConfig(BaseModel):
    model_config = {"extra": "ignore"}

    mode: str = "warn"
    rules: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Constraint loading
# ---------------------------------------------------------------------------


def load_constraints(cwd: Path) -> Optional[ConstraintsConfig]:
    """Load .voss/constraints.yml. Returns None if missing or invalid."""
    path = cwd / ".voss" / "constraints.yml"
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return ConstraintsConfig.model_validate(raw)
    except (yaml.YAMLError, ValidationError):
        return None


# ---------------------------------------------------------------------------
# Diff capture
# ---------------------------------------------------------------------------


def capture_diff(mode: str, cwd: Path, ref: Optional[str] = None) -> str:
    """Capture diff text from git or stdin.

    Modes: "staged", "ref", "stdin".
    Raises RuntimeError if cwd is not a git repository.
    """
    if mode == "stdin":
        text = sys.stdin.read()
    else:
        # Pre-flight: verify git repo
        check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if check.returncode != 0:
            raise RuntimeError("not a git repository")

        if mode == "staged":
            cmd = ["git", "diff", "--cached"]
        elif mode == "ref":
            cmd = ["git", "diff", ref]
        else:
            raise ValueError(f"unknown diff mode: {mode}")

        out = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = out.stdout

    if len(text) > MAX_DIFF_CHARS:
        text = text[:MAX_DIFF_CHARS] + "\n[diff truncated]"
    return text


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def build_prompt(constraints: ConstraintsConfig, diff_text: str) -> str:
    """Build system prompt injecting constraint rules and the diff."""
    return render_package_template(
        "voss",
        "templates/prompts/consensus.txt.jinja",
        {
            "rules": list(constraints.rules),
            "diff_text": diff_text,
        },
    )


# ---------------------------------------------------------------------------
# Single-shot critique
# ---------------------------------------------------------------------------


async def run_critique(
    provider,
    model: str,
    constraints: ConstraintsConfig,
    diff_text: str,
) -> Optional[CritiqueResponse]:
    """Single provider.complete call. Returns None on any failure (fail-open)."""
    system_prompt = build_prompt(constraints, diff_text)
    try:
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "Review the staged diff above against the constraints.",
                },
            ],
            model=model,
            response_format=CritiqueResponse,
            temperature=0.0,
            max_tokens=2000,
        )
    except Exception:  # noqa: BLE001 — fail-open contract
        return None
    if resp.parsed is None:
        return None
    return resp.parsed


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_violations(
    result: CritiqueResponse,
) -> tuple[str, bool]:
    """Format critique output. Returns (text, has_violations)."""
    if not result.violations:
        n = result.summary.total_checked
        return (f"\u2713 All clear — {n} constraints checked, 0 violations.", False)

    violations: list[dict] = []
    for v in result.violations:
        loc = None
        if v.file:
            loc = v.file
            if v.line is not None:
                loc += f":{v.line}"
        violations.append(
            {"constraint": v.constraint, "location": loc, "explanation": v.explanation}
        )

    # Template ends with a final newline (keep_trailing_newline); the original
    # "\n".join() produced none, so strip it to preserve byte parity.
    text = render_package_template(
        "voss",
        "templates/consensus/violations.txt.jinja",
        {
            "violations": violations,
            "count": result.summary.violation_count,
            "total": result.summary.total_checked,
        },
    ).rstrip("\n")
    return (text, True)
