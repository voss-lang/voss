# code-recall-ab

Thirty tasks for the J3 paired A/B (rerank `off` vs `active`, D-14..D-16). Every task runs on
the pinned Voss commit `c1a27046` (`corpus = "pinned"`) and has one deterministic `cmd` check.
`recall` is left unset; the A/B run overrides it per side.

- Split: 15 answer tasks (cite a location) and 15 edit tasks (change one behavior, verified by a test).
- Answer tasks: the check greps `.voss-eval-final.txt` for `path:line` inside the defining range at the
  pinned commit. The expected answer is in `reference.txt`.
- Edit tasks: the test is inlined in the cmd check as a heredoc, written to a temp dir outside the
  run tree at check time, and run with the eval Python. Nothing the agent can see names the module
  to edit. The test fails on the untouched tree and passes after `git apply reference.patch`.
- Topics come only from dev-split query groups; `SOURCES.json` maps each task to its group, and
  `tests/eval/test_rerank_suite.py` fails if any mapped group is not dev-only.

## Permission modes

- Answer tasks use `mode = "edit"` without `auto_approve_edits`. In `plan` mode every tool outside
  `READ_ONLY` (fs_read, fs_glob, fs_grep, git_status, git_diff, voss_check) prompts, and a
  non-interactive prompt is denied, so `code_search` and `code_recall` would be refused. `edit`
  runs non-mutating tools without prompting, while writes still prompt and are denied
  non-interactively. It is the least-privileged `TaskSpec` mode where all three tools run.
- Edit tasks use `mode = "edit"` with `auto_approve_edits = true`.

## Tasks

| Task | Kind | Prompt | Check | Source group |
|------|------|--------|-------|--------------|
| 01-step-batches | answer | When the agent executes a multi-step plan, some tool calls run concurrently and others run one at a time. Where does Voss decide which plan steps get grouped into a concurrent batch? | `grep -Eq 'voss/harness/agent\.py:(1699\|17[0-5][0-9])([^0-9]\|$)' .voss-eval-final.txt` | b01-g014 |
| 02-max-iter-final | answer | When a turn runs out of iterations, what final message does the user get, and where is it defined? | `grep -Eq '(voss/harness/agent\.py:(38[5-9])\|voss/harness/agent\.py:(122[0-4]))([^0-9]\|$)' .voss-eval-final.txt` | b01-g023 |
| 03-context-watermarks | answer | When the agent's replayed context gets close to its packing budget, where is the logic that decides between keeping the frozen prefix and re-folding older iterations? I was told it uses some kind of hysteresis. | `grep -Eq 'voss/harness/context_allocator\.py:(17[5-9]\|1[8-9][0-9]\|2[0-1][0-9]\|22[0-6])([^0-9]\|$)' .voss-eval-final.txt` | b01-g026 |
| 04-memory-lock-busy | answer | If two Voss processes write project memory at the same time, what happens to the write that cannot get the lock? Show me where that is handled. | `grep -Eq 'voss/harness/memory_store\.py:(19[4-9]\|20[0-9]\|210)([^0-9]\|$)' .voss-eval-final.txt` | b01-g035 |
| 05-background-watchdog | answer | A background shell job that hangs without printing anything eventually gets killed. Where is that enforced? | `grep -Eq 'voss/harness/lifecycle\.py:(22[6-9]\|2[3-8][0-9])([^0-9]\|$)' .voss-eval-final.txt` | b02-g013 |
| 06-mcp-oversized-line | answer | When Voss runs as an MCP server over stdio and a client sends one enormous request line, how does the server respond, and where is that handled? | `grep -Eq '(voss/harness/mcp/server\.py:(5[1-9]\|[6-8][0-9]\|9[0-7])\|voss/harness/mcp/server\.py:(21[4-9]\|22[0-9]\|23[0-1]))([^0-9]\|$)' .voss-eval-final.txt` | b02-g020 |
| 07-bearer-asgi | answer | How does `voss serve` check the bearer token without breaking server-sent event streams? Point me to the implementation. | `grep -Eq 'voss/harness/server/app\.py:(7[6-9]\|[8-9][0-9]\|10[0-1])([^0-9]\|$)' .voss-eval-final.txt` | b02-g036 |
| 08-event-queue-drop | answer | In the HTTP server, what happens to session events when the client is slow and the event queue fills up? Where is that code? | `grep -Eq 'voss/harness/server/renderer\.py:(5[8-9]\|[6-7][0-9]\|8[0-5])([^0-9]\|$)' .voss-eval-final.txt` | b02-g038 |
| 09-oauth-writeback | answer | After Voss refreshes a Claude subscription login token, where does it save the new token, and where is that logic? | `grep -Eq 'voss/harness/auth\.py:(18[6-9]\|19[0-9]\|2[0-2][0-9]\|23[0-1])([^0-9]\|$)' .voss-eval-final.txt` | b02-g027 |
| 10-implicit-ctx-scope | answer | If a .voss program calls ask(...) outside any ctx block, what token budget does the compiled Python get, and where does the compiler decide that? | `grep -Eq 'voss/codegen\.py:(117[5-9]\|118[0-9]\|119[0-1])([^0-9]\|$)' .voss-eval-final.txt` | b03-g020 |
| 11-board-wip | answer | Moving a card into a full column on the team board fails. Where is that check, and what does the board record about the refused move? | `grep -Eq 'voss/harness/board/machine\.py:(42[2-9]\|43[0-9]\|44[0-5])([^0-9]\|$)' .voss-eval-final.txt` | b04-g001 |
| 12-gate-dry-run | answer | Is there a way to check whether a card would pass a board gate without actually moving it or recording a transition? Where is it? | `grep -Eq 'voss/harness/board/machine\.py:(56[5-9]\|5[7-9][0-9]\|60[0-9]\|61[0-5])([^0-9]\|$)' .voss-eval-final.txt` | b04-g010 |
| 13-go-word-diff | answer | The Go TUI shows a word-level diff on edit tool cards. What stops that diff from blowing up on large edits, and where is it? | `grep -Eq 'tui/diff\.go:(1[7-9]\|[2-7][0-9])([^0-9]\|$)' .voss-eval-final.txt` | b04-g041 |
| 14-rust-status-line | answer | In the Rust renderer, where is the end-of-turn status line built (the line with the token count, cost and context percent)? | `grep -Eq '(crates/voss-render/src/status_line\.rs:(1[1-9]\|[2-3][0-9]\|4[0-2])\|crates/voss-render/src/status_line\.rs:(5[2-9]\|6[0-3]))([^0-9]\|$)' .voss-eval-final.txt` | b04-g046 |
| 15-ts-handshake | answer | The TypeScript SDK launches `voss serve` and reads a handshake line before connecting. Where is that handshake read and validated? | `grep -Eq 'sdk/typescript/src/launcher/launcher\.ts:(10[5-9]\|1[1-6][0-9]\|17[0-2])([^0-9]\|$)' .voss-eval-final.txt` | b04-g043 |
| 16-tokenize-acronyms | edit | Lexical memory recall cannot match `HTTPServer` when I search for "server": a run of capitals followed by a capitalized word stays glued together when text is tokenized for BM25. Make `HTTPServer` tokenize as `http`, `server` (and `parseJSONResponse` as `parse`, `json`, `response`) without changing how ordinary camelCase and snake_case text is split. | inline pytest of test_tokenize_acronyms.py (heredoc in task.toml) | b01-g002 |
| 17-fractional-token-budget | edit | A .voss program with `ctx(budget: 1.5k tokens)` fails to parse. Support fractional token budgets with a k or M suffix (1.5k tokens = 1500, 2.5M tokens = 2500000). Whole-number budgets like `200k tokens` and `4000 tokens` must keep working. | inline pytest of test_fractional_token_budget.py (heredoc in task.toml) | b03-g001 |
| 18-mcp-env-default | edit | MCP server commands in .voss/mcp.yml can reference `${VAR}`, but there is no way to give a fallback. Support `${VAR:-default}`: use the default when VAR is unset, use VAR when it is set, and keep failing on a plain `${VAR}` that is unset. | inline pytest of test_mcp_env_default.py (heredoc in task.toml) | b02-g018 |
| 19-correlation-capped | edit | The eval summary's plan-confidence vs task-success correlation (and its n) includes runs that hit the iteration cap. Leave out rows where `capped` is true when computing that correlation. | inline pytest of test_correlation_capped.py (heredoc in task.toml) | b04-g034 |
| 20-mcp-destructive-hint | edit | If an MCP server marks a tool with both `readOnlyHint: true` and `destructiveHint: true`, Voss treats it as read-only. Contradictory annotations should fail safe: `destructiveHint: true` must make the tool mutating. Other cases stay as they are. | inline pytest of test_mcp_destructive_hint.py (heredoc in task.toml) | b02-g017 |
| 21-skill-github-prefix | edit | Let `voss skill add` accept an explicit `github:owner/repo` source, cloning the same URL as the bare `owner/repo` shorthand. A `github:` value that is not a valid owner/repo should be rejected with a ValueError. | inline pytest of test_skill_github_prefix.py (heredoc in task.toml) | b02-g024 |
| 22-session-exact-match | edit | Resuming a saved session by its full id fails with an "ambiguous session id" error when another session id starts with the same characters. An exact id or exact name match should win over prefix matches; a prefix that matches several sessions should still be ambiguous. | inline pytest of test_session_exact_match.py (heredoc in task.toml) | b01-g042 |
| 23-walk-skip-hidden | edit | When the code index has to walk the filesystem because the project is not a git repo, it descends into hidden directories such as `.tox` or `.idea` and indexes their files. Skip directories whose names start with a dot in that fallback. Hidden files at the top level can stay. | inline pytest of test_walk_skip_hidden.py (heredoc in task.toml) | b01-g004 |
| 24-anchor-case | edit | Hashline edits fail with "anchor not found" when the model sends the line anchor in uppercase or with stray spaces around it. Accept anchors case-insensitively and ignore surrounding whitespace. | inline pytest of test_anchor_case.py (heredoc in task.toml) | b02-g001 |
| 25-calibration-skipped | edit | Reviewer calibration counts review sidecars where reviewer B was skipped (verdict "skipped") toward the false-pass pairs and the slop-rejection denominator. Treat a skipped B verdict as no B verdict. | inline pytest of test_calibration_skipped.py (heredoc in task.toml) | b04-g028 |
| 26-swarm-log-corrupt | edit | Replaying a swarm event log silently stops at the first unparseable line, so a corrupt line in the middle drops every later event. Keep tolerating a torn final line, but raise a ValueError when an unparseable line is followed by more events. | inline pytest of test_swarm_log_corrupt.py (heredoc in task.toml) | b04-g023 |
| 27-gather-exceptions | edit | The runtime helper that waits on several spawned agent handles with a timeout turns every failure into None, so callers cannot tell a crash from a timeout. Add an opt-in `return_exceptions=True` flag: failed handles then come back as their exception, timed-out handles stay None, and the default behavior is unchanged. | inline pytest of test_gather_exceptions.py (heredoc in task.toml) | b03-g043 |
| 28-overlap-dotdot | edit | Two swarm tasks can both own the same file if one spells the path with `..` segments (for example `src/util/../app.py` and `src/app.py`), because the ownership overlap check misses it. Make the check treat those as the same file; tasks ordered by depends_on may still share it. | inline pytest of test_overlap_dotdot.py (heredoc in task.toml) | b04-g016 |
| 29-rate-per-second | edit | Writing `web_fetch = "2/s"` under `[net.rate_limits]` in config.toml is silently ignored. Accept a per-second string form and convert it to the per-minute rate (2/s becomes rate 120, burst 120). The `"60/min"` form and the inline-table form must keep working. | inline pytest of test_rate_per_second.py (heredoc in task.toml) | b02-g031 |
| 30-split-long-line | edit | Code chunking for the semantic index leaves a single very long line (minified JS, a giant literal) as one oversize chunk that the embedding model silently truncates. When one line is longer than the chunk size limit, split it into limit-sized pieces that all keep that line number. Splitting of multi-line regions should stay as it is. | inline pytest of test_split_long_line.py (heredoc in task.toml) | b01-g038 |

## How to approve

1. Skim each prompt: it should read like a real request and must not name the answer.
2. Spot-check a few tasks: open `task.toml` with `reference.txt` or `reference.patch` and confirm the
   check accepts the right answer and nothing broader.
3. Confirm the 15/15 answer/edit split.
4. Reply "approved", or list task ids to drop or rewrite.
