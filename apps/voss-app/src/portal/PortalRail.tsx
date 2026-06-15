// V24-02 (VADE2-02) — left portal nav rail. 48px icon rail, role=tablist with
// the 8 PORTAL_ITEMS plus an "Ask Voss to…" composer trigger at the bottom.
//
// V24-03 (VADE2-03) — layout presets demoted out of the top chrome land here as
// a bottom-area "Layout" affordance that opens a menu mounting the UNCHANGED
// PresetSwitcher (fanout/pipeline/swarm/watchers). The preset state still flows
// from App (single source of truth shared with ⌘G cycling); the rail only moves
// the mount point.
//
// Pitfall 5: PortalRail does NOT own the activeView signal — it lives in App.tsx
// so the openInGridRequest deep-link effect can flip back to 'grid'. The rail
// receives activeView + onNavTo as props (controlled component). The same rule
// applies to the layout preset state (activeLayout + onLayoutSelect).

import { type Component, createSignal, For, Show } from 'solid-js';
import { PORTAL_ITEMS, type PortalView } from './portalTypes';
import PresetSwitcher from '../components/titlebar/PresetSwitcher';
import type { ActiveLayout, LayoutPreset } from '../grid/layoutPresets';
import './portal.css';

export interface PortalRailProps {
  activeView: PortalView;
  onNavTo: (view: PortalView) => void;
  onOpenComposer?: () => void;
  /** Active layout preset (App-owned, shared with ⌘G). Drives the layout menu. */
  activeLayout?: ActiveLayout;
  layoutDisabled?: boolean;
  onLayoutSelect?: (preset: LayoutPreset) => void;
}

const PortalRail: Component<PortalRailProps> = (props) => {
  const [layoutMenuOpen, setLayoutMenuOpen] = createSignal(false);

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
      {/* Layout presets (V24-03) — demoted from the top chrome. Distinct from the
          8 nav tabs and the ask trigger. Opens a menu that mounts the unchanged
          PresetSwitcher to the right of the rail. */}
      <Show when={props.onLayoutSelect}>
        <div class="portal-layout-wrap">
          <button
            type="button"
            class={`portal-layout${layoutMenuOpen() ? ' portal-layout--open' : ''}`}
            aria-label="Layout presets"
            title="Layout presets"
            aria-haspopup="menu"
            aria-expanded={layoutMenuOpen() ? 'true' : 'false'}
            onClick={() => setLayoutMenuOpen((open) => !open)}
          >
            <span aria-hidden="true">▦</span>
          </button>
          <Show when={layoutMenuOpen()}>
            <div class="portal-layout-menu" role="menu" aria-label="Layout presets">
              <PresetSwitcher
                activeLayout={props.activeLayout ?? 'custom'}
                disabled={props.layoutDisabled}
                onSelect={(preset) => {
                  props.onLayoutSelect?.(preset);
                  setLayoutMenuOpen(false);
                }}
              />
            </div>
          </Show>
        </div>
      </Show>
    </nav>
  );
};

export default PortalRail;
