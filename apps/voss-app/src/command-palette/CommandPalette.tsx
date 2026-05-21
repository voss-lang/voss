import { createMemo, createSignal, For, Show, onMount } from 'solid-js';
import { formatChord } from './chords';
import { rankCommandItems } from './fuzzy';
import { filterQuickItems, type QuickOpenItem } from './quickOpen';
import type { Command, CommandCategory } from './registry';

/**
 * A7-02 Task 1 — Variant B command palette (D-06).
 *
 * One component, two modes:
 * - `quick` (⌘P): saved layouts + recent projects.
 * - `full` (⌘⇧P): all registry commands with chord hints.
 *
 * Centered overlay, 48px input, 32px rows, 0px radius, token-only colors.
 * Esc / click-outside dismiss. Enter executes. ArrowUp/Down navigate.
 * While open, all keystrokes belong to the palette (T-A7-03).
 */

const CATEGORY_GLYPH: Record<CommandCategory, string> = {
  Window: 'W',
  Workspace: 'K',
  Pane: 'P',
  Layout: 'L',
  Project: 'R',
  Settings: 'S',
  Help: '?',
};

export interface CommandPaletteProps {
  mode: 'quick' | 'full';
  commands: readonly Command[];
  quickItems: readonly QuickOpenItem[];
  recentCommandIds: ReadonlySet<string>;
  onExecute: (id: string) => void;
  onDismiss: () => void;
}

export default function CommandPalette(props: CommandPaletteProps) {
  let inputRef!: HTMLInputElement;
  let panelRef!: HTMLDivElement;
  const [query, setQuery] = createSignal('');
  const [selected, setSelected] = createSignal(0);

  // --- Computed rows ---------------------------------------------------------

  type DisplayRow = {
    id: string;
    glyph: string;
    label: string;
    secondary?: string;
    chord?: string;
    section?: string;
  };

  const rows = createMemo((): DisplayRow[] => {
    if (props.mode === 'quick') {
      const filtered = filterQuickItems(props.quickItems, query());
      return filtered.map((item) => ({
        id: item.id,
        glyph: item.glyph,
        label: item.label,
        secondary: item.secondary,
        section: item.section,
      }));
    }
    const ranked = rankCommandItems(
      query(),
      props.commands as (Command & { id: string; label: string })[],
      props.recentCommandIds,
    );
    return ranked.map((cmd) => ({
      id: cmd.id,
      glyph: CATEGORY_GLYPH[cmd.category] ?? '·',
      label: cmd.label,
      chord: cmd.keybinding ? formatChord(cmd.keybinding) : undefined,
    }));
  });

  // --- Keyboard & focus ------------------------------------------------------

  const execute = (id: string) => {
    props.onExecute(id);
    props.onDismiss();
  };

  const onKeyDown = (e: KeyboardEvent) => {
    const r = rows();
    if (e.key === 'Escape') {
      e.preventDefault();
      props.onDismiss();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, r.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const row = r[selected()];
      if (row) execute(row.id);
    }
  };

  const onBackdropClick = (e: MouseEvent) => {
    if (panelRef && !panelRef.contains(e.target as Node)) {
      props.onDismiss();
    }
  };

  onMount(() => {
    inputRef?.focus();
  });

  // Reset selection when query changes
  const onInput = (value: string) => {
    setQuery(value);
    setSelected(0);
  };

  // --- Section headers for quick mode ----------------------------------------

  const sectionBreaks = createMemo((): Set<number> => {
    if (props.mode !== 'quick') return new Set();
    const r = rows();
    const breaks = new Set<number>();
    let lastSection = '';
    for (let i = 0; i < r.length; i++) {
      if (r[i].section && r[i].section !== lastSection) {
        breaks.add(i);
        lastSection = r[i].section!;
      }
    }
    return breaks;
  });

  // --- Placeholder & empty state ---------------------------------------------

  const placeholder = () =>
    props.mode === 'quick'
      ? 'Open layout or recent project'
      : 'Run command';

  const emptyHeading = () =>
    props.mode === 'quick'
      ? 'No layouts or recent projects'
      : 'No matching commands';

  const emptyBody = () =>
    props.mode === 'quick'
      ? 'Save a layout or open a project to add quick-open targets.'
      : 'Refine the query or press Esc to return to the focused pane.';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        'z-index': 100,
        display: 'flex',
        'justify-content': 'center',
        'padding-top': '64px',
        background: 'rgba(0,0,0,0.48)',
      }}
      onClick={onBackdropClick}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        data-testid="command-palette"
        class="font-mono"
        style={{
          width: 'min(680px, calc(100vw - 64px))',
          'max-height': 'min(520px, calc(100vh - 96px))',
          background: 'var(--bg-1)',
          border: '1px solid var(--border-bright)',
          'border-radius': '0px',
          'box-shadow': '0 16px 48px rgba(0,0,0,0.45)',
          display: 'flex',
          'flex-direction': 'column',
          overflow: 'hidden',
          'align-self': 'flex-start',
        }}
      >
        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          data-testid="palette-input"
          aria-label={
            props.mode === 'quick'
              ? 'Quick open search'
              : 'Command search'
          }
          placeholder={placeholder()}
          value={query()}
          onInput={(e) => onInput(e.currentTarget.value)}
          onKeyDown={onKeyDown}
          style={{
            width: '100%',
            height: '48px',
            padding: '0 16px',
            background: 'transparent',
            border: 'none',
            'border-bottom': '1px solid var(--border)',
            color: 'var(--fg-0)',
            'font-family': 'inherit',
            'font-size': '13px',
            'font-weight': 600,
            outline: 'none',
          }}
          onfocus={(e) => {
            (e.target as HTMLElement).style.boxShadow =
              'inset 0 0 0 1px var(--focus)';
          }}
          onblur={(e) => {
            (e.target as HTMLElement).style.boxShadow = 'none';
          }}
        />

        {/* Results */}
        <Show
          when={rows().length > 0}
          fallback={
            <div
              data-testid="palette-empty"
              style={{
                padding: '16px',
                color: 'var(--fg-2)',
                'font-size': '12px',
              }}
            >
              <div style={{ 'font-weight': 400, 'margin-bottom': '4px' }}>
                {emptyHeading()}
              </div>
              <div style={{ color: 'var(--fg-3)', 'font-size': '11px' }}>
                {emptyBody()}
              </div>
            </div>
          }
        >
          <div
            role="listbox"
            style={{ 'overflow-y': 'auto', flex: 1 }}
          >
            <For each={rows()}>
              {(row, idx) => (
                <>
                  <Show when={sectionBreaks().has(idx())}>
                    <div
                      style={{
                        padding: '8px 16px 4px',
                        'font-size': '10px',
                        color: 'var(--fg-3)',
                        'font-weight': 400,
                        'text-transform': 'uppercase',
                        'letter-spacing': '0.05em',
                      }}
                    >
                      {row.section}
                    </div>
                  </Show>
                  <button
                    type="button"
                    role="option"
                    aria-selected={idx() === selected()}
                    data-testid="palette-row"
                    onClick={() => execute(row.id)}
                    style={{
                      display: 'flex',
                      'align-items': 'center',
                      width: '100%',
                      'min-height': '32px',
                      padding: '0 16px',
                      background:
                        idx() === selected()
                          ? 'var(--bg-2)'
                          : 'transparent',
                      border: 'none',
                      'border-left-width': '1px',
                      'border-left-style': 'solid',
                      'border-left-color':
                        idx() === selected()
                          ? 'var(--focus)'
                          : 'transparent',
                      cursor: 'default',
                      'font-family': 'inherit',
                      'font-size': '12px',
                      'font-weight': idx() === selected() ? 600 : 400,
                      color:
                        idx() === selected()
                          ? 'var(--fg-0)'
                          : 'var(--fg-1)',
                      'text-align': 'left',
                    }}
                    onMouseEnter={() => setSelected(idx())}
                  >
                    {/* Glyph */}
                    <span
                      style={{
                        width: '16px',
                        'font-size': '10px',
                        color:
                          idx() === selected()
                            ? 'var(--fg-1)'
                            : 'var(--fg-3)',
                        'flex-shrink': 0,
                      }}
                    >
                      {row.glyph}
                    </span>
                    {/* Label */}
                    <span style={{ flex: 1, 'min-width': 0 }}>
                      {row.label}
                    </span>
                    {/* Secondary */}
                    <Show when={row.secondary}>
                      <span
                        style={{
                          color: 'var(--fg-3)',
                          'font-size': '11px',
                          'margin-left': '8px',
                          overflow: 'hidden',
                          'text-overflow': 'ellipsis',
                          'white-space': 'nowrap',
                          'max-width': '200px',
                        }}
                      >
                        {row.secondary}
                      </span>
                    </Show>
                    {/* Chord hint */}
                    <Show when={row.chord}>
                      <span
                        data-testid="chord-hint"
                        style={{
                          color: 'var(--fg-3)',
                          'font-size': '10px',
                          'margin-left': '8px',
                          'flex-shrink': 0,
                        }}
                      >
                        {row.chord}
                      </span>
                    </Show>
                  </button>
                </>
              )}
            </For>
          </div>
        </Show>
      </div>
    </div>
  );
}
