# Phase V18: Budget-Aware Context Allocator (Token Optimization) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** V18-Budget-Aware Context Allocator (Token Optimization)
**Areas discussed:** Savings surfacing

---

## Gray-area selection

Requirements locked by V18-SPEC.md (8, VOPT-01..08) — discussion limited to HOW (implementation). Four gray areas presented; user selected **one**.

| Area | Description | Selected |
|------|-------------|----------|
| Default posture & config | Packing on-by-default vs opt-in flag; config.toml block vs context.yml | |
| Decay aggressiveness | Default K/M tier sizes; conservative vs aggressive | |
| Savings surfacing | Loudness, ledger location, framing, $ vs tokens | ✓ |
| Digest method scope | Structural-only vs opt-in LLM-summary now | |

---

## Savings surfacing

### Loudness
| Option | Description | Selected |
|--------|-------------|----------|
| /cost line + reuse F3 HUD | `context packed: X→Y (−Z%)` in /cost and the existing F3 HUD | ✓ |
| /cost text only | Line in /cost, no HUD change | |
| Quiet ledger-only | jsonl only, no user-facing line | |

### Ledger location/granularity
| Option | Description | Selected |
|--------|-------------|----------|
| Per-session jsonl | `.voss/sessions/<id>/token-savings.jsonl`, one record/turn | ✓ |
| Project-root cumulative | Growing lifetime `.voss/token-savings.jsonl` | |
| Both: per-session + root rollup | Detail files + rolled-up summary | |

### Framing (honesty)
| Option | Description | Selected |
|--------|-------------|----------|
| Per-turn estimate, labeled ~ | This-turn estimate; reconcile w/ provider usage; no hero number | ✓ |
| Cumulative session total | Running 'saved N / −X%' for the session | |
| Both, both labeled estimate | Per-turn + cumulative | |

### Dollar figure
| Option | Description | Selected |
|--------|-------------|----------|
| Tokens only | Token deltas; avoid $ claims | |
| Tokens + estimated $ | Token delta × model price via F3 cost map / litellm | ✓ |

**User's choice:** /cost line + F3 HUD · per-session jsonl · per-turn labeled estimate · tokens **+ estimated $**.
**Notes:** User overrode the tokens-only recommendation to include an estimated `$` figure. Honesty framing still applies — the `$` is labeled `~estimate`, derived from the token delta × model price (existing litellm cost map), netting out prompt-cache reduced-rate billing so it isn't inflated, and reconciled with real cost when known.

---

## Claude's Discretion

User locked only Savings surfacing; the other three areas default per SPEC (planner may revisit):
- **Default posture & config:** packing ON + conservative profile; `--no-pack` byte-identical; prefer a `[context]` block in existing config over a new file.
- **Decay aggressiveness:** large recent-full tier (conservative K) + late digest→fold cutoff (M); aggressive profiles opt-in; exact K/M from planner informed by the M5 quality gate.
- **Digest method:** structural/extractive only in V18; no LLM-summarization on any path.

## Deferred Ideas

- Opt-in LLM-summarization profile — future phase, post quality-gate proof.
- Project-root cumulative lifetime savings ledger — layer on later with rotation.
- F4 context-heatmap rendering of packed/evicted files — F4 territory.
