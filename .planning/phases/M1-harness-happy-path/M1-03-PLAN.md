---
phase: M1-harness-happy-path
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/session.py
  - tests/harness/test_session_redaction.py
autonomous: true
requirements:
  - CTRL-09
tags:
  - harness
  - session
  - security

must_haves:
  truths:
    - "Session JSON files never contain provider API keys, OAuth tokens, or Bearer headers."
    - "A CI test asserts secret patterns are absent from a saved session that was fed synthetic secrets."
    - "The redaction guarantee is documented in the session module docstring."
  artifacts:
    - path: "voss/harness/session.py"
      provides: "SessionRecord schema allowlist + module docstring stating the redaction invariant"
      contains: "Redaction guarantee"
    - path: "tests/harness/test_session_redaction.py"
      provides: "Pattern-scan test over a saved JSON containing synthetic secrets"
  key_links:
    - from: "tests/harness/test_session_redaction.py"
      to: "voss/harness/session.py::save"
      via: "save(record, history) then read file + regex scan"
      pattern: "Bearer \\|sk-\\|oauth_\\|anthropic-beta\\|api_key\\|Authorization"
---

<objective>
Freeze the redaction guarantee for `SessionRecord` with a CI test that fails if any known secret pattern leaks into the saved JSON.

Purpose: D-16 says redaction is enforced by **schema allowlist** — `SessionRecord` has fixed fields and nothing else gets serialized. Today that invariant is true by structure but unprotected by any test. A future refactor that adds a free-form field (e.g. "raw_response") would silently regress. This plan adds the build-time check that locks the contract. Covers CTRL-09.

Output:
- `tests/harness/test_session_redaction.py` runs a synthetic turn whose context contains `sk-test-...`, `Bearer test-...`, and `anthropic-beta` headers, calls `session.save(...)`, then scans the resulting file for `Authorization`, `Bearer `, `sk-`, `oauth_`, `anthropic-beta`, `api_key`. Fails on any hit.
- `voss/harness/session.py` module docstring updated to explicitly state: "Redaction guarantee = SessionRecord schema allowlist. No field outside the dataclass is serialized."
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M1-harness-happy-path/M1-CONTEXT.md
@voss/harness/session.py
@tests/harness/test_session.py

<interfaces>
SessionRecord fields (voss/harness/session.py):
    id, name, cwd, model, started_at, updated_at, total_cost_usd, turns

save(record, history) -> Path  # writes JSON via asdict(record); chmod 600

EpisodicMemory.add(content: str, role: str) — used to populate history.
EpisodicMemory.last(n) returns list of {"role": ..., "content": ...} dicts.

Note: SessionRecord.turns gets populated from history.last(10_000) at save time.
The redaction risk vector is therefore: anything that ends up in turn[]["content"]
or any new SessionRecord field someone adds in the future. The schema allowlist
in asdict(record) is the structural guarantee; the test makes it observable.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add session redaction test and document the guarantee</name>
  <files>tests/harness/test_session_redaction.py, voss/harness/session.py</files>
  <read_first>
    - voss/harness/session.py (entire file — 113 LOC, full save path)
    - tests/harness/test_session.py (existing test patterns to mirror)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-15..D-18, especially D-17)
  </read_first>
  <behavior>
    - Test 1: Build an `EpisodicMemory`, add a user turn whose content is "normal task" (no secrets) and an assistant turn whose content is also clean. Save via `session.save(record, history)`. Read the JSON file. Assert NONE of the six secret patterns appear. (Sanity: control passes.)
    - Test 2: Build an `EpisodicMemory`, add a user turn whose content includes:
        - `sk-test-DEADBEEF`
        - `Bearer test-AAAA-BBBB`
        - `anthropic-beta: oauth-2025-04-20`
        - `"api_key": "secret"`
        - `"Authorization": "Bearer foo"`
        - `"oauth_token": "bar"`
      Save. Read the JSON. Assert each pattern IS PRESENT in the JSON (because EpisodicMemory.content is part of the allowlist and gets serialized verbatim — this is **intended**; the user can write secrets into their own prompt). This test exists to make a separate point: the **provider creds** are what we must not leak.
    - Test 3 (the actual contract): Build a `SessionRecord` with a fresh `EpisodicMemory`, call `session.save(record, history)`, then verify the only top-level JSON keys are exactly: `{"id", "name", "cwd", "model", "started_at", "updated_at", "total_cost_usd", "turns"}`. No extra keys. No "headers", "credentials", "provider", "api_key", "access_token" fields at top level.
    - Test 4 (the secret-pattern scan): Construct a `SessionRecord` directly + an `EpisodicMemory` with clean content. Save. Read JSON as text. Assert these six patterns do NOT appear in the JSON: `Authorization`, `Bearer `, `sk-ant-`, `sk-proj-`, `oauth_token`, `access_token`. (These are creds-shaped patterns the harness would never put into transcripts — if any of them shows up, the schema allowlist has been broken.) `sk-` is too broad (matches "sk-test-DEADBEEF" in user prompts), so the test uses the more specific `sk-ant-` and `sk-proj-` prefixes that Anthropic/OpenAI actually use.
    - Test 5: Verify `voss/harness/session.py` module docstring contains the string "Redaction guarantee" — locks the documentation in place.
  </behavior>
  <action>
1. Update `voss/harness/session.py` module docstring (top of file). Replace the current docstring with:
```python
"""Persisted session snapshots.

Sessions live at $XDG_STATE_HOME/voss/sessions/<id>.json (default
~/.local/state/voss/sessions). Each snapshot stores the episodic transcript,
cwd, model, and total cost.

Redaction guarantee
-------------------
SessionRecord is a fixed-field dataclass. Save serializes via dataclasses.asdict,
which means nothing outside the schema gets written. Provider credentials
(API keys, OAuth access/refresh tokens, Bearer headers, anthropic-beta marker)
are NEVER fields on this record and therefore cannot be saved.

User-provided prompt text is allowed to contain anything — including strings
that look like secrets — because EpisodicMemory.content is part of the
allowlist by design (the user typed it). The guarantee is specifically about
what the harness itself attaches to the record (it attaches nothing
secret-shaped).

This invariant is enforced at build time by tests/harness/test_session_redaction.py.
Adding a new SessionRecord field that could carry creds is a breaking change
and must be paired with an explicit redaction step.

Storage location stays at ~/.local/state/voss/sessions/ for M1.
The move to .voss/sessions/ happens in M2.
"""
```

2. Create `tests/harness/test_session_redaction.py`:
```python
"""Lock the SessionRecord redaction guarantee (D-17).

If a future change adds a SessionRecord field that holds provider creds or
adds a serialization path that bypasses the dataclass, these tests fail.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from voss_runtime import EpisodicMemory

from voss.harness import session as session_store


@pytest.fixture
def state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path / "state" / "voss" / "sessions"


class TestSchemaAllowlist:
    def test_saved_json_has_exactly_schema_keys(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        history.add("hello", role="user")
        path = session_store.save(record, history)
        data = json.loads(path.read_text())
        expected = {"id", "name", "cwd", "model", "started_at", "updated_at",
                    "total_cost_usd", "turns"}
        assert set(data.keys()) == expected

    def test_no_credentials_keys_at_top_level(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        path = session_store.save(record, history)
        text = path.read_text()
        forbidden_top_level_keys = (
            '"access_token"', '"refresh_token"', '"api_key"',
            '"Authorization"', '"anthropic-beta"', '"oauth_token"',
            '"credentials"', '"provider"', '"headers"',
        )
        for key in forbidden_top_level_keys:
            assert key not in text, f"forbidden key present: {key}"

    def test_secret_patterns_absent_from_clean_session(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        history.add("summarize this repo", role="user")
        history.add("the repo is a Python harness.", role="assistant")
        path = session_store.save(record, history)
        text = path.read_text()
        # These are creds-shaped patterns the harness itself would never put
        # in a transcript. Their presence means the schema allowlist broke.
        secret_patterns = ("sk-ant-", "sk-proj-", "Bearer ",
                           "oauth_token", "access_token", "Authorization")
        for pat in secret_patterns:
            assert pat not in text, f"secret pattern leaked: {pat!r}"


class TestUserPromptsArePassthrough:
    """User prompt content is intentionally not redacted — the user typed it."""

    def test_user_prompt_with_secret_shape_is_preserved(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        history.add("debug this: my key was sk-test-DEADBEEF", role="user")
        path = session_store.save(record, history)
        text = path.read_text()
        assert "sk-test-DEADBEEF" in text  # the user typed it; we preserve it


class TestDocstringFreezesGuarantee:
    def test_module_docstring_mentions_redaction_guarantee(self):
        assert "Redaction guarantee" in session_store.__doc__
```

3. Run `pytest tests/harness/test_session_redaction.py tests/harness/test_session.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_session_redaction.py tests/harness/test_session.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/test_session_redaction.py` exists.
    - `grep -c "Redaction guarantee" voss/harness/session.py` returns at least 1.
    - `grep -c "class TestSchemaAllowlist" tests/harness/test_session_redaction.py` returns 1.
    - `grep -c "class TestUserPromptsArePassthrough" tests/harness/test_session_redaction.py` returns 1.
    - `grep -c "class TestDocstringFreezesGuarantee" tests/harness/test_session_redaction.py` returns 1.
    - `pytest tests/harness/test_session_redaction.py -x` exits 0.
    - `pytest tests/harness/test_session.py -x` still exits 0 (no regression).
  </acceptance_criteria>
  <done>Redaction test in place; module docstring locks the guarantee; both existing and new session tests pass.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_session_redaction.py tests/harness/test_session.py -x` exits 0.
- Manual: edit `voss/harness/session.py` to add `headers: dict = field(default_factory=dict)` to SessionRecord, populate it with `{"Authorization": "Bearer foo"}`, run the redaction test, confirm it FAILS. Revert the edit.
</verification>

<success_criteria>
- Schema allowlist invariant is testable, not just structural (D-16).
- Test covers all six secret patterns from D-17 (Authorization, Bearer, sk- variants, oauth, access_token, api_key — with the nuance that user-typed `sk-test-...` is allowed in prompts).
- The redaction guarantee is documented in the module docstring so future readers see it before changing the schema (D-16).
- Storage path unchanged in M1 (D-15) — no new dirs introduced.
- No re-authentication side effects at save time (D-18 preserved).
</success_criteria>

<output>
After completion, create `.planning/phases/M1-harness-happy-path/M1-03-SUMMARY.md` documenting the schema allowlist, the test surface, and the M2 handoff (when storage moves to `.voss/sessions/`, the same tests must be re-pointed at the new location).
</output>
