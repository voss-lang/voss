// V24-10 (VADE2-10) — Context surface.
//
// Closes the V24-SPEC §41/86/91 requirement that Context "wire to existing
// panels/drawers as-is". The full Context feature already ships as the F4 side
// drawer (components/ContextPanel.tsx); this surface gives it a full-canvas home in
// the portal, fed by the SAME focused-pane ContextData the drawer uses (passed via
// a contextSlot thunk from App, mirroring reviewSlot). No re-derivation, no new
// data path.
//
// Empty state: ContextPanel's own empty text is styled for the narrow F4 side
// drawer (position:absolute, 240px) and looks broken on a full canvas, so here
// we render the shared centered SurfaceEmpty card instead and only mount
// ContextPanel once there's an agent pane with real context to show.

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

const ContextSurface: Component<ContextSurfaceProps> = (props) => (
  <div class="surface" role="tabpanel" aria-label="Context">
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
