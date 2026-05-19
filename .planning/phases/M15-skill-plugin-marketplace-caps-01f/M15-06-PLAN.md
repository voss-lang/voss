---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 06
type: execute
wave: 4
depends_on: ["M15-05"]
files_modified:
  - tests/e2e/test_skill_lifecycle.py
  - tests/harness/skill/test_install.py
  - examples/skills/voss-git-summary/README.md
  - voss/harness/cli.py
autonomous: true
requirements: [SKILL-06]
user_setup: []

must_haves:
  truths:
    - "CI runs the full add → list → run → update → remove cycle against the shipped example bundle and it passes"
    - "The example's committed signature verifies against its committed trusted key"
    - "The gate-only-confinement limitation is documented in voss doctor / voss skill list output and the bundle README"
    - "No central registry/search, OS sandbox, or M9 TUI code was introduced anywhere in the phase"
  artifacts:
    - path: "tests/e2e/test_skill_lifecycle.py"
      provides: "SKILL-06 e2e: full lifecycle cycle against examples/skills/voss-git-summary"
      contains: "def test_fixture_bundle_e2e"
    - path: "examples/skills/voss-git-summary/README.md"
      provides: "Documented gate-only-confinement limitation (OS sandbox deferred)"
      contains: "OS sandbox"
  key_links:
    - from: "tests/e2e/test_skill_lifecycle.py"
      to: "examples/skills/voss-git-summary/"
      via: "trust fixture key → add → list → run → update → remove against the shipped signed bundle"
      pattern: "voss-git-summary"
    - from: "voss/harness/cli.py"
      to: "doctor / skill list output"
      via: "the documented confinement limitation is surfaced to users at runtime"
      pattern: "confinement|sandbox|gate-level"
---

<objective>
Close SKILL-06: the shipped signed example bundle is the end-to-end CI acceptance anchor. Make `tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e` GREEN by exercising the full `trust → add → list → run → update → remove` cycle against `examples/skills/voss-git-summary/` (built + signed in M15-01, now runnable via the M15-02..05 spine), and surface the gate-only-confinement limitation in `voss skill list` / `voss doctor` and the bundle README (SPEC constraint: the OS-sandbox-deferred limitation MUST be documented, not hidden — RESEARCH Pitfall 5).

Purpose: SKILL-06 — CI runs the full cycle against the real shipped bundle and it passes; the signature verifies against the committed trusted key; the documented trust limitation is visible to users.

Output: GREEN e2e fixture-cycle test; documented limitation in runtime output + README; a phase-wide scope-fence audit confirming no central registry / OS sandbox / M9 TUI / GPG / parallel-system code was introduced.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-SPEC.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-VALIDATION.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-05-SUMMARY.md

<interfaces>
Consume (full stack, all prior waves):
- voss skill CLI verbs: add / list / remove / update / trust (M15-05, voss/harness/cli.py skill_group)
- install_bundle / remove_bundle / update_bundle (M15-04)
- verify_manifest / pin_key / key_fingerprint (M15-02)
- scoped_gate / ScopeSpec (M15-03)
- make_voss_skill_handler / load_voss_skills (M15-05)
- the shipped signed bundle examples/skills/voss-git-summary/ + test_signing_key.pub (M15-01)

e2e test shape (tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e):
- isolated XDG via conftest; CliRunner against the top-level voss CLI (or harness skill_group)
- voss skill trust <b64 of test_signing_key.pub> --identity voss-fixture@example.com
- voss skill add ./examples/skills/voss-git-summary  → exit 0
- voss skill list  → output contains "voss-git-summary"
- /skill voss-git-summary (or skill run voss-git-summary)  → produces the skill's declared git-summary output
- voss skill update voss-git-summary  → re-verifies, exit 0 (unchanged upstream verifies)
- voss skill remove voss-git-summary  → exit 0; subsequent list omits it; registry get() is None

Reuse: tests/e2e/runner.py + tests/e2e/conftest.py patterns (existing e2e harness); tests/harness/skill/conftest.py seed_git_repo (the .voss skill summarizes a git tree).
</interfaces>

<analog>
e2e harness: tests/e2e/conftest.py + tests/e2e/runner.py + e.g. tests/e2e/test_extensions_e2e.py (CliRunner full-cycle pattern).
Fixture cycle script: M15-RESEARCH.md §Example Skill Bundle "CI test fixture cycle" (the exact trust→add→list→run→update→remove sequence).
Documented-limitation surface: M15-RESEARCH.md §Pitfall 5 (document in manifest schema, `voss skill list` output, `voss doctor`).
Scope-fence audit source: M15-SPEC.md §Boundaries out-of-scope list + M15-CONTEXT.md <scope_fence> "Do NOT touch / introduce".
</analog>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: e2e full-lifecycle test against the shipped signed bundle</name>
  <read_first>
    - tests/e2e/test_skill_lifecycle.py (the W0 RED e2e test — file being satisfied)
    - tests/e2e/conftest.py + tests/e2e/runner.py (existing e2e CliRunner/full-cycle harness)
    - tests/e2e/test_extensions_e2e.py (closest full-cycle CLI analog)
    - examples/skills/voss-git-summary/ (the shipped signed bundle: manifest.toml, manifest.toml.sig, git_summary.voss, test_signing_key.pub)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Example Skill Bundle CI cycle)
  </read_first>
  <behavior>
    - With the fixture pub key NOT yet trusted, `voss skill add ./examples/skills/voss-git-summary` is REFUSED (exit non-zero, nothing installed) — proves the trust gate is live in the e2e path
    - After `voss skill trust <fixture_pub_b64> --identity voss-fixture@example.com`, the same add succeeds (exit 0)
    - `voss skill list` then contains "voss-git-summary"
    - Running the skill (`skill run voss-git-summary` / `/skill voss-git-summary`) in a seeded git repo produces the skill's declared git-summary output (non-empty, references the repo state)
    - `voss skill update voss-git-summary` against the unchanged committed bundle re-verifies and exits 0
    - `voss skill remove voss-git-summary` exits 0; subsequent `voss skill list` omits it; `default_skill_registry().get("voss-git-summary")` is None
  </behavior>
  <action>
    Implement `test_fixture_bundle_e2e` in `tests/e2e/test_skill_lifecycle.py` driving the exact RESEARCH §Example Skill Bundle CI cycle against `examples/skills/voss-git-summary/`, using the existing e2e CliRunner/runner harness and the isolated-XDG conftest. Read the fixture public key from `examples/skills/voss-git-summary/test_signing_key.pub`. Order: (a) assert add-before-trust is refused; (b) `skill trust`; (c) `skill add ./…`; (d) `skill list` shows it; (e) seed a git repo (conftest `seed_git_repo`) and run the skill, asserting non-empty declared output; (f) `skill update` exits 0 (unchanged upstream verifies — point `source_url`/update at the local bundle path); (g) `skill remove`; (h) `skill list` omits + registry get() is None. Also add a focused `tests/harness/skill/test_install.py` assertion (or reuse an existing test) that the committed `manifest.toml.sig` verifies against the committed `test_signing_key.pub` over `manifest.toml` (the SPEC "signature verifies against its committed trusted key" clause) — this guards against a stale committed signature. No `xfail`/`skip` masking.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e -x -q 2>&1 | tail -3 && python3 -m pytest tests/harness/skill/ -q -m "not live" 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e -x` PASSES (was RED since W0 — the SKILL-06 acceptance anchor)
    - The test asserts add-before-trust is refused AND add-after-trust succeeds (the trust gate is exercised end-to-end, not bypassed)
    - The committed `manifest.toml.sig` verifies against the committed `test_signing_key.pub` (asserted in the suite — stale-signature guard)
    - `pytest tests/harness/skill/ -q -m "not live"` — entire SKILL-01..05 suite still GREEN (no regression from e2e wiring)
    - No `xfail`/unconditional `skip` in `tests/e2e/test_skill_lifecycle.py`
  </acceptance_criteria>
  <done>SKILL-06: CI runs the full trust→add→list→run→update→remove cycle against the shipped signed bundle and it passes; the committed signature verifies against the committed key.</done>
</task>

<task type="auto">
  <name>Task 2: Document the gate-only-confinement limitation + phase scope-fence audit</name>
  <read_first>
    - examples/skills/voss-git-summary/README.md (the limitation note from M15-01 — file being modified/confirmed)
    - voss/harness/cli.py (the `skill list` output + the `doctor` command — file being modified; surface the caveat)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-SPEC.md (§Boundaries out-of-scope)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-CONTEXT.md (<scope_fence> Do NOT touch/introduce list)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Pitfall 5)
  </read_first>
  <action>
    Ensure the gate-only-confinement limitation is stated in THREE surfaces (RESEARCH Pitfall 5): (1) `examples/skills/voss-git-summary/README.md` — confirm/extend the note that scope confinement is gate-level only; direct Python `open()`/`urllib`/subprocess inside the `.voss` skill are NOT confined (OS sandbox deferred to a later phase). (2) `voss skill list` output — include a one-line caveat (e.g. a footer line) noting third-party skills are confined to declared scopes at the harness tool gate ONLY, not at the OS level. (3) `voss doctor` — add a row/line surfacing the same limitation when third-party skills are installed. Then run the phase-wide scope-fence audit: grep the M15-touched tree to confirm NONE of the forbidden items were introduced — no central registry/search backend, no OS sandbox (subprocess-isolation/seccomp/container) module, no M9 TUI code, no GPG, no parallel manifest/enablement system separate from plugins.py, no second permission/gate engine separate from permissions.py/tools.py/sandbox.py, no new `.voss` interpreter. Record the audit result in the SUMMARY.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -li "OS sandbox\|gate.level\|not confined\|gate-only" examples/skills/voss-git-summary/README.md && grep -rn "registry.*search\|seccomp\|import gnupg\|import gpg" voss/harness/skill/ voss/harness/trust.py 2>/dev/null | grep -v "skill_registry\|SkillRegistry" | head -3; echo "FENCE_GREP_EXIT=$?" && python3 -m pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q -m "not live" 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `examples/skills/voss-git-summary/README.md` contains the gate-only-confinement / OS-sandbox-deferred note (grep matches)
    - `voss skill list` output contains a one-line confinement caveat (asserted via CliRunner in a test or grep of the cli.py list handler)
    - `voss doctor` surfaces the limitation when a third-party skill is installed (grep of the doctor handler shows the caveat line)
    - Scope-fence audit clean: no `seccomp`/`import gnupg`/`import gpg`/central-search-registry code in the M15-touched tree (the forbidden-pattern grep returns no real hits; documented in SUMMARY)
    - `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q -m "not live"` — FULL phase suite (SKILL-01..06) GREEN
  </acceptance_criteria>
  <done>The accepted confinement limitation is documented in README + `voss skill list` + `voss doctor`; the phase scope-fence audit confirms no forbidden subsystem was introduced; the full SKILL-01..06 suite is GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| committed fixture sig → CI verify | A stale committed signature must not silently pass; CI verifies the sig at test time |
| user expectation → actual confinement | Users must not believe the gate gives OS-level isolation (it does not) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M15-06-01 | Tampering | Stale committed `manifest.toml.sig` | mitigate | The suite verifies the committed sig against the committed pub key over current manifest bytes every CI run; a drifted manifest fails the build (not a false green) |
| T-M15-06-02 | Spoofing | Misleading confinement claim | mitigate | RESEARCH Pitfall 5: the gate-only/OS-sandbox-deferred limitation is stated in README + `voss skill list` + `voss doctor` — not hidden (SPEC documentation constraint) |
| T-M15-06-03 | Elevation of Privilege | Trust gate bypassed in e2e path | mitigate | The e2e test asserts add-BEFORE-trust is refused and add-AFTER-trust succeeds — proves the trust gate is enforced through the full CLI path, not just unit-mocked |
| T-M15-06-04 | Tampering | Forbidden subsystem sneaks in (scope-fence breach) | mitigate | Phase-wide scope-fence grep audit (no central registry/search, OS sandbox, M9 TUI, GPG, parallel manifest/gate engine, new .voss interpreter); recorded in SUMMARY |
| T-M15-06-SC | Tampering | No new package introduced | accept | e2e + docs only; no package-manager install in this wave |
</threat_model>

<verification>
- `pytest tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e -x -q` GREEN (SKILL-06 anchor)
- `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q -m "not live"` — full SKILL-01..06 suite GREEN
- Committed signature verifies against committed key over current manifest bytes
- Confinement limitation present in README + `voss skill list` + `voss doctor`
- Scope-fence audit clean (no forbidden subsystem in M15-touched tree)
</verification>

<success_criteria>
SKILL-06 satisfied: the shipped signed example bundle passes the full add→list→run→update→remove CI cycle and its signature verifies against the committed key; the accepted gate-only confinement limitation is documented in three user-visible surfaces; the phase introduced no central registry/search, OS sandbox, M9 TUI, GPG, parallel manifest/enablement system, second gate engine, or new .voss interpreter.
</success_criteria>

<output>
Create `.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-06-SUMMARY.md` when done
</output>
