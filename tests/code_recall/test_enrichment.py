"""VSEM-07/08 RED tests: enrichment profile routing, fail-closed default,
budget cap, cost-ledger row.

Planned seams:
  voss.harness.config.get_index_enrich_model() -> str | None   (D-06 fail-closed)
  voss.harness.config.get_code_recall_config() -> dict          (enrich_profile/enrich_budget_tokens/inject)
  CodeIndex._run_enrichment(...) dispatches via
  voss.harness.model_router.build_provider_for_model (stub_provider intercepts).
  Ledger row: .voss/sessions/<id>/token-savings.jsonl, method == "enrich".
"""
from __future__ import annotations

import json

from .conftest import write_fixture_repo


def _write_config(tmp_path, monkeypatch, body: str):
    config_home = tmp_path / "xdg"
    (config_home / "voss").mkdir(parents=True)
    (config_home / "voss" / "config.toml").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))


def _build_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    write_fixture_repo(repo)

    from voss.harness.code.index import build_index

    build_index(repo)

    from voss.harness.code.semantic_index import CodeIndex

    index = CodeIndex(repo)
    index.build(session_id="test-session")
    return repo, index


def test_profile_off_zero_llm(tmp_path, fake_embed_fn, stub_provider, monkeypatch):
    """Default (profile off): a full index build makes ZERO provider calls."""
    _write_config(tmp_path, monkeypatch, "[code_recall]\n")

    _build_repo(tmp_path)

    assert stub_provider.call_count == 0, (
        f"profile-off build must not touch the provider path "
        f"(saw {stub_provider.calls})"
    )


def test_routes_index_enrich_role(tmp_path, fake_embed_fn, stub_provider, monkeypatch):
    """Profile on: enrichment calls route to the index_enrich tier's model,
    never the session model."""
    _write_config(
        tmp_path,
        monkeypatch,
        "[model_tiers]\n"
        'index_enrich = "test-enrich-model"\n'
        "\n"
        "[code_recall]\n"
        "enrich_profile = true\n"
        "enrich_budget_tokens = 100000\n",
    )

    from voss.harness.config import get_index_enrich_model

    assert get_index_enrich_model() == "test-enrich-model"

    _build_repo(tmp_path)

    assert stub_provider.call_count > 0, "profile-on build must run enrichment"
    assert set(stub_provider.models) == {"test-enrich-model"}, (
        f"enrichment must route only via index_enrich, saw {stub_provider.models}"
    )


def test_fail_closed_no_config(tmp_path, fake_embed_fn, stub_provider, monkeypatch):
    """D-06: profile on but NO index_enrich model configured → enrichment
    disabled, zero provider calls, build still succeeds."""
    _write_config(
        tmp_path,
        monkeypatch,
        "[code_recall]\nenrich_profile = true\nenrich_budget_tokens = 100000\n",
    )

    from voss.harness.config import get_index_enrich_model

    assert get_index_enrich_model() is None

    repo, index = _build_repo(tmp_path)

    assert stub_provider.call_count == 0, "missing index_enrich config must fail closed"
    assert index.query("retry backoff delay", top_k=3), "index must still build"


def test_budget_cap_abort(tmp_path, fake_embed_fn, stub_provider, monkeypatch):
    """VSEM-08: tiny enrich_budget_tokens → clean abort (no raise), index
    remains valid and queryable."""
    _write_config(
        tmp_path,
        monkeypatch,
        "[model_tiers]\n"
        'index_enrich = "test-enrich-model"\n'
        "\n"
        "[code_recall]\n"
        "enrich_profile = true\n"
        "enrich_budget_tokens = 1\n",
    )

    repo, index = _build_repo(tmp_path)  # must not raise at the cap

    hits = index.query("retry backoff delay", top_k=3)
    assert hits, "index must stay valid after budget abort"


def test_cost_ledger_line(tmp_path, fake_embed_fn, stub_provider, monkeypatch):
    """VSEM-08: enrichment writes a method=="enrich" row to the session-scoped
    token-savings.jsonl ledger that /cost reads."""
    _write_config(
        tmp_path,
        monkeypatch,
        "[model_tiers]\n"
        'index_enrich = "test-enrich-model"\n'
        "\n"
        "[code_recall]\n"
        "enrich_profile = true\n"
        "enrich_budget_tokens = 100000\n",
    )

    repo, _index = _build_repo(tmp_path)

    ledger = repo / ".voss" / "sessions" / "test-session" / "token-savings.jsonl"
    assert ledger.exists(), f"enrichment must write the session ledger at {ledger}"
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line]
    enrich_rows = [r for r in rows if r.get("method") == "enrich"]
    assert enrich_rows, f"expected a method=='enrich' ledger row, got {rows}"
    assert enrich_rows[0].get("model") == "test-enrich-model"
