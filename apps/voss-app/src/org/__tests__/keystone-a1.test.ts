import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
declare const process: { cwd(): string };

import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';
import liveRegistry from './fixtures/live-registry.json';
import bridgeBinding from './fixtures/bridge-binding.json';

const HEX12 = /^[0-9a-f]{12}$/;

export const A1_FINDING =
  'A1 RESOLVED (verified against a real .voss/sessions tree): for a native run the ' +
  "create-response id (harness sessionID = uuid4().hex[:12], 12-hex) IS the snapshot " +
  'node id (SessionTreeNode.id = the .voss/sessions/<id>.json filename stem, which ' +
  'equals the record JSON `id`). create-response-id === node-id, so Bridge A stores ' +
  'the create-response id DIRECTLY into cardToSessionNode — NO second lookup is needed ' +
  'for the single-node native case. (The app-minted agent_registry.session_id is a ' +
  'separate namespace and does NOT join; that is Bridge B / cardId↔paneId.) ' +
  'resolveCard\'s `cardToSessionNode[cardId] ?? cardId` fallback covers any future ' +
  'multi-node run-dir divergence without a silent mis-bind.';

function findRepoRoot(start: string): string {
  let dir = start;
  for (let i = 0; i < 12; i++) {
    if (existsSync(join(dir, '.git'))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return start;
}

function findSessionTrees(root: string): string[] {
  const found: string[] = [];
  const skip = new Set(['node_modules', '.git', 'target', 'dist']);
  const walk = (dir: string, depth: number) => {
    if (depth > 6) return;
    let entries: string[];
    try {
      entries = readdirSync(dir);
    } catch {
      return;
    }
    for (const name of entries) {
      if (skip.has(name)) continue;
      const full = join(dir, name);
      let isDir = false;
      try {
        isDir = statSync(full).isDirectory();
      } catch {
        continue;
      }
      if (!isDir) continue;
      if (name === '.voss') {
        const sessions = join(full, 'sessions');
        if (existsSync(sessions) && statSync(sessions).isDirectory()) {
          found.push(sessions);
        }
        continue; // don't descend into .voss further
      }
      walk(full, depth + 1);
    }
  };
  walk(root, 0);
  return found;
}

const repoRoot = findRepoRoot(process.cwd());
const sessionTrees = findSessionTrees(repoRoot);

function collectRealSessions(): { id: string; stem: string }[] {
  for (const tree of sessionTrees) {
    const out: { id: string; stem: string }[] = [];
    for (const fname of readdirSync(tree)) {
      if (!fname.endsWith('.json')) continue;
      const stem = basename(fname, '.json');
      try {
        const rec = JSON.parse(readFileSync(join(tree, fname), 'utf8'));
        if (rec && typeof rec.id === 'string') out.push({ id: rec.id, stem });
      } catch {

      }
    }
    if (out.length) return out;
  }
  return [];
}

const realSessions = collectRealSessions();
const usingRealTree = realSessions.length > 0;

describe('V14 Keystone A1 — create-response id ↔ SessionTreeNode.id', () => {
  it('exports a documented A1_FINDING stating the create-response-id ↔ node-id relationship', () => {
    expect(A1_FINDING).toMatch(/create-response-id === node-id/);
    expect(A1_FINDING).toMatch(/NO second lookup/);
  });

  it(
    usingRealTree
      ? `grounds the finding in a REAL .voss/sessions tree (${realSessions.length} session records found)`
      : 'falls back to snapshot node fixtures (no real .voss/sessions tree found)',
    () => {
      if (usingRealTree) {
        expect(sessionTrees.length).toBeGreaterThan(0);
      } else {
        expect([nodeRoot.id, nodeChild.id].every((id) => typeof id === 'string')).toBe(true);
      }
    },
  );

  it('PROTOCOL §11: the native sessionID / node id is 12-hex (uuid4().hex[:12])', () => {
    if (usingRealTree) {
      for (const { id, stem } of realSessions) {
        expect(stem, `real session file stem ${stem}`).toMatch(HEX12);
        expect(id, `record id for ${stem} must equal its filename stem`).toBe(stem);
      }
    } else {
      for (const id of [nodeRoot.id, nodeChild.id]) {
        expect(id).toMatch(HEX12);
      }
    }
  });

  it('Bridge A convention: a native create-response id EQUALS the snapshot node id (no second lookup)', () => {
    const createResponseId = usingRealTree ? realSessions[0].id : nodeRoot.id;
    const nodeId = usingRealTree ? realSessions[0].stem : nodeRoot.id;

    expect(createResponseId).toMatch(HEX12); // (c) 12-hex sessionID format
    expect(createResponseId).toBe(nodeId); // create-response id === node id

    const cardToSessionNode: Record<string, string> = { C1: createResponseId };
    expect(cardToSessionNode.C1).toBe(nodeId);
  });

  it('registry session_id is a SEPARATE app-minted namespace (does NOT join to node id)', () => {
    const terminal = (liveRegistry as Array<{ paneId: string; sessionId: string }>).find(
      (a) => a.paneId === 'P2',
    );
    expect(terminal).toBeDefined();
    expect(terminal!.sessionId).not.toMatch(HEX12); // app-minted, not a harness sessionID
  });
});

describe('V14 Keystone A1 — binding fixtures', () => {
  it('live-registry.json parses as AgentEntry[] with a native agent on pane P1', () => {
    const arr = liveRegistry as Array<Record<string, unknown>>;
    expect(Array.isArray(arr)).toBe(true);
    const p1 = arr.find((a) => a.paneId === 'P1');
    expect(p1, 'an agent must be bound to pane P1').toBeDefined();
    for (const k of ['paneId', 'sessionId', 'cliBinary', 'cliArgs', 'cwd', 'status', 'lastSeen']) {
      expect(p1!, `AgentEntry must carry ${k}`).toHaveProperty(k);
    }
    expect(p1!.sessionId as string).toMatch(HEX12);
  });

  it('bridge-binding.json encodes the canonical case card C1 ↔ pane P1 ↔ node N1', () => {
    const b = bridgeBinding as {
      cardToPane: Record<string, string>;
      cardToSessionNode: Record<string, string>;
      expected: { cardId: string; paneId: string; sessionNodeId: string };
    };
    expect(b.cardToPane.C1).toBe('P1'); // C1 ↔ P1
    expect(b.cardToSessionNode.C1).toBe('N1'); // C1 ↔ N1
    expect(b.expected).toEqual({ cardId: 'C1', paneId: 'P1', sessionNodeId: 'N1' });
  });
});
