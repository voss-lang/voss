# V17 → V16 Handoff: Coordination Conventions for the Managed AGENTS.md Section

**From:** V17 (external agent coordination surface), 2026-06-10
**Action for V16:** fold a condensed version of `docs/agent-coordination.md`
into the managed AGENTS.md section template.

What to fold (condensed, not the full doc):

1. The five `voss claims` verbs + the three `voss bus` verbs, one line each.
2. The exit-code contract: 0 clear · 1 conflict · 2 identity/usage · 124 wait timeout.
3. `VOSS_AGENT_ID` (injected at pane spawn; required by all verbs).
4. The label vocabulary: `coord:blocker`, `coord:handoff`, `mission:<id>`, `review-request`.
5. The pre-edit guard one-liner:
   `voss claims check <files> || { echo "blocked"; exit 1; }`

Source of truth is `docs/agent-coordination.md` — keep the AGENTS.md section
condensed and link back to it rather than duplicating prose. Per the V17
boundary (SPEC: "Editing AGENTS.md templates directly — V16's design
territory"), V17 deliberately did NOT touch any AGENTS.md template; this
note is the only V16-directed artifact.

Note: the bus verbs are V15-gated (V17-05/06 execute after the V15 sidecar
ships). If V16 lands first, mark the bus rows "requires voss serve (V15)".

VBUS-08 coherence guard verified green at V17-07 (2026-06-10): swarm/ + sandbox.rs byte-unchanged, sandbox tests pass unmodified (147 cargo tests), no fs-watcher dep, no new coordination UI components.
