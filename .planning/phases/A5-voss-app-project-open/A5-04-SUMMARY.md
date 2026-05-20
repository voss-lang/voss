# A5-04 Summary

**Date:** 2026-05-20

## Result

Created the controlled Solid setup surface for no-project startup:

- `SetupWindowProps` matches the A5-04 contract exactly.
- All behavior is props in, callbacks out.
- No local state, Tauri imports, `invoke`, `window`, or `document` usage.
- Recents are gated by Solid `<Show>` and rendered with `<For>`.
- All button query handles are deterministic `aria-label` values.

## Line Count Sanity

| Component | Lines |
|---|---:|
| `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx` | 110 |
| `apps/voss-app/src/components/setup/SetupWindow.tsx` | 176 |

SetupWindow is larger because it owns three visual regions instead of one compact titlebar control: heading copy, primary/secondary actions, and the conditional recents list.

## Representative DOM Dump

Rendered with:

```ts
recents={[
  '/Users/benjaminmarks/Projects/Voss',
  '/tmp/demo',
]}
```

Representative surface for A5-06 visual checkpoint:

```html
<main aria-label="Project setup" style="display: flex; align-items: center; justify-content: center; min-height: 100%; padding: 32px; background: var(--bg-0); color: var(--fg-0); font-family: var(--font-sans);">
  <section style="display: flex; flex-direction: column; gap: 18px; width: min(560px, 100%); padding: 24px; background: var(--bg-3); border: 1px solid var(--border);">
    <header style="display: flex; flex-direction: column; gap: 8px;">
      <h1 style="margin: 0; color: var(--fg-0); font-size: 20px; font-weight: 600; line-height: 1.2;">Choose a project</h1>
      <p style="margin: 0; color: var(--fg-2); font-size: 13px; line-height: 1.5;">Open a folder or continue without one.</p>
    </header>
    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
      <button type="button" aria-label="Open project" style="background: var(--focus); color: var(--fg-0); border: 1px solid var(--focus); padding: 9px 14px; font-family: var(--font-mono); font-size: 12px; cursor: pointer; line-height: 1;">Open project</button>
      <button type="button" aria-label="Start without project" style="background: transparent; color: var(--fg-2); border: 1px solid var(--border); padding: 9px 14px; font-family: var(--font-mono); font-size: 12px; cursor: pointer; line-height: 1;">Start without project</button>
    </div>
    <section aria-label="Recent projects" style="display: flex; flex-direction: column; gap: 8px; border-top: 1px solid var(--border); padding-top: 16px;">
      <h2 style="margin: 0; color: var(--fg-2); font-size: 12px; font-weight: 500; line-height: 1;">Recent projects</h2>
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <button type="button" aria-label="Open recent: Voss" title="/Users/benjaminmarks/Projects/Voss" style="background: var(--bg-0); color: var(--fg-0); border: 1px solid var(--border); padding: 8px 10px; font-family: var(--font-mono); font-size: 12px; cursor: pointer; line-height: 1.3; text-align: left;">/Users/benjaminmarks/Projects/Voss</button>
        <button type="button" aria-label="Open recent: demo" title="/tmp/demo" style="background: var(--bg-0); color: var(--fg-0); border: 1px solid var(--border); padding: 8px 10px; font-family: var(--font-mono); font-size: 12px; cursor: pointer; line-height: 1.3; text-align: left;">/tmp/demo</button>
      </div>
    </section>
  </section>
</main>
```

## CSS Tokens Introduced

Zero. SetupWindow reuses existing app variables only:

- `--bg-0`
- `--bg-3`
- `--fg-0`
- `--fg-2`
- `--focus`
- `--border`
- `--font-sans`
- `--font-mono`

## Verification

Passed:

```bash
cd /Users/benjaminmarks/Projects/Voss/apps/voss-app
pnpm vitest run src/components/setup/__tests__/SetupWindow.test.tsx --reporter=dot
pnpm exec tsc --noEmit -p .
grep -q 'export type SetupWindowProps' src/components/setup/SetupWindow.tsx
grep -q 'onOpenProject' src/components/setup/SetupWindow.tsx
grep -q 'onStartProjectLess' src/components/setup/SetupWindow.tsx
grep -q 'onOpenRecent' src/components/setup/SetupWindow.tsx
grep -q 'aria-label' src/components/setup/SetupWindow.tsx
! grep -nE 'invoke|@tauri-apps' src/components/setup/SetupWindow.tsx
! grep -niE '\bwhite\b|#[0-9a-f]{3,8}\b' src/components/setup/SetupWindow.tsx | grep -v '^[[:space:]]*//'
! rg -n 'createSignal|\binvoke\b|@tauri-apps|\bwindow\b|\bdocument\b' src/components/setup/SetupWindow.tsx
```

Not available:

```bash
pnpm exec prettier --check src/components/setup/SetupWindow.tsx src/components/setup/__tests__/SetupWindow.test.tsx
```

`prettier` is not installed in `apps/voss-app`.
