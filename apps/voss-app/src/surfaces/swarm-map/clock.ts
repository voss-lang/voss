import { createSignal, onCleanup } from 'solid-js';

const [nowMs, setNowMs] = createSignal(Date.now());

let timer: ReturnType<typeof setInterval> | undefined;
let subscribers = 0;

/**
 * Subscribe to the 1s tick; returns the current `nowMs` accessor. Auto-stops
 * the interval when the last subscriber (component) is disposed
 */
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

export function formatElapsed(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}
