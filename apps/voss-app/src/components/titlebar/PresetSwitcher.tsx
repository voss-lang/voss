import { createSignal, For } from 'solid-js';

const PRESETS = ['fanout', 'pipeline', 'swarm', 'watchers'] as const;
type Preset = typeof PRESETS[number];

export default function PresetSwitcher() {
  // Default active: 'pipeline' — matches sketch default (A1-UI-SPEC Titlebar Contract)
  const [active, setActive] = createSignal<Preset>('pipeline');

  return (
    // Visual only — clicking updates state only, no layout geometry changes (CONTEXT D-04).
    <div
      style={{
        display: 'flex',
        border: '1px solid var(--border)',
        overflow: 'hidden',
        'flex-shrink': '0',
        'margin-right': '10px',
      }}
    >
      <For each={PRESETS}>
        {(preset) => (
          <button
            onClick={() => setActive(preset)}
            style={{
              background: active() === preset ? 'var(--focus)' : 'transparent',
              color: active() === preset ? 'white' : 'var(--fg-2)',
              border: 'none',
              'border-right': preset !== 'watchers' ? '1px solid var(--border)' : 'none',
              padding: '4px 10px',
              'font-family': 'var(--font-mono)',
              'font-size': '11px',
              cursor: 'pointer',
              'line-height': '1',
            }}
          >
            {preset}
          </button>
        )}
      </For>
    </div>
  );
}
