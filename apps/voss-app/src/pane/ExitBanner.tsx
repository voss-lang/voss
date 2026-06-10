/** UI-SPEC §4 / PTY-07 — shell-exit banner with Restart. */
export interface ExitBannerProps {
  exitCode: number;
  onRestart: () => void;
  /** V15 D-11: override message (e.g. "[session ended]"); default "[exited {code}]". */
  message?: string;
  /** V15 D-11: hide Restart for server-death (default true = current behavior). */
  showRestart?: boolean;
}

type Tier = 'ok' | 'warn' | 'err';

function tier(code: number): Tier {
  if (code === 0) return 'ok';
  if (code > 127) return 'err';
  return 'warn';
}

export default function ExitBanner(props: ExitBannerProps) {
  const t = () => tier(props.exitCode);
  return (
    <div class="exit-banner">
      <span class={`eb-dot ${t()}`}>●</span>
      <span class={`eb-msg ${t()}`}>
        {props.message ?? `[exited ${props.exitCode}]`}
      </span>
      <span class="eb-spacer" />
      {props.showRestart !== false && (
        <button
          class="eb-restart"
          type="button"
          onClick={() => props.onRestart()}
        >
          Restart
        </button>
      )}
    </div>
  );
}
