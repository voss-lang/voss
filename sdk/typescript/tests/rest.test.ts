import { afterEach, describe, expect, it } from "vitest";

import { createVossClient } from "../src/client/rest";
import { VossApiError } from "../src/errors";
import { createTempCwd, spawnVossServe, type ServeFixture } from "./helpers/serve-fixture";

let fixture: ServeFixture | undefined;

afterEach(async () => {
  await fixture?.teardown();
  fixture = undefined;
});

describe("REST client integration", () => {
  it("creates a session, posts a message, reads cost, and deletes the session", async () => {
    fixture = await spawnVossServe(await createTempCwd());
    const client = createVossClient(fixture.baseUrl, fixture.token);

    const sessionId = await client.createSession();
    expect(sessionId).toEqual(expect.any(String));

    const accepted = await client.postMessage(sessionId, "hello from rest test");
    expect(accepted).toMatchObject({ v: 1, status: "accepted" });

    const cost = await client.getCost(sessionId);
    expect(cost).toMatchObject({ v: 1 });
    expect(Number(cost.total_usd)).toBeGreaterThanOrEqual(0);

    await expect(client.deleteSession(sessionId)).resolves.toBeUndefined();
  });

  it("surfaces bad bearer tokens as VossApiError 401", async () => {
    fixture = await spawnVossServe(await createTempCwd());
    const client = createVossClient(fixture.baseUrl, "not-the-token");

    await expectVossStatus(client.createSession(), 401);
  });

  it("surfaces concurrent messages during a turn as VossApiError 409", async () => {
    fixture = await spawnVossServe(await createTempCwd());
    const client = createVossClient(fixture.baseUrl, fixture.token);
    const sessionId = await client.createSession();

    const attempts = await Promise.allSettled(
      Array.from({ length: 24 }, (_, index) => client.postMessage(sessionId, `busy ${index}`)),
    );

    expect(attempts.some((attempt) => attempt.status === "fulfilled")).toBe(true);
    expect(
      attempts.some(
        (attempt) => attempt.status === "rejected" && attempt.reason instanceof VossApiError && attempt.reason.status === 409,
      ),
    ).toBe(true);
  });
});

async function expectVossStatus(promise: Promise<unknown>, status: number): Promise<void> {
  try {
    await promise;
  } catch (error) {
    expect(error).toBeInstanceOf(VossApiError);
    expect((error as VossApiError).status).toBe(status);
    return;
  }

  throw new Error(`expected VossApiError ${status}`);
}
