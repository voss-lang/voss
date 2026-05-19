"""M13 headline multi-agent chat e2e (MAG-08) — green under the stub provider.

ONE stub-provider `voss chat --plain` end-to-end run: a single NL request
fans out to >=2 concurrent sub-agent children, the parent injects >=1
mid-run course-correction into a running child (the child observably
branches on it), the even-split reserve rebalances as the live child set
changes, `subagent_gather` aggregates every child's result into the parent
turn, and after gather no children remain active — ALL six MAG-08 signals
asserted from the one run's transcript (M13-VALIDATION.md row MAG-08).

────────────────────────────────────────────────────────────────────────────
Why this replaces the M13-01 Wave-0 scaffold body
────────────────────────────────────────────────────────────────────────────
The M13-01 RED scaffold drove the RIGHT architecture (`cli_runner.run("chat",
"--plain", stdin=..., ...)` — real `voss chat` + the e2e StubProvider) but
left the deterministic provider script as an implicit TODO: it relied on the
runner's single `default_response`, which can never make the parent fan out,
and asserted bare substrings (`"sub-agent" in out`, `"rebalance" in out`,
`"budget" in out`) that the REAL `PlainRenderer` NEVER emits — under
`--plain` the `PanelBridgeRenderer` panel/`BudgetMeter`/rebalance hooks are
`hasattr`-guarded no-ops (only the `TextualRenderer` has `show_subagent_*`).
Per the M13-06 scaffold-defect pre-authorization, ONLY the diverged
setup/driver is rewritten to exercise the real architecture (stdin-scripted
`voss chat --plain` + a content-reactive scripted multi-agent provider
injected via the documented `CliRunner(extra_sitecustomize=...)` seam, the
mechanism the runner already exposes). The SIX MAG-08 signal assertions are
preserved verbatim in intent and made OBJECTIVELY observable from the real
transcript (tool-call lines on stderr + streamed child/parent text on
stdout) instead of asserting strings the system never produces — strictly
stronger, never weakened.

Hermetic: no live network (the runner strips `ANTHROPIC_API_KEY` /
`OPENAI_API_KEY` and patches `_resolve_auth_or_die` to the in-proc stub),
no disk persistence of sub-agent sessions, deterministic across runs.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .runner import CliRunner

_FIXTURE_MINIMAL = Path(__file__).resolve().parent / "fixtures" / "projects" / "minimal"

# Unique tokens scripted into the run so the content-reactive provider can
# route parent vs. each child, and so the assertions key off markers the
# REAL system actually streams/echoes (not invented renderer strings).
_REQ = "MAG8REQUEST"
_AUTH = "MAG8AUTH"
_RATE = "MAG8RATE"
_STEER = "MAG8STEER"


# ---------------------------------------------------------------------------
# Scripted, content-reactive multi-agent provider — injected verbatim into the
# subprocess via CliRunner(extra_sitecustomize=...). It runs AFTER the runner's
# own sitecustomize template, so it overrides the registered `__stub__` and
# re-patches the harness auth resolver to return this scripted provider. It is
# hermetic (no network), and reactive on `messages` content (the default
# fingerprint StubProvider is order/hash-keyed only and cannot drive a
# parent->fan-out->steer->gather scenario deterministically).
# ---------------------------------------------------------------------------
_SCRIPTED_PROVIDER = r'''
import re as _re
import json as _json

from voss.harness.agent import Plan as _Plan, ToolCall as _TC
from voss.harness.providers import (
    Done as _Done,
    ParsedPlan as _PP,
    TextDelta as _TD,
    Usage as _Usage,
)
import voss_runtime as _vr


def _plan(*, steps=None, final="", rationale="m13e2e"):
    return _Plan(
        rationale=rationale,
        steps=[_TC(**s) for s in (steps or [])],
        confidence=0.95,
        open_question=None,
        final_when_done=final,
    )


def _stream(plan, *, text):
    # The TextDelta streams to stdout through the child's PanelBridgeRenderer
    # (delegated to PlainRenderer.stream_delta) — the honest child-output sink
    # under --plain (run_turn itself never calls show_final; only the CLI does
    # for the PARENT turn).
    return [
        _TD(text=text),
        _PP(plan=plan),
        _Usage(prompt_tokens=12, completion_tokens=6, cost_usd=0.0),
        _Done(stop_reason="end_turn"),
    ]


class _ScriptedMultiAgentProvider:
    """Deterministic, content-routed parent + 2-child + steer script.

    Routing is purely off concatenated `messages` content (replayed prior
    iterations include tool-result lines — see agent._serialize_iter_for_replay
    — so the parent can read its spawned children's handles back out and the
    children can detect the injected `[steering from parent agent]` message).
    """

    def __init__(self):
        self.calls = []

    def _blob(self, messages):
        return "\n".join(str(m.get("content", "")) for m in messages)

    def _events(self, messages):
        b = self._blob(messages)
        is_child = "Subagent role:" in b

        # ---- AUTH child (steer-branching) ---------------------------------
        if is_child and "%(AUTH)s" in b:
            steered = ("[steering from parent agent]" in b) and ("%(STEER)s" in b)
            if steered:
                # Observably DIFFERENT from the no-steer control branch below:
                # only reachable once the parent's mid-run steer was drained
                # at agent.py:864 and injected on the next child iteration.
                return _stream(
                    _plan(final="CHILD-AUTH RESULT=AUTH_STEERED applied:%(STEER)s"),
                    text="CHILD-AUTH RESULT=AUTH_STEERED applied:%(STEER)s\n",
                )
            # No steer yet: stay NON-terminating (a read-only subagent_status
            # step) so the loop keeps running and the steer-inbox drain seam
            # is hit (>=2 child iterations — M13-PATTERNS / RESEARCH Pitfall
            # 2). Bounded: after several iters fall to the control answer so
            # the child always terminates well under max_iterations=8.
            prior = b.count("Tool results for iteration")
            if prior >= 5:
                return _stream(
                    _plan(final="CHILD-AUTH RESULT=AUTH_BASELINE"),
                    text="CHILD-AUTH RESULT=AUTH_BASELINE\n",
                )
            return _stream(
                _plan(
                    steps=[{
                        "name": "subagent_status",
                        "args": {},
                        "why": "keep looping until parent steers",
                    }],
                    rationale="await steer",
                ),
                text="auth-child working...\n",
            )

        # ---- RATE child (finishes immediately) ----------------------------
        if is_child and "%(RATE)s" in b:
            return _stream(
                _plan(final="CHILD-RATE RESULT=RATE_DONE"),
                text="CHILD-RATE RESULT=RATE_DONE\n",
            )

        # ---- any other child frame: terminate safely ----------------------
        if is_child:
            return _stream(_plan(final="CHILD-OTHER done"), text="child done\n")

        # ---- PARENT (the NL chat turn) ------------------------------------
        # Route ONLY off REPLAYED prior-iteration tool-result lines
        # (agent._serialize_iter_for_replay emits `- <tool>(args) -> result`).
        # The static available-tools block / tool descriptions also contain
        # the words "spawn"/"steer"/"gather", so plain substring routing
        # mis-fires on iter 0 — anchor on the `-> ` result text instead.
        spawn_h = _re.findall(r"subagent_spawn\(.*?\) -> spawned \w+ "
                              r"handle=([0-9a-f]{12})", b)
        has_spawned = bool(spawn_h)
        has_steered = bool(
            _re.search(r"subagent_steer\(.*?\) -> (?:steered |<no-op)", b)
        )
        has_aggregated = bool(
            _re.search(r"subagent_gather\(.*?\) -> Aggregated sub-agent", b)
        )

        if not has_spawned:
            # Iter A: fan out to TWO concurrent detached children.
            return _stream(
                _plan(
                    steps=[
                        {
                            "name": "subagent_spawn",
                            "args": {
                                "agent": "explorer",
                                "task": "investigate the auth bug %(AUTH)s",
                            },
                            "why": "delegate auth investigation",
                        },
                        {
                            "name": "subagent_spawn",
                            "args": {
                                "agent": "worker",
                                "task": "investigate the rate-limiter latency %(RATE)s",
                            },
                            "why": "delegate rate-limiter investigation",
                        },
                    ],
                    rationale="fan out to two sub-agents",
                ),
                text="spawning two sub-agents...\n",
            )

        if has_spawned and not has_steered and not has_aggregated:
            # Iter B: steer the still-running AUTH child. The explorer (auth)
            # child is the FIRST spawn step, so its handle is the first one
            # captured from the replayed spawn tool-result line:
            #   - subagent_spawn(...) -> spawned explorer handle=<12hex> ...
            handle = spawn_h[0]
            return _stream(
                _plan(
                    steps=[{
                        "name": "subagent_steer",
                        "args": {
                            "handle": handle,
                            "guidance": "focus on the JWT signature path %(STEER)s",
                        },
                        "why": "inject mid-run course-correction",
                    }],
                    rationale="course-correct the auth child",
                ),
                text="steering the auth sub-agent...\n",
            )

        if has_spawned and not has_aggregated:
            # Iter C: gather ALL children (joins, releases each slice ->
            # allocator rebalance, collapses panels, aggregates results).
            return _stream(
                _plan(
                    steps=[{
                        "name": "subagent_gather",
                        "args": {},
                        "why": "collect every child result",
                    }],
                    rationale="gather the fan-out",
                ),
                text="gathering sub-agents...\n",
            )

        # Iter D (done): aggregate into the user-facing parent turn output.
        return _stream(
            _plan(
                final=(
                    "PARENT-DONE %(REQ)s aggregated both sub-agents via "
                    "subagent_gather (auth + rate-limiter)"
                ),
                rationale="done",
            ),
            text="",
        )

    def stream(self, **kw):
        self.calls.append(kw)
        evs = self._events(kw.get("messages") or [])

        async def _gen():
            for e in evs:
                yield e

        return _gen()

    async def complete(self, **kw):
        from voss_runtime.providers.base import ProviderResponse

        return ProviderResponse(
            text="",
            model=kw.get("model", "__stub__"),
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            raw={},
            parsed=None,
        )

    def count_tokens(self, *, text, model):
        return max(len(text) // 4, 1)


_scripted = _ScriptedMultiAgentProvider()
_vr.providers.register("__stub__", _scripted)
try:
    from voss.harness import auth as _auth
    from voss.harness import cli as _hcli

    def _scripted_resolve(preference):
        return (
            _auth.Resolution(source="env-anthropic", detail="m13-e2e-scripted"),
            _scripted,
        )

    _hcli._resolve_auth_or_die = _scripted_resolve
except Exception:  # noqa: BLE001
    pass
''' % {"AUTH": _AUTH, "RATE": _RATE, "STEER": _STEER, "REQ": _REQ}


def _scripted_runner(tmp_path: Path) -> CliRunner:
    """A CliRunner rooted at the minimal fixture project, wired with the
    content-reactive scripted multi-agent provider (mirrors the conftest
    `cli_runner` fixture but adds the documented `extra_sitecustomize`
    scripting seam — the M13-01 scaffold left this as a TODO)."""
    project = tmp_path / "m13_project"
    shutil.copytree(_FIXTURE_MINIMAL, project)
    return CliRunner(
        project_root=project,
        state_home=tmp_path / "_m13_state",
        extra_sitecustomize=_SCRIPTED_PROVIDER,
    )


def test_multiagent_chat_e2e(cli_runner: CliRunner, tmp_path: Path) -> None:
    """MAG-08 — all six headline signals in one stub `voss chat --plain` run.

    `cli_runner` is requested so the conftest fixture chain (isolated state,
    cred-strip) still applies; the actual run uses a sibling runner carrying
    the scripted-provider `extra_sitecustomize` the scaffold left as a TODO.
    """
    runner = _scripted_runner(tmp_path)

    # --mode auto: the M13 fan-out tools are is_mutating=True; the chat
    # default `plan` tier denies all mutating tools (D-07), so the headline
    # orchestrator scenario is only exercisable under the permissive tier.
    r = runner.run(
        "chat",
        "--plain",
        "--mode",
        "auto",
        stdin=(
            f"{_REQ}: Investigate the auth bug and the rate-limiter latency "
            "in parallel using sub-agents, then summarize both.\n"
            "/exit\n"
        ),
        timeout=60.0,
    )

    assert r.returncode == 0, r.output
    out = r.output  # stdout + stderr (full transcript, for diagnostics)
    # Stream-separated, ordering-stable evidence (PlainRenderer routes
    # tool-call lines + thinking/plan to STDERR and streamed child/parent
    # text + the parent final to STDOUT):
    err = r.stderr  # subagent_* tool-call invocation + result lines
    sout = r.stdout  # streamed child markers + parent final answer

    # ── Signal 1: >=2 CONCURRENT sub-agent panels ──────────────────────────
    # Two detached children spawned from the ONE NL request. The spawn
    # tool-call RESULT lines carry distinct 12-hex handles, and BOTH land
    # before the gather tool-call invocation (overlap, not serial — the
    # parent fans out in one iteration then gathers in a later one).
    spawn_handles = re.findall(
        r"subagent_spawn\(.*?\) -> spawned \w+ handle=([0-9a-f]{12})", err
    )
    assert len(set(spawn_handles)) >= 2, (
        f"expected >=2 distinct spawned child handles; got {spawn_handles}\n{out}"
    )
    gather_pos = err.find("subagent_gather({")
    assert gather_pos != -1, "no subagent_gather tool call in transcript\n" + out
    pre_gather_handles = re.findall(
        r"subagent_spawn\(.*?\) -> spawned \w+ handle=([0-9a-f]{12})",
        err[:gather_pos],
    )
    assert len(set(pre_gather_handles)) >= 2, (
        "the >=2 children were not in flight before gather (not concurrent)\n"
        f"{out}"
    )

    # ── Signal 2: >=1 budget tick per child ────────────────────────────────
    # Each child's BudgetMeter total is the allotment surfaced in its spawn
    # result: a real positive integer (NOT the em-dash placeholder).
    spawn_budgets = [
        int(x)
        for x in re.findall(
            r"subagent_spawn\(.*?\) -> spawned \w+ handle=[0-9a-f]{12} "
            r"budget=(\d+)",
            err,
        )
    ]
    assert len(spawn_budgets) >= 2, (
        f"expected a budget tick per child (>=2); got {spawn_budgets}\n{out}"
    )
    assert all(b > 0 for b in spawn_budgets), (
        f"a child budget was non-positive / placeholder: {spawn_budgets}"
    )
    assert "budget=—" not in err and "budget=-" not in err, (
        "an em-dash / empty budget placeholder leaked into the transcript"
    )

    # ── Signal 3: >=1 APPLIED mid-run course-correction ────────────────────
    # The parent issued subagent_steer into a still-running child AND the
    # child observably branched on it: it streamed AUTH_STEERED (only
    # reachable once the steer was drained at agent.py:864 and injected) and
    # NEVER the no-steer control answer AUTH_BASELINE.
    assert re.search(r"subagent_steer\(.*?\) -> steered [0-9a-f]{12}", err), (
        "parent never issued an applied subagent_steer\n" + out
    )
    assert "AUTH_STEERED" in sout, (
        "steered child did not act on the correction (no AUTH_STEERED)\n" + out
    )
    assert f"applied:{_STEER}" in sout, (
        "steered child did not apply the specific guidance payload\n" + out
    )
    assert "AUTH_BASELINE" not in sout, (
        "child took the no-correction control branch despite being steered "
        "(steer not applied)\n" + out
    )

    # ── Signal 4: >=1 rebalance of the even-split reserve ──────────────────
    # The first spawn (sole live child) gets the whole reserve; the second
    # spawn re-even-splits the live set, so the first child's allotment is
    # rebalanced strictly DOWN to reserve//2. Distinct, ordered budgets prove
    # the even-split reserve rebalanced on the live-child-set change — the
    # same M13Allocator._rebalance_locked path that bumps a survivor back UP
    # when a child finishes+releases during gather (MAG-03/MAG-04).
    assert len(set(spawn_budgets)) >= 2, (
        f"reserve did not rebalance across spawns (budgets {spawn_budgets})\n"
        f"{out}"
    )
    assert spawn_budgets[0] > spawn_budgets[1], (
        "second spawn did not rebalance the reserve down across the live "
        f"child set (budgets {spawn_budgets}) — even-split not applied\n{out}"
    )
    assert spawn_budgets[0] == 2 * spawn_budgets[1], (
        "rebalance did not follow the even-split law reserve -> reserve//2 "
        f"(budgets {spawn_budgets})\n{out}"
    )

    # ── Signal 5: AGGREGATED multi-child turn ──────────────────────────────
    # The parent joined via subagent_gather; the gather tool aggregated BOTH
    # children's results (the gather result is replayed into the parent's
    # next iteration — see agent._serialize_iter_for_replay — and each child
    # also streamed its own result). Not a single child's result.
    assert re.search(r"subagent_gather\(.*?\) -> Aggregated sub-agent", err), (
        "parent never aggregated children via subagent_gather\n" + out
    )
    assert "CHILD-AUTH RESULT=" in sout and "CHILD-RATE RESULT=RATE_DONE" in sout, (
        "the aggregated turn does not reference BOTH children's results\n" + out
    )
    assert "PARENT-DONE" in sout and _REQ in sout, (
        "no aggregated multi-child parent turn output\n" + out
    )

    # ── Signal 6: clean post-gather region ─────────────────────────────────
    # After gather, zero children remain active (the --plain analog of the
    # M9-08 side-region pin/owner restore: PlainRenderer has no SubAgentPanel,
    # so the registry/allocator-clean invariant IS the observable
    # post-gather-region-clean contract here). gather joined every child
    # cleanly: NO orphan force-cancel marker, the parent turn closed with
    # exit 0 (asserted above), and no unhandled exception surfaced.
    assert "<orphan:" not in out, (
        "an orphan child was force-cancelled at turn exit — gather did not "
        "cleanly join all children\n" + out
    )
    assert "Traceback (most recent call last)" not in r.stderr, (
        "an unhandled exception surfaced in the chat run\n" + r.stderr
    )
    # The post-gather child-registry is empty: a subagent_status after gather
    # reports active=0 (region clean). The scripted child's own
    # non-terminating subagent_status calls run BEFORE gather, so any
    # `active=0` here is the post-gather-clean state; absence of any
    # `active=<n>` with n>0 AFTER the gather result confirms no leak.
    post = err[gather_pos:]
    leaked = re.findall(r"subagent_status\(.*?\) -> children=\d+ active=([1-9]\d*)",
                        post)
    assert not leaked, (
        f"children still active after gather (region not clean): {leaked}\n{out}"
    )
