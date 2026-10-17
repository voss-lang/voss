"""Systems under test. Each adapter mutates the workspace and reports what it claimed."""
from __future__ import annotations

import functools
import json
import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .spec import BenchmarkSpec, Config, Usage, VossInfo
from .store import Store
from .workspace import Workspace


@dataclass
class AdapterResult:
    final: str = ""
    exit_reason: str | None = None
    claimed_complete: bool | None = None
    usage: Usage = field(default_factory=Usage)
    model: str | None = None
    provider: str | None = None
    voss: VossInfo | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def oracle(spec, task_dir, ws, env, config, store) -> AdapterResult:
    patch = task_dir / "reference.patch"
    if not patch.is_file():
        return AdapterResult(exit_reason="error", errors=["no reference.patch"])
    p = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", str(patch)],
        cwd=ws.repo, capture_output=True, text=True,
    )
    if p.returncode != 0:
        return AdapterResult(exit_reason="error", errors=[f"git apply: {p.stderr.strip()[:300]}"])
    return AdapterResult(exit_reason="done", claimed_complete=True)


def null(spec, task_dir, ws, env, config, store) -> AdapterResult:
    return AdapterResult(exit_reason="done")


@functools.cache
def _voss_version(voss_bin: str) -> str | None:
    try:
        out = subprocess.run([voss_bin, "--version"], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.strip().rsplit(" ", 1)[-1] or None


def _handshake(proc: subprocess.Popen, timeout: float) -> dict | None:
    lines: queue.Queue[str] = queue.Queue()

    def pump() -> None:
        for line in proc.stdout:
            lines.put(line)

    threading.Thread(target=pump, daemon=True).start()
    deadline = time.monotonic() + timeout
    while (left := deadline - time.monotonic()) > 0:
        try:
            line = lines.get(timeout=left)
        except queue.Empty:
            return None
        try:
            h = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(h, dict) and h.get("token"):
            return h
    return None


def _sse(response: httpx.Response):
    event_type = ""
    for line in response.iter_lines():
        if not line:
            event_type = ""
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            try:
                payload = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            payload.setdefault("type", event_type)
            yield payload


def _usage_from_record(record: dict, res: AdapterResult) -> None:
    runs = record.get("runs") or []
    if not runs:
        return
    its = [it for r in runs for it in (r.get("iterations") or [])]
    res.usage.input_tokens = sum(int(it.get("prompt_tokens") or 0) for it in its)
    res.usage.output_tokens = sum(int(it.get("completion_tokens") or 0) for it in its)
    res.exit_reason = runs[-1].get("exit_reason") or res.exit_reason
    res.claimed_complete = res.exit_reason == "done"


def voss_serve(spec: BenchmarkSpec, task_dir: Path, ws: Workspace, env: dict[str, str],
               config: Config, store: Store) -> AdapterResult:
    """Drive one turn through `voss serve` REST+SSE, the public headless surface."""
    res = AdapterResult(provider=config.auth)
    res.voss = VossInfo(version=_voss_version(config.voss_bin))
    server_env = {
        **env,
        "LITELLM_LOCAL_MODEL_COST_MAP": "true",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        **config.env,
    }
    proc = subprocess.Popen(
        [config.voss_bin, "serve"], cwd=ws.repo, env=server_env, text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    stderr: list[str] = []
    threading.Thread(target=lambda: stderr.extend(proc.stderr), daemon=True).start()
    events: list[dict] = []
    try:
        hs = _handshake(proc, 60)
        if hs is None:
            res.exit_reason = "error"
            res.errors.append("serve handshake timeout: " + "".join(stderr[-5:])[-300:])
            return res
        base = f"http://127.0.0.1:{hs['port']}"
        headers = {"Authorization": f"Bearer {hs['token']}"}
        deadline = time.monotonic() + spec.budget.wall_s
        with httpx.Client(base_url=base, headers=headers, timeout=httpx.Timeout(30, read=60)) as c:
            caps = c.get("/capabilities")
            if caps.status_code == 200:
                body = caps.json()
                res.voss.capabilities = list(body.get("capabilities", []) if isinstance(body, dict) else body)
            session = {"cwd": str(ws.repo), "auth": config.auth}
            if config.model:
                session["model"] = config.model
            r = c.post("/session", json=session)
            r.raise_for_status()
            sid = r.json()["id"]
            res.model = c.get(f"/session/{sid}").json().get("model")
            message = {
                "parts": [{"type": "text", "text": spec.prompt}],
                "mode": config.mode or spec.mode,
                "command_id": str(uuid.uuid4()),
            }
            choice = config.permission_choice or spec.permission_choice
            with c.stream("GET", f"/session/{sid}/events", headers={"Accept": "text/event-stream"}) as sse:
                c.post(f"/session/{sid}/message", json=message).raise_for_status()
                for ev in _sse(sse):
                    events.append(ev)
                    if ev["type"] == "permission.updated":
                        c.post(f"/session/{sid}/permission", json={"id": ev["id"], "choice": choice})
                    elif ev["type"] == "final":
                        res.final = ev.get("text", "")
                    elif ev["type"] == "session.idle":
                        break
                    if time.monotonic() > deadline:
                        c.post(f"/session/{sid}/abort")
                        res.exit_reason = "timeout"
                        res.errors.append(f"wall budget {spec.budget.wall_s}s exceeded")
                        break
            cost = c.get(f"/session/{sid}/cost").json()
            if cost.get("turns"):
                res.usage.cost_usd = float(cost["total_usd"])
                res.usage.cost_source = "serve:/cost"
        record_path = ws.repo / ".voss" / "sessions" / f"{sid}.json"
        if record_path.is_file():
            res.artifacts["session_record"] = store.put(record_path.read_bytes())
            _usage_from_record(json.loads(record_path.read_text()), res)
        res.exit_reason = res.exit_reason or "done"
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        res.exit_reason = "error"
        res.errors.append(f"{type(exc).__name__}: {str(exc)[:300]}")
    finally:
        if proc.stdin:
            proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if events:
            res.artifacts["events"] = store.put("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
    return res


ADAPTERS = {"oracle": oracle, "null": null, "voss-serve": voss_serve}
