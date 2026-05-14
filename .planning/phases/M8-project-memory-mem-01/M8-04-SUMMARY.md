---
phase: M8
plan: 04
status: complete
date: 2026-05-14
---

# M8-04 Summary — Convention Extraction at Clean Exit (MEM-04)

`voss/harness/conventions.py` now has full behavior. Both REPL clean-exit
(EOFError/KeyboardInterrupt) and `voss do` post-run paths invoke
`run_on_clean_exit`. Pitfall 5 mitigated by tightened has_signal quorum +
non-interactive default to "persist none".

## has_signal Quorum

Returns True only when:
- **(a)** at least one user-turn matches `_SIGNAL_RE` AND total user-turn count ≥ 2, OR
- **(b)** repeat-edit-same-target: at least one path appears in `run.changed` lists of ≥ 2 runs.

Pitfall 5 mitigation: single "use X" prompts no longer fire extraction.
Quorum tightens the budget impact for free.

`turns` argument accepts both `voss_runtime.memory.Turn` objects and dict
shapes via the private `_turn_role` / `_turn_content` accessors (acceptance
gate uses dicts; production callers use Turn).

`runs` argument tolerates RunRecord dataclass, dict, or any object with
`.changed` attribute.

## extract_conventions Failure Modes

All return `[]`:

| Failure | Path |
|---------|------|
| `asyncio.TimeoutError` after `timeout` seconds (default 8.0) | `except asyncio.TimeoutError` |
| Any provider exception | `except Exception` + stderr one-liner |
| Provider returned empty / no text | implicit check before parse |
| `json.JSONDecodeError` on response | `except json.JSONDecodeError` |
| Response root not a list | `if not isinstance(raw, list)` |
| `pydantic.ValidationError` on any element | bail entire batch (no partials) |

Prompt strips optional fenced code blocks (\`\`\`json … \`\`\`) before parse so
chatty providers can't break extraction.

## review_candidates Interactive vs Non-Interactive

- Empty `candidates` → `[]`.
- `interactive=False, selection=None` → `[]` (Req 4 acceptance for piped / CI use).
- `interactive=False, selection="1 3"` → `[0, 2]` (1-based input → 0-based indices; out-of-range tokens silently dropped; duplicates deduped via order-preserving append).
- `interactive=True` → click.echo numbered list + `input()` prompt; `EOFError` / `KeyboardInterrupt` / empty → `[]`.

## run_on_clean_exit Config + Defensive Wrap

- Reads `.voss/config.yml` via `yaml.safe_load`; absence / parse error → default config.
- `memory.extract_conventions` (bool, default `True`) — false skips the entire path with no LLM call.
- `memory.extraction_timeout_seconds` (float, default 8.0) — overrides the asyncio.wait_for timeout.
- All logic wrapped in top-level `try/except Exception`. Failure emits `conventions extraction skipped: <exc>` to stderr and returns 0. REPL exit is never blocked.
- Missing `ctx.provider` or `ctx.model` → stderr one-liner + return 0.
- `interactive = sys.stdin.isatty()` so piped sessions (CI, `voss do …`) take the non-interactive branch automatically; explicit `ctx.persist_conventions_selection` overrides via plumbed kwarg.

## Wire Points

- `voss/harness/cli.py::ReplContext` — added `memory_store`, `model`, `persist_conventions_selection` fields.
- `voss/harness/cli.py::_run_repl` — `MemoryStore(cwd).bind(session_id=record.id)` attached to ctx at boot.
- `voss/harness/cli.py::_run_repl` EOFError/KeyboardInterrupt branch — `conventions.run_on_clean_exit(ctx, history=ctx.history, record=record, memory_store=ctx.memory_store)` wrapped in try/except so a thrown exception still allows the REPL to return.
- `voss/harness/cli.py::do_cmd` — pinned locals `do_cwd / do_provider / do_model / do_record / do_history / do_memory_store` + `do_ctx = SimpleNamespace(...)`. Hook fires after `result.run` is appended to `do_record.runs` so has_signal's repeat-edit detection sees the just-completed run; before any disk persistence so a side-effect cannot race.
- `do_cmd` now builds a `SessionRecord` and `EpisodicMemory` locally and threads `history=do_history` + `session_id=do_record.id` into `run_turn` (parity with `_run_repl`).

## Tests (6 — all GREEN)

| Test | Coverage |
|------|----------|
| `test_scripted_signal_session_surfaces_candidate` | has_signal True + extract_conventions parses JSON array → 1 ConventionCandidate |
| `test_decline_writes_nothing` | `review_candidates(..., interactive=False, selection=None) == []` |
| `test_accept_writes_one_file_with_evidence` | `MemoryStore.write_convention` lands frontmatter (`related_session`, `evidence_turn_idx`, `confidence`) + body (statement + Evidence + verbatim quote) |
| `test_no_signal_skips_llm_entirely` | 1 user turn + no signal → `has_signal` False; gate prevents LLM call |
| `test_run_on_clean_exit_smoke` | Full pipeline: AsyncMock provider → run_on_clean_exit → exactly 1 file under `.voss/memory/conventions/` |
| `test_extraction_timeout_returns_empty` | `asyncio.wait_for(timeout=0.1)` vs `sleep(2.0)` → `[]` (no exception) |

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `pytest tests/harness/test_conventions.py -x` | 6 passed |
| `grep -v '^#' voss/harness/conventions.py | grep -c "NotImplementedError"` | 0 |
| `grep -nc "conventions.run_on_clean_exit" voss/harness/cli.py` | 2 (REPL + do_cmd) |
| `grep -nE "do_record|do_history|do_memory_store" voss/harness/cli.py` | 10 (pinned-names invariant) |
| `python -c "...inspect.signature(run_on_clean_exit).parameters has 'memory_store'"` | passes |
| Full harness suite (excl. pre-existing diagnostics failures) | 273 passed, 15 skipped |

## Pitfall 5 Mitigation Recap

| Mitigation | Mechanism |
|------------|-----------|
| Tightened quorum | has_signal requires `≥2 user turns AND signal match` for path (a); `≥2 runs sharing a changed file` for path (b) |
| Hard timeout | `asyncio.wait_for(provider.complete(...), timeout=8.0)` |
| Non-interactive default to "persist none" | `review_candidates(..., interactive=False, selection=None) → []` |
| Config-driven kill-switch | `memory.extract_conventions: false` in `.voss/config.yml` short-circuits run_on_clean_exit |

## Deviations from Plan

1. **`history.add` signature.** Plan example uses `history.add("user", "...")` positional ordering, but the real `EpisodicMemory.add(content, *, role="user")` takes content first with role keyword-only. Tests use the correct signature `history.add("...", role="user")`.

2. **`do_cmd` constructs `SessionRecord` + `EpisodicMemory` locally.** Plan assumed M8-01/M8-03 had already wired these locals in `do_cmd`; they had not. This plan adds the construction inline so the M8-04 hook can fire. Pinned local names (`do_cwd / do_provider / do_model / do_record / do_history / do_memory_store`) match the plan's instructions verbatim.

3. **`_turn_role` / `_turn_content` private helpers** added to `conventions.py` so has_signal accepts both `Turn` objects (production) and dicts (plan acceptance gate). The plan's behavior section names Turn as the typed contract but the acceptance gate at the bottom passes dicts — duck-typing satisfies both.

No other deviations.
