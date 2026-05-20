import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';

import SetupWindow from '../SetupWindow';
import {
  OPEN_PROJECT_LABEL,
  RECENTS_HEADING,
  START_PROJECT_LESS_LABEL,
} from '../../../project/projectStorage';

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

function openButton(root: HTMLElement): HTMLButtonElement {
  return root.querySelector(
    `button[aria-label="${OPEN_PROJECT_LABEL}"]`,
  ) as HTMLButtonElement;
}

function projectLessButton(root: HTMLElement): HTMLButtonElement {
  return root.querySelector(
    `button[aria-label="${START_PROJECT_LESS_LABEL}"]`,
  ) as HTMLButtonElement;
}

function recentButton(root: HTMLElement, path: string): HTMLButtonElement {
  const name = path.split('/').pop() || path;
  return root.querySelector(
    `button[aria-label="Open recent: ${name}"]`,
  ) as HTMLButtonElement;
}

describe('SetupWindow — primary actions', () => {
  it('renders the open-project action with locked copy', () => {
    const el = mount(() => (
      <SetupWindow
        recents={[]}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    expect(openButton(el).textContent?.trim()).toBe(OPEN_PROJECT_LABEL);
  });

  it('renders the start-without-project action with locked copy', () => {
    const el = mount(() => (
      <SetupWindow
        recents={[]}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    expect(projectLessButton(el).textContent?.trim()).toBe(
      START_PROJECT_LESS_LABEL,
    );
  });
});

describe('SetupWindow — recents visibility and structure', () => {
  it('hides recents when no recent paths are provided', () => {
    const el = mount(() => (
      <SetupWindow
        recents={[]}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    expect(el.querySelector('[aria-label="Recent projects"]')).toBeNull();
    expect(el.querySelectorAll('button[aria-label^="Open recent"]')).toHaveLength(
      0,
    );
  });

  it('renders one recent button per path with basename aria-labels', () => {
    const paths = ['/a', '/b', '/c'];
    const el = mount(() => (
      <SetupWindow
        recents={paths}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    expect(recentButton(el, '/a')).not.toBeNull();
    expect(recentButton(el, '/b')).not.toBeNull();
    expect(recentButton(el, '/c')).not.toBeNull();
    expect(el.querySelectorAll('button[aria-label^="Open recent"]')).toHaveLength(
      3,
    );
  });

  it('preserves exact full recent paths as text and title', () => {
    const path = '/Users/benjaminmarks/Projects/Voss';
    const el = mount(() => (
      <SetupWindow
        recents={[path]}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    const recent = recentButton(el, path);
    expect(recent.textContent?.trim()).toBe(path);
    expect(recent.getAttribute('title')).toBe(path);
  });

  it('renders the recents heading with locked copy when recents are present', () => {
    const el = mount(() => (
      <SetupWindow
        recents={['/a']}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    const heading = el.querySelector('h2');
    expect(heading?.textContent?.trim()).toBe(RECENTS_HEADING);
    expect(el.querySelector('main[aria-label="Project setup"]')).not.toBeNull();
  });

  it('does not render GridRoot inside the setup branch', () => {
    const el = mount(() => (
      <SetupWindow
        recents={['/a']}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    expect(el.querySelector('.grid-root')).toBeNull();
  });
});

describe('SetupWindow — controlled click behavior', () => {
  it('clicking Open project calls onOpenProject once and does not change DOM', () => {
    const onOpenProject = vi.fn<() => void>();
    const el = mount(() => (
      <SetupWindow
        recents={['/a']}
        onOpenProject={onOpenProject}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    const before = el.innerHTML;
    fireEvent.click(openButton(el));
    expect(onOpenProject).toHaveBeenCalledTimes(1);
    expect(el.innerHTML).toBe(before);
  });

  it('clicking Start without project calls onStartProjectLess once', () => {
    const onStartProjectLess = vi.fn<() => void>();
    const el = mount(() => (
      <SetupWindow
        recents={[]}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={onStartProjectLess}
      />
    ));
    fireEvent.click(projectLessButton(el));
    expect(onStartProjectLess).toHaveBeenCalledTimes(1);
  });

  it('clicking a recent calls onOpenRecent with the exact path', () => {
    const path = '/Users/benjaminmarks/Projects/Voss';
    const onOpenRecent = vi.fn<(path: string) => void>();
    const el = mount(() => (
      <SetupWindow
        recents={[path]}
        onOpenProject={() => {}}
        onOpenRecent={onOpenRecent}
        onStartProjectLess={() => {}}
      />
    ));
    fireEvent.click(recentButton(el, path));
    expect(onOpenRecent).toHaveBeenCalledTimes(1);
    expect(onOpenRecent).toHaveBeenCalledWith(path);
  });
});

describe('SetupWindow — surface discipline', () => {
  it('rendered HTML contains no raw color literals', () => {
    const el = mount(() => (
      <SetupWindow
        recents={['/a']}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    expect(el.innerHTML.toLowerCase()).not.toContain('white');
    expect(el.innerHTML).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  it('rendered HTML contains no forbidden L2 vocabulary', () => {
    const el = mount(() => (
      <SetupWindow
        recents={['/a']}
        onOpenProject={() => {}}
        onOpenRecent={() => {}}
        onStartProjectLess={() => {}}
      />
    ));
    const html = el.innerHTML.toLowerCase();
    for (const word of ['agent', 'worktree', 'reviewer', 'model', 'cost', 'token']) {
      expect(html).not.toContain(word);
    }
  });
});
