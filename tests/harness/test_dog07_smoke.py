"""DOG-07 / D-12 (c): compiled harness CLI smoke exits 0 with output."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


# Registers a deterministic stub provider and patches the harness auth resolver
# so `voss do` runs without real credentials (CI has none).
_STUB_SITECUSTOMIZE = '''\
from pathlib import Path as _Path

import voss_runtime as _vr
from voss_runtime import StubProvider as _SP, configure as _cfg
from voss.harness import local_sources as _sources

_sources.user_home = lambda: _Path.cwd() / "_isolated_home"
_sources.codex_home = lambda: _sources.user_home() / ".codex"

_stub = _SP(default_response="noop summary stub")
_vr.providers.register("__stub__", _stub)
_cfg(default_model="__stub__")

try:
    from voss.harness import auth as _a
    from voss.harness import cli as _c

    def _resolve(preference, *args, **kwargs):
        return (_a.Resolution(source="env-anthropic", detail="stub-dog07"), _stub)

    _c._resolve_auth_or_die = _resolve
except Exception:  # noqa: BLE001
    pass
'''


def test_dog07_voss_do_through_compiled_harness(precompiled_harness: Path) -> None:
    precompiled_harness.joinpath("fixture.md").write_text("noop fixture body\n")

    repo_root = Path(__file__).resolve().parents[2]
    stub_dir = precompiled_harness / "_voss_stub"
    stub_dir.mkdir(exist_ok=True)
    (stub_dir / "sitecustomize.py").write_text(_STUB_SITECUSTOMIZE)

    config_dir = precompiled_harness / "_voss_config" / "voss"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.toml").write_text("[code_recall]\ninject = false\n")

    env = os.environ.copy()
    env["XDG_CONFIG_HOME"] = str(config_dir.parent)
    env["VOSS_HARNESS"] = "compiled"
    env["VOSS_HERMETIC"] = "1"
    # Stub-only: strip inherited live creds and block HF/transformers downloads.
    for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        env.pop(_k, None)
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    existing_pythonpath = env.get("PYTHONPATH")
    parts = [str(stub_dir), str(repo_root)]
    if existing_pythonpath:
        parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(parts)

    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "do", "noop summary of fixture.md"],
        cwd=str(precompiled_harness),
        env=env,
        input="",
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
