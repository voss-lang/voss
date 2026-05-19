/**
 * RED scaffold for D-02 flood-performance harness — owned by A2-05.
 *
 * When implemented (A2-05) this harness will:
 *   1. Spawn a PTY pane and flood it with a high-volume output stream
 *      (e.g. `cat` of a large file, or `yes` for N seconds).
 *   2. Sample per-frame render time via requestAnimationFrame.
 *   3. Assert p95 frame time < 33ms (≈30fps floor under flood) AND
 *      keystroke→echo latency < 200ms while the flood is in progress.
 *
 * Until then this script exits non-zero so the A2-VALIDATION.md D-02 command
 * resolves to a real FAILING command (never skipped, never green-by-default).
 *
 * Usage (A2-05): `pnpm test:flood-perf -- --cat <path>`
 */

interface FloodPerfArgs {
  cat: string | null;
}

function parseArgs(argv: string[]): FloodPerfArgs {
  const catIdx = argv.indexOf('--cat');
  // --cat is parsed now but unused until A2-05 wires the real flood source.
  return { cat: catIdx >= 0 ? (argv[catIdx + 1] ?? null) : null };
}

function main(): void {
  const args = parseArgs(process.argv.slice(2));
  void args; // parsed, intentionally unused this plan

  console.error(
    'RED: D-02 flood-perf not implemented — A2-05 ' +
      '(target: p95 rAF frame < 33ms, keystroke→echo < 200ms under flood)',
  );
  process.exit(1);
}

main();
