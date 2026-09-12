import { describe, it, expect, afterAll } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { spawnHermeticServe, type HermeticServe } from './acSpawn';
import { buildVossClientFromHandshake } from '../vossClientBuild';
import type { BuiltVossClient } from '../vossClientBuild';
import { connectLiveStream, liveLabel, __resetLiveStream } from '../sseClient';
import { __resetAttentionQueue } from '../../attention/attentionQueue';
import { __resetBridgeMaps } from '../../model/bridge';
import { replyPermission } from '../../../../../../sdk/typescript/src/client/permission';
import type { AgentEvent } from '../../../../../../sdk/typescript/src/client/sse';

const STEP_TIMEOUT = 30_000; // every network wait bounded — CI fails fast
const SPAWN_TIMEOUT = 90_000; // cold .pyc compile can take ~45-60s

let serve: HermeticServe | undefined;
let built: BuiltVossClient | undefined;
let sessionId = '';
let workdir = '';

describe.skipIf(process.env.VOSS_AC_LIVE !== '1')(
  'VLIVE-08 live spine (hermetic)',
  () => {
    afterAll(async () => {
      await serve?.kill();
      __resetLiveStream();
      __resetAttentionQueue();
      __resetBridgeMaps();
      if (workdir) rmSync(workdir, { recursive: true, force: true });
    });

    it(
      'spawns a real voss serve and completes the {port, token} handshake (VLIVE-01)',
      async () => {
        workdir = mkdtempSync(join(tmpdir(), 'voss-ac-spine-'));
        serve = await spawnHermeticServe(workdir);

        expect(serve.port).toBeGreaterThan(0);
        expect(serve.token.length).toBeGreaterThan(0);
      },
      SPAWN_TIMEOUT,
    );

    it(
      'builds the client and creates a real server session (VLIVE-02)',
      async () => {
        built = buildVossClientFromHandshake({
          port: serve!.port,
          token: serve!.token,
        });

        sessionId = await built.client.createSession(workdir);
        expect(typeof sessionId).toBe('string');
        expect(sessionId.length).toBeGreaterThan(0);

        const sessions = await client.listSessions();
        expect(sessions.map((s) => s.id)).toContain(sessionId);
      },
      STEP_TIMEOUT,
    );

    it(
      'streams real §6 events for a posted turn; liveLabel flips live→snapshot (VLIVE-03)',
      async () => {
        const events: AgentEvent[] = [];
        let sawIdle: (() => void) | undefined;
        const idle = new Promise<void>((resolve) => {
          sawIdle = resolve;
        });

        const handle = connectLiveStream({
          baseUrl: built!.baseUrl,
          sessionId,
          token: built!.token,
          cardId: sessionId,
          onEvent: (ev) => {
            events.push(ev);
            if (ev.type === 'session.idle') sawIdle?.();
          },
        });

        expect(liveLabel()).toBe('live');

        const accepted = await built!.client.postMessage(
          sessionId,
          'do something small',
        );
        expect(accepted).toBeTruthy(); // 202 body

        await Promise.race([
          idle,
          new Promise((_, reject) =>
            setTimeout(
              () => reject(new Error(`no session.idle within ${STEP_TIMEOUT}ms`)),
              STEP_TIMEOUT,
            ),
          ),
        ]);

        const types = events.map((e) => e.type);
        expect(types.length).toBeGreaterThan(0);
        expect(types).toContain('user');
        expect(types).toContain('final');
        expect(types).toContain('session.idle');

        handle.abort();
        expect(liveLabel()).toBe('snapshot');
      },
      STEP_TIMEOUT * 2,
    );

    it(
      'permission transport: a reply POST for an absent id is answered (stale-tolerant 200)',
      async () => {

        await expect(
          replyPermission(built!.client, sessionId, {
            id: 'ac-absent-id',
            choice: 'a',
          }),
        ).resolves.toBeUndefined();
      },
      STEP_TIMEOUT,
    );

    it(
      'a follow-up postMessage on the same session is accepted (VLIVE-02 follow-up)',
      async () => {
        const accepted = await built!.client.postMessage(
          sessionId,
          'follow up',
        );
        expect(accepted).toBeTruthy();
      },
      STEP_TIMEOUT,
    );
  },
);
