import WindowControls from './WindowControls';
import PresetSwitcher from './PresetSwitcher';

export default function Titlebar() {
  return (
    <div
      style={{
        display: 'flex',
        'align-items': 'center',
        height: 'var(--titlebar-height)',
        'flex-shrink': '0',
        background: 'var(--bg-0)',
        'border-bottom': '1px solid var(--border)',
        overflow: 'hidden',
      }}
    >
      {/* Window controls — platform-switched (mac: traffic lights; others: stub) */}
      <WindowControls />

      {/* Left drag spacer — the drag attribute belongs on the spacer ONLY, never on  */}
      {/* the outer container or any button-bearing child (RESEARCH Pitfall 1).        */}
      <div data-tauri-drag-region style={{ flex: '1' }} />

      {/* Project name placeholder — shows "Voss ADE" until A5 opens a project */}
      <div
        style={{
          'flex-shrink': '0',
          color: 'var(--fg-1)',
          'font-size': '11px',
          'font-family': 'var(--font-mono)',
          'font-weight': '400',
          'pointer-events': 'none',
        }}
      >
        Voss ADE
      </div>

      {/* Right drag spacer */}
      <div data-tauri-drag-region style={{ flex: '1' }} />

      {/* Preset switcher — visual only in A1 (no cost / model / token slot) */}
      <PresetSwitcher />
    </div>
  );
}
