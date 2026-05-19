---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - pyproject.toml
  - tests/harness/skill/__init__.py
  - tests/harness/skill/conftest.py
  - tests/harness/skill/test_trust.py
  - tests/harness/skill/test_scope.py
  - tests/harness/skill/test_install.py
  - tests/harness/skill/test_registry.py
  - tests/harness/skill/test_lifecycle.py
  - tests/e2e/test_skill_lifecycle.py
  - examples/skills/voss-git-summary/manifest.toml
  - examples/skills/voss-git-summary/git_summary.voss
  - examples/skills/voss-git-summary/README.md
  - examples/skills/voss-git-summary/manifest.toml.sig
  - examples/skills/voss-git-summary/test_signing_key
  - examples/skills/voss-git-summary/test_signing_key.pub
  - scripts/sign_fixture_bundle.py
autonomous: false
requirements: [SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06]
user_setup: []

must_haves:
  truths:
    - "Every M15-VALIDATION Requirement→Test command resolves to a real test that FAILS (RED) because the implementation does not exist yet"
    - "cryptography is an explicit direct runtime dependency in pyproject.toml (not relied on transitively)"
    - "A real Ed25519-signed example bundle exists in-repo with a committed test keypair and a valid detached signature over its manifest"
  artifacts:
    - path: "tests/harness/skill/conftest.py"
      provides: "Shared FakeProvider + seed_git_repo + XDG isolation fixtures for the skill suite"
      min_lines: 30
    - path: "tests/harness/skill/test_trust.py"
      provides: "SKILL-03 RED tests (tamper / unknown-key / trust-then-add)"
      contains: "def test_tampered_manifest_refused"
    - path: "tests/harness/skill/test_scope.py"
      provides: "SKILL-04 RED tests (out-of-scope blocked / in-scope allowed)"
      contains: "def test_out_of_scope_blocked"
    - path: "tests/harness/skill/test_install.py"
      provides: "SKILL-01 RED tests (add local / add github)"
      contains: "def test_add_local"
    - path: "tests/harness/skill/test_registry.py"
      provides: "SKILL-02 RED tests (dispatch / unknown-not-found)"
      contains: "def test_voss_skill_dispatch"
    - path: "tests/harness/skill/test_lifecycle.py"
      provides: "SKILL-05 RED tests (remove / update-tamper-leaves-prior-intact)"
      contains: "def test_update_tamper_leaves_prior_intact"
    - path: "tests/e2e/test_skill_lifecycle.py"
      provides: "SKILL-06 RED e2e fixture-cycle test"
      contains: "def test_fixture_bundle_e2e"
    - path: "examples/skills/voss-git-summary/manifest.toml"
      provides: "Signed example skill bundle manifest with [skill]/[scopes]/[trust]/[install] tables"
      contains: "git_summary.voss"
    - path: "examples/skills/voss-git-summary/manifest.toml.sig"
      provides: "Valid Ed25519 detached signature (hex) over manifest.toml"
      min_lines: 1
  key_links:
    - from: "scripts/sign_fixture_bundle.py"
      to: "examples/skills/voss-git-summary/manifest.toml.sig"
      via: "Ed25519PrivateKey.sign(manifest_bytes).hex() written to .sig"
      pattern: "Ed25519PrivateKey"
    - from: "tests/harness/skill/test_trust.py"
      to: "voss.harness.trust"
      via: "import of not-yet-existing trust module (RED until W1)"
      pattern: "from voss.harness.trust import|import voss.harness.trust"
---

<objective>
Wave 0 scaffold for the skill marketplace. Stand up the full RED test suite that every later wave must turn green, pin `cryptography` as an explicit direct dependency, and ship the real signed example bundle (manifest + `.voss` program + committed test keypair + valid Ed25519 detached signature) that is the e2e acceptance anchor for SKILL-06.

Purpose: Establish the Nyquist feedback contract before any implementation. Per M15-VALIDATION.md, all 12 Requirement→Test rows must resolve to real failing tests so each subsequent wave has a falsifiable green target. The signed fixture must be a genuine signed bundle (RESEARCH §Example Skill Bundle, CONTEXT specifics), not an ad-hoc stub.

Output: `tests/harness/skill/` suite (RED), `tests/e2e/test_skill_lifecycle.py` (RED), `examples/skills/voss-git-summary/` signed bundle, `scripts/sign_fixture_bundle.py` author-side signer, `cryptography` in pyproject `dependencies`.
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
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-PATTERNS.md

<interfaces>
<!-- Contracts the RED tests assert against. These modules do NOT exist yet — that is why the suite is RED. -->
<!-- Final module/symbol names are these; later waves implement to match. -->

Target import surface the suite expects (do NOT implement here — tests must RED):
- `voss.harness.trust`         → verify_manifest(manifest_path: Path, sig_path: Path, *, trusted_keys: dict) -> tuple[bool, str]; trust_store_path() -> Path; pin_key(identity, pub_key_b64, *, tofu=False) -> Path; is_key_trusted(pub_key_b64) -> bool
- `voss.harness.skill.scope`   → ScopeSpec dataclass (tools/fs/net); scoped_gate(spec, base_gate) -> PermissionGate; scope_to_mode(tools_value) -> Mode
- `voss.harness.skill.fetch`   → fetch_bundle(source: str, staging_dir: Path) -> Path
- `voss.harness.skill.install` → install_bundle(source, *, cwd) -> str; remove_bundle(skill_id, *, cwd) -> None; update_bundle(skill_id, *, cwd) -> None
- `voss.harness.skill.adapter` → make_voss_skill_handler(voss_path: Path, spec: ScopeSpec) -> SkillHandler

Existing surfaces the tests reuse (these DO exist):
From voss/harness/skill_registry.py:
```python
SkillHandler = Callable[[Any, list[str]], None]
@dataclass(frozen=True)
class SkillEntry: id: str; description: str; handler: SkillHandler; mutating: bool = False
class SkillRegistry: register(entry); get(skill_id) -> SkillEntry | None; ids() -> list[str]
def default_skill_registry() -> SkillRegistry
```
From voss/harness/permissions.py:
```python
Mode = Literal["plan", "edit", "auto"]
@dataclass class PermissionGate: mode: Mode = "edit"; auto_yes: bool = False
  def check(tool_name, args, *, is_mutating=False, is_network=False) -> tuple[bool, str]
```
From voss/harness/plugins.py: user_plugin_dir(); project_plugin_dir(cwd); set_plugin_enabled(id, bool); load_plugins(cwd, ...)
</interfaces>

<analog>
Test conftest analog: tests/skills/conftest.py (FakeProvider lines ~85-157, seed_git_repo ~57-77, autouse isolated_state ~51-54, __all__ re-export ~34-48).
CLI install test analog: tests/harness/test_extensions.py (CliRunner + monkeypatch XDG_CONFIG_HOME + tmp plugin dir, lines ~76-122).
Dispatch test analog: tests/skills/test_skills_smoke.py (skill run() + gate-mode assertion, lines ~43-81).
.voss example analog: voss/harness/skills/voss/summarize-diff.voss (structure + "# NOT the runtime exec path" comment + ctx(budget:) form).
Ed25519 signing: M15-RESEARCH.md §Code Examples "Verified: cryptography Ed25519" (key gen / sign / verify, VERIFIED 2026-05-19).
</analog>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pin cryptography as a direct dependency + scaffold the skill test package</name>
  <read_first>
    - pyproject.toml (the `[project] dependencies` list — file being modified)
    - tests/skills/conftest.py (FakeProvider, seed_git_repo, isolated_state — copy-with-adjustments analog)
    - tests/harness/test_extensions.py (CliRunner + monkeypatch XDG pattern)
  </read_first>
  <action>
    Add `"cryptography>=43.0.3"` to the `[project] dependencies` array in pyproject.toml. RATIONALE: M15 directly imports `cryptography.hazmat.primitives.asymmetric.ed25519`; it is currently only a TRANSITIVE dep (present in uv.lock at 48.0.0, installed 43.0.3, absent from pyproject `dependencies`) — depending on a transitive dep for a security-critical import is fragile and MUST be made explicit (this corrects RESEARCH's "already a runtime dep" claim, which referred to the transitive presence).
    Create `tests/harness/skill/__init__.py` (empty package marker).
    Create `tests/harness/skill/conftest.py` adapting `tests/skills/conftest.py`: re-export `FakeProvider`, `seed_git_repo`, `Plan`, `PermissionGate`, `PlainRenderer`, `make_toolset`; keep the `autouse isolated_state` fixture that monkeypatches `XDG_STATE_HOME` AND additionally `XDG_CONFIG_HOME` to `tmp_path` subdirs so the trust store / plugin dir / enablement file are all per-test isolated. Add a `signed_fixture_bundle` fixture that returns the path to `examples/skills/voss-git-summary/` (built in Task 3) for the install/lifecycle/e2e tests.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q 'cryptography>=' pyproject.toml && python3 -c "import ast,sys; ast.parse(open('tests/harness/skill/conftest.py').read())" && python3 -m pytest tests/harness/skill/ --collect-only -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'cryptography>=' pyproject.toml` ≥ 1 AND the match is inside the `[project] dependencies` array (not optional-deps/dev)
    - `tests/harness/skill/__init__.py` exists (0-byte or comment-only acceptable)
    - `tests/harness/skill/conftest.py` parses, exposes `FakeProvider` and `seed_git_repo`, and its `isolated_state` fixture sets both `XDG_STATE_HOME` and `XDG_CONFIG_HOME` under `tmp_path`
    - `pytest tests/harness/skill/ --collect-only` exits 0 (collection succeeds even though no test files yet — conftest imports cleanly)
  </acceptance_criteria>
  <done>cryptography is an explicit direct dependency; the skill test package collects with an isolated conftest mirroring tests/skills/conftest.py.</done>
</task>

<task type="auto">
  <name>Task 2: Author the RED test suite for SKILL-01..06</name>
  <read_first>
    - tests/harness/skill/conftest.py (the fixtures authored in Task 1 — file being modified context)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-VALIDATION.md (Requirement→Test Map — exact test names and commands are pinned here)
    - tests/skills/test_skills_smoke.py (gate-mode assertion pattern, lines ~43-81)
    - tests/harness/test_extensions.py (CliRunner invoke + exit_code/output asserts)
  </read_first>
  <action>
    Create six test files with the EXACT function names from the M15-VALIDATION Requirement→Test Map so every row's automated command resolves:
    - `tests/harness/skill/test_trust.py`: `test_tampered_manifest_refused` (SKILL-03 — flip a manifest byte, assert verify_manifest returns `(False, ...)` and that install raised + nothing landed in plugin dir), `test_unknown_key_refused` (SKILL-03 — key not in trust store ⇒ refuse with non-zero / `(False,...)`), `test_trust_then_install_succeeds` (SKILL-03 — after `pin_key`, same install passes).
    - `tests/harness/skill/test_scope.py`: `test_out_of_scope_blocked` (SKILL-04 — a `read-only`-scoped skill's `fs_write`/`shell_run` is denied by the scoped gate), `test_in_scope_allowed` (SKILL-04 — an in-scope `fs_read` is permitted).
    - `tests/harness/skill/test_install.py`: `test_add_local` (SKILL-01 — `voss skill add ./<fixture>` then `voss skill list` shows it, via CliRunner), `test_add_github` marked `@pytest.mark.skipif`-able / `-m "not live"` (SKILL-01 — GitHub shorthand resolves; structure it so `-m "not live"` excludes the network call but still asserts shorthand→URL transformation).
    - `tests/harness/skill/test_registry.py`: `test_voss_skill_dispatch` (SKILL-02 — after install, `skill_registry.get(<id>)` resolves and handler runs producing the declared effect), `test_unknown_skill_not_found` (SKILL-02 — before install the id is `None`).
    - `tests/harness/skill/test_lifecycle.py`: `test_remove` (SKILL-05 — after `remove`, list omits + registry `get` is None), `test_update_tamper_leaves_prior_intact` (SKILL-05 — update against a tampered upstream fails and the prior installed version still resolves+runs).
    - `tests/e2e/test_skill_lifecycle.py`: `test_fixture_bundle_e2e` (SKILL-06 — trust fixture key → add → list shows → run produces output → update succeeds → remove → list omits, against `examples/skills/voss-git-summary/`).
    Tests import the not-yet-existing target modules from the `<interfaces>` block; that import failure / behavior gap is what makes them RED. Use `pytest.fail("RED: <module> not implemented")` only where an import-guard is needed so collection still succeeds. Do NOT use `xfail`/`skip` to mask — failures must be real (M13 scaffold-ad-lib lesson: scaffold bodies must drive the REAL pinned API from `<interfaces>`, never a fictional one).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py --collect-only -q 2>&1 | grep -E "12 tests|test_tampered_manifest_refused|test_out_of_scope_blocked|test_fixture_bundle_e2e" | head -5 && python3 -m pytest tests/harness/skill/test_trust.py -x -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - Every command in the M15-VALIDATION Requirement→Test Map resolves: `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py --collect-only` lists exactly the 12 named tests
    - `pytest tests/harness/skill/test_trust.py -x` exits non-zero (RED — `voss.harness.trust` does not exist / behavior unmet)
    - No `@pytest.mark.xfail` and no unconditional `@pytest.mark.skip` in any of the six files (grep: `grep -rn "xfail\|mark.skip" tests/harness/skill/ tests/e2e/test_skill_lifecycle.py | grep -v "skipif.*live\|not live"` returns nothing)
    - Test bodies reference the exact symbol names from `<interfaces>` (e.g. `verify_manifest`, `scoped_gate`, `install_bundle`) — not invented names
  </acceptance_criteria>
  <done>All 12 Requirement→Test rows resolve to real RED tests driving the pinned target API; no masking.</done>
</task>

<task type="auto">
  <name>Task 3: Build + Ed25519-sign the example skill bundle and author-side signer</name>
  <read_first>
    - voss/harness/skills/voss/summarize-diff.voss (.voss skill structure + "# NOT the runtime exec path" comment + ctx(budget:) form)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Example Skill Bundle layout + §Code Examples "Verified: cryptography Ed25519" sign/keygen)
    - voss/cli.py (the `check` command — generated bundle .voss MUST pass `voss check`)
  </read_first>
  <action>
    Create `scripts/sign_fixture_bundle.py`: a standalone author-side signer (NOT the install path) that generates a test Ed25519 keypair if absent, writes `examples/skills/voss-git-summary/test_signing_key` (raw 32-byte private key, base64) + `test_signing_key.pub` (raw 32-byte public key, base64), reads `manifest.toml` bytes, computes `Ed25519PrivateKey.sign(manifest_bytes)`, and writes the hex signature to `manifest.toml.sig`. Idempotent: re-running re-signs the current manifest with the existing key.
    Create the bundle `examples/skills/voss-git-summary/`:
    - `git_summary.voss`: a small read-only skill that summarizes the working tree (git status/diff). Include the "# NOT the runtime exec path" companion comment; use `ctx(budget: N tokens)` for the agentic summary call so it passes `voss check`.
    - `manifest.toml`: `id="voss-git-summary"`, `name`, `description`, `version`, `author_identity="voss-fixture@example.com"`; `[skill] entry="git_summary.voss" id="voss-git-summary" mutating=false`; `[scopes] tools="read-only" fs="cwd" net=false`; `[trust] sig_file="manifest.toml.sig" pub_key="<b64 of test_signing_key.pub>"`; `[install] source_url="" installed_at=""` (placeholders, install path fills these).
    - `README.md`: one-paragraph human description + an explicit "SECURITY: the committed `test_signing_key` is a CI fixture key with no production value; scope confinement is gate-level only — direct Python `open()`/`urllib` inside the .voss subprocess is NOT confined (OS sandbox deferred)" note.
    Run the signer to produce `test_signing_key`, `test_signing_key.pub`, `manifest.toml.sig`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 scripts/sign_fixture_bundle.py && python3 -c "
import base64, pathlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
b=pathlib.Path('examples/skills/voss-git-summary')
pub=Ed25519PublicKey.from_public_bytes(base64.b64decode((b/'test_signing_key.pub').read_text().strip()))
pub.verify(bytes.fromhex((b/'manifest.toml.sig').read_text().strip()), (b/'manifest.toml').read_bytes())
print('SIG OK')" && python3 -m voss.cli check examples/skills/voss-git-summary/git_summary.voss 2>&1 | tail -2</automated>
  </verify>
  <acceptance_criteria>
    - `python3 scripts/sign_fixture_bundle.py` exits 0 and is idempotent (second run leaves a valid sig)
    - The committed `manifest.toml.sig` verifies against `test_signing_key.pub` over `manifest.toml` bytes (the inline check prints `SIG OK`)
    - Flipping one byte of `manifest.toml` makes verification raise `InvalidSignature` (sign script not re-run) — verified by: `python3 -c "...tamper...; pub.verify(...)"` raises
    - `python3 -m voss.cli check examples/skills/voss-git-summary/git_summary.voss` exits 0 (the .voss program is valid)
    - `manifest.toml` contains `[skill]`, `[scopes]`, `[trust]`, `[install]` tables; `README.md` contains the documented gate-only-confinement limitation
  </acceptance_criteria>
  <done>A genuine Ed25519-signed example bundle exists in-repo; its signature verifies; its .voss passes voss check; the limitation is documented.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <what-built>cryptography promoted to a direct dependency; the full RED skill test suite (12 tests across 6 files + e2e); a real Ed25519-signed example bundle with committed test keypair. This is the security-critical phase's foundation — the threat surface (signed third-party code execution) starts here, so the dependency + fixture-key decision is gated per the M15 security threat model (T-M15-SC).</what-built>
  <how-to-verify>
    1. Confirm `cryptography>=43.0.3` is in `[project] dependencies` of pyproject.toml (NOT a transitive assumption): `grep -n cryptography pyproject.toml`
    2. Confirm the committed fixture private key `examples/skills/voss-git-summary/test_signing_key` is acceptable as an in-repo CI fixture (it has NO production security value — it only signs the example bundle). Alternative if you object: have CI generate the key at test time instead of committing it (RESEARCH Assumption A7).
    3. Confirm the suite is RED for the right reason: `python3 -m pytest tests/harness/skill/ -q 2>&1 | tail -5` shows failures due to missing `voss.harness.trust` / `voss.harness.skill.*`, NOT collection errors.
    4. Confirm the documented gate-only-confinement limitation appears in `examples/skills/voss-git-summary/README.md`.
  </how-to-verify>
  <resume-signal>Type "approved" to proceed to Wave 1 (trust + scope spine), or describe required changes (e.g. "generate fixture key in CI instead of committing").</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo → CI | The committed fixture private key crosses into CI; it must have zero production value |
| author → install path | The signing script (`scripts/sign_fixture_bundle.py`) is author-side and OUTSIDE the install trust path — it must never be importable as a verification helper |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M15-01-01 | Tampering | Fixture `manifest.toml.sig` | mitigate | Signer recomputes sig over current manifest bytes; CI verifies sig at test time (no stale sig); Task 3 acceptance asserts byte-flip → InvalidSignature |
| T-M15-01-02 | Information Disclosure | Committed `test_signing_key` | accept | Fixture-only keypair, no production trust value; documented in README; human checkpoint confirms acceptance or routes to CI-time keygen |
| T-M15-01-03 | Spoofing | Test masking (xfail/skip hiding RED) | mitigate | Acceptance criteria forbid xfail/unconditional skip (M13 false-green lesson); tests must drive the pinned `<interfaces>` API, not invented symbols |
| T-M15-01-SC | Tampering | `cryptography` install (direct dep add) | mitigate | `cryptography` is a 13+yr PyCA package, 150M+/wk, already in uv.lock (48.0.0) — Package Legitimacy Audit disposition "Approved (existing)"; no `[ASSUMED]`/`[SUS]` package introduced, so no blocking install checkpoint needed beyond the human gate above |
</threat_model>

<verification>
- `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py --collect-only` lists exactly the 12 named tests from M15-VALIDATION
- `pytest tests/harness/skill/ -q` is RED (missing `voss.harness.trust` / `voss.harness.skill.*`), NOT collection-broken
- Fixture signature verifies against committed pub key; byte-flip → InvalidSignature
- `python3 -m voss.cli check examples/skills/voss-git-summary/git_summary.voss` exits 0
- `cryptography>=43.0.3` in `[project] dependencies`
</verification>

<success_criteria>
All 12 Requirement→Test rows resolve to real RED tests; cryptography is a direct dependency; a genuine signed example bundle ships in-repo with a verifying signature and a documented confinement limitation; human gate approved the fixture-key + dependency decision.
</success_criteria>

<output>
Create `.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-01-SUMMARY.md` when done
</output>
