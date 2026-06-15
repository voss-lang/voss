// V24-04 (VADE2-04) — "Ask Voss to…" composer default-state contract.
//
// Progressive intake (D-04/D-05): on open the composer shows ONLY the ask field
// and a safety-mode control defaulted to "Read only". Scope / agent target /
// team / budget / attached context are collapsed behind "Advanced". No raw
// internal labels (Plan/Edit/Auto, runId) surface by default (D-09). This suite
// pins that behavior before the component exists (RED).

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import VossComposer from '../VossComposer';

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

describe('VossComposer — default open state (D-04/D-05)', () => {
  it('shows the ask textarea and a "Safety mode" control; Advanced panel collapsed', () => {
    const el = mount(() => <VossComposer open={true} onClose={() => {}} />);
    expect(el.querySelector('textarea')).toBeTruthy();
    expect(el.querySelector('[aria-label="Safety mode"]')).toBeTruthy();
    // Advanced panel absent until expanded.
    expect(el.querySelector('#advanced-panel')).toBeNull();
    const toggle = el.querySelector('[aria-controls="advanced-panel"]');
    expect(toggle?.getAttribute('aria-expanded')).toBe('false');
  });

  it('defaults the safety-mode control to "Read only"', () => {
    const el = mount(() => <VossComposer open={true} onClose={() => {}} />);
    const select = el.querySelector('[aria-label="Safety mode"]') as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(select.value).toBe('Read only');
  });

  it('shows no scope/budget fields and no raw Plan/Edit/Auto labels by default', () => {
    const el = mount(() => <VossComposer open={true} onClose={() => {}} />);
    expect(el.querySelector('[aria-label="Scope"]')).toBeNull();
    expect(el.querySelector('[aria-label="Budget"]')).toBeNull();
    const buttonLabels = Array.from(el.querySelectorAll('button')).map((b) =>
      b.textContent?.trim(),
    );
    expect(buttonLabels).not.toContain('Plan');
    expect(buttonLabels).not.toContain('Edit');
    expect(buttonLabels).not.toContain('Auto');
  });
});

describe('VossComposer — Advanced disclosure (D-05)', () => {
  it('clicking "Advanced" reveals the advanced fields and flips aria-expanded', () => {
    const el = mount(() => <VossComposer open={true} onClose={() => {}} />);
    const toggle = el.querySelector(
      '[aria-controls="advanced-panel"]',
    ) as HTMLButtonElement;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(el.querySelector('#advanced-panel')).toBeTruthy();
    expect(el.querySelector('[aria-label="Scope"]')).toBeTruthy();
    expect(el.querySelector('[aria-label="Budget"]')).toBeTruthy();
  });
});

describe('VossComposer — closed state', () => {
  it('renders nothing when open is false', () => {
    const el = mount(() => <VossComposer open={false} onClose={() => {}} />);
    expect(el.querySelector('textarea')).toBeNull();
    expect(el.querySelector('[aria-label="Safety mode"]')).toBeNull();
  });
});
