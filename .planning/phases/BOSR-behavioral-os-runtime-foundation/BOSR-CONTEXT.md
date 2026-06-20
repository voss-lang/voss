# BOSR Context: Behavioral OS Runtime Foundation

**Created:** 2026-06-20
**Phase:** BOSR - Behavioral OS Runtime Foundation
**Status:** Active consolidated phase

## Phase Goal

Turn the Behavioral OS source artifacts into a local runtime substrate:
projected engineering events, append-only event ledger, decision and outcome
capture, shadow recommendations, and a read model suitable for desktop/web
control-plane surfaces.

## Why This Reset Exists

BOS0-BOS18 was created as a docs-first decomposition. That captured useful
knowledge, but it became too broad and too plan-heavy. BOSI then separated
implementation from contracts, but that added another track instead of fixing
the root problem.

BOSR is the correction: one active implementation phase that consumes the
knowledge already captured and proceeds through normal GSD artifacts.

## Source Artifacts To Preserve

- BOS0: product thesis, ICP, wedge, discovery script.
- BOS1: planning audit/archive index.
- BOS2: monorepo and stack architecture.
- BOS3: event schema and point-in-time rules.
- BOS4: decision ledger schema and rationale.
- BOS5: outcome/reward schema, examples, and tests.
- BOS6: privacy, governance, autonomy bands, tenant boundaries.
- BOS7: web/control-plane responsibility map.
- BOS8: team/project/work model context.
- BOS9: recommendation review surface context and plans.
- BOSI1: `voss/harness/bos_events.py` and schema-validation tests.

## Locked Decisions

| ID | Decision | Consequence |
|---|---|---|
| D-01 | BOSR is the only active BOS implementation phase | ROADMAP/PROJECT/STATE/REQUIREMENTS point to BOSR |
| D-02 | Old BOS/BOSI artifacts are source material, not active phase rows | No further BOS10-BOS18 or BOSI2-BOSI6 planning |
| D-03 | Local harness/server/ADE/swarm is the substrate | No parallel bus; no filesystem-as-runtime transport |
| D-04 | Event projection remains pure | Source session/swarm writers are not modified by projection |
| D-05 | Ledger is local-first and append-only | `.voss/bos/events.jsonl` is the first persistence target |
| D-06 | Decisions and outcomes are separate records | Outcomes never mutate or leak into decision-time features |
| D-07 | Recommendations start shadow-mode | Human verdicts produce training signals; no autonomy increase |
| D-08 | Web is read-first | Shared control plane reads validated local/team state before write workflows |
| D-09 | Governance is enforced as data-shape and UI constraints | No rankings, raw activity scoring, or nudge-engagement optimization |
| D-10 | LEM/RL/online learning are deferred | BOSR exports point-in-time data; modeling comes later |

## Implementation Boundary

In scope:
- Local BOS event ledger.
- Runtime decision/outcome writers.
- Shadow recommendation records.
- Local read model for desktop/web surfaces.
- Contract and no-leakage tests.
- Roadmap/project/requirements/state reconciliation.

Out of scope:
- External PM/CI/deploy/incident ingestion.
- Online learning, contextual bandits in production, or LEM training.
- Multi-tenant SaaS, billing, admin, accounts, or cloud sync.
- Jira/Linear replacement workflows beyond the read model.
- New coordination transport.

## Success Definition

BOSR is complete when Voss can produce a point-in-time-correct local BOS
dataset from real harness/swarm activity, attach decisions and outcomes without
leakage, generate shadow recommendations, and expose a read model that desktop
or web surfaces can consume.
