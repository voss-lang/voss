# Native / C Embedding Reference

**Audience:** native and C/C++ embedders — CI bots, devops daemons, language runtimes, and FFI shims that want to drive a local Voss harness without a managed-language SDK.

**Status:** This document is the V13.4 deliverable. It ships **zero code**. The native "ABI" today **is** the JSON-over-loopback protocol defined in [`.planning/PROTOCOL.md`](../.planning/PROTOCOL.md) (wire version `v1`). There is no C struct ABI, no shared library, no header. A native embedder builds directly against the JSON contract described and pointed at below.

> **One-line summary:** spawn or attach `voss serve`, read its one-line `{v,port,token}` handshake from stdout, then speak JSON over loopback HTTP — REST for commands, SSE for the server→client event stream — sending `Authorization: Bearer <token>` on every request.

---

## 1. Consumption model (VSDK-C-01)

A native embedder integrates Voss as a **local subprocess speaking JSON over loopback**:

1. **Spawn or attach.** Launch `voss serve` (it binds an ephemeral port) or attach to one already running. The harness binds `127.0.0.1:0` — **loopback only**, never a routable interface, and there is **no TLS on loopback**.
2. **Read the handshake.** `voss serve` prints exactly **one line of JSON to stdout** and nothing else before it:
   ```
   {"v":1,"port":54123,"token":"<url-safe-32-byte-token>"}
   ```
   Parse that single line to learn the `port` and the `token`. The base URL is `http://127.0.0.1:<port>`.
3. **Authenticate every request.** Send `Authorization: Bearer <token>` on **every** request — every REST call **and** the SSE `GET`. A missing or wrong token is rejected at middleware with `401` (constant-time compare); it never reaches route logic.
4. **Send commands over REST.** `Content-Type: application/json`; request and response bodies are JSON. One running turn per session — posting a message while a turn is in flight returns `409`.
5. **Consume events over SSE.** `GET /session/:id/events` returns `text/event-stream`; the server streams typed JSON events server→client. The first event is always `server.connected`; a turn finishes with `session.idle`. Disconnecting the SSE stream cancels the in-flight turn (no separate abort needed).

There is **no C struct ABI**. The transport (loopback REST + SSE) and the auth (Bearer token from the handshake line) above are the entire integration surface a native embedder must implement.

### Token handling (security)

- The token is **ephemeral and per-server-process** — generated at startup, **never persisted** to disk.
- **Never log the token** and never place it in a URL query string; carry it only in the `Authorization` header.
- Because the bind is loopback-only, do **not** reconfigure the server to listen on a routable interface — that would expose an unauthenticated-by-network surface guarded only by the bearer token.

---

## 2. Contract source of truth (VSDK-C-02)

This document **points at** the authoritative contract; it does **not** inline or fork it. The single sources of truth are:

| Path | Role |
|------|------|
| [`.planning/PROTOCOL.md`](../.planning/PROTOCOL.md) | The `v1` wire contract — transport, auth, endpoints, event model, error model. The native ABI. |
| [`contracts/openapi.json`](../contracts/openapi.json) | The committed OpenAPI 3.1 snapshot of the REST surface (request/response shapes, status codes). |
| [`contracts/events.schema.json`](../contracts/events.schema.json) | The committed JSON-Schema snapshot of the SSE event union — **the authoritative event-union member source** (see §3). |

Cross-links:

- [`docs/sdk.md`](./sdk.md) — the SDK strategy / surface overview.
- [`docs/ORCHESTRATION_LAYERS.md`](./ORCHESTRATION_LAYERS.md) — the V13 tier taxonomy + SDK Surface Matrix used by §4. (Pending: produced by V13. The current design source is [`.planning/docs/ORCHESTRATION_LAYERS.md`](../.planning/docs/ORCHESTRATION_LAYERS.md) until V13 ships the published copy.)

> **Soft-dependency note.** `contracts/openapi.json` and `contracts/events.schema.json` are V13.1 deliverables and `docs/ORCHESTRATION_LAYERS.md` is a V13 deliverable. As of this writing the `contracts/*.json` snapshots are committed and present; `docs/ORCHESTRATION_LAYERS.md` is still pending. The references-resolve gate [`docs/check-native-embedding-refs.sh`](./check-native-embedding-refs.sh) enumerates every cited path: it hard-fails on a missing always-present path (`PROTOCOL.md`, `sdk.md`) and warn-skips (exit 0) while any upstream-gated path is absent.

This document never inlines a JSON-Schema body — no schema-keyword blocks, no field-definition blocks. Read the shapes from the contract files above; read this document for the *consumption model*.

---

## 3. JSON → native reading reference (VSDK-C-03)

A native embedder parses JSON into its own structures. The contract files carry the exact shapes; this table gives the reading rules.

### Protocol invariants

| Field | Meaning | Native handling |
|-------|---------|-----------------|
| `v` | Protocol version, present on **every** REST body and **every** SSE `data` payload. Currently `"v": 1`. | Read and check it. A future breaking change bumps `v` and ships a migration note (see §4). Treat an unexpected `v` as "newer protocol — re-check the contract." |
| `type` | The **discriminator** for the SSE event union. It is **both** the SSE `event:` name **and** the serde tag inside the `data` JSON. | Read `type` first, then parse the matching payload shape. |

### Discriminated event union

The SSE event union is a discriminated union keyed on `` `type` ``. The wire framing per event is:

```
event: <type>
data: {"v":1,"type":"<type>", ...}
id: <seq>
```

To decode in native code: read the `data` JSON, read its `` `type` `` string (the discriminator), then interpret the remaining fields per the member shape for that `` `type` ``.

> **The member set is authoritative-from-schema.** Do **not** hardcode a frozen list of event types as your contract. Enumerate the members from [`contracts/events.schema.json`](../contracts/events.schema.json) (the discriminated-union members and their fields). `.planning/PROTOCOL.md` §6 lists them for orientation, but `events.schema.json` is the source you generate or validate against. Two members always anchor a turn: `server.connected` (first) and `session.idle` (turn complete).

### JSON scalar/composite → native reading

| JSON type | Native reading guidance |
|-----------|-------------------------|
| string | UTF-8 text; copy into your string type. |
| number | May be integer or floating-point — read as double unless the field is documented integral (e.g. a sequence/count). |
| boolean | Map to your native bool. |
| object | A nested record; recurse using the member shape from the schema. |
| array | A homogeneous list; iterate. |
| null / absent | A field may be **optional**: absent or `null`. Treat "absent" and "null" as "not provided" and supply your own default; do not assume every documented field is present on every payload. Required fields are always present. |

REST errors are an HTTP status plus a JSON body `{"v":1,"detail":"<message>"}` — read `detail` for the human-readable reason.

---

## 4. Stability statement (VSDK-C-04)

The JSON wire contract is **stable as `.planning/PROTOCOL.md` v1**. The version-bump policy is the PROTOCOL header policy: a **breaking** change increments `v` and ships a migration note; additive, backward-compatible fields do not bump `v`.

Mapping to the V13 stability tiers (defined in [`docs/ORCHESTRATION_LAYERS.md`](./ORCHESTRATION_LAYERS.md)), using the five tier names verbatim — **stable-now**, **experimental**, **generated-from-protocol**, **private-internal**, **deferred**:

| Surface | Tier |
|---------|------|
| The JSON-over-loopback protocol an embedder consumes (REST shapes, event union) | **generated-from-protocol** — derived from the committed `contracts/` snapshot; it tracks PROTOCOL.md v1 and is regenerated, not hand-forked. |
| The locked `v1` wire contract itself (transport, auth, error model) | **stable-now** — changes only via a `v` bump + migration note. |
| C headers / FFI ergonomics | **deferred** (see §5). |

A native embedder should code against the **generated-from-protocol** surface (the `contracts/` snapshot) and rely on the `v` field + the PROTOCOL version-bump policy for forward compatibility.

---

## 5. Deferred: C headers, cbindgen, FFI/cgo (VSDK-C-05)

The following are **deliberately not built** and are marked **deferred** — a complete, acceptable end-state, not unfinished work:

- **C headers** (`.h`) describing structs/functions for the protocol.
- **`cbindgen`** (or any header-generation tool) configuration and output.
- An **FFI / cgo** shim or any `extern "C"` / `#[no_mangle]` boundary.
- High-level C ergonomics (a convenience C client library).

**Why deferred:** the native ABI today is the JSON-over-loopback protocol, and a native embedder can consume it directly with any HTTP + SSE + JSON capability. C-struct headers and an FFI shim add maintenance and a memory-safety boundary with no current consumer to justify them.

**Activation trigger:** build these **only when a concrete native embedder with a real integration need appears** — i.e. a specific native/C consumer that cannot reasonably speak JSON-over-loopback and requires a struct-level ABI. Until that trigger, native embedders integrate against the JSON contract in §§1–3 directly.

---

## See also

- [`.planning/PROTOCOL.md`](../.planning/PROTOCOL.md) — the authoritative `v1` wire contract.
- [`contracts/openapi.json`](../contracts/openapi.json), [`contracts/events.schema.json`](../contracts/events.schema.json) — committed contract snapshots.
- [`docs/sdk.md`](./sdk.md) — SDK strategy.
- [`docs/ORCHESTRATION_LAYERS.md`](./ORCHESTRATION_LAYERS.md) — stability-tier taxonomy (pending V13).
- [`docs/check-native-embedding-refs.sh`](./check-native-embedding-refs.sh) — references-resolve gate for this document.
