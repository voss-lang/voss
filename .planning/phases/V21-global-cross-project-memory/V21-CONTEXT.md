# Phase V21: Global Cross-Project Memory - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning
**Note:** No SPEC for this phase (discuss-direct path). Requirements VGMEM-* to be minted at plan time from the decisions below + ROADMAP entry. D-01..D-08 are USER-LOCKED via discuss-phase; D-09+ are Claude-discretion defaults.

<domain>
## Phase Boundary

V21 gives facts that transcend a single repo — operator preferences, recurring conventions, cross-repo patterns — a durable curated home (`~/.voss/memory/global/`-style store) and surfaces them in every recall path with `[global]` labels. One new write path (`voss memory promote`), one reverse path (`voss memory forget --global`), RRF fusion into existing recall. **Reuse-not-rebuild:** second `MemoryStore` instance with a root override (memory_store.py:75 currently hardcodes `cwd/.voss/memory`), existing `_rrf_merge` + source-label machinery from V19's cross-corpus CLI, existing tombstone + vacuum + cap machinery. No new store type, no new schema, no cloud.

</domain>

<decisions>
## Implementation Decisions

### Promotion Semantics (USER-LOCKED)
- **D-01 — Copy, provenance-tagged:** promote copies the memory into the global store with `promoted_from: <repo-identifier>/<locator>` metadata; project copy untouched. Re-promoting the same locator UPDATES the existing global entry (dedup via provenance match), never duplicates.
- **D-02 — Promotable sources = notes, decisions, conventions only:** turns and ledgers are session/project-bound and excluded. `voss memory promote <locator>` rejects turn/ledger locators with a clear error.
- **D-03 — Reverse = `voss memory forget --global <locator>`:** tombstones the global entry using existing tombstone machinery. No demote-back-to-project verb (copy semantics make it unnecessary).

### Store Location & Lifecycle (USER-LOCKED)
- **D-04 — Path = `~/.voss/memory/` with `VOSS_HOME` override:** global root mirrors the project `.voss/memory/` layout exactly (same sources dirs, chroma/, .locks/, tombstones) so the same `MemoryStore` code serves both. `VOSS_HOME` env var overrides the `~/.voss` base (tests, multi-profile). No XDG/platformdirs dependency.
- **D-05 — Same 100MB cap + vacuum:** reuse `DEFAULT_CAP_BYTES`; `voss memory vacuum --global` points existing vacuum at the global root. No new curation machinery.

### Recall Blending (USER-LOCKED)
- **D-06 — Equal RRF, rank decides:** global ranking + project ranking fused via existing `_rrf_merge` (rank-based, corpus-agnostic — V19 cross-corpus precedent). No weighting knobs, no fallback-only mode.
- **D-07 — Surfaces everywhere recall exists:** agent-side memory recall tool AND `voss recall` CLI both fuse global hits, labeled `[global]`. Single config off-switch `[memory] global = false` disables global participation everywhere at once.

### Write Guardrails (USER-LOCKED)
- **D-08 — Promote verb is the ONLY write path to global:** no agent tool may write the global store; no auto-capture; no session turns ever land there. Curation guaranteed by construction (roadmap "never auto-promoted" honored literally).

### Claude's Discretion (planner may revisit within decisions above)
- **D-09 — MemoryStore root override:** add `root_override: Path | None = None` (or equivalent factory) to `MemoryStore` rather than subclassing; `self.root = root_override or cwd / ".voss" / "memory"`. Global instance never binds a session for turn-writing (D-02/D-08 make turn paths unreachable anyway — assert defensively).
- **D-10 — Repo identifier in provenance:** use the project root's basename + short hash of absolute path (stable, readable, collision-resistant) — planner may pick exact format; must be deterministic per repo.
- **D-11 — Promote UX:** `voss memory promote <locator>` under the existing `voss memory` click group (memory_cli.py:18); locator format = the composite ID convention already used by `make_id` (`<source>:<locator>`); `voss memory promote --list` (or reuse of existing listing) acceptable for discovery — planner decides minimal discovery surface.
- **D-12 — Chroma collection in global store:** same collection name/convention as project store (layout mirror per D-04); embedding model follows same `default_embedding_model` config — dim-mismatch between stores is acceptable (rankings fused by rank, not vector space).
- **D-13 — Concurrency:** global store shared across simultaneous voss sessions in different repos — existing portalocker `.locks/` machinery must guard promote/forget/vacuum writes (already in MemoryStore; verify lock paths resolve under global root).

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase V21 entry (goal, out-of-scope: no cloud sync, no auto-promotion heuristics, no global code index)
- `voss/harness/memory_store.py` — MemoryStore (root at L75 to parameterize), `_rrf_merge` (L426), tombstones, vacuum/cap, portalocker locks, `make_id` composite IDs
- `voss/harness/memory_cli.py` — `voss memory` click group (L18) for `promote` / `forget --global` / `vacuum --global`
- `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md` + `V19-SPEC.md` — D-09 unified recall + source-label conventions V21 extends; V19 plans define the CLI fusion code path V21 plugs into
- `voss_runtime/memory/semantic.py` — chroma wrapper (persist_dir parameterization)

</canonical_refs>

<specifics>
## Specific Ideas

- Hit labeling: `[global]` prefix consistent with V19's `[code]`/`[memory]` labels — three-corpus display in `voss recall` output.
- `[memory] global = false` must also skip global store init entirely (no chroma open, no lock churn) — not just filter hits.

</specifics>

<deferred>
## Deferred Ideas

- Direct global capture verb (`voss memory note --global`) — rejected for this phase; promote-only write path. Revisit if promote friction observed in dogfood.
- Agent-proposed promotion with permission prompt — same; would dilute D-08 guarantee.
- Migration/import of existing external memory files — V22 territory (external memory & docs ingest).

</deferred>

---

*Phase: V21-global-cross-project-memory*
*Context gathered: 2026-06-11*
*Depends on: V19 (unified recall surface + source labels)*
