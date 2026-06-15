// V24-05 (VADE2-05) — Agents mission-control surface.
//
// Agent roster grouped by role (the session-tree nodes that carry a role).
// Each row: role-colored status dot (var(--role-*), mirroring AgentItem), the
// agent name (focal point), and cost (mono, tabular-nums). Clicking a row
// deep-links to its pane (bridge B) or review drawer via org/selection — same
// contract as the Task rows. Model/elapsed are omitted: the snapshot node shape
// does not carry them (honest-signal — no fabricated columns).

import { type Component, For, Show } from 'solid-js';
import '../surfaces.css';
import { runData, loading, loadError } from '../../org/orgStore';
import { paneIdForCard } from '../../org/model/bridge';
import { requestOpenInGrid, requestOpenInReview } from '../../org/selection';
import type { RunData } from '../../org/types';

interface AgentRow {
  id: string;
  name: string;
  role: string;
  spent: number;
}

function agentsFromRun(data: RunData | null): AgentRow[] {
  if (!data) return [];
  return data.session_tree.nodes
    .filter((n) => n.role !== null)
    .map((n) => ({
      id: n.id,
      name: n.scope ?? n.id,
      role: n.role as string,
      spent: n.envelope.spent,
    }));
}

function groupByRole(rows: AgentRow[]): { role: string; rows: AgentRow[] }[] {
  const order: string[] = [];
  const byRole = new Map<string, AgentRow[]>();
  for (const row of rows) {
    if (!byRole.has(row.role)) {
      byRole.set(row.role, []);
      order.push(row.role);
    }
    byRole.get(row.role)!.push(row);
  }
  return order.map((role) => ({ role, rows: byRole.get(role)! }));
}

function openAgent(row: AgentRow): void {
  const paneId = paneIdForCard(row.id);
  if (paneId) requestOpenInGrid(paneId);
  else requestOpenInReview(row.id);
}

const AgentsSurface: Component = () => {
  const agents = () => agentsFromRun(runData());
  const groups = () => groupByRole(agents());

  return (
    <div class="surface" role="tabpanel" aria-label="Agents">
      <div class="surface__header">
        <span class="surface__title">Agents</span>
        <span class="surface__count">{agents().length}</span>
      </div>
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
              <p class="org-error-state__heading">Couldn't load Agents.</p>
              <p class="org-error-state__body">Check that Voss is running.</p>
            </div>
          }
        >
          <Show
            when={agents().length > 0}
            fallback={
              <div class="surface-empty">
                <p class="surface-empty__title">No agents running</p>
                <p class="surface-empty__hint">Create a Task to deploy agents.</p>
              </div>
            }
          >
            <div class="surface__body">
              <For each={groups()}>
                {(group) => (
                  <div class="surface-group">
                    <div class="surface-group__header">
                      <span
                        class="surface-group__dot"
                        style={{ background: `var(--role-${group.role})` }}
                      />
                      <span class="surface-group__name">{group.role}</span>
                      <span class="surface-group__count">{group.rows.length}</span>
                    </div>
                    <For each={group.rows}>
                      {(row) => (
                        <div class="surface-row-wrap">
                          <div class="surface-row-line">
                            <button
                              type="button"
                              class="surface-row"
                              aria-label={`Open agent: ${row.name}`}
                              onClick={() => openAgent(row)}
                            >
                              <span
                                class="surface-row__dot"
                                style={{ background: `var(--role-${row.role})` }}
                              />
                              <span class="surface-row__name">{row.name}</span>
                              <span class="surface-row__meta">{row.role}</span>
                              <span class="surface-row__meta surface-row__meta--cost">
                                ${row.spent}
                              </span>
                            </button>
                          </div>
                        </div>
                      )}
                    </For>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </Show>
      </Show>
    </div>
  );
};

export default AgentsSurface;
