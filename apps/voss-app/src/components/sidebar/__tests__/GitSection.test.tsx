import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue([]) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import GitSection from '../GitSection';

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
  h.invoke.mockReset().mockResolvedValue([]);
});

describe('GitSection', () => {
  it("renders 'No project open' when workspacePath is null", () => {
    const el = mount(() => <GitSection workspacePath={null} />);
    expect(el.textContent).toContain('No project open');
  });

  it("renders 'Not a git repository' when no commits returned", async () => {
    h.invoke.mockResolvedValue([]);
    const el = mount(() => <GitSection workspacePath="/non-git" />);
    await new Promise((r) => setTimeout(r, 10));
    expect(el.textContent).toContain('Not a git repository');
  });

  it('renders commit entries', async () => {
    const now = Math.floor(Date.now() / 1000);
    h.invoke.mockResolvedValue([
      { hash: 'abc123', message: 'feat: add feature', timestamp_secs: now - 60 },
      { hash: 'def456', message: 'fix: bug fix', timestamp_secs: now - 3600 },
      { hash: 'ghi789', message: 'docs: update readme', timestamp_secs: now - 86400 },
    ]);
    const el = mount(() => <GitSection workspacePath="/test" />);
    await new Promise((r) => setTimeout(r, 10));
    expect(el.textContent).toContain('feat: add feature');
    expect(el.textContent).toContain('fix: bug fix');
    expect(el.textContent).toContain('docs: update readme');
  });

  it('formats relative timestamps', async () => {
    const now = Math.floor(Date.now() / 1000);
    h.invoke.mockResolvedValue([
      { hash: 'abc', message: 'recent', timestamp_secs: now - 300 },
    ]);
    const el = mount(() => <GitSection workspacePath="/test" />);
    await new Promise((r) => setTimeout(r, 10));
    expect(el.textContent).toContain('5m ago');
  });
});
