---
phase: V20-edict-residue-hardening
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/eval/friction.py
  - voss/eval/runner.py
  - voss/eval/summary.py
  - tests/eval/test_friction.py
autonomous: true
requirements: [VEDR-02]
must_haves:
  truths:
    - "Fixture transcript with N planted failed tool calls scores friction.failed_tools == N; zero-failure record scores 0 across all fields"
    - "Reducer is pure: consumes existing recorder fields only (failures[], validation[]), captures nothing new, no provider, no I/O"
    - "Every eval row gains one `friction` field and summary.md gains one friction column; existing row fields and summary columns byte-stable"
  artifacts:
    - path: "voss/eval/friction.py"
      provides: "pure reducer friction(record) -> dict over SessionRecord.runs"
      contains: "def friction"
    - path: "tests/eval/test_friction.py"
      provides: "RED-first reducer tests with synthetic run dicts (no live model)"
      contains: "test_friction_counts_planted_failures"
  key_links:
    - from: "voss/eval/runner.py"
      to: "voss.eval.friction"
      via: "row['friction'] = friction(record) next to _extract_signals at runner.py:718, row built at :746"
      pattern: "friction"
    - from: "voss/eval/summary.py"
      to: "row['friction']"
      via: "mean wasted-calls column in write_summary task table + totals"
      pattern: "friction"
---

<objective>
Score the friction already being recorded. RunRecorder captures failures[]={tool,error}
(recorder.py:241-243) and validation[]={cmd,exit,summary} (recorder.py:258-266) per run, but
nothing reduces them: eval rows (runner.py:746) carry success/cost/tokens/confidence and
summary.py aggregates pass-rate/mean-cost only. A run that thrashes (10 failed tool calls,
5 red validations, retries) looks identical to a clean one as long as the judge passes it.

One pure reducer over existing fields. No new capture surface.
</objective>

<context>
- Recorder fields: voss/harness/recorder.py:241 (failures), :258-266 (validation; exit parsed
  via _parse_exit, may be None).
- SessionRecord.runs: list of per-run dicts — confirm exact key names recorder.finalize/
  to_run_record emits (`failures`, `validation`) before writing the reducer; cited fields are
  dataclass attrs on RunRecorder, verify they survive serialization.
- Row build: voss/eval/runner.py:746-770; signals extracted at :718 (_extract_signals pattern
  at :118 is the template for iterating record.runs defensively).
- Summary: voss/eval/summary.py write_summary:49 — per-task table rows ~85-103, totals ~127.
</context>

<tasks>

## Task 1 — RED tests (commit 1: `test(eval): RED friction reducer cases`)
tests/eval/test_friction.py with synthetic SessionRecord-shaped objects (match how
tests/eval already fakes records):
1. `test_friction_counts_planted_failures` — N entries in failures[] → failed_tools == N.
2. `test_friction_counts_red_validations` — validation entries with exit in {1,2} counted;
   exit 0 and exit None not counted.
3. `test_friction_zero_clean_run` — empty failures/validation → all-zero dict.
4. `test_friction_repeat_command_retries` — same validation cmd appearing k>1 times → retries
   == k-1 (the cheap retry heuristic; --help probe: cmd containing ` --help` counted as probe).
5. `test_friction_missing_keys_tolerated` — run dict without failures/validation keys → zeros,
   no KeyError (old transcripts must not crash summaries).

## Task 2 — reducer (commit 2: `feat(eval): friction reducer`)
voss/eval/friction.py:
```python
def friction(record) -> dict:
    # {"failed_tools": int, "failed_validations": int, "retries": int,
    #  "help_probes": int, "wasted_calls": int}  # wasted = sum of the others
```
Pure function over record.runs; defensive .get() everywhere; ints only (JSONL-safe).

## Task 3 — wire row + summary (commit 3: `feat(eval): friction column in rows + summary`)
- runner.py: `row["friction"] = friction(record)` in the row dict at :746 (single nested dict
  field — keeps JSONL schema additive).
- summary.py: per-task `mean_wasted` column (mean of row["friction"]["wasted_calls"] over
  task rows, "n/a" when absent) + overall mean in totals. Tolerate rows lacking the field.

## Task 4 — GREEN + suite
`.venv/bin/python -m pytest tests/eval -q` green; assert no existing summary fixture/golden
test broke (summary column is additive — if a golden exists, update it in the same commit and
say so in the summary).
</tasks>

<verification>
- Fixture transcript with N planted failed calls scores N (headline verify line).
- Eval row + summary each gain exactly one field/column; nothing else moves.
</verification>
