"""V12-01 safety policy: strict schema, reference validation, pure classifier.

Covers VSAFE-02/03/04/06 at the policy/classifier layer (no runtime gate yet).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from voss.harness import cognition
from voss.harness.cognition_schemas import SafetyConfig
from voss.harness.safety import (
    SafetyActorContext,
    classify,
    decide,
)


# --- Strict schema + reference validation (Task 1, VSAFE-06) ----------------


def test_empty_safety_config_is_valid() -> None:
    c = SafetyConfig()
    assert c.factory_only_paths == []
    assert c.runbooks == []


def test_safety_config_rejects_unknown_keys() -> None:
    with pytest.raises(ValidationError):
        SafetyConfig.model_validate({"stray_key": 1})


def test_well_formed_config_with_refs_validates() -> None:
    c = SafetyConfig.model_validate(
        {
            "runbooks": [{"name": "prod-deploy", "steps": ["plan", "apply"]}],
            "pipelines": [{"name": "fast-path"}],
            "factory_only_paths": [
                {"glob": "infra/prod/**", "runbook": "prod-deploy", "classes": ["prod"]}
            ],
            "factory_only_operations": [
                {"pattern": "git push *", "runbook": "prod-deploy", "classes": ["irreversible"]}
            ],
            "latency_pipelines": [{"pattern": "quote *", "pipeline": "fast-path"}],
            "weak_model_scaffolds": [
                {"model_tiers": ["cheap", "fast"], "pattern": "*", "runbook": "prod-deploy"}
            ],
        }
    )
    assert c.factory_only_paths[0].runbook == "prod-deploy"
    assert c.latency_pipelines[0].pipeline == "fast-path"


def test_unknown_runbook_reference_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        SafetyConfig.model_validate(
            {
                "runbooks": [{"name": "exists"}],
                "factory_only_paths": [
                    {"glob": "infra/prod/**", "runbook": "ghost-runbook"}
                ],
            }
        )
    assert "ghost-runbook" in str(exc.value)


def test_unknown_pipeline_reference_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        SafetyConfig.model_validate(
            {
                "latency_pipelines": [{"pattern": "quote *", "pipeline": "ghost-pipe"}],
            }
        )
    assert "ghost-pipe" in str(exc.value)


def test_unknown_scaffold_runbook_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        SafetyConfig.model_validate(
            {
                "weak_model_scaffolds": [
                    {"roles": ["backend"], "runbook": "ghost-rb"}
                ],
            }
        )
    assert "ghost-rb" in str(exc.value)


# --- Loader integration (Task 1) --------------------------------------------


def _init_project(tmp_path):
    (tmp_path / "VOSS.md").write_text("# project\n")
    (tmp_path / ".voss").mkdir()


def test_missing_safety_file_does_not_fail_init(tmp_path) -> None:
    _init_project(tmp_path)
    bundle = cognition.load(tmp_path)
    assert bundle.initialized is True
    assert bundle.safety is None
    assert bundle.load_errors == []


def test_safety_file_loaded_into_bundle(tmp_path) -> None:
    _init_project(tmp_path)
    (tmp_path / ".voss" / "safety.yml").write_text(
        "runbooks:\n"
        "  - name: prod-deploy\n"
        "factory_only_paths:\n"
        "  - glob: 'infra/prod/**'\n"
        "    runbook: prod-deploy\n"
        "    classes: [prod]\n"
    )
    bundle = cognition.load(tmp_path)
    assert bundle.safety is not None
    assert bundle.safety.factory_only_paths[0].runbook == "prod-deploy"
    assert bundle.load_errors == []


def test_invalid_safety_ref_surfaces_load_error(tmp_path) -> None:
    _init_project(tmp_path)
    (tmp_path / ".voss" / "safety.yml").write_text(
        "factory_only_paths:\n"
        "  - glob: 'infra/prod/**'\n"
        "    runbook: missing-rb\n"
    )
    bundle = cognition.load(tmp_path)
    assert bundle.safety is None
    assert any("missing-rb" in e for e in bundle.load_errors)


# --- Pure classifier (Task 2, VSAFE-02/03/04) -------------------------------


def _policy() -> SafetyConfig:
    return SafetyConfig.model_validate(
        {
            "runbooks": [{"name": "prod-deploy"}, {"name": "scaffold-rb"}],
            "pipelines": [{"name": "fast-path"}],
            "factory_only_paths": [
                {
                    "id": "prod-paths",
                    "glob": "infra/prod/**",
                    "runbook": "prod-deploy",
                    "classes": ["prod", "irreversible"],
                }
            ],
            "factory_only_operations": [
                {
                    "id": "git-push",
                    "tool": "shell_run",
                    "pattern": "git push *",
                    "runbook": "prod-deploy",
                    "classes": ["deploy"],
                }
            ],
            "latency_pipelines": [
                {"id": "quote", "pattern": "quote *", "pipeline": "fast-path"}
            ],
            "weak_model_scaffolds": [
                {
                    "id": "cheap-scaffold",
                    "model_tiers": ["cheap", "fast"],
                    "pattern": "*",
                    "runbook": "scaffold-rb",
                }
            ],
        }
    )


def test_factory_only_path_glob_matches_and_returns_runbook() -> None:
    c = classify(_policy(), "fs_write", {"path": "infra/prod/app.yml"})
    assert c.label == "factory_only_path"
    assert c.runbook == "prod-deploy"
    assert c.trigger_rule_id == "prod-paths"
    assert c.trigger_path == "infra/prod/app.yml"
    assert c.requires_confirmation is True  # irreversible class


def test_factory_only_path_does_not_match_outside_glob() -> None:
    c = classify(_policy(), "fs_write", {"path": "src/app.yml"})
    assert c.label == "none"
    assert c.matched is False


def test_factory_only_operation_pattern_matches_command() -> None:
    c = classify(_policy(), "shell_run", {"cmd": "git push origin main"})
    assert c.label == "factory_only_operation"
    assert c.runbook == "prod-deploy"
    assert "deploy" in c.classes


def test_operation_tool_filter_excludes_other_tools() -> None:
    # Same pattern text but a different tool name → no operation match.
    c = classify(_policy(), "fs_write", {"path": "git push notes.txt"})
    assert c.label == "none"


def test_latency_pipeline_only_for_configured_operations() -> None:
    hit = classify(_policy(), "shell_run", {"cmd": "quote AAPL"})
    assert hit.label == "latency_pipeline"
    assert hit.pipeline == "fast-path"
    miss = classify(_policy(), "shell_run", {"cmd": "echo hi"})
    assert miss.label == "none"


def test_weak_model_scaffold_matches_cheap_not_strong() -> None:
    cheap = classify(
        _policy(),
        "fs_write",
        {"path": "src/x.py"},
        actor=SafetyActorContext(role="backend", model_tier="cheap"),
    )
    assert cheap.label == "weak_model_scaffold"
    assert cheap.runbook == "scaffold-rb"
    strong = classify(
        _policy(),
        "fs_write",
        {"path": "src/x.py"},
        actor=SafetyActorContext(role="backend", model_tier="strong"),
    )
    assert strong.label == "none"


def test_classify_none_when_no_policy() -> None:
    c = classify(None, "fs_write", {"path": "infra/prod/app.yml"})
    assert c.label == "none"


def test_decide_routes_factory_to_runbook() -> None:
    c = classify(_policy(), "fs_write", {"path": "infra/prod/app.yml"})
    d = decide(c)
    assert d.action == "runbook"
    assert d.runbook == "prod-deploy"
    assert d.requires_confirmation is True


def test_decide_allows_unmatched() -> None:
    d = decide(classify(_policy(), "fs_read", {"path": "README.md"}))
    assert d.action == "allow"
