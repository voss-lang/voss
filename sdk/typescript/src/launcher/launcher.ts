import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

import { createVossClient, type VossClient } from "../client/rest";

const HANDSHAKE_TIMEOUT_MS = 10_000;

export interface VossLauncherOptions {
  python?: string;
  cwd?: string;
}

export interface VossHandshake {
  v: 1;
  port: number;
  token: string;
}

export interface VossLaunchResult {
  client: VossClient;
  pid: number;
}

type SpawnedVossServe = ReturnType<typeof spawn>;

export class VossLauncher {
  private child: SpawnedVossServe | undefined;
  private exitHookRegistered = false;

  private readonly disposeOnProcessExit = () => {
    this.dispose();
  };

  async start(options: VossLauncherOptions = {}): Promise<VossLaunchResult> {
    if (this.child !== undefined) {
      throw new Error("voss serve is already running for this launcher");
    }

    const python = options.python ?? process.env.PYTHON_BIN ?? "python3";
    const cwd = options.cwd ?? process.cwd();
    const child = spawn(python, ["-m", "voss.cli", "serve"], {
      cwd,
      env: process.env,
      stdio: ["pipe", "pipe", "inherit"],
    });

    try {
      const handshake = await readHandshake(child);
      const pid = child.pid;

      if (pid === undefined) {
        throw new Error("voss serve did not report a process id");
      }

      this.child = child;
      this.registerProcessExitHook();
      child.once("exit", () => {
        if (this.child === child) {
          this.child = undefined;
          this.unregisterProcessExitHook();
        }
      });

      return {
        client: createVossClient(`http://127.0.0.1:${handshake.port}`, handshake.token),
        pid,
      };
    } catch (error) {
      disposeChild(child);
      throw error;
    }
  }

  dispose(): void {
    if (this.child === undefined) {
      return;
    }

    const child = this.child;
    this.child = undefined;
    this.unregisterProcessExitHook();
    disposeChild(child);
  }

  private registerProcessExitHook(): void {
    if (this.exitHookRegistered) {
      return;
    }

    process.on("exit", this.disposeOnProcessExit);
    this.exitHookRegistered = true;
  }

  private unregisterProcessExitHook(): void {
    if (!this.exitHookRegistered) {
      return;
    }

    process.removeListener("exit", this.disposeOnProcessExit);
    this.exitHookRegistered = false;
  }
}

function readHandshake(child: SpawnedVossServe): Promise<VossHandshake> {
  if (child.stdout === null) {
    return Promise.reject(new Error("voss serve stdout was not piped"));
  }

  const stdout = child.stdout;

  return new Promise((resolve, reject) => {
    const lines = createInterface({ input: stdout });
    const timeout = setTimeout(() => {
      fail(new Error("timed out waiting for voss serve handshake"));
    }, HANDSHAKE_TIMEOUT_MS);

    function cleanup(): void {
      clearTimeout(timeout);
      lines.close();
      child.removeListener("error", onError);
      child.removeListener("exit", onExit);
    }

    function fail(error: Error): void {
      cleanup();
      reject(error);
    }

    function onError(error: Error): void {
      fail(error);
    }

    function onExit(code: number | null, signal: string | null): void {
      fail(new Error(`voss serve exited before handshake (code ${code ?? "null"}, signal ${signal ?? "null"})`));
    }

    child.once("error", onError);
    child.once("exit", onExit);
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

function parseHandshake(line: string): VossHandshake {
  const value = JSON.parse(line) as unknown;

  if (!isRecord(value)) {
    throw new Error("voss serve handshake was not an object");
  }

  if (value.v !== 1) {
    throw new Error("voss serve handshake had an unexpected shape");
  }

  if (typeof value.port !== "number" || !Number.isInteger(value.port) || value.port <= 0 || value.port > 65_535) {
    throw new Error("voss serve handshake had an unexpected shape");
  }

  if (typeof value.token !== "string" || value.token.length === 0) {
    throw new Error("voss serve handshake had an unexpected shape");
  }

  return { v: 1, port: value.port, token: value.token };
}

function disposeChild(child: SpawnedVossServe): void {
  child.stdin?.end();

  if (child.exitCode === null && !child.killed) {
    child.kill("SIGTERM");
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
