"""Metadata-only subscription availability for managed desktop execution."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from . import auth, config
from .subscription_models import SUBSCRIPTION_MODELS


class PreflightBody(BaseModel):
    harness: str = Field(max_length=64)
    model: str = Field(default="", max_length=256)
    account_alias: str | None = Field(default=None, max_length=128)


class Availability(BaseModel):
    v: Literal[1] = 1
    harness: str
    provider: str
    model: str
    cli_installed: bool = False
    available: bool = False
    code: str
    message: str
    login_command: str | None = None
    checked_at: str
    check_scope: Literal["local_metadata"] = "local_metadata"
    account_alias: str | None = None
    account_selection: Literal[False] = False


class Catalog(BaseModel):
    v: Literal[1] = 1
    harnesses: list[Availability]
    selected_harness: str | None = None


def _model(harness: str, requested: str) -> str:
    if requested:
        return requested
    saved = config.load_harness_config()
    if saved.get("auth") == harness and saved.get("preferred_model"):
        return saved["preferred_model"]
    if harness == "codex":
        configured = auth.load_codex_default_model()
        if configured:
            return configured
    return next(m.id for m in SUBSCRIPTION_MODELS[harness] if m.recommended)


def _codex_expiry(access_token: str) -> float:
    payload = access_token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    expiry = claims["exp"]
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not math.isfinite(expiry):
        raise ValueError("invalid expiry")
    return expiry


def preflight(body: PreflightBody) -> Availability:
    harness = body.harness
    result = Availability(
        harness=harness, provider={"claude": "anthropic", "codex": "openai"}.get(harness, ""),
        model=body.model, code="unsupported_harness",
        message="This harness has no supported OAuth launch adapter.",
        checked_at=datetime.now(timezone.utc).isoformat(),
        login_command={"claude": "claude auth login", "codex": "codex login"}.get(harness),
    )
    if harness not in SUBSCRIPTION_MODELS:
        return result
    if body.account_alias is not None:
        return result.model_copy(update={
            "code": "account_selection_unavailable",
            "message": "Saved-account selection is unavailable. Use the current local OAuth login.",
        })
    try:
        result.cli_installed = auth.detect_upstream_cli(harness) is not None
        home_key, default_home = ("CLAUDE_CONFIG_DIR", Path.home() / ".claude") if harness == "claude" else ("CODEX_HOME", Path.home() / ".codex")
        if os.environ.get(home_key) and Path(os.environ[home_key]).expanduser().resolve() != default_home.resolve():
            result.code, result.message = "custom_login_location", "This login location is not supported by the managed OAuth adapter."
            return result
        result.model = _model(harness, body.model)
        compatible = result.model.startswith("claude-") if harness == "claude" else auth.is_codex_backend_model(result.model)
        if not compatible:
            result.code, result.message = "model_mismatch", "Choose a model for this harness. Your saved selection has not changed."
            return result
        if harness == "claude" and not result.cli_installed:
            result.code, result.message = "cli_missing", "Install Claude Code, then sign in with your subscription."
            return result
        if harness == "claude":
            try:
                from claude_agent_sdk import query  # noqa: F401
            except ImportError:
                result.code, result.message = "adapter_unavailable", "Install the engine's Claude Agent SDK integration, then recheck."
                return result
        creds = auth.load_anthropic_oauth() if harness == "claude" else auth.load_codex()
        if creds is None:
            result.code, result.message = "oauth_missing", "Sign in with your subscription, then recheck."
            return result
        if harness == "codex" and (not creds.has_oauth or not isinstance(creds.auth_mode, str) or creds.auth_mode.lower() != "chatgpt"):
            result.code, result.message = "oauth_required", "Sign in with ChatGPT. API-key credentials cannot enable this harness."
            return result
        expiry = creds.expires_at_ms / 1000 if harness == "claude" else _codex_expiry(creds.access_token)
        if expiry <= time.time() + 60:
            result.code, result.message = "oauth_expired", "The local OAuth login has expired. Sign in again, then recheck."
            return result
        result.available = True
        result.code = "oauth_present"
        result.message = "Local OAuth login found. Remote access is checked when work starts."
    except Exception:
        result.available = False
        result.code, result.message = "check_failed", "Could not check this local OAuth login. Sign in again, then recheck."
    return result


def catalog() -> Catalog:
    try:
        selected = config.load_harness_config().get("auth")
    except Exception:
        selected = None
    return Catalog(harnesses=[preflight(PreflightBody(harness=harness)) for harness in SUBSCRIPTION_MODELS],
                   selected_harness=selected if selected in SUBSCRIPTION_MODELS else None)


def unavailable(result: Availability, code: str, message: str) -> Availability:
    return result.model_copy(update={"available": False, "code": code, "message": message})


def _credentials(harness):
    return auth.load_anthropic_oauth() if harness == "claude" else auth.load_codex()


def _fingerprint(creds) -> bytes:
    return hashlib.sha256(creds.access_token.encode()).digest()


class BoundProvider:
    def __init__(self, provider, availability: Availability, credentials):
        self.provider = provider
        self.availability = availability
        self.credentials = credentials
        self.fingerprint = _fingerprint(credentials)
        self.blocked: Availability | None = None

    def check(self) -> Availability | None:
        if self.blocked is not None:
            return self.blocked
        result = preflight(PreflightBody(harness=self.availability.harness, model=self.availability.model))
        if result.available:
            try:
                if _fingerprint(_credentials(result.harness)) != self.fingerprint:
                    result = unavailable(result, "login_changed", "The local login changed. Retry explicitly to use the current login.")
            except Exception:
                result = unavailable(result, "check_failed", "Could not recheck the local login. Sign in again, then retry.")
        if not result.available:
            self.blocked = result
        return self.blocked

    def _require(self):
        if self.check() is not None:
            raise auth.OAuthRequired(self.blocked.message)

    def _rejected(self, exc):
        message = "OAuth access stopped working. Sign in again, then retry explicitly." if exc.code == "oauth_rejected" else "The provider stopped. Check its login and task output before an explicit retry."
        self.blocked = unavailable(self.availability, exc.code, message)

    async def complete(self, **kwargs):
        self._require()
        try:
            return await self.provider.complete(**kwargs)
        except auth.OAuthRequired as exc:
            self._rejected(exc)
            raise

    async def stream(self, **kwargs):
        self._require()
        try:
            async for event in self.provider.stream(**kwargs):
                yield event
        except auth.OAuthRequired as exc:
            self._rejected(exc)
            raise

    def count_tokens(self, **kwargs):
        return self.provider.count_tokens(**kwargs)

    async def aclose(self):
        close = getattr(self.provider, "aclose", None)
        if close is not None:
            await close()


def prepare(body: PreflightBody) -> tuple[Availability, BoundProvider | None]:
    result = preflight(body)
    if not result.available:
        return result, None
    try:
        creds = _credentials(body.harness)
        if body.harness == "claude":
            from .claude_agent_provider import ClaudeAgentProvider

            provider = ClaudeAgentProvider(model_default=result.model, cli_path=auth.detect_upstream_cli("claude"),
                                           oauth_token=creds.access_token)
            provider._resolve_query()
        else:
            from .providers import OpenAIOAuthProvider

            provider = OpenAIOAuthProvider(auth.CodexCreds(None, creds.access_token, None, creds.account_id, "ChatGPT"),
                                          base_url=auth.CHATGPT_BACKEND_BASE, allow_refresh=False)
        bound = BoundProvider(provider, result, creds)
        blocked = bound.check()
        return (blocked, None) if blocked is not None else (result, bound)
    except Exception:
        return unavailable(result, "check_failed", "Could not prepare this OAuth login. Sign in again, then recheck."), None


class _OAuthHandle:
    def __init__(self, handle, directory, binding):
        self.handle, self.directory, self.binding = handle, directory, binding
        self.cancelled = False

    def wait(self, timeout=None):
        code = self.handle.wait(timeout)
        if self.directory is not None:
            self.directory.cleanup()
        if code != 0 and not self.cancelled:
            self.binding.blocked = unavailable(self.binding.availability, "worker_unavailable",
                "The worker stopped. Check its login and task output before an explicit retry.")
            raise auth.OAuthRequired(self.binding.blocked.message)
        return code

    def terminate(self):
        self.cancelled = True
        self.handle.terminate()


def check_cli(binding: BoundProvider):
    binding._require()
    if not binding.availability.cli_installed:
        binding.blocked = unavailable(binding.availability, "cli_missing", "Install this CLI, then sign in and recheck.")
    elif binding.availability.harness == "codex" and not binding.credentials.id_token:
        binding.blocked = unavailable(binding.availability, "cli_login_unavailable", "Sign in with Codex again to enable an isolated worker login.")
    if binding.blocked is not None:
        raise auth.OAuthRequired(binding.blocked.message)


def spawn_cli(binding: BoundProvider, argv: list[str], cwd: Path):
    from .claude_agent_provider import _API_BILLING_ENV_KEYS_TO_SHADOW
    from .swarm_runtime import _PopenHandle

    check_cli(binding)
    harness = binding.availability.harness
    env = {key: value for key, value in os.environ.items()
           if not key.endswith("_API_KEY") and not key.startswith(("OPENAI_", "ANTHROPIC_", "CLAUDE_CODE_USE_"))
           and key not in (*_API_BILLING_ENV_KEYS_TO_SHADOW, "CODEX_HOME", "CODEX_ACCESS_TOKEN", "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_OAUTH_TOKEN")}
    directory = None
    try:
        directory = tempfile.TemporaryDirectory(prefix="voss-oauth-")
        if harness == "claude":
            env["CLAUDE_CODE_OAUTH_TOKEN"] = binding.credentials.access_token
            env["CLAUDE_CONFIG_DIR"] = directory.name
            argv = [str(auth.detect_upstream_cli("claude")), "--setting-sources", "", "--settings",
                    '{"forceLoginMethod":"claudeai","apiKeyHelper":""}', *argv[1:]]
        else:
            home = Path(directory.name)
            creds = binding.credentials
            path = home / "auth.json"
            path.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {
                "access_token": creds.access_token, "refresh_token": creds.refresh_token,
                "id_token": creds.id_token, "account_id": creds.account_id,
            }}))
            path.chmod(0o600)
            env["CODEX_HOME"] = str(home)
            argv = [str(auth.detect_upstream_cli("codex")), "-c", 'forced_login_method="chatgpt"',
                    "-c", 'cli_auth_credentials_store="file"', "-c", 'model_provider="openai"', *argv[1:]]
        process = subprocess.Popen(argv, cwd=str(cwd), env=env, start_new_session=True)
        return _OAuthHandle(_PopenHandle(process), directory, binding)
    except Exception:
        if directory is not None:
            directory.cleanup()
        raise
