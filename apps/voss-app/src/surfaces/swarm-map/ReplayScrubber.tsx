// V24-07 (VADE2-07) — completed-run replay scrubber.
//
// Replaces ReplayPanel's ‹/› buttons with an accessible <input type="range">
// (UI-SPEC §7) driving the SAME pure reducer (computeBoardAtStep). MANDATORY
// proxy-strip before the reducer (Solid store proxies throw — ReplayPanel
// pattern). Shown only for completed runs (the caller gates on run_final).

import { type Component, createSignal, onCleanup } from 'solid-js';
import { computeBoardAtStep } from '../../org/replayReducer';
import type { RunData, SessionTreeNode } from '../../org/types';

export interface ReplayScrubberProps {
  data: RunData;
  /** Notified with each computed frame so the canvas can project the scrub. */
  onFrame?: (frame: ReturnType<typeof computeBoardAtStep>) => void;
}

/** Total replay steps = count of board.transition entries (ReplayPanel parity). */
function countSteps(nodes: SessionTreeNode[]): number {
  let n = 0;
  for (const node of nodes) {
    for (const t of node.transitions) {
      if (t.kind === 'board.transition') n++;
    }
  }
  return n;
}

const ReplayScrubber: Component<ReplayScrubberProps> = (props) => {
  const [step, setStep] = createSignal(0);
  const [playing, setPlaying] = createSignal(false);

  // MANDATORY proxy-strip before the pure reducer.
  const plainNodes = (): SessionTreeNode[] =>
    JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []));
  const total = () => countSteps(plainNodes());
  const maxStep = () => Math.max(0, total() - 1);
  const frame = () => {
    const f = computeBoardAtStep(plainNodes(), step());
    props.onFrame?.(f);
    return f;
  };

  let timer: ReturnType<typeof setInterval> | undefined;
  const stop = () => {
    if (timer) {
      clearInterval(timer);
      timer = undefined;
    }
    setPlaying(false);
  };
  const play = () => {
    if (total() === 0) return;
    setPlaying(true);
    timer = setInterval(() => {
      setStep((s) => {
        if (s >= maxStep()) {
          stop();
          return s;
        }
        return s + 1;
      });
    }, 600);
  };
  const toggle = () => (playing() ? stop() : play());
  onCleanup(stop);

  return (
    <div
      class="replay-scrubber"
      data-step={step()}
      data-done={frame().columns.Done?.length ?? 0}
    >
      <button
        type="button"
        class="replay-scrubber__play"
        aria-label={playing() ? 'Pause replay' : 'Play replay'}
        onClick={toggle}
      >
        {playing() ? '⏸' : '⏵'}
      </button>
      <input
        type="range"
        class="replay-scrubber__range"
        aria-label="Replay timeline"
        aria-valuenow={step()}
        aria-valuemin={0}
        aria-valuemax={maxStep()}
        min={0}
        max={maxStep()}
        value={step()}
        onInput={(e) => {
          stop();
          setStep(Number(e.currentTarget.value));
        }}
      />
      <span class="replay-scrubber__time">{step() + 1}</span>
      <span class="replay-scrubber__end">/ {Math.max(1, total())}</span>
    </div>
  );
};

export default ReplayScrubber;
