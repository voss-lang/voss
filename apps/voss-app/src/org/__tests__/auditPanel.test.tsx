import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import AuditPanel from '../panels/AuditPanel';
import type { RunData } from '../types';
import auditReport from './fixtures/audit-report.json';

const FIXTURE_RUN_DATA = {
  run_id: 'a1b2c3d4e5f6',
  session_tree: { root_id: 'a1b2c3d4e5f6', nodes: [] },
  review: {},
  audit: auditReport,
  run_final: null,
} as unknown as RunData;

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

describe('AuditPanel — VADE-04', () => {
  it('renders audit summary sections', () => {
    const root = mount(() => <AuditPanel data={FIXTURE_RUN_DATA} />);
    expect(root.textContent).toContain('PRINCIPLES');
    expect(root.textContent).toContain('CLAIMS');
  });

  it('flags the unsupported claim with ⚑ + aria-label', () => {
    const root = mount(() => <AuditPanel data={FIXTURE_RUN_DATA} />);
    const flag = root.querySelector('[aria-label="Unsupported claim"]');
    expect(flag).toBeTruthy();
    expect(flag?.textContent).toContain('⚑');
    // the unsupported node id (from fixture unsupported_claims) is rendered
    expect(root.textContent).toContain('bbb111222333');
  });

  it('renders the RESIDUAL RISK section from leak6', () => {
    const root = mount(() => <AuditPanel data={FIXTURE_RUN_DATA} />);
    expect(root.textContent).toContain('RESIDUAL RISK');
    expect(root.textContent).toContain('residual'); // leak6.status
  });

  it('null data → audit empty-state copy', () => {
    const root = mount(() => <AuditPanel data={null} />);
    expect(root.textContent).toContain('No audit data for this run.');
  });
});
