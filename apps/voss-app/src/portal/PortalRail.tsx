// V24-02 (VADE2-02) — left portal nav rail. 48px icon rail, role=tablist with
// the 8 PORTAL_ITEMS plus an "Ask Voss to…" composer trigger at the bottom.
//
// Pitfall 5: PortalRail does NOT own the activeView signal — it lives in App.tsx
// so the openInGridRequest deep-link effect can flip back to 'grid'. The rail
// receives activeView + onNavTo as props (controlled component).

import { type Component, For } from 'solid-js';
import { PORTAL_ITEMS, type PortalView } from './portalTypes';
import './portal.css';

export interface PortalRailProps {
  activeView: PortalView;
  onNavTo: (view: PortalView) => void;
  onOpenComposer?: () => void;
}

const PortalRail: Component<PortalRailProps> = (props) => {
  return (
    <nav class="portal-rail" aria-label="Voss portal">
      <div class="portal-tablist" role="tablist" aria-orientation="vertical">
        <For each={PORTAL_ITEMS}>
          {(item) => (
            <button
              type="button"
              role="tab"
              aria-selected={props.activeView === item.id ? 'true' : 'false'}
              aria-label={item.label}
              title={item.label}
              class={`portal-item${props.activeView === item.id ? ' portal-item--active' : ''}`}
              onClick={() => props.onNavTo(item.id)}
            >
              <span aria-hidden="true">{item.glyph}</span>
            </button>
          )}
        </For>
      </div>
      {/* "Ask Voss to…" composer trigger (D-03). The composer itself lands in
          V24-04; onOpenComposer is wired then. */}
      <button
        type="button"
        class="portal-ask"
        aria-label="Ask Voss to…"
        title="Ask Voss to…"
        onClick={() => props.onOpenComposer?.()}
      >
        <span aria-hidden="true">❯</span>
      </button>
    </nav>
  );
};

export default PortalRail;
