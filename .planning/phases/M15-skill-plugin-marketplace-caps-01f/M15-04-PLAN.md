---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 04
type: execute
wave: 2
depends_on: ["M15-02", "M15-03"]
files_modified:
  - voss/harness/plugins.py
  - voss/harness/skill/fetch.py
  - voss/harness/skill/install.py
  - tests/harness/skill/test_install.py
  - tests/harness/skill/test_lifecycle.py
autonomous: true
requirements: [SKILL-01, SKILL-05]
user_setup: []

must_haves:
  truths:
    - "voss skill add from a local path installs a bundle that voss skill list then shows; no central index is contacted"
    - "GitHub owner/repo shorthand resolves to https://github.com/owner/repo.git (local path takes precedence on ambiguity)"
    - "Nothing is written to the plugin dir until the detached signature verifies against a trusted pinned key (staging → verify → copy)"
    - "voss skill remove uninstalls; voss skill update re-fetches + re-verifies and leaves the prior version intact on verification failure"
  artifacts:
    - path: "voss/harness/skill/fetch.py"
      provides: "fetch_bundle: git clone (HTTPS only) / local dir / archive → staging dir"
      exports: ["fetch_bundle"]
      min_lines: 40
    - path: "voss/harness/skill/install.py"
      provides: "install_bundle / remove_bundle / update_bundle with staging→verify→atomic-copy"
      exports: ["install_bundle", "remove_bundle", "update_bundle"]
      min_lines: 80
    - path: "voss/harness/plugins.py"
      provides: "PluginManifest extended with skill/scope/trust/install fields (backward compatible)"
      contains: "voss_entry"
  key_links:
    - from: "voss/harness/skill/install.py"
      to: "voss.harness.trust.verify_manifest"
      via: "install/update refuse before any copy unless verify_manifest returns (True, ...)"
      pattern: "verify_manifest"
    - from: "voss/harness/skill/install.py"
      to: "voss.harness.plugins.user_plugin_dir"
      via: "verified bundle copied into user_plugin_dir()/<skill-id>/ (existing discovery path, not a parallel root)"
      pattern: "user_plugin_dir"
    - from: "voss/harness/skill/fetch.py"
      to: "git clone --depth=1"
      via: "subprocess git for git URL / GitHub shorthand; HTTPS enforced, git:// + http:// rejected"
      pattern: "git.*clone"
---

<objective>
Wire the install path: extend `PluginManifest` with the skill/scope/trust/install fields (backward compatible — defaults so existing `.toml` still loads), add `voss/harness/skill/fetch.py` (git clone / local / archive → staging dir) and `voss/harness/skill/install.py` (`install_bundle` / `remove_bundle` / `update_bundle`) with the staging→verify→atomic-copy discipline gated by `voss.harness.trust.verify_manifest`. Installed bundles land in the EXISTING `user_plugin_dir()` discovery path and are enabled via `set_plugin_enabled()` — not a parallel system (SPEC constraint; RESEARCH anti-pattern).

Purpose: SKILL-01 (fetch+install from git URL / GitHub shorthand / local path/archive) and SKILL-05 (remove + signature-re-verifying update; update failure leaves prior version intact and runnable — a first-class requirement per CONTEXT specifics). No third-party code RUNS yet (that is M15-05) — this wave only fetches, verifies, and places bytes.

Output: extended `plugins.py`, new `fetch.py` + `install.py`; the SKILL-01 RED tests and the SKILL-05 RED tests (`test_remove`, `test_update_tamper_leaves_prior_intact`) turn GREEN.
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
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-PATTERNS.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-02-SUMMARY.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-03-SUMMARY.md

<interfaces>
<!-- Surface this plan creates + the W1 surface it consumes. -->

voss/harness/skill/fetch.py:
```python
GITHUB_SHORTHAND = re.compile(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$')
def fetch_bundle(source: str, staging_dir: Path) -> Path
    # local-path-FIRST (Path(source).exists()) then github-shorthand then git URL then archive
    # (Pitfall 6: local path beats shorthand). git URL must be https:// (reject git://, http://).
    # returns the bundle dir inside staging_dir; raises ValueError on unrecognised source,
    # RuntimeError on git clone failure
```

voss/harness/skill/install.py:
```python
def install_bundle(source: str, *, cwd: Path, allow_tofu: bool = False) -> str
    # 1 fetch_bundle → staging  2 read manifest.toml + [trust].pub_key  3 trust gate:
    #   is_key_trusted? else (allow_tofu? pin TOFU : refuse, return non-zero / raise)
    #   4 verify_manifest(staged manifest, staged sig, pub_key)  -> on (False,_) raise, copy NOTHING
    #   5 ONLY on (True,_): copy staging → user_plugin_dir()/<skill_id>/  6 record [install].source_url
    #   7 set_plugin_enabled(skill_id, True)  -> returns skill_id
def remove_bundle(skill_id: str, *, cwd: Path) -> None
    # rm user_plugin_dir()/<skill_id>/ ; set_plugin_enabled(skill_id, False)
def update_bundle(skill_id: str, *, cwd: Path) -> None
    # re-fetch from stored [install].source_url → staging → verify; FAIL: leave install dir
    # untouched, raise/non-zero; PASS: atomic swap (rename current→.bak, new→current, rm .bak)
```

Consume (from W1):
- voss.harness.trust: `verify_manifest(manifest_path, sig_path, *, pub_key_b64) -> tuple[bool,str]`; `is_key_trusted(b64) -> bool`; `pin_key(identity, b64, *, tofu) -> Path`; `key_fingerprint(b64) -> str`
- voss.harness.skill.scope: `scope_spec_from_manifest(raw) -> ScopeSpec` (used to validate the manifest declares parseable scopes at install time)

Extend (existing — add fields with defaults, do NOT break callers):
voss/harness/plugins.py `PluginManifest` (frozen dataclass, lines 15-25) — append:
`voss_entry: str = ""`, `skill_id: str = ""`, `skill_mutating: bool = False`,
`scope_tools: str = "read-only"`, `scope_fs: str = "cwd"`, `scope_net: bool = False`,
`sig_file: str = ""`, `author_identity: str = ""`, `source_url: str = ""`,
`bundle_dir: Path | None = None`.
`_read_manifest` (lines 86-134) — read the new `[skill]`/`[scopes]`/`[trust]`/`[install]` tables defensively (same `str(raw.get(...))` shape) and pass to the constructor; existing manifests (no new tables) keep current behavior (all new fields default).
Reuse: `user_plugin_dir()` (28-30), `set_plugin_enabled()` (60-77), `load_plugins()` (137-160).
</interfaces>

<analog>
Manifest extend: voss/harness/plugins.py:86-134 (`_read_manifest` defensive `.get`); :15-25 (`PluginManifest` frozen dataclass — add `= default` fields).
git-clone fetch + archive + shorthand: M15-RESEARCH.md §Pattern 5 (`fetch_bundle`, `_git_clone --depth=1`, `GITHUB_SHORTHAND`); §Pitfall 6 (local-first); §Pitfall 1 (staging before verification); §Pitfall 3 (same-filesystem atomic rename — stage under `user_plugin_dir().parent/"._staging"`).
Update failure path: M15-RESEARCH.md §Update Failure Path (rename current→.bak, new→current, restore on OS error).
CLI install test analog: tests/harness/test_extensions.py (CliRunner + monkeypatch XDG + tmp plugin dir, lines ~76-122) — but install.py here is the library; CLI wiring is M15-05.
</analog>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend PluginManifest + _read_manifest with skill/scope/trust/install fields</name>
  <read_first>
    - voss/harness/plugins.py (lines 15-25 `PluginManifest`; lines 86-134 `_read_manifest`; lines 137-160 `load_plugins` — file being modified)
    - tests/harness/test_extensions.py (existing plugin-manifest test — must still pass; backward-compat oracle)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Manifest Schema Extension)
  </read_first>
  <behavior>
    - An existing minimal manifest (only `id`/`name`/`skills=[]`) still loads — all new fields take defaults (no KeyError, no behavior change)
    - A bundle manifest with `[skill] entry/id/mutating`, `[scopes] tools/fs/net`, `[trust] sig_file/pub_key`, `[install] source_url` loads with those fields populated on PluginManifest
    - Malformed/partial new tables fall back to defaults (default-deny scopes), never raise (mirrors existing `_read_manifest` try/except)
  </behavior>
  <action>
    Append the new fields (with defaults, per `<interfaces>`) to the frozen `PluginManifest` dataclass. In `_read_manifest`, after the existing field reads, defensively read `raw.get("skill",{})`, `raw.get("scopes",{})`, `raw.get("trust",{})`, `raw.get("install",{})` using the existing `str(raw.get(...))` / `bool(...)` coercion shape and pass them to the constructor. Keep the existing `try/except (OSError, TOMLDecodeError): return None`. Do NOT change `load_plugins`'s glob/scan — installed bundle dirs are discovered by extending the scan to also read `<root>/<id>/manifest.toml` in addition to the existing `<root>/*.toml` (add the subdir-manifest glob; existing flat `*.toml` discovery unchanged).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest tests/harness/test_extensions.py -x -q 2>&1 | tail -2 && python3 -c "from voss.harness.plugins import PluginManifest; m=PluginManifest(id='x',name='x'); assert m.voss_entry=='' and m.scope_tools=='read-only' and m.scope_net is False and m.bundle_dir is None; print('MANIFEST BACKCOMPAT OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_extensions.py -x` PASSES (no regression — existing manifests still load identically)
    - The inline check prints `MANIFEST BACKCOMPAT OK` (new fields default correctly on a minimal manifest)
    - A manifest with the 4 new tables loads with `voss_entry`/`skill_id`/`scope_tools`/`sig_file`/`source_url` populated (covered by a test in test_install.py)
    - `load_plugins` discovers both flat `*.toml` AND `<id>/manifest.toml` subdir bundles
  </acceptance_criteria>
  <done>PluginManifest carries the bundle schema; existing manifests load unchanged; installed-bundle subdirs are discoverable via the existing discovery path.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: fetch_bundle (local-first, HTTPS git, archive) + install_bundle staging→verify→copy</name>
  <read_first>
    - voss/harness/plugins.py (the extended manifest from Task 1; `user_plugin_dir`, `set_plugin_enabled` — file being modified context)
    - voss/harness/trust.py (verify_manifest / is_key_trusted / pin_key / key_fingerprint — W1 surface consumed)
    - voss/harness/skill/scope.py (scope_spec_from_manifest — validate scopes parse at install)
    - tests/harness/skill/test_install.py (`test_add_local`, `test_add_github` — RED tests being satisfied)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Pattern 5 fetch; §Pitfall 1/3/6; §Security Domain git MITM row)
  </read_first>
  <behavior>
    - fetch_bundle("./examples/skills/voss-git-summary") → copies into staging (local path resolved FIRST, beats shorthand — Pitfall 6)
    - fetch_bundle("owner/repo") → git clone https://github.com/owner/repo.git (shorthand → URL); `git://` and `http://` sources → ValueError (HTTPS enforced — git MITM mitigation)
    - install_bundle of an UNTRUSTED-key bundle (allow_tofu=False) → refuses, raises, plugin dir has NO new entry (Pitfall 1: staging→verify→copy; nothing written on refusal)
    - install_bundle of a TAMPERED manifest → verify_manifest (False,_) → raises, nothing copied
    - install_bundle of a trusted, validly-signed bundle → copies to user_plugin_dir()/<id>/, records [install].source_url, set_plugin_enabled(id, True), returns id
  </behavior>
  <action>
    Create `voss/harness/skill/fetch.py` per `<interfaces>` §Pattern 5: `GITHUB_SHORTHAND` regex, local-path-FIRST resolution (`Path(source).exists()` before shorthand — Pitfall 6), `git clone --depth=1` via subprocess for HTTPS git URL / shorthand→URL, archive via `shutil.unpack_archive`. Reject `git://` and `http://` URLs with `ValueError` (enforce HTTPS — RESEARCH Security Domain git-MITM row). Create `voss/harness/skill/install.py`: `install_bundle` does fetch→staging (stage under `user_plugin_dir().parent/"._staging"/<tmp>` for same-filesystem atomic ops — Pitfall 3), parse staged `manifest.toml`, extract `[trust].pub_key` + `author_identity`; if `not is_key_trusted(pub_key)`: when `allow_tofu` print `key_fingerprint` + TOFU-pin via `pin_key(..., tofu=True)`, else raise `SkillTrustError` (refuse, nothing copied); call `verify_manifest(staged_manifest, staged_sig, pub_key_b64=...)` — on `(False,_)` raise, copy NOTHING (Pitfall 1); ONLY on `(True,_)` `shutil.copytree(staging → user_plugin_dir()/<skill_id>/)`, write `[install].source_url`/`installed_at` back into the installed manifest, `set_plugin_enabled(skill_id, True)`, return `skill_id`. Validate `scope_spec_from_manifest(raw)` succeeds (parseable scopes) before copy. TOFU defaults OFF (RESEARCH §Trust Store Details — refuse by default, print fingerprint + instruction).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest "tests/harness/skill/test_install.py::test_add_local" "tests/harness/skill/test_install.py::test_add_github" -x -q -m "not live" 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/skill/test_install.py -x -m "not live"` — `test_add_local` PASSES and `test_add_github` PASSES (shorthand→URL transformation asserted without the live network call)
    - On an untrusted-key bundle with `allow_tofu=False`, `install_bundle` raises and `user_plugin_dir()` has no `<skill_id>/` entry (test asserts nothing-written)
    - `grep -n "verify_manifest" voss/harness/skill/install.py` shows verify is called BEFORE any `copytree`/`shutil.copy` to the install dir
    - `grep -n "git://\|http://" voss/harness/skill/fetch.py` shows both are rejected (HTTPS enforced)
    - No central index / network search is contacted (only the explicit source URL / git clone)
  </acceptance_criteria>
  <done>SKILL-01: bundles install from local path + GitHub shorthand through a staging→trust-gate→verify→copy pipeline; nothing lands on disk unless a trusted key validly signed the manifest.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: remove_bundle + update_bundle (re-verify, prior-version-intact on failure)</name>
  <read_first>
    - voss/harness/skill/install.py (install_bundle from Task 2 — file being modified)
    - voss/harness/plugins.py (`user_plugin_dir`, `set_plugin_enabled`, extended manifest `source_url`)
    - voss/harness/trust.py (verify_manifest — re-verified on update)
    - tests/harness/skill/test_lifecycle.py (`test_remove`, `test_update_tamper_leaves_prior_intact` — RED tests being satisfied)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Update Failure Path; §Pitfall 3 same-filesystem rename)
  </read_first>
  <behavior>
    - remove_bundle(id): user_plugin_dir()/<id>/ is deleted; set_plugin_enabled(id, False); subsequent load_plugins omits it
    - update_bundle(id) with a now-TAMPERED upstream: verify fails → install dir UNTOUCHED, raises non-zero; the prior installed manifest+.voss still present and loadable (the SKILL-05 first-class requirement)
    - update_bundle(id) with a valid re-signed upstream: atomic swap (current→.bak, new→current, rm .bak); on OS error mid-swap → restore from .bak (no half-installed state)
  </behavior>
  <action>
    Add `remove_bundle(skill_id, *, cwd)` (rm `user_plugin_dir()/<skill_id>/`, `set_plugin_enabled(skill_id, False)`) and `update_bundle(skill_id, *, cwd)` to install.py. update_bundle: read stored `[install].source_url` from the installed manifest; `fetch_bundle(source_url, staging)`; `verify_manifest` the staged manifest — on `(False,_)` print error, `raise SkillTrustError` / non-zero exit, LEAVE the current install dir completely untouched (RESEARCH §Update Failure Path step 4). On verify pass: `rename(current → current.bak)`, `rename(staged → current)`, on success `rmtree(current.bak)`; on any OSError during the swap, restore `current.bak → current` (no partial state — Pitfall 3 same-filesystem staging makes rename atomic). Reuse the trust gate exactly as install_bundle (an update from an untrusted key is also refused).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest tests/harness/skill/test_lifecycle.py -x -q 2>&1 | tail -3 && python3 -m pytest tests/harness/skill/ -q -m "not live" 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/skill/test_lifecycle.py -x` — `test_remove` AND `test_update_tamper_leaves_prior_intact` PASS (were RED in W0)
    - After a tampered-upstream `update_bundle`, the prior `user_plugin_dir()/<id>/manifest.toml` + `.voss` are byte-identical to before the update attempt (test asserts prior version intact)
    - `update_bundle` re-calls `verify_manifest` (grep shows it; an update is not exempt from the trust gate)
    - `pytest tests/harness/skill/ -q -m "not live"` shows only the still-unimplemented registry/dispatch (SKILL-02) tests RED — install/trust/scope/lifecycle GREEN, no regression
  </acceptance_criteria>
  <done>SKILL-05 (remove + update) satisfied: remove uninstalls cleanly; a tampered-upstream update fails and the prior version remains intact and loadable; updates re-enforce the trust gate.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| remote source → staging dir | Untrusted bundle bytes (git clone / archive) land in staging before any trust check |
| staging dir → plugin dir | The verify gate; bytes cross into the discovered install path ONLY after a trusted-key signature passes |
| upstream → update | A previously-trusted source may be compromised at update time (supply-chain) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M15-04-01 | Tampering | Bundle written before verify (staging pitfall) | mitigate | install_bundle copies to plugin dir ONLY after `verify_manifest`→(True,_); acceptance grep asserts verify precedes any copytree (Pitfall 1) |
| T-M15-04-02 | Spoofing | Untrusted/unknown signing key | mitigate | `is_key_trusted` checked before verify; TOFU OFF by default — unknown key refused, fingerprint + `voss skill trust` instruction printed |
| T-M15-04-03 | Tampering | Supply-chain: compromised upstream on update | mitigate | `update_bundle` re-fetches AND re-runs `verify_manifest`; failure leaves prior version intact (no trust-on-first-install-only); SKILL-05 acceptance test |
| T-M15-04-04 | Spoofing | git clone MITM (non-HTTPS transport) | mitigate | fetch.py rejects `git://`/`http://`; HTTPS enforced; signature verification catches content tampering regardless of transport (RESEARCH Security Domain) |
| T-M15-04-05 | Elevation of Privilege | Path traversal in bundle/archive (`../../.bashrc`) | mitigate | Confine extraction/copy to staging then to `user_plugin_dir()/<skill_id>/`; reject bundle entries resolving outside the bundle dir (post-`unpack_archive` path check / `jail_path` discipline) |
| T-M15-04-06 | Tampering | Cross-device rename leaves half-install | mitigate | Stage under `user_plugin_dir().parent/"._staging"` (same filesystem — Pitfall 3); atomic rename swap with `.bak` restore on OSError |
| T-M15-04-SC | Tampering | `git` subprocess / archive libs | accept | `git` CLI (2.50.1) + stdlib `shutil.unpack_archive` only; no new package; signature gate catches any post-fetch tampering regardless |
</threat_model>

<verification>
- `pytest tests/harness/skill/test_install.py tests/harness/skill/test_lifecycle.py -x -m "not live"` — SKILL-01 + SKILL-05 tests GREEN
- `pytest tests/harness/test_extensions.py -x` — no regression on existing plugin loading
- Untrusted-key / tampered-manifest install writes NOTHING to the plugin dir
- Tampered-upstream update leaves the prior installed version byte-intact
- `git://`/`http://` sources rejected; only HTTPS git + local + archive accepted; no central index contacted
</verification>

<success_criteria>
SKILL-01 + SKILL-05 satisfied: bundles fetch+install from local path/GitHub shorthand through a staging→trust→verify→copy pipeline into the existing discovery path; remove uninstalls; update re-verifies and preserves the prior version on failure; PluginManifest schema is extended backward-compatibly.
</success_criteria>

<output>
Create `.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-04-SUMMARY.md` when done
</output>
