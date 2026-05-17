# T3-09 Summary: CI + Eval Network Surface

## Outcome

Implemented the final T3 network-surface verification layer:

- Added `.github/workflows/mcp-integration.yml`.
- Added eval golden task `tests/eval/golden/06-fetch-summarize/`.
- Extended eval task specs with `tools = [...]`.
- Added hermetic `httpx.MockTransport` injection for stub `web_fetch` eval tasks.
- Added `tests/harness/test_eval_task_6_stub.py`.
- Added explicit MCP client process cleanup used by `voss mcp list` and `voss mcp call`.
- Added `StubProvider.stream()` so `voss eval --stub` completes turns instead of recording an `AttributeError`.

The plan referenced `voss/harness/eval.py`, but the actual M5 eval runner in this codebase is `voss/eval/runner.py`; the implementation landed there.

## Checkpoint Resolution

Pinned npm package:

```text
@modelcontextprotocol/server-filesystem@2026.1.14
```

Pinned read tool:

```text
read_text_file
```

Probe result against the pinned package:

```text
INIT: protocolVersion 2025-11-25 accepted
TOOL: read_file
TOOL: read_text_file
TOOL: read_media_file
TOOL: read_multiple_files
TOOL: write_file
TOOL: edit_file
TOOL: create_directory
TOOL: list_directory
TOOL: list_directory_with_sizes
TOOL: directory_tree
TOOL: move_file
TOOL: search_files
TOOL: get_file_info
TOOL: list_allowed_directories
```

`read_file` is still advertised, but deprecated by the server. `read_text_file` is the current text-read surface and accepts `path` plus optional `head`/`tail`.

## Verification

Commands run:

```text
uv run pytest tests/harness/test_eval_task_6_stub.py -x -q
uv run pytest tests/harness/test_cli_mcp.py -x -q
uv run pytest tests/eval/test_task_spec.py tests/eval/test_suite_loads.py tests/eval/test_voss_eval_stub.py -q
uv run pytest tests/harness/test_cli_mcp.py tests/harness/mcp/ tests/harness/test_eval_task_6_stub.py -x -q
uv run python -m py_compile voss/eval/runner.py voss/eval/suite.py voss/harness/cli.py voss/harness/mcp/client.py voss_runtime/providers/stub.py
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/mcp-integration.yml')); print('YAML OK')"
git diff --check
```

Results:

```text
tests/harness/test_eval_task_6_stub.py: 1 passed
tests/harness/test_cli_mcp.py: 10 passed
tests/eval/test_task_spec.py tests/eval/test_suite_loads.py tests/eval/test_voss_eval_stub.py: 18 passed
tests/harness/test_cli_mcp.py tests/harness/mcp/ tests/harness/test_eval_task_6_stub.py: 24 passed
YAML OK
git diff --check: clean
```

Local real-server MCP smoke:

```text
voss mcp list --cwd <tmp>: exit 0
voss mcp call filesystem read_text_file --arg "path=./README.md" --cwd <tmp>: exit 0
output contained "# Voss"
```

Task 06 stub smoke:

```text
voss eval --stub --auth none --task 06-fetch-summarize -k 1: exit 0
runs.jsonl row task_id: 06-fetch-summarize
success: null
judge_verdict: skipped
```

GitHub Actions run link: pending until the next push/PR executes `mcp-integration`.
