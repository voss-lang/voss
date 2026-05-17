# Cache Integration Cassettes

This directory holds vcrpy YAML cassettes for `tests/harness/test_cache_integration.py`.

Re-record live Anthropic fixtures with:

```bash
VOSS_RECORD=1 ANTHROPIC_API_KEY=... python3 -m pytest tests/harness/test_cache_integration.py -x
```

Cassette recording must use `filter_headers` for:

- `x-api-key`
- `authorization`
- `anthropic-api-key`
- `cookie`
- `set-cookie`

CI is replay-only. `record_mode='none'` raises on a missing cassette by design; that is the signal to re-record and commit the cassette.
