import { afterEach, describe, expect, it } from "vitest";

import { createVossClient } from "../src/client/rest";
import { type AgentEvent, subscribeToEvents } from "../src/client/sse";
import { createTempCwd, spawnVossServe, type ServeFixture } from "./helpers/serve-fixture";

let fixture: ServeFixture | undefined;

afterEach(async () => {
  await fixture?.teardown();
  fixture = undefined;
});

describe("SSE client integration", () => {
  it("yields server.connected first, session.idle last, and typed fake-turn events between", async () => {
    fixture = await spawnVossServe(await createTempCwd());
    const client = createVossClient(fixture.baseUrl, fixture.token);
    const sessionId = await client.createSession();
    const controller = new AbortController();
    const iterator = subscribeToEvents(fixture.baseUrl, sessionId, fixture.token, controller.signal)[Symbol.asyncIterator]();

    try {
      const first = await iterator.next();
      expect(first.done).toBe(false);
      expect(first.value.type).toBe("server.connected");

      await client.postMessage(sessionId, "hello over sse");

      const events: AgentEvent[] = [first.value];
      while (true) {
        const next = await iterator.next();
        expect(next.done).toBe(false);
        events.push(next.value);

        if (next.value.type === "session.idle") {
          break;
        }
      }

      expect(events.at(0)?.type).toBe("server.connected");
      expect(events.at(-1)?.type).toBe("session.idle");
      expect(events.some((event) => event.type === "plan")).toBe(true);
      expect(events.some((event) => event.type === "stream.delta")).toBe(true);
      expect(events.some((event) => event.type === "final")).toBe(true);
    } finally {
      controller.abort();
    }
  });

  it("ends cleanly when the consumer aborts during a stream", async () => {
    fixture = await spawnVossServe(await createTempCwd());
    const client = createVossClient(fixture.baseUrl, fixture.token);
    const sessionId = await client.createSession();
    const controller = new AbortController();
    const unhandledRejections: unknown[] = [];
    let resolveConnected!: () => void;
    const connected = new Promise<void>((resolve) => {
      resolveConnected = resolve;
    });

    const onUnhandledRejection = (reason: unknown) => {
      unhandledRejections.push(reason);
    };

    process.on("unhandledRejection", onUnhandledRejection);

    try {
      const consume = (async () => {
        for await (const event of subscribeToEvents(fixture!.baseUrl, sessionId, fixture!.token, controller.signal)) {
          if (event.type === "server.connected") {
            resolveConnected();
            continue;
          }

          controller.abort();
        }
      })();

      await connected;
      await client.postMessage(sessionId, "abort this stream");
      await expect(consume).resolves.toBeUndefined();
      await delay(0);
      expect(unhandledRejections).toHaveLength(0);
    } finally {
      process.removeListener("unhandledRejection", onUnhandledRejection);
      controller.abort();
    }
  });
});

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
