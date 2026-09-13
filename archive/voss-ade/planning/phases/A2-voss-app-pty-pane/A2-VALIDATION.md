---
phase: A2
slug: voss-app-pty-pane
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase A2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from A2-RESEARCH.md "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (frontend unit) + Rust `cargo test` (backend) + Playwright (Tauri E2E) |
| **Config file** | `apps/voss-app/vitest.config.ts` (Wave 0 if absent); `crates/voss-app-core/Cargo.toml` test config |
| **Quick run command** | `pnpm vitest run --reporter=dot` |
| **Full suite command** | `pnpm vitest run && cargo test -p voss-app-core` |
| **Estimated runtime** | ~60 seconds (full); <10s (quick) |

---

## Sampling Rate

- **After every task commit:** Run `pnpm vitest run --reporter=dot`
- **After every plan wave:** Run `pnpm vitest run && cargo test -p voss-app-core`
- **Before `/gsd:verify-work`:** Full suite green **+ D-02 flood performance assertion passed**
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| PTY-01 | `$SHELL` spawns with `TERM`/`COLORTERM` env | Integration (Rust) | `cargo test -p voss-app-core test_pty_spawn_env` | ❌ W0 | ⬜ pending |
| PTY-02 | Bidirectional round-trip (`echo hi` → `hi\r\n`) | Integration (Rust) | `cargo test -p voss-app-core test_pty_round_trip` | ❌ W0 | ⬜ pending |
| PTY-02 | D-02 flood: `yes` — UI responsive, input echoed | E2E perf | `pnpm tsx scripts/test-flood-perf.ts` (Playwright) | ❌ W0 | ⬜ pending |
| PTY-02 | D-02 cat: `cat /dev/urandom \| strings` no freeze | E2E perf | `pnpm tsx scripts/test-flood-perf.ts --cat` | ❌ W0 | ⬜ pending |
| PTY-03 | 10k scrollback; `⌘F` finds line 9999 | E2E | `pnpm playwright test pty-scrollback` | ❌ W0 | ⬜ pending |
| PTY-03 | `⌘⇧K` clears scrollback | E2E | `pnpm playwright test pty-clear` | ❌ W0 | ⬜ pending |
| PTY-04 | Multi-line paste → banner shows | Unit (FE) | `pnpm vitest run PasteGuard` | ❌ W0 | ⬜ pending |
| PTY-04 | `⌘⇧V` bypasses banner | Unit (FE) | `pnpm vitest run PasteGuard` | ❌ W0 | ⬜ pending |
| PTY-04 | `⌘C` w/ selection = copy | E2E | `pnpm playwright test pty-copy` | ❌ W0 | ⬜ pending |
| PTY-04 | `⌘C` w/o selection = SIGINT (`^C`) | E2E | `pnpm playwright test pty-sigint` | ❌ W0 | ⬜ pending |
| PTY-05 | OSC 8 URL `⌘+click` opens browser (mock) | E2E | `pnpm playwright test pty-osc8` | ❌ W0 | ⬜ pending |
| PTY-06 | OSC 0/2 title → header; pgid fallback | E2E + Rust | `pnpm playwright test pty-title` + `cargo test test_foreground_pgid` | ❌ W0 | ⬜ pending |
| PTY-07 | Shell exit → `[exited N]` banner; Restart works | E2E | `pnpm playwright test pty-exit-restart` | ❌ W0 | ⬜ pending |
| PTY-08 | `vim` alt-screen renders + `:q` clean | Manual | manual checklist | Manual | ⬜ pending |
| PTY-08 | `htop` TUI renders + `q` exits | Manual | manual checklist | Manual | ⬜ pending |
| PTY-08 | `tmux` / `less` alt-screen correct | Manual | manual checklist | Manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## D-02 Flood Performance Assertion (hardest contract)

**Metric:** While `yes` or `cat /dev/urandom | strings` floods the pane, the frontend `requestAnimationFrame` p95 delta must stay < 33ms (≤2× the 60fps frame budget). Keystrokes sent via `pty_write` during flood must echo within 200ms.

**Procedure:**
1. Start `yes` in the PTY (infinite flood).
2. rAF loop records actual frame deltas → assert p95 < 33ms.
3. Inject keystrokes via `invoke('pty_write')` mid-flood → assert echo < 200ms.
4. Automated as a Playwright + perf-measurement page (`scripts/test-flood-perf.ts`).

**Implementation requirement:** per-rAF coalescing **and** watermark backpressure (HIGH=100KB / LOW=10KB) both required. One alone fails under `cat /dev/urandom`.

---

## Wave 0 Requirements

- [ ] `crates/voss-app-core/src/pty/tests.rs` — PTY-01 spawn-env, PTY-02 round-trip, PTY-06 pgid resolution
- [ ] `apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx` — PTY-04 paste banner + bypass
- [ ] `apps/voss-app/vitest.config.ts` — if not delivered by A1
- [ ] `pnpm add -D vitest @testing-library/dom @playwright/test` — if absent
- [ ] `apps/voss-app/scripts/test-flood-perf.ts` — D-02 perf benchmark harness
- [ ] Playwright Tauri E2E harness bootstrap (if not delivered by A1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `vim` alt-screen | PTY-08 | Visual alt-screen + cursor fidelity not reliably assertable headless | `vim test.txt` → confirm alt-screen, edit, `:q` clean exit |
| `htop` TUI | PTY-08 | Color/TUI rendering judgement | `htop` → confirm colors + layout, `q` exits |
| `tmux` / `less` | PTY-08 | Nested alt-screen / pager behavior | open each, confirm correct render + clean exit |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] D-02 flood perf assertion automated (not manual)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
