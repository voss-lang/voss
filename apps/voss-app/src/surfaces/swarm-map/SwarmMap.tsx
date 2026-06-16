// V24-06 (VADE2-06) — static radial Swarm Map surface.
//
// Hand-rolled SVG radial graph derived ONLY from real signals. runData is
// proxy-stripped (JSON.parse(JSON.stringify)) before the pure deriveSwarmGraph
// (Pitfall 3 — Solid store proxies throw in plain reads). Honest empty state
// when there is no real graph; placeholder nodes render dashed/no-accent. The
// `swarm-paused` class pause-hook is wired now; the live keyframes land in V24-07.

import {
  type Component,
  createEffect,
  createSignal,
  For,
  onCleanup,
  onMount,
  Show,
} from 'solid-js';
import './swarmMap.css';
import { runData, loading, loadError } from '../../org/orgStore';
import { attentionQueue } from '../../org/attention/attentionQueue';
import { liveGraphPatches } from '../../org/live/sseClient';
import { paneIdForCard } from '../../org/model/bridge';
import { requestOpenInGrid, requestOpenInReview } from '../../org/selection';
import { deriveSwarmGraph, type SwarmNode, type SwarmEdge } from './swarmMapDerive';
import { layoutSwarm } from './swarmLayout';
import SwarmMapLegend from './SwarmMapLegend';
import EventTraceList from './EventTraceList';
import ReplayScrubber from './ReplayScrubber';

const EDGE_COLOR: Record<string, string> = {
  delegation: 'var(--focus)',
  message: 'var(--accent-blue)',
  'tool-call': 'var(--accent-magenta)',
  'file-edit': 'var(--accent-green)',
  review: 'var(--accent-amber)',
  blocker: 'var(--accent-red)',
};

/** Work-node deep-link: strip the `work:` prefix back to the real card id. */
function openNode(node: SwarmNode): void {
  if (node.type !== 'work') return;
  const cardId = node.id.slice('work:'.length);
  const paneId = paneIdForCard(cardId);
  if (paneId) requestOpenInGrid(paneId);
  else requestOpenInReview(cardId);
}

const SwarmMap: Component = () => {
  const [selected, setSelected] = createSignal<SwarmNode | null>(null);
  const [pan, setPan] = createSignal({ x: 480, y: 340 });
  let canvasRef: SVGSVGElement | undefined;

  // Proxy-strip before the pure derive (MANDATORY — Pitfall 3).
  const plainRunData = () => {
    const rd = runData();
    return rd ? JSON.parse(JSON.stringify(rd)) : null;
  };

  const graph = () => {
    const rd = plainRunData();
    const runs = rd ? [{ runData: rd, liveOverlay: {} }] : [];
    return deriveSwarmGraph(runs, attentionQueue());
  };

  const positioned = () => layoutSwarm(graph().nodes);
  const posById = () => {
    const map = new Map<string, { x: number; y: number }>();
    for (const n of positioned()) map.set(n.id, { x: n.x, y: n.y });
    return map;
  };

  // Reduced-motion: OS preference OR the html.reduced-motion class (A8). Under
  // reduced motion the connectors render static and the EventTraceList pins open.
  const [reduced, setReduced] = createSignal(false);
  onMount(() => {
    const mql =
      typeof window.matchMedia === 'function'
        ? window.matchMedia('(prefers-reduced-motion: reduce)')
        : null;
    const compute = () =>
      setReduced(
        document.documentElement.classList.contains('reduced-motion') ||
          (mql?.matches ?? false),
      );
    compute();
    mql?.addEventListener?.('change', compute);
    onCleanup(() => mql?.removeEventListener?.('change', compute));
  });

  // Live edges merged from the SSE patch stream — each keeps its real `source`
  // (honest-signal preserved on the live path). Mapped to rendered node ids;
  // undrawable patches still surface in the EventTraceList.
  const liveEdges = (): SwarmEdge[] => {
    const nodes = positioned();
    const obj = nodes.find((n) => n.type === 'objective');
    if (!obj) return [];
    const out: SwarmEdge[] = [];
    liveGraphPatches().forEach((p, i) => {
      const to = nodes.find(
        (n) => n.id === `work:${p.toNodeId}` || n.id.endsWith(`:${p.toNodeId}`),
      );
      if (!to) return;
      out.push({
        id: `live:${i}:${p.timestamp}`,
        from: obj.id,
        to: to.id,
        type: p.edgeType,
        source: p.source,
      });
    });
    return out;
  };
  const allEdges = () => [...graph().edges, ...liveEdges()];
  const pulsedIds = () => new Set(liveEdges().map((e) => e.to));

  // Pause-hook for V24-07 animations: toggle `swarm-paused` when the tab hides.
  createEffect(() => {
    const el = canvasRef;
    if (!el) return;
    const onVis = () => el.classList.toggle('swarm-paused', document.hidden);
    document.addEventListener('visibilitychange', onVis);
    onCleanup(() => document.removeEventListener('visibilitychange', onVis));
  });

  // Background drag-to-pan.
  let dragging = false;
  let last = { x: 0, y: 0 };
  const onDown = (e: PointerEvent) => {
    if (e.target !== canvasRef) return; // only the background
    dragging = true;
    last = { x: e.clientX, y: e.clientY };
  };
  const onMove = (e: PointerEvent) => {
    if (!dragging) return;
    const dx = e.clientX - last.x;
    const dy = e.clientY - last.y;
    last = { x: e.clientX, y: e.clientY };
    setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
  };
  const onUp = () => {
    dragging = false;
  };

  const hasGraph = () => graph().nodes.length > 0;

  return (
    <div class="surface swarm-map" role="tabpanel" aria-label="Swarm Map">
      <div class="swarm-map__body">
        <Show
          when={!loading()}
          fallback={
            <div class="org-spinner">
              <span class="org-spinner__glyph">⟳</span>
            </div>
          }
        >
          <Show
            when={!loadError()}
            fallback={
              <div class="org-error-state">
                <p class="org-error-state__heading">Couldn't load the Swarm Map.</p>
                <p class="org-error-state__body">Check that Voss is running.</p>
              </div>
            }
          >
            <Show
              when={hasGraph()}
              fallback={
                <div class="swarm-empty">
                  <p class="swarm-empty__title">No run data yet</p>
                  <p class="swarm-empty__hint">
                    Start a Task with ⌘K to see agents appear here.
                  </p>
                </div>
              }
            >
              <svg
                ref={canvasRef}
                class="swarm-canvas"
                width="100%"
                height="100%"
                onPointerDown={onDown}
                onPointerMove={onMove}
                onPointerUp={onUp}
                onPointerLeave={onUp}
              >
                <g transform={`translate(${pan().x},${pan().y})`}>
                  {/* edges first, under the nodes (derived + live, all sourced) */}
                  <For each={allEdges()}>
                    {(edge) => {
                      const a = posById().get(edge.from);
                      const b = posById().get(edge.to);
                      return (
                        <Show when={a && b}>
                          <line
                            class={`swarm-edge${edge.type === 'blocker' ? ' swarm-edge--blocker' : ''}`}
                            data-edge-type={edge.type}
                            data-edge-source={edge.source}
                            x1={a!.x}
                            y1={a!.y}
                            x2={b!.x}
                            y2={b!.y}
                            stroke={EDGE_COLOR[edge.type] ?? 'var(--border)'}
                          />
                        </Show>
                      );
                    }}
                  </For>

                  {/* Traveling dots on freshly-patched live edges (motion mode). */}
                  <Show when={!reduced()}>
                    <For each={liveEdges()}>
                      {(edge) => {
                        const a = posById().get(edge.from);
                        const b = posById().get(edge.to);
                        return (
                          <Show when={a && b}>
                            <circle
                              class="swarm-traveling-dot"
                              style={{
                                'offset-path': `path("M ${a!.x} ${a!.y} L ${b!.x} ${b!.y}")`,
                              }}
                            />
                          </Show>
                        );
                      }}
                    </For>
                  </Show>

                  <For each={positioned()}>
                    {(node) => (
                      <g
                        class={`swarm-node${!reduced() && pulsedIds().has(node.id) ? ' swarm-node-pulse' : ''}`}
                        data-node-type={node.type}
                        data-x={node.x}
                        data-y={node.y}
                        transform={`translate(${node.x},${node.y})`}
                        onClick={() => setSelected(node)}
                        onDblClick={() => openNode(node)}
                      >
                        <NodeShape node={node} />
                        <text class="swarm-node__label" y="28">
                          {node.label}
                        </text>
                      </g>
                    )}
                  </For>
                </g>
              </svg>
            </Show>
          </Show>
        </Show>
        {/* Replay scrubber — bottom strip, only for completed runs (D-06/D-07). */}
        <Show when={!loading() && !loadError() && runData()?.run_final}>
          <ReplayScrubber data={runData()!} />
        </Show>
      </div>
      <div class="swarm-side">
        <SwarmMapLegend node={selected()} onOpen={openNode} />
        <EventTraceList expanded={reduced()} />
      </div>
    </div>
  );
};

/** SVG shape per node type (UI-SPEC §Component Inventory 5). */
const NodeShape: Component<{ node: SwarmNode }> = (props) => {
  const t = props.node.type;
  if (t === 'objective')
    return <circle class="swarm-shape swarm-shape--objective" r="20" />;
  if (t === 'agent')
    return <circle class="swarm-shape swarm-shape--agent" r="14" />;
  if (t === 'work')
    return (
      <rect class="swarm-shape swarm-shape--work" x="-10" y="-10" width="20" height="20" />
    );
  if (t === 'artifact')
    return (
      <polygon class="swarm-shape swarm-shape--artifact" points="0,-11 11,0 0,11 -11,0" />
    );
  if (t === 'alert')
    return (
      <polygon class="swarm-shape swarm-shape--alert" points="0,-11 10,9 -10,9" />
    );
  return <circle class="swarm-shape swarm-shape--placeholder" r="10" />;
};

export default SwarmMap;
