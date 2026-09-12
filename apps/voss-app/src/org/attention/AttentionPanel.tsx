import { For, Show } from 'solid-js';

import './attentionPanel.css';
import {
  attentionQueue,
  type AttentionItem,
  type PermissionAction,
} from './attentionQueue';
import { setSelectedCardId } from '../selection';

const BLOCKING_KINDS = new Set<AttentionItem['kind']>(['permission', 'signoff']);

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

  onPermissionAction?: (item: AttentionItem, action: PermissionAction) => void;
};

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
