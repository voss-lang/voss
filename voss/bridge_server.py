"""JSON-RPC over stdio server. Companion to crates/voss-bridge.

LSP-style framing: ``Content-Length: <n>\\r\\n\\r\\n<json-body>``.
Versioned envelope: every successful response carries ``"v": 1`` inside
``result``. Methods: ``ast``, ``check``, ``compile``, ``run``.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1


def _read_frame(stream) -> bytes | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        decoded = line.decode("ascii", errors="replace").rstrip("\r\n")
        if decoded == "":
            break
        if ":" in decoded:
            k, v = decoded.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    raw = headers.get("content-length")
    if raw is None:
        raise ValueError("missing Content-Length")
    n = int(raw)
    if n < 0:
        raise ValueError(f"negative Content-Length: {n}")
    return stream.read(n)


def _write_frame(stream, body: bytes) -> None:
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stream.write(body)
    stream.flush()


def _diag_to_dict(d: Any) -> dict:
    return dataclasses.asdict(d) if dataclasses.is_dataclass(d) else dict(d.__dict__)


def _project_root(params: dict) -> Path:
    return Path(params.get("project_root") or os.getcwd()).resolve()


def _resolve_inside(root: Path, raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path escapes project root: {raw}")
    return resolved


def _handle(req: dict) -> dict:
    method = req.get("method")
    params = req.get("params") or {}
    rid = req.get("id")
    try:
        root = _project_root(params)
        if method == "ast":
            from voss.parser import parse
            from voss.ast_serializer import to_dict

            path = _resolve_inside(root, params["path"])
            src = path.read_text()
            program = parse(src, file=str(path))
            result = {
                "v": PROTOCOL_VERSION,
                "program": to_dict(program, normalize_spans=bool(params.get("normalize_spans", False))),
            }
        elif method == "check":
            from voss.parser import parse
            from voss.analyzer import analyze

            path = _resolve_inside(root, params["path"])
            src = path.read_text()
            program = parse(src, file=str(path))
            report = analyze(program, source_path=str(path))
            result = {
                "v": PROTOCOL_VERSION,
                "ok": report.ok,
                "diagnostics": [_diag_to_dict(d) for d in report.diagnostics],
            }
        elif method == "compile":
            from voss.parser import parse
            from voss.codegen import generate_python

            src_path = _resolve_inside(root, params["path"])
            program = parse(src_path.read_text(), file=str(src_path))
            cg = generate_python(program, source_path=str(src_path))
            out_path = _resolve_inside(root, params.get("output") or str(src_path.with_suffix(".py")))
            out_path.write_text(cg.source)
            result = {
                "v": PROTOCOL_VERSION,
                "output": str(out_path),
                "ok": True,
            }
        elif method == "run":
            # Stub — wave R3 wires the runtime path.
            result = {"v": PROTOCOL_VERSION, "ok": True, "note": "stub"}
        else:
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"method not found: {method}"},
            }
    except Exception as e:  # noqa: BLE001 — surface any error to caller.
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "error": {"code": -32000, "message": f"{type(e).__name__}: {e}"},
        }
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve() -> None:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        try:
            body = _read_frame(stdin)
        except ValueError as e:
            # Malformed framing — emit error response with id=null and continue.
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"parse error: {e}"},
            }
            _write_frame(stdout, json.dumps(err).encode("utf-8"))
            return
        if body is None:
            return
        try:
            req = json.loads(body)
        except json.JSONDecodeError as e:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"json parse error: {e}"},
            }
            _write_frame(stdout, json.dumps(err).encode("utf-8"))
            continue
        resp = _handle(req)
        _write_frame(stdout, json.dumps(resp).encode("utf-8"))


if __name__ == "__main__":
    serve()
