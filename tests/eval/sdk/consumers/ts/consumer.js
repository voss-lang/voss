// E4 TS consumer subprogram: public-API-only (@vosslang/sdk index surface).
// The Python eval runner owns the serve lifecycle and passes coordinates via
// env — never the node launcher (10s handshake timeout vs 15-45s cold litellm).
// No per-runtime scoring: emits one structured-JSON line; the runner scores
// via the single E1 substrate.
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
// Plan 07 drives Deny through this same file with VOSS_PERMISSION_CHOICE=d.
const choice = process.env.VOSS_PERMISSION_CHOICE || "a";

const client = createVossClient(baseUrl, token);

let sessionId = "";
let finalText = "";
let sawPermissionGate = false;
const eventTypesSeen = [];
const ac = new AbortController();

try {
  sessionId = await client.createSession(cwd);
  await client.postMessage(sessionId, prompt, mode);

  for await (const event of subscribeToEvents(baseUrl, sessionId, token, ac.signal)) {
    eventTypesSeen.push(event.type);
    if (event.type === "permission.updated") {
      sawPermissionGate = true;
      await replyPermission(client, sessionId, { id: event.id, choice });
    }
    if (event.type === "final") {
      finalText = event.text;
    }
    if (event.type === "session.idle") {
      ac.abort();
      break;
    }
  }
} catch (error) {
  if (!(error instanceof DOMException && error.name === "AbortError")) {
    // Still emit the JSON below with whatever was captured — the runner
    // needs a parseable line, not a crash.
    console.error(`consumer error: ${error}`);
  }
}

const cost = await client.getCost(sessionId).catch(() => ({ total_usd: 0 }));
process.stdout.write(
  JSON.stringify({
    surface: "sdk:ts",
    session_id: sessionId,
    final: finalText,
    saw_permission_gate: sawPermissionGate,
    cost_usd: cost.total_usd ?? 0,
    event_types_seen: eventTypesSeen,
  }) + "\n",
);
