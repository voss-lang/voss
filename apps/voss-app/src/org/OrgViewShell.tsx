import { type Component } from 'solid-js';
import './orgStyles.css';
import CockpitShell from './cockpit/CockpitShell';
import type { FollowUpClient } from './feedbackWritePath';
import type { VossClient } from '../../../../sdk/typescript/src/client/rest';

const OrgViewShell: Component<{
  cwd: string;
  cliBinary: string;
  onClose: () => void;

  followUpClient?: FollowUpClient;

  vossClient?: SidecarVossClient;
  onAttach?: (sessionId: string) => void;
}> = (props) => {
  return (
    <CockpitShell
      cwd={props.cwd}
      cliBinary={props.cliBinary}
      onClose={props.onClose}
      followUpClient={props.followUpClient}
      vossClient={props.vossClient}
      onAttach={props.onAttach}
    />
  );
};

export default OrgViewShell;
