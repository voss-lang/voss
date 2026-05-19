import WindowControls from './WindowControls';
import PresetSwitcher from './PresetSwitcher';
import type {
  ActiveLayout,
  LayoutPreset,
} from '../../grid/layoutPresets';

/**
 * A1 titlebar shell, extended in A4-02 to carry controlled preset state
 * down to `PresetSwitcher`. Window controls, drag regions, title text,
 * and 22px height all stay unchanged.
 *
 * Props are optional so existing A1/A3 tests that render `<Titlebar />`
 * continue to work; when omitted, the switcher defaults to `custom` and
 * `onLayoutSelect` is a no-op.
 */
export type TitlebarProps = {
  activeLayout?: ActiveLayout;
  layoutDisabled?: boolean;
  onLayoutSelect?: (preset: LayoutPreset) => void;
};

export default function Titlebar(props: TitlebarProps = {}) {
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
      <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />

      {/* Project name placeholder — shows "Voss ADE" until A5 opens a project.   */}
      {/* Drag attr on the text element itself so clicking the title drags the    */}
      {/* window (matches macOS standard titlebar behavior). Safe because the div */}
      {/* contains plain text only — no buttons / interactive children.           */}
      <div
        data-tauri-drag-region
        style={{
          'flex-shrink': '0',
          color: 'var(--fg-1)',
          'font-size': '11px',
          'font-family': 'var(--font-mono)',
          'font-weight': '400',
          'align-self': 'stretch',
          display: 'flex',
          'align-items': 'center',
        }}
      >
        Voss ADE
      </div>

      {/* Right drag spacer */}
      <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />

      {/* Controlled preset switcher (A4-02). App owns the activeLayout */}
      {/* signal and the apply callback; the switcher is a pure reflection. */}
      <PresetSwitcher
        activeLayout={props.activeLayout ?? 'custom'}
        disabled={props.layoutDisabled}
        onSelect={(p) => props.onLayoutSelect?.(p)}
      />
    </div>
  );
}
