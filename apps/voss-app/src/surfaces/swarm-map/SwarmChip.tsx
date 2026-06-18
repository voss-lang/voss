// V24 swarm surface — a rich chip card for one swarm node (the reference look).
//
// Renders role icon tile + name + a current-work line (the builder's bound
// Task.goal, real from the V25 plane) + a meta row (role tag, model, status dot).
// HONEST: every line is a real signal or omitted — no fabricated duration/cost
// (the plane snapshot carries no per-agent created_at/cost source yet, so those
// are intentionally hidden, not invented). Rendered inside an SVG <foreignObject>.

import { type Component, Show } from 'solid-js';
import Crown from 'lucide-solid/icons/crown';
import Hammer from 'lucide-solid/icons/hammer';
import Eye from 'lucide-solid/icons/eye';
import Search from 'lucide-solid/icons/search';
import Bot from 'lucide-solid/icons/bot';
import TriangleAlert from 'lucide-solid/icons/triangle-alert';
import type { Component as Comp } from 'solid-js';
import type { SwarmNode } from './swarmMapDerive';

function roleKind(node: SwarmNode): string {
  const r = (node.role ?? '').toLowerCase();
  if (node.type === 'alert' || r === 'operator') return 'operator';
  if (node.type === 'objective' || r.startsWith('coord')) return 'coordinator';
  if (r.startsWith('build')) return 'builder';
  if (r.startsWith('review')) return 'reviewer';
  if (r.startsWith('scout')) return 'scout';
  return 'agent';
}

const ICONS: Record<string, Comp<{ size?: number; 'stroke-width'?: number; 'aria-hidden'?: boolean }>> = {
  coordinator: Crown,
  builder: Hammer,
  reviewer: Eye,
  scout: Search,
  operator: TriangleAlert,
  agent: Bot,
};

function tagFor(kind: string, node: SwarmNode): string {
  if (kind === 'coordinator') return 'CONDUCTOR';
  if (kind === 'builder') return 'ENGINEER';
  if (kind === 'reviewer') return 'AUDITOR';
  if (kind === 'scout') return 'RESEARCHER';
  if (kind === 'operator') return 'OPERATOR';
  return (node.role ?? node.type).toUpperCase();
}

export interface SwarmChipProps {
  node: SwarmNode;
  selected?: boolean;
}

const SwarmChip: Component<SwarmChipProps> = (props) => {
  const kind = () => roleKind(props.node);
  const Icon = () => ICONS[kind()] ?? Bot;

  return (
    <div
      class="swarm-chip"
      classList={{
        'swarm-chip--coordinator': kind() === 'coordinator',
        'swarm-chip--operator': kind() === 'operator',
        'swarm-chip--placeholder': props.node.type === 'placeholder',
        'swarm-chip--selected': !!props.selected,
      }}
      data-role={kind()}
      data-status={props.node.status ?? ''}
      role="button"
      tabindex="0"
      aria-label={`${props.node.label}${props.node.work ? ` — ${props.node.work}` : ''}`}
    >
      <div class="swarm-chip__icon">
        {(() => {
          const I = Icon();
          return <I size={16} stroke-width={1.75} aria-hidden={true} />;
        })()}
      </div>
      <div class="swarm-chip__body">
        <div class="swarm-chip__name">{props.node.label}</div>
        <div class="swarm-chip__work">
          <span class="swarm-chip__chevron">&gt;</span>{' '}
          {props.node.work ?? '—'}
        </div>
        <div class="swarm-chip__meta">
          <span class="swarm-chip__tag">{tagFor(kind(), props.node)}</span>
          <Show when={props.node.model}>
            <span class="swarm-chip__model">{props.node.model}</span>
          </Show>
          <Show when={props.node.status}>
            <span class="swarm-chip__status">{props.node.status}</span>
          </Show>
        </div>
      </div>
    </div>
  );
};

export default SwarmChip;
