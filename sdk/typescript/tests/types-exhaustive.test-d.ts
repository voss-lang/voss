import type { components } from "../src/generated/types";

type AgentEvent = components["schemas"]["EventEnvelope"]["event"];

function assertExhaustiveAgentEvent(event: AgentEvent): AgentEvent {
  switch (event.type) {
    case "server.connected":
      return event;
    case "session.idle":
      return event;
    case "permission.updated":
      return event;
    case "banner":
      return event;
    case "user":
      return event;
    case "thinking":
      return event;
    case "plan":
      return event;
    case "tool":
      return event;
    case "clarify":
      return event;
    case "final":
      return event;
    case "stream.delta":
      return event;
    case "stream.finalize":
      return event;
    case "status":
      return event;
    case "cognition_loaded":
      return event;
    case "cognition_overflow":
      return event;
    case "principles_overflow":
      return event;
    case "warning":
      return event;
    case "probable":
      return event;
    case "budget.updated":
      return event;
    case "confidence.updated":
      return event;
    case "gate.updated":
      return event;
    default: {
      const _exhaustive: never = event;
      return _exhaustive;
    }
  }
}
