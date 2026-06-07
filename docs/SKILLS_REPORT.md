# Skills / Plugins in the Voss Roadmap — Fit & Necessity

**Date:** 2026-06-06
**Source of truth:** `.planning/docs/ORCHESTRATION_LAYERS.md` (canonical PRD — V-track V0–V12)
**Question:** Where do skills/plugins fit the PRD, and are they needed?

---

## TL;DR

Skills/plugins are **not a primitive** — they collapse into the **Capabilities** primitive (L0) as a *provider / distribution* mechanism. They sit on the **M-track (M15 skills marketplace)**, **not** the V-track (V0–V12), and are **off the critical path**.

**They are not needed for the product thesis or MVP.** Voss already has two extension mechanisms that cover the same ground — **MCP** (tool extension) and **`.voss`** (workflow/coordination reuse). A separate plugin/skill marketplace is largely redundant against those, and an *open* marketplace actively fights the bounded/audited differentiator that IS the product.

---

## 1. Where they fit

Skills/plugins are **not** a 7th primitive. They bucket under **Capabilities** (the L0 toolbelt). PRD touchpoints:

| PRD anchor | Meaning |
|---|---|
| M15 skills marketplace (PRD line 215, Phase 1 "Existing Assets") | An **M-track** phase, not V-track. Distribution layer for capabilities. |
| **CAP-07** | "Unify MCP tools into the same capability registry." Skills, like MCP, are just another capability *source*. |
| **CAP-01 / CAP-02** | Any skill-supplied tool must conform to the normalized `Capability` schema (name, I/O schema, mutability, network, scope, audit behavior). |
| **CAP-09** | Mutating capabilities (incl. plugin-supplied) require permission-gate approval. |

So in the model: **skills/plugins = "extend the toolbelt," folded into Capabilities, off the V0–V12 critical path.**

---

## 2. Are they needed? — No, not for the thesis

The MVP (PRD §11) proves the invariants — EM-can't-invent-roles, scope containment, no budget oversell, independent review, evidence-gated Done, understandable audit — using the **built-in** capability set (`fs`/`git`/`test`/`shell`/`code`/`memory`/`review`). **Zero plugins required.**

Stronger: **Voss already has two extension mechanisms that cover what skills/plugins would do.** A marketplace is largely redundant against them:

| Extension need | PRD answer | Plugin/skill redundant? |
|---|---|---|
| Add a new **tool** | **MCP** (M12 / CAP-07) — unified into the capability registry | Yes — MCP already does this |
| Reuse a **workflow / coordination pattern** | **`.voss`** (V10 — `team` / `gate` / `board` / `review` declared) | Yes — a `.voss` file IS Voss's "skill" |

- A Voss **"skill"** = a `.voss` file (declarative coordination, V10).
- A Voss **"plugin"** = an MCP server (tool provider, M12).

Both are already planned and both are held to the Capability schema + permission gate + audit.

---

## 3. Why an open marketplace fights the thesis

- **CAP-02** demands every capability declare scope/mutability/network/audit behavior. A marketplace of unvetted third-party skills is the hardest thing to hold to that contract.
- **§9 risks** ("budget system leaky," scope violations) + **§10 differentiator** (*bounded, audited, reviewed*). A large plugin ecosystem is the **opposite** selling point — it's the sprawl other AI coding tools have and that Voss is explicitly positioned against.
- More capability providers = a larger trust surface on the **capability cage** — the exact boundary that is the product.

---

## 4. Recommendation

- **Defer M15 (skills marketplace) — likely cuttable for v1.** Not a primitive, not on V0–V12.
- **Extensibility is already covered:** MCP for tools, `.voss` for workflows.
- **Revisit M15 only when** (a) the V1 capability schema (CAP-01..10) is solid **and** (b) there is real external demand to add capabilities Voss doesn't ship.
- **Even then,** frame it as "a capability provider conforming to the `Capability` schema + permission gate + audit" — **not** a free-for-all plugin store.

**Net:** skills/plugins are a Capabilities-primitive nicety, redundant with MCP + `.voss`, and a marketplace trades the audit-trust differentiator for ecosystem sprawl. Not needed on the roadmap.

---

*Cross-refs: `.planning/docs/ORCHESTRATION_LAYERS.md` §4.1 (primitives), §4.3 (track→primitive map), Phase 1 (CAP-01..10), Phase 10 (`.voss` language), §9 (risks), §10 (positioning), §11 (MVP). M-track M12 (MCP bridge), M15 (skills marketplace) in `.planning/ROADMAP.md`.*
