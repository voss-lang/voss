// V24-10 (VADE2-10) — Settings surface.
//
// Closes the V24-SPEC §41/86/91 requirement that Settings "wire to existing
// panels as-is". The existing appearanceCommands palette entries were stubs whose
// handlers only re-open the palette (App.tsx); this surface gives the persisted
// appearance settings an actual home. It is backed entirely by the existing
// appearance store (appearance/settings.ts) — no new Tauri command, no new schema.
//
// On any change: applyAppearanceSettings() (live apply + updates committed +
// notifies subscribers) then saveAppearanceSettings() (persists via the existing
// save_appearance_settings command). Theme/font-family selection is intentionally
// deferred (the theme catalog lives behind themeRuntime; this surface scopes to the
// AppearanceSettings fields). Persisted + applied is the bar.

import { type Component, createSignal, onCleanup } from 'solid-js';
import '../surfaces.css';
import './settings.css';
import {
  type AppearanceSettings,
  type BellBehavior,
  type CursorBlink,
  type CursorShape,
  applyAppearanceSettings,
  saveAppearanceSettings,
  getCommittedAppearanceSettings,
  subscribeAppearanceSettings,
  clampFontSize,
  MIN_FONT_SIZE,
} from '../../appearance/settings';

const BELL_BEHAVIORS: BellBehavior[] = ['visual', 'audible', 'badge', 'none'];
const CURSOR_SHAPES: CursorShape[] = ['block', 'bar', 'underline'];
const CURSOR_BLINKS: CursorBlink[] = ['off', 'slow', 'fast'];

const SettingsSurface: Component = () => {
  const [settings, setSettings] = createSignal<AppearanceSettings>(
    getCommittedAppearanceSettings(),
  );

  // Reflect external changes (e.g. palette commands) live.
  const unsub = subscribeAppearanceSettings((s) => setSettings(s));
  onCleanup(unsub);

  /** Apply live + persist a single-field change. */
  function update(patch: Partial<AppearanceSettings>): void {
    const next = { ...settings(), ...patch };
    setSettings(next);
    applyAppearanceSettings(next);
    void saveAppearanceSettings(next).catch((e: unknown) =>
      console.error('[voss-app] saveAppearanceSettings failed:', e),
    );
  }

  return (
    <div class="surface" role="tabpanel" aria-label="Settings">
      <div class="surface__header">
        <span class="surface__title">Settings</span>
      </div>
      <div class="surface__body">
        <div class="settings-section">
          <span class="settings-section__title">Appearance</span>

          <label class="settings-field">
            <span class="settings-field__label">Font size</span>
            <input
              class="settings-field__input"
              type="number"
              min={MIN_FONT_SIZE}
              max={32}
              value={settings().fontSize}
              aria-label="Font size"
              onChange={(e) =>
                update({ fontSize: clampFontSize(e.currentTarget.valueAsNumber) })
              }
            />
          </label>

          <label class="settings-field settings-field--toggle">
            <span class="settings-field__label">High contrast</span>
            <input
              type="checkbox"
              aria-label="High contrast"
              checked={settings().highContrastEnabled}
              onChange={(e) =>
                update({ highContrastEnabled: e.currentTarget.checked })
              }
            />
          </label>

          <label class="settings-field settings-field--toggle">
            <span class="settings-field__label">Reduced motion</span>
            <input
              type="checkbox"
              aria-label="Reduced motion"
              checked={settings().reducedMotionEnabled}
              onChange={(e) =>
                update({ reducedMotionEnabled: e.currentTarget.checked })
              }
            />
          </label>
        </div>

        <div class="settings-section">
          <span class="settings-section__title">Terminal</span>

          <label class="settings-field">
            <span class="settings-field__label">Bell</span>
            <select
              class="settings-field__input"
              aria-label="Bell behavior"
              value={settings().bellBehavior}
              onChange={(e) =>
                update({ bellBehavior: e.currentTarget.value as BellBehavior })
              }
            >
              {BELL_BEHAVIORS.map((b) => (
                <option value={b}>{b}</option>
              ))}
            </select>
          </label>

          <label class="settings-field">
            <span class="settings-field__label">Cursor shape</span>
            <select
              class="settings-field__input"
              aria-label="Cursor shape"
              value={settings().cursorShape}
              onChange={(e) =>
                update({ cursorShape: e.currentTarget.value as CursorShape })
              }
            >
              {CURSOR_SHAPES.map((c) => (
                <option value={c}>{c}</option>
              ))}
            </select>
          </label>

          <label class="settings-field">
            <span class="settings-field__label">Cursor blink</span>
            <select
              class="settings-field__input"
              aria-label="Cursor blink"
              value={settings().cursorBlink}
              onChange={(e) =>
                update({ cursorBlink: e.currentTarget.value as CursorBlink })
              }
            >
              {CURSOR_BLINKS.map((c) => (
                <option value={c}>{c}</option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </div>
  );
};

export default SettingsSurface;
