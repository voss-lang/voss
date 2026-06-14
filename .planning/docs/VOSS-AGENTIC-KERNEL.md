# VOSS Agentic Kernel — Architecture Spec

**Created:** 2026-06-14
**Status:** Architecture exploration — committed *design* direction, no implementation started.
**Supersedes the "reject kernel" stance in:** `.planning/VOSS-USERSPACE-OS-HANDOFF.md` §A.
**Decision locked (2026-06-14):** Embodiment = **microVM unikernel (Firecracker)**. Not bare-metal, not a plain userspace daemon.
**Scope:** This is the long-horizon north star (V-track successor). The harness MVP remains the shipping userland; the kernel slides underneath later.

---

## 0. Thesis

Build a **kernel-level operating system for agentic engineering** whose scheduled primitive is **the token**, not the CPU cycle.

Every general-purpose OS schedules a scarce resource (CPU time) across processes and isolates them. Containers and seccomp already do that for agents-as-processes — which is exactly why the prior handoff called a kernel redundant. That judgment assumed CPU scheduling.

It is wrong for one reason: **the scarce resource in agentic computing is not CPU — it is tokens, context, and inference capacity.** No existing kernel, container runtime, or sandbox schedules, accounts for, preempts, or isolates *that* resource. That gap is the entire justification for a new kernel.

> **The LLM is the CPU. Context is the RAM. Tools are the syscalls. The kernel schedules token-work onto inference cores.**

---

## 1. The core mapping (the spine)

Every row already half-exists in Voss userspace. The kernel pulls each below the syscall line and enforces it in compiled code.

| OS concept | Agentic kernel | Voss antecedent |
|---|---|---|
| CPU core | model endpoint (Claude / GPT / local GPU) | `voss/harness/providers.py` |
| process | agent | `SubagentSpec`, `run_subagent` |
| PID | agent ID | `VOSS_AGENT_ID` (V17) |
| scheduler | token-budget scheduler (preemptive) | budget logic in runtime |
| time slice | token quota per turn | context/budget caps |
| RAM + pages | context window + context pages | `voss_runtime` context |
| virtual memory / swap | semantic memory (vector store) | V19 chroma code memory |
| MMU | context manager | context assembler |
| **page fault** | **retrieval** (needed info not resident → fetch) | semantic match / recall |
| syscall | tool call | `voss/harness/tools.py` |
| capability (seL4-style) | tool permission grant | `PermissionGate`, `permissions.yml` |
| fork / exec | `agent_spawn` | subagent spawn |
| wait / gather | `agent_gather` | board join / collect |
| signal / kill | cancel / interrupt agent | `lifecycle.py` tree-kill |
| init (PID 1) | EM loop / board / supervisor | EM loop, reviewer gates |
| daemon | long-running background agent | background jobs |
| device driver | provider adapter | `providers.py` |
| filesystem | project cognition + repo | `.voss/`, `.voss-cache/` |
| inode / handle | memory record / artifact handle | cognition records |
| cgroups / rlimits | budget + scope limits | token budgets, scope |
| dmesg / audit log | append-only replay journal | `recorder.py` |
| user / group perms | team roles | `team.py` |

**This table is the product.** Building the kernel = enforcing this table in a microVM.

---

## 2. Embodiment: microVM unikernel (locked)

```
                per-agent microVM
        ┌────────────────────────────────┐
        │  Firecracker (KVM)             │
        │  ┌──────────────────────────┐  │
        │  │  voss agentic ukernel     │  │  ring 0 *inside the VM*
        │  │  ┌────────────────────┐  │  │
        │  │  │ token scheduler     │  │  │
        │  │  │ context MMU         │  │  │
        │  │  │ capability table    │  │  │
        │  │  │ syscall dispatch    │  │  │
        │  │  │ journal driver      │  │  │
        │  │  └────────────────────┘  │  │
        │  │  userland: harness servers│  │  ring 3 in-VM
        │  └────────────┬─────────────┘  │
        │      virtio (net/vsock/blk)    │
        └────────────────┼───────────────┘
                         │  (HTTPS / gRPC over virtio-net)
              inference endpoints  ← "devices" (the CPU cores)
              host journal sink    ← durable audit
              cognition volume     ← virtio-blk / 9p mount
```

**Why this and not the alternatives:**

- **vs bare-metal:** inference is remote. A bare-metal kernel would write disk/net drivers purely to make HTTPS calls. The "manages hardware" value is ≈0; only the isolation value is real. microVM gives the isolation (KVM-enforced) without the driver-years.
- **vs plain C daemon:** a daemon's isolation is borrowed seccomp/namespaces you didn't author. The whole pitch is *hardware-enforced* cap isolation that untrusted agent code cannot escape. Only a VM boundary delivers that.

**One agent-tree = one microVM.** Boot ≈125ms (Firecracker proven at Lambda/Fargate scale). Sub-agents are processes *within* the VM unless they need stronger isolation, in which case they get their own nested microVM.

**Inference endpoints are devices.** The kernel's "scheduler" dispatches token-work to whichever endpoint is the right core (cheapest, fastest, highest-quality) — multi-provider load balancing as multi-core scheduling.

---

## 3. Implementation language — Rust core, C ABI

Recommendation, with the tradeoff stated plainly:

- **Kernel core in Rust.** The two kernels that survive contact with reality are seL4 (C + full formal verification — a multi-year proof effort) and Rust kernels (Redox, Linux's Rust subsystems) that get memory safety by construction. A hand-rolled C kernel from a small team is a memory-safety footgun farm with none of seL4's proofs. The repo is already Rust (`crates/voss-app-core`).
- **C ABI at the syscall boundary.** The stable agent↔kernel contract (`agent_spawn`, `cap_grant`, …) is exposed as a C ABI so any guest userland (the Python harness, future native agents, third-party tools) can call it via FFI. "Literally a C kernel" is honored where it matters — the public ABI is C — without writing the unsafe core in C.
- **Pure C only if** you commit to the seL4 formal-verification path. That is a separate, much larger bet; flag it, don't default to it.

---

## 4. Syscall ABI (C surface)

Illustrative, not final. The ABI *is* the product contract — design it before any subsystem.

```c
/* ---- lifecycle ---- */
agent_t  agent_spawn(const struct agent_spec *spec);      /* fork+exec */
int      agent_send(agent_t to, const void *msg, size_t n);
int      agent_gather(agent_t *kids, size_t n, struct result *out);
int      agent_signal(agent_t target, enum sig s);        /* cancel/pause/resume */
int      agent_wait(agent_t target, struct exit_info *out);

/* ---- capabilities (deny by default) ---- */
cap_t    cap_grant(agent_t to, enum tool t, const struct scope *s);
int      cap_revoke(agent_t from, cap_t c);
int      cap_check(agent_t who, enum tool t, const struct scope *s);

/* ---- token scheduling (the heart) ---- */
int      budget_set(agent_t a, struct token_budget b);    /* rlimit analog */
int      budget_query(agent_t a, struct token_budget *out);
/* preemption: kernel may pause an agent mid-turn on overrun and emit a
   checkpoint; budget_yield lets a cooperative agent give back early.    */
int      budget_yield(agent_t self, uint64_t tokens_returned);

/* ---- context MMU ---- */
ctx_t    ctx_map(agent_t a, const struct mem_ref *what);  /* page in */
int      ctx_unmap(agent_t a, ctx_t page);                /* evict */
int      ctx_fault(agent_t a, const struct query *q, struct mem_ref *out);
                                                          /* retrieval */

/* ---- inference dispatch (the "devices") ---- */
int      infer_submit(agent_t a, const struct turn *t, infer_handle *h);
int      infer_poll(infer_handle h, struct turn_result *out);

/* ---- audit / replay ---- */
int      audit_append(agent_t a, const struct event *e);  /* mostly implicit */
int      audit_read(uint64_t from_seq, struct entry *buf, size_t *n);
int      replay_open(uint64_t session, struct replay_ctx *out);
```

**Design rules:**
- **Deny by default.** No `cap_grant` → no tool. Every `syscall`/tool call passes `cap_check` in the kernel; the guest cannot bypass it.
- **All nondeterminism journaled.** Model outputs and tool results are recorded at the syscall boundary so `replay_open` reproduces a session bit-exact.
- **Budget overrun is preemptive, not advisory.** The scheduler can pause an agent mid-turn, checkpoint it, and resume or reap later — true preemption, unlike today's cooperative budget checks.

---

## 5. Net-new kernel subsystems (beyond what Voss has)

1. **Preemptive token scheduler** — pause/checkpoint an agent mid-turn on budget blow; resume later. Priority classes (reviewer > worker > speculative). Today's budget logic is cooperative; this is real preemption with saved state.
2. **Context MMU** — working-set management. Agent declares needs; kernel pages context in; a *page fault* = a retrieval against semantic memory (V19). Auto-compaction becomes a page-eviction policy (LRU / relevance-weighted).
3. **Capability microkernel** — generalizes `PermissionGate` to the syscall level, KVM-enforced. The unit of authority is a *tool + scope*, not a file mode.
4. **Inference scheduler** — routes token-work across endpoints like a multi-core scheduler: cheapest/fastest/best core for the job, with failover. Generalizes `providers.py` into a driver layer.
5. **Deterministic syscall replay** — record-replay at the ABI boundary; bit-exact session reconstruction for debugging, audit, and regression.
6. **Multi-tenancy** — many agents/users on one host, isolated by microVM. Real multi-user OS model for an agent fleet.

These are the "stuff we don't have yet." Items 1–4 *extend* existing Voss code; 5 extends `recorder.py`; 6 is genuinely new.

---

## 6. Voss becomes the userland

Nothing in the current project is wasted — it relocates above the syscall line.

| Voss today | Role under the kernel |
|---|---|
| `voss/harness/*` | userspace servers (the "userland" the kernel runs) |
| `voss/harness/providers.py` | inference device drivers |
| `voss/harness/permissions.py` | seed for the kernel capability table |
| `voss/harness/lifecycle.py` | informs `agent_signal` / reap semantics |
| `recorder.py` | journal driver behind `audit_*` |
| `.voss` language | init / shell scripts that drive the syscall ABI |
| `.voss/`, `.voss-cache/` | filesystem + swap (cognition + vector memory) |
| `crates/voss-app-core` | host-side supervisor + Firecracker orchestration |
| OSC `BudgetData`/`ContextData` | proto-`/proc` — promote to real kernel introspection |

The voss-app `CONCEPT.md` L1→L2→L3 build order is unaffected; L2's "cell supervisor + IPC" is the natural host-side launcher for microVMs.

---

## 7. Phased roadmap

Each phase is independently valuable — no big-bang. Stop at any phase and still have a shipped product.

| Phase | Deliverable | Proves |
|---|---|---|
| **K0** | This doc + syscall ABI frozen (`.h` header, no impl) | the contract is coherent |
| **K1** | Host orchestrator: boot a Firecracker microVM, run the existing harness inside it, journal to host | isolation works; harness survives the VM boundary |
| **K2** | `cap_check` enforced in-guest: deny-by-default tool gate at the ABI | hardware-enforced capability isolation |
| **K3** | Token scheduler: `budget_set` + preemptive pause/checkpoint/resume | tokens-as-scheduled-resource is real |
| **K4** | Context MMU: `ctx_map`/`ctx_fault` with retrieval-as-page-fault | context-as-memory abstraction holds |
| **K5** | Inference scheduler: multi-endpoint routing + failover | LLM-as-multi-core |
| **K6** | Deterministic replay across the ABI | reviewed + replayable, kernel-enforced |
| **K7** | Multi-tenancy: fleet of agent microVMs, one host | OS-for-an-org claim earned |

**K1 is the make-or-break spike.** If the harness can't run cleanly inside a Firecracker microVM with acceptable boot/latency, the whole embodiment is wrong — find out first.

---

## 8. Non-goals (do not contradict)

Carried from `ORCHESTRATION_LAYERS.md` §3.2, plus kernel-specific:

- Bare-metal boot / custom hardware drivers — explicitly rejected (§2).
- Replacing the Python harness with a native runtime — harness *becomes* the userland, unchanged.
- Replacing all programming languages, or `.voss` as a general-purpose language.
- Fully autonomous deploy/delete/spend without human confirmation.
- Pure-C unsafe core — Rust core + C ABI unless the seL4 verification bet is explicitly taken (§3).
- Letting the kernel eat the MVP — harness userland ships on its own schedule; kernel is the V-track successor.

---

## 9. Open questions (for K0 → K1)

1. **Guest userland shape:** does the full Python harness run in-VM, or a thin agent stub that RPCs to a host-side harness? (Latency vs isolation.)
2. **Sub-agent granularity:** process-in-VM by default, nested microVM only for untrusted code — what's the trigger?
3. **Journal durability:** vsock to host sink vs virtio-blk append log — ordering + crash semantics.
4. **Context MMU residency:** what counts as a "resident page" — token-count budget, semantic relevance, or both?
5. **Scheduler policy:** priority classes and preemption granularity (per-turn vs per-tool-call).
6. **ABI stability:** version the C header from day one; how do guest/host negotiate versions?
7. **Cost accounting:** is dollar-cost a first-class scheduled resource alongside tokens, or derived?

---

## 10. Verification for "done" on this design pass

- [ ] Every syscall maps to an existing Voss antecedent or a named net-new subsystem (§4–6).
- [ ] Non-goals consistent with `ORCHESTRATION_LAYERS.md`.
- [ ] No bare-metal / custom-driver commitment.
- [ ] microVM design compatible with voss-app `CONCEPT.md` L2 supervisor.
- [ ] K1 spike scoped tightly enough to falsify the embodiment fast.
- [ ] C ABI header drafted before any subsystem implementation.

---

## Key files to read first

```
.planning/VOSS-USERSPACE-OS-HANDOFF.md     # the prior (now-superseded §A) analysis
.planning/docs/ORCHESTRATION_LAYERS.md     # product truth, non-goals
apps/voss-app/CONCEPT.md                    # L2 cell supervisor = host-side VM launcher
voss/harness/permissions.py                 # seed for capability table
voss/harness/providers.py                   # seed for inference device layer
voss/harness/recorder.py                    # seed for journal driver
voss/harness/lifecycle.py                   # signal/reap semantics
crates/voss-app-core/src/pty/commands.rs    # BudgetData/ContextData = proto-/proc
```
