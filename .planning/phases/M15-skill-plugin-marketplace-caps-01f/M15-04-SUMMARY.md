---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 04
subsystem: harness
tags: [skill-marketplace, fetch, install, lifecycle, manifest-extension]

requires: ["M15-02", "M15-03"]
provides:
  - PluginManifest extended with skill/scope/trust/install fields (backward compatible)
  - fetch_bundle: git clone (HTTPS only) / local dir / archive → staging dir
  - install_bundle with staging→verify→atomic-copy discipline
  - remove_bundle and update_bundle with re-verification
  - update failure leaves prior version intact
  - load_plugins discovers subdir bundles (<id>/manifest.toml)
affects:
  - voss/harness/plugins.py
  - voss/harness/skill/fetch.py
  - voss/harness/skill/install.py
  - tests/harness/skill/test_install.py
  - tests/harness/skill/test_lifecycle.py
  - tests/harness/skill/test_trust.py

tech-stack:
  added: []
  patterns: [staging-verify-copy, atomic-swap-bak, local-first-resolution, https-enforcement]

key-files:
  created:
    - voss/harness/skill/fetch.py
    - voss/harness/skill/install.py
  modified:
    - voss/harness/plugins.py
    - tests/harness/skill/test_install.py
    - tests/harness/skill/test_lifecycle.py
    - tests/harness/skill/test_trust.py

key-decisions:
  - "Local path resolution takes precedence over GitHub shorthand (Pitfall 6)."
  - "Staging dir placed under user_plugin_dir().parent/'._staging' for same-filesystem atomic rename (Pitfall 3)."
  - "verify_manifest called BEFORE any copytree to install dir (Pitfall 1)."
  - "TOFU defaults OFF — unknown keys are refused with fingerprint + instructions printed."
  - "git:// and http:// transports rejected; HTTPS enforced for git clone."
  - "Update atomic swap: current→.bak, new→current, rm .bak; OSError restores from .bak."
  - "W0 RED test stubs rewritten to exercise library functions directly (CLI wiring deferred to M15-05)."

patterns-established:
  - "staging→trust-gate→verify→copy install discipline."
  - "SkillTrustError exception for all trust/verification failures."
  - "Path traversal jail check on extracted bundle entries (T-M15-04-05)."
  - "_write_install_metadata records source_url in installed manifest for update re-fetch."

requirements-completed: [SKILL-01, SKILL-05]

duration: 15min
completed: 2026-05-20
---

# Phase M15-04: Skill Install Pipeline Summary

**Bundles now fetch, verify, install, remove, and update through a staging→trust→verify→copy pipeline into the existing plugin discovery path.**

## Performance

- **Duration:** 15 min
- **Tasks:** 3
- **Files created:** 2
- **Files modified:** 4

## Accomplishments

- Extended `PluginManifest` with 12 new fields (voss_entry, skill_id, skill_mutating, scope_tools, scope_fs, scope_net, sig_file, author_identity, source_url, bundle_dir) — all with defaults, zero regression on existing manifests.
- Extended `_read_manifest` to defensively read `[skill]`, `[scopes]`, `[trust]`, `[install]` TOML tables using existing coercion patterns.
- Extended `load_plugins` to discover installed bundle subdirs (`<root>/<id>/manifest.toml`) alongside existing flat `*.toml` discovery.
- Implemented `fetch_bundle` with local-path-first resolution (Pitfall 6), GitHub shorthand→HTTPS URL, HTTPS-only git clone (git:// and http:// rejected), and archive extraction.
- Implemented `install_bundle` with staging→trust-gate→verify→copy: nothing written to plugin dir until verify_manifest returns (True, _).
- Implemented `remove_bundle` (rmtree + set_plugin_enabled(False)).
- Implemented `update_bundle` with re-fetch, re-verify, atomic swap via .bak, and OSError restore.
- Updated W0 RED test stubs to exercise library directly (CLI wiring deferred to M15-05).

## Task Commits

1. **Task 1: PluginManifest extension** — `67d0559` (feat)
2. **Task 2: fetch.py + install.py + test rewrites** — `e53bbe9` (test)
3. **Task 3: lifecycle + W1 trust test fixes** — `ddb1dfb` (fix)

## Verification

- `pytest tests/harness/skill/test_install.py tests/harness/skill/test_lifecycle.py -x -m "not live"` — 7 tests GREEN (SKILL-01 + SKILL-05)
- `pytest tests/harness/test_extensions.py -x` — 4 tests GREEN (no regression)
- `pytest tests/harness/skill/ -q -m "not live" --ignore=tests/harness/skill/test_registry.py` — 12 tests GREEN
- Only `test_registry.py::test_voss_skill_dispatch` remains RED (SKILL-02 adapter = M15-05 wave, expected)
- Untrusted-key install writes NOTHING to plugin dir (test_untrusted_key_refuses)
- Tampered-manifest install writes NOTHING (test_tampered_manifest_refuses)
- Tampered-upstream update leaves prior version intact (test_update_tamper_leaves_prior_intact)
- `grep verify_manifest voss/harness/skill/install.py` confirms verify precedes copytree
- `grep "git://\|http://" voss/harness/skill/fetch.py` confirms both rejected
