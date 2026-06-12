// E4 TS consumer subprogram: public-API-only (@vosslang/sdk index surface).
// The Python eval runner owns the serve lifecycle and passes coordinates via
// env — never the node launcher (10s handshake timeout vs 15-45s cold litellm).
import { createVossClient, subscribeToEvents, replyPermission } from "@vosslang/sdk";

const baseUrl = process.env.VOSS_BASE_URL;
if (!baseUrl) {
  console.error("VOSS_BASE_URL required");
  process.exit(2);
}
const token = process.env.VOSS_TOKEN ?? "";
const cwd = process.env.VOSS_CWD || ".";
const prompt = process.env.VOSS_PROMPT ?? "";
const mode = process.env.VOSS_MODE || "plan";

const client = createVossClient(baseUrl, token);
const sessionId = await client.createSession(cwd);

let finalText = "";
let sawPermissionGate = false;
const eventTypesSeen = [];
const ac = new AbortController();

await client.postMessage(sessionId, prompt, mode);

for await (const event of subscribeToEvents(baseUrl, sessionId, token, ac.signal)) {
  eventTypesSeen.push(event.type);
  if (event.type === "permission.updated") {
    sawPermissionGate = true;
    await replyPermission(client, sessionId, { id: event.id, choice: "a" });
  }
  if (event.type === "final") {
    finalText = event.text;
  }
  if (event.type === "session.idle") {
    ac.abort();
    break;
  }
}

const cost = await client.getCost(sessionId).catch(() => ({ total_usd: 0 }));
process.stdout.write(
  JSON.stringify({
    surface: "sdk:ts",
    session_id: sessionId,
    final: finalText,
    saw_permission_gate: sawPermissionGate,
    cost_usd: cost.total_usd,
    event_types_seen: eventTypesSeen,
  }) + "\n",
);
