# Phase M1: Harness Happy Path - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

M1 makes the Python harness usable on a real repo for the four canonical entry points: `voss doctor`, `voss do`, `voss edit`, and the bare `voss` / `voss chat` REPL — plus the supporting commands `voss tools`, `voss config`, `voss sessions`, `voss resume`. It does **not** add durable project cognition (`.voss/project.json`, `.voss/architecture.md`, etc. — those are M2).

**In scope:**
- Polish existing `voss/harness/*.py` (~2.4k LOC) so the documented happy path actually runs against a foreign repo end-to-end.
- Fill the M1 command gaps: `voss edit <path>` (REPL with scoped edit set), `voss tools` (registry table), `voss config` (open/report `~/.config/voss/config.toml`).
- Implement and wire permission modes `plan` / `edit` / `auto` to the tool registry tiers.
- REPL slash commands: `/login`, `/model`, `/mode`, plus existing help/quit.
- `voss doctor` minimal-essentials check set, diagnose-and-suggest only.
- Session snapshot redaction guarantee (schema-allowlist + secret-pattern unit test). Storage stays at `~/.local/state/voss/sessions/<id>.json`.

**Out of scope (deferred to other phases):**
- `.voss/project.json`, `.voss/architecture.md`, `.voss/sessions/`, `.voss/plans/`, `.voss/decisions/`, repo index, persistent project memory — all M2.
- `.voss` language sample validation — M3.
- Dogfooded harness loop in `.voss` — M4.
- Eval golden tasks, cost/success tracking, install polish — M5.
- Rust harness shell — post-v0.1.
- New providers, fine-grained model routing, MCP — deferred.

</domain>

<decisions>
## Implementation Decisions

### `voss edit` scope contract
- **D-01:** `voss edit <path>` runs as an interactive REPL session (not a one-shot). Exits on `/quit`, Ctrl-D, or EOF on stdin. Matches Claude Code's edit flow.
- **D-02:** Default editable scope is `<path> + its sibling test file`. Resolution rules:
  - If `<path>` is `src/foo/bar.py`, sibling set is the mirror in `tests/` (`tests/foo/test_bar.py`, `tests/test_bar.py`, etc.) when one exists.
  - If `<path>` is a directory, the scope is the directory recursively plus the mirror test directory.
  - If no obvious test mirror exists, scope is just `<path>`. The doctor/scope-summary line on session start lists the resolved set so the user sees it.
- **D-03:** Tools may always **read** any file under the cwd path jail without a prompt. Scope only restricts **writes** (`fs_write`, `fs_edit`) and any tool that mutates state outside the in-scope set.
- **D-04:** When the agent attempts a write outside the scope set, the permission gate prompts `expand scope to include <path>? [y/once/always/n]`. "always" persists for the rest of the session only (not across `voss resume`). "n" causes the tool call to fail with a structured error the agent can read.

### Permission modes (`plan` / `edit` / `auto`)
- **D-05:** Strict tier mapping:
  - `plan` → read-only set: `fs_read`, `fs_glob`, `fs_grep`, `git_status`, `git_diff`, `voss_check`. All mutating tools are unavailable (tool call returns "denied by mode plan").
  - `edit` → read-only set plus `fs_write`, `fs_edit`. Every mutating call shows a diff preview + `[y/once/always/n]` prompt. `shell_run` is **not** available in `edit`.
  - `auto` → all tools, including `shell_run`. `shell_run` still enforces the shell allowlist and command timeout, and prompts on allowlist miss. `fs_write`/`fs_edit` prompt the first time per file and remember "always" for the session.
- **D-06:** Tool descriptors carry an explicit `is_mutating: bool` (data-driven classification, no name-pattern matching), so adding a new tool requires explicitly choosing its tier.
- **D-07:** Mode selection: per-command default + override.
  - `voss do` → defaults to `plan`.
  - `voss edit` → defaults to `edit`.
  - `voss chat` / bare `voss` → defaults to `plan`.
  - CLI flag `--mode={plan,edit,auto}` overrides the default.
  - REPL slash command `/mode <name>` switches mid-session (cannot escalate to `auto` mid-session without explicit confirmation `/mode auto --confirm` to avoid a stray paste running shell).

### Auth REPL surface
- **D-08:** Two new REPL slash commands in M1:
  - `/login [provider]` — kicks the OAuth flow for `anthropic` (Claude Code Keychain) or `openai` (Codex Keychain/`~/.codex/auth.json`). No-arg form prompts which provider. If creds already exist, prints status and offers refresh.
  - `/model [name]` — no-arg lists detected providers + currently active model. With a name, switches active model. The last choice persists to `~/.config/voss/config.toml` under `[harness] preferred_model = "..."`.
- **D-09:** Resolution order when no explicit `/model` choice: keep existing `auth.resolve(preference="auto")` logic — Keychain over file, Anthropic over Codex when both present.
- **D-10:** Provider credentials still live where they live today (macOS Keychain, `~/.claude/.credentials.json`, `~/.codex/auth.json`). M1 does not introduce a new credential store.

### `voss doctor`
- **D-11:** Minimal-essentials check set (in display order):
  1. Python version (>= 3.10).
  2. `voss` compiler import (`voss.cli`, `voss_runtime`) reachable.
  3. Provider auth: Anthropic Keychain/file present and unexpired; Codex creds present (informational if missing).
  4. `git` binary on PATH.
  5. cwd writable.
  6. `~/.config/voss/` and `~/.local/state/voss/sessions/` creatable.
  7. `.voss/` and `.voss-cache/` creatable in cwd (informational for M1 — M2 enforces).
- **D-12:** Output is a traffic-light table: ✓ / ⚠ / ✗ per row, with a one-line reason for non-✓.
- **D-13:** Diagnose-and-suggest only. Failed rows print the exact command to fix (e.g. `Run: claude /login` for missing Anthropic auth, `pyenv install 3.10` for Python too old). Doctor never executes a fix itself.
- **D-14:** Exit code: 0 if all ✓, 1 if any ✗, 0 with non-zero stderr message if only ⚠ (informational misses).

### Session snapshot
- **D-15:** Storage location stays at `~/.local/state/voss/sessions/<id>.json` for M1. Move to `.voss/sessions/` happens in M2 along with the rest of project cognition. Dual-write/migration is M2's problem.
- **D-16:** Redaction guarantee = **schema allowlist**. `SessionRecord` dataclass has fixed fields (`id`, `name`, `cwd`, `model`, `started_at`, `updated_at`, `total_cost_usd`, `turns`). Nothing outside the schema gets serialized.
- **D-17:** Add a unit test (`tests/harness/test_session_redaction.py`) that:
  - Runs a synthetic turn whose context includes a fake API key (`sk-test-...`), OAuth bearer (`Bearer test-...`), and `anthropic-beta` header value.
  - Saves the session.
  - Scans the JSON for known secret patterns (`Authorization`, `Bearer `, `sk-`, `oauth_`, `anthropic-beta`, `api_key`).
  - Fails the build if any pattern appears.
- **D-18:** `voss resume <id>` rehydrates `cwd`, `model`, and the transcript into `EpisodicMemory`. It does NOT re-authenticate provider creds — those resolve fresh from Keychain at resume time.

### Claude's Discretion
- Exact `voss tools` and `voss config` table layout — pick something readable that matches the existing `voss sessions` style.
- REPL prompt string and color/glyph treatment — match existing `render.py` conventions.
- Path-jail edge cases (symlinks pointing outside cwd, `/proc`-style virtual paths) — pick the safe default (deny by default; existing `sandbox.py` already covers most cases).
- Concrete shell allowlist for `auto` mode — start from the existing `sandbox.py` allowlist; expand only if needed.
- File-watcher / repl-redraw behavior — pick a non-intrusive default.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v0.1 scope and product framing
- `.vscode/voss_v_0_1_scope_lock.md` — Source of truth for v0.1. Defines harness-led MVP, M0–M5 phase split, naming rules (`voss run` vs `voss do`), `.voss/` vs `.voss-cache/` split.
- `.planning/PROJECT.md` — Project framing, active requirements, key decisions, constraints.
- `.planning/REQUIREMENTS.md` — Specifically CLIH-01..10 and CTRL-01..09 (the requirement IDs M1 owns).
- `.planning/ROADMAP.md` §"Phase M1: Harness Happy Path" — Phase goal, success criteria, cross-cutting constraints.
- `.planning/HARNESS-PLAN.md` §0 (v0.1 scope lock), §1, §2 — Original harness design; M1 polishes toward this target.

### Existing Python harness (parity contract to polish, not rewrite)
- `voss/harness/cli.py` (484 LOC) — Click command surface; `do`, `chat`, `doctor`, `sessions`, `resume`. M1 adds `edit`, `tools`, `config`.
- `voss/harness/agent.py` (238 LOC) — `run_turn` and `Plan` schema.
- `voss/harness/auth.py` (331 LOC) — Anthropic Keychain + Codex resolution; basis for `/login` and `/model`.
- `voss/harness/providers.py` (401 LOC) — `AnthropicOAuthProvider`, `OpenAIOAuthProvider`.
- `voss/harness/permissions.py` (126 LOC) — Gate + persistence; M1 extends with mode tiers.
- `voss/harness/sandbox.py` (49 LOC) — cwd path jail + shell allowlist.
- `voss/harness/session.py` (113 LOC) — `SessionRecord` schema; M1 hardens redaction.
- `voss/harness/tools.py` (170 LOC) — 9 tool implementations + descriptors; M1 adds `is_mutating: bool`.
- `voss/harness/render.py` (202 LOC) — Tty/Plain/Ndjson renderers.

### Existing tests (parity contract)
- `tests/harness/test_cli.py`
- `tests/harness/test_agent_integration.py`
- `tests/harness/test_auth.py`
- `tests/harness/test_oauth_provider.py`, `tests/harness/test_openai_oauth.py`
- `tests/harness/test_sandbox.py`
- `tests/harness/test_session.py` — extend with the redaction test (D-17).
- `tests/harness/test_tools.py`

### External, do not re-derive
- Anthropic Messages API + `anthropic-beta: oauth-2025-04-20` — already encoded in `voss/harness/providers.py:AnthropicOAuthProvider`.
- Codex ChatGPT subscription wire shape — already encoded in `voss/harness/providers.py:OpenAIOAuthProvider`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Whole `voss/harness/` package**: ~2.4k LOC of working, test-covered code. M1 polishes; it does not rewrite.
- **`voss/harness/auth.py:resolve(preference="auto")`**: returns a `Resolution` with provider, model, source, detail. Already the basis for `/login` and `/model` UX.
- **`voss/harness/session.py:SessionRecord`**: schema already excludes provider secrets. M1's redaction test (D-17) freezes that invariant.
- **`voss/harness/sandbox.py`**: cwd path jail + shell allowlist already exist. M1 reuses; does not replace.
- **`voss/harness/permissions.py`**: existing `[y/once/always/n]` gate. M1 layers mode-tier filtering on top of it.
- **`voss/cli.py:main`**: existing Click group; `voss/harness/cli.py:register(group)` already mounts the harness verbs onto it. M1 adds `edit`, `tools`, `config` via the same `register` seam.

### Established Patterns
- **Tool descriptor pattern**: every tool exposes name/description/parameters/invoke. M1 adds an `is_mutating: bool` field — data-driven mode tier classification.
- **Auth resolution as a pure function**: `resolve(preference)` returns a `Resolution` dataclass; harness consumes that, never the raw blob. `/model` writes preference; `resolve` reads it.
- **REPL slash commands**: existing pattern in `voss/harness/cli.py:_run_repl` and `_print_slash_help`. `/login`, `/model`, `/mode` follow that template.
- **Renderer-aware output**: Tty/Plain/Ndjson renderers in `render.py`; `voss doctor` and `voss tools` tables should reuse the Tty renderer's table primitive.

### Integration Points
- **Mode → tool filtering**: `permissions.py` is the right seam — wrap tool registry lookup with a mode predicate before invocation.
- **`/login` → OAuth flows**: Anthropic flow needs to plug into Claude Code's Keychain entry; Codex flow needs to write `~/.codex/auth.json`. Both flows already partially exist in `auth.py` (read paths); M1 adds the write/refresh-from-scratch paths if missing.
- **`voss edit` scope set**: lives in the session state (not the global gate), so it resets per `voss edit` invocation.
- **`voss doctor` output**: stays in `voss/harness/cli.py:doctor_cmd`; checks are pure functions added to `auth.py` (already has `resolve`) and a new tiny `voss/harness/diagnostics.py` for filesystem/binary checks.

</code_context>

<specifics>
## Specific Ideas

- **`/login` UX modeled on Claude Code / Codex CLI** — user's framing: "you can sign up with your provider, and then maybe `/model` if you want to use multiple. It pulls your keychain keys for whatever services you're trying to use." Means: detect what's available, surface it, let the user pick — don't force a full OAuth flow if Keychain already has tokens.
- **Strict tier semantics over prompt-heavy** — `plan` should make it structurally impossible to write; `edit` allows writes-with-prompt; `auto` is the only place `shell_run` lives. This is enforcement, not advice.
- **Schema-allowlist for redaction** — the test that scans for secret patterns must run in CI; this is the kind of guarantee that silently regresses without a build-time check.

</specifics>

<deferred>
## Deferred Ideas

- **`.voss/sessions/` durable session move** — M2; touches project cognition. Dual-write strategy intentionally not adopted in M1.
- **Network reachability check in `voss doctor`** (ping Anthropic/OpenAI base URLs) — out of scope for M1; revisit if users hit corp-proxy issues in practice.
- **Tool smoke tests in `voss doctor`** (exec each tool on a temp scratch) — deferred; minimal-essentials is enough for M1.
- **Doctor offers to fix inline** (`mkdir`, run `/login`) — explicitly rejected for M1. Read-only diagnose is the safer default; revisit after dogfooding.
- **Path + grep-related-refs as default edit scope** — rejected as too wide. If a real workflow needs it, add a `/widen --refs` REPL command in a later milestone.
- **Agent-proposed file set at session start** — rejected for M1; revisit if path+tests proves too narrow in practice.
- **Regex scrubber pass over turn content** — deferred. Schema allowlist + pattern test is the M1 guarantee; add the scrubber only if a leak is found.
- **Config-driven default mode** — rejected; per-command defaults are clearer for new users.
- **`/mode auto` mid-session without `--confirm`** — explicitly gated to avoid a stray paste triggering shell execution.

</deferred>

---

*Phase: M1-harness-happy-path*
*Context gathered: 2026-05-10*
