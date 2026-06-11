# Phase V21: Global Cross-Project Memory - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** V21-global-cross-project-memory
**Areas discussed:** Promotion semantics, Global store location, Recall blending policy, Write guardrails
**Mode:** default interactive, no SPEC (discuss-direct)

---

## Promotion semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Copy, provenance-tagged (recommended) | Project copy stays; global gets promoted_from metadata; re-promote = update | ✓ |
| Move | Tombstone project copy after promote | |

| Option | Description | Selected |
|--------|-------------|----------|
| notes + decisions + conventions (recommended) | Curated sources only; turns/ledgers excluded | ✓ |
| All five sources | Max flexibility, noise risk | |
| Conventions only | Too tight | |

| Option | Description | Selected |
|--------|-------------|----------|
| voss memory forget --global (recommended) | Tombstone by locator, reuses machinery | ✓ |
| Full demote verb | Move back to project — more machinery | |
| None this phase | No way to kill stale global fact | |

---

## Global store location

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.voss/memory/ + VOSS_HOME (recommended) | Mirrors project layout, same MemoryStore code; env override | ✓ |
| XDG data dir | platformdirs dep, asymmetric layout | |
| Config-pointed path | No default; off until configured | |

| Option | Description | Selected |
|--------|-------------|----------|
| Same 100MB cap + vacuum (recommended) | DEFAULT_CAP_BYTES + vacuum --global | ✓ |
| Smaller cap (10MB) | Forces curation | |
| No cap | Unbounded chroma risk | |

---

## Recall blending policy

| Option | Description | Selected |
|--------|-------------|----------|
| Equal RRF, rank decides (recommended) | _rrf_merge fusion, zero knobs, V19 precedent | ✓ |
| Project-favored weight | Multiplier knob | |
| Global as fallback only | Misses outranking global facts | |

| Option | Description | Selected |
|--------|-------------|----------|
| Everywhere recall exists (recommended) | Agent tool + CLI both fuse, [global] labels, single off-switch | ✓ |
| CLI only this phase | Agents blind to cross-repo facts | |
| Agent tool only | Backwards vs V19 unified verb | |

---

## Write guardrails

| Option | Description | Selected |
|--------|-------------|----------|
| Promote verb ONLY (recommended) | Single human write path; curation by construction | ✓ |
| Promote + agent tool w/ approval | More capture, more prompts | |
| Promote + global-note verb | Extra surface | |

---

## Deferred Ideas

- `voss memory note --global` direct capture — revisit on dogfood friction
- Agent-proposed promotion w/ permission prompt — dilutes write guarantee
- External memory file import — V22

## Claude's Discretion

D-09..D-13: root override mechanics, repo-identifier format, promote discovery UX, chroma collection naming, lock verification under global root.
