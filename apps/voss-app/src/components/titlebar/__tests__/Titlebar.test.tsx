import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'solid-js/web';

import Titlebar from '../Titlebar';

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

function titleRegion(root: HTMLElement): HTMLElement {
  const regions = Array.from(
    root.querySelectorAll('[data-tauri-drag-region]'),
  ) as HTMLElement[];
  const title = regions.find((el) => el.textContent?.trim().length);
  expect(title).toBeDefined();
  return title!;
}

describe('Titlebar - project name fallback', () => {
  it('bare render shows Voss ADE', () => {
    const el = mount(() => <Titlebar />);

    expect(titleRegion(el).textContent?.trim()).toBe('Voss ADE');
  });

  it('renders an explicit projectName as-is', () => {
    const el = mount(() => <Titlebar projectName="my-project" />);

    expect(titleRegion(el).textContent?.trim()).toBe('my-project');
  });

  it('explicit undefined falls back to Voss ADE', () => {
    const el = mount(() => <Titlebar projectName={undefined} />);

    expect(titleRegion(el).textContent?.trim()).toBe('Voss ADE');
  });

  it('empty string falls back to Voss ADE', () => {
    const el = mount(() => <Titlebar projectName="" />);

    expect(titleRegion(el).textContent?.trim()).toBe('Voss ADE');
  });
});
