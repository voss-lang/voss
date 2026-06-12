# Phase V21 — Minted Requirements (VGMEM-*)

**Minted:** 2026-06-11 (plan time — discuss-direct path, no SPEC; IDs derived from CONTEXT D-01..D-08 + ROADMAP V21 goal).
**Traceability:** every VGMEM ID below is covered by exactly one implementation plan (V21-02..04); V21-01 is the Wave-0 RED scaffold that pins all of them.

| Req ID | Source decisions | Description | Plan |
|--------|------------------|-------------|------|
| VGMEM-01 | D-04, D-09 | `MemoryStore.root_override` param + `_global_memory_root()` (VOSS_HOME / ~/.voss, HOME-less graceful) + `make_global_store()` factory + `_repo_id()` + layout mirror | V21-02 |
| VGMEM-02 | D-08 | Global store unreachable from any write tool — `attach_memory_tools` global_store is read-only, never passed to `memory_remember`/`write_*` (by construction + test) | V21-04 |
| VGMEM-03 | D-01, D-02, D-10, D-11 | `voss memory promote <locator>` — copy + `promoted_from` provenance + dedup-on-repromote + turn/ledger rejection + `--list` discovery; 0o600 file perms | V21-03 |
| VGMEM-04 | D-03 | `voss memory forget <locator>` dual-scope (project default, `--global` tombstones global store) | V21-03 |
| VGMEM-05 | D-05, D-13 | `voss memory vacuum --global` + blocking-lock concurrency safety on promote | V21-03 |
| VGMEM-06 | D-06, D-07 | Dual-store RRF fusion in agent `memory_recall` tool, `[global]` label, namespaced locators; 3 `attach_memory_tools` call sites wired | V21-04 |
| VGMEM-07 | D-07 | `[memory] global = false` config off-switch (config.toml) — skips global store init entirely | V21-02 |
| VGMEM-08 | D-06, D-07 | `voss recall` CLI extended with `[global]` corpus as a third RRF ranking (extends as-built V19-04 recall_cmd) | V21-04 |

**Discretion notes:**
- D-12 (chroma collection convention): no dedicated requirement — same collection name/embedding-model convention as project store, satisfied by construction via the layout mirror (VGMEM-01). Dim-mismatch between stores is acceptable (rank-based fusion).

**Cross-phase dependency:** V21 executes ONLY AFTER V19 ships. VGMEM-08 extends the V19-04 `recall_cmd` seam (does not reimplement it).
