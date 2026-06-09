import { onMount, onCleanup, createSignal, Show } from 'solid-js';
import { Terminal, type ILink, type ILinkProvider } from '@xterm/xterm';
import { CanvasAddon } from '@xterm/addon-canvas';
import { FitAddon } from '@xterm/addon-fit';
import { SearchAddon } from '@xterm/addon-search';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { invoke } from '@tauri-apps/api/core';
import '@xterm/xterm/css/xterm.css';
import './pane.css';
import { PtyTransport, type AgentConfig, type BudgetState } from './pty-ipc';
import { isKnownAgentCli } from './agentDetect';
import { registerPaneProc, unregisterPaneProc } from './procRegistry';
import { registerPaneBudget, unregisterPaneBudget } from './budgetRegistry';
import { adoptionByPaneId } from './adoptionRegistry';
import { registerPaneContext, unregisterPaneContext } from './contextRegistry';
import { maybeLatchAgent, unregisterAgentPane } from './agentPaneRegistry';
import BudgetBar from '../grid/BudgetBar';
import BudgetPopover from '../grid/BudgetPopover';
import PasteGuard from './PasteGuard';
import ExitBanner from './ExitBanner';
import FindBar from './FindBar';
import {
  registerScrollbackProvider,
  unregisterScrollbackProvider,
} from './scrollbackRegistry';
import {
  getCurrentXtermTheme,
  registerTerminal,
  unregisterTerminal,
  applyAppearanceToTerminal,
} from '../themes/themeRuntime';
import {
  loadAppearanceSettings,
  subscribeAppearanceSettings,
  type AppearanceSettings,
} from '../appearance/settings';
import { DEFAULT_APPEARANCE_SETTINGS } from '../appearance/types';

export interface PaneProps {
  /** Pane id for scrollback registry and restore keying (A6). */
  id?: string;
  /** Working directory for the spawned shell; header shows its basename. */
  cwd?: string;
  /** $SHELL basename for the header shell slot (A2 = static; A8 wires real). */
  shell?: string;
  /** Pane index — A2 is always 1; A3 assigns real indices. */
  index?: number;
  /** Session-restored scrollback lines to seed before shell interaction (A6 D-09). */
  restoredScrollback?: string[];
  /** Called once on first user input in a restored pane (dismiss RestoreBanner). */
  onFirstInput?: () => void;
  agentConfig?: AgentConfig;
  workspacePath?: string;
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
  let firstInputFired = false; // A6: one-shot first-input callback guard
  let lastOscTitleAt = 0; // ms; D-07 OSC-vs-pgid arbitration
  let bellFlashTimer: ReturnType<typeof setTimeout> | undefined;
  let bellBadgeTimer: ReturnType<typeof setTimeout> | undefined;
  let appearanceUnsub: (() => void) | undefined;
  let headerRef!: HTMLDivElement;
  const copyMode = 'smart' as CopyMode; // D-06 configurable hook (A8 UI)

  const [focused, setFocused] = createSignal(true); // single pane = focused (A2)
  const [dot, setDot] = createSignal<DotState>('loading');
  const [proc, setProc] = createSignal('');
  const [pendingPaste, setPendingPaste] = createSignal<string | null>(null);
  const [showFind, setShowFind] = createSignal(false);
  const [exitCode, setExitCode] = createSignal<number | null>(null);
  const [appearance, setAppearance] = createSignal<AppearanceSettings>(
    DEFAULT_APPEARANCE_SETTINGS,
  );
  const [bellBadge, setBellBadge] = createSignal(false);
  const [headerFlash, setHeaderFlash] = createSignal(false);
  const [budget, setBudget] = createSignal<BudgetState | null>(null);
  const [budgetPopoverAnchor, setBudgetPopoverAnchor] = createSignal<HTMLElement | null>(null);
  const openBudgetPopover = (anchor: HTMLElement) =>
    setBudgetPopoverAnchor((prev) => (prev === anchor ? null : anchor));
  const closeBudgetPopover = () => setBudgetPopoverAnchor(null);
  const isAgentCli = () => isKnownAgentCli(proc());
  const updateProc = (name: string) => {
    setProc(name);
    const paneId = props.id;
    if (paneId) {
      registerPaneProc(paneId, name);
      maybeLatchAgent(paneId, name);
    }
  };

  const cwdBase = () => basename(props.cwd ?? '~');
  const shellName = () => props.shell ?? 'shell';
  const onDpr = () => fitAddon?.fit();

  const writeBytes = (b: Uint8Array) => transport?.write(b);
  const writeStr = (s: string) => writeBytes(new TextEncoder().encode(s));

  const playAudibleBell = () => {
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = 880;
      gain.gain.value = 0.08;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.08);
      osc.onended = () => void ctx.close();
    } catch {
      /* no audio — ignore */
    }
  };

  const triggerBell = (behavior: AppearanceSettings['bellBehavior']) => {
    if (behavior === 'none') return;

    if (behavior === 'badge') {
      setBellBadge(true);
      if (bellBadgeTimer) clearTimeout(bellBadgeTimer);
      bellBadgeTimer = setTimeout(() => setBellBadge(false), 2000);
      return;
    }

    if (behavior === 'audible') {
      playAudibleBell();
      return;
    }

    // visual flash (default)
    if (appearance().reducedMotionEnabled) {
      setHeaderFlash(true);
      if (bellFlashTimer) clearTimeout(bellFlashTimer);
      bellFlashTimer = setTimeout(() => setHeaderFlash(false), 120);
      return;
    }
    setHeaderFlash(true);
    if (bellFlashTimer) clearTimeout(bellFlashTimer);
    bellFlashTimer = setTimeout(() => setHeaderFlash(false), 200);
  };

  const buildTerminalOptions = (settings: AppearanceSettings) => ({
    scrollback: 10_000,
    fontFamily: `"${settings.fontFamily}", "SF Mono", "Menlo", ui-monospace, monospace`,
    fontSize: settings.fontSize,
    lineHeight: settings.lineHeight,
    letterSpacing: settings.letterSpacing,
    customGlyphs: settings.ligatures,
    theme: getCurrentXtermTheme(),
    cursorStyle: settings.cursorShape,
    cursorBlink: settings.cursorBlink !== 'off',
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
    if (props.agentConfig) {
      // VCKP-13: the managed toggle routes to the SANDBOXED command — never a
      // no-op security switch. Unmanaged configs keep the unchanged spawnAgent.
      if (props.agentConfig.managed) {
        await transport!.spawnManagedAgent({
          rows: t.rows,
          cols: t.cols,
          cwd: props.cwd,
          paneId: props.id ?? '',
          workspacePath: props.workspacePath,
          ...props.agentConfig,
          scope: props.agentConfig.scope ?? props.cwd ?? '',
          tier: props.agentConfig.tier ?? 'B',
        });
      } else {
        await transport!.spawnAgent({
          rows: t.rows,
          cols: t.cols,
          cwd: props.cwd,
          paneId: props.id ?? '',
          workspacePath: props.workspacePath,
          ...props.agentConfig,
        });
      }
    } else {
      await transport!.spawn({ rows: t.rows, cols: t.cols, cwd: props.cwd });
    }
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
    let settings = DEFAULT_APPEARANCE_SETTINGS;
    try {
      settings = await loadAppearanceSettings();
      setAppearance(settings);
    } catch {
      /* use defaults when settings unavailable (tests) */
    }

    term = new Terminal(buildTerminalOptions(settings));

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
    applyAppearanceToTerminal(t, settings);
    t.onBell(() => triggerBell(appearance().bellBehavior));
    t.registerLinkProvider(filePathLinkProvider(t));
    t.attachCustomKeyEventHandler(keyHandler);
    containerRef.addEventListener('paste', onPaste, true); // capture phase

    transport = new PtyTransport({
      write: (data, cb) => t.write(data, cb),
      onExit: (code) => {
        setDot('exited');
        setExitCode(code);
      },
      onFgProcess: (name) => updateProc(name),
      onTitle: (title) => {
        lastOscTitleAt = Date.now();
        updateProc(title);
      },
      onBudgetUpdate: (data) => {
        setBudget(data);
        if (props.id) {
          registerPaneBudget(props.id, data);
          // V14-12 (VCKP-12): adopted-agent budget-stop. Adoption happens
          // AFTER spawn, so the limit is read per-event from the adoption
          // registry instead of being frozen into the transport opts.
          const adopted = adoptionByPaneId()[props.id];
          if (
            adopted &&
            adopted.budgetUsd > 0 &&
            data.cost_usd >= adopted.budgetUsd
          ) {
            transport?.kill();
          }
        }
      },
      onContextUpdate: (data) => {
        if (props.id) registerPaneContext(props.id, data);
      },
      ...(props.agentConfig
        ? {
            agentPaneId: props.id,
            workspacePath: props.workspacePath,
            // VCKP-13c: budget-kill threshold for managed launches.
            budgetKillLimitUsd: props.agentConfig.budgetUsd,
          }
        : {}),
    });

    // D-07 primary: OSC 0/2 title → process slot.
    t.onTitleChange((title) => {
      lastOscTitleAt = Date.now();
      updateProc(title);
    });
    // Keystrokes → PTY. Fire onFirstInput once for restore-banner dismiss (A6 D-09).
    t.onData((d) => {
      if (!firstInputFired && props.onFirstInput) {
        firstInputFired = true;
        props.onFirstInput();
      }
      writeStr(d);
    });

    // A6: seed restored scrollback before shell spawns (context only, not re-executed).
    if (props.restoredScrollback && props.restoredScrollback.length > 0) {
      t.write(props.restoredScrollback.join('\r\n') + '\r\n');
    }

    // A6: register scrollback provider — extracts plain text from buffer.normal (D-02/D-03).
    const paneId = props.id ?? String(props.index ?? 1);
    registerTerminal(paneId, t);
    registerScrollbackProvider(paneId, () => {
      const buf = t.buffer.normal;
      const lines: string[] = [];
      const totalRows = buf.length;
      for (let i = 0; i < totalRows; i++) {
        const line = buf.getLine(i);
        if (line) {
          lines.push(line.translateToString(true));
        }
      }
      // Trim trailing empty lines (xterm pads the buffer to viewport height).
      while (lines.length > 0 && lines[lines.length - 1].trim() === '') {
        lines.pop();
      }
      return lines;
    });

    await doSpawn(t);

    appearanceUnsub = subscribeAppearanceSettings((next) => {
      setAppearance(next);
      applyAppearanceToTerminal(t, next);
    });

    // D-07 fallback: poll pgid only when no recent OSC title (>2s).
    fgPoll = setInterval(() => {
      if (Date.now() - lastOscTitleAt < 2000) return;
      transport
        ?.fgProcess()
        .then((name) => {
          if (name) updateProc(name);
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

    // D-02 test-only perf probe: records rAF deltas into a ring buffer for
    // the flood-perf harness. Inert in production (env guard) — T-A2-12.
    if (import.meta.env.MODE === 'test') {
      const w = window as unknown as { __vossPerf?: { frames: number[] } };
      w.__vossPerf = { frames: [] };
      let last = performance.now();
      const tick = () => {
        if (perfStop) return;
        const now = performance.now();
        const f = w.__vossPerf!.frames;
        f.push(now - last);
        if (f.length > 1000) f.shift();
        last = now;
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  });

  onCleanup(() => {
    perfStop = true;
    if (resizeTimer) clearTimeout(resizeTimer);
    if (fgPoll) clearInterval(fgPoll);
    if (bellFlashTimer) clearTimeout(bellFlashTimer);
    if (bellBadgeTimer) clearTimeout(bellBadgeTimer);
    appearanceUnsub?.();
    observer?.disconnect();
    dprMedia?.removeEventListener('change', onDpr);
    containerRef?.removeEventListener('paste', onPaste, true);
    const paneId = props.id ?? String(props.index ?? 1);
    unregisterTerminal(paneId);
    unregisterScrollbackProvider(paneId);
    if (props.id) unregisterPaneProc(props.id);
    if (props.id) unregisterPaneContext(props.id);
    if (props.id) unregisterPaneBudget(props.id);
    if (props.id) unregisterAgentPane(props.id);
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
      <div
        ref={headerRef}
        class={`pane-header${headerFlash() ? ' bell-flash' : ''}${isAgentCli() ? ' agent-pane' : ''}`}
      >
        <span class={`dot ${dot()}${isAgentCli() ? ' agent' : ''}`}>●</span>
        <span class="sep">·</span>
        <span class="idx">{props.index ?? 1}</span>
        <span class="sep">·</span>
        <span class="cwd">{cwdBase()}</span>
        <span class="sep">·</span>
        <span class="shell">{shellName()}</span>
        <Show when={proc()}>
          <span class="sep">·</span>
          <span class={isAgentCli() ? 'proc agent-proc' : 'proc'}>{proc()}</span>
        </Show>
        <Show when={isAgentCli() && !budget()}>
          <span class="sep">·</span>
          <span style={{ color: 'var(--accent-cyan)', 'font-size': '11px' }}>agent</span>
        </Show>
        <Show when={isAgentCli() && budget()?.model}>
          <span class="sep">·</span>
          <span class="model">{budget()!.model}</span>
        </Show>
        <Show when={bellBadge()}>
          <span class="sep">·</span>
          <span class="bell-badge" title="Bell">
            *
          </span>
        </Show>
        <span class="spacer" />
        <Show when={budget()}>
          {(b) => (
            <BudgetBar
              budget={b()}
              onClickDetail={(anchor) => openBudgetPopover(anchor)}
            />
          )}
        </Show>
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

      <Show when={budgetPopoverAnchor() != null && budget() != null}>
        <BudgetPopover
          budget={budget()!}
          anchor={budgetPopoverAnchor()!}
          onClose={closeBudgetPopover}
        />
      </Show>
    </div>
  );
}
