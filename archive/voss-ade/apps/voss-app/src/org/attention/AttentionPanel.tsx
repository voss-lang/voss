import { For, Show } from 'solid-js';

import './attentionPanel.css';
import {
  attentionQueue,
  type AttentionItem,
  type PermissionAction,
} from './attentionQueue';
import { setSelectedCardId } from '../selection';

/** Blocking kinds drive the pill pulse; here they only tint the row badge */
const BLOCKING_KINDS = new Set<AttentionItem['kind']>(['permission', 'signoff']);

/**
 * chunk C row polish (mockup.ai colored kind-dot): red for the hard
 * blockers (permission / blocked), focus-orange for sign-off, amber for the
 */
function kindDotColor(kind: AttentionItem['kind']): string {
  switch (kind) {
    case 'permission':
    case 'blocked':
      return 'var(--accent-red)';
    case 'signoff':
      return 'var(--focus)';
    case 'idle':
      return 'var(--fg-3)';
    default:
      return 'var(--accent-amber)';
  }
}

export type AttentionPanelProps = {
  open: boolean;
  onClose: () => void;
/**
 * Permission resolution backend is out of scope for this plan — the buttons
 * must exist + be clickable. App passes a stub (or none) and we no-op
 */
  onPermissionAction?: (item: AttentionItem, action: PermissionAction) => void;
};

/**
 * Deep-link focus: set the global selection to the bound card/session. The
 * cockpit (Board spine / drawer / rail) all read selectedCardId, so this is the
 */
function focusItem(item: AttentionItem): void {
  setSelectedCardId(item.cardId ?? item.deepLink.sessionNodeId ?? null);
}

export default function AttentionPanel(props: AttentionPanelProps) {
  return (
    <Show when={props.open}>
      <div class="attn-panel" role="region" aria-label="Attention queue">
        <div class="attn-panel__header">
          <span>Attention · {attentionQueue().length}</span>
          <button
            type="button"
            class="attn-panel__close"
            title="Close attention panel"
            onClick={() => props.onClose()}
          >
            ✕
          </button>
        </div>

        <div class="attn-panel__body">
          <Show
            when={attentionQueue().length > 0}
            fallback={<div class="attn-panel__empty">Nothing needs attention.</div>}
          >
            <For each={attentionQueue()}>
              {(item) => {
                const blocking = BLOCKING_KINDS.has(item.kind);
                return (
                  <div class="attn-row">
                    <div class="attn-row__head">
                      <span
                        class="attn-row__dot"
                        style={{ background: kindDotColor(item.kind) }}
                        aria-hidden="true"
                      />
                      <span
                        class={`attn-row__badge${blocking ? ' attn-row__badge--blocking' : ''}`}
                      >
                        {item.kind}
                      </span>
                      <span class="attn-row__summary" title={item.summary}>
                        {item.summary}
                      </span>
                      <button
                        type="button"
                        class="attn-btn attn-btn--focus"
                        title="Focus the bound card/session"
                        onClick={() => focusItem(item)}
                      >
                        Focus
                      </button>
                    </div>

                    <Show when={item.tool || item.affectedPath || item.dimension}>
                      <div class="attn-row__meta">
                        <Show when={item.tool}>{item.tool}</Show>
                        <Show when={item.dimension}>{` · ${item.dimension}`}</Show>
                        <Show when={item.affectedPath}>{` · ${item.affectedPath}`}</Show>
                      </div>
                    </Show>

                    <Show when={item.actions && item.actions.length > 0}>
                      <div class="attn-row__actions">
                        <For each={item.actions}>
                          {(action) => (
                            <button
                              type="button"
                              class={`attn-btn${action === 'deny' ? ' attn-btn--deny' : ''}`}
                              onClick={() => props.onPermissionAction?.(item, action)}
                            >
                              {action}
                            </button>
                          )}
                        </For>
                      </div>
                    </Show>
                  </div>
                );
              }}
            </For>
          </Show>
        </div>
      </div>
    </Show>
  );
}
