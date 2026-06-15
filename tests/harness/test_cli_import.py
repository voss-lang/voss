from __future__ import annotations

import os
import subprocess
import sys
import typing
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


def test_harness_net_session_annotations_resolve() -> None:
    import voss.harness.cli as cli
    import voss.harness.tools as tools
    from voss.harness.net import NetSession

    assert typing.get_type_hints(cli)["_NET_SESSION"] == NetSession | None
    assert typing.get_type_hints(cli._get_net_session)["return"] is NetSession
    assert typing.get_type_hints(tools.make_toolset)["net"] == NetSession | None
