# V24 — Terminal-First (L1) + Visual + Tauri Verification Checklist

> **Requirement:** VADE2-08. This is the named **L1 acceptance gate** before
> `/gsd-verify-work` — the user chose a documented manual checklist over automated
> regression for the experiential terminal-first guarantee. The automated suite
> (`npm test`, 871 passing incl. all 10 V24 modules) covers everything that can be
> asserted in jsdom; this file covers what only a human on a live Tauri build can
> confirm. **Tick every box and sign off at the bottom.**

**How to run:** `cd apps/voss-app && npm run tauri dev` (or the project's run
command). Work through all three sections in order.

---

## 1. Terminal-First (L1) Checklist

> **Gate:** every step below MUST pass **without Voss credentials** and **without a
> project** — proving the app stands on its own as a terminal workbench. If any
> single step requires Voss login or a configured project, the L1 constraint has
> failed and the phase does not pass.

Set-up: launch the app signed-out / with no Voss credentials configured, opened in
a directory that is **not** a Voss project (project-less).

- [ ] **Boots to the terminal grid.** Fresh / project-less workspace opens directly
      on the terminal canvas (not a Voss surface) — D-02 launch behavior.
- [ ] **Open a terminal.** A pane spawns a working shell with a live prompt.
- [ ] **Split right (⌘D).** New pane opens to the right; both panes are live.
- [ ] **Split below (⌘⇧D).** New pane opens below; locked tiling stays balanced.
- [ ] **Focus panes.** Click / keyboard-focus moves between panes; the focused pane
      receives keystrokes.
- [ ] **Run an arbitrary shell command.** e.g. `ls -la && echo hello` — output
      renders correctly in the focused pane.
- [ ] **Launch a custom CLI agent in a pane.** Start an arbitrary external CLI
      (e.g. `claude`, `codex`, or any shell program) in a pane — it runs as a normal
      child process, no Voss run required.
- [ ] **Project-less usage holds.** Everything above worked with no project open and
      no Voss credentials.
- [ ] **Session persists across reload.** Reload the window; open panes / shell
      sessions are restored (PTY identity survives).

**Section 1 result:** ☐ PASS ☐ FAIL — notes: ______________________________

---

## 2. Product Vocabulary / No-Raw-Labels Visual Review

> Screenshot-review the default chrome and each surface. Confirm **no raw internal
> labels** are visible and the **locked vocabulary** is present. This is the
> judgment check for VADE2-01 register ("a fluent dev understands Voss on first
> open without learning internal labels").

**Raw labels that MUST be absent from default chrome:**

- [ ] No layout-preset names as navigation — no `fanout`, `pipeline`, `swarm`,
      `watchers` presented as top-level nav (presets live only in the demoted
      layout menu / pane control).
- [ ] No raw `Plan` / `Edit` / `Auto` mode toggle in the top chrome.
- [ ] No raw `runId` / `RunData` / `currentRunId` shown anywhere user-facing.

**Locked vocabulary that MUST be present (byte-exact — PRODUCT.md §Locked Vocabulary):**

- [ ] Portal item reads **"Tasks"** (never "Runs").
- [ ] Observability surface reads **"Swarm Map"**.
- [ ] Composer safety modes read **"Read only" / "Can edit" / "Autopilot"** (not Plan/Edit/Auto).
- [ ] Composer title reads **"Ask Voss to…"** (Unicode ellipsis) and CTA reads **"Create Task"**.
- [ ] Board work-items read **steps / cards** — never "tasks" inside a Task.

**Two hard-fails — either one alone = product failure (PRODUCT.md §Success Criteria). Confirm BOTH absent:**

- [ ] **Hard-fail 1 — Raw internal labels in default chrome:** ABSENT (no `runId`,
      `RunData`, `Plan/Edit/Auto`, or preset name shown as product vocabulary).
- [ ] **Hard-fail 2 — Presets-as-navigation:** ABSENT (`fanout/pipeline/swarm/watchers`
      are a demoted layout control, not top-level navigation).

**Section 2 result:** ☐ PASS ☐ FAIL — notes: ______________________________

---

## 3. Swarm Map Tauri Smoke (live build)

> Verifies the interactions that cannot be exercised in jsdom (matrix pan vs native
> scroll, real reduced-motion media evaluation, replay over a live graph). Needs a
> real Tauri build with **≥1 run** present.

- [ ] **Open Swarm Map** with at least one run — radial clusters render (one per run).
- [ ] **Drag-pan** the canvas — the `<g transform>` follows the pointer; **no native-scroll conflict** (the window does not scroll / rubber-band).
- [ ] **Zoom** the canvas — scales smoothly with no scroll interception.
- [ ] **Toggle reduced motion** (OS setting or `html.reduced-motion`) — connector
      animations / traveling dots **cease**, and the **Event Trace** list is shown
      (the equivalent static fallback — motion conveys nothing the trace doesn't).
- [ ] **Scrub a completed run** — moving the replay scrubber drives the graph state
      to the corresponding step (the rendered board tracks the scrubber position).

**Section 3 result:** ☐ PASS ☐ FAIL — notes: ______________________________

---

## Operator Sign-Off

All three sections must pass. The L1 (Section 1) gate is non-negotiable: the app
must work as a terminal **without Voss** credentials or a project.

- **Build / commit reviewed:** ____________________
- **Date:** ____________________
- **Operator:** ____________________
- **Verdict:** ☐ APPROVED — V24 terminal-first + visual + Tauri smoke all pass
              ☐ CHANGES REQUIRED — see section notes above
