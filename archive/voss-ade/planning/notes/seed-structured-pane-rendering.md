# Seed: Voss-native structured pane rendering (Live Work transcript view)

**Captured:** 2026-06-09 (V14-12 close-out; operator-requested)
**Source:** `.planning/sketches/V14-livework-mockup.html` — the approved Live Work mockup's *inside-the-terminal* content, the one V14 element explicitly not built.

## The gap

V14 shipped the chrome AROUND panes (role edge, role pill, live cost, card chip, streaming dot) but a Voss-native agent pane still renders raw PTY output. The mockup shows what the pane body should become for Voss-native runs:

- EM task header (`EM task: <title> (C3)` + scope · budget · risk · reviewer-bar line)
- Structured tool lines (`fs_read src/auth/webauthn.ts (142 lines)`, `code_search "verifyRegistration" → 3 refs`, `fs_edit … +34 −2` with inline code excerpt)
- Plan text rendered as prose between tool events
- **Inline permission gate** inside the pane (`⚠ permission · mutating · prod-adjacent` + Deny / Allow once / Allow for scope buttons) — routed to the same `permission.updated` → `POST /permission` loop the AttentionQueue uses
- Reviewer transcript (`build_acceptance_bar → 4 criteria`, `voss_eval rubric=… conf 0.83 · A: PASS`)
- Statusbar `● live · voss serve :7421` once a real server session backs the pane

## Why deferred from V14

V14 is a PROTOCOL v1 *client* over snapshot + PTY (SPEC boundary: no new harness contracts; real `voss serve` E2E rides V13.1). Structured pane content requires the live SSE plane: render the §6 event union (`plan`/`tool`/`stream.delta`/`permission.updated`/`final`…) as pane DOM instead of (or alongside) xterm output.

## Shape when picked up

- New pane mode for Voss-native sessions: protocol-backed view (SSE consumer per session via sdk/typescript `subscribeToEvents`) replacing the PTY xterm body; external CLI panes stay PTY.
- Event→DOM renderer keyed by the §6 union; permission events render the inline gate AND feed the global AttentionQueue (D-06 stays the aggregator).
- The `{port,token}` handshake source in-webview is the open question (V14 Pitfall 4 — webview can't spawn `voss serve`); needs a Tauri-side spawn/attach command handing the handshake to the frontend.
- Mockup = visual contract; distill to UI-SPEC at phase start (lesson from V14: don't build from prose alone).

Candidate phase: V15 or post-V13.1-integration wave.
