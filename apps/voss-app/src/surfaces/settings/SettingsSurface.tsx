// V24-10 (VADE2-10) — Settings surface.

import { invoke } from '@tauri-apps/api/core';
import {
  type Component,
  For,
  Show,
  createMemo,
  createSignal,
  onCleanup,
  onMount,
} from 'solid-js';
import '../surfaces.css';
import './settings.css';
import {
  MODEL_CLI_KEYS,
  MODEL_PRESETS,
  type ModelCliKey,
} from '../../agents/modelPrefs';
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
import { listBundledThemes, type Theme } from '../../themes/themeCatalog';
import {
  applyThemeToRuntime,
  getCommittedTheme,
} from '../../themes/themeRuntime';

const BELL_BEHAVIORS: BellBehavior[] = ['visual', 'audible', 'badge', 'none'];
const CURSOR_SHAPES: CursorShape[] = ['block', 'bar', 'underline'];
const CURSOR_BLINKS: CursorBlink[] = ['off', 'slow', 'fast'];
const FONT_FAMILIES = [
  'JetBrains Mono',
  'SF Mono',
  'Menlo',
  'Fira Code',
  'Cascadia Code',
  'Monaco',
] as const;
const LINE_HEIGHTS = [1.25, 1.35, 1.5, 1.65, 1.8] as const;
const THEMES = listBundledThemes();

function themeVars(theme: Theme): string {
  return [
    `--settings-theme-bg: ${theme.cssVars['--bg-0']}`,
    `--settings-theme-surface: ${theme.cssVars['--bg-2']}`,
    `--settings-theme-fg: ${theme.cssVars['--fg-0']}`,
    `--settings-theme-muted: ${theme.cssVars['--fg-2']}`,
    `--settings-theme-focus: ${theme.cssVars['--focus']}`,
    `--settings-theme-border: ${theme.cssVars['--border-bright']}`,
  ].join(';');
}

function labelFor(value: string): string {
  return value
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

const SettingsSurface: Component = () => {
  const [settings, setSettings] = createSignal<AppearanceSettings>(
    getCommittedAppearanceSettings(),
  );
  const [themeId, setThemeId] = createSignal(getCommittedTheme().id);

  const activeTheme = createMemo(
    () => THEMES.find((theme) => theme.id === themeId()) ?? getCommittedTheme(),
  );

  // Reflect external changes (e.g. palette commands) live.
  const unsub = subscribeAppearanceSettings((s) => setSettings(s));
  onCleanup(unsub);

  onMount(() => {
    void invoke<string | null>('load_active_theme_id')
      .then((id) => {
        const theme = id
          ? THEMES.find((candidate) => candidate.id === id)
          : undefined;
        if (!theme) return;
        setThemeId(theme.id);
        applyThemeToRuntime(theme, {
          highContrast: settings().highContrastEnabled,
        });
      })
      .catch((e: unknown) =>
        console.error('[voss-app] load_active_theme_id failed:', e),
      );
  });

  /** Apply live + persist a single-field change. */
  function update(patch: Partial<AppearanceSettings>): void {
    const next = { ...settings(), ...patch };
    setSettings(next);
    applyAppearanceSettings(next);
    void saveAppearanceSettings(next).catch((e: unknown) =>
      console.error('[voss-app] saveAppearanceSettings failed:', e),
    );
  }

  function selectTheme(theme: Theme): void {
    setThemeId(theme.id);
    applyThemeToRuntime(theme, {
      highContrast: settings().highContrastEnabled,
    });
    void invoke('save_active_theme_id', { id: theme.id }).catch((e: unknown) =>
      console.error('[voss-app] save_active_theme_id failed:', e),
    );
  }

  function modelValue(cli: ModelCliKey): string {
    return settings().cliDefaultModels?.[cli] ?? '';
  }

  function modelPlaceholder(cli: ModelCliKey): string {
    return MODEL_PRESETS[cli].defaultModel ?? 'CLI default';
  }

  function updateModel(cli: ModelCliKey, model: string): void {
    const nextModels = { ...(settings().cliDefaultModels ?? {}) };
    const trimmed = model.trim();
    if (trimmed) {
      nextModels[cli] = trimmed;
    } else {
      delete nextModels[cli];
    }
    update({
      cliDefaultModels:
        Object.keys(nextModels).length > 0 ? nextModels : undefined,
    });
  }

  return (
    <div class="surface settings-surface" role="tabpanel" aria-label="Settings">
      <div class="surface__header">
        <span class="surface__title">Settings</span>
      </div>
      <div class="surface__body">
        <div class="settings-shell">
          <aside class="settings-nav" aria-label="Settings categories">
            <a class="settings-nav__item" href="#settings-theme">Theme</a>
            <a class="settings-nav__item" href="#settings-interface">Interface</a>
            <a class="settings-nav__item" href="#settings-terminal">Terminal</a>
            <a class="settings-nav__item" href="#settings-agents">Agents</a>
          </aside>

          <main class="settings-content">
            <section class="settings-panel" id="settings-theme">
              <div class="settings-panel__header">
                <div>
                  <h2 class="settings-panel__title">Theme</h2>
                  <p class="settings-panel__meta">
                    {activeTheme().name}
                    <span class="settings-panel__meta-chip">
                      {activeTheme().appearance}
                    </span>
                  </p>
                </div>
              </div>

              <div class="settings-theme-grid" aria-label="Theme picker">
                <For each={THEMES}>
                  {(theme) => (
                    <button
                      type="button"
                      classList={{
                        'settings-theme-card': true,
                        'settings-theme-card--active': themeId() === theme.id,
                      }}
                      style={themeVars(theme)}
                      title={theme.name}
                      aria-label={`Use theme: ${theme.name}`}
                      aria-pressed={themeId() === theme.id}
                      onClick={() => selectTheme(theme)}
                    >
                      <span class="settings-theme-card__preview">
                        <span class="settings-theme-card__bar" />
                        <span class="settings-theme-card__line settings-theme-card__line--strong" />
                        <span class="settings-theme-card__line" />
                        <span class="settings-theme-card__line settings-theme-card__line--short" />
                      </span>
                      <span class="settings-theme-card__name">{theme.name}</span>
                      <span class="settings-theme-card__appearance">
                        {theme.appearance}
                      </span>
                    </button>
                  )}
                </For>
              </div>
            </section>

            <section class="settings-panel" id="settings-interface">
              <div class="settings-panel__header">
                <div>
                  <h2 class="settings-panel__title">Interface</h2>
                  <p class="settings-panel__meta">{settings().fontFamily}</p>
                </div>
              </div>

              <div class="settings-grid settings-grid--two">
                <label class="settings-field settings-field--stacked">
                  <span class="settings-field__label">Terminal font</span>
                  <select
                    class="settings-field__input"
                    aria-label="Terminal font"
                    value={settings().fontFamily}
                    onChange={(e) =>
                      update({ fontFamily: e.currentTarget.value })
                    }
                  >
                    <For each={FONT_FAMILIES}>
                      {(font) => <option value={font}>{font}</option>}
                    </For>
                  </select>
                </label>

                <label class="settings-field settings-field--stacked">
                  <span class="settings-field__label">Font size</span>
                  <div class="settings-inline-control">
                    <input
                      class="settings-field__range"
                      type="range"
                      min={MIN_FONT_SIZE}
                      max={32}
                      value={settings().fontSize}
                      aria-label="Font size"
                      onInput={(e) =>
                        update({
                          fontSize: clampFontSize(e.currentTarget.valueAsNumber),
                        })
                      }
                    />
                    <span class="settings-value">{settings().fontSize}px</span>
                  </div>
                </label>

                <label class="settings-field settings-field--stacked">
                  <span class="settings-field__label">Line height</span>
                  <select
                    class="settings-field__input"
                    aria-label="Line height"
                    value={String(settings().lineHeight)}
                    onChange={(e) =>
                      update({ lineHeight: Number(e.currentTarget.value) })
                    }
                  >
                    <For each={LINE_HEIGHTS}>
                      {(height) => <option value={height}>{height}</option>}
                    </For>
                  </select>
                </label>

                <label class="settings-field settings-field--stacked">
                  <span class="settings-field__label">Letter spacing</span>
                  <div class="settings-inline-control">
                    <input
                      class="settings-field__input settings-field__input--compact"
                      type="number"
                      min={-1}
                      max={2}
                      step={0.1}
                      value={settings().letterSpacing}
                      aria-label="Letter spacing"
                      onChange={(e) =>
                        update({ letterSpacing: e.currentTarget.valueAsNumber })
                      }
                    />
                    <span class="settings-value">px</span>
                  </div>
                </label>
              </div>

              <div class="settings-toggle-row">
                <label class="settings-toggle">
                  <input
                    type="checkbox"
                    aria-label="High contrast"
                    checked={settings().highContrastEnabled}
                    onChange={(e) =>
                      update({ highContrastEnabled: e.currentTarget.checked })
                    }
                  />
                  <span class="settings-toggle__track" aria-hidden="true">
                    <span class="settings-toggle__thumb" />
                  </span>
                  <span class="settings-toggle__label">High contrast</span>
                </label>

                <label class="settings-toggle">
                  <input
                    type="checkbox"
                    aria-label="Reduced motion"
                    checked={settings().reducedMotionEnabled}
                    onChange={(e) =>
                      update({ reducedMotionEnabled: e.currentTarget.checked })
                    }
                  />
                  <span class="settings-toggle__track" aria-hidden="true">
                    <span class="settings-toggle__thumb" />
                  </span>
                  <span class="settings-toggle__label">Reduced motion</span>
                </label>

                <label class="settings-toggle">
                  <input
                    type="checkbox"
                    aria-label="Terminal ligatures"
                    checked={settings().ligatures}
                    onChange={(e) =>
                      update({ ligatures: e.currentTarget.checked })
                    }
                  />
                  <span class="settings-toggle__track" aria-hidden="true">
                    <span class="settings-toggle__thumb" />
                  </span>
                  <span class="settings-toggle__label">Terminal ligatures</span>
                </label>
              </div>
            </section>

            <section class="settings-panel" id="settings-terminal">
              <div class="settings-panel__header">
                <div>
                  <h2 class="settings-panel__title">Terminal</h2>
                  <p class="settings-panel__meta">
                    {labelFor(settings().cursorShape)}
                    <span class="settings-panel__meta-chip">
                      {settings().bellBehavior} bell
                    </span>
                  </p>
                </div>
              </div>

              <div class="settings-terminal-layout">
                <div class="settings-terminal-preview" aria-label="Terminal preview">
                  <div class="settings-terminal-preview__line">
                    <span class="settings-terminal-preview__prompt">voss</span>
                    <span>swarm run build-settings</span>
                    <span
                      classList={{
                        'settings-terminal-preview__cursor': true,
                        'settings-terminal-preview__cursor--bar':
                          settings().cursorShape === 'bar',
                        'settings-terminal-preview__cursor--underline':
                          settings().cursorShape === 'underline',
                        'settings-terminal-preview__cursor--blink':
                          settings().cursorBlink !== 'off',
                        'settings-terminal-preview__cursor--slow':
                          settings().cursorBlink === 'slow',
                      }}
                      style={{
                        background:
                          settings().cursorColor ??
                          activeTheme().cursor ??
                          activeTheme().cssVars['--focus'],
                      }}
                    />
                  </div>
                  <div
                    class="settings-terminal-preview__sample"
                    style={{
                      'font-family': settings().fontFamily,
                      'font-size': `${settings().fontSize}px`,
                      'line-height': String(settings().lineHeight),
                      'letter-spacing': `${settings().letterSpacing}px`,
                    }}
                  >
                    coordinator ready
                  </div>
                </div>

                <div class="settings-terminal-controls">
                  <div class="settings-field settings-field--stacked">
                    <span class="settings-field__label">Bell</span>
                    <div class="settings-segmented" aria-label="Bell behavior">
                      <For each={BELL_BEHAVIORS}>
                        {(behavior) => (
                          <button
                            type="button"
                            classList={{
                              'settings-segmented__btn': true,
                              'settings-segmented__btn--active':
                                settings().bellBehavior === behavior,
                            }}
                            aria-label={`Set bell behavior: ${behavior}`}
                            aria-pressed={settings().bellBehavior === behavior}
                            onClick={() => update({ bellBehavior: behavior })}
                          >
                            {behavior}
                          </button>
                        )}
                      </For>
                    </div>
                  </div>

                  <div class="settings-field settings-field--stacked">
                    <span class="settings-field__label">Cursor shape</span>
                    <div class="settings-segmented" aria-label="Cursor shape">
                      <For each={CURSOR_SHAPES}>
                        {(shape) => (
                          <button
                            type="button"
                            classList={{
                              'settings-segmented__btn': true,
                              'settings-segmented__btn--active':
                                settings().cursorShape === shape,
                            }}
                            aria-label={`Set cursor shape: ${shape}`}
                            aria-pressed={settings().cursorShape === shape}
                            onClick={() => update({ cursorShape: shape })}
                          >
                            {shape}
                          </button>
                        )}
                      </For>
                    </div>
                  </div>

                  <div class="settings-field settings-field--stacked">
                    <span class="settings-field__label">Cursor blink</span>
                    <div class="settings-segmented" aria-label="Cursor blink">
                      <For each={CURSOR_BLINKS}>
                        {(blink) => (
                          <button
                            type="button"
                            classList={{
                              'settings-segmented__btn': true,
                              'settings-segmented__btn--active':
                                settings().cursorBlink === blink,
                            }}
                            aria-label={`Set cursor blink: ${blink}`}
                            aria-pressed={settings().cursorBlink === blink}
                            onClick={() => update({ cursorBlink: blink })}
                          >
                            {blink}
                          </button>
                        )}
                      </For>
                    </div>
                  </div>

                  <label class="settings-field settings-field--stacked">
                    <span class="settings-field__label">Cursor color</span>
                    <div class="settings-inline-control">
                      <input
                        class="settings-color"
                        type="color"
                        aria-label="Cursor color"
                        value={
                          settings().cursorColor ??
                          activeTheme().cursor ??
                          activeTheme().cssVars['--focus']
                        }
                        onInput={(e) =>
                          update({ cursorColor: e.currentTarget.value })
                        }
                      />
                      <button
                        type="button"
                        class="settings-ghost-button"
                        onClick={() => update({ cursorColor: undefined })}
                      >
                        Use theme
                      </button>
                    </div>
                  </label>
                </div>
              </div>
            </section>

            <section class="settings-panel" id="settings-agents">
              <div class="settings-panel__header">
                <div>
                  <h2 class="settings-panel__title">Agents</h2>
                  <p class="settings-panel__meta">{MODEL_CLI_KEYS.length} CLIs</p>
                </div>
              </div>

              <div class="settings-model-list">
                <For each={MODEL_CLI_KEYS}>
                  {(cli) => (
                    <label class="settings-model-row">
                      <span class="settings-model-row__label">
                        {MODEL_PRESETS[cli].label}
                        <span class="settings-model-row__key">{cli}</span>
                      </span>
                      <span class="settings-model-row__controls">
                        <Show when={MODEL_PRESETS[cli].alternates.length > 0}>
                          <span
                            class="settings-segmented settings-segmented--compact"
                            aria-label={`${MODEL_PRESETS[cli].label} presets`}
                          >
                            <For each={MODEL_PRESETS[cli].alternates}>
                              {(model) => (
                                <button
                                  type="button"
                                  classList={{
                                    'settings-segmented__btn': true,
                                    'settings-segmented__btn--active':
                                      (modelValue(cli) ||
                                        MODEL_PRESETS[cli].defaultModel) === model,
                                  }}
                                  onClick={() => updateModel(cli, model)}
                                >
                                  {model}
                                </button>
                              )}
                            </For>
                          </span>
                        </Show>
                        <input
                          class="settings-field__input settings-model-row__input"
                          aria-label={`${MODEL_PRESETS[cli].label} model`}
                          value={modelValue(cli)}
                          placeholder={modelPlaceholder(cli)}
                          onChange={(e) => updateModel(cli, e.currentTarget.value)}
                        />
                      </span>
                    </label>
                  )}
                </For>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
};

export default SettingsSurface;
