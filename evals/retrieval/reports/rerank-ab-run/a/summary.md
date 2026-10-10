# voss eval — a

- runs: 30
- provider: `ClaudeAgentProvider` · model: `claude-sonnet-5-5`
- overall success rate: 0% (0/1)
- gate pass rate: 97% (29/30)
- judge pass rate: n/a (0/0)
- mean cost: n/a
- mean wasted calls: 0.9
- conf_corr_r: n/a (n=0)

## Per-task

| task | runs | gate pass | pass rate | mean cost | mean wasted |
|------|-----:|----------:|----------:|----------:|------------:|
| `01-step-batches` | 1 | 100% | n/a | n/a | 0.0 |
| `02-max-iter-final` | 1 | 100% | n/a | n/a | 0.0 |
| `03-context-watermarks` | 1 | 100% | n/a | n/a | 0.0 |
| `04-memory-lock-busy` | 1 | 100% | n/a | n/a | 0.0 |
| `05-background-watchdog` | 1 | 0% | 0% | n/a | 0.0 |
| `06-mcp-oversized-line` | 1 | 100% | n/a | n/a | 0.0 |
| `07-bearer-asgi` | 1 | 100% | n/a | n/a | 0.0 |
| `08-event-queue-drop` | 1 | 100% | n/a | n/a | 0.0 |
| `09-oauth-writeback` | 1 | 100% | n/a | n/a | 0.0 |
| `10-implicit-ctx-scope` | 1 | 100% | n/a | n/a | 0.0 |
| `11-board-wip` | 1 | 100% | n/a | n/a | 0.0 |
| `12-gate-dry-run` | 1 | 100% | n/a | n/a | 0.0 |
| `13-go-word-diff` | 1 | 100% | n/a | n/a | 0.0 |
| `14-rust-status-line` | 1 | 100% | n/a | n/a | 0.0 |
| `15-ts-handshake` | 1 | 100% | n/a | n/a | 0.0 |
| `16-tokenize-acronyms` | 1 | 100% | n/a | n/a | 1.0 |
| `17-fractional-token-budget` | 1 | 100% | n/a | n/a | 4.0 |
| `18-mcp-env-default` | 1 | 100% | n/a | n/a | 1.0 |
| `19-correlation-capped` | 1 | 100% | n/a | n/a | 1.0 |
| `20-mcp-destructive-hint` | 1 | 100% | n/a | n/a | 1.0 |
| `21-skill-github-prefix` | 1 | 100% | n/a | n/a | 1.0 |
| `22-session-exact-match` | 1 | 100% | n/a | n/a | 2.0 |
| `23-walk-skip-hidden` | 1 | 100% | n/a | n/a | 1.0 |
| `24-anchor-case` | 1 | 100% | n/a | n/a | 1.0 |
| `25-calibration-skipped` | 1 | 100% | n/a | n/a | 2.0 |
| `26-swarm-log-corrupt` | 1 | 100% | n/a | n/a | 1.0 |
| `27-gather-exceptions` | 1 | 100% | n/a | n/a | 2.0 |
| `28-overlap-dotdot` | 1 | 100% | n/a | n/a | 3.0 |
| `29-rate-per-second` | 1 | 100% | n/a | n/a | 3.0 |
| `30-split-long-line` | 1 | 100% | n/a | n/a | 2.0 |
