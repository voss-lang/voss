"""M10 project-index context injection tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from voss_runtime.providers.base import ProviderResponse

from voss.harness.agent import Plan, run_turn
from voss.harness.code.context import render_project_index_section
from voss.harness.code.models import IndexSummary
from voss.harness.code.service import CodeIntelService
from voss.harness.permissions import PermissionGate
from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset


def test_repl_project_index_skips_non_project_directory(
    tmp_path: Path, monkeypatch
) -> None:
    from voss.harness import cli

    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("non-project startup should not build code index")

    monkeypatch.setattr(cli, "_get_code_service", fail_if_called)

    assert cli._render_project_index_text(tmp_path) == ""
    assert called is False


def test_repl_project_index_skips_home_even_with_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    from voss.harness import cli

    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        cli,
        "_get_code_service",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("home startup should not build code index")
        ),
    )

    assert cli._render_project_index_text(tmp_path) == ""


class CapturingProvider:
    def __init__(self, plan: Plan):
        self.plan = plan
        self.calls: list[dict] = []

    async def complete(self, **kwargs) -> ProviderResponse:
        self.calls.append(kwargs)
        return ProviderResponse(
            text="",
            model=kwargs.get("model", "stub"),
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            raw={},
            parsed=None,
        )

    def stream(self, **kwargs):
        self.calls.append(kwargs)

        async def _gen():
            yield TextDelta(text="...")
            yield ParsedPlan(plan=self.plan)
            yield Usage(prompt_tokens=1, completion_tokens=1, cost_usd=0.0)
            yield Done(stop_reason="end_turn")

        return _gen()

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)


def _system_text(provider: CapturingProvider) -> str:
    chunks: list[str] = []
    for call in provider.calls:
        for msg in call.get("messages", []):
            if msg.get("role") != "system":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                chunks.extend(block.get("text", "") for block in content if isinstance(block, dict))
            else:
                chunks.append(str(content or ""))
    return "\n".join(chunks)


def test_project_index_text_is_injected_into_system_context(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def shared_entry(x):\n    return x\n", encoding="utf-8")
    svc = CodeIntelService.for_cwd(tmp_path)
    project_index_text = render_project_index_section(svc.get_project_index_summary())
    provider = CapturingProvider(
        Plan(rationale="done", steps=[], confidence=0.9, final_when_done="done")
    )

    asyncio.run(
        run_turn(
            "ping",
            tools=make_toolset(tmp_path),
            cwd=tmp_path,
            renderer=PlainRenderer(),
            provider=provider,
            permissions=PermissionGate(auto_yes=True),
            project_index_text=project_index_text,
        )
    )

    sys_text = _system_text(provider)
    assert "## Project Index" in sys_text
    assert "app.py" in sys_text


def test_project_index_renderer_exact_markdown() -> None:
    summary = IndexSummary(
        file_count=3,
        symbol_count=12,
        languages={"Python": 2, "Voss": 1},
        top_modules=[("b.py", 5), ("a.py", 4)],
        entry_points=["main.py", "cli.py"],
    )

    assert render_project_index_section(summary) == (
        "## Project Index\n"
        "\n"
        "**Files by language:** Python (2), Voss (1)\n"
        "\n"
        "**Top modules by symbol count:**\n"
        "- `b.py` — 5 symbols\n"
        "- `a.py` — 4 symbols\n"
        "\n"
        "**Entry points:** `main.py`, `cli.py`\n"
        "\n"
        "_Total: 3 files, 12 symbols_"
    )
