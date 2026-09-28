"""Regenerate the Python reference results: .venv/bin/python gen.py

commands.txt -> commands.golden: one JSON line per command with
sandbox.shell_allowed and shlex.split. vossmd/NAME.md -> vossmd/NAME.out:
voss_md.append_voss_notes_bullet with the note "added note" at a fixed time.
"""
import json
import shlex
import shutil
import tempfile
from pathlib import Path

from voss.harness import sandbox, voss_md

here = Path(__file__).parent
rows = []
for cmd in (here / "commands.txt").read_text().splitlines():
    allowed, reason = sandbox.shell_allowed(cmd)
    try:
        split = shlex.split(cmd)
    except ValueError as exc:
        split = "error: " + str(exc)
    rows.append(json.dumps({"cmd": cmd, "allowed": allowed, "reason": reason, "split": split}))
(here / "commands.golden").write_text("\n".join(rows) + "\n")

for md in sorted((here / "vossmd").glob("*.md")):
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "VOSS.md"
        shutil.copy(md, target)
        if md.stat().st_size == 0:
            target.unlink()
        voss_md.append_voss_notes_bullet(target, "added note", "2026-09-27T12:00:00+00:00")
        (md.with_suffix(".out")).write_text(target.read_text())
