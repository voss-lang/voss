from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from typing import Literal

import click

from voss_runtime.judgments import (
    KEY_ENV, KILLED_MESSAGE, MISSING_KEY_MESSAGE, ChoiceQuestion, ChoiceResult, JevClient, JudgmentError,
    JudgmentLedger, JudgmentResult, NoulQuestion, Question, ScoreQuestion, ScoreResult, is_killed, question_from_wire,
)

from . import auth, config
from .conventions import _load_judgments_code_recall, _load_judgments_enabled

CODE_RECALL_MODES = ("off", "shadow", "active")


def judgments_state(cwd) -> Literal["killed", "disabled", "enabled"]:
    if is_killed():
        return "killed"
    return "enabled" if _load_judgments_enabled(cwd) else "disabled"


def resolve_api_key() -> tuple[str, Literal["env", "keychain"]] | None:
    value = os.environ.get(KEY_ENV, "").strip()
    if value:
        return value, "env"
    value = auth.load_provider_key(KEY_ENV)
    return (value, "keychain") if value else None


def bridge_judgments_env() -> None:
    if is_killed() or os.environ.get(KEY_ENV, "").strip():
        return
    value = auth.load_provider_key(KEY_ENV)
    if value:
        os.environ[KEY_ENV] = value


def code_recall_mode(cwd) -> Literal["off", "shadow", "active"]:
    if judgments_state(cwd) != "enabled" or resolve_api_key() is None:
        return "off"
    return _load_judgments_code_recall(cwd)


def make_client(api_key: str, *, timeout_ms: int | None = None, ledger: JudgmentLedger | None = None) -> JevClient:
    cfg = config.get_judgments_config()
    return JevClient(
        api_key, model=cfg["model"], timeout_ms=cfg["timeout_ms"] if timeout_ms is None else timeout_ms,
        max_request_bytes=cfg["max_request_bytes"], max_calls=cfg["max_calls_per_turn"],
        max_cost_usd=cfg["max_cost_usd"], ledger=ledger,
    )


def open_client(cwd, *, explicit: bool) -> JevClient:
    if is_killed():
        raise JudgmentError("disabled", KILLED_MESSAGE)
    if not explicit and not _load_judgments_enabled(cwd):
        raise JudgmentError("disabled", "judgments not enabled for this project")
    found = resolve_api_key()
    if found is None:
        raise JudgmentError("unavailable", MISSING_KEY_MESSAGE)
    return make_client(found[0])


def demo_request() -> tuple[str, dict[str, Question]]:
    return (
        "Synthetic function: def add(a, b): return a - b\nFailing test: add(2, 3) should equal 5.",
        {
            "next_step": ChoiceQuestion("What should the developer do next?", {
                "run_tests": "Run tests to reproduce the failure.",
                "edit_code": "Correct the arithmetic operation.",
                "ask_user": "Ask for missing requirements.",
                "insufficient_evidence": "The state does not support a choice.",
            }),
            "risk": ScoreQuestion("How risky is fixing this arithmetic bug?", ["low", "medium", "high"]),
            "needs_tests": NoulQuestion("Should the fix be verified with tests?"),
        },
    )


def load_request_file(path: Path) -> tuple[object, dict[str, Question]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        json.dumps(data, allow_nan=False)
    except (OSError, UnicodeError, ValueError):
        raise ValueError("expected readable JSON with finite values") from None
    if not isinstance(data, dict) or "state" not in data:
        raise ValueError("expected an object containing state and questions")
    raw = data.get("questions")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("questions must be a non-empty object")
    questions = {}
    for qid, question in raw.items():
        if not qid:
            raise ValueError("each question needs an ID and instructions")
        questions[qid] = question_from_wire(question)
    return data["state"], questions


def _render_result(result: JudgmentResult) -> None:
    click.echo(f"{'Question':<22} {'Type':<8} Answer")
    for qid, answer in result.answers.items():
        if isinstance(answer, ChoiceResult):
            selected = f"{answer.choice} (p={answer.probabilities[answer.choice]:.3f})"
        elif isinstance(answer, ScoreResult):
            level = max(answer.probabilities, key=answer.probabilities.get)
            selected = f"score {answer.score:.3f}; level {level} (p={answer.probabilities[level]:.3f})"
        else:
            selected = f"P(yes)={answer.noul:.3f}"
        click.echo(f"{qid:<22} {answer.type:<8} {selected}")
        if isinstance(answer, (ChoiceResult, ScoreResult)):
            distribution = ", ".join(f"{option}={p:.3f}" for option, p in answer.probabilities.items())
            click.echo(f"  {distribution}; confidence={answer.confidence:.3f}")
        else:
            click.echo(f"  true={answer.noul:.3f}, false={1 - answer.noul:.3f}")
    click.echo(f"model {result.model}; tokens in {result.input_tokens} out {result.output_tokens}")
    click.echo(f"{result.latency_ms:.0f} ms; attempts {result.attempts}; cost estimate ${result.cost_usd_estimate:.6f}")


@click.command("judge")
@click.argument("request_file", required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--demo", is_flag=True, help="Evaluate a synthetic coding request with all three question types.")
@click.option("--json", "as_json", is_flag=True, help="Print the typed result as JSON.")
def judge_cmd(request_file: Path | None, demo: bool, as_json: bool) -> None:
    """Evaluate an explicit Jev request from a JSON file or --demo."""
    if demo == (request_file is not None):
        raise click.UsageError("provide either a request file or --demo")
    try:
        state, questions = demo_request() if demo else load_request_file(request_file)
    except ValueError as err:
        click.echo(f"invalid request file: {err}", err=True)
        sys.exit(1)

    async def evaluate(client):
        async with client:
            return await client.evaluate(state, questions)

    try:
        result = asyncio.run(evaluate(open_client(Path.cwd(), explicit=True)))
    except JudgmentError as err:
        click.echo(f"judgment {err.outcome}: {err}", err=True)
        sys.exit(1)
    if as_json:
        click.echo(json.dumps(asdict(result), indent=2))
    else:
        _render_result(result)
