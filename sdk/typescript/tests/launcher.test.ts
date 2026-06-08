import { describe, expect, it } from "vitest";

import { VossLauncher } from "../src/node";
import { createTempCwd, expectPidGone } from "./helpers/serve-fixture";

describe("VossLauncher integration", () => {
  it("spawns voss serve, runs a turn, and leaves no orphan pid after dispose", async () => {
    const launcher = new VossLauncher();
    const previousFakeTurn = process.env.VOSS_SERVE_FAKE_TURN;
    process.env.VOSS_SERVE_FAKE_TURN = "1";

    let pid: number | undefined;

    try {
      const launched = await launcher.start({
        python: process.env.PYTHON_BIN,
        cwd: await createTempCwd("voss-sdk-launcher-"),
      });
      pid = launched.pid;

      const sessionId = await launched.client.createSession();
      expect(sessionId).toEqual(expect.any(String));

      const accepted = await launched.client.postMessage(sessionId, "hello from launcher");
      expect(accepted).toMatchObject({ v: 1, status: "accepted" });

      const cost = await launched.client.getCost(sessionId);
      expect(cost).toMatchObject({ v: 1 });
    } finally {
      launcher.dispose();
      restoreEnv("VOSS_SERVE_FAKE_TURN", previousFakeTurn);
    }

    expect(pid).toEqual(expect.any(Number));
    // expectPidGone polls process.kill(pid, 0) until it reports ESRCH.
    await expectPidGone(pid!);
  });
});

function restoreEnv(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name];
    return;
  }

  process.env[name] = value;
}
