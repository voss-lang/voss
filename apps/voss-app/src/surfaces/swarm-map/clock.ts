// V24 swarm surface — shared 1-second ticker for live elapsed-time text.
//
// A single setInterval drives a `nowMs` signal that chips read to render elapsed
// duration ("2m 22s"). This is a TEXT update, not a CSS animation — the
// reduced-motion guard (swarmA11y) forbids `animation:`, not periodic text, so the
// ticker is a11y-safe. Lazily started on first read, stopped when unused.

import { createSignal, onCleanup } from 'solid-js';

const [nowMs, setNowMs] = createSignal(Date.now());

let timer: ReturnType<typeof setInterval> | undefined;
let subscribers = 0;

/** Subscribe to the 1s tick; returns the current `nowMs` accessor. Auto-stops
 *  the interval when the last subscriber (component) is disposed. */
export function useNow(): () => number {
  subscribers += 1;
  if (timer === undefined) {
    timer = setInterval(() => setNowMs(Date.now()), 1000);
  }
  onCleanup(() => {
    subscribers -= 1;
    if (subscribers <= 0 && timer !== undefined) {
      clearInterval(timer);
      timer = undefined;
    }
  });
  return nowMs;
}

/** Format an elapsed duration (ms) as "Ns" / "Nm Ns" / "Nh Nm". */
export function formatElapsed(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}
