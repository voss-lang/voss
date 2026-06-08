import { spawn } from "node:child_process";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline";

const HANDSHAKE_TIMEOUT_MS = 10_000;
const TEARDOWN_TIMEOUT_MS = 2_000;

export interface ServeFixture {
  baseUrl: string;
  token: string;
  pid: number;
  proc: SpawnedVossServe;
  teardown(): Promise<void>;
}

export interface ServeHandshake {
  v: 1;
  port: number;
  token: string;
}

type SpawnedVossServe = ReturnType<typeof spawn>;

export async function createTempCwd(prefix = "voss-sdk-"): Promise<string> {
  return mkdtemp(join(tmpdir(), prefix));
}

export async function spawnVossServe(cwd: string): Promise<ServeFixture> {
  const python = process.env.PYTHON_BIN ?? "python3";
  const proc = spawn(python, ["-m", "voss.cli", "serve"], {
    cwd,
    env: { ...process.env, VOSS_SERVE_FAKE_TURN: "1" },
    stdio: ["pipe", "pipe", "inherit"],
  });

  try {
    const handshake = await readHandshake(proc, python);
    const pid = proc.pid;

    if (pid === undefined) {
      throw new Error("voss serve did not report a process id");
    }

    return {
      baseUrl: `http://127.0.0.1:${handshake.port}`,
      token: handshake.token,
      pid,
      proc,
      teardown: () => teardownServe(proc),
    };
  } catch (error) {
    await teardownServe(proc);
    throw error;
  }
}

export async function expectPidGone(pid: number, timeoutMs = TEARDOWN_TIMEOUT_MS): Promise<void> {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    if (!isPidAlive(pid)) {
      return;
    }

    await delay(50);
  }

  if (isPidAlive(pid)) {
    throw new Error(`expected voss serve pid ${pid} to exit`);
  }
}

function readHandshake(proc: SpawnedVossServe, python: string): Promise<ServeHandshake> {
  if (proc.stdout === null) {
    return Promise.reject(new Error("voss serve stdout was not piped"));
  }

  const stdout = proc.stdout;

  return new Promise((resolve, reject) => {
    const lines = createInterface({ input: stdout });
    const timeout = setTimeout(() => {
      fail(new Error(`timed out waiting for voss serve handshake from ${python}`));
    }, HANDSHAKE_TIMEOUT_MS);

    function cleanup(): void {
      clearTimeout(timeout);
      lines.close();
      proc.removeListener("error", onError);
      proc.removeListener("exit", onExit);
    }

    function fail(error: Error): void {
      cleanup();
      reject(error);
    }

    function onError(error: Error): void {
      fail(error);
    }

    function onExit(code: number | null, signal: string | null): void {
      fail(
        new Error(
          `voss serve exited before handshake (code ${code ?? "null"}, signal ${signal ?? "null"}). ` +
            `Ensure PYTHON_BIN points at an environment with voss[server] installed.`,
        ),
      );
    }

    proc.once("error", onError);
    proc.once("exit", onExit);
    lines.once("line", (line) => {
      try {
        const handshake = parseHandshake(line);
        cleanup();
        resolve(handshake);
      } catch (error) {
        fail(error instanceof Error ? error : new Error(String(error)));
      }
    });
  });
}

async function teardownServe(proc: SpawnedVossServe): Promise<void> {
  proc.stdin?.end();

  if (proc.exitCode === null && !proc.killed) {
    proc.kill("SIGTERM");
  }

  if (proc.pid !== undefined) {
    await expectPidGone(proc.pid).catch(() => undefined);
  }
}

function parseHandshake(line: string): ServeHandshake {
  const value = JSON.parse(line) as unknown;

  if (!isRecord(value) || value.v !== 1) {
    throw new Error("voss serve handshake had an unexpected shape");
  }

  if (typeof value.port !== "number" || !Number.isInteger(value.port) || value.port <= 0 || value.port > 65_535) {
    throw new Error("voss serve handshake had an unexpected port");
  }

  if (typeof value.token !== "string" || value.token.length === 0) {
    throw new Error("voss serve handshake had an unexpected token");
  }

  return { v: 1, port: value.port, token: value.token };
}

function isPidAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    if (isNodeError(error) && error.code === "ESRCH") {
      return false;
    }

    throw error;
  }
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && "code" in error;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
