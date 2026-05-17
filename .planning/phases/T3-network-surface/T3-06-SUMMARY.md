# T3-06 Summary

Date: 2026-05-17

## What Landed

- Added `voss/harness/web_search.py` with `SearchResult`, `BraveBackend`, and `render_bundle`.
- Extended `NetSession.search(query, count)` in `voss/harness/net.py:175`.
- Registered the `web_search` tool in `voss/harness/tools.py:342` as `is_mutating=False` and `is_network=True`.
- Replaced the NET-02 skip scaffold in `tests/harness/test_web_search.py` with six MockTransport tests.
- Updated the tool registry count test for the new non-mutating network tool.

## BraveBackend API

Public surface:

```python
@dataclass
class SearchResult:
    title: str
    url: str
    description: str

class BraveBackend:
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, *, client: httpx.AsyncClient | None = None) -> None:
        ...

    async def search(self, query: str, count: int) -> list[SearchResult] | str:
        ...
```

`BraveBackend.search` issues `GET https://api.search.brave.com/res/v1/web/search` with `X-Subscription-Token` and params `q` and `count`.

## render_bundle Sample

```text
1. Title 0
   https://example.com/0
   Desc 0

2. Title 1
   https://example.com/1
   Desc 1

3. Title 2
   https://example.com/2
   Desc 2
```

## NetSession.search

Line references:

- `voss/harness/net.py:175` starts `NetSession.search`.
- `voss/harness/net.py:177` reads `BRAVE_SEARCH_API_KEY` at call time.
- `voss/harness/net.py:181` applies the `web_search` token bucket.
- `voss/harness/net.py:185` clamps `count` to `[1, 20]` with `RuntimeWarning`.
- `voss/harness/net.py:194` constructs `BraveBackend(api_key, client=self._http())`, satisfying the D-05 shared `httpx.AsyncClient` invariant.
- `voss/harness/net.py:209` deduplicates results by URL with first occurrence winning.

`web_search` now shares the same `httpx.AsyncClient` connection pool as `web_fetch` through `NetSession._http()`.

## Verification

```text
$ uv run pytest tests/harness/test_web_search.py -x -q
......                                                                   [100%]
```

```text
$ uv run pytest tests/harness/test_web_fetch.py tests/harness/test_web_search.py tests/harness/test_rate_limit.py tests/harness/test_allow_net.py -x -q
..............................                                           [100%]
```

```text
$ uv run pytest tests/harness/test_tools.py::TestToolEntryClassification::test_mutating_count -q
.                                                                        [100%]
```

```text
$ uv run pytest tests/harness -x -q
passed on rerun; first broad run exposed the stale tool registry count, which was updated.
```

Additional checks:

- `uv run pytest tests/harness/test_web_search.py --collect-only -q` collected 6 tests.
- `grep -c "pytest.skip" tests/harness/test_web_search.py` returned 0.
- `uv run python -m py_compile voss/harness/web_search.py voss/harness/net.py voss/harness/tools.py tests/harness/test_web_search.py` passed.
- `git diff --check -- voss/harness/web_search.py voss/harness/net.py voss/harness/tools.py tests/harness/test_web_search.py` passed.
