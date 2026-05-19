---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 01
subsystem: harness
tags: [skill-marketplace, ed25519, validation, scaffold]

requires: []
provides:
  - cryptography pinned as an explicit direct runtime dependency in pyproject.toml
  - Ed25519-signed example bundle examples/skills/voss-git-summary/ with manifest, program, keypair, and signature
  - author-side standalone signer scripts/sign_fixture_bundle.py
  - complete RED test suite in tests/harness/skill/ and tests/e2e/ mapping all 12 validation requirements
affects:
  - pyproject.toml
  - tests/harness/skill/conftest.py

tech-stack:
  added: [cryptography>=43.0.3]
  patterns: [scaffold, signature-verification, test-isolation]

key-files:
  created:
    - tests/harness/skill/__init__.py
    - tests/harness/skill/conftest.py
    - tests/harness/skill/test_trust.py
    - tests/harness/skill/test_scope.py
    - tests/harness/skill/test_install.py
    - tests/harness/skill/test_registry.py
    - tests/harness/skill/test_lifecycle.py
    - tests/e2e/test_skill_lifecycle.py
    - scripts/sign_fixture_bundle.py
    - examples/skills/voss-git-summary/git_summary.voss
    - examples/skills/voss-git-summary/manifest.toml
    - examples/skills/voss-git-summary/README.md
    - examples/skills/voss-git-summary/test_signing_key
    - examples/skills/voss-git-summary/test_signing_key.pub
    - examples/skills/voss-git-summary/manifest.toml.sig
  modified:
    - pyproject.toml

key-decisions:
  - "cryptography is promoted from a transitive dependency to a direct runtime dependency (pinned >= 43.0.3) in pyproject.toml for explicit security imports."
  - "The committed Ed25519 keypair for the git-summary fixture has zero production security value (CI test-only key) and is explicitly documented as such in the README."
  - "All target imports (e.g. voss.harness.trust, voss.harness.skill.*) are driven natively inside the tests via clean try/except guards, so tests collect successfully but fail RED as expected."

patterns-established:
  - "Detached signature verification pattern using raw 32-byte Base64 Ed25519 keys."
  - "Strict environment sandboxing in tests by monkeypatching both XDG_STATE_HOME and XDG_CONFIG_HOME under a unique tmp_path."

requirements-completed: [SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06]

duration: 20min
completed: 2026-05-19
---

# Phase M15-01: Skill Marketplace Wave 0 Scaffold Summary

**The harness now features the complete security-first validation contract and signed example bundle for the forthcoming Skill Plugin Marketplace.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-05-19T18:10:28Z
- **Completed:** 2026-05-19T18:11:55Z
- **Tasks:** 3
- **Files created/modified:** 16

## Accomplishments

- Added `"cryptography>=43.0.3"` directly to `pyproject.toml`'s dependencies.
- Created `tests/harness/skill/conftest.py` with full XDG config/state sandboxing and mock LLM stream provider fixtures.
- Created a genuine Ed25519-signed test skill bundle (`examples/skills/voss-git-summary/`) containing a valid `.voss` program, a signed `manifest.toml`, private/public keypair, and a hex detached signature.
- Wrote `scripts/sign_fixture_bundle.py`, an author-side signing script that generates keypairs and registers signatures over manifest bytes.
- Scaffolded all **12 RED tests** across 6 files inside `tests/harness/skill/` and `tests/e2e/`, representing every requirement from `M15-VALIDATION.md`.

## Task Commits

1. **Task 1: Pin cryptography and conftest scaffold** - `e12bf37` (feat)
2. **Task 2: Author the RED test suite** - `92d8a4c` (test)
3. **Task 3: Build and sign example bundle** - `bf79a32` (feat/docs)

## Verification

- `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py --collect-only` exits **0** and collects exactly **12** tests.
- `pytest tests/harness/skill/` successfully runs all tests and fails **RED** with `Failed: RED: missing ...` as expected (no collection errors).
- `python3 scripts/sign_fixture_bundle.py` is fully idempotent and generates verifying keypairs.
- Inline cryptography Ed25519 signature checks verify the manifest; flipping a single byte successfully causes verification to raise `InvalidSignature`.
- `voss check examples/skills/voss-git-summary/git_summary.voss` passes compiled static checks cleanly with exit code **0**.
