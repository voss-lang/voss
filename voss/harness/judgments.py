from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Literal

import click
import yaml

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


class _JudgeGroup(click.Group):
    def parse_args(self, ctx, args):
        if not args or (args[0] not in self.commands and args[0] not in ctx.help_option_names):
            args = ["run", *args]
        return super().parse_args(ctx, args)


@click.group("judge", cls=_JudgeGroup)
def judge_cmd() -> None:
    """Evaluate an explicit Jev request from a JSON file or --demo."""


@judge_cmd.command("run")
@click.argument("request_file", required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--demo", is_flag=True, help="Evaluate a synthetic coding request with all three question types.")
@click.option("--json", "as_json", is_flag=True, help="Print the typed result as JSON.")
def run_cmd(request_file: Path | None, demo: bool, as_json: bool) -> None:
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


def _set_code_recall_line(text: str) -> str:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        raise ValueError("the file is not valid YAML") from None
    if not isinstance(data, dict) or not isinstance(data.get("judgments"), dict):
        raise ValueError("no judgments mapping found")
    lines = text.splitlines(keepends=True)
    headers = [i for i, line in enumerate(lines) if re.fullmatch(r"judgments:\s*(#.*)?", line.rstrip("\r\n"))]
    if len(headers) != 1:
        raise ValueError("expected exactly one top-level block-style judgments: line")
    end = headers[0] + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][0] in " \t"):
        end += 1
    block = range(headers[0] + 1, end)
    content = [i for i in block if lines[i].strip() and not lines[i].lstrip().startswith("#")]
    if not content:
        raise ValueError("the judgments block is empty")
    indent = re.match(r"[ \t]*", lines[content[0]])[0]
    found = [i for i in block if lines[i].startswith(f"{indent}code_recall:")]
    if len(found) > 1:
        raise ValueError("more than one code_recall line")
    if found:
        line = lines[found[0]]
        body = line.rstrip("\r\n")
        m = re.fullmatch(r"(\s*code_recall:\s*)(.*?)(\s+#.*)?", body)
        lines[found[0]] = f"{m[1]}active{m[3] or ''}{line[len(body):]}"
    else:
        anchor = [i for i in block if lines[i].startswith(f"{indent}enabled:")]
        if len(anchor) != 1:
            raise ValueError("expected exactly one enabled line under judgments")
        line = lines[anchor[0]]
        body = line.rstrip("\r\n")
        eol = line[len(body):] or "\n"
        lines[anchor[0]] = body + eol
        lines.insert(anchor[0] + 1, f"{indent}code_recall: active{eol}")
    result = "".join(lines)
    expected = {**data, "judgments": {**data["judgments"], "code_recall": "active"}}
    try:
        if yaml.safe_load(result) != expected:
            raise ValueError("the edited file does not parse to the expected settings")
    except yaml.YAMLError:
        raise ValueError("the edited file is not valid YAML") from None
    return result


def _gate_failure(report: dict | None, name: str, model_key: str, model: str, rubric: str) -> str | None:
    if report is None:
        return f"{name} is missing or unreadable"
    if report.get("passed") is not True:
        return f"{name} did not pass"
    if report.get(model_key) != model:
        return f"{name} was produced with Jev model {report.get(model_key)!r}, configured model is {model!r}"
    if report.get("rubric_version") != rubric:
        return f"{name} has rubric_version {report.get('rubric_version')!r}, current is {rubric!r}"
    return None


def _read_report(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _refuse(reason: str) -> None:
    click.echo(f"activate refused: {reason}", err=True)
    sys.exit(1)


@judge_cmd.command("activate")
@click.argument("consumer", type=click.Choice(["code_recall"]))
@click.option("--reports", type=click.Path(file_okay=False, path_type=Path),
              default=Path(__file__).resolve().parents[2] / "evals" / "retrieval" / "reports",
              help="Directory holding rerank-test.json and rerank-ab.json.")
def activate_cmd(consumer: str, reports: Path) -> None:
    """Set judgments.code_recall: active after checking the published gate reports."""
    from .code.rerank import RUBRIC_VERSION

    cwd = Path.cwd()
    if is_killed():
        _refuse(KILLED_MESSAGE)
    if not _load_judgments_enabled(cwd):
        _refuse("judgments.enabled is not true in .voss/config.yml")
    model = config.get_judgments_config()["model"]
    test = _read_report(reports / "rerank-test.json")
    ab = _read_report(reports / "rerank-ab.json")
    if test is not None and test.get("status") != "complete":
        _refuse("rerank-test.json is incomplete")
    if test is not None and test.get("split") != "test":
        _refuse(f"rerank-test.json is for split {test.get('split')!r}, not test")
    reason = _gate_failure(test, "rerank-test.json", "model", model, RUBRIC_VERSION) or _gate_failure(
        ab, "rerank-ab.json", "jev_model", model, RUBRIC_VERSION
    )
    if reason:
        _refuse(reason)
    try:
        ranking, latency, compare = test["ranking"], test["latency"], ab["compare"]
        summary = [
            f"ranking: nDCG@5 gain {ranking['mean_gain']:.4f}, CI lower bound {ranking['ci_low']:.4f}, recall diff {ranking['recall_diff']:.4f}",
            f"latency: n {latency['n']}, p95 {latency['p95_ms']:.0f} ms",
            f"A/B: {compare['n_tasks']} tasks, off {compare['a_pass_rate']:.3f} vs active {compare['b_pass_rate']:.3f}, regressions {compare['regressions']}",
        ]
    except (KeyError, TypeError, ValueError):
        _refuse("a gate report is missing required fields")
    click.echo(f"Gate evidence ({reports}):")
    for line in summary:
        click.echo(f"  {line}")
    click.echo(f"  model {model}; rubric {RUBRIC_VERSION}")
    click.echo("Active mode sends the task text and candidate code chunks to Jev on each turn.")
    path = cwd / ".voss" / "config.yml"
    if _load_judgments_code_recall(cwd) == "active":
        click.echo(f"judgments.code_recall is already active in {path}")
        return
    click.confirm(f"Set judgments.code_recall: active in {path}?", default=False, abort=True)
    try:
        updated = _set_code_recall_line(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as err:
        _refuse(f"cannot edit {path} safely: {err}")
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as tmp:
        tmp.write(updated.encode("utf-8"))
    try:
        os.chmod(tmp.name, stat.S_IMODE(path.stat().st_mode))
        os.replace(tmp.name, path)
    except OSError:
        os.unlink(tmp.name)
        raise
    click.echo(f"judgments.code_recall set to active in {path}")
