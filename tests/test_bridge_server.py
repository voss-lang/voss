from __future__ import annotations

from pathlib import Path

from voss import bridge_server


def test_bridge_rejects_source_outside_project_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.voss"
    outside.write_text("let x = 1\n")

    resp = bridge_server._handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "ast",
            "params": {"path": str(outside), "project_root": str(root)},
        }
    )

    assert resp["error"]["code"] == -32000
    assert "path escapes project root" in resp["error"]["message"]


def test_bridge_rejects_compile_output_outside_project_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    source = root / "main.voss"
    source.write_text("let x = 1\n")
    outside = tmp_path / "main.py"

    resp = bridge_server._handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "compile",
            "params": {
                "path": str(source),
                "output": str(outside),
                "project_root": str(root),
            },
        }
    )

    assert resp["error"]["code"] == -32000
    assert "path escapes project root" in resp["error"]["message"]
