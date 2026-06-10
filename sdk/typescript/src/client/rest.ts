import createClient, { type Client, type Middleware } from "openapi-fetch";

import { VossApiError } from "../errors";
import type { components, operations, paths } from "../generated/types";

type JsonObject = Record<string, unknown>;
type JsonResponse<
  OperationName extends keyof operations,
  Status extends keyof operations[OperationName]["responses"],
> = operations[OperationName]["responses"][Status] extends {
  content: { "application/json": infer Body };
}
  ? Body
  : never;

type CreateSessionBody = components["schemas"]["CreateSessionBody"];
type MessageBody = components["schemas"]["MessageBody"];

export type VossOpenApiClient = Client<paths>;
export type CreateSessionResponse = JsonResponse<"create_session_session_post", 201>;
export type SessionInfo = JsonObject;
export type SavedSession = JsonObject;
export type AcceptedResponse = JsonResponse<"post_message_session__session_id__message_post", 202>;
export type CostInfo = JsonResponse<"cost_session__session_id__cost_get", 200>;
export type DoctorReport = JsonResponse<"doctor_doctor_get", 200>;

type ClientResult<T> =
  | {
      data: T;
      error?: never;
      response: Response;
    }
  | {
      data?: never;
      error: unknown;
      response: Response;
    };

type CwdQueryInit = { params: { query: { cwd: string } } } | undefined;

export function createVossClient(baseUrl: string, token: string) {
  const client = createClient<paths>({ baseUrl });

  client.use(createAuthAndErrorMiddleware(token));

  return {
    client,

    async createSession(cwd?: string): Promise<string> {
      const body: CreateSessionBody = {
        auth: "auto",
        ...(cwd === undefined ? {} : { cwd }),
      };
      const result = await client.POST("/session", { body });
      const data = await unwrapResult<CreateSessionResponse>(result);

      if (isRecord(data) && typeof data.id === "string") {
        return data.id;
      }

      throw decodeError(result.response, "expected createSession response to include string id");
    },

    async listSessions(): Promise<SessionInfo[]> {
      const result = await client.GET("/session");
      const data = await unwrapResult<unknown>(result);
      // The server wraps the list in a `{v, sessions: [...]}` envelope
      // (harness/server/app.py list_sessions); accept a bare array too.
      return expectSessionsArray<SessionInfo>(data, result.response, "expected listSessions response to be an array");
    },

    async listSaved(cwd?: string): Promise<SavedSession[]> {
      const result = await client.GET("/sessions/saved", cwdQueryInit(cwd));
      const data = await unwrapResult<unknown>(result);
      // Same `{v, sessions: [...]}` envelope as listSessions.
      return expectSessionsArray<SavedSession>(data, result.response, "expected listSaved response to be an array");
    },

    async getSession(sessionId: string): Promise<SessionInfo> {
      const result = await client.GET("/session/{session_id}", {
        params: { path: { session_id: sessionId } },
      });
      const data = await unwrapResult<unknown>(result);

      if (isRecord(data)) {
        return data;
      }

      throw decodeError(result.response, "expected getSession response to be an object");
    },

    async deleteSession(sessionId: string): Promise<void> {
      const result = await client.DELETE("/session/{session_id}", {
        params: { path: { session_id: sessionId } },
        parseAs: "text",
      });
      await unwrapResult<unknown>(result);
    },

    async postMessage(sessionId: string, text: string, mode = "plan"): Promise<AcceptedResponse> {
      const body: MessageBody = {
        mode,
        parts: [{ type: "text", text }],
      };
      const result = await client.POST("/session/{session_id}/message", {
        params: { path: { session_id: sessionId } },
        body,
      });
      return unwrapResult<AcceptedResponse>(result);
    },

    async abort(sessionId: string): Promise<void> {
      const result = await client.POST("/session/{session_id}/abort", {
        params: { path: { session_id: sessionId } },
      });
      await unwrapResult<unknown>(result);
    },

    async getCost(sessionId: string): Promise<CostInfo> {
      const result = await client.GET("/session/{session_id}/cost", {
        params: { path: { session_id: sessionId } },
      });
      return unwrapResult<CostInfo>(result);
    },

    async doctor(cwd?: string): Promise<DoctorReport> {
      const result = await client.GET("/doctor", cwdQueryInit(cwd));
      return unwrapResult<DoctorReport>(result);
    },
  };
}

export type VossClient = ReturnType<typeof createVossClient>;

function createAuthAndErrorMiddleware(token: string): Middleware {
  return {
    onRequest({ request }) {
      request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
    async onResponse({ response }) {
      if (!response.ok) {
        throw new VossApiError(response.status, await parseErrorDetail(response));
      }

      return response;
    },
  };
}

async function unwrapResult<T>(result: ClientResult<T>): Promise<T> {
  if ("error" in result && result.error !== undefined) {
    throw await toVossApiError(result.response, result.error);
  }

  return result.data as T;
}

async function toVossApiError(response: Response, error: unknown): Promise<VossApiError> {
  if (error instanceof VossApiError) {
    return error;
  }

  return new VossApiError(response.status, detailFromValue(error) ?? (await parseErrorDetail(response)));
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
    return detailFromValue(JSON.parse(body)) ?? fallback;
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

function expectArray<T>(value: unknown, response: Response, message: string): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  throw decodeError(response, message);
}

/** Accept either a bare array or the server's `{v, sessions: [...]}` envelope. */
function expectSessionsArray<T>(value: unknown, response: Response, message: string): T[] {
  if (isRecord(value) && Array.isArray(value.sessions)) {
    return value.sessions as T[];
  }

  return expectArray<T>(value, response, message);
}

function decodeError(response: Response, detail: string): VossApiError {
  return new VossApiError(response.status, `Decode error: ${detail}`);
}

function cwdQueryInit(cwd?: string): CwdQueryInit {
  return cwd === undefined ? undefined : { params: { query: { cwd } } };
}

function isRecord(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
