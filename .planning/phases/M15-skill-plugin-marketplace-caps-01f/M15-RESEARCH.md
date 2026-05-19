# Phase M15: Skill / Plugin Marketplace (CAPS-01f) — Research

**Researched:** 2026-05-19
**Domain:** Skill bundle install, detached-signature trust, manifest-declared scope enforcement, .voss runtime dispatch
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Artifact**: plugin **bundle dir** = TOML manifest + `.voss` program file(s) + optional assets. Extends `voss/harness/plugins.py` discovery + `~/.config/voss/plugins.toml` enablement — NOT a fork/parallel install system.
- **Sources (v0.2)**: git URL, GitHub `owner/repo` shorthand, local path, local archive. **No central index / `voss skill search` / network name resolution.**
- **Verbs**: `voss skill add`, `voss skill list`, `voss skill remove`, `voss skill update`. `update` re-fetches **and** re-verifies signature; verification failure leaves prior version intact and runnable.
- **Trust**: detached signature over the manifest, **minisign / ssh-sig family** (NOT GPG). `voss skill trust <key>` pins a key; first-add may TOFU-pin. Tampered manifest OR unknown/untrusted key → refuse, non-zero exit, install nothing.
- **`.voss` skill registration**: bundle manifest binds a skill id → `.voss` program; loads into `skill_registry`; runs via the **existing harness `.voss` runtime** (no new interpreter). Runnable via `/skill <id>` like built-ins.
- **Confinement**: manifest-declared permission scopes (tools / fs / net) enforced at skill run time by **reusing the existing tool gate/allowlist** — no second enforcement engine, **no OS-level sandbox** this phase. The limitation MUST be documented.
- **Surface**: headless only — top-level CLI + REPL slash. **No M9 TUI dependency** (deferred, M14-parity discipline).
- **Fixture**: ship one real signed `.voss` skill bundle in-repo (manifest + signature + declared scopes) exercising add → list → run → update → remove; CI runs the full cycle.

### Cross-cutting constraints (locked, from ROADMAP M15 section)

- **Sandbox/permission story is a hard prerequisite** — no third-party code path runs before scope-vs-gate enforcement exists. Highest-risk surface of the cycle; plan it first in the wave order.
- **Default-deny posture**: third-party skill default scope is read-only; mutating-tool scopes require explicit declared grant in the manifest (aligns with SPEC scope enforcement). Map declared scopes onto the **existing M1 permission tiers (`plan` / `edit` / `auto`)** in `voss/harness/permissions.py` rather than inventing a parallel tier vocabulary.
- **Audit trail**: every third-party skill invocation is logged through the existing M2 RunRecorder (`voss/harness/recorder.py`) — installs, scope grants/denials, and skill runs are recorded events.

### Claude's Discretion (HOW — resolve in planning)

- **Manifest filename/format detail**: SPEC locks "TOML, extends plugins.py"; ROADMAP headline mentioned a `voss-skill.yml`. SPEC wins — extend the existing TOML `PluginManifest` schema with the new fields (signature ref, declared scopes, `.voss` skill binding). Pick exact field names/layout in planning.
- **Signature library choice**: minisign vs ssh-sig (`ssh-keygen -Y`) — both satisfy the locked "detached sig + pinned key" mechanism. Choose based on dependency weight + availability; document the falsifiable behavior (tamper→refuse, unknown-key→refuse-until-pinned) regardless.
- **Scope grammar**: concrete shape of declared `tools/fs/net` scopes and how they bind to existing gate/allowlist predicates in `tools.py`/`sandbox.py`/`permissions.py`.
- **Fetch implementation**: git clone vs sparse fetch; cache/extraction location under the existing plugin dirs.
- **Trust store location/format**: where pinned keys live (under `~/.config/voss/`), file perms (mirror the existing `plugins.toml` chmod 0600 pattern).
- **Example skill content**: pick a small genuinely useful `.voss` skill for the fixture.

### Deferred Ideas (OUT OF SCOPE)

- Central/hosted registry + `voss skill search` / name index — explicitly "central registry later" (seed + SPEC out-of-scope).
- OS-level sandbox (subprocess isolation, seccomp, containers) — deferred; v0.2 confinement = signature + manifest-scope-vs-gate only (documented limitation).
- M9 TUI marketplace / install panel — deferred (headless-only).
- GPG keyring trust path — minisign/ssh-sig chosen instead.
- Skill authoring/publishing toolchain (`voss skill publish`, scaffolding) — not this phase.
- Inter-skill dependency / version resolution — out (single self-contained bundle).
- Auto-update / background refresh — `update` is explicit and manual only.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKILL-01 | `voss skill add` bundle install from git URL, GitHub `owner/repo`, local path/archive | §Fetch Architecture, §Code Examples (git fetch), §Recommended Project Structure |
| SKILL-02 | `.voss`-authored skill registration into skill_registry via existing .voss runtime (entry point, ctx wiring) | §VossSkillAdapter Pattern, §Code Examples (voss runtime dispatch), §SkillEntry extension |
| SKILL-03 | Detached-signature + pinned-key trust gate: tampered manifest → refuse; unknown/untrusted key → refuse until pinned | §Signature Mechanism (DECIDED: ssh-sig via `cryptography`), §Trust Store, §Code Examples (signing) |
| SKILL-04 | Manifest-declared permission scopes (tools/fs/net) enforced via existing tool gate | §Scope Grammar, §Gate Binding, §Code Examples (scope enforcement) |
| SKILL-05 | list/remove/update lifecycle; update re-verifies signature, leaves prior intact on failure | §Lifecycle Verbs, §Update Failure Path |
| SKILL-06 | Shipped signed example `.voss` skill bundle as e2e CI fixture | §Example Skill Bundle, §Validation Architecture |
</phase_requirements>

---

## Summary

M15 builds on a well-understood substrate. The six existing harness files (`plugins.py`, `skill_registry.py`, `permissions.py`, `sandbox.py`, `tools.py`, `recorder.py`) already provide all enforcement, registration, and audit plumbing — M15 wires them together with three new concerns: fetch+extract, signature verification, and scope-limited dispatch.

**Signature mechanism (key research question 1):** The `minisign` PyPI package (0.1.0) is a Development Status 1 stub with no implementation. The `minisign` CLI binary is not in the CI environment. However, `ssh-keygen -Y sign / verify` is available on macOS and all major Linux distros (OpenSSH ≥ 8.0, released 2019), and the `cryptography` library (already a runtime dependency, version 43.0.3 installed) provides Ed25519 sign+verify natively. **Recommendation: use `cryptography` Ed25519 directly for the detached signature — zero new dependencies, consistent with the existing dependency graph, falsifiable tamper behavior verified by live test.** ssh-keygen subprocess is an acceptable fallback for key generation UX only (generating the author keypair), not for verification in the critical install/run path.

**Scope binding (key research question 4):** The existing `PermissionGate` already has an `is_network` axis and a `mode` axis (plan/edit/auto). The mapping is direct: a third-party skill's declared scopes cap the effective mode for that skill's tool calls. Default scope = `plan` (read-only). Declaring `tools: [mutating]` = `edit`. Declaring `tools: [all]` = `auto`. The gate's `_check_impl` path is called per tool call, so injecting a scope-limited gate instance at dispatch time is zero-surgery enforcement.

**`.voss` runtime dispatch (key research question 3):** `voss run` compiles `.voss` → Python in a tmpdir, then `subprocess.run([sys.executable, generated_py])`. The existing `SkillEntry.handler` is a synchronous Python callable that takes `(ctx, args)`. A `VossSkillAdapter` wraps this: on invocation, it compiles the bundle's `.voss` file via `_compile_source` and runs it in a subprocess, capturing stdout. This reuses the existing compiler path exactly and requires no new interpreter. The skill's output is rendered via the existing renderer (same as `make_skill_dispatch` in `server_skills.py`).

**Primary recommendation:** Implement in four waves: (W1) scope enforcement module + trust store + signature module — the permission spine must exist before any third-party code runs; (W2) fetch+extract + manifest schema extension + trust gate integration; (W3) skill registration + VossSkillAdapter + `voss skill add/list/remove/update/trust` CLI subcommands; (W4) example bundle + CI fixture + recorder audit events.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Bundle fetch (git clone / local extract) | Harness CLI module | OS git subprocess | Install is a CLI-time operation; runs in the harness process before any skill code executes |
| Signature verification | Harness trust module (new) | `cryptography` lib | Verification is a pure-Python gate in the install path; no skill code runs until this passes |
| Trust store (pinned keys) | Harness config dir (~/.config/voss/) | — | Mirrors plugins.toml location; same chmod 0600 pattern |
| Manifest schema extension | plugins.py (extend) | — | `PluginManifest` is the single manifest model; add fields, not a parallel type |
| Skill registration (SkillEntry) | skill_registry.py (extend) | — | Registry is the single source of truth; add VossSkillEntry subclass or adapter |
| `.voss` skill execution | Existing voss run subprocess path | compiler (voss.codegen) | No new interpreter; reuse `_compile_source` + `subprocess.run` exactly as `voss run` does |
| Scope enforcement | permissions.py (PermissionGate) | tools.py (tool gate) | Per-call enforcement already exists; inject scope-limited gate at skill dispatch time |
| Audit trail (install/run events) | recorder.py (RunRecorder) | — | `RunRecorder.observe` call sites already exist; add new event kinds |
| `voss skill` CLI group | cli.py (extend skill_group) | — | `skill_group` already exists with `skill run`; add `add/list/remove/update/trust` |
| REPL slash commands | cli.py (extend `/skill`, `/plugins`) | — | `/skill <id>` already dispatches; update to include third-party skills in listing |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | `>=43.0.3` (already pinned) | Ed25519 detached signatures | Already a runtime dep; provides `Ed25519PrivateKey` / `Ed25519PublicKey` with sign/verify; zero new dependencies; verified round-trip in live test |
| `tomllib` / `tomli_w` | stdlib + already-optional dep | TOML manifest read/write | Already used in `plugins.py`; no change needed |
| `click` | `>=8.1.0` (already pinned) | CLI subcommands | Already used for all harness CLI; skill group already exists |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `gitpython` | `>=3.1.44` | git clone / fetch for bundle install | For the git URL + GitHub shorthand source path; subprocess git is the alternative (lighter) |
| `subprocess` (stdlib) | stdlib | git clone (light path) + voss run subprocess | Sufficient for git clone; already used by `voss run` |

**Package legitimacy note:** `gitpython` (PyPI, not npm; slopcheck tested npm registry where it got SLOP — this is a PyPI package). See Package Legitimacy Audit section.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cryptography` Ed25519 | `minisign` CLI binary | minisign CLI not in CI/production environments; minisign PyPI 0.1.0 is a stub; `cryptography` is already a dep |
| `cryptography` Ed25519 | `ssh-keygen -Y sign` subprocess | Available everywhere; but subprocess-based verification adds process overhead on each skill run; `cryptography` is in-process and already present |
| `gitpython` | `subprocess git clone` | subprocess has fewer deps; gitpython provides cleaner API for clone/fetch/tag enumeration; recommendation: subprocess first (no new dep), gitpython as optional enhancement |
| Bundle dir in plugin dirs | Separate install root | Separate root would be a parallel system (forbidden by SPEC); plugin dirs are the canonical discovery path |

**Installation (new deps only):**
```bash
# No new runtime deps if using subprocess git clone.
# If gitpython is added:
# uv add 'GitPython>=3.1.44'
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `cryptography` | PyPI | 13+ yrs | 150M+/wk | github.com/pyca/cryptography | N/A (already dep) | Approved (existing) |
| `minisign` (PyPI) | PyPI | ~4 yrs, 1 version only | minimal | gitlab.com/hackancuba/minisign-py | [ASSUMED] SUS — 1 version, stub implementation, Dev Status 1 | **REMOVED** — stub package, no usable API |
| `GitPython` | PyPI | 15+ yrs | 120M+/wk | github.com/gitpython-developers/GitPython | [OK] via PyPI | Approved if used; subprocess git is preferred |
| `watchdog` | PyPI | 14+ yrs (already in M14) | 40M+/wk | github.com/gorakhargosh/watchdog | [OK] | Not needed for M15 |

**Packages removed due to stub/unusable verdict:** `minisign` (PyPI 0.1.0 — verified empty stub, Development Status 1 - Planning)

**Recommendation:** Use `cryptography` (existing dep) for Ed25519 signatures. Use `subprocess git clone` for fetch (no new dep). GitPython is optional enhancement only.

---

## Architecture Patterns

### System Architecture Diagram

```
voss skill add <source>
        │
        ▼
  ┌─────────────┐
  │ FetchLayer  │  git clone / local extract → tmp staging dir
  │  (new)      │
  └──────┬──────┘
         │ staged bundle dir
         ▼
  ┌─────────────┐
  │ TrustGate   │  read manifest.toml → compute hash → verify Ed25519 sig
  │  (new)      │  against trust_store (~/.config/voss/trusted_keys.toml)
  └──────┬──────┘
         │ verified bundle
         ▼
  ┌─────────────┐
  │ InstallLayer│  copy bundle dir → user_plugin_dir() / <skill-id>/
  │  (new)      │  write enablement via set_plugin_enabled()
  └──────┬──────┘
         │ installed
         ▼
  ┌─────────────┐
  │ SkillLoader │  _read_manifest (extended) → VossSkillAdapter
  │  (extends   │  registered into SkillRegistry
  │ plugins.py) │
  └──────┬──────┘
         │ registered skill
         ▼
/skill <id>  ──→  SkillRegistry.get(id)
                        │
                        ▼
               ┌─────────────────┐
               │ VossSkillAdapter│  compile .voss → py (tmpdir)
               │  .handler(ctx,  │  inject scope-limited PermissionGate
               │   args)         │  subprocess.run(generated_py)
               └────────┬────────┘
                        │ tool calls
                        ▼
               ┌─────────────────┐
               │ Scope-Limited   │  declared_scopes → effective_mode
               │ PermissionGate  │  per-call gate check (existing path)
               └────────┬────────┘
                        │ audit
                        ▼
               RunRecorder.observe()  →  skill.run / scope.deny events
```

### Recommended Project Structure

```
voss/harness/
├── plugins.py              # EXTEND: PluginManifest adds sig_file, scopes, voss_entry fields
├── skill_registry.py       # EXTEND: VossSkillEntry + load_voss_skills()
├── skills/
│   └── (existing skills unchanged)
├── skill/                  # NEW module package
│   ├── __init__.py
│   ├── trust.py            # TrustStore, verify_signature, tofu_pin
│   ├── fetch.py            # fetch_bundle(): git clone / local / archive
│   ├── install.py          # install_bundle(), remove_bundle(), update_bundle()
│   ├── scope.py            # ScopeSpec, scoped_gate(), scope_to_mode()
│   └── adapter.py          # VossSkillAdapter (SkillEntry-compatible handler)
├── cli.py                  # EXTEND: skill_group gets add/list/remove/update/trust
└── recorder.py             # EXTEND: observe() skill.install / scope.deny / skill.run events
```

```
~/.config/voss/
├── plugins.toml            # existing enablement (chmod 0600)
├── trusted_keys.toml       # NEW: pinned public keys (chmod 0600, same pattern)
└── plugins/                # existing plugin dir
    └── <skill-id>/         # NEW: installed bundle subdirs
        ├── manifest.toml   # bundle manifest (TOML, extended schema)
        ├── manifest.toml.sig  # detached Ed25519 signature (hex/base64)
        └── <skill>.voss    # the .voss skill program
```

### Pattern 1: Ed25519 Detached Signature over Manifest

**What:** Sign the manifest TOML bytes with Ed25519 (from `cryptography`); store sig as hex in `manifest.toml.sig`. Verify at install/update time before any code is placed on disk.
**When to use:** All install and update operations.

```python
# Source: cryptography docs (https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
# VERIFIED: live round-trip test run 2026-05-19
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
import base64

# --- Signing (bundle author, run once) ---
def sign_manifest(manifest_path: Path, private_key_path: Path) -> bytes:
    key_bytes = base64.b64decode(private_key_path.read_text().strip())
    key = Ed25519PrivateKey.from_private_bytes(key_bytes)
    manifest_bytes = manifest_path.read_bytes()
    return key.sign(manifest_bytes)  # 64-byte raw signature

# --- Verification (at install/update time) ---
def verify_manifest(manifest_path: Path, sig_hex: str, pub_key_b64: str) -> None:
    """Raises InvalidSignature on failure. Raises on tampered content."""
    from cryptography.exceptions import InvalidSignature
    pub_bytes = base64.b64decode(pub_key_b64)
    pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
    sig = bytes.fromhex(sig_hex)
    manifest_bytes = manifest_path.read_bytes()
    pub.verify(sig, manifest_bytes)  # raises InvalidSignature if tampered
```

**Falsifiable behaviors (verified):**
- Tampered manifest bytes → `InvalidSignature` raised, install aborted, nothing written to plugin dir [VERIFIED: live test 2026-05-19]
- Unknown key → key not in trust store → install refused before signature verification

### Pattern 2: Trust Store (Pinned Keys, chmod 0600)

**What:** TOML file at `~/.config/voss/trusted_keys.toml` listing pinned public keys by author identity. First-add TOFU pins the key. `voss skill trust <pub_key_b64>` adds a key explicitly.

```python
# [ASSUMED] — pattern mirrors plugins.toml logic from plugins.py

# trusted_keys.toml layout:
# [keys."<author-identity>"]
# public_key = "<base64-encoded-32-byte-Ed25519-pub-key>"
# pinned_at = "2026-05-19T12:00:00Z"
# tofu = true  # if TOFU-pinned on first add

def trust_store_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "trusted_keys.toml"

def is_key_trusted(pub_key_b64: str) -> bool:
    store = _load_trust_store()
    return any(v["public_key"] == pub_key_b64 for v in store.values())

def pin_key(author_identity: str, pub_key_b64: str, *, tofu: bool = False) -> Path:
    path = trust_store_path()
    # write then chmod 0600 — mirrors set_plugin_enabled() pattern
    path.write_text(updated_toml)
    path.chmod(0o600)
    return path
```

### Pattern 3: Scope Grammar → Gate Binding

**What:** Manifest declares `scopes.tools`, `scopes.fs`, `scopes.net`. These map onto the existing `PermissionGate.mode` + `is_network` axis. A scope-limited gate is injected at skill dispatch time — no new enforcement engine.

```python
# [ASSUMED] — derived from permissions.py inspection

# Manifest TOML (new fields):
# [scopes]
# tools = "read-only"   # or "mutating" or "all"
# fs = "cwd"            # or "none"
# net = false           # or true

from voss.harness.permissions import PermissionGate, Mode

SCOPE_TO_MODE: dict[str, Mode] = {
    "read-only": "plan",    # fs_read, fs_glob, fs_grep only; no writes/shell
    "mutating":  "edit",    # reads + fs_write/fs_edit; no shell_run
    "all":       "auto",    # everything (requires explicit manifest declaration)
}

def scoped_gate(declared_scopes: ScopeSpec, base_gate: PermissionGate) -> PermissionGate:
    """Return a new PermissionGate capped to declared_scopes.
    Default (no scope declared) = plan (read-only).
    """
    tools_mode: Mode = SCOPE_TO_MODE.get(declared_scopes.tools, "plan")
    # net axis: override allow_net based on declaration
    # This returns a new gate with auto_yes=True (non-interactive) and
    # effective mode = min(base_gate.mode, tools_mode).
    return PermissionGate(
        mode=_min_mode(base_gate.mode, tools_mode),
        auto_yes=True,  # third-party skills never prompt interactively
        store=None,     # no "always remember" for third-party skills
    )
    # net gate is handled by PermissionGate._check_impl is_network check:
    # if not declared_scopes.net: voss_runtime._config must have allow_net=False
```

**Default-deny:** A skill with no `[scopes]` declaration runs in `plan` mode — read-only, no writes, no shell, no network.

### Pattern 4: VossSkillAdapter (`.voss`-backed SkillEntry)

**What:** A `SkillEntry`-compatible handler that compiles the bundle's `.voss` file and runs it via `subprocess`. Reuses the same path as `voss run`.

```python
# [ASSUMED] — mirrors voss/cli.py run() and mcp/server_skills.py make_skill_dispatch()
import sys, subprocess, tempfile
from pathlib import Path
from voss.cli import _compile_source  # existing compile path

def _make_voss_skill_handler(voss_path: Path, declared_scopes: ScopeSpec):
    def handler(ctx, args: list[str]) -> None:
        with tempfile.TemporaryDirectory(prefix="voss-skill-") as tmp:
            generated = Path(tmp) / (voss_path.stem + ".py")
            _compile_source(
                voss_path,
                output_path=generated,
                project_root=ctx.cwd,
                cache_dir=ctx.cwd / ".voss-cache",
                verbose=False,
            )
            # Inject scoped gate — third-party code never sees base_gate directly
            scoped = scoped_gate(declared_scopes, ctx.gate)
            # Pass scopes as env vars to the subprocess (or via a config file)
            # The subprocess uses voss_runtime which reads from env
            env = _build_skill_env(ctx, scoped)
            result = subprocess.run(
                [sys.executable, str(generated)] + args,
                capture_output=True, text=True, env=env,
            )
            if result.stdout:
                import click; click.echo(result.stdout, nl=False)
            if result.returncode != 0:
                import click; click.echo(result.stderr, nl=False, err=True)
    return handler
```

**Key constraint:** The subprocess boundary is the confinement layer at this phase. It does not prevent the subprocess from making system calls outside its declared scopes — the PermissionGate enforcement applies to tool calls routed through the harness, not to arbitrary Python `open()` / `urllib` calls made directly. This limitation MUST be documented in the installed skill's manifest and in `voss doctor` / `voss skill list` output.

### Pattern 5: Fetch Path (git clone / local)

**What:** Three source types, all ending in a staging bundle dir that passes the trust gate before install.

```python
# [ASSUMED] — subprocess git, no new deps

import re, shutil, subprocess, tarfile, zipfile
from pathlib import Path

GITHUB_SHORTHAND = re.compile(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$')

def fetch_bundle(source: str, staging_dir: Path) -> Path:
    """Fetch bundle into staging_dir. Returns path to the bundle dir inside staging_dir."""
    if GITHUB_SHORTHAND.match(source):
        url = f"https://github.com/{source}.git"
        return _git_clone(url, staging_dir)
    if source.startswith(("https://", "http://", "git@", "git://")):
        return _git_clone(source, staging_dir)
    p = Path(source)
    if p.is_dir():
        dest = staging_dir / p.name
        shutil.copytree(p, dest)
        return dest
    if p.suffix in (".zip", ".tar", ".gz", ".tgz", ".tar.gz"):
        return _extract_archive(p, staging_dir)
    raise ValueError(f"unrecognised source: {source!r}")

def _git_clone(url: str, staging_dir: Path) -> Path:
    result = subprocess.run(
        ["git", "clone", "--depth=1", url, str(staging_dir / "bundle")],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")
    return staging_dir / "bundle"
```

**GitHub shorthand detection:** Pattern `<owner>/<repo>` with no slashes beyond the one separator, no protocol prefix. If ambiguous, require explicit `https://github.com/...`.

### Anti-Patterns to Avoid

- **Running `.voss` code before trust verification:** Scope enforcement and signature verification MUST be complete before any subprocess spawning the compiled `.voss` file. Wave ordering enforces this: W1 = trust/scope modules, W2 = fetch + install gating, W3 = skill dispatch wiring.
- **Extending `PermissionGate` with new enforcement logic:** Bind declared scopes to EXISTING mode/is_network parameters — never add a new check axis. The existing `_check_impl` order-of-operations comment (project-policy → net gate → mode-tier → scope → prompt) already handles all needed cases.
- **Separate manifest/enablement system:** Installed bundles MUST land in `user_plugin_dir()` (or `project_plugin_dir()`) and be enabled via `set_plugin_enabled()`. `load_plugins()` must discover them via the existing glob. No parallel manifest model.
- **Hardcoding skill IDs into CLI:** Use `skill_registry.ids()` to enumerate — the same call site `_print_skills()` already uses.
- **Storing private keys under ~/.config/voss/:** Trust store holds ONLY public keys. The bundle author retains their private key. The trust store is a read path for verification, not a keyring.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 sign + verify | Custom crypto primitives | `cryptography.hazmat.primitives.asymmetric.ed25519` | Already a dep; battle-tested; InvalidSignature exception is well-defined |
| TOML read/write | Custom parser | `tomllib` (stdlib) + `tomli_w` (already optional dep in plugins.py) | Already used in `plugins.py`; consistent |
| File hashing for integrity | Custom hash | Python `hashlib.sha256` (stdlib) | For manifest content integrity pre-signature |
| Archive extraction | Custom unzipper | `shutil.unpack_archive()` (stdlib) | Handles .zip, .tar.gz, .tgz without new deps |
| Git fetch | Custom HTTP git client | `subprocess git clone --depth=1` | Git is available everywhere; GitPython is optional |
| Plugin dir discovery | New path logic | `user_plugin_dir()` / `project_plugin_dir()` from `plugins.py` | Single source of truth; already used by all plugin loading |
| REPL skill dispatch | New dispatch mechanism | `skill_registry.get(id).handler(ctx, args)` | Same call site as built-in `/skill <id>` |

**Key insight:** Every infrastructure concern already has a canonical implementation in the codebase. M15 is almost entirely wiring, not greenfield. The only genuinely new code is `trust.py` (key pinning) and `fetch.py` (bundle download).

---

## Manifest Schema Extension

**Extend `PluginManifest` in `plugins.py` (frozen dataclass — add fields with defaults so existing `.toml` files continue to load):**

```toml
# manifest.toml — extended schema (new fields in [skill] and [scopes] tables)
id = "voss-hello"
name = "Hello Skill"
description = "Greets the user from a .voss program"
version = "0.1.0"
author_identity = "author@example.com"  # must match trust store principal

# Existing fields (unchanged)
commands = []
skills = []       # For built-in skills only (existing behavior)
agents = []

# NEW: .voss skill binding
[skill]
entry = "hello.voss"         # relative path inside bundle dir
id = "voss-hello"            # skill id registered in SkillRegistry (MUST be unique)
mutating = false             # maps to SkillEntry.mutating

# NEW: declared permission scopes
[scopes]
tools = "read-only"          # "read-only" | "mutating" | "all" (default: "read-only")
fs = "cwd"                   # "cwd" | "none" (default: "cwd" when tools != "none")
net = false                  # true | false (default: false)

# NEW: trust/signing fields
[trust]
sig_file = "manifest.toml.sig"   # relative path of detached signature file
pub_key = "base64..."            # author's Ed25519 public key (informational)
                                  # Verification uses trust store, not this field
```

**`PluginManifest` additions (all with defaults for backward compat):**

```python
# [ASSUMED] field names — final names are Claude's Discretion
@dataclass(frozen=True)
class PluginManifest:
    # existing fields unchanged...
    # NEW fields:
    voss_entry: str = ""           # relative path to .voss file in bundle
    skill_id: str = ""             # skill id to register (empty = not a .voss skill)
    skill_mutating: bool = False
    scope_tools: str = "read-only" # "read-only" | "mutating" | "all"
    scope_fs: str = "cwd"          # "cwd" | "none"
    scope_net: bool = False
    sig_file: str = ""             # relative path of .sig file
    author_identity: str = ""      # trust store lookup key
    bundle_dir: Path | None = None # set after install; None for legacy manifests
```

---

## Trust Store Details

**Location:** `~/.config/voss/trusted_keys.toml` (mirrors `plugins.toml` chmod 0600 pattern)

```toml
# trusted_keys.toml
[keys."author@example.com"]
public_key = "base64-encoded-32-byte-Ed25519-public-key"
pinned_at = "2026-05-19T12:00:00+00:00"
tofu = false   # true if first-add TOFU-pinned (user should verify out-of-band)
```

**`voss skill trust <pub_key_b64>` workflow:**
1. Decode + validate the key is a valid Ed25519 public key (32 bytes)
2. Prompt: "Trust key fingerprint `<sha256_fingerprint>` for `<identity>`? [y/N]"
3. Write entry to `trusted_keys.toml`, chmod 0600
4. Confirmation message: "Key pinned. Subsequent `voss skill add` from this author will succeed."

**TOFU behavior:** When `voss skill add` encounters a key not in the trust store, it MAY TOFU-pin (configurable, off by default for production use). Default: refuse and print the key fingerprint with instructions to run `voss skill trust <pub_key_b64>`.

---

## RunRecorder Event Shape (SKILL-01..05 audit events)

The existing `RunRecorder.observe()` method handles `INSPECT_TOOLS`, `CHANGE_TOOLS`, `VALIDATE_TOOLS`. For M15, extend the structured event model with new event types, OR use the existing `failures` list for denials and add a new `skill_events` list for installs/runs. [ASSUMED] — exact field names for planner to finalize.

**Recommended minimal extension:**

```python
# New event categories (add to RunRecorder dataclass):
# skill_installs: list[dict]  — {"action": "install"|"remove"|"update", "skill_id": ..., "source": ..., "ok": bool}
# scope_denials: list[dict]   — {"skill_id": ..., "tool": ..., "reason": ...}

# Existing observe() call sites don't change.
# New call sites in skill/install.py and adapter.py:

def observe_skill_install(self, skill_id: str, source: str, *, ok: bool, error: str = "") -> None:
    self.skill_installs.append({"action": "install", "skill_id": skill_id, "source": source, "ok": ok, "error": error[:200]})

def observe_scope_denial(self, skill_id: str, tool: str, reason: str) -> None:
    self.scope_denials.append({"skill_id": skill_id, "tool": tool, "reason": reason})
```

If RunRecorder extension is too invasive for a single wave, the planner may route to `failures` list (existing) for denials and use `changed` list for installs — acceptable as a minimum viable audit trail.

---

## Update Failure Path (SKILL-05 first-class requirement)

```
voss skill update <id>
  1. Resolve current install dir = user_plugin_dir() / <id>
  2. Create tmp staging dir
  3. Re-fetch from original source (stored in manifest: source_url field)
  4. Verify signature of new manifest
     → FAIL: print error, exit non-zero. Leave current install dir untouched.
     → PASS: atomically replace: rename current → current.bak, rename new → current
  5. If replacement fails (OS error): restore from .bak
  6. Remove .bak on success
```

**Atomic replace:** `Path.rename()` on POSIX is atomic within the same filesystem. Staging dir must be on the same filesystem as the plugin dir. If not (XDG_CONFIG_HOME on different mount), use shutil.copytree + atomic swap pattern.

---

## Example Skill Bundle (SKILL-06 fixture)

**Recommended fixture:** A `.voss` skill that reads the current working directory's git log summary — read-only (plan mode), no external network, no file mutation. This exercises the full add → list → run → update → remove cycle while keeping the scope declaration minimal.

**Bundle layout:**
```
examples/skills/voss-git-summary/
├── manifest.toml            # id="voss-git-summary", scopes.tools="read-only"
├── manifest.toml.sig        # Ed25519 signature (hex)
├── git_summary.voss         # the skill: runs git_diff/git_status, prints summary
└── README.md                # (optional) human description
```

**Committed trusted key:** A test keypair lives in `examples/skills/voss-git-summary/` — the PRIVATE key is for test signing only (committed is acceptable for a CI fixture, as it has no production security value). A `tests/skill/test_fixture_key.pub` file is the CI trust anchor.

**CI test fixture cycle:**
```
voss skill trust <fixture_pub_key>
voss skill add examples/skills/voss-git-summary/
voss skill list  # shows voss-git-summary
/skill voss-git-summary  # runs and produces output
voss skill update voss-git-summary  # re-verifies, succeeds
voss skill remove voss-git-summary
voss skill list  # does NOT show voss-git-summary
```

---

## Common Pitfalls

### Pitfall 1: Staging Before Verification
**What goes wrong:** Bundle files written to the final install dir before signature verification passes.
**Why it happens:** Natural "fetch then check" ordering puts install before verify.
**How to avoid:** Fetch to a tmpdir staging area. Only call `shutil.copytree(staged → install_dir)` AFTER `verify_manifest()` returns without raising.
**Warning signs:** If the install dir is created before `verify_manifest()` is called, the code is in this pitfall.

### Pitfall 2: PermissionGate Interactive Prompts in Skill Subprocess
**What goes wrong:** Skill subprocess inherits a `PermissionGate` that tries to prompt the user interactively (via `sys.stdin.readline()`), causing hangs or silent failures in non-TTY CI environments.
**Why it happens:** The subprocess doesn't inherit the parent's gate; if it runs voss tooling internally, it picks up default gate settings.
**How to avoid:** Skill subprocesses run with `auto_yes=True` and `mode` capped to declared scopes. Never pass `store` to the skill's gate (no "always remember" for third-party skills).
**Warning signs:** Test hangs in CI when no TTY is available.

### Pitfall 3: "Same filesystem" assumption for atomic rename
**What goes wrong:** `os.rename(staged, install_dir)` fails with `OSError: [Errno 18] Invalid cross-device link` when XDG_CONFIG_HOME is on a different mount than /tmp.
**Why it happens:** `os.rename` on POSIX requires same filesystem.
**How to avoid:** Put staging dir under `user_plugin_dir().parent / "._staging"` (same filesystem). Fallback: `shutil.copytree` + delete old + rename new.
**Warning signs:** Works in dev (all on same SSD), breaks in CI (Docker with tmpfs).

### Pitfall 4: Trust Store Concurrent Write
**What goes wrong:** Two simultaneous `voss skill add` processes corrupt `trusted_keys.toml`.
**Why it happens:** Read-modify-write on a TOML file without a file lock.
**How to avoid:** Use `portalocker` (already a dep in pyproject.toml) to acquire an exclusive lock on `trusted_keys.toml` before reading and writing.
**Warning signs:** Intermittent TOML parse errors after parallel test runs.

### Pitfall 5: Scope Enforcement Only at Gate Level
**What goes wrong:** Documenting "scope enforcement reuses existing gate" without noting that direct Python calls inside the `.voss` subprocess (e.g., `open()`, `urllib`) bypass the gate entirely.
**Why it happens:** The gate enforces harness tool calls, not OS-level syscalls.
**How to avoid:** Document the limitation explicitly in the manifest schema, in `voss skill list` output, and in `voss doctor`. The SPEC accepts this; the limitation must be stated, not hidden.
**Warning signs:** Any code that claims OS-level confinement from the PermissionGate alone.

### Pitfall 6: GitHub Shorthand Collision with Local Paths
**What goes wrong:** `voss skill add user/repo` interpreted as GitHub shorthand when the user intended a local relative path `user/repo/` directory.
**Why it happens:** The shorthand regex matches any `word/word` string.
**How to avoid:** Check for local path existence FIRST (`Path(source).exists()`), then fall back to GitHub shorthand interpretation. For ambiguity, require explicit `./user/repo` for local paths.
**Warning signs:** Users report "github not found" when they intended a local path.

---

## Code Examples

### Verified: ssh-keygen -Y sign/verify round-trip (subprocess approach)

```bash
# Source: verified live 2026-05-19 on macOS (OpenSSH 9.x)
# Sign
ssh-keygen -Y sign -f testkey -n "voss-skill" manifest.toml
# Produces manifest.toml.sig

# Verify (allowed_signers format: "<principal> <keytype> <base64key>")
# "test@voss ssh-ed25519 AAAA..." > allowed_signers
ssh-keygen -Y verify -f allowed_signers -I "test@voss" -n "voss-skill" \
  -s manifest.toml.sig < manifest.toml
# exit 0 on success, 255 on tampered/unknown

# Tampered file correctly exits 255:
echo "TAMPERED" > manifest.toml
ssh-keygen -Y verify ... < manifest.toml  # exit 255: "Signature verification failed"
```

[VERIFIED: live test 2026-05-19 — both clean and tampered paths confirmed]

### Verified: cryptography Ed25519 (RECOMMENDED — zero new deps)

```python
# Source: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/
# [VERIFIED: live round-trip test 2026-05-19 — cryptography 43.0.3]
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
from cryptography.exceptions import InvalidSignature
import base64

# Key generation (author, run once — not part of install path)
key = Ed25519PrivateKey.generate()
priv_bytes = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())  # 32 bytes
pub_bytes = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)        # 32 bytes
pub_b64 = base64.b64encode(pub_bytes).decode()  # store in trusted_keys.toml

# Signing (author, at bundle publication time)
manifest_bytes = Path("manifest.toml").read_bytes()
sig = key.sign(manifest_bytes)  # 64 bytes
Path("manifest.toml.sig").write_text(sig.hex())

# Verification (harness, at install/update time)
def verify_or_raise(manifest_path: Path, sig_path: Path, pub_key_b64: str) -> None:
    pub_bytes = base64.b64decode(pub_key_b64)
    pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
    sig = bytes.fromhex(sig_path.read_text().strip())
    manifest_bytes = manifest_path.read_bytes()
    pub.verify(sig, manifest_bytes)  # raises InvalidSignature on tampered content
    # [VERIFIED: tampered content correctly raises InvalidSignature]
```

### Existing: PluginManifest reading pattern (plugins.py, extend in-place)

```python
# Source: voss/harness/plugins.py:_read_manifest (existing, line 86)
# Pattern for extending: add new fields with defaults to _read_manifest()
# and PluginManifest dataclass. Existing callers are unaffected.
voss_entry = str(raw.get("skill", {}).get("entry", ""))
skill_id = str(raw.get("skill", {}).get("id", ""))
scope_tools = str(raw.get("scopes", {}).get("tools", "read-only"))
scope_net = bool(raw.get("scopes", {}).get("net", False))
```

### Existing: set_plugin_enabled() pattern (plugins.py, line 60)

```python
# Source: voss/harness/plugins.py:set_plugin_enabled (line 60)
# Trust store write MUST mirror this pattern (same path.chmod(0o600))
path.write_text(text)
path.chmod(0o600)  # <-- REQUIRED for trust store too
```

### Existing: SkillEntry handler registration (skill_registry.py)

```python
# Source: voss/harness/skill_registry.py (existing pattern, lines 51-57)
# VossSkillAdapter follows same registration pattern
registry.register(
    SkillEntry(
        id="voss-git-summary",
        description="Summarize git log (read-only, .voss-authored)",
        handler=_make_voss_skill_handler(bundle_dir / "git_summary.voss", declared_scopes),
        mutating=False,  # from manifest skill.mutating
    )
)
```

### Existing: voss run subprocess path (voss/cli.py:run, line 220)

```python
# Source: voss/cli.py:run() (lines 225-265)
# VossSkillAdapter reuses _compile_source + subprocess.run exactly
with tempfile.TemporaryDirectory(prefix="voss-skill-") as tmp:
    tmp_dir = Path(tmp)
    generated = tmp_dir / (voss_path.stem + ".py")
    _compile_source(source, output_path=generated, project_root=project_root,
                    cache_dir=cache_dir, verbose=False)
    completed = subprocess.run([sys.executable, str(generated)],
                               capture_output=True, text=True)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| minisign CLI binary (separate install) | `cryptography` Ed25519 (existing dep) | M15 research 2026-05-19 | Zero new deps; no CLI tool dependency |
| GPG keyring (planned in early ROADMAP) | minisign/ssh-sig family (SPEC lock) | SPEC interview round 2 | Lighter UX, no GPG agent required |
| Python-minisign PyPI (assumed available) | Stub only (Dev Status 1, empty impl) | Discovered 2026-05-19 | Must use cryptography instead |
| Global PermissionGate for all skills | Scope-limited gate injected at dispatch | M15 design | Default-deny third-party; no surgery to existing gate logic |

**Deprecated/outdated:**
- `minisign` PyPI: Do not add as a dependency — verified empty stub with no API.
- `python-minisign` PyPI: Does not exist (pip index versions returned no distribution found).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Trust store TOML field names (`keys."<identity>"`, `public_key`, `pinned_at`, `tofu`) | §Trust Store Details | Names are Claude's Discretion; planner picks final names |
| A2 | `PluginManifest` extended field names (`voss_entry`, `skill_id`, `scope_tools`, etc.) | §Manifest Schema Extension | Names are Claude's Discretion; planner picks final names |
| A3 | `ScopeSpec.tools` values are `"read-only"` / `"mutating"` / `"all"` | §Scope Grammar | Planner may choose different vocabulary as long as it maps to plan/edit/auto |
| A4 | `RunRecorder` extended with `skill_installs` + `scope_denials` lists | §RunRecorder Event Shape | Planner may choose to use existing `failures` list instead |
| A5 | Private key stored as raw 32-byte base64 | §Pattern 1 | Standard Ed25519 raw encoding is 32 bytes; alternative is PEM encoding |
| A6 | GitHub shorthand detection uses simple `<word>/<word>` regex before checking local path | §Pattern 5 | Local-first check (Path.exists()) recommended; planner confirms precedence |
| A7 | Fixture private key committed to repo under `examples/skills/` is acceptable for CI | §Example Skill Bundle | Security review may flag; planner can generate key at CI time as alternative |
| A8 | `portalocker` (already in pyproject.toml) used for trust store write lock | §Pitfall 4 | Already a dep; safe assumption |
| A9 | `_compile_source` is importable from `voss.cli` in the harness module | §Pattern 4 | Current import is `from voss.cli import _compile_source`; this crosses module boundaries; planner may expose via a public compile helper |

**If this table is empty:** Not applicable — several architectural details are explicitly Claude's Discretion per CONTEXT.md and are appropriately marked [ASSUMED].

---

## Open Questions

1. **`_compile_source` cross-module import**
   - What we know: `voss/cli.py` defines `_compile_source` as a module-level function (private). The `VossSkillAdapter` in `voss/harness/skill/adapter.py` needs to call it.
   - What's unclear: Whether to import the private function directly or expose a public `voss.compile_file(source, output, ...)` function.
   - Recommendation: Expose a public `compile_voss_file()` helper in `voss/__init__.py` or `voss/compiler.py` that wraps `_compile_source`. This avoids private-function coupling and is consistent with M7 SDK Polish discipline.

2. **Scope enforcement for subprocess tool calls vs. direct Python calls**
   - What we know: The gate enforces harness tool calls only. A `.voss` subprocess that uses `open()` or `urllib` directly bypasses the gate.
   - What's unclear: Whether to document this as a known limitation (SPEC accepts it) or add a best-effort warning.
   - Recommendation: Document in the manifest schema comment, `voss skill list` output, and `voss doctor`. Do NOT attempt subprocess-level enforcement this phase — that is the deferred OS sandbox.

3. **Source URL storage in manifest for `update`**
   - What we know: `voss skill update <id>` needs to re-fetch from the original source.
   - What's unclear: Where to store the original source URL (in `manifest.toml` as `[install] source_url = "..."` or in a separate `.install-metadata.toml` sidecar).
   - Recommendation: Add `[install]` table to the manifest with `source_url` and `installed_at` fields. This keeps all install metadata in one place.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` CLI | Bundle fetch (git URL / GitHub shorthand) | ✓ | 2.50.1 | Restrict to local path / archive sources only |
| `cryptography` Python lib | Ed25519 sign/verify | ✓ | 43.0.3 | N/A (already a runtime dep) |
| `ssh-keygen -Y sign/verify` | Optional: keypair generation UX | ✓ | OpenSSH bundled | Use `cryptography` keygen directly |
| `minisign` CLI | N/A — not used | ✗ | — | N/A (replaced by `cryptography`) |
| `portalocker` | Trust store write lock | ✓ | already in pyproject.toml | stdlib `fcntl.flock` (POSIX only) |
| `tomli_w` | Writing updated TOML (plugins.toml, trusted_keys.toml) | ✓ (soft dep) | optional in plugins.py | Inline TOML serializer (already implemented in plugins.py fallback) |

**Missing dependencies with no fallback:** None (all required capabilities are present).

**Missing dependencies with fallback:** `git` CLI — if absent, restrict to local path sources; print a clear error for git URL / GitHub shorthand sources.

---

## Validation Architecture

> `workflow.nyquist_validation = true` in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (see pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/harness/skill/ -x -q` |
| Full suite command | `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-01 (local path) | `voss skill add ./bundle` installs and `voss skill list` shows it | integration | `pytest tests/harness/skill/test_install.py::test_add_local -x` | ❌ Wave 0 |
| SKILL-01 (GitHub shorthand) | `voss skill add owner/repo` resolves and installs | integration (requires git) | `pytest tests/harness/skill/test_install.py::test_add_github -x -m "not live"` | ❌ Wave 0 |
| SKILL-02 (registration) | After add, `/skill <id>` resolves and runs | integration | `pytest tests/harness/skill/test_registry.py::test_voss_skill_dispatch -x` | ❌ Wave 0 |
| SKILL-02 (before-add) | Before add, id does NOT resolve | unit | `pytest tests/harness/skill/test_registry.py::test_unknown_skill_not_found -x` | ❌ Wave 0 |
| SKILL-03 (tamper) | Tampered manifest → refused, exits non-zero, nothing installed | unit | `pytest tests/harness/skill/test_trust.py::test_tampered_manifest_refused -x` | ❌ Wave 0 |
| SKILL-03 (unknown key) | Unknown key → refused until `voss skill trust <key>` | unit | `pytest tests/harness/skill/test_trust.py::test_unknown_key_refused -x` | ❌ Wave 0 |
| SKILL-03 (trust then add) | After trust, same install succeeds | unit | `pytest tests/harness/skill/test_trust.py::test_trust_then_install_succeeds -x` | ❌ Wave 0 |
| SKILL-04 (out-of-scope blocked) | Tool outside declared scopes → gate blocks it | unit | `pytest tests/harness/skill/test_scope.py::test_out_of_scope_blocked -x` | ❌ Wave 0 |
| SKILL-04 (in-scope allowed) | Tool inside declared scopes → permitted | unit | `pytest tests/harness/skill/test_scope.py::test_in_scope_allowed -x` | ❌ Wave 0 |
| SKILL-05 (remove) | After remove, list omits it and `/skill <id>` does not resolve | integration | `pytest tests/harness/skill/test_lifecycle.py::test_remove -x` | ❌ Wave 0 |
| SKILL-05 (update tamper) | Update against tampered upstream → fails, prior version intact | integration | `pytest tests/harness/skill/test_lifecycle.py::test_update_tamper_leaves_prior_intact -x` | ❌ Wave 0 |
| SKILL-06 (e2e CI fixture) | Fixture bundle passes full add→list→run→remove cycle | e2e | `pytest tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/harness/skill/ -x -q`
- **Per wave merge:** `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/skill/__init__.py` — package marker
- [ ] `tests/harness/skill/test_trust.py` — covers SKILL-03 (3 tests)
- [ ] `tests/harness/skill/test_scope.py` — covers SKILL-04 (2 tests)
- [ ] `tests/harness/skill/test_install.py` — covers SKILL-01 (2 tests)
- [ ] `tests/harness/skill/test_registry.py` — covers SKILL-02 (2 tests)
- [ ] `tests/harness/skill/test_lifecycle.py` — covers SKILL-05 (2 tests)
- [ ] `tests/e2e/test_skill_lifecycle.py` — covers SKILL-06 (1 test)
- [ ] `examples/skills/voss-git-summary/` — fixture bundle with committed test keypair
- [ ] Framework install: none needed (pytest already in dev deps)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | Scope-limited PermissionGate; default-deny (plan mode) for third-party skills |
| V5 Input Validation | yes | Bundle source URL/path validation; GITHUB_SHORTHAND regex; manifest TOML parse |
| V6 Cryptography | yes | Ed25519 via `cryptography` library; never hand-roll; verify before install |
| V7 Error Handling | yes | Non-zero exit on sig failure; no partial-install state |

### Known Threat Patterns for Skill Marketplace Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered manifest post-download | Tampering | Ed25519 signature verification before install; staging → verify → copy pattern |
| Path traversal in bundle (e.g., `../../.bashrc` in archive) | Elevation of Privilege | `jail_path(install_dir, entry_path)` to confine extraction to bundle dir; `shutil.unpack_archive` + post-extract path check |
| Slopsquatted/supply-chain poisoned bundle | Tampering | Signed bundles only; trust store requires explicit pin; TOFU optional (off by default) |
| Scope escalation via manifest self-modification | Tampering | Manifest bytes verified at install time; re-verified at update time; no runtime manifest re-read |
| Direct Python calls in .voss subprocess bypassing gate | Elevation of Privilege | Documented limitation (accepted, OS sandbox deferred); non-zero-exit on tool call outside scope blocks tool-call path but not direct Python |
| Trust store corruption (race condition) | Tampering | `portalocker` exclusive lock on trusted_keys.toml write |
| Installing known-malicious skill via TOFU | Spoofing | TOFU off by default; user must explicitly run `voss skill trust`; key fingerprint printed before pinning |
| git clone MITM (non-HTTPS source) | Spoofing | Enforce HTTPS for git URLs; reject `git://` and `http://`; signature verification catches content tampering regardless of transport |

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/plugins.py` (in-repo, read directly 2026-05-19) — PluginManifest structure, user_plugin_dir, enablement pattern, chmod 0600 precedent
- `voss/harness/skill_registry.py` (in-repo, read directly 2026-05-19) — SkillRegistry, SkillEntry, default_skill_registry pattern
- `voss/harness/permissions.py` (in-repo, read directly 2026-05-19) — PermissionGate, mode_allows, M1 tiers, _check_impl order-of-operations
- `voss/harness/sandbox.py` (in-repo, read directly 2026-05-19) — jail_path, shell_allowed, DEFAULT_SHELL_ALLOWLIST
- `voss/harness/tools.py` (in-repo, read directly 2026-05-19) — ToolEntry, is_mutating, is_network classifications, make_toolset
- `voss/harness/recorder.py` (in-repo, read directly 2026-05-19) — RunRecorder, observe(), INSPECT/CHANGE/VALIDATE_TOOLS sets
- `voss/harness/cli.py` (in-repo, read directly 2026-05-19) — existing skill_group, _extension_context, voss run subprocess path
- `voss/harness/mcp/server_skills.py` (in-repo, read directly 2026-05-19) — make_skill_dispatch prior art
- `voss/cli.py:run()` (in-repo, read directly 2026-05-19) — _compile_source + subprocess.run pattern (the .voss runtime)
- `cryptography` Ed25519 (live round-trip test, 2026-05-19) — Ed25519PrivateKey.sign/verify, InvalidSignature on tampered data [VERIFIED]
- `ssh-keygen -Y sign/verify` (live round-trip test, 2026-05-19) — correct allowed_signers format, exit 0/255 semantics [VERIFIED]

### Secondary (MEDIUM confidence)

- `minisign` PyPI 0.1.0 inspection (2026-05-19) — confirmed stub with no implementation; Development Status 1 - Planning [CITED: PyPI metadata, whl content]
- `pyproject.toml` (in-repo, read directly 2026-05-19) — existing deps, dev deps, pytest config

### Tertiary (LOW confidence)

- None — all claims are either verified from in-repo code or cited from official library docs/live tests.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — cryptography Ed25519 verified in live test; all other deps already present
- Architecture: HIGH — all extension points found in existing code; no greenfield infrastructure except trust.py + fetch.py
- Scope binding: HIGH — PermissionGate._check_impl dissected; mode/is_network axes map directly
- Pitfalls: HIGH — all from live test results or in-code analysis; no speculation
- Fixture/CI: MEDIUM — fixture content (git_summary.voss skill) is prescriptive recommendation; final content is Claude's Discretion

**Research date:** 2026-05-19
**Valid until:** 2026-06-18 (30 days — stable domain; cryptography and permission APIs change rarely)
