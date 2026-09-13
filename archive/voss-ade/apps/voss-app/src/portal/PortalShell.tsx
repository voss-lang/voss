import { type Component, type JSX, Show, Switch, Match } from 'solid-js';
import { type PortalView } from './portalTypes';
import OverviewSurface from '../surfaces/overview/OverviewSurface';
import TasksSurface from '../surfaces/tasks/TasksSurface';
import AgentsSurface from '../surfaces/agents/AgentsSurface';
import SwarmMap from '../surfaces/swarm-map/SwarmMap';
import SettingsSurface from '../surfaces/settings/SettingsSurface';
import MemorySurface from '../surfaces/memory/MemorySurface';
import './portal.css';

export interface PortalShellProps {
  activeView: PortalView;
  onNavTo: (view: PortalView) => void;
/**
 * Lazy slot for the existing Review surface (OrgViewShell). Thunk so the
 * component only mounts when 'review' is active (not eagerly at prop build)
 */
  reviewSlot?: () => JSX.Element;
/**
 * Lazy slot for the Context surface (ContextSurface). Thunk so it only mounts
 * when 'context' is active; App owns the focused-pane ContextData it needs
 */
  contextSlot?: () => JSX.Element;
/**
 * Lazy slot for the Memory surface. Thunk so App can pass the live server
 * the opaque sidecar handle off vossClient; falls back to MemorySurface
 */
  memorySlot?: () => JSX.Element;
/** Overview surface header project identity + session/task actions */
  projectName?: string;
  projectPath?: string | null;
  gitBranch?: string | null;
  onNewSession?: () => void;
  onNewTask?: () => void;
}

const PortalShell: Component<PortalShellProps> = (props) => {
  return (
    <Show when={props.activeView !== 'grid'}>
      <div class="portal-surface">
        <Switch>
          <Match when={props.activeView === 'review'}>
            {props.reviewSlot?.()}
          </Match>
          <Match when={props.activeView === 'context'}>
            {props.contextSlot?.()}
          </Match>
          <Match when={props.activeView === 'overview'}>
            <OverviewSurface
              projectName={props.projectName ?? ''}
              projectPath={props.projectPath}
              gitBranch={props.gitBranch}
              onNewSession={props.onNewSession}
              onNewTask={props.onNewTask}
            />
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
          <Match when={props.activeView === 'settings'}>
            <SettingsSurface />
          </Match>
          <Match when={props.activeView === 'memory'}>
            {props.memorySlot ? props.memorySlot() : <MemorySurface />}
          </Match>
        </Switch>
      </div>
    </Show>
  );
};

export default PortalShell;
