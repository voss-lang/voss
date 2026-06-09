// VCKP-05 — persistent Card detail drawer, recomposed in V14 chunk B to the
// cockpit mockup .drawer (curated sections instead of stacked full panels).
//
// Sections (top to bottom):
//   header   — mono card-id line, 14px/600 title, 2x2 kv grid (Risk / Column /
//              Budget / Confidence — Confidence renders only when the live SSE
//              overlay carries a score; snapshot runs omit the cell).
//   peek     — live agent frame, ONLY when a pane is bound via the id-bridge
//              (D-07); keeps the verbatim "coming soon" copy.
//   criteria — EM acceptance criteria, ONLY when the card's em.ticket carries
//              a criteria list (no persisted field exists in the V2-V7
//              substrate today, so this stays hidden until the harness ships
//              one — never faked).
//   reviewers— Reviewer-A / Reviewer-B verdict rows from the ReviewSidecar
//              (pend/pass/fail coloring).
//   diff     — compact container reusing DiffPanel's data source (the review
//              sidecar). Raw diff text NEVER persists in this substrate
//              (Pitfall 4) so the body is the truthful no-diff state plus the
//              a_verification evidence (rubric + notes).
//   routing  — EM routing rationale from the em.routing transition (hidden
//              when absent).
//   comment  — VCKP-09 follow-up affordance, UNCHANGED behavior (disabled-
//              with-reason on snapshot cards; feedbackWritePath.test.ts).
//   audit /  — the run-level Audit + Blocked panel bodies stay reachable in
//   blocked    compact collapsibles (Scope/Budget detail moved to the kv grid
//              + gate bar; Verdict detail lives in the reviewers section).
//   actions  — Reject ⓘ (disabled-with-reason: no CLI reject path) and the
//              primary Open in grid (publishes openInGridRequest, D-07).

import { Show, For, createSignal, type JSX } from 'solid-js';
import type { RunData, ReviewSidecar, EmRouting } from '../types';
import { runData } from '../orgStore';
import { selectedCardId, requestOpenInGrid } from '../selection';
import { paneIdForCard } from '../model/bridge';
import { liveOverlay } from '../live/sseClient';
import { deriveColumn, deriveRisk } from '../boardDerive';
import {
  dispatchFollowUp,
  nativeSessionNodeId,
  FOLLOWUP_DISABLED_REASON,
  type FollowUpClient,
} from '../feedbackWritePath';
import AuditPanel from '../panels/AuditPanel';
import BlockedPanel from '../panels/BlockedPanel';

// Same one-write-path disabled reason BlockedPanel shows for reject/unblock —
// decisionActions has no non-interactive reject surface (no invented behavior).
const NO_REJECT_REASON =
  'No non-interactive CLI command exists yet — use the harness sign-off';
const OPEN_DISABLED_REASON =
  'No live agent is bound to this card — it comes from a saved run.';

// Board column key -> display label + token color (cockpit-scoped: the
// --org-col-* aliases live outside the A12 allowed set, so map to base tokens).
const COLUMN_LABELS: Record<string, string> = {
  Backlog: 'Backlog',
  Planned: 'Planned',
  InProgress: 'In Progress',
  InReview: 'In Review',
  Done: 'Done',
  Blocked: 'Blocked',
};
const COLUMN_COLORS: Record<string, string> = {
  Backlog: 'var(--fg-3)',
  Planned: 'var(--fg-2)',
  InProgress: 'var(--accent-cyan)',
  InReview: 'var(--accent-amber)',
  Done: 'var(--accent-green)',
  Blocked: 'var(--accent-red)',
};

function riskColor(risk: string): string {
  return risk === 'high'
    ? 'var(--accent-red)'
    : risk === 'low'
      ? 'var(--accent-green)'
      : 'var(--accent-amber)';
}

function resTone(result: string | undefined): 'pass' | 'fail' | 'pend' {
  const v = (result ?? '').toUpperCase();
  if (v === 'PASS') return 'pass';
  if (v === 'FAIL' || v === 'BLOCK') return 'fail';
  return 'pend';
}

function DrawerCollapse(props: { title: string; children: JSX.Element }) {
  const [open, setOpen] = createSignal(false);
  return (
    <section class="cockpit-dcollapse">
      <button
        type="button"
        class="cockpit-dcollapse__head"
        aria-expanded={open()}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{open() ? '▾' : '▸'}</span> {props.title}
      </button>
      <Show when={open()}>
        <div class="cockpit-dcollapse__body">{props.children}</div>
      </Show>
    </section>
  );
}

/**
 * Persistent drawer. Reads the global `selectedCardId()` / `runData()`. A
 * `data` prop is accepted so CockpitShell may pass the snapshot explicitly, but
 * it defaults to the global `runData()` accessor to keep the shell wiring thin.
 */
export default function CardDrawer(props: {
  data?: RunData | null;
  /** V13.1 client for the VCKP-09 follow-up write path (absent = no live wiring). */
  followUpClient?: FollowUpClient;
}) {
  const data = (): RunData | null =>
    props.data !== undefined ? props.data : runData();

  // D-07: the bound live pane for the selected card (undefined for pure
  // snapshot cards). Drives the peek section + the Open-in-grid enabled state.
  const boundPaneId = (): string | undefined => {
    const id = selectedCardId();
    return id ? paneIdForCard(id) : undefined;
  };

  // UI-REVIEW 2a: the drawer leads with the card's TITLE (scope), never the
  // raw internal id. Falls back to the id only when the node isn't in the
  // snapshot (e.g. live-only cards).
  const selectedNode = () => {
    const id = selectedCardId();
    const d = data();
    if (!id || !d) return undefined;
    return d.session_tree.nodes.find((n) => n.id === id);
  };

  const sidecar = (): ReviewSidecar | null => {
    const id = selectedCardId();
    const d = data();
    return id && d ? (d.review[id] ?? null) : null;
  };

  // LIVE-only confidence: the SSE overlay keyed by the session correlation key
  // (card id IS the session node id for snapshot cards). Never from RunData.
  const confidence = (): number | undefined => {
    const id = selectedCardId();
    return id ? liveOverlay()[id]?.confidence : undefined;
  };

  // EM acceptance criteria: tolerant read of a `criteria: string[]` field on
  // the em.ticket transition. No such field persists in the V2-V7 substrate
  // yet, so this resolves [] (section hidden) — never fabricated.
  const criteria = (): string[] => {
    const n = selectedNode();
    if (!n) return [];
    for (const t of n.transitions) {
      if (t.kind === 'em.ticket') {
        const c = (t as { criteria?: unknown }).criteria;
        if (Array.isArray(c)) {
          return c.filter((x): x is string => typeof x === 'string');
        }
      }
    }
    return [];
  };

  const routing = (): EmRouting | null => {
    const n = selectedNode();
    if (!n) return null;
    for (const t of n.transitions) {
      if (t.kind === 'em.routing') return t;
    }
    return null;
  };

  // VCKP-09: a comment can dispatch only when a live client exists AND the
  // selected card is bound to a NATIVE session (snapshot cards have no write
  // path → disabled-with-reason, never a silent no-op).
  const [comment, setComment] = createSignal('');
  const canComment = (): boolean => {
    const id = selectedCardId();
    return !!props.followUpClient && !!id && !!nativeSessionNodeId(id);
  };
  const sendFollowUp = () => {
    const id = selectedCardId();
    const text = comment().trim();
    if (!id || !text) return;
    void dispatchFollowUp({
      cardId: id,
      comment: text,
      client: props.followUpClient,
      hasNativePath: !!props.followUpClient,
    }).then((res) => {
      if (!res.disabled) setComment('');
    });
  };

  const openInGrid = () => {
    const p = boundPaneId();
    if (p) requestOpenInGrid(p);
  };

  return (
    <Show
      when={selectedCardId()}
      fallback={
        <div class="org-panel">
          <div class="org-empty">Select a card to see its details.</div>
        </div>
      }
    >
      <div class="cockpit-drawer__body">
        {/* Header (mockup .dhdr): mono id line, title, kv grid. */}
        <header class="cockpit-dhdr">
          <div class="cockpit-dhdr__id">
            {selectedCardId()}
            <Show when={selectedNode()?.role}>
              {' · '}
              {selectedNode()!.role}
            </Show>
          </div>
          <div class="cockpit-drawer__title">
            {selectedNode()?.scope ?? selectedCardId()}
          </div>
          <Show when={selectedNode()}>
            {(node) => (
              <div class="cockpit-kvgrid">
                <div class="cockpit-kv">
                  <div class="cockpit-kv__k">Risk</div>
                  <div
                    class="cockpit-kv__v"
                    style={{ color: riskColor(deriveRisk(node())) }}
                  >
                    {deriveRisk(node())}
                  </div>
                </div>
                <div class="cockpit-kv">
                  <div class="cockpit-kv__k">Column</div>
                  <div
                    class="cockpit-kv__v"
                    style={{
                      color:
                        COLUMN_COLORS[deriveColumn(node())] ?? 'var(--fg-0)',
                    }}
                  >
                    {COLUMN_LABELS[deriveColumn(node())] ??
                      deriveColumn(node())}
                  </div>
                </div>
                <div class="cockpit-kv">
                  <div class="cockpit-kv__k">Budget</div>
                  <div class="cockpit-kv__v cockpit-kv__v--mono">
                    {node().envelope.spent} / {node().envelope.limit}
                  </div>
                </div>
                {/* Confidence: live SSE overlay only — omitted on snapshot. */}
                <Show when={confidence() !== undefined}>
                  <div class="cockpit-kv">
                    <div class="cockpit-kv__k">Confidence</div>
                    <div class="cockpit-kv__v cockpit-kv__v--mono">
                      {confidence()!.toFixed(2)}
                    </div>
                  </div>
                </Show>
              </div>
            )}
          </Show>
        </header>

        {/* D-07: read-only live-pane peek — rendered ONLY when a live pane is
            bound (UI-REVIEW 2c: no dead chrome on snapshot cards). */}
        <Show when={boundPaneId()}>
          <section class="cockpit-dsec" aria-label="Live execution">
            <div class="cockpit-dsec__title">Live execution</div>
            <div class="cockpit-peek">
              <div class="cockpit-peek__hdr">
                <span class="cockpit-peek__dot" /> live agent attached
              </div>
              <div class="cockpit-peek__body">
                Output preview coming soon — use Open in grid to see live
                output.
              </div>
            </div>
          </section>
        </Show>

        {/* EM acceptance criteria — only when the ticket carries them. */}
        <Show when={criteria().length > 0}>
          <section class="cockpit-dsec" aria-label="Acceptance criteria">
            <div class="cockpit-dsec__title">EM acceptance criteria</div>
            <For each={criteria()}>
              {(c) => (
                <div class="cockpit-ac">
                  <span class="cockpit-ac__mk">○</span>
                  {c}
                </div>
              )}
            </For>
          </section>
        </Show>

        {/* Reviewers — A/B verdict rows from the ReviewSidecar. */}
        <section class="cockpit-dsec" aria-label="Reviewers">
          <div class="cockpit-dsec__title">Reviewers</div>
          <div class="cockpit-verdict">
            <span class="cockpit-verdict__who">Reviewer-A</span>
            <Show
              when={sidecar()?.a_verification}
              fallback={
                <span class="cockpit-verdict__res cockpit-verdict__res--pend">
                  ⧗ pending
                </span>
              }
            >
              {(a) => (
                <>
                  <span
                    class={`cockpit-verdict__res cockpit-verdict__res--${resTone(a().result)}`}
                  >
                    {a().result.toUpperCase()}
                  </span>
                  <span class="cockpit-verdict__conf">
                    {a().test_path_or_rubric}
                  </span>
                </>
              )}
            </Show>
          </div>
          <div class="cockpit-verdict">
            <span class="cockpit-verdict__who">Reviewer-B</span>
            <Show
              when={sidecar()?.b_verdict}
              fallback={
                <span class="cockpit-verdict__res cockpit-verdict__res--pend">
                  ⧗ pending
                </span>
              }
            >
              {(b) => (
                <>
                  <span
                    class={`cockpit-verdict__res cockpit-verdict__res--${resTone(b().verdict)}`}
                  >
                    {b().verdict.toUpperCase()}
                  </span>
                  <span class="cockpit-verdict__conf">
                    conf {b().conf.toFixed(2)} · {b().domain_inferred}
                  </span>
                </>
              )}
            </Show>
          </div>
        </section>

        {/* Diff — compact container over DiffPanel's data source. Raw diff
            text never persists in this substrate (Pitfall 4): the truthful
            no-diff state + the a_verification evidence. */}
        <section class="cockpit-dsec" aria-label="Diff">
          <div class="cockpit-dsec__title">Diff</div>
          <div class="cockpit-diff">
            <div class="cockpit-diff__empty">
              No diff recorded for this card.
            </div>
          </div>
          <Show when={sidecar()?.a_verification}>
            {(a) => (
              <div class="cockpit-diff__verification">
                <span class="cockpit-diff__rubric">
                  {a().test_path_or_rubric}
                </span>
                <span class="cockpit-diff__notes">{a().notes}</span>
              </div>
            )}
          </Show>
        </section>

        {/* Routing rationale — from the em.routing transition when present. */}
        <Show when={routing()}>
          {(r) => (
            <section class="cockpit-dsec" aria-label="Routing rationale">
              <div class="cockpit-dsec__title">Routing rationale</div>
              <div class="cockpit-dsec__body">
                EM → {r().chosen_role}. {r().rationale_text}
              </div>
            </section>
          )}
        </Show>

        {/* VCKP-09: inline follow-up comment — active only on a native session. */}
        <section class="cockpit-comment" aria-label="Follow-up comment">
          <textarea
            class="cockpit-comment__box"
            placeholder="Add a follow-up for this task"
            value={comment()}
            onInput={(e) => setComment(e.currentTarget.value)}
            disabled={!canComment()}
          />
          <button
            type="button"
            class="cockpit-comment__send"
            disabled={!canComment()}
            title={
              canComment()
                ? 'Send this follow-up to the running session'
                : FOLLOWUP_DISABLED_REASON
            }
            onClick={sendFollowUp}
          >
            Send follow-up
          </button>
          <Show when={!canComment()}>
            <div class="cockpit-comment__reason">
              {FOLLOWUP_DISABLED_REASON}
            </div>
          </Show>
        </section>

        {/* Run-level Audit / Blocked panel bodies — compact collapsibles. */}
        <DrawerCollapse title="Audit">
          <AuditPanel data={data()} />
        </DrawerCollapse>
        <DrawerCollapse title="Blocked cards">
          <BlockedPanel data={data()} />
        </DrawerCollapse>

        {/* Bottom action row (mockup .dactions). */}
        <div class="cockpit-dactions">
          <button
            type="button"
            disabled
            aria-disabled="true"
            title={NO_REJECT_REASON}
          >
            Reject ⓘ
          </button>
          <button
            type="button"
            class="cockpit-dactions__primary"
            disabled={!boundPaneId()}
            title={
              boundPaneId() ? 'Open this card in the grid' : OPEN_DISABLED_REASON
            }
            onClick={openInGrid}
          >
            Open in grid
          </button>
        </div>
      </div>
    </Show>
  );
}
