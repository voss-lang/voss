// V24-03 (VADE2-03) — quiet top chrome contract.
//
// One of the two hard product-failure conditions from the SPEC Interview Log
// is "raw internal labels in default chrome" / "presets-as-navigation". This
// suite pins both away from TopChrome: the rendered chrome must surface NO
// fanout/pipeline/swarm/watchers preset switcher and NO Plan/Edit/Auto (the
// titlebar-modetoggle) toggle. It must surface the ⌘K command-palette trigger,
// the live chip, and a safety-mode chip when a mode is supplied.
//
// jsdom does not run WindowControls' Tauri onMount path (platform() throws and
// is caught → StubControls), matching the existing Titlebar.test.tsx contract;
// the core mock is harmless and kept per the V24-03 plan harness spec.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import TopChrome from '../TopChrome';
// @ts-ignore -- node builtin available in the vitest runtime; app tsconfig is browser-lib only.
import { readFileSync } from 'node:fs';

// Path relative to the vitest root (apps/voss-app — vitest.config.ts).
const rawTopChrome: string = readFileSync(
  'src/components/titlebar/TopChrome.tsx',
  'utf8',
);

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
    const el = mount(() => <TopChrome projectName="demo" />);
    const text = el.textContent ?? '';
    expect(text).not.toMatch(/\b(fanout|pipeline|swarm|watchers)\b/i);
  });

  it('renders no PresetSwitcher element (no preset-state node, no "Switch layout to" buttons)', () => {
    const el = mount(() => <TopChrome projectName="demo" />);
    expect(el.querySelector('[data-preset-state]')).toBeNull();
    const presetButtons = Array.from(el.querySelectorAll('button')).filter((b) =>
      (b.getAttribute('aria-label') ?? '').startsWith('Switch layout to'),
    );
    expect(presetButtons).toHaveLength(0);
  });
});

describe('TopChrome — no raw Plan/Edit/Auto mode toggle in default chrome', () => {
  it('renders no titlebar-modetoggle group', () => {
    const el = mount(() => <TopChrome projectName="demo" />);
    expect(el.querySelector('.titlebar-modetoggle')).toBeNull();
    expect(el.querySelector('[role="group"][aria-label="View mode"]')).toBeNull();
  });

  it('renders no button labeled exactly Plan, Edit, or Auto', () => {
    const el = mount(() => <TopChrome projectName="demo" />);
    const labels = Array.from(el.querySelectorAll('button')).map((b) =>
      b.textContent?.trim(),
    );
    expect(labels).not.toContain('Plan');
    expect(labels).not.toContain('Edit');
    expect(labels).not.toContain('Auto');
  });
});

describe('TopChrome — quiet chrome affordances', () => {
  it('renders a ⌘K command-palette trigger button', () => {
    const el = mount(() => <TopChrome projectName="demo" onOpenComposer={() => {}} />);
    const trigger = Array.from(el.querySelectorAll('button')).find(
      (b) =>
        (b.textContent ?? '').includes('⌘K') ||
        (b.getAttribute('aria-label') ?? '').includes('⌘K'),
    );
    expect(trigger).toBeTruthy();
  });

  it('shows a safety-mode chip with the supplied mode label', () => {
    const el = mount(() => (
      <TopChrome projectName="demo" currentSafetyMode="Read only" />
    ));
    expect(el.textContent).toContain('Read only');
  });

  it('hides the safety-mode chip when no mode is supplied', () => {
    const el = mount(() => <TopChrome projectName="demo" />);
    const text = el.textContent ?? '';
    expect(text).not.toContain('Read only');
    expect(text).not.toContain('Can edit');
    expect(text).not.toContain('Autopilot');
  });

  it('renders the project name as identity text', () => {
    const el = mount(() => <TopChrome projectName="my-project" />);
    expect(el.textContent).toContain('my-project');
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
