import { VossApiError } from "../errors";
import type { VossClient } from "./rest";

export type PermissionChoice = "a" | "A" | "d" | "y" | "n";

export type PermissionReplyArgs = {
  id: string;
  choice: PermissionChoice;
};

export async function replyPermission(
  client: VossClient,
  sessionId: string,
  args: PermissionReplyArgs,
): Promise<void> {
  const body = {
    v: 1,
    id: args.id,
    choice: args.choice,
  } satisfies { v: 1; id: string; choice: PermissionChoice };

  const result = await client.client.POST("/session/{session_id}/permission", {
    params: { path: { session_id: sessionId } },
    body,
  });

  if ("error" in result && result.error !== undefined) {
    throw new VossApiError(result.response.status, detailFromError(result.error));
  }
}

function detailFromError(error: unknown): string {
  if (typeof error === "string" && error.length > 0) {
    return error;
  }

  if (isRecord(error) && "detail" in error) {
    return stringifyDetail(error.detail);
  }

  return "Permission reply failed";
}

function stringifyDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (detail === undefined || detail === null) {
    return "Permission reply failed";
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
