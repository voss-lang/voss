"""Real server, synthetic turns only. No provider credentials or tools."""
import asyncio
import os
from pathlib import Path

os.environ["VOSS_SERVE_FAKE_TURN"] = "1"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"
os.environ["XDG_STATE_HOME"] = str(Path.cwd() / "state")
os.environ["XDG_CONFIG_HOME"] = str(Path.cwd() / "config")
os.environ["VOSS_HOME"] = str(Path.cwd() / "voss")

from voss.harness.server import app as appmod
from voss.harness.server.renderer import EventBusRenderer
from voss.harness.server.serve import run_server


async def turn(session, text, mode):
    with Path("starts").open("a") as output:
        output.write("start\n")
    renderer = EventBusRenderer(session.queue, session_id=session.id)
    renderer.show_warning("synthetic nonfatal warning")
    renderer.session_idle()
    if text == "wait":
        await asyncio.Event().wait()
    await asyncio.sleep(0.1)
    session.turn_outcome = "done"


appmod._run_turn = turn
run_server(token="synthetic-sdk-replay")
