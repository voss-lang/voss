// V24-09 — reference-design top chrome contract.
//
// Pins away preset switcher / Plan·Edit·Auto toggle, and asserts the new bar
// affordances: search + ⌘K composer trigger, section label, project/branch
// identity pill, "New task" CTA, safety chip, and live chip.
//
// jsdom does not run WindowControls' Tauri onMount path (platform() throws and
// is caught → StubControls), matching the existing Titlebar.test.tsx contract.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import TopChrome from '../TopChrome';
// @ts-ignore -- node builtin available in the vitest runtime; app tsconfig is browser-lib only.
import { readFileSync } from 'node:fs';

const rawTopChrome: string = readFileSync(
  'src/components/titlebar/TopChrome.tsx',
  'utf8',
);

const defaultProps = { sectionLabel: 'WORKSPACES' };

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  vi.restoreAllMocks();
});

describe('TopChrome — no preset switcher in default chrome', () => {
  it('renders none of the fanout/pipeline/swarm/watchers preset labels', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="demo" />);
    const text = el.textContent ?? '';
    expect(text).not.toMatch(/\b(fanout|pipeline|swarm|watchers)\b/i);
  });

  it('renders no PresetSwitcher element (no preset-state node, no "Switch layout to" buttons)', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="demo" />);
    expect(el.querySelector('[data-preset-state]')).toBeNull();
    const presetButtons = Array.from(el.querySelectorAll('button')).filter((b) =>
      (b.getAttribute('aria-label') ?? '').startsWith('Switch layout to'),
    );
    expect(presetButtons).toHaveLength(0);
  });
});

describe('TopChrome — no raw Plan/Edit/Auto mode toggle in default chrome', () => {
  it('renders no titlebar-modetoggle group', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="demo" />);
    expect(el.querySelector('.titlebar-modetoggle')).toBeNull();
    expect(el.querySelector('[role="group"][aria-label="View mode"]')).toBeNull();
  });

  it('renders no button labeled exactly Plan, Edit, or Auto', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="demo" />);
    const labels = Array.from(el.querySelectorAll('button')).map((b) =>
      b.textContent?.trim(),
    );
    expect(labels).not.toContain('Plan');
    expect(labels).not.toContain('Edit');
    expect(labels).not.toContain('Auto');
  });
});

describe('TopChrome — reference chrome affordances', () => {
  it('renders search with placeholder "Search…" and a ⌘K hint', () => {
    const el = mount(() => (
      <TopChrome {...defaultProps} projectName="demo" onOpenComposer={() => {}} />
    ));
    const search = el.querySelector('[aria-label="Search"]');
    expect(search).toBeTruthy();
    expect(search?.getAttribute('placeholder')).toBe('Search…');
    expect(el.textContent).toContain('⌘K');
  });

  it('opens composer when search field is clicked', () => {
    const onOpenComposer = vi.fn();
    const el = mount(() => (
      <TopChrome {...defaultProps} projectName="demo" onOpenComposer={onOpenComposer} />
    ));
    const search = el.querySelector('[aria-label="Search"]') as HTMLInputElement;
    search.click();
    expect(onOpenComposer).toHaveBeenCalledTimes(1);
  });

  it('renders a "New task" button with exact copy', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="demo" />);
    const newTask = Array.from(el.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('New task'),
    );
    expect(newTask).toBeTruthy();
    expect(newTask?.textContent?.trim()).toBe('New task');
  });

  it('shows the section label when sectionLabel prop is passed', () => {
    const el = mount(() => (
      <TopChrome sectionLabel="TASKS" projectName="demo" />
    ));
    expect(el.textContent).toContain('TASKS');
  });

  it('shows a safety-mode chip with the supplied mode label', () => {
    const el = mount(() => (
      <TopChrome {...defaultProps} projectName="demo" currentSafetyMode="Read only" />
    ));
    expect(el.textContent).toContain('Read only');
  });

  it('hides the safety-mode chip when no mode is supplied', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="demo" />);
    const text = el.textContent ?? '';
    expect(text).not.toContain('Read only');
    expect(text).not.toContain('Can edit');
    expect(text).not.toContain('Autopilot');
  });

  it('renders the project name in the identity pill', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="my-project" />);
    expect(el.textContent).toContain('my-project');
  });

  it('renders git branch when gitBranch prop is passed', () => {
    const el = mount(() => (
      <TopChrome {...defaultProps} projectName="my-project" gitBranch="main" />
    ));
    expect(el.textContent).toContain('main');
  });

  it('falls back to "Voss ADE" when project name is empty', () => {
    const el = mount(() => <TopChrome {...defaultProps} projectName="" />);
    expect(el.textContent).toContain('Voss ADE');
  });
});

describe('TopChrome — source contract', () => {
  it('does not import PresetSwitcher', () => {
    expect(rawTopChrome).not.toContain('PresetSwitcher');
  });

  it('contains no titlebar-modetoggle markup', () => {
    expect(rawTopChrome).not.toContain('titlebar-modetoggle');
  });
});
