"""Credential discovery for Claude Code (Anthropic) and Codex (OpenAI).

Order of preference (when --auth=auto):
  1. Explicit env vars (ANTHROPIC_API_KEY / OPENAI_API_KEY)
  2. Claude Code OAuth tokens (macOS Keychain or ~/.claude/.credentials.json)
  3. Codex auth.json (~/.codex/auth.json — uses bundled OPENAI_API_KEY)

For Claude Code OAuth: tokens auto-refresh via Anthropic's token endpoint.
The harness reuses Claude Code's published client_id; this is intended for
personal use and may break if Anthropic changes the protocol.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

CLAUDE_CODE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
ANTHROPIC_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
ANTHROPIC_API_BASE = "https://api.anthropic.com"
ANTHROPIC_OAUTH_BETA = "oauth-2025-04-20"

# Codex CLI client. Reused for refresh.
CODEX_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OPENAI_TOKEN_URL = "https://auth.openai.com/oauth/token"
OPENAI_API_BASE = "https://api.openai.com"
# ChatGPT subscription tokens reach the Responses API via chatgpt.com,
# not api.openai.com. The Codex CLI uses this endpoint for "ChatGPT" auth_mode.
CHATGPT_BACKEND_BASE = "https://chatgpt.com/backend-api/codex"


# ---------------------------------------------------------------------------
# Anthropic OAuth (Claude Code)
# ---------------------------------------------------------------------------


@dataclass
class AnthropicOAuthCreds:
    access_token: str
    refresh_token: str
    expires_at_ms: int
    subscription_type: str = ""

    @property
    def expired(self) -> bool:
        # Refresh proactively 60s before stated expiry.
        return time.time() * 1000 >= self.expires_at_ms - 60_000

    @property
    def expires_in_seconds(self) -> int:
        return max(0, int((self.expires_at_ms - time.time() * 1000) / 1000))


def _read_macos_keychain() -> Optional[dict]:
    if platform.system() != "Darwin":
        return None
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def _read_claude_credentials_file() -> Optional[dict]:
    path = Path.home() / ".claude" / ".credentials.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def load_anthropic_oauth() -> Optional[AnthropicOAuthCreds]:
    blob = _read_macos_keychain() or _read_claude_credentials_file()
    if not blob:
        return None
    oauth = blob.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        return None
    access = oauth.get("accessToken")
    refresh = oauth.get("refreshToken")
    expires_at = oauth.get("expiresAt", 0)
    if not access or not refresh:
        return None
    return AnthropicOAuthCreds(
        access_token=access,
        refresh_token=refresh,
        expires_at_ms=int(expires_at),
        subscription_type=oauth.get("subscriptionType", ""),
    )


def _write_macos_keychain(blob: dict) -> bool:
    if platform.system() != "Darwin":
        return False
    payload = json.dumps(blob)
    try:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",  # update if exists
                "-s",
                "Claude Code-credentials",
                "-a",
                os.environ.get("USER", "voss"),
                "-w",
                payload,
            ],
            check=True,
            timeout=5,
            capture_output=True,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _write_claude_credentials_file(blob: dict) -> bool:
    path = Path.home() / ".claude" / ".credentials.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(blob, indent=2))
        return True
    except OSError:
        return False


def refresh_anthropic(creds: AnthropicOAuthCreds, *, client: Optional[httpx.Client] = None) -> AnthropicOAuthCreds:
    """Refresh the Anthropic access token using the stored refresh_token.

    Persists the new tokens back to wherever the originals came from (keychain
    on macOS, otherwise the credentials.json file).
    """
    own_client = client is None
    c = client or httpx.Client(timeout=15.0)
    try:
        resp = c.post(
            ANTHROPIC_TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "refresh_token": creds.refresh_token,
                "client_id": CLAUDE_CODE_CLIENT_ID,
            },
            headers={"content-type": "application/json"},
        )
    finally:
        if own_client:
            c.close()
    resp.raise_for_status()
    body = resp.json()
    new = AnthropicOAuthCreds(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token", creds.refresh_token),
        expires_at_ms=int((time.time() + body.get("expires_in", 3600)) * 1000),
        subscription_type=creds.subscription_type,
    )
    # Persist back. Macos keychain first, then file.
    blob = _read_macos_keychain() or _read_claude_credentials_file() or {}
    blob.setdefault("claudeAiOauth", {})
    blob["claudeAiOauth"]["accessToken"] = new.access_token
    blob["claudeAiOauth"]["refreshToken"] = new.refresh_token
    blob["claudeAiOauth"]["expiresAt"] = new.expires_at_ms
    if not _write_macos_keychain(blob):
        _write_claude_credentials_file(blob)
    return new


# ---------------------------------------------------------------------------
# Codex (OpenAI) — reads ~/.codex/auth.json
# ---------------------------------------------------------------------------


@dataclass
class CodexCreds:
    api_key: Optional[str]
    access_token: Optional[str]
    refresh_token: Optional[str]
    account_id: Optional[str]
    auth_mode: str  # "ApiKey" | "ChatGPT" | "chatgpt" | ""

    @property
    def usable_api_key(self) -> Optional[str]:
        return self.api_key

    @property
    def has_oauth(self) -> bool:
        return bool(self.access_token and self.refresh_token)


def refresh_codex(creds: CodexCreds, *, client: Optional[httpx.Client] = None) -> CodexCreds:
    """Refresh a Codex/ChatGPT OAuth access token."""
    own_client = client is None
    c = client or httpx.Client(timeout=15.0)
    try:
        resp = c.post(
            OPENAI_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": creds.refresh_token,
                "client_id": CODEX_CLIENT_ID,
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    finally:
        if own_client:
            c.close()
    resp.raise_for_status()
    body = resp.json()
    new = CodexCreds(
        api_key=creds.api_key,
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token", creds.refresh_token),
        account_id=creds.account_id,
        auth_mode=creds.auth_mode,
    )
    # Persist back to ~/.codex/auth.json.
    path = Path.home() / ".codex" / "auth.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    data.setdefault("tokens", {})
    data["tokens"]["access_token"] = new.access_token
    data["tokens"]["refresh_token"] = new.refresh_token
    if creds.api_key is not None:
        data["OPENAI_API_KEY"] = creds.api_key
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        pass
    return new


def load_codex() -> Optional[CodexCreds]:
    path = Path.home() / ".codex" / "auth.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    tokens = data.get("tokens") or {}
    return CodexCreds(
        api_key=data.get("OPENAI_API_KEY"),
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        account_id=tokens.get("account_id"),
        auth_mode=data.get("auth_mode", ""),
    )


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


@dataclass
class Resolution:
    source: str  # "env-anthropic" | "env-openai" | "claude-oauth" | "codex" | "codex-oauth" | "none"
    detail: str
    anthropic_oauth: Optional[AnthropicOAuthCreds] = None
    openai_api_key: Optional[str] = None
    codex_oauth: Optional[CodexCreds] = None


def resolve(preference: str = "auto") -> Resolution:
    """Decide which auth path to use.

    preference: auto | claude | codex | api | none
    """
    if preference == "none":
        return Resolution(source="none", detail="forced none")

    if preference in ("auto", "api"):
        if k := os.environ.get("ANTHROPIC_API_KEY"):
            return Resolution(source="env-anthropic", detail="ANTHROPIC_API_KEY", openai_api_key=None)
        if k := os.environ.get("OPENAI_API_KEY"):
            return Resolution(source="env-openai", detail="OPENAI_API_KEY", openai_api_key=k)

    if preference in ("auto", "claude"):
        if creds := load_anthropic_oauth():
            return Resolution(
                source="claude-oauth",
                detail=f"keychain ({creds.subscription_type}, expires {creds.expires_in_seconds}s)",
                anthropic_oauth=creds,
            )

    if preference in ("auto", "codex"):
        if codex := load_codex():
            if codex.api_key:
                return Resolution(
                    source="codex",
                    detail=f"~/.codex/auth.json ({codex.auth_mode}, api key)",
                    openai_api_key=codex.api_key,
                )
            if codex.has_oauth:
                return Resolution(
                    source="codex-oauth",
                    detail=f"~/.codex/auth.json ({codex.auth_mode}, OAuth)",
                    codex_oauth=codex,
                )

    if preference == "claude":
        return Resolution(source="none", detail="no Claude OAuth creds found")
    if preference == "codex":
        return Resolution(source="none", detail="no Codex creds found")
    if preference == "api":
        return Resolution(source="none", detail="no API key in env")
    return Resolution(source="none", detail="no creds found via any path")
