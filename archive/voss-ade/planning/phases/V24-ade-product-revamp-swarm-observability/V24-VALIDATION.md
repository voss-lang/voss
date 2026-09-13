---
phase: V24
slug: ade-product-revamp-swarm-observability
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-14
---

# Phase V24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from V24-RESEARCH.md "Validation Architecture" (signals verified against existing apps/voss-app tests).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.6 + jsdom 29.1.1 (unit); Playwright (e2e) |
| **Config file** | `apps/voss-app/vitest.config.ts` |
| **Quick run command** | `cd apps/voss-app && npm test -- <module>` |
| **Full suite command** | `cd apps/voss-app && npm test` |
| **E2E command** | `cd apps/voss-app && npm run test:e2e` |
| **Estimated runtime** | full vitest suite ~tens of seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command on the module under change only (e.g. `npm test -- swarmMapDerive`)
- **After every plan wave:** Run full `npm test` suite
- **Before `/gsd-verify-work`:** Full suite green AND manual terminal-first checklist documented
- **Max feedback latency:** < 60s for quick module runs

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File (✅ exists / ❌ W0 gap) | Status |
|--------|----------|-----------|-------------------|------------------------------|--------|
| VADE2-01 | PRODUCT/UI-SPEC committed with locked vocabulary | Manual + grep | check file exists + grep vocab tokens (Task/Swarm Map/Read only·Can edit·Autopilot/steps·cards) | UI-SPEC ✅ / PRODUCT manual | ⬜ pending |
| VADE2-02 | Grid host element identity survives portal round-trip; only `display` flips | unit | `npm test -- swarmPortal` | `src/__tests__/swarmPortal.test.tsx` ❌ W0 | ⬜ pending |
| VADE2-02 | Pane/PTY session identity survives round-trip | unit | `npm test -- swarmPortal` | same ❌ W0 | ⬜ pending |
| VADE2-03 | Top chrome has no preset / Plan·Edit·Auto controls; presets in layout menu | CSS/DOM source assertion | `npm test -- TopChrome` | `src/components/titlebar/__tests__/TopChrome.test.tsx` ❌ W0 | ⬜ pending |
| VADE2-04 | Composer shows only ask + safety on open; Advanced collapsed | unit (jsdom) | `npm test -- VossComposer` | `src/composer/__tests__/VossComposer.test.tsx` ❌ W0 | ⬜ pending |
| VADE2-04 | Safety mode defaults to "Read only" | unit | `npm test -- VossComposer` | same ❌ W0 | ⬜ pending |
| VADE2-05 | Fixture runs appear under correct status groups | unit | `npm test -- TasksSurface` | `src/surfaces/tasks/__tests__/TasksSurface.test.tsx` ❌ W0 | ⬜ pending |
| VADE2-05 | Deep link from row opens correct pane/drawer | unit | `npm test -- portalDeepLink` | `src/__tests__/portalDeepLink.test.tsx` ❌ W0 | ⬜ pending |
| VADE2-06 | **No-fake-signal guard:** empty RunData → 0 edges, objective placeholder only | unit (guard) | `npm test -- swarmMapDerive` | `src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts` ❌ W0 | ⬜ pending |
| VADE2-06 | Partial RunData: every edge has `edge.source !== undefined` | unit (guard) | `npm test -- swarmMapDerive` | same ❌ W0 | ⬜ pending |
| VADE2-06 | Full fixture: all 5 node types render in radial clusters | unit (jsdom) | `npm test -- SwarmMap` | `src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx` ❌ W0 | ⬜ pending |
| VADE2-07 | Live SSE event adds edge to graph | unit (mock stream) | `npm test -- swarmLive` | `src/surfaces/swarm-map/__tests__/swarmLive.test.ts` ❌ W0 | ⬜ pending |
| VADE2-07 | Reduced-motion: swarmMap.css has no animation outside the guard | CSS source assertion | `npm test -- swarmA11y` | `src/surfaces/swarm-map/__tests__/swarmA11y.test.ts` ❌ W0 | ⬜ pending |
| VADE2-07 | Replay scrubber drives graph to correct step state | unit | `npm test -- ReplayScrubber` | `src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx` ❌ W0 | ⬜ pending |
| VADE2-08 | Manual terminal-first checklist passes + documented | manual | n/a — checklist in V24-08 plan | manual | ⬜ pending |
| VADE2-08 | Existing grid/pane/terminal unit tests stay green | regression | `npm test` | existing `src/grid/__tests__/`, `src/pane/__tests__/` ✅ | ⬜ pending |
| VADE2-08 | Swarm Map pan on real Tauri window (not jsdom) | manual smoke | n/a — live Tauri build | manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (test files to create before implementation)

- [ ] `src/__tests__/swarmPortal.test.tsx` — canvas-swap + pane identity round-trip (VADE2-02) — extend `liveReviewToggle.test.tsx` pattern
- [ ] `src/components/titlebar/__tests__/TopChrome.test.tsx` — no preset/Plan·Edit·Auto in default chrome (VADE2-03)
- [ ] `src/composer/__tests__/VossComposer.test.tsx` — composer default state + Advanced collapse + Read-only default (VADE2-04)
- [ ] `src/surfaces/tasks/__tests__/TasksSurface.test.tsx` — fixture run status grouping (VADE2-05)
- [ ] `src/__tests__/portalDeepLink.test.tsx` — row → pane/drawer deep link (VADE2-05)
- [ ] `src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts` — **no-fake-signal guard (VADE2-06, critical)** — mirror `swarmReconcile.test.ts`
- [ ] `src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx` — radial render smoke (VADE2-06)
- [ ] `src/surfaces/swarm-map/__tests__/swarmLive.test.ts` — live SSE → edge update (VADE2-07)
- [ ] `src/surfaces/swarm-map/__tests__/swarmA11y.test.ts` — CSS reduced-motion guard assertion (VADE2-07) — mirror `a11y.test.tsx`
- [ ] `src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx` — scrubber drives graph (VADE2-07)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Terminal-first preservation | VADE2-08 | L1 credibility is experiential; user chose manual checklist over automated regression as the named L1 gate | Open app with no project / no Voss creds → open terminal, split (⌘D / ⌘⇧D), focus, run arbitrary command, launch a custom CLI agent, confirm session persists across reload. All must work. |
| Swarm Map pan/zoom in Tauri webview | VADE2-07 | `<g transform>` matrix pan vs Tauri native scroll interception not verifiable in jsdom | On a real Tauri build, open Swarm Map with ≥1 run, drag-pan and zoom; confirm no native-scroll conflict. |
| Product vocabulary readability | VADE2-01 | "fluent dev understands without internal labels" is a judgment check | Screenshot-review default chrome + surfaces; confirm no raw fanout/pipeline/snapshot/Plan-Edit-Auto labels visible. |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (10 test files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
