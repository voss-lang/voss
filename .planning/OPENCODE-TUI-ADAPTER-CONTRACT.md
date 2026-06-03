# OpenCode TUI Fork — Feasibility Gate + Adapter Contract

**Created:** 2026-06-03
**Fork target:** anomalyco/opencode @ **v1.15.13** (tag `385cb69`)
**Plan origin:** memory `voss-opencode-tui-fork` (Option F). Keep OpenCode's SolidJS/OpenTUI TUI; replace the SDK boundary so it drives Voss's existing Python server (`voss serve`) unmodified.
**Method:** static map of the real cloned fork (`/tmp/opencode-fork`) + live build smoke on this machine (darwin arm64) + 5-agent reverse-engineering workflow cross-checked against `voss/harness/server/{events.py,app.py}` and `PROTOCOL.md`.

---

## 0. FEASIBILITY GATE — BUILD SIDE: ✅ PASS

| Check | Result |
|---|---|
| Clone v1.15.13 | ✅ shallow clone, 151M, HEAD `385cb69` |
| **zig requirement (predicted blocker)** | ✅ **DEAD.** `@opentui/core@0.2.16` ships prebuilt per-platform native libs as optionalDependencies (`@opentui/core-darwin-arm64` → `libopentui.dylib`, 1.6MB). esbuild/swc pattern. No zig at any point. |
| `bun install` (full monorepo, user-authorized) | ✅ 4718 pkgs, 53s, exit 0. postinstall (`fix-node-pty`, `husky`) clean. |
| CLI dependency graph loads + runs | ✅ `bun run … src/index.ts --version` → `local`, exits 0 |
| OpenTUI native lib loads under bun | ✅ `@opentui/core` imports, exports resolve |
| TUI app module graph (SolidJS+OpenTUI) imports | ✅ `import tui/app.tsx` → `createTuiRenderer, tui, tuiRendererConfig` |
| Live interactive render | ⚠️ **un-verifiable headless** — OpenTUI needs a real TTY. Environmental limit, NOT a fork blocker (same class as the Tauri-WebDriver-on-macOS limit). |

**Toolchain (this machine):** bun 1.3.6, node 22.22.2, pnpm 10, gh 2.87.3 — all present. zig still missing and **confirmed irrelevant**.

---

## 1. VERDICT: 🟡 YELLOW (heavy end)

The **plumbing is GREEN** — `fetch`, `headers`, and `events` are real prop-injection seams on `TuiInput` (`app.tsx:164-174`) forwarded unconditionally into `SDKProvider` (`app.tsx:249-255 → sdk.tsx:24-32, 111-124`). Transport / auth / event-source all swap with **zero edits to the TUI render/transport core**.

But the adapter is **not a thin shim.** Voss's wire protocol is structurally *further* from v2 than the handoff assumed:
- Voss emits **~20 flat, snake_case, correlation-free events** (`events.py`) — **no** `messageID`/`partID`/`callID`, **no** `message.part.updated`/`message.updated`/`session.status` envelopes.
- Voss SSE is **per-session** (`GET /session/{id}/events`), **not** a global `/global/event` stream.
- Voss exposes **none** of the 6 boot GETs the TUI hard-requires.

So the adapter must (a) **fully synthesize the boot REST layer** in-process, and (b) run a **stateful event-assembly machine** that mints stable IDs, re-segments `stream.delta` into `Part` snapshots, drives tool lifecycle, and synthesizes `session.status` + terminal `message.updated`. That statefulness is **M-to-L**, the core engineering risk.

> **Two handoff corrections (verified against source):**
> 1. Voss does **not** emit `message.part.updated`-shaped events — it's flat snake_case with `session_id` and zero correlation IDs → assembly machine mandatory.
> 2. Voss SSE is **per-session**, not global → custom `EventSource` opens one stream per active session.

---

## 2. BOOT STUB TABLE

The TUI's 6 blocking GETs gate `status: loading→partial`; any error → `exit(e)` (`sync.tsx:474`). Voss exposes none (`app.py` = `/session*`, `/doctor`, `/openapi.json` only). All 6 → **stub-in-process** inside custom `fetch`. The 3 `.data!`-unwrapped ones must return real shapes or SolidJS `reconcile` crashes *after* the gate.

| sdk method | HTTP | Decision | Minimal stub | Voss source |
|---|---|---|---|---|
| `path.get` | `GET /path` | **stub** | `{home:"",state:"",config:"",worktree:"<cwd>",directory:"<cwd>"}` | synth from cwd |
| `project.current` | `GET /project/current` | **stub** | `{id:"voss",worktree:"<cwd>",time:{created:0,updated:0},sandboxes:[]}` | synth |
| `config.providers` | `GET /config/providers` | **stub** `.data!` | `{providers:[<1 Provider>],default:{}}` — not null | synth |
| `provider.list` | `GET /provider` | **stub** `.data!` | `{all:[<1 Provider>],default:{},connected:["voss"]}` — non-empty `connected` suppresses onboarding dialog (`app.tsx:542-551`) | synth |
| `app.agents` | `GET /agent` | **stub** | `[]` (later: map `.voss/agents/*.md`) | partial |
| `config.get` | `GET /config` | **stub** | `{}` (all optional) | synth |
| `global.event` (SSE) | `GET /global/event` | **replaced** | inject custom `EventSource` instead (§5) | Voss uses `/session/{id}/events` |
| `session.list` | `GET /session` | **proxy** | map `[SessionInfo]→Session[]` | ✅ `app.py:313` |
| `session.get` | `GET /session/{id}` | **proxy** | map `SessionInfo→Session` | ✅ `app.py:342` |
| `command/lsp/mcp/formatter/session.status/provider.auth/vcs/experimental.*` | various | **stub-noop** | `[]`/`{}`/`null` | none |

**Most tedious stub (write-once, static):** the `Provider` for `config.providers`/`provider.list` needs ≥1 `Model` with full nested `cost{input,output,cache{read,write}}`, `limit{context,output}`, `capabilities{}`, `release_date`. Voss tracks no per-model pricing → **hardcode one synthetic `Model` per provider.**

---

## 3. EVENT TRANSLATION TABLE (the crux)

Fork's live route = the v1-shaped `sync.tsx` family (`message.updated` / `message.part.updated` / `message.part.delta` / `session.status`). **Every emitted envelope must carry `{directory:"global", payload:{...}}`** or `event.ts:19` **silently drops it** (Voss has no project id → use `"global"`).

### Direct-ish mappings
| Voss event (snake_case) | → v2 payload | Synthesis required |
|---|---|---|
| `server.connected` | `server.connected` | direct |
| `user {task}` | `message.updated {info:UserMessage}` | mint `messageID`; fill `agent`,`model{providerID,modelID}`,`time.created` |
| `stream.delta {text}` | seed `message.part.updated`(TextPart) once → then `message.part.delta {messageID,partID,field:"text",delta}` | **delta dropped if part not seeded** (`sync.tsx:329`) |
| `tool {name,args,summary,state}` | `message.part.updated {part:ToolPart}` | mint stable `callID`+`partID`; state ok→completed/error→error/pending→pending/running→running; synth `output`,`title`,`metadata`,`time` |
| `plan {confidence,steps,cost_usd}` | TextPart **or** custom render | no v2 `plan` part |
| `thinking {label}` | `message.part.updated`(ReasoningPart) | `ReasoningPart.time` required |
| `clarify {question,confidence}` | `question.asked` **or** text | only if question modal wired |
| `final {text,confidence,cost_usd}` | terminal `message.updated`(AssistantMessage `time.completed`,`finish:"stop"`,`cost`,`tokens`) + final TextPart | **turn-done #1** |
| `stream.finalize` | folds into terminal `message.updated` | stamps `time.completed` |
| `session.idle {session_id}` | `session.status {sessionID,status:{type:"idle"}}` | **turn-done #2** — emit `session.status`, NOT v2 `session.idle` (nothing subscribes to it) |
| `permission.updated {id,tool_name,args,dimension}` | `permission.asked {PermissionRequest}` | `id→requestID`; reply via `POST /permission` |
| `warning {message}` | `tui.toast.show {message,variant:"warning"}` | direct-ish |
| `status {model,tokens,cost_usd,ctx_pct}` | fold into AssistantMessage.tokens | footer |

### Gap (a) — Voss events with NO v2 home → custom rendering (§6)
`probable`, `budget.updated`, `confidence.updated`, `gate.updated`, `cognition_loaded`, `cognition_overflow`.

### Gap (b) — v2 events Voss NEVER emits → adapter must SYNTHESIZE
1. **`session.status {type:"busy"}`** on `POST /message` 202 (Voss has no turn-start event) → without it, prompt box / abort keybind / spinner never arm.
2. **`message.updated` with `AssistantMessage.time.completed` + `finish`** — re-emit whole assistant msg or in-message spinner never stops (`index.tsx:212`).
3. **Stable `messageID`/`partID`/`callID`** — store binary-searches by id; unstable id ⇒ duplicate rows. Monotonic, lexicographically-sortable.
4. **`AssistantMessage.cost`/`tokens`/`path`/`parentID`/`mode`/`agent`** — non-optional; fill from `final`/`status`, rest zeros/empties.

### Turn hot-path (deliverable center)
```
Voss POST /message → 202        ⇒ session.status {busy}
                                 ⇒ message.updated {AssistantMessage id=A, time.created, NO completed}
stream.delta {text:"He"}        ⇒ (first) message.part.updated {TextPart id=A.t0, messageID=A, text:"He"}
stream.delta {text:"llo"}       ⇒ message.part.delta {messageID:A, partID:A.t0, field:"text", delta:"llo"}
tool {bash, pending}            ⇒ message.part.updated {ToolPart id=A.c0, callID=c0, state:{status:"pending",input,raw:""}}
tool {bash, running}            ⇒ message.part.updated {ToolPart id=A.c0, state:{status:"running",input,time:{start}}}
tool {bash, ok}                 ⇒ message.part.updated {ToolPart id=A.c0, state:{status:"completed",input,output:summary,title,metadata,time:{start,end}}}
final {text,confidence,cost}    ⇒ message.part.updated {final TextPart} + message.updated {AssistantMessage id=A, time.completed, finish:"stop", cost, tokens}
session.idle {session_id}       ⇒ session.status {idle}
```
**Correlation invariant:** deltas between two tool/final boundaries belong to the current TextPart; new TextPart only after an interleaving tool. Voss gives no boundaries → **adapter defines them.** Tool identity keyed `(name, turn-counter)` — same `callID` re-sent across pending→running→ok.

**Path B (`session.next.*`) is DEAD WEIGHT** — only feeds a hidden debug pane (`session-v2.tsx`). Do **not** emit any `session.next.*`. Deletes ~24 mappings the handoff implied.

---

## 4. REST TRANSLATION (~40 sdk.client.* methods)

**Session-critical (7 real proxies + 5 stubs):** `session.create`→`POST /session`; `session.list`→`GET /session`; `session.get`→`GET /session/{id}`; `session.delete`→`DELETE /session/{id}`; `session.prompt/message`→`POST /session/{id}/message` (also triggers synth `session.status:busy`); `session.abort`→`POST /session/{id}/abort`; `permission.reply`→`POST /session/{id}/permission` (map choice a/A/d). Stubs: `session.messages`/`session.todo`/`session.diff`/`v2.session.messages` (Voss has no history GET — rely on live SSE).

**Boot (§2):** 6 stub + `session.list` proxy.

**Optional (stub-noop / unsupported):** `command/lsp/mcp/formatter/session.status/provider.auth/vcs/experimental.*` (Phase-C degrade); `find.files/find.symbol/app.skills` (dialogs); `pty/workspace/installation/account/models.*` (no Voss analog).

> Of ~40 methods: **7 real proxies**, rest stub/noop.

---

## 5. SEAM PLAN — zero edits to render/transport core

| Change | File | Type |
|---|---|---|
| New yargs cmd `voss.ts` (~30 lines, mirrors `attach.ts:84-98`): build headers/fetch/events, `createTuiRenderer(config)`, `tui({url,config,renderer,args,directory,fetch,events})`, `await handle.done` | new `tui/voss.ts` | additive |
| Register cmd | `src/index.ts` (by `AttachCommand`, ~line 161) | 1-line edit |
| Custom `fetch` (REST stub+proxy, §2/§4) | new `tui/voss/fetch.ts` | new module |
| Custom `EventSource` (`{subscribe}`, `sdk.tsx:8-10`) wrapping Voss `/session/{id}/events` + assembly machine (§3) | new `tui/voss/events.ts` | **new module — bulk of work** |
| Auth: `headers:{Authorization:"Bearer <token>"}` from handshake line; do NOT call `ServerAuth.headers` | in `voss.ts` | prop value |
| Voss-part components | `routes/session/index.tsx:1521` `PART_MAPPING` + new components | internal edit (§6) |

**Injection points (verified):** fetch → `sdk.tsx:29`→`client.ts:48` (fully replaces REST; can strip auto-injected `x-opencode-directory`). EventSource → `sdk.tsx:112-113`. headers → `sdk.tsx:30` (but on custom-events path, **stream auth is your job inside `subscribe`** — use Bearer from handshake).

**Lifecycle (PROTOCOL §2-3):** launcher spawns `voss serve`, reads one stdout JSON line `{v,port,token}`, derives url/token, supervises child (`kill_on_drop`). Extra vs `attach` (which takes a URL) but small.

---

## 6. VOSS DIFFERENTIATORS (probable/budget/confidence/gate)

Fork renders parts via `PART_MAPPING={text,tool,reasoning}` (`index.tsx:1521`). None of Voss's natives render today.
- **`probable` → message PART:** extend `PART_MAPPING` + widen v2 `Part` union (module augmentation; store reconciles by `part.id`, tolerates unknown `type`) + `ProbablePart` component (probability bar + collapsible `alternatives[]`, like `ReasoningPart`).
- **`budget`/`confidence`/`gate` → session STATUS strip:** net-new tiny store updated from adapter, rendered in header/footer (not the message list).

~4 new components + 1 small store + `PART_MAPPING`/`Part`-union widening.

---

## 7. EFFORT

| Area | Est | Note |
|---|---|---|
| Launcher + child supervision + handshake | **S** | ~30 lines, mirrors `attach.ts` |
| Auth Basic→Bearer | **S** | pure prop value |
| Boot REST stubs | **M** | synthetic Provider/Model matrix fiddly but static |
| REST proxy (session CRUD/msg/abort/perm) | **S–M** | 7 thin proxies + field renaming |
| **Event assembly machine** | **L** | **hardest** — mint IDs, re-segment deltas, tool lifecycle, synth busy/idle + terminal message.updated, `directory:"global"`. One instance per open session. |
| Voss-part rendering | **M** | 3-4 components + union widen + footer store |
| Build/packaging | **M** | bundle fork, ship alongside `voss serve`; native TUI = no macOS-WebDriver issue |

**Hardest sub-problem:** the event-assembly state machine. Holds turn correctness, id-dedup, and the **two-signal turn-done** (`session.status:idle` AND `message.updated.time.completed`) — either wrong ⇒ permanent spinner or duplicated rows.

---

## 8. TOP 5 RISKS + FIRST VERTICAL SLICE

1. **Silent drop on missing `directory:"global"`** (`event.ts:19`) — nothing renders, no error. → hardcode + unit-test assert.
2. **`.data!` crash after boot gate** (`sync.tsx:411-415`) — null `config.providers`/`provider.list`/`config.get` passes gate then crashes in reconcile. → return fully-shaped stubs.
3. **Half-stuck spinner** from one-sided turn-done. → emit `session.status:idle` AND terminal `message.updated{time.completed}` atomically.
4. **Tool-row duplication** from unstable ids. → key callID `(name, turn-counter)`, re-send across transitions; test.
5. **Synthetic Model drift / packaging coupling.** → pin v2 SDK version; isolate synthetic model; packaging = own phase.

### FIRST VERTICAL SLICE (smallest real end-to-end turn)
Build ONLY:
1. `voss.ts` launcher: spawn `voss serve`, read `{port,token}`, `tui()` with Bearer headers.
2. Custom `fetch`: hardcoded boot stubs (1 synthetic provider/model) + proxy `POST /session` and `POST /session/{id}/message`.
3. Custom `EventSource`: handle ONLY `user`, `stream.delta`, `final`, `session.idle` → emit `session.status:busy`, `message.updated`(user+assistant), one TextPart + delta stream, terminal `message.updated{time.completed}`, `session.status:idle`.

**Skip** tools, permissions, probable/budget/confidence, all Phase-C stubs (let status sit at `partial`).
**Success =** type a prompt in the forked TUI, see Voss's streamed text appear token-by-token, spinner stops cleanly. Proves boot gate + envelope routing + delta path + two-signal turn-done — the entire risky core — in the smallest change. Tools, then Voss part types, are the next two slices.

---

## Key files (absolute)
- Voss protocol: `/Users/benjaminmarks/Projects/Voss/.planning/PROTOCOL.md`
- Voss event union (real wire): `voss/harness/server/events.py`
- Voss emit shapes: `voss/harness/render.py:485-569`
- Voss routes: `voss/harness/server/app.py` (`/session*`, `/doctor` only; per-session SSE `/session/{id}/events`)
- Fork event seam: `/tmp/opencode-fork/.../tui/context/sdk.tsx:8-10,29,111-124`
- Fork event filter: `/tmp/opencode-fork/.../tui/context/event.ts:14-22`
- Fork live reducer: `/tmp/opencode-fork/.../tui/context/sync.tsx`
- Fork part render: `/tmp/opencode-fork/.../tui/routes/session/index.tsx:1521`
- Launcher template: `/tmp/opencode-fork/.../tui/attach.ts:84-98`

*Build-gate live-verified 2026-06-03. Contract from 5-agent workflow `wf_6c36a907-792`, cross-checked against both real codebases.*

---

# Appendix A — Slice-1 implementation (BUILT + VERIFIED, then reverted from repo)

**Status 2026-06-03:** Slice 1 was fully built against vendored fork `opencode-tui/` (OpenCode v1.15.13). It typechecked clean (`tsgo --noEmit`, 0 errors across the whole package), 6 assembly unit tests passed (46 assertions), the `opencode voss` command registered + the module graph imported. The vendored fork (2.7 GB w/ node_modules) was **reverted** — too large for the Voss repo. The code below is preserved verbatim so resuming = re-clone fork + paste these files (15 min), not rebuild.

**Confirmed seam facts (re-verify on resume but these held):**
- `tui/context/sdk.tsx` accepts `props.fetch` + `props.events` (an `EventSource = {subscribe(handler:(GlobalEvent)=>void):Promise<()=>void>}`); `TuiInput` (app.tsx:164-174) declares `fetch?`/`headers?`/`events?` and `tui()` forwards all three into `SDKProvider` (app.tsx:249-255). **Zero core-render edits.**
- `context/event.ts:13-22` unwraps `GlobalEvent.payload` and **drops anything where `event.directory !== "global"` AND `event.project !== project.project()`** → emit `directory:"global"`. Also skips `payload.type === "sync"`.
- Reducer `context/sync.tsx` switches on `event.type` reading `event.properties.*`; consumes `message.updated`{info:Message}, `message.part.updated`{part:Part,time}, `message.part.delta`{messageID,partID,field,delta} (DROPS delta if the part wasn't seeded first — `if(!parts)break`/`if(!result.found)break`), `session.status`{sessionID,status}. Stores binary-search by id → ids must be monotonic + lexicographically sortable.
- Send path: `component/prompt/index.tsx:1197` `sdk.client.session.prompt({sessionID,messageID,model,parts})` → `POST /session/{id}/prompt_async`, fire-and-forget. No optimistic render — TUI renders only from `message.updated` events, so the adapter mints its own ids.
- Launch: `voss` command spawns `voss serve` (console script `voss.cli:main`; on the dev box use `.venv/bin/voss serve`), reads one stdout line `{"v":1,"port","token"}`, pipes stdin (server's stdin-EOF heartbeat). v2 client `fetch` receives a `Request` (client.ts:48-52).

## 🔴 THE BUG that cost the over-the-wire turn (fix is in adapter.ts below)
`sse-starlette` frames events with **CRLF**: `event: <type>\r\ndata: <json>\r\n\r\n`. Splitting the SSE buffer on `"\n\n"` matches **nothing** (CR-LF-CR-LF contains no double-LF) → zero frames parsed → only the synthesized `busy` ever reached the TUI, turn appeared to hang. **Fix: normalize `\r\n`→`\n` on the buffer before splitting on `\n\n`.** Verified via the `VOSS_SERVE_FAKE_TURN=1` seam (canned turn, no LLM): raw frames are e.g. `"event: stream.delta\r\ndata: {\"v\":1,\"type\":\"stream.delta\",\"text\":\"hello \"}\r\n\r\n"`, multiple frames per chunk.

## Resume checklist
1. Clone OpenCode `v1.15.13` to a **sibling dir / separate repo** (NOT vendored in Voss). `bun install` (no zig — prebuilt `libopentui.dylib`).
2. Drop the 5 files below into `packages/opencode/src/cli/cmd/tui/` (voss.ts + voss/{assembly,stubs,adapter,assembly.test}.ts).
3. Add to `src/index.ts`: `import { VossCommand } from "./cli/cmd/tui/voss"` + `.command(VossCommand)` next to `AttachCommand`.
4. `bun test src/cli/cmd/tui/voss/assembly.test.ts` (6 green) ; `bun run typecheck` (0 errors).
5. OTW: spawn `.venv/bin/voss serve`, drive `adapter.fetch`+`adapter.events` (create→GET session→prompt_async), assert v2 envelope sequence. Use `VOSS_SERVE_FAKE_TURN=1` for the free path first; the FAKE-turn final text is `echo: <input>`.
6. Then a real turn (keychain OAuth, ~cents). Then launch `opencode voss` in a real TTY for the actual render (couldn't verify headless).

### `tui/voss/assembly.ts` (pure, unit-tested — the event-assembly machine)
```ts
import type { GlobalEvent, UserMessage, AssistantMessage, TextPart } from "@opencode-ai/sdk/v2"
export type AssemblyOptions = { cwd: string }
export function createAssembly(sessionID: string, opts: AssemblyOptions) {
  let n = 0
  const id = (prefix: string) => prefix + (++n).toString().padStart(12, "0")
  let userId: string | null = null, assistantId: string | null = null, assistantCreatedAt = 0, textPartId: string | null = null
  let providerID = "voss", modelID = "voss-default", tokensOut = 0, cost = 0
  const wrap = (type: string, properties: unknown): GlobalEvent =>
    ({ directory: "global", payload: { id: id("vevt"), type, properties } } as unknown as GlobalEvent)
  const msgUpdated = (info: UserMessage | AssistantMessage) => wrap("message.updated", { sessionID, info })
  const partUpdated = (part: TextPart) => wrap("message.part.updated", { sessionID, part, time: Date.now() })
  const delta = (messageID: string, partID: string, d: string) => wrap("message.part.delta", { sessionID, messageID, partID, field: "text", delta: d })
  const sessionStatus = (sid: string, status: { type: "idle" | "busy" }) => wrap("session.status", { sessionID: sid, status })
  function setModel(m: string | undefined) { if (!m) return; const s = m.indexOf("/"); if (s > 0) { providerID = m.slice(0, s); modelID = m.slice(s + 1) } else modelID = m }
  function mkUser(): UserMessage { return { id: userId!, sessionID, role: "user", time: { created: Date.now() }, agent: "voss", model: { providerID, modelID } } }
  function mkAssistant(done: boolean): AssistantMessage {
    const msg: AssistantMessage = { id: assistantId!, sessionID, role: "assistant",
      time: done ? { created: assistantCreatedAt, completed: Date.now() } : { created: assistantCreatedAt },
      parentID: userId ?? "", modelID, providerID, mode: "auto", agent: "voss", path: { cwd: opts.cwd, root: opts.cwd },
      cost: done ? cost : 0, tokens: { input: 0, output: tokensOut, reasoning: 0, cache: { read: 0, write: 0 } } }
    if (done) msg.finish = "stop"; return msg }
  function ensureAssistant(): GlobalEvent[] { if (assistantId) return []; assistantId = id("vmsg"); assistantCreatedAt = Date.now(); return [msgUpdated(mkAssistant(false))] }
  function busy(): GlobalEvent { return sessionStatus(sessionID, { type: "busy" }) }
  function translate(type: string, data: any): GlobalEvent[] {
    switch (type) {
      case "user": {
        userId = id("vmsg")
        const userText: TextPart = { id: id("vprt"), sessionID, messageID: userId, type: "text", text: data?.task ?? "" }
        assistantId = id("vmsg"); assistantCreatedAt = Date.now(); textPartId = null
        return [msgUpdated(mkUser()), partUpdated(userText), msgUpdated(mkAssistant(false))] }
      case "status": { setModel(data?.model); if (typeof data?.tokens === "number") tokensOut = data.tokens; if (typeof data?.cost_usd === "number") cost = data.cost_usd; return [] }
      case "stream.delta": {
        const pre = ensureAssistant(); const text: string = data?.text ?? ""
        if (!textPartId) { textPartId = id("vprt"); return [...pre, partUpdated({ id: textPartId, sessionID, messageID: assistantId!, type: "text", text })] }
        return [...pre, delta(assistantId!, textPartId, text)] }
      case "final": {
        const out = ensureAssistant(); if (typeof data?.cost_usd === "number") cost = data.cost_usd
        if (!textPartId) { textPartId = id("vprt"); out.push(partUpdated({ id: textPartId, sessionID, messageID: assistantId!, type: "text", text: data?.text ?? "" })) }
        out.push(msgUpdated(mkAssistant(true))); textPartId = null; return out }
      case "session.idle": { const ev = sessionStatus(data?.session_id ?? sessionID, { type: "idle" }); userId = null; assistantId = null; textPartId = null; return [ev] }
      default: return [] // server.connected + later-slice events (tool/plan/probable/budget/confidence/gate/...)
    } }
  return { translate, busy }
}
export type Assembly = ReturnType<typeof createAssembly>
```

### `tui/voss/stubs.ts` (boot REST stubs + synthetic Provider/Model + v2 Session mapper)
```ts
import type { Session, Provider, Model } from "@opencode-ai/sdk/v2"
const MODEL: Model = { id: "voss-default", providerID: "voss", api: { id: "voss", url: "", npm: "" }, name: "Voss",
  capabilities: { temperature: true, reasoning: true, attachment: false, toolcall: true,
    input: { text: true, audio: false, image: false, video: false, pdf: false }, output: { text: true, audio: false, image: false, video: false, pdf: false }, interleaved: false },
  cost: { input: 0, output: 0, cache: { read: 0, write: 0 } }, limit: { context: 200000, output: 32000 },
  status: "active", options: {}, headers: {}, release_date: "2026-01-01" }
export const VOSS_PROVIDER: Provider = { id: "voss", name: "Voss", source: "custom", env: [], options: {}, models: { "voss-default": MODEL } }
export function vossSession(id: string, cwd: string, title = ""): Session {
  const now = Date.now()
  return { id, slug: id, projectID: "voss", directory: cwd, title: title || "Voss session", version: "1", time: { created: now, updated: now } } }
const jsonResponse = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } })
export function bootStub(path: string, method: string, cwd: string): Response {
  switch (path) {
    case "/config": return jsonResponse({})
    case "/config/providers": return jsonResponse({ providers: [VOSS_PROVIDER], default: {} })
    case "/provider": return jsonResponse({ all: [VOSS_PROVIDER], default: {}, connected: ["voss"] }) // non-empty connected suppresses onboarding
    case "/provider/auth": return jsonResponse({})
    case "/agent": return jsonResponse([])
    case "/path": return jsonResponse({ home: "", state: "", config: "", worktree: cwd, directory: cwd })
    case "/project": return jsonResponse([])
    case "/project/current": return jsonResponse({ id: "voss", worktree: cwd, time: { created: 0, updated: 0 }, sandboxes: [] })
    case "/command": return jsonResponse([])
    case "/lsp": return jsonResponse([])
    case "/mcp": return jsonResponse({})
    case "/formatter": return jsonResponse([])
    case "/session/status": return jsonResponse({})
    case "/vcs": return jsonResponse(null)
    case "/find": case "/find/file": case "/find/symbol": return jsonResponse([])
    default: return method === "GET" ? jsonResponse([]) : jsonResponse({})
  } }
export { jsonResponse }
```

### `tui/voss/adapter.ts` (fetch routing + Voss SSE multiplexing — INCLUDES the CRLF fix)
```ts
import type { GlobalEvent } from "@opencode-ai/sdk/v2"
import { createAssembly, type Assembly } from "./assembly"
import { bootStub, vossSession, jsonResponse } from "./stubs"
export type VossAdapterOptions = { serverUrl: string; token: string; cwd: string }
export type VossEventSource = { subscribe: (handler: (event: GlobalEvent) => void) => Promise<() => void> }
export function createVossAdapter(opts: VossAdapterOptions) {
  const authHeaders = { Authorization: `Bearer ${opts.token}` }
  let handler: ((event: GlobalEvent) => void) | null = null
  const machines = new Map<string, Assembly>(), streams = new Map<string, AbortController>()
  const emit = (e: GlobalEvent) => handler?.(e)
  function machine(sid: string): Assembly { let m = machines.get(sid); if (!m) { m = createAssembly(sid, { cwd: opts.cwd }); machines.set(sid, m) } return m }
  function parseFrame(frame: string): { type: string; data: any } | null {
    let type = "message", data = ""
    for (const line of frame.split("\n")) { if (line.startsWith("event:")) type = line.slice(6).trim(); else if (line.startsWith("data:")) data += line.slice(5).trim() }
    if (!data) return null; try { return { type, data: JSON.parse(data) } } catch { return null } }
  async function openStream(sid: string): Promise<void> {
    if (streams.has(sid)) return
    const ctrl = new AbortController(); streams.set(sid, ctrl)
    let res: Response | null = null
    try { res = await fetch(`${opts.serverUrl}/session/${sid}/events`, { headers: authHeaders, signal: ctrl.signal }) } catch { streams.delete(sid); return }
    if (!res.ok || !res.body) { streams.delete(sid); return }
    const reader = res.body.getReader(), dec = new TextDecoder()
    void (async () => { let buf = ""
      try { for (;;) { const { done, value } = await reader.read(); if (done) break
        buf = (buf + dec.decode(value, { stream: true })).replace(/\r\n/g, "\n") // CRLF→LF (sse-starlette frames are CRLF)
        let idx: number
        while ((idx = buf.indexOf("\n\n")) >= 0) { const frame = buf.slice(0, idx); buf = buf.slice(idx + 2)
          const ev = parseFrame(frame); if (!ev) continue
          for (const g of machine(sid).translate(ev.type, ev.data)) emit(g) } } }
      catch {} finally { streams.delete(sid) } })() }
  async function proxyJson(path: string, init?: RequestInit): Promise<Response> { return fetch(`${opts.serverUrl}${path}`, { ...init, headers: { ...authHeaders, ...(init?.headers ?? {}) } }) }
  async function vossFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const req = input instanceof Request ? input : new Request(input, init)
    const url = new URL(req.url), path = url.pathname, method = req.method.toUpperCase()
    if (method === "POST" && path === "/session") {
      const r = await proxyJson("/session", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ cwd: opts.cwd, auth: "auto" }) }).catch(() => null)
      const body = r ? await r.json().catch(() => ({})) : {}
      if (!r || !r.ok) return jsonResponse({ error: (body as any)?.detail ?? "create failed" }, r?.status ?? 502)
      return jsonResponse(vossSession((body as any).id, opts.cwd)) }
    if (method === "GET" && path === "/session") return jsonResponse([])
    const getMatch = path.match(/^\/session\/([^/]+)$/)
    if (method === "GET" && getMatch) { const sid = getMatch[1]; void openStream(sid)
      const r = await proxyJson(`/session/${sid}`).catch(() => null); const body = r && r.ok ? await r.json().catch(() => null) : null
      return jsonResponse(vossSession(sid, body?.cwd ?? opts.cwd, body?.title)) }
    const promptMatch = path.match(/^\/session\/([^/]+)\/prompt_async$/)
    if (method === "POST" && promptMatch) { const sid = promptMatch[1]; await openStream(sid)
      const body = await req.json().catch(() => ({}) as any)
      const text: string = (body.parts ?? []).filter((p: any) => p?.type === "text").map((p: any) => p.text).join("\n")
      const r = await proxyJson(`/session/${sid}/message`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ v: 1, parts: [{ type: "text", text }], mode: "auto" }) }).catch(() => null)
      if (r && r.ok) emit(machine(sid).busy()); return jsonResponse({ status: "accepted" }, 202) }
    const abortMatch = path.match(/^\/session\/([^/]+)\/abort$/)
    if (method === "POST" && abortMatch) { await proxyJson(`/session/${abortMatch[1]}/abort`, { method: "POST" }).catch(() => {}); return jsonResponse({ status: "ok" }) }
    return bootStub(path, method, opts.cwd) }
  const events: VossEventSource = { subscribe: async (h) => { handler = h; return () => { if (handler === h) handler = null } } }
  function dispose() { for (const c of streams.values()) c.abort(); streams.clear() }
  return { fetch: vossFetch as unknown as typeof fetch, events, dispose }
}
```

### `tui/voss.ts` (launcher command — register in src/index.ts)
```ts
import { cmd } from "../cmd"
import { UI } from "@/cli/ui"
import { win32DisableProcessedInput, win32InstallCtrlCGuard } from "./win32"
import { TuiConfig } from "@/cli/cmd/tui/config/tui"
import { createVossAdapter } from "./voss/adapter"
export const VossCommand = cmd({
  command: "voss", describe: "launch the Voss harness TUI (spawns `voss serve`)",
  builder: (yargs) => yargs.option("dir", { type: "string", describe: "directory to run in" })
    .option("serve-cmd", { type: "string", describe: "override server launch (default: $VOSS_SERVE_CMD or `voss serve`)" }),
  handler: async (args) => {
    const unguard = win32InstallCtrlCGuard()
    let proc: ReturnType<typeof Bun.spawn> | undefined, disposeAdapter: (() => void) | undefined
    try {
      win32DisableProcessedInput()
      const directory = (() => { if (!args.dir) return process.cwd(); try { process.chdir(args.dir); return process.cwd() } catch { return args.dir } })()
      const serveCmd = (args.serveCmd ?? process.env["VOSS_SERVE_CMD"] ?? "voss serve").split(" ").filter(Boolean)
      try { proc = Bun.spawn(serveCmd, { cwd: directory, stdin: "pipe", stdout: "pipe", stderr: "inherit", env: process.env }) }
      catch (e) { UI.error(`failed to spawn \`${serveCmd.join(" ")}\`: ${String(e)}`); process.exitCode = 1; return }
      const handshake = await readLine(proc.stdout as ReadableStream<Uint8Array>)
      if (!handshake) { UI.error("voss serve did not emit a handshake line on stdout"); process.exitCode = 1; return }
      let port: number, token: string
      try { const p = JSON.parse(handshake); port = p.port; token = p.token; if (!port || !token) throw new Error("missing port/token") }
      catch (e) { UI.error(`bad handshake: ${handshake} (${String(e)})`); process.exitCode = 1; return }
      const serverUrl = `http://127.0.0.1:${port}`
      const adapter = createVossAdapter({ serverUrl, token, cwd: directory }); disposeAdapter = adapter.dispose
      const config = await TuiConfig.get()
      const { createTuiRenderer, tui } = await import("./app")
      const renderer = await createTuiRenderer(config)
      const handle = tui({ url: serverUrl, config, renderer, args: {}, directory, fetch: adapter.fetch, events: adapter.events })
      await handle.done
    } finally { disposeAdapter?.(); try { proc?.kill() } catch {} ; unguard?.() }
  } })
async function readLine(stream: ReadableStream<Uint8Array>): Promise<string | null> {
  const reader = stream.getReader(), dec = new TextDecoder(); let buf = ""
  try { for (;;) { const { done, value } = await reader.read(); if (done) return buf.trim() || null
    buf += dec.decode(value, { stream: true }); const nl = buf.indexOf("\n"); if (nl >= 0) return buf.slice(0, nl).trim() } }
  finally { reader.releaseLock() } }
```

### `tui/voss/assembly.test.ts` (6 tests, all passed — see git-less history)
Asserts, over a `user → busy → status → 2×stream.delta → final → session.idle` sequence: every envelope has `directory:"global"`; the reducer types are present (`message.updated`/`message.part.updated`/`message.part.delta`/`session.status`); two-signal turn-done (`busy` then `idle` + assistant `time.completed`+`finish:"stop"`); first delta SEEDS a TextPart and subsequent deltas reference its id; user msg+part precede assistant (id-monotonic, `parentID` set); final-with-no-deltas still seeds text. (Full test body is mechanical — re-derive from these assertions.)
