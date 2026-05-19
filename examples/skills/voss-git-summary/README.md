# voss-git-summary

A read-only Voss skill that provides an agentic summary of the git status and git diff in the current working directory. It analyzes modified files and staged/unstaged changes, generating a concise, readable developer update on current progress.

> [!WARNING]
> **SECURITY NOTE**: The committed `test_signing_key` is a CI fixture key with no production value; it is strictly used to sign this test example bundle in a secure and reproducible manner.
>
> Scope confinement is gate-level only — direct Python `open()`, `urllib`, or similar operations executed inside the `.voss` subprocess itself are NOT sandboxed (OS-level sandboxing is deferred).

## Permissions
- **Tools**: `read-only`
- **Filesystem**: `cwd`
- **Network**: `False`
