import { connectLiveStream } from './sseClient';
import { createSwarm, runSwarm, type RoleSpecBody } from './swarmClient';
import { setActiveSwarmId } from './swarmLive';
import type { LiveServer } from './liveServer';

const isCoordinator = (role: string) => /^coord/i.test(role);

export interface LaunchSwarmOpts {
  goal: string;
  builders: number;

  roster?: RoleSpecBody[];
}

export async function launchSwarm(
  srv: LiveServer,
  opts: LaunchSwarmOpts,
): Promise<string> {
  const { id, sessions } = await createSwarm(srv.sidecarId, {
    goal: opts.goal,
    builders: opts.builders,
    cwd: srv.cwd,
    roster: opts.roster,
  });
  setActiveSwarmId(id);

  const native = sessions.filter((s) => !!s.session_id);
  for (const s of native) {
    connectLiveStream({
      sidecarId: srv.sidecarId,
      sessionId: s.session_id!,
    });
  }

  const coord = native.find((s) => isCoordinator(s.role));
  if (coord?.session_id && srv.followUpClient) {
    await srv.followUpClient.postMessage(coord.session_id, opts.goal);
  }

  const hasCli = sessions.some((s) => s.pending || !s.session_id);
  if (hasCli) {
    await runSwarm(srv.sidecarId, id);
  }
  return id;
}
