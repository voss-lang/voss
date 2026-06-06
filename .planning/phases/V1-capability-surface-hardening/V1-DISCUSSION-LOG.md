# Phase V1: Capability Surface Hardening — Discussion Log

**Date:** 2026-06-06
**Mode:** discuss (default). Options presented in plain language with technical term in parens (Ben's standing V-track preference), full rigor in decisions.

> Human-reference record only. Not consumed by downstream agents — see V1-CONTEXT.md.

## Area 1 — Capability metadata source
**Options presented:**
1. Tag every tool by hand (per-entry literal metadata)
2. Auto-derive from name prefix (convention-based)
3. Hybrid: derive + override (recommended)

**Selected:** Tag every tool by hand → D-01. Ben chose maximum precision over the recommended hybrid; explicit per-entry fields, no naming magic.

## Area 2 — MCP / external tool trust default
**Options presented:**
1. Treat as risky → needs approval (recommended, default-deny)
2. Trust each server's declaration

**Selected:** Default-deny → D-02. MCP capabilities default mutating + gated unless server declares read-only.

## Area 3 — Scope-requirement granularity
**Options presented:**
1. Coarse buckets (recommended, group-level)
2. Fine-grained resource scopes (path/host)

**Selected:** Coarse buckets → D-03. Group-level scope this phase; fine-grained deferred to V3/V4.

## Area 4 — `voss capabilities list` output
**Options presented:**
1. Names grouped by group
2. Names + permission badges (recommended)
3. Full table

**Selected:** Names grouped by group → D-04. Compact list; full detail lives in `inspect`.

## Claude's Discretion (locked at planning)
- audit-behavior field values (`full | redact_args | metadata_only`, default `full`)
- `is_stateful` flag (default false; CAP-03)
- recorder capability-invocation event shape (reuse RunRecorder/telemetry)
- input schema = `descriptor.parameters`; output schema authored per capability

## Deferred
- Fine-grained per-path/per-host scopes → V3/V4
- `.voss` team{} role→capability grammar → V3
