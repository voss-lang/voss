"""V20-02 friction reducer (VRES-02): score the thrash already recorded.

RunRecorder captures failures[]={tool,error} and validation[]={cmd,exit,
summary} per run, but nothing reduced them — a run with 10 failed tool
calls and 5 red validations looked identical to a clean one as long as
the judge passed it. friction() is one pure reducer over those existing
fields: no new capture surface, no provider, no I/O.
"""
from __future__ import annotations

from collections import Counter


def friction(record) -> dict:
    """Reduce record.runs to int friction counters (JSONL-safe).

    {"failed_tools": int, "failed_validations": int, "retries": int,
     "help_probes": int, "wasted_calls": int}  # wasted = sum of the others

    Defensive over old transcripts: missing keys, None values, and
    non-dict runs all contribute zero — never raises.
    """
    failed_tools = 0
    failed_validations = 0
    help_probes = 0
    cmd_counts: Counter[str] = Counter()

    for run in getattr(record, "runs", None) or []:
        if not isinstance(run, dict):
            continue
        failures = run.get("failures")
        if isinstance(failures, list):
            failed_tools += len(failures)
        validations = run.get("validation")
        if not isinstance(validations, list):
            continue
        for entry in validations:
            if not isinstance(entry, dict):
                continue
            exit_code = entry.get("exit")
            if isinstance(exit_code, int) and exit_code != 0:
                failed_validations += 1
            cmd = entry.get("cmd")
            if isinstance(cmd, str) and cmd:
                cmd_counts[cmd] += 1
                if " --help" in cmd:
                    help_probes += 1

    # Cheap retry heuristic: the same validation cmd run k>1 times means
    # k-1 of them were re-checks of work that wasn't done yet.
    retries = sum(count - 1 for count in cmd_counts.values() if count > 1)

    return {
        "failed_tools": failed_tools,
        "failed_validations": failed_validations,
        "retries": retries,
        "help_probes": help_probes,
        "wasted_calls": failed_tools + failed_validations + retries + help_probes,
    }


__all__ = ["friction"]
