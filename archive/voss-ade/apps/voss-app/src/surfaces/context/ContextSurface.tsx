import { type Component, Show } from 'solid-js';
import '../surfaces.css';
import ContextPanel from '../../components/ContextPanel';
import SurfaceEmpty from '../SurfaceEmpty';
import type { ContextData } from '../../pane/pty-ipc';

export interface ContextSurfaceProps {
  context: ContextData | null;
  isAgentPane: boolean;
  paneCwd?: string;
  onTogglePin?: (path: string, pinned: boolean) => void;
}

const ContextIcon = () => (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <path d="M12 3 3 8l9 5 9-5-9-5Z" />
    <path d="m3 13 9 5 9-5" />
  </svg>
);

function cwdBasename(cwd?: string): string {
  if (!cwd) return '';
  const parts = cwd.replace(/\/+$/, '').split('/');
  return parts[parts.length - 1] || cwd;
}

const ContextSurface: Component<ContextSurfaceProps> = (props) => (
  <div class="surface" role="tabpanel" aria-label="Context">
    <div class="surface__header">
      <span class="surface__title">Context</span>
      <Show when={props.isAgentPane && props.context && props.paneCwd}>
        <span class="surface__count">{cwdBasename(props.paneCwd)}</span>
      </Show>
    </div>
    <Show
      when={props.isAgentPane && props.context}
      fallback={
        <SurfaceEmpty
          icon={<ContextIcon />}
          title="No context to show"
          hint={
            <>
              Focus an agent pane to inspect its working set — the files,
              conversation, and tokens currently loaded into the model.
            </>
          }
        />
      }
    >
      <ContextPanel
        open={true}
        context={props.context}
        isAgentPane={props.isAgentPane}
        paneCwd={props.paneCwd}
        onTogglePin={props.onTogglePin}
      />
    </Show>
  </div>
);

export default ContextSurface;
