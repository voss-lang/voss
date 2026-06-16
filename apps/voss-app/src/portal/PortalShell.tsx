// V24-02 (VADE2-02) — canvas-swap host (portal-surface layer ONLY).
//
// CRITICAL (Pitfall 1): PortalShell does NOT render GridRoot and does NOT wrap
// the grid in <Show>. The grid lives in App.tsx behind a `display:none` toggle.
// PortalShell renders only the portal surface, position:absolute over the hidden
// grid, mounted via <Show when={activeView !== 'grid'}> (D-01).
//
// Surface routing (this plan, W1):
//   'review'                          → reviewSlot() (existing OrgViewShell)
//   'overview'|'tasks'|'agents'|'swarm-map' → labeled placeholders (filled V24-05/06)
//   'context'|'memory'|'settings'     → labeled placeholders (wired to existing
//                                       panels in a later plan; no standalone shell
//                                       component exists to mount as-is yet)

import { type Component, type JSX, Show, Switch, Match } from 'solid-js';
import { PORTAL_ITEMS, type PortalView } from './portalTypes';
import OverviewSurface from '../surfaces/overview/OverviewSurface';
import TasksSurface from '../surfaces/tasks/TasksSurface';
import AgentsSurface from '../surfaces/agents/AgentsSurface';
import SwarmMap from '../surfaces/swarm-map/SwarmMap';
import './portal.css';

export interface PortalShellProps {
  activeView: PortalView;
  onNavTo: (view: PortalView) => void;
  /** Lazy slot for the existing Review surface (OrgViewShell). Thunk so the
   *  component only mounts when 'review' is active (not eagerly at prop build). */
  reviewSlot?: () => JSX.Element;
  /** Overview surface header — project identity + session/task actions. */
  projectName?: string;
  projectPath?: string | null;
  gitBranch?: string | null;
  onNewSession?: () => void;
  onNewTask?: () => void;
}

function labelFor(view: PortalView): string {
  return PORTAL_ITEMS.find((i) => i.id === view)?.label ?? view;
}

const SurfacePlaceholder: Component<{ view: PortalView }> = (props) => (
  <div
    class="portal-placeholder"
    data-surface={props.view}
    role="tabpanel"
    aria-label={labelFor(props.view)}
  >
    <span class="portal-placeholder__title">{labelFor(props.view)}</span>
    <span class="portal-placeholder__hint">Coming in a later V24 plan</span>
  </div>
);

const PortalShell: Component<PortalShellProps> = (props) => {
  return (
    <Show when={props.activeView !== 'grid'}>
      <div class="portal-surface">
        <Switch fallback={<SurfacePlaceholder view={props.activeView} />}>
          <Match when={props.activeView === 'review'}>
            {props.reviewSlot ? props.reviewSlot() : <SurfacePlaceholder view="review" />}
          </Match>
          <Match when={props.activeView === 'overview'}>
            <OverviewSurface />
          </Match>
          <Match when={props.activeView === 'tasks'}>
            <TasksSurface />
          </Match>
          <Match when={props.activeView === 'agents'}>
            <AgentsSurface />
          </Match>
          <Match when={props.activeView === 'swarm-map'}>
            <SwarmMap />
          </Match>
        </Switch>
      </div>
    </Show>
  );
};

export default PortalShell;
