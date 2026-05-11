# Phase M1: Harness Happy Path - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** M1-harness-happy-path
**Areas discussed:** voss edit scope contract, Permission mode semantics, voss doctor checks + failure UX, M1 session snapshot shape

---

## voss edit scope contract

### Default editable scope

| Option | Description | Selected |
|--------|-------------|----------|
| Just the path | Only the file/dir passed as `<path>`. Anything else requires explicit user widening. | |
| Path + sibling tests | `<path>` plus mirror in `tests/`. Common case for safe edits with test feedback. | ✓ |
| Path + grep-related refs | `<path>` plus files that import/reference it. Wider blast radius. | |
| Path + agent-proposed set | Agent proposes set at start, user approves once, locked for session. | |

**User's choice:** Path + sibling tests.

### REPL vs one-shot

| Option | Description | Selected |
|--------|-------------|----------|
| REPL session | Drops into interactive loop; user issues turns, sees diffs, approves. Exits on `/quit`/Ctrl-D. | ✓ |
| One-shot with task arg | `voss edit <path> "<task>"` single turn; REPL only without task. | |
| Either based on TTY | TTY → REPL; non-TTY (piped) → one-shot from stdin. | |

**User's choice:** REPL session.

### Out-of-scope behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file permission prompt | Tool call paused; `[y/once/always/n]` prompt to expand scope. | ✓ |
| Abort with explanation | Agent must propose `/widen <path>` first; tool call fails until run. | |
| Auto-allow read, prompt on write | Reads outside scope free; writes outside scope prompt. | |

**User's choice:** Per-file permission prompt.

---

## Permission mode semantics

### plan/edit/auto matrix

| Option | Description | Selected |
|--------|-------------|----------|
| Strict tiers | plan=read-only; edit=read+fs_write/fs_edit (prompt per write); auto=all incl shell_run (allowlist still enforced). | ✓ |
| Prompt-heavy tiers | Same tool sets; every mutating call prompts even in auto. | |
| Plan / approval / yolo | plan=read-only; edit=mutating w/ diff approve each; auto=no prompts (allowlist only). | |

**User's choice:** Strict tiers.

### Mode selection mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Per-command default + flag | `voss do`→plan; `voss edit`→edit; `voss chat`→plan. `--mode=...` overrides. `/mode <name>` in REPL. | ✓ |
| Always explicit | Every command requires `--mode=...` or prompts on first risky tool call. | |
| Config-driven | Default from `.voss/permissions.yml` or `~/.config/voss/config.toml`. | |

**User's choice:** Per-command default + `/mode`.
**Notes:** User raised a related but distinct concern about auth — "envisioning `/login` to sign up with provider, and `/model` to switch between multiple. Pulls Keychain keys." Captured as separate decisions D-08..D-10 in CONTEXT.md.

---

## Auth REPL surface (raised during mode-select turn)

| Option | Description | Selected |
|--------|-------------|----------|
| `/login` + `/model` in REPL | OAuth or guide to creds; list+switch model; falls back to auto-resolve from Keychain. Persists to config. | ✓ |
| Just `/model`, `/login` deferred | Assume already logged in; only switch between detected providers. | |
| CLI flags only | `--provider=... --model=...`; no slash commands in M1. | |

**User's choice:** `/login` + `/model` in REPL.

---

## voss doctor checks + failure UX

### Check set

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal essentials | Provider auth, Python version, voss compiler, git, cwd writable, .voss/.voss-cache creatable. | ✓ |
| Above + network reachability | Plus HEAD-ping Anthropic/OpenAI API URLs. | |
| Above + tool smoke tests | Plus exec each tool once on temp scratch. | |

**User's choice:** Minimal essentials.

### Failure UX

| Option | Description | Selected |
|--------|-------------|----------|
| Diagnose + suggest, never fix | Print what's wrong + exact fix command; user runs it. | ✓ |
| Diagnose + offer to fix | `[y/N]` to run fixable items inline. | |
| Diagnose only, link to docs | Just failures + docs URL; no inline suggestions. | |

**User's choice:** Diagnose + suggest, never fix.

---

## M1 session snapshot shape

### Storage location

| Option | Description | Selected |
|--------|-------------|----------|
| Keep XDG state for M1 | Don't touch session.py location; verify redaction; leave `.voss/sessions/` migration to M2. | ✓ |
| Move to .voss/sessions/ now | M1 writes project-local; pulls M2 forward; risks half-built cognition. | |
| Dual-write, project preferred | `.voss/sessions/` when inside project; XDG fallback; resume reads both. | |

**User's choice:** Keep XDG state for M1.

### Redaction guarantee

| Option | Description | Selected |
|--------|-------------|----------|
| Schema-allowlist | Fixed dataclass fields; unit test scans saved JSON for secret patterns and fails build on match. | ✓ |
| Schema + scrubber pass | Allowlist + regex scrubber over turn content. Belt-and-suspenders. | |
| Trust schema, no test | Ship as-is; document; revisit if leak found. | |

**User's choice:** Schema-allowlist.

---

## Claude's Discretion

- `voss tools` and `voss config` table layout — match existing `voss sessions` style.
- REPL prompt string, color/glyph treatment — match `render.py` conventions.
- Path-jail edge cases (symlinks outside cwd) — safe-deny defaults from existing `sandbox.py`.
- Shell allowlist for `auto` mode — reuse existing list; expand only if needed.

## Deferred Ideas

- `.voss/sessions/` durable session move (M2).
- Network reachability check + tool smoke tests in doctor.
- Doctor offers to fix inline.
- Path+grep-refs default edit scope.
- Agent-proposed file set at session start.
- Regex scrubber over turn content.
- Config-driven default mode.
- `/mode auto` mid-session without `--confirm`.
