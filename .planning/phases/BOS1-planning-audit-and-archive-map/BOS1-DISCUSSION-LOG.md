# Phase BOS1: Planning Audit and Archive Map - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS1-planning-audit-and-archive-map
**Areas discussed:** Audit scope, Classification taxonomy, Index format + location, Archive action boundary

---

## Audit Scope / Inventory Net

| Option | Description | Selected |
|--------|-------------|----------|
| Root plans + track rollup + ancillary | Per-file loose root .md + seeds/notes/docs; phase dirs at track level; stray external in appendix | ✓ |
| Loose root plans only | Only ~12 .planning root .md files | |
| Everything per-file | Every file in all 91 phase dirs + root + seeds/notes/docs | |
| Full .planning + external | Rollup approach + repo-root/.vscode as first-class rows | |

**User's choice:** Root plans + track rollup + ancillary (Recommended).
**Notes:** Phase dirs already indexed in ROADMAP/STATE → track-level rollup avoids redundant per-file audit.

---

## Classification Taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| Two axes: status + BOS-relationship | status{active/historical/superseded/archive-candidate} + BOS-relationship{substrate/dependency/historical-context/out-of-scope} | ✓ |
| Single 4-label status | Just status; PLAN-04 as free-text note | |
| One merged label set | Single enum mixing both concerns | |

**User's choice:** Two axes (Recommended).
**Notes:** PLAN-02 (lifecycle) and PLAN-04 (BOS relationship) are orthogonal — kept separate to avoid lossy merge.

---

## Index Format + Location

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown table in .planning/ root | AUDIT-INDEX.md, columns doc/track, status, BOS-relationship, reason, supersedes pointer | ✓ |
| Markdown + JSON sidecar | Same plus AUDIT-INDEX.json now | |
| Live in .planning/archive/ | Index inside archive dir | |

**User's choice:** Markdown table at .planning/ root (Recommended).
**Notes:** JSON sidecar deferred unless tooling needs it.

---

## Archive Action Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Index-only, no moves | Classify + flag only, archiving is a later step | |
| Index + move-not-delete | Also move archive-candidates to .planning/archive/ | |
| Index + move + delete approved | Full cleanup: classify, move, delete with per-item approval | ✓ |

**User's choice:** Index + move + delete approved.
**Notes:** Captured with guardrails in CONTEXT D-04/D-05 — index-first + per-item human approval keeps it consistent with PROJECT.md "no blind deletion" and global git-safety. Move preferred over delete; delete reserved for clearly-dead docs with explicit sign-off.

---

## Claude's Discretion

- AUDIT-INDEX.md column ordering, grouping, section headers.
- Track grouping/labeling in the rollup (by prefix).
- `reason` cell wording and supersession-pointer notation.
- External-stray-docs appendix structure.

## Deferred Ideas

- Machine-readable AUDIT-INDEX.json sidecar (only if tooling needs it).
- Re-splitting the roadmap (BOS-PLAN-03 — split already exists; BOS1 verifies, not re-architects).
- Source-code dead-file cleanup (out of scope; .planning corpus only).
- Per-file pruning inside phase dirs (track-level rollup only).
