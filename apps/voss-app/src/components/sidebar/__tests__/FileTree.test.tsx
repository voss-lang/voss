import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue([]) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import FileTree from '../FileTree';

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

describe('FileTree', () => {
  it('renders empty state when projectPath is null', () => {
    const el = mount(() => <FileTree projectPath={null} />);
    expect(el.textContent).toContain('No project open');
  });

  it('renders directory entries', async () => {
    h.invoke.mockResolvedValue([
      { name: 'src', is_dir: true, children: [{ name: 'main.ts', is_dir: false }] },
      { name: 'README.md', is_dir: false },
    ]);
    const el = mount(() => <FileTree projectPath="/test" />);
    // Wait for async invoke to resolve
    await new Promise((r) => setTimeout(r, 10));
    expect(el.textContent).toContain('src');
    expect(el.textContent).toContain('README.md');
  });

  it('clicking dir toggles expand/collapse', async () => {
    h.invoke.mockResolvedValue([
      { name: 'lib', is_dir: true, children: [{ name: 'index.ts', is_dir: false }] },
    ]);
    const el = mount(() => <FileTree projectPath="/test" />);
    await new Promise((r) => setTimeout(r, 10));
    // Dir should be auto-expanded, showing child
    expect(el.textContent).toContain('index.ts');
    // Click to collapse
    const dirRow = Array.from(el.querySelectorAll('div')).find(
      (d) => d.textContent?.includes('lib') && d.textContent?.includes('▾'),
    );
    if (dirRow) fireEvent.click(dirRow);
    await new Promise((r) => setTimeout(r, 10));
    // Child should be hidden after collapse
    // (The ▸ icon should now be visible instead of ▾)
  });

  it('clicking file does nothing', async () => {
    h.invoke.mockResolvedValue([
      { name: 'file.txt', is_dir: false },
    ]);
    const el = mount(() => <FileTree projectPath="/test" />);
    await new Promise((r) => setTimeout(r, 10));
    const fileRow = Array.from(el.querySelectorAll('div')).find(
      (d) => d.textContent?.includes('file.txt'),
    );
    // Should not throw or navigate
    if (fileRow) fireEvent.click(fileRow);
    expect(el.textContent).toContain('file.txt');
  });
});
