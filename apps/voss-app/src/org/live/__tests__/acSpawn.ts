// V15-06 (VLIVE-08) — hermetic AC spawn helper. Reimplements the MINIMAL
// `voss serve` spawn from crates/voss-app-core/src/sidecar.rs in Node/TS for
// the AC suite ONLY (the production spawn stays in Rust): interpreter chain
// VOSS_PYTHON > repo .venv/bin/python > python3, `-m voss.cli serve --port 0`,
// one-line {v,port,token} stdout handshake (log lines never false-parse),
// continuous stderr drain, stdin held open as heartbeat, SIGKILL + exit-await
// reap (T-V15-SC / T-V15-02).
//
// Hermetic env: VOSS_SERVE_FAKE_TURN=1 is the server's canned-turn seam
// (harness/server/app.py — no creds, no network); VOSS_HERMETIC=1 is set too
// for the CLI-side stub discipline. LITELLM_LOCAL_MODEL_COST_MAP=true removes
// the boot-time network fetch (V13.2-06).

import { spawn, type ChildProcess } from 'node:child_process';
import { once } from 'node:events';
import { createInterface } from 'node:readline';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

export interface HermeticServe {
  port: number;
  token: string;
  kill: () => Promise<void>;
  /** stderr captured so far (diagnostics). */
  stderrTail: () => string;
}

/** Repo root: apps/voss-app/src/org/live/__tests__ → five dirs up. */
function repoRoot(): string {
  return join(__dirname, '..', '..', '..', '..', '..', '..');
}

function pythonPath(): string {
  if (process.env.VOSS_PYTHON) return process.env.VOSS_PYTHON;
  const venv = join(repoRoot(), '.venv', 'bin', 'python');
  if (existsSync(venv)) return venv;
  return 'python3';
}

const HANDSHAKE_BUDGET_MS = 60_000; // cold .pyc ~45s; warm ~1.5s (SPIKE)

export async function spawnHermeticServe(cwd: string): Promise<HermeticServe> {
  const child: ChildProcess = spawn(
    pythonPath(),
    ['-m', 'voss.cli', 'serve', '--port', '0'],
    {
      cwd,
      env: {
        ...process.env,
        VOSS_HERMETIC: '1',
        VOSS_SERVE_FAKE_TURN: '1',
        LITELLM_LOCAL_MODEL_COST_MAP: 'true',
        PYDANTIC_DISABLE_PLUGINS: '1',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    },
  );

  let stderrBuf = '';
  child.stderr!.on('data', (chunk: Buffer) => {
    stderrBuf += chunk.toString();
    if (stderrBuf.length > 16_384) stderrBuf = stderrBuf.slice(-16_384);
  });

  const kill = async (): Promise<void> => {
    if (child.exitCode === null && !child.killed) {
      child.kill('SIGKILL');
      await once(child, 'exit');
    } else if (child.exitCode === null) {
      await once(child, 'exit');
    }
  };

  const handshake = await new Promise<{ port: number; token: string }>(
    (resolve, reject) => {
      const timer = setTimeout(() => {
        void kill().then(() =>
          reject(
            new Error(
              `voss serve handshake timed out (${HANDSHAKE_BUDGET_MS}ms); stderr:\n${stderrBuf}`,
            ),
          ),
        );
      }, HANDSHAKE_BUDGET_MS);

      const lines = createInterface({ input: child.stdout! });
      lines.on('line', (line) => {
        try {
          const parsed = JSON.parse(line) as Record<string, unknown>;
          if (
            typeof parsed.port === 'number' &&
            typeof parsed.token === 'string'
          ) {
            clearTimeout(timer);
            // Keep draining stdout so a full pipe never blocks the server.
            resolve({ port: parsed.port, token: parsed.token });
          }
        } catch {
          // Non-JSON log line — ignore (handshake parse mirrors sidecar.rs).
        }
      });

      child.on('exit', (code) => {
        clearTimeout(timer);
        reject(
          new Error(
            `voss serve exited before handshake (code ${code}); stderr:\n${stderrBuf}`,
          ),
        );
      });
      child.on('error', (err) => {
        clearTimeout(timer);
        reject(err);
      });
    },
  );

  return {
    port: handshake.port,
    token: handshake.token,
    kill,
    stderrTail: () => stderrBuf,
  };
}
