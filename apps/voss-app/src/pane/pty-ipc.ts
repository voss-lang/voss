import { invoke, Channel } from '@tauri-apps/api/core';

/**
 * Tauri PTY transport: owns the D-02 flood-contract frontend mechanisms —
 * per-requestAnimationFrame coalescing AND watermark backpressure (BOTH
 * required, complementary). The xterm `write` is injected so this layer is
 * unit-testable without a real Terminal.
 *
 * Mirrors the Rust `PtyEvent` (serde tag = "type", snake_case) from A2-02.
 */
export type PtyEvent =
  | { type: 'data'; bytes: number[] }
  | { type: 'exit'; code: number }
  | { type: 'fg_process'; name: string }
  | { type: 'title_change'; title: string };

/** D-02 watermark thresholds — locked constants (do not tune). */
export const HIGH_WATERMARK = 100_000; // 100 KB → pause
export const LOW_WATERMARK = 10_000; //  10 KB → resume

export interface PtyTransportOpts {
  /** xterm `term.write` (data, callback). Injected for testability. */
  write: (data: Uint8Array, cb?: () => void) => void;
  onExit?: (code: number) => void;
  onFgProcess?: (name: string) => void;
  onTitle?: (title: string) => void;
}

function mergeChunks(chunks: Uint8Array[]): Uint8Array {
  let total = 0;
  for (const c of chunks) total += c.length;
  const out = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    out.set(c, off);
    off += c.length;
  }
  return out;
}

export class PtyTransport {
  private channel = new Channel<PtyEvent>();
  private sessionId: string | null = null;
  private pending: Uint8Array[] = [];
  private rafPending = false;
  private watermark = 0;
  private opts: PtyTransportOpts;

  constructor(opts: PtyTransportOpts) {
    this.opts = opts;
    this.channel.onmessage = (ev: PtyEvent) => this.handle(ev);
  }

  private handle(ev: PtyEvent): void {
    switch (ev.type) {
      case 'data': {
        const buf = Uint8Array.from(ev.bytes);
        this.pending.push(buf);
        this.watermark += buf.length;
        if (!this.rafPending) {
          this.rafPending = true;
          requestAnimationFrame(() => this.flush());
        }
        // Backpressure: too much buffered → tell Rust to stop reading.
        if (this.watermark > HIGH_WATERMARK && this.sessionId) {
          void invoke('pty_pause', { sessionId: this.sessionId });
        }
        break;
      }
      case 'exit':
        this.opts.onExit?.(ev.code);
        break;
      case 'fg_process':
        this.opts.onFgProcess?.(ev.name);
        break;
      case 'title_change':
        this.opts.onTitle?.(ev.title);
        break;
    }
  }

  /** Merge a frame's worth of chunks into ONE xterm write (coalescing). */
  private flush(): void {
    this.rafPending = false;
    if (this.pending.length === 0) return;
    const merged = mergeChunks(this.pending);
    this.pending = [];
    this.opts.write(merged, () => {
      this.watermark = Math.max(this.watermark - merged.length, 0);
      if (this.watermark < LOW_WATERMARK && this.sessionId) {
        void invoke('pty_resume', { sessionId: this.sessionId });
      }
    });
  }

  async spawn(o: { rows: number; cols: number; cwd?: string }): Promise<string> {
    this.sessionId = await invoke<string>('spawn_pty', {
      onData: this.channel,
      rows: o.rows,
      cols: o.cols,
      cwd: o.cwd,
    });
    return this.sessionId;
  }

  write(bytes: Uint8Array): void {
    if (!this.sessionId) return;
    void invoke('pty_write', {
      sessionId: this.sessionId,
      data: Array.from(bytes),
    });
  }

  resize(rows: number, cols: number): void {
    if (!this.sessionId) return;
    void invoke('pty_resize', { sessionId: this.sessionId, rows, cols });
  }

  kill(): void {
    if (!this.sessionId) return;
    void invoke('pty_kill', { sessionId: this.sessionId });
    this.sessionId = null;
  }
}
