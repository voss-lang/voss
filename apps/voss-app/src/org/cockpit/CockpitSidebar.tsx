// V14 chunk B — cockpit team sidebar (mockup .sidebar, 252px, left column).
//
// Three sections:
//   1. VOSS TEAM — roster rows reusing RosterPanel's derivation
//      (audit.team_config.roster_ids ∪ distinct node roles) restyled to the
//      mockup .arow look: role-colored dot, role name + status pill, sub line
//      (card count · scope), mono spent total.
//   2. EXTERNAL TERMINAL AGENTS — live launched agents: the A13 swarm roster
//      (when a manifest exists) plus cockpit-launched cards bound via the
//      bridge cardToPane map (Bridge B). The bridge stores only cardId→paneId,
//      so binary/provider is shown only for swarm rows where the manifest
//      carries it.
//   3. SESSIONS · RUN LINEAGE — compact root row (root id + node count);
//      clicking reveals the full SessionTreePanel in a collapsible so its
//      data-node-id tree stays reachable.

import { For, Show, createSignal } from 'solid-js';
import type { RunData } from '../types';
import type { SwarmReconcileResult } from '../swarmReconcile';
import { rosterRows, type RosterRow } from '../panels/RosterPanel';
import { cardToPane } from '../model/bridge';
import SessionTreePanel from '../panels/SessionTreePanel';

// COPIED from RosterPanel.tsx (private helper; copy not import — the GateBar
// budgetColor precedent).
function roleColor(role: string): string {
  switch (role) {
    case 'planner':
    case 'pm':
      return 'var(--role-planner)';
    case 'reviewer':
    case 'reviewer-a':
    case 'reviewer-b':
      return 'var(--role-reviewer)';
    case 'watcher':
      return 'var(--role-watcher)';
    case 'user':
      return 'var(--role-user)';
    default:
      return 'var(--role-executor)';
  }
}

function statusColor(status: RosterRow['status']): string {
  return status === 'active'
    ? 'var(--accent-green)'
    : status === 'done'
      ? 'var(--fg-2)'
      : 'var(--fg-3)';
}

function shortId(id: string): string {
  return id.length > 10 ? `${id.slice(0, 10)}…` : id;
}

interface ExternalRow {
  key: string;
  name: string;
  sub: string;
}

export default function CockpitSidebar(props: {
  data: RunData | null;
  swarm: SwarmReconcileResult;
}) {
  const [sessionsOpen, setSessionsOpen] = createSignal(false);

  const nodes = () => props.data?.session_tree.nodes ?? [];
  const roster = () => (props.data ? rosterRows(props.data) : []);

  const roleSpent = (role: string) =>
    nodes()
      .filter((n) => n.role === role)
      .reduce((s, n) => s + n.envelope.spent, 0);
  const roleCards = (role: string) =>
    nodes().filter((n) => n.role === role && n.parent_run_id !== null).length;
  const roleScope = (role: string) =>
    nodes().find((n) => n.role === role)?.scope ?? null;

  // Live launched agents: swarm roster + bridge-bound cards (deduped by pane).
  const externalRows = (): ExternalRow[] => {
    const swarmRows: ExternalRow[] = props.swarm.rosterRows.map((a) => ({
      key: `swarm-${a.id}`,
      name: a.provider || a.id,
      sub: a.role || a.status,
    }));
    const swarmPanes = new Set(
      props.swarm.rosterRows
        .map((a) => a.paneId)
        .filter((p): p is string => p != null),
    );
    const bridgeRows: ExternalRow[] = Object.entries(cardToPane())
      .filter(([, paneId]) => !swarmPanes.has(paneId))
      .map(([cardId, paneId]) => ({
        key: `bridge-${cardId}`,
        name: shortId(cardId),
        sub: `in grid · ${shortId(paneId)}`,
      }));
    return [...swarmRows, ...bridgeRows];
  };

  return (
    <>
      {/* 1 — Voss team roster */}
      <div class="cockpit-sect">Voss team</div>
      <Show
        when={roster().length > 0}
        fallback={
          <div class="cockpit-sidebar__empty">No roster data for this run.</div>
        }
      >
        <For each={roster()}>
          {(row) => (
            <div class="cockpit-arow">
              <span
                class="cockpit-arow__dot"
                style={{ background: roleColor(row.role) }}
              />
              <div class="cockpit-arow__meta">
                <div class="cockpit-arow__nm">
                  {row.role}
                  <span
                    class="cockpit-rolepill"
                    style={{
                      color: statusColor(row.status),
                      background: `color-mix(in srgb, ${statusColor(row.status)} 16%, transparent)`,
                    }}
                  >
                    {row.status}
                  </span>
                </div>
                <div class="cockpit-arow__sub">
                  {roleCards(row.role)} cards
                  {roleScope(row.role) ? ` · ${roleScope(row.role)}` : ''}
                </div>
              </div>
              <span class="cockpit-arow__cost">{roleSpent(row.role)}</span>
            </div>
          )}
        </For>
      </Show>

      {/* 2 — external terminal agents (live plane) */}
      <Show when={externalRows().length > 0}>
        <div class="cockpit-sect">External terminal agents</div>
        <Show when={props.swarm.idea}>
          <div class="cockpit-sidebar__goal">{props.swarm.idea}</div>
        </Show>
        <For each={externalRows()}>
          {(row) => (
            <div class="cockpit-arow">
              <span
                class="cockpit-arow__dot"
                style={{ background: 'var(--accent-green)' }}
              />
              <div class="cockpit-arow__meta">
                <div class="cockpit-arow__nm">{row.name}</div>
                <div class="cockpit-arow__sub cockpit-arow__sub--mono">
                  {row.sub}
                </div>
              </div>
              <span class="cockpit-arow__cost">—</span>
            </div>
          )}
        </For>
      </Show>

      {/* 3 — sessions / run lineage */}
      <Show when={props.data}>
        {(d) => (
          <>
            <div class="cockpit-sect">Sessions · run lineage</div>
            <div
              class={`cockpit-arow${sessionsOpen() ? ' cockpit-arow--sel' : ''}`}
              role="button"
              aria-expanded={sessionsOpen()}
              onClick={() => setSessionsOpen((o) => !o)}
            >
              <span
                class="cockpit-arow__dot"
                style={{ background: 'var(--focus)' }}
              />
              <div class="cockpit-arow__meta">
                <div class="cockpit-arow__nm">root</div>
                <div class="cockpit-arow__sub cockpit-arow__sub--mono">
                  {shortId(d().session_tree.root_id)} · {nodes().length} nodes
                </div>
              </div>
              <span class="cockpit-arow__cost">
                {sessionsOpen() ? '▾' : '▸'}
              </span>
            </div>
            <Show when={sessionsOpen()}>
              <div class="cockpit-sidebar__tree">
                <SessionTreePanel data={d()} />
              </div>
            </Show>
          </>
        )}
      </Show>
    </>
  );
}
