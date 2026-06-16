// VADE2-11 — typed client for the loopback server's GET /memory route.
//
// Read-only view of the harness memory store for a workspace. The bearer token is
// the sole auth for the loopback server and must never be logged or stringified
// (T-V15-10) — it rides the Authorization header only.

export interface MemoryHit {
  source: string;
  locator: string;
  score: number;
  excerpt: string;
  session_id: string | null;
  ts: string | null;
  line_start: number | null;
  line_end: number | null;
}

export interface MemoryResponse {
  v: number;
  summary: string;
  query: string | null;
  hits: MemoryHit[];
}

/**
 * Fetch the memory summary (and recall hits when `q` is given) from the
 * `voss serve` sidecar at `baseUrl`. Throws on a non-OK response.
 */
export async function fetchMemory(
  baseUrl: string,
  token: string,
  cwd: string,
  q?: string,
  topK = 5,
): Promise<MemoryResponse> {
  const params = new URLSearchParams({ cwd });
  if (q && q.trim()) {
    params.set('q', q.trim());
    params.set('top_k', String(topK));
  }
  const res = await fetch(`${baseUrl}/memory?${params.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`GET /memory failed: ${res.status}`);
  }
  return (await res.json()) as MemoryResponse;
}
