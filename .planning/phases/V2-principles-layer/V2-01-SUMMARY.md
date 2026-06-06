---
phase: V2-principles-layer
plan: 01
subsystem: config
tags: [principles, frozen-config, yaml-loader, merge, defaults]

requires: []
provides:
  - "PrinciplesConfig (frozen, slots) — immutable ordered (key,text) principle set"
  - "DEFAULT_PRINCIPLES — the six shipped defaults (exact D-02 strings)"
  - "load_principles — loud-on-malformed .voss/principles.yml loader"
  - "merge_principles / resolve_principles — additive-override + explicit-disable merge"
  - "resolve_with_sources — (key,text,source) triples for `voss principles show`"
  - "VossPrinciplesConfigError — clear non-silent config error"
affects: [V2-02 injection, V2-03 show + opacity guard]

tech-stack:
  added: []
  patterns:
    - "Frozen config + loud-error mirroring team.py; .voss/*.yml safe_load mirroring consensus.py but RAISING on malformed (not silent-to-None)"
    - "Key-agnostic merge: zero branching on principle keys/text (opaque text)"

key-files:
  created:
    - voss/harness/principles.py
    - tests/harness/test_principles_config.py

key-decisions:
  - "Defaults live as the DEFAULT_PRINCIPLES constant in-module (no shipped .voss/principles.default.yml) — single source of truth"
  - "principles stored as tuple[tuple[str,str],...] for stable order + frozen immutability"
  - "D-04 conflict rule LOCKED: explicit disable WINS over a redefinition (a key both disabled and given a value is removed)"
  - "Project-only additions appended after defaults in project insertion order; default overrides keep their ordinal position"

patterns-established:
  - "resolve_with_sources is the provenance accessor downstream `show` consumes"

requirements-completed: [VPRIN-01, VPRIN-03, VPRIN-05, VPRIN-06]

duration: 15min
completed: 2026-06-06
---

# Phase V2-01: Principles Layer — Config Substrate Summary

**A frozen, immutable `PrinciplesConfig` with the six shipped defaults, a loud-on-malformed `.voss/principles.yml` loader, and a key-agnostic additive-override + explicit-disable merge with source provenance — the substrate every downstream principles plan consumes.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 / 2 (TDD)
- **Files modified:** 1 source + 1 test created

## Accomplishments

### Task 1 — PrinciplesConfig + six defaults + loader
- `PrinciplesConfig` (`@dataclass(frozen=True, slots=True)`) storing `principles: tuple[tuple[str,str],...]` with `as_mapping()`/`keys()`/`__iter__`/`__len__`.
- `DEFAULT_PRINCIPLES` — the six exact D-02 pairs (diff/evidence/tests/scope/review/reversibility), in-module single source of truth.
- `VossPrinciplesConfigError` mirroring `VossTeamConfigError`.
- `load_principles(cwd)` → `_ProjectLayer`: `yaml.safe_load`; missing file → empty layer (no raise); RAISES on invalid YAML / non-mapping top level / non-string value / bad `disable` list (deliberate divergence from `load_constraints`).

### Task 2 — additive-override + explicit-disable merge
- `_resolve` (shared) → ordered `(key, text, source)`: project-only key ADDS (after defaults, project order); matching key REPLACES text in place (stable ordinal); default REMOVED only via null value or `disable:` list. Conflict: disable beats redefine.
- `merge_principles` / `resolve_principles(cwd)` → `PrinciplesConfig`; `resolve_with_sources(cwd)` → triples for `show`.
- Merge is key-agnostic set algebra — no branching on any principle key/text.

## Verification

- `test_principles_config.py` (15) green: frozen mutation raises; six exact defaults; valid/missing/malformed(YAML, list, non-string, bad-disable) loader paths; no-file→6 defaults; add-key; override-keeps-position; disable-list + null-value removal; disable-wins-over-redefine.
- No new deps (`git status pyproject.toml` clean); `yaml.safe_load` only (no bare `yaml.load`); 170 lines (≥80 min); principle key-strings appear ONLY in `DEFAULT_PRINCIPLES`.

## Notes

- VPRIN-03 immutability is enforced here (frozen config + mutation test); the broader opacity GUARD test lands in V2-03 per the SPEC.
