import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render } from 'solid-js/web';

// invoke resolves a successful DecisionResult; we assert run_decision is the
// ONLY write-path call (VADE-09 / one-write-path invariant).
const invokeMock = vi.fn((cmd: string, _args?: unknown) => {
  if (cmd === 'run_decision') {
    return Promise.resolve({ success: true, stdout: 'approve: permitted', stderr: '', exit_code: 0 });
  }
  return Promise.resolve(undefined);
});
vi.mock('@tauri-apps/api/core', () => ({ invoke: (cmd: string, args?: unknown) => invokeMock(cmd, args) }));

import BlockedPanel from '../panels/BlockedPanel';
import type { RunData } from '../types';
import nodeChild from './fixtures/node-child.json';

// A blocked card = a node whose derived column is "Blocked" (killed terminal).
function blockedRunData(): RunData {
  const killed = JSON.parse(JSON.stringify(nodeChild));
  killed.terminal_state.exit_reason = 'killed';
  return {
    run_id: 'a1b2c3d4e5f6',
    session_tree: { root_id: 'a1b2c3d4e5f6', nodes: [killed] },
    review: {},
    audit: null,
    run_final: null,
  } as unknown as RunData;
}

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
beforeEach(() => invokeMock.mockClear());
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

function byText(root: HTMLElement, text: string): HTMLElement | undefined {
  return [...root.querySelectorAll('button')].find(
    (b) => b.textContent?.trim() === text,
  ) as HTMLElement | undefined;
}

describe('BlockedPanel — VADE-09', () => {
  it('lists blocked cards with id + reason', () => {
    const root = mount(() => <BlockedPanel data={blockedRunData()} />);
    expect(root.textContent).toContain(nodeChild.id);
    expect(byText(root, 'Approve')).toBeTruthy();
  });

  it('Reject / Unblock are disabled (no non-interactive CLI surface)', () => {
    const root = mount(() => <BlockedPanel data={blockedRunData()} />);
    expect((byText(root, 'Reject') as HTMLButtonElement).disabled).toBe(true);
    expect((byText(root, 'Unblock') as HTMLButtonElement).disabled).toBe(true);
  });

  it('Approve opens a dialog showing the exact --approve CLI command', () => {
    const root = mount(() => <BlockedPanel data={blockedRunData()} />);
    byText(root, 'Approve')!.click();
    const dialog = root.querySelector('[role="dialog"]');
    expect(dialog).toBeTruthy();
    expect(dialog?.textContent).toContain('Command to run:');
    expect(dialog?.textContent).toContain('audit');
    expect(dialog?.textContent).toContain('--approve');
  });

  it('Confirm shells run_decision and nothing else (CLI is sole write path)', async () => {
    const root = mount(() => <BlockedPanel data={blockedRunData()} />);
    byText(root, 'Approve')!.click();
    const dialog = root.querySelector('[role="dialog"]') as HTMLElement;
    byText(dialog, 'Confirm')!.click();
    await Promise.resolve();
    await Promise.resolve();
    expect(invokeMock).toHaveBeenCalledWith('run_decision', expect.anything());
    const cmds = invokeMock.mock.calls.map((c) => c[0]);
    // no filesystem/write command — only run_decision (+ any refresh load_run)
    expect(cmds.every((c) => c === 'run_decision' || c === 'load_run')).toBe(true);
  });

  it('null data → empty-state copy', () => {
    const root = mount(() => <BlockedPanel data={null} />);
    expect(root.textContent).toContain('No blocked cards in this run.');
  });
});
