"""T2-02 Task 2: cli.py bootstrap wires [agent] config into RuntimeConfig.

Uses subprocess.run with a fresh Python interpreter to avoid RuntimeConfig
singleton contamination across tests (the bootstrap runs at import time
and configure() mutates global state).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROBE = (
    "import voss.harness.cli; "
    "from voss_runtime import get_config; "
    "c = get_config(); "
    "print(f'{c.max_iterations}|{c.max_parallel_reads}')"
)


def _run_probe(tmp_path: Path) -> tuple[int, str, str]:
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path)}
    # Drop any pre-existing override that might bleed in from the parent shell.
    env.pop("VOSS_MAX_PARALLEL_READS", None)
    env.pop("VOSS_MAX_ITERATIONS", None)
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def test_bootstrap_default_no_config(tmp_path: Path) -> None:
    rc, out, err = _run_probe(tmp_path)
    assert rc == 0, f"subprocess failed: {err}"
    assert out == "8|8", f"unexpected output: {out!r} (stderr={err!r})"


def test_bootstrap_reads_max_parallel_reads_override(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "voss"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").write_text('[agent]\nmax_parallel_reads = "16"\n')
    rc, out, err = _run_probe(tmp_path)
    assert rc == 0, f"subprocess failed: {err}"
    assert out == "8|16", f"unexpected output: {out!r} (stderr={err!r})"


def test_bootstrap_reads_both_agent_keys(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "voss"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").write_text(
        '[agent]\nmax_iterations = "12"\nmax_parallel_reads = "20"\n'
    )
    rc, out, err = _run_probe(tmp_path)
    assert rc == 0, f"subprocess failed: {err}"
    assert out == "12|20", f"unexpected output: {out!r} (stderr={err!r})"


def test_bootstrap_out_of_range_falls_back_to_default(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "voss"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").write_text(
        '[agent]\nmax_parallel_reads = "100"\n'
    )
    rc, out, err = _run_probe(tmp_path)
    assert rc == 0, f"subprocess failed: {err}"
    assert out == "8|8", f"unexpected output: {out!r} (stderr={err!r})"
