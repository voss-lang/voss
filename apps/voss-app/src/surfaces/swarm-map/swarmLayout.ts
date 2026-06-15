// V24-06 (VADE2-06) — pure radial layout for the Swarm Map.
//
// Fixed polar coordinates, no force simulation, no external library
// (RESEARCH §Radial Layout Algorithm). Per cluster (one per run): objective at
// the cluster centroid, agents on a 120px ring, work/artifact on 220px, alerts
// on 300px. Multiple clusters pack across the canvas via a golden-angle
// Phyllotaxis spiral. Deterministic — fixture-testable.

import type { SwarmNode } from './swarmMapDerive';

export interface PositionedSwarmNode extends SwarmNode {
  x: number;
  y: number;
}

// Ring radii (px) per UI-SPEC §Component Inventory 5.
const RING_AGENT = 120;
const RING_WORK = 220;
const RING_ALERT = 300;

// Golden angle for the Phyllotaxis cluster spiral.
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
// Cluster centre spacing: 2×max-radius (300) + 80px min gap, rounded up so two
// clusters' outer rings never overlap.
const CLUSTER_GAP = 760;

function ringFor(type: SwarmNode['type']): number {
  if (type === 'agent') return RING_AGENT;
  if (type === 'work' || type === 'artifact') return RING_WORK;
  if (type === 'alert') return RING_ALERT;
  return RING_AGENT; // placeholder (non-centre) orbits with the agents
}

/**
 * Assign (x, y) to every node. Center of cluster 0 is the origin; later
 * clusters spiral outward by the golden angle. Within a cluster, each ring's
 * nodes are evenly distributed by angle.
 */
export function layoutSwarm(nodes: SwarmNode[]): PositionedSwarmNode[] {
  // Group by runId, preserving first-seen order (deterministic).
  const order: string[] = [];
  const byRun = new Map<string, SwarmNode[]>();
  for (const n of nodes) {
    if (!byRun.has(n.runId)) {
      byRun.set(n.runId, []);
      order.push(n.runId);
    }
    byRun.get(n.runId)!.push(n);
  }

  const out: PositionedSwarmNode[] = [];

  order.forEach((runId, clusterIndex) => {
    const angle = clusterIndex * GOLDEN_ANGLE;
    const dist = clusterIndex === 0 ? 0 : CLUSTER_GAP * Math.sqrt(clusterIndex);
    const cx = Math.cos(angle) * dist;
    const cy = Math.sin(angle) * dist;

    const group = byRun.get(runId)!;
    const hasObjective = group.some((n) => n.type === 'objective');
    const isCentre = (n: SwarmNode) =>
      n.type === 'objective' || (!hasObjective && n.type === 'placeholder');

    const centre = group.filter(isCentre);
    const orbit = group.filter((n) => !isCentre(n));

    // Centre node(s) at the cluster centroid (tiny offset if more than one).
    centre.forEach((n, i) => {
      out.push({ ...n, x: cx + i * 6, y: cy + i * 6 });
    });

    // Distribute orbit nodes evenly within each ring radius.
    const byRadius = new Map<number, SwarmNode[]>();
    for (const n of orbit) {
      const r = ringFor(n.type);
      if (!byRadius.has(r)) byRadius.set(r, []);
      byRadius.get(r)!.push(n);
    }
    for (const [radius, ringNodes] of byRadius) {
      const count = ringNodes.length;
      ringNodes.forEach((n, i) => {
        const a = (i / count) * 2 * Math.PI;
        out.push({
          ...n,
          x: cx + Math.cos(a) * radius,
          y: cy + Math.sin(a) * radius,
        });
      });
    }
  });

  return out;
}
