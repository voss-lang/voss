"""Systems under test. Each adapter mutates the workspace and reports what it claimed."""
from __future__ import annotations

import functools
import json
import os
import queue
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from . import sealed
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
    session_id: str | None = None


def _no_model() -> Usage:
    return Usage(input_tokens=0, output_tokens=0, cost_usd=0.0, cost_source="no model")


def oracle(spec, task_dir, ws, env, config, store) -> AdapterResult:
    with sealed.answers(task_dir) as src:
        patch = src / "reference.patch"
        if not patch.is_file():
            return AdapterResult(exit_reason="error", errors=["no reference.patch"])
        p = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", str(patch)],
            cwd=ws.repo, capture_output=True, text=True,
        )
    if p.returncode != 0:
        return AdapterResult(exit_reason="error", errors=[f"git apply: {p.stderr.strip()[:300]}"])
    return AdapterResult(exit_reason="done", claimed_complete=True, usage=_no_model())


def null(spec, task_dir, ws, env, config, store) -> AdapterResult:
    return AdapterResult(exit_reason="done", usage=_no_model())


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


PING = {"type": "sse.ping"}


def _sse(response):
    event_type = ""
    for line in response.iter_lines():
        if not line:
            event_type = ""
        elif line.startswith(":"):
            yield PING
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            try:
                payload = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            payload.setdefault("type", event_type)
            yield payload


NO_RUN = "turn was routed to ambient chat, so no agent run happened"


def turn_problems(events: list[dict]) -> list[str]:
    """Stream errors, plus a note when the server never entered its agent loop."""
    problems = [e["text"].strip() for e in events
                if e["type"] == "stream.delta" and "[error:" in e.get("text", "")]
    if "run" not in {e.get("phase") for e in events if e["type"] == "status"}:
        problems.append(NO_RUN)
    return problems


def usage_from_record(record: dict, res: AdapterResult) -> None:
    runs = record.get("runs") or []
    if not runs:
        return
    its = [it for r in runs for it in (r.get("iterations") or [])]

    def total(key: str) -> int:
        return sum(int(it.get(key) or 0) for it in its)

    res.usage.input_tokens = total("prompt_tokens")
    res.usage.output_tokens = total("completion_tokens")
    res.usage.cache_creation_tokens = total("cache_creation_input_tokens")
    res.usage.cache_read_tokens = total("cache_read_input_tokens")
    if res.usage.cost_usd == 0 and res.usage.output_tokens:
        res.usage.cost_usd = None
        res.usage.cost_source = "unknown: voss reported $0 for a run that used tokens"
    res.exit_reason = res.exit_reason or runs[-1].get("exit_reason")
    res.claimed_complete = res.exit_reason == "done"


def _start_serve(ws: Workspace, env: dict[str, str], config: Config) -> tuple[subprocess.Popen, list[str]]:
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
    return proc, stderr


def _stop_serve(proc: subprocess.Popen) -> None:
    if proc.stdin:
        proc.stdin.close()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def voss_serve(spec: BenchmarkSpec, task_dir: Path, ws: Workspace, env: dict[str, str],
               config: Config, store: Store, resume: str | None = None) -> AdapterResult:
    """Drive one turn through `voss serve` REST+SSE, the public headless surface."""
    res = AdapterResult(provider=config.auth)
    res.voss = VossInfo(version=_voss_version(config.voss_bin))
    proc, stderr = _start_serve(ws, env, config)
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
            if resume:
                session["resume"] = resume
            r = c.post("/session", json=session)
            r.raise_for_status()
            created = r.json()
            sid = res.session_id = created["id"]
            res.provider = created.get("auth") or config.auth
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
                    if ev is not PING:
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
            usage_from_record(json.loads(record_path.read_text()), res)
        problems = turn_problems(events)
        if problems:
            res.exit_reason = "no-run" if NO_RUN in problems else "error"
            res.claimed_complete = None
            res.errors += problems
        res.exit_reason = res.exit_reason or "done"
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        res.exit_reason = "error"
        res.errors.append(f"{type(exc).__name__}: {str(exc)[:300]}")
    finally:
        _stop_serve(proc)
        if events:
            res.artifacts["events"] = store.put("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
    return res


SWARM_DONE = {"swarm.complete", "swarm.candidates_ready"}
SWARM_FAILED = {"decompose_failed", "run_failed", "run_incomplete"}


def _watch_member(base: str, headers: dict, sid: str, choice: str, events: list[dict],
                  ready: threading.Event, done: threading.Event, outcome: list[dict]) -> None:
    try:
        with httpx.Client(base_url=base, headers=headers, timeout=httpx.Timeout(30, read=60)) as c, \
                c.stream("GET", f"/session/{sid}/events", headers={"Accept": "text/event-stream"}) as sse:
            ready.set()
            for ev in _sse(sse):
                if done.is_set():
                    return
                if ev is PING:
                    continue
                events.append({**ev, "member_session": sid})
                if ev["type"] == "permission.updated":
                    c.post(f"/session/{sid}/permission", json={"id": ev["id"], "choice": choice})
                elif ev["type"] in SWARM_DONE or (ev["type"] == "swarm.gate" and ev.get("gate_type") in SWARM_FAILED):
                    outcome.append(ev)
                    done.set()
    except httpx.HTTPError:
        ready.set()


def voss_swarm(spec: BenchmarkSpec, task_dir: Path, ws: Workspace, env: dict[str, str],
               config: Config, store: Store) -> AdapterResult:
    """Configuration C: `POST /swarm` with the default native roster, then `/swarm/{id}/run`."""
    res = AdapterResult(provider=config.auth)
    res.voss = VossInfo(version=_voss_version(config.voss_bin))
    proc, stderr = _start_serve(ws, env, config)
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
            body = {"goal": spec.prompt, "cwd": str(ws.repo), "builders": config.builders}
            if config.model:
                names = ["coordinator", *(f"builder-{i}" for i in range(1, config.builders + 1)), "reviewer"]
                body["roster"] = [{"name": n, "model": config.model, "auth_pref": config.auth} for n in names]
            r = c.post("/swarm", json=body)
            r.raise_for_status()
            created = r.json()
            members = [m for m in created["sessions"] if m.get("session_id")]
            res.model = ",".join(sorted({m["model"] for m in members if m.get("model")})) or None
            done, outcome = threading.Event(), []
            choice = config.permission_choice or spec.permission_choice
            for m in members:
                ready = threading.Event()
                threading.Thread(target=_watch_member, daemon=True, args=(
                    base, headers, m["session_id"], choice, events, ready, done, outcome)).start()
                ready.wait(timeout=30)
            c.post(f"/swarm/{created['id']}/run").raise_for_status()
            if not done.wait(timeout=max(0.0, deadline - time.monotonic())):
                for m in members:
                    c.post(f"/session/{m['session_id']}/abort")
                res.exit_reason = "timeout"
                res.errors.append(f"wall budget {spec.budget.wall_s}s exceeded")
            elif outcome[0]["type"] in SWARM_DONE:
                res.exit_reason, res.claimed_complete = "done", True
            else:
                res.exit_reason, res.claimed_complete = "error", False
                res.errors.append(f"swarm gate {outcome[0].get('gate_type')}: {outcome[0].get('detail', '')[:300]}")
            res.artifacts["swarm"] = store.put(json.dumps(c.get(f"/swarm/{created['id']}").json(), sort_keys=True))
            costs = [c.get(f"/session/{m['session_id']}/cost").json() for m in members]
            if any(cost.get("turns") for cost in costs):
                res.usage.cost_usd = sum(float(cost.get("total_usd") or 0) for cost in costs)
                res.usage.cost_source = "serve:/cost summed over member sessions; excludes the coordinator's task split"
        totals = {"input_tokens": 0, "output_tokens": 0, "cache_creation_tokens": 0, "cache_read_tokens": 0}
        for m in members:
            path = ws.repo / ".voss" / "sessions" / f"{m['session_id']}.json"
            if not path.is_file():
                continue
            res.artifacts[f"session_record:{m['role']}"] = store.put(path.read_bytes())
            member = AdapterResult(usage=Usage(cost_usd=res.usage.cost_usd))
            usage_from_record(json.loads(path.read_text()), member)
            for key in totals:
                totals[key] += getattr(member.usage, key) or 0
        if any(totals.values()):
            res.usage = res.usage.model_copy(update=totals)
            if res.usage.cost_usd == 0 and res.usage.output_tokens:
                res.usage.cost_usd = None
                res.usage.cost_source = "unknown: voss reported $0 for a run that used tokens"
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        res.exit_reason = "error"
        res.errors.append(f"{type(exc).__name__}: {str(exc)[:300]}")
    finally:
        _stop_serve(proc)
        if events:
            res.artifacts["events"] = store.put("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
    return res


CLAUDE_SANDBOX = json.dumps({"sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True}})


def _claude_cmd(spec: BenchmarkSpec, ws: Workspace, config: Config, resume: str | None) -> list[str]:
    cmd = ["claude", "-p", spec.prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
           "--settings", CLAUDE_SANDBOX, "--setting-sources", "project,local", "--strict-mcp-config"]
    cmd += ["--resume", resume] if resume else []
    cmd += [] if config.memory == "resume" else ["--no-session-persistence"]
    return cmd + (["--model", config.model] if config.model else [])


def _codex_cmd(spec: BenchmarkSpec, ws: Workspace, config: Config, resume: str | None) -> list[str]:
    cmd = ["codex", "exec", "--json", "--ephemeral", "-s", "workspace-write", "--ignore-user-config",
           "-C", str(ws.repo)]
    return cmd + (["-m", config.model] if config.model else []) + [spec.prompt]


def _claude_result(out: str, res: AdapterResult) -> None:
    data = [e for e in map(json.loads, filter(None, out.splitlines())) if e.get("type") == "result"][-1]
    res.final = data.get("result") or ""
    res.session_id = data.get("session_id")
    res.claimed_complete = data.get("subtype") == "success" and not data.get("is_error")
    res.exit_reason = "done" if res.claimed_complete else "error"
    usage = data.get("usage") or {}
    res.usage = Usage(
        input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"),
        cache_creation_tokens=usage.get("cache_creation_input_tokens"),
        cache_read_tokens=usage.get("cache_read_input_tokens"),
        cost_usd=data.get("total_cost_usd"),
        cost_source="claude -p total_cost_usd: list-price estimate, a subscription may not bill it",
    )
    res.model = ",".join(sorted(data.get("modelUsage") or {})) or res.model
    if not res.claimed_complete:
        res.errors.append(f"claude -p {data.get('subtype')}: {res.final[:200]}")


def _codex_result(out: str, res: AdapterResult) -> None:
    events = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    turns = [e["usage"] for e in events if e.get("type") == "turn.completed"]
    failed = [e for e in events if e.get("type") in ("turn.failed", "error")]
    messages = [e["item"]["text"] for e in events
                if e.get("type") == "item.completed" and e["item"].get("type") == "agent_message"]
    res.final = messages[-1] if messages else ""
    res.claimed_complete = bool(turns) and not failed
    res.exit_reason = "done" if res.claimed_complete else "error"
    res.usage = Usage(
        input_tokens=sum(t.get("input_tokens", 0) for t in turns),
        output_tokens=sum(t.get("output_tokens", 0) for t in turns),
        cache_read_tokens=sum(t.get("cached_input_tokens", 0) for t in turns),
        cost_source="unknown: codex exec reports no cost",
    )
    res.errors += [json.dumps(e)[:200] for e in failed]


CLI_AGENTS = {"claude": (_claude_cmd, _claude_result), "codex": (_codex_cmd, _codex_result)}


def cli_agent(spec: BenchmarkSpec, task_dir: Path, ws: Workspace, env: dict[str, str],
              config: Config, store: Store, resume: str | None = None) -> AdapterResult:
    """Baseline A: one external coding agent, run non-interactively and sandboxed in the workspace."""
    build, parse = CLI_AGENTS[config.agent]
    res = AdapterResult(provider=f"{config.agent}-cli", model=config.model)
    p = subprocess.Popen(build(spec, ws, config, resume), cwd=ws.repo, env={**env, **config.env}, text=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=spec.budget.wall_s)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        res.exit_reason = "timeout"
        res.errors.append(f"wall budget {spec.budget.wall_s}s exceeded")
    if out:
        res.artifacts["events"] = store.put(out)
    if res.exit_reason == "timeout":
        return res
    try:
        parse(out, res)
    except (json.JSONDecodeError, KeyError, TypeError, IndexError) as exc:
        res.exit_reason, res.claimed_complete = "error", None
        res.errors.append(f"{config.agent} output: {type(exc).__name__}: {(err or out)[-300:]}")
    if p.returncode and res.exit_reason == "done":
        res.exit_reason, res.claimed_complete = "error", None
        res.errors.append(f"{config.agent} exit {p.returncode}: {err[-300:]}")
    return res


ADAPTERS = {"oracle": oracle, "null": null, "voss-serve": voss_serve, "cli-agent": cli_agent,
            "voss-swarm": voss_swarm}
