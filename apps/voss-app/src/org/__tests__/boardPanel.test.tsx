import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import {
  deriveColumn,
  deriveRisk,
  cardsFromRunData,
} from '../boardDerive';
import BoardPanel from '../panels/BoardPanel';
import type { RunData, SessionTreeNode } from '../types';
import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';
import auditReport from './fixtures/audit-report.json';

const FIXTURE_RUN_DATA = {
  run_id: nodeRoot.root_id,
  session_tree: { root_id: nodeRoot.root_id, nodes: [nodeRoot, nodeChild] },
  review: {},
  audit: auditReport,
  run_final: null,
} as unknown as RunData;

const ROOT = nodeRoot as unknown as SessionTreeNode;
const CHILD = nodeChild as unknown as SessionTreeNode;

function clone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x)) as T;
}

// --- Test harness ------------------------------------------------------------

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

// --- VADE-02: derivation -----------------------------------------------------

describe('boardDerive — column/risk (verified harness algorithm)', () => {
  it('deriveColumn: last board.transition + terminal "done" → Done', () => {
    expect(deriveColumn(CHILD)).toBe('Done');
  });

  it('deriveColumn: no board.transition, no terminal → Backlog', () => {
    expect(deriveColumn(ROOT)).toBe('Backlog');
  });

  it('deriveColumn: terminal "killed"/"timeout" overrides to Blocked', () => {
    const killed = clone(CHILD);
    killed.terminal_state!.exit_reason = 'killed';
    expect(deriveColumn(killed)).toBe('Blocked');
    const timeout = clone(CHILD);
    timeout.terminal_state!.exit_reason = 'timeout';
    expect(deriveColumn(timeout)).toBe('Blocked');
  });

  it('deriveRisk: first em.ticket.risk_tier; "med" when absent', () => {
    expect(deriveRisk(CHILD)).toBe('high');
    const noTicket = clone(CHILD);
    noTicket.transitions = noTicket.transitions.filter(
      (t) => t.kind !== 'em.ticket',
    );
    expect(deriveRisk(noTicket)).toBe('med');
  });

  it('cardsFromRunData: one card per non-root node; null → []', () => {
    const cards = cardsFromRunData(FIXTURE_RUN_DATA);
    expect(cards).toHaveLength(1);
    expect(cards[0].id).toBe(CHILD.id);
    expect(cards[0].column).toBe('Done');
    expect(cards[0].risk).toBe('high');
    expect(cardsFromRunData(null)).toEqual([]);
  });
});

// --- VADE-02: BoardPanel render ----------------------------------------------

describe('BoardPanel — 6 columns + cards + selection', () => {
  it('renders all 6 columns', () => {
    const root = mount(() => <BoardPanel data={FIXTURE_RUN_DATA} />);
    expect(root.querySelectorAll('.org-board-col').length).toBe(6);
    expect(root.textContent).toContain('Backlog');
    expect(root.textContent).toContain('In Progress');
    expect(root.textContent).toContain('Blocked');
  });

  it('places the child card in its derived (Done) column', () => {
    const root = mount(() => <BoardPanel data={FIXTURE_RUN_DATA} />);
    const doneCol = root.querySelector(
      '.org-board-col[data-col="Done"]',
    ) as HTMLElement;
    expect(doneCol).toBeTruthy();
    expect(doneCol.querySelector(`[data-card-id="${CHILD.id}"]`)).toBeTruthy();
  });

  it('clicking a card fires onCardSelect with the card id', () => {
    const onSelect = vi.fn();
    const root = mount(() => (
      <BoardPanel data={FIXTURE_RUN_DATA} onCardSelect={onSelect} />
    ));
    const card = root.querySelector(
      `[data-card-id="${CHILD.id}"]`,
    ) as HTMLElement;
    card.click();
    expect(onSelect).toHaveBeenCalledWith(CHILD.id);
  });

  it('null data → board empty-state copy', () => {
    const root = mount(() => <BoardPanel data={null} />);
    expect(root.textContent).toContain('No board data for this run.');
  });
});
