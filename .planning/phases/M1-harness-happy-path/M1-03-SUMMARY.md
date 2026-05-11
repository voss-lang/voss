---
phase: M1-harness-happy-path
plan: 03
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/session.py (docstring rewrite)
  - tests/harness/test_session_redaction.py (new)
tests_added: 5
tests_total_passing: 117
---

# M1-03 Summary: Session Redaction Guarantee

## What shipped

### `voss/harness/session.py` docstring

Module docstring now explicitly states the redaction guarantee, names what's
in the allowlist (the 8 SessionRecord fields), notes the user-prompt
passthrough nuance, and points future readers at the build-time test.

### `tests/harness/test_session_redaction.py` (new)

Five tests across three classes lock the D-17 contract:

| Class                            | Test                                              | What it locks |
|----------------------------------|---------------------------------------------------|---------------|
| `TestSchemaAllowlist`            | `test_saved_json_has_exactly_schema_keys`         | Only the 8 SessionRecord fields appear at top level. Any new field fails the test. |
| `TestSchemaAllowlist`            | `test_no_credentials_keys_at_top_level`           | None of `access_token`, `refresh_token`, `api_key`, `Authorization`, `anthropic-beta`, `oauth_token`, `credentials`, `provider`, `headers` show up as JSON keys. |
| `TestSchemaAllowlist`            | `test_secret_patterns_absent_from_clean_session`  | None of `sk-ant-`, `sk-proj-`, `Bearer `, `oauth_token`, `access_token`, `Authorization` show up in the serialized text on a clean session. |
| `TestUserPromptsArePassthrough`  | `test_user_prompt_with_secret_shape_is_preserved` | User-typed `sk-test-DEADBEEF` stays in the transcript — guarantee is about harness-attached fields, not prompt content. |
| `TestDocstringFreezesGuarantee`  | `test_module_docstring_mentions_redaction_guarantee` | "Redaction guarantee" string stays in the docstring so future readers see the invariant. |

### Manual regression validation

Inserted `headers: dict = field(default_factory=lambda: {"Authorization": "Bearer foo"})`
into `SessionRecord`. Test correctly FAILED with:
```
E   AssertionError: ...extra item: 'headers'
```
Reverted; tests green again. The contract is observable, not just structural.

## Verification

- `pytest tests/harness/test_session_redaction.py tests/harness/test_session.py -x` — 11 passed.
- Full harness suite: `pytest tests/harness/` — 117 passed (up from 112).

## M2 handoff

When storage path moves from `~/.local/state/voss/sessions/` to
`.voss/sessions/` (M2):

1. Update the module docstring final paragraph to point at the new location.
2. The `state_dir` test fixture uses `XDG_STATE_HOME` override, which keeps
   working unchanged as long as `_state_dir()` still honors that env var. If
   M2 switches to a project-rooted `.voss/sessions/`, repoint the fixture
   to set the cwd-anchored override (or pass `cwd` into a new
   `session.save(..., root=cwd)` if the API changes).
3. None of the assertion content needs to change — it's all about JSON
   shape, not storage path.

## Decisions implemented

- **D-16** schema allowlist = redaction mechanism — docstring + test.
- **D-17** specific patterns scanned: 6 creds-shaped strings.
- **D-18** no re-auth at save time — preserved (save still calls only
  `history.last(...)` + `json.dumps`, no provider calls).

## Requirements covered

CTRL-09.
