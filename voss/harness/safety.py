"""V12 safety policy: pure classification + decision types (VSAFE-02/03/04/06).

This module is intentionally PURE — no tool execution, no prompting, no I/O.
Runtime integrations (PermissionGate overlay, EM dispatch, audit) call into the
classifier here in later plans. Keeping it pure makes the dangerous-operation
routing deterministic and unit-testable before any enforcement exists.

The strict `.voss/safety.yml` schema lives in `cognition_schemas`; it is
re-exported here so callers can `from voss.harness.safety import SafetyConfig`.
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any, Mapping, Optional

from voss.harness.cognition_schemas import (
    SafetyClass,
    SafetyConfig,
    SafetyLatencyRule,
    SafetyOperationRule,
    SafetyPathRule,
    SafetyPipeline,
    SafetyRunbook,
    SafetyScaffoldRule,
)

__all__ = [
    "SafetyClass",
    "SafetyConfig",
    "SafetyLatencyRule",
    "SafetyOperationRule",
    "SafetyPathRule",
    "SafetyPipeline",
    "SafetyRunbook",
    "SafetyScaffoldRule",
    "SafetyActorContext",
    "SafetyClassification",
    "SafetyDecision",
    "DANGEROUS_CLASSES",
    "classify",
    "decide",
]

# Dangerous-operation classes routed to factory runbooks (VSAFE-02).
DANGEROUS_CLASSES: tuple[str, ...] = (
    "irreversible",
    "deploy",
    "delete",
    "migration",
    "money",
    "prod",
)

# Tool-arg keys that carry a filesystem path / a shell command, in priority order.
_PATH_KEYS = ("path", "file", "target", "dest", "destination")
_CMD_KEYS = ("cmd", "command", "argv", "script")


@dataclass(frozen=True)
class SafetyActorContext:
    """Who is requesting the operation (direct loop or EM-dispatched worker)."""

    role: Optional[str] = None
    model_tier: Optional[str] = None  # "cheap" | "fast" | "strong" | ...


@dataclass(frozen=True)
class SafetyClassification:
    """Structured result of classifying one tool call against the policy."""

    label: str  # none|factory_only_path|factory_only_operation|latency_pipeline|weak_model_scaffold
    classes: tuple[str, ...] = ()
    trigger_rule_id: Optional[str] = None
    trigger_path: Optional[str] = None
    runbook: Optional[str] = None
    pipeline: Optional[str] = None
    actor_role: Optional[str] = None
    actor_model_tier: Optional[str] = None
    requires_confirmation: bool = False

    @property
    def matched(self) -> bool:
        return self.label != "none"


@dataclass(frozen=True)
class SafetyDecision:
    """Routing decision derived from a classification (consumed by later plans)."""

    action: str  # allow | deny | confirm | runbook | scaffold
    classification: SafetyClassification
    runbook: Optional[str] = None
    pipeline: Optional[str] = None
    requires_confirmation: bool = False
    reason: str = ""


def _first_str(args: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[str]:
    for k in keys:
        v = args.get(k)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, (list, tuple)) and v:
            return " ".join(str(x) for x in v)
    return None


def _arg_path(args: Mapping[str, Any]) -> Optional[str]:
    return _first_str(args, _PATH_KEYS)


def _arg_command(args: Mapping[str, Any]) -> Optional[str]:
    return _first_str(args, _CMD_KEYS)


def _op_matches(rule_tool: Optional[str], pattern: str, tool_name: str, op_text: str) -> bool:
    if rule_tool is not None and rule_tool != tool_name:
        return False
    return fnmatch(op_text, pattern) or fnmatch(tool_name, pattern)


def classify(
    config: Optional[SafetyConfig],
    tool_name: str,
    tool_args: Optional[Mapping[str, Any]] = None,
    *,
    tool_meta: Optional[Mapping[str, Any]] = None,  # reserved for later plans
    actor: Optional[SafetyActorContext] = None,
) -> SafetyClassification:
    """Pure classifier. Deterministic; first matching category wins.

    Category precedence: factory-only paths → factory-only operations →
    latency pipelines → weak-model scaffolds. Returns label "none" when nothing
    matches (the ordinary autonomous path — additive, no behavior change).
    """
    actor = actor or SafetyActorContext()
    args: Mapping[str, Any] = tool_args or {}
    base = {
        "actor_role": actor.role,
        "actor_model_tier": actor.model_tier,
    }
    if config is None:
        return SafetyClassification(label="none", **base)

    path = _arg_path(args)
    op_text = _arg_command(args) or tool_name

    # 1. Factory-only paths (VSAFE-06).
    if path is not None:
        for i, rule in enumerate(config.factory_only_paths):
            if fnmatch(path, rule.glob):
                return SafetyClassification(
                    label="factory_only_path",
                    classes=tuple(rule.classes),
                    trigger_rule_id=rule.id or f"factory_only_paths[{i}]",
                    trigger_path=path,
                    runbook=rule.runbook,
                    requires_confirmation="irreversible" in rule.classes,
                    **base,
                )

    # 2. Factory-only operations (VSAFE-02).
    for i, rule in enumerate(config.factory_only_operations):
        if _op_matches(rule.tool, rule.pattern, tool_name, op_text):
            return SafetyClassification(
                label="factory_only_operation",
                classes=tuple(rule.classes),
                trigger_rule_id=rule.id or f"factory_only_operations[{i}]",
                runbook=rule.runbook,
                requires_confirmation="irreversible" in rule.classes,
                **base,
            )

    # 3. Latency-critical fixed pipelines (VSAFE-03).
    for i, rule in enumerate(config.latency_pipelines):
        if _op_matches(rule.tool, rule.pattern, tool_name, op_text):
            return SafetyClassification(
                label="latency_pipeline",
                trigger_rule_id=rule.id or f"latency_pipelines[{i}]",
                pipeline=rule.pipeline,
                **base,
            )

    # 4. Weak-model scaffolds (VSAFE-04). Only fires for rules that constrain by
    # role or tier AND whose actor matches — strong/unconfigured actors are exempt.
    for i, rule in enumerate(config.weak_model_scaffolds):
        if not (rule.roles or rule.model_tiers):
            continue
        role_ok = (not rule.roles) or (actor.role in rule.roles)
        tier_ok = (not rule.model_tiers) or (actor.model_tier in rule.model_tiers)
        if role_ok and tier_ok and (
            fnmatch(op_text, rule.pattern) or fnmatch(tool_name, rule.pattern)
        ):
            return SafetyClassification(
                label="weak_model_scaffold",
                trigger_rule_id=rule.id or f"weak_model_scaffolds[{i}]",
                runbook=rule.runbook,
                **base,
            )

    return SafetyClassification(label="none", **base)


def decide(classification: SafetyClassification) -> SafetyDecision:
    """Map a classification to a routing decision. Pure; later plans enforce it."""
    c = classification
    if not c.matched:
        return SafetyDecision(action="allow", classification=c)
    if c.label in ("factory_only_path", "factory_only_operation"):
        return SafetyDecision(
            action="runbook",
            classification=c,
            runbook=c.runbook,
            requires_confirmation=c.requires_confirmation,
            reason=f"factory-only → runbook '{c.runbook}'",
        )
    if c.label == "latency_pipeline":
        return SafetyDecision(
            action="runbook",
            classification=c,
            pipeline=c.pipeline,
            reason=f"latency-critical → fixed pipeline '{c.pipeline}'",
        )
    if c.label == "weak_model_scaffold":
        return SafetyDecision(
            action="scaffold",
            classification=c,
            runbook=c.runbook,
            reason="weak-model → scaffolded procedure",
        )
    return SafetyDecision(action="allow", classification=c)
