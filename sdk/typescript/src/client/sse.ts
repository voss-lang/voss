import { EventSourceParserStream } from "eventsource-parser/stream";

import { VossApiError } from "../errors";
import type { components } from "../generated/types";

export type AgentEvent = components["schemas"]["EventEnvelope"]["event"];

type SseMessage = {
  data: string;
};

export async function* subscribeToEvents(
  baseUrl: string,
  sessionId: string,
  token: string,
  signal?: AbortSignal,
): AsyncIterable<AgentEvent> {
  try {
    const response = await fetch(buildEventsUrl(baseUrl, sessionId), {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });

    if (!response.ok) {
      throw new VossApiError(response.status, await parseErrorDetail(response));
    }

    if (response.body === null) {
      throw new VossApiError(response.status, "SSE response body is empty");
    }

    const stream = response.body
      .pipeThrough(new TextDecoderStream())
      .pipeThrough(new EventSourceParserStream());
    const reader = stream.getReader();

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          return;
        }

        const data = (value as SseMessage).data;
        if (data.length === 0) {
          continue;
        }

        yield JSON.parse(data) as AgentEvent;
      }
    } finally {
      reader.releaseLock();
      await stream.cancel().catch((error: unknown) => {
        if (!isAbortError(error, signal)) {
          throw error;
        }
      });
    }
  } catch (error) {
    if (isAbortError(error, signal)) {
      return;
    }

    throw error;
  }
}

function buildEventsUrl(baseUrl: string, sessionId: string): string {
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  return new URL(`session/${encodeURIComponent(sessionId)}/events`, normalizedBaseUrl).toString();
}

async function parseErrorDetail(response: Response): Promise<string> {
  const fallback = response.statusText || `HTTP ${response.status}`;
  const body = await response
    .clone()
    .text()
    .catch(() => "");

  if (body.length === 0) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(body) as unknown;
    return detailFromValue(parsed) ?? fallback;
  } catch {
    return body;
  }
}

function detailFromValue(value: unknown): string | undefined {
  if (typeof value === "string" && value.length > 0) {
    return value;
  }

  if (isRecord(value) && "detail" in value) {
    return stringifyDetail(value.detail);
  }

  return undefined;
}

function stringifyDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") {
    return detail;
  }

  if (detail === undefined || detail === null) {
    return undefined;
  }

  try {
    return JSON.stringify(detail);
  } catch {
    return String(detail);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isAbortError(error: unknown, signal?: AbortSignal): boolean {
  return signal?.aborted === true || (error instanceof DOMException && error.name === "AbortError");
}
