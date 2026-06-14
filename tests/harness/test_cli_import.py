from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_voss_cli_import_does_not_import_litellm() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    paths = [str(repo_root)]
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, voss.cli; print('litellm' in sys.modules)",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"
