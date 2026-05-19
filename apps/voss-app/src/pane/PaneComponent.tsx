import { onMount, onCleanup, createSignal, Show } from 'solid-js';
import { Terminal } from '@xterm/xterm';
import { CanvasAddon } from '@xterm/addon-canvas';
import { FitAddon } from '@xterm/addon-fit';
import { SearchAddon } from '@xterm/addon-search';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import './pane.css';
import { PtyTransport } from './pty-ipc';

export interface PaneProps {
  /** Working directory for the spawned shell; header shows its basename. */
  cwd?: string;
  /** $SHELL basename for the header shell slot (A2 = static; A8 wires real). */
  shell?: string;
  /** Pane index — A2 is always 1; A3 assigns real indices. */
  index?: number;
}

function basename(p: string): string {
  const parts = p.replace(/\/+$/, '').split('/');
  return parts[parts.length - 1] || p;
}

type DotState = 'loading' | 'running' | 'exited';

export default function PaneComponent(props: PaneProps) {
  let containerRef!: HTMLDivElement;
  let bodyRef!: HTMLDivElement;
  let term: Terminal | undefined;
  let fitAddon: FitAddon | undefined;
  let transport: PtyTransport | undefined;
  let observer: ResizeObserver | undefined;
  let resizeTimer: ReturnType<typeof setTimeout> | undefined;
  let dprMedia: MediaQueryList | undefined;

  const [focused, setFocused] = createSignal(true); // single pane = focused (A2)
  const [dot, setDot] = createSignal<DotState>('loading');
  const [proc, setProc] = createSignal('');

  const cwdBase = () => basename(props.cwd ?? '~');
  const shellName = () => props.shell ?? 'shell';

  const onDpr = () => fitAddon?.fit();

  onMount(async () => {
    term = new Terminal({
      scrollback: 10_000,
      fontFamily:
        '"JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace',
      fontSize: 13,
      lineHeight: 1.5,
      theme: {
        background: '#0a0b0e',
        foreground: '#e8eaf0',
        cursor: '#5a7cff',
        cursorAccent: '#0a0b0e',
        selectionBackground: 'rgba(122, 162, 255, 0.30)',
        black: '#0a0b0e',
        brightBlack: '#444a5a',
        red: '#e87b7b',
        brightRed: '#e87b7b',
        green: '#6fd28f',
        brightGreen: '#6fd28f',
        yellow: '#e8b86c',
        brightYellow: '#e8b86c',
        blue: '#7aa2ff',
        brightBlue: '#7aa2ff',
        magenta: '#c084d4',
        brightMagenta: '#c084d4',
        cyan: '#6cc7d4',
        brightCyan: '#6cc7d4',
        white: '#aab0c0',
        brightWhite: '#e8eaf0',
      },
      cursorBlink: true,
      macOptionIsMeta: true,
      rightClickSelectsWord: false,
      allowProposedApi: false,
    });

    fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new SearchAddon());
    term.loadAddon(new WebLinksAddon());
    term.open(bodyRef);
    // D-01 Pitfall 2: CanvasAddon MUST load strictly AFTER term.open().
    term.loadAddon(new CanvasAddon());
    fitAddon.fit();

    const t = term;
    transport = new PtyTransport({
      write: (data, cb) => t.write(data, cb),
      onExit: () => setDot('exited'),
      onFgProcess: (name) => setProc(name),
      onTitle: (title) => setProc(title),
    });

    // D-07 primary: OSC 0/2 title → process slot.
    t.onTitleChange((title) => setProc(title));
    // Keystrokes → PTY.
    t.onData((d) => transport?.write(new TextEncoder().encode(d)));

    await transport.spawn({
      rows: t.rows,
      cols: t.cols,
      cwd: props.cwd,
    });
    setDot('running');

    // Debounced container resize → fit + pty_resize (Pattern 6).
    observer = new ResizeObserver(() => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        fitAddon?.fit();
        if (term) transport?.resize(term.rows, term.cols);
      }, 150);
    });
    observer.observe(containerRef);

    // Pitfall 5: re-fit on DPR (Retina ↔ external display) change.
    dprMedia = window.matchMedia(
      `(resolution: ${window.devicePixelRatio}dppx)`,
    );
    dprMedia.addEventListener('change', onDpr);
  });

  onCleanup(() => {
    if (resizeTimer) clearTimeout(resizeTimer);
    observer?.disconnect();
    dprMedia?.removeEventListener('change', onDpr);
    transport?.kill();
    term?.dispose();
  });

  return (
    <div
      ref={containerRef}
      class={focused() ? 'pane focused' : 'pane'}
      onClick={() => setFocused(true)}
    >
      <div class="pane-header">
        <span class={`dot ${dot()}`}>●</span>
        <span class="sep">·</span>
        <span class="idx">{props.index ?? 1}</span>
        <span class="sep">·</span>
        <span class="cwd">{cwdBase()}</span>
        <span class="sep">·</span>
        <span class="shell">{shellName()}</span>
        <Show when={proc()}>
          <span class="sep">·</span>
          <span class="proc">{proc()}</span>
        </Show>
        <span class="spacer" />
        <button class="menu" title="menu" type="button">
          ⋯
        </button>
      </div>
      <div ref={bodyRef} class="pane-body" />
    </div>
  );
}
