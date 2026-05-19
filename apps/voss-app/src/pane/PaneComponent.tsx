import { onMount, onCleanup, createSignal, Show } from 'solid-js';
import { Terminal, type ILink, type ILinkProvider } from '@xterm/xterm';
import { CanvasAddon } from '@xterm/addon-canvas';
import { FitAddon } from '@xterm/addon-fit';
import { SearchAddon } from '@xterm/addon-search';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { invoke } from '@tauri-apps/api/core';
import '@xterm/xterm/css/xterm.css';
import './pane.css';
import { PtyTransport } from './pty-ipc';
import PasteGuard from './PasteGuard';
import ExitBanner from './ExitBanner';
import FindBar from './FindBar';

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

/** D-06 copy/interrupt mode. 'smart' = selection→copy else SIGINT. A8 surfaces UI. */
type CopyMode = 'smart' | 'copy' | 'sigint';

// OSC8 / file-path link scheme allowlist (T-A2-09).
const ALLOWED_SCHEMES = ['http:', 'https:', 'mailto:', 'file:'];
// File-path detection (UI-SPEC §3 link handling).
const FILE_PATH_RE = /(\/[^\s'"]+|~\/[^\s'"]+|\.[./][^\s'"]+)/g;

export default function PaneComponent(props: PaneProps) {
  let containerRef!: HTMLDivElement;
  let bodyRef!: HTMLDivElement;
  let term: Terminal | undefined;
  let fitAddon: FitAddon | undefined;
  let searchAddon: SearchAddon | undefined;
  let transport: PtyTransport | undefined;
  let observer: ResizeObserver | undefined;
  let resizeTimer: ReturnType<typeof setTimeout> | undefined;
  let dprMedia: MediaQueryList | undefined;
  let fgPoll: ReturnType<typeof setInterval> | undefined;
  let perfStop = false; // stops the test-only rAF perf probe on cleanup
  let bypassFlag = false; // one-shot ⌘⇧V paste bypass
  let lastOscTitleAt = 0; // ms; D-07 OSC-vs-pgid arbitration
  const copyMode = 'smart' as CopyMode; // D-06 configurable hook (A8 UI)

  const [focused, setFocused] = createSignal(true); // single pane = focused (A2)
  const [dot, setDot] = createSignal<DotState>('loading');
  const [proc, setProc] = createSignal('');
  const [pendingPaste, setPendingPaste] = createSignal<string | null>(null);
  const [showFind, setShowFind] = createSignal(false);
  const [exitCode, setExitCode] = createSignal<number | null>(null);

  const cwdBase = () => basename(props.cwd ?? '~');
  const shellName = () => props.shell ?? 'shell';
  const onDpr = () => fitAddon?.fit();

  const writeBytes = (b: Uint8Array) => transport?.write(b);
  const writeStr = (s: string) => writeBytes(new TextEncoder().encode(s));

  const SEARCH_DECORATIONS = {
    activeMatchBackground: 'rgba(90,124,255,0.35)',
    matchOverviewRuler: 'rgba(90,124,255,0.35)',
    activeMatchColorOverviewRuler: 'rgba(90,124,255,0.35)',
  } as const;

  const openLink = (uri: string) => {
    try {
      const u = new URL(uri);
      if (ALLOWED_SCHEMES.includes(u.protocol)) {
        void invoke('open_url', { url: uri });
      }
      // Any other scheme is silently rejected (T-A2-09).
    } catch {
      /* not a valid URL — ignore */
    }
  };

  const filePathLinkProvider = (t: Terminal): ILinkProvider => ({
    provideLinks(y, callback) {
      const line = t.buffer.active.getLine(y - 1);
      if (!line) return callback(undefined);
      const text = line.translateToString(true);
      const links: ILink[] = [];
      for (const m of text.matchAll(FILE_PATH_RE)) {
        const idx = m.index ?? 0;
        links.push({
          text: m[0],
          range: {
            start: { x: idx + 1, y },
            end: { x: idx + m[0].length, y },
          },
          activate: (e: MouseEvent, path: string) => {
            if (e.metaKey) void invoke('open_path', { path });
          },
        });
      }
      callback(links.length ? links : undefined);
    },
  });

  const doSpawn = async (t: Terminal) => {
    await transport!.spawn({ rows: t.rows, cols: t.cols, cwd: props.cwd });
    setDot('running');
  };

  const restart = async () => {
    if (!term) return;
    transport?.kill();
    setExitCode(null);
    setDot('loading');
    await doSpawn(term); // scrollback preserved — Terminal NOT disposed
  };

  const keyHandler = (e: KeyboardEvent): boolean => {
    const meta = e.metaKey;
    if (!meta) return true;
    const k = e.key.toLowerCase();

    // ⌘⇧V — one-shot paste bypass (let the native paste through, no banner).
    if (e.shiftKey && k === 'v') {
      bypassFlag = true;
      return true;
    }
    // ⌘⇧K — clear scrollback.
    if (e.shiftKey && k === 'k') {
      term?.clear();
      return false;
    }
    // ⌘F — open find bar.
    if (!e.shiftKey && k === 'f') {
      setShowFind(true);
      return false;
    }
    // ⌘C — selection ⇒ copy; no selection ⇒ SIGINT (D-06, configurable).
    if (!e.shiftKey && k === 'c') {
      const hasSel = !!term?.hasSelection();
      if (copyMode !== 'sigint' && hasSel) {
        const sel = term?.getSelection() ?? '';
        void navigator.clipboard?.writeText(sel);
        term?.clearSelection();
        return false;
      }
      if (copyMode !== 'copy') {
        writeBytes(new Uint8Array([0x03])); // ETX → SIGINT to fg pgid
        return false;
      }
    }
    return true;
  };

  const onPaste = (e: ClipboardEvent) => {
    e.preventDefault();
    const text = e.clipboardData?.getData('text') ?? '';
    if (!text) return;
    if (text.includes('\n') && !bypassFlag) {
      setPendingPaste(text);
    } else {
      writeStr(text);
    }
    bypassFlag = false; // consume one-shot
  };

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
      linkHandler: {
        activate: (event: MouseEvent, uri: string) => {
          if (event.metaKey) openLink(uri);
        },
        allowNonHttpProtocols: true,
      },
    });

    fitAddon = new FitAddon();
    searchAddon = new SearchAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(searchAddon);
    term.loadAddon(new WebLinksAddon());
    term.open(bodyRef);
    // D-01 Pitfall 2: CanvasAddon MUST load strictly AFTER term.open().
    term.loadAddon(new CanvasAddon());
    fitAddon.fit();

    const t = term;
    t.registerLinkProvider(filePathLinkProvider(t));
    t.attachCustomKeyEventHandler(keyHandler);
    containerRef.addEventListener('paste', onPaste, true); // capture phase

    transport = new PtyTransport({
      write: (data, cb) => t.write(data, cb),
      onExit: (code) => {
        setDot('exited');
        setExitCode(code);
      },
      onFgProcess: (name) => setProc(name),
      onTitle: (title) => {
        lastOscTitleAt = Date.now();
        setProc(title);
      },
    });

    // D-07 primary: OSC 0/2 title → process slot.
    t.onTitleChange((title) => {
      lastOscTitleAt = Date.now();
      setProc(title);
    });
    // Keystrokes → PTY.
    t.onData((d) => writeStr(d));

    await doSpawn(t);

    // D-07 fallback: poll pgid only when no recent OSC title (>2s).
    fgPoll = setInterval(() => {
      if (Date.now() - lastOscTitleAt < 2000) return;
      transport
        ?.fgProcess()
        .then((name) => {
          if (name) setProc(name);
        })
        .catch(() => {});
    }, 500);

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
    if (fgPoll) clearInterval(fgPoll);
    observer?.disconnect();
    dprMedia?.removeEventListener('change', onDpr);
    containerRef?.removeEventListener('paste', onPaste, true);
    transport?.kill();
    term?.dispose();
  });

  const sendPaste = () => {
    const p = pendingPaste();
    if (p) writeStr(p);
    setPendingPaste(null);
  };
  const discardPaste = () => setPendingPaste(null);

  const closeFind = () => {
    setShowFind(false);
    term?.focus();
  };

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

      <Show when={showFind()}>
        <FindBar
          onNext={(q) =>
            searchAddon?.findNext(q, { decorations: SEARCH_DECORATIONS })
          }
          onPrev={(q) =>
            searchAddon?.findPrevious(q, { decorations: SEARCH_DECORATIONS })
          }
          onClose={closeFind}
        />
      </Show>

      <Show when={pendingPaste() !== null}>
        <PasteGuard
          pendingText={pendingPaste() as string}
          onSend={sendPaste}
          onDiscard={discardPaste}
        />
      </Show>

      <Show when={exitCode() !== null}>
        <ExitBanner exitCode={exitCode() as number} onRestart={restart} />
      </Show>
    </div>
  );
}
