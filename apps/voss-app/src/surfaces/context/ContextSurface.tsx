// V24-10 (VADE2-10) — Context surface.
//
// Closes the V24-SPEC §41/86/91 requirement that Context "wire to existing
// panels/drawers as-is". The full Context feature already ships as the F4 side
// drawer (components/ContextPanel.tsx); this surface gives it a full-canvas home in
// the portal, fed by the SAME focused-pane ContextData the drawer uses (passed via
// a contextSlot thunk from App, mirroring reviewSlot). No re-derivation, no new
// data path. ContextPanel owns its own empty state ("No agent context — focus an
// agent pane"), so the wrapper stays thin.

import { type Component } from 'solid-js';
import '../surfaces.css';
import ContextPanel from '../../components/ContextPanel';
import type { ContextData } from '../../pane/pty-ipc';

export interface ContextSurfaceProps {
  context: ContextData | null;
  isAgentPane: boolean;
  paneCwd?: string;
  onTogglePin?: (path: string, pinned: boolean) => void;
}

const ContextSurface: Component<ContextSurfaceProps> = (props) => (
  <div class="surface" role="tabpanel" aria-label="Context">
    <ContextPanel
      open={true}
      context={props.context}
      isAgentPane={props.isAgentPane}
      paneCwd={props.paneCwd}
      onTogglePin={props.onTogglePin}
    />
  </div>
);

export default ContextSurface;
