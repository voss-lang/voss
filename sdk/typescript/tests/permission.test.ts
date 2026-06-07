import { afterEach, describe, expect, it } from "vitest";

import { createVossClient, type VossClient } from "../src/client/rest";
import { type PermissionChoice, replyPermission } from "../src/client/permission";
import { createTempCwd, spawnVossServe, type ServeFixture } from "./helpers/serve-fixture";

let fixture: ServeFixture | undefined;

afterEach(async () => {
  await fixture?.teardown();
  fixture = undefined;
});

describe("permission integration", () => {
  it("posts permission replies to the real endpoint and receives stale for an unknown request", async () => {
    fixture = await spawnVossServe(await createTempCwd());
    const client = createVossClient(fixture.baseUrl, fixture.token);
    const sessionId = await client.createSession();
    const choices = ["a", "A", "d", "y", "n"] satisfies PermissionChoice[];

    for (const choice of choices) {
      const result = await client.client.POST("/session/{session_id}/permission", {
        params: { path: { session_id: sessionId } },
        body: { v: 1, id: `missing-${choice}`, choice },
      });

      expect(result.response.status).toBe(200);
      expect(result.data).toMatchObject({ v: 1, status: "stale" });
    }
  });

  it("replyPermission posts the protocol permission body", async () => {
    const bodies: unknown[] = [];
    const client = {
      client: {
        POST: async (_path: string, init: { body?: unknown }) => {
          bodies.push(init.body);
          return { response: new Response(null, { status: 200 }) };
        },
      },
    } as unknown as VossClient;

    await replyPermission(client, "session-1", { id: "permission-1", choice: "a" });

    expect(bodies).toEqual([{ v: 1, id: "permission-1", choice: "a" }]);
  });
});
