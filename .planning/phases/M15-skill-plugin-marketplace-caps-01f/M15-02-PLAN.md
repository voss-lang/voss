---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 02
type: execute
wave: 1
depends_on: ["M15-01"]
files_modified:
  - voss/harness/trust.py
  - tests/harness/skill/test_trust.py
autonomous: true
requirements: [SKILL-03]
user_setup: []

must_haves:
  truths:
    - "A tampered manifest fails signature verification and the operation is refused"
    - "A bundle signed by a key not in the trust store is refused until the key is pinned"
    - "After `voss skill trust <key>` (pin_key), the same bundle's signature verifies and install proceeds"
    - "The trust store holds ONLY public keys, is chmod 0600, and writes are file-locked"
  artifacts:
    - path: "voss/harness/trust.py"
      provides: "Ed25519 detached-signature verification + pinned-key trust store"
      exports: ["verify_manifest", "trust_store_path", "pin_key", "is_key_trusted", "load_trusted_keys", "key_fingerprint"]
      min_lines: 80
  key_links:
    - from: "voss/harness/trust.py"
      to: "cryptography.hazmat.primitives.asymmetric.ed25519"
      via: "Ed25519PublicKey.from_public_bytes(...).verify(sig, manifest_bytes)"
      pattern: "Ed25519PublicKey"
    - from: "voss/harness/trust.py"
      to: "~/.config/voss/trusted_keys.toml"
      via: "trust_store_path() + chmod 0600 + portalocker exclusive lock"
      pattern: "chmod\\(0o600\\)"
---

<objective>
Build the signature-trust spine: `voss/harness/trust.py` — Ed25519 detached-signature verification over the manifest, plus a pinned-key trust store at `~/.config/voss/trusted_keys.toml` (chmod 0600, portalocker-guarded). This is a HARD PREREQUISITE: no third-party `.voss` code path runs until this module exists and is proven (RESEARCH cross-cutting constraint; CONTEXT specifics — "implemented and provable before any third-party code executes").

Purpose: SKILL-03 — tampered manifest → refuse; unknown/untrusted key → refuse until pinned. The trust gate is the install/update boundary; verification is pure-Python, in-process, runs before any bytes land on disk.

Output: `voss/harness/trust.py` with `verify_manifest` / trust-store CRUD; the SKILL-03 RED tests in `tests/harness/skill/test_trust.py` turn GREEN.
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

<interfaces>
<!-- The public surface this plan creates. The W0 RED tests assert exactly these. -->

voss/harness/trust.py public API:
```python
def trust_store_path() -> Path
    # base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home()/".config")); base/"voss"/"trusted_keys.toml"

def load_trusted_keys() -> dict[str, dict]
    # {identity: {"public_key": b64, "pinned_at": iso8601, "tofu": bool}}; missing/corrupt file -> {} (never raises)

def is_key_trusted(pub_key_b64: str) -> bool

def key_fingerprint(pub_key_b64: str) -> str
    # sha256 hex of the raw 32-byte public key, for human display before TOFU pin

def pin_key(identity: str, pub_key_b64: str, *, tofu: bool = False) -> Path
    # validates key is a 32-byte Ed25519 pub; read-modify-write trusted_keys.toml under
    # portalocker exclusive lock; path.chmod(0o600); returns trust_store_path()

def verify_manifest(manifest_path: Path, sig_path: Path, *, pub_key_b64: str) -> tuple[bool, str]
    # reads manifest bytes + hex sig; Ed25519PublicKey.from_public_bytes(b64decode(pub_key_b64)).verify(sig, bytes)
    # returns (True, "verified") | (False, "<reason>"); NEVER raises (catches InvalidSignature, OSError, ValueError)
```

Reuse (existing, do NOT reimplement):
From voss/harness/permissions.py — the `(bool, str)` check-return convention and `_config_path()` XDG pattern (`base/"voss"/"permissions.json"`); trust.py mirrors it as `base/"voss"/"trusted_keys.toml"`.
From voss/harness/plugins.py:60-77 — `set_plugin_enabled` write-then-`path.chmod(0o600)` pattern + the `tomli_w`-or-inline-fallback TOML serializer. Copy this serialization shape (do not invent a new one).
`portalocker` is already in pyproject.toml dependencies — use `portalocker.Lock(path, "a", flags=...)` or `portalocker.lock` for the exclusive trust-store write lock (Pitfall 4).
`cryptography>=43.0.3` is a direct dependency as of M15-01.
</interfaces>

<analog>
Structural analog: voss/harness/permissions.py (dataclass + load/save + `(bool, str)` check; `_config_path()` lines 68-70; error-swallow `except (OSError, json.JSONDecodeError): return cls(...)` lines ~118-127).
TOML write + chmod 0600 + tomli_w-or-inline fallback: voss/harness/plugins.py:60-77 (`set_plugin_enabled`).
Ed25519 verify code (VERIFIED live 2026-05-19): M15-RESEARCH.md §Code Examples "Verified: cryptography Ed25519" — `Ed25519PublicKey.from_public_bytes`, `.verify(sig, manifest_bytes)` raises `InvalidSignature` on tamper.
No exact analog for crypto (M15-PATTERNS §No Analog Found) — borrow the permissions.py structure only.
</analog>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Ed25519 verify_manifest + trust store path/load</name>
  <read_first>
    - voss/harness/permissions.py (lines 68-70 `_config_path`; lines ~118-127 error-swallow load pattern; `(bool,str)` return convention)
    - voss/harness/plugins.py (lines 28-30 `user_plugin_dir` XDG; lines 42-57 `_load_enablement` corrupt-file-returns-empty pattern)
    - tests/harness/skill/test_trust.py (the RED tests this turns green — file being satisfied)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Code Examples cryptography Ed25519; §Trust Store Details)
  </read_first>
  <behavior>
    - verify_manifest over an untampered manifest with the correct pub key → `(True, "verified")`
    - verify_manifest after flipping one manifest byte → `(False, "signature invalid")`, NO exception escapes
    - verify_manifest with a missing sig file or malformed hex → `(False, "<reason>")`, NO exception escapes
    - trust_store_path() honors `XDG_CONFIG_HOME`; load_trusted_keys() on missing/corrupt file → `{}` (never raises)
    - is_key_trusted(b64) → True iff that exact base64 public key is present in any trust-store entry
  </behavior>
  <action>
    Create `voss/harness/trust.py`. Implement `trust_store_path()` (XDG pattern mirroring permissions._config_path → `base/"voss"/"trusted_keys.toml"`), `load_trusted_keys()` (tomllib.loads with `except (OSError, tomllib.TOMLDecodeError): return {}` — never raise, mirroring `_load_enablement`), `is_key_trusted(pub_key_b64)`, `key_fingerprint(pub_key_b64)` (sha256 hex of raw decoded 32 bytes), and `verify_manifest(manifest_path, sig_path, *, pub_key_b64) -> tuple[bool,str]`. verify_manifest: base64-decode pub key → `Ed25519PublicKey.from_public_bytes`; read `sig_path` hex → `bytes.fromhex`; read manifest bytes; `pub.verify(sig, manifest_bytes)`; wrap in try/except catching `InvalidSignature` → `(False,"signature invalid")`, `(OSError, ValueError, TypeError)` → `(False,"<reason>")`. NEVER raise out of verify_manifest (permissions.py error-swallow discipline). Reject non-32-byte decoded keys with `(False,"invalid public key")`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest "tests/harness/skill/test_trust.py::test_tampered_manifest_refused" "tests/harness/skill/test_trust.py::test_unknown_key_refused" -x -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/skill/test_trust.py::test_tampered_manifest_refused -x` PASSES (was RED in W0)
    - `verify_manifest` returns a `tuple[bool, str]` and never raises for tampered/missing/malformed inputs (test asserts no exception, `(False, ...)`)
    - `grep -n "Ed25519PublicKey" voss/harness/trust.py` shows the verify uses `cryptography`, not a hand-rolled check
    - `trust_store_path()` resolves under `XDG_CONFIG_HOME` when set (test monkeypatches it)
  </acceptance_criteria>
  <done>Tampered/unknown-key manifests are refused via real Ed25519 verification that never raises; trust-store read path is corruption-safe.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: pin_key write path (chmod 0600 + portalocker, public keys only)</name>
  <read_first>
    - voss/harness/trust.py (the module from Task 1 — file being modified)
    - voss/harness/plugins.py (lines 60-77 `set_plugin_enabled`: read-modify-write + tomli_w-or-inline fallback + `path.chmod(0o600)`)
    - tests/harness/skill/test_trust.py (`test_trust_then_install_succeeds` — the RED test this turns green)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Trust Store Details + Pitfall 4 portalocker)
  </read_first>
  <behavior>
    - pin_key("id", b64) writes a `[keys."id"]` table with `public_key`, `pinned_at` (iso8601 UTC), `tofu` to trusted_keys.toml; file mode becomes 0600
    - After pin_key, is_key_trusted(b64) → True and load_trusted_keys()["id"]["public_key"] == b64
    - pin_key on a non-32-byte / non-base64 key → raises ValueError (caller surfaces non-zero exit); store unchanged
    - Concurrent pin_key calls do not corrupt the TOML (portalocker exclusive lock around read-modify-write)
  </behavior>
  <action>
    Add `pin_key(identity, pub_key_b64, *, tofu=False) -> Path` to trust.py. Validate the key decodes to exactly 32 bytes and constructs a valid `Ed25519PublicKey` (else `raise ValueError`). Acquire an exclusive `portalocker` lock on `trust_store_path()` before the read-modify-write. Read existing keys via `load_trusted_keys()`, set `keys[identity] = {"public_key": pub_key_b64, "pinned_at": <utc iso8601>, "tofu": tofu}`, serialize with the `tomli_w`-or-inline fallback copied from plugins.py:66-74 (table form `[keys."<identity>"]`), `path.parent.mkdir(parents=True, exist_ok=True)`, `path.write_text(text)`, `path.chmod(0o600)`. Store ONLY public keys (RESEARCH anti-pattern: trust store is never a private keyring).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest tests/harness/skill/test_trust.py -x -q 2>&1 | tail -3 && python3 -c "import os,tempfile,base64; d=tempfile.mkdtemp(); os.environ['XDG_CONFIG_HOME']=d; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as K; from cryptography.hazmat.primitives import serialization as S; k=K.generate(); pb=base64.b64encode(k.public_key().public_bytes(S.Encoding.Raw,S.PublicFormat.Raw)).decode(); import voss.harness.trust as t; p=t.pin_key('x@y',pb); import stat,os as o; print('MODE', oct(stat.S_IMODE(o.stat(p).st_mode)), 'TRUSTED', t.is_key_trusted(pb))"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/skill/test_trust.py -x` — all 3 SKILL-03 tests PASS
    - The inline check prints `MODE 0o600 TRUSTED True`
    - `grep -n "portalocker" voss/harness/trust.py` shows the write path takes an exclusive lock
    - `grep -n "private" voss/harness/trust.py` shows no private-key storage (trust store is public-key-only)
    - pin_key on a bad key raises `ValueError` and leaves the store unchanged (test asserts)
  </acceptance_criteria>
  <done>Keys pin to a 0600, lock-guarded, public-key-only trust store; the full SKILL-03 RED suite is GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| untrusted bundle → install path | The manifest + detached sig arrive from an untrusted source; verify_manifest is the gate |
| filesystem → trust store | Concurrent processes / corrupt file crossing into the trust-store read/write path |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M15-02-01 | Tampering | Manifest bytes post-fetch | mitigate | `verify_manifest` does Ed25519 `pub.verify(sig, manifest_bytes)`; any byte change → `InvalidSignature` → `(False, "signature invalid")`; caller refuses + non-zero exit |
| T-M15-02-02 | Spoofing | Forged signature / unknown key | mitigate | Verification uses the pinned public key from the trust store only; a key absent from `load_trusted_keys()` ⇒ `is_key_trusted` False ⇒ refuse before verify |
| T-M15-02-03 | Tampering | trusted_keys.toml concurrent write | mitigate | `portalocker` exclusive lock around read-modify-write (Pitfall 4); chmod 0600 limits local tamper surface |
| T-M15-02-04 | Information Disclosure | Private key leakage into trust store | mitigate | Trust store stores ONLY base64 public keys; acceptance greps assert no private-key path; RESEARCH anti-pattern enforced |
| T-M15-02-05 | Repudiation / DoS | Crash on corrupt trust store | mitigate | `load_trusted_keys()` swallows `OSError`/`TOMLDecodeError` → `{}` (permissions.py discipline); a corrupt store fails safe (deny), never crashes the harness |
| T-M15-02-SC | Tampering | `cryptography` supply chain | accept | PyCA `cryptography`, 13+yr, 150M+/wk, pinned `>=43.0.3` (added M15-01); Package Legitimacy Audit disposition Approved; no new `[ASSUMED]` package |
</threat_model>

<verification>
- `pytest tests/harness/skill/test_trust.py -x -q` — 3/3 SKILL-03 tests GREEN
- verify_manifest never raises (tampered / missing-sig / malformed-hex all return `(False, ...)`)
- trusted_keys.toml is chmod 0600 and written under a portalocker exclusive lock
- No private-key storage path in trust.py
- `pytest tests/harness/skill/ -q` shows only the still-unimplemented (scope/install/registry/lifecycle) tests RED — no regression
</verification>

<success_criteria>
SKILL-03 fully satisfied: tampered manifest refused, unknown key refused until pinned, pin-then-add succeeds; trust store is a 0600 lock-guarded public-key-only file; verification is in-process Ed25519 that fails safe.
</success_criteria>

<output>
Create `.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-02-SUMMARY.md` when done
</output>
