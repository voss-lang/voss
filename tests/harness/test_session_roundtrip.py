"""T2-01: BatchRecord schema + IterationRecord.batches additive field.

Locks the additive substrate for PAR-06: BatchRecord dataclass, the new
batches field on IterationRecord, and the round-trip guarantees that
preserve pre-T2 on-disk fixtures (no "batches" key) and reconstruct
multi-batch iterations losslessly.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import asdict
from pathlib import Path

from voss_runtime import EpisodicMemory

from voss.harness.session import (
    BatchRecord,
    IterationRecord,
    RunRecord,
    SessionRecord,
    load,
    save,
)


class TestBatchRecordSchema:
    def test_defaults_zeroed_with_only_index_required(self) -> None:
        br = BatchRecord(batch_index=0)
        assert br.batch_index == 0
        assert br.step_indices == []
        assert br.parallel_count == 0
        assert br.wall_clock_ms == 0
        assert br.ok_count == 0
        assert br.err_count == 0

    def test_full_payload_preserves_every_field(self) -> None:
        br = BatchRecord(
            batch_index=2,
            step_indices=[3, 4, 5],
            parallel_count=3,
            wall_clock_ms=120,
            ok_count=3,
            err_count=0,
        )
        assert br.batch_index == 2
        assert br.step_indices == [3, 4, 5]
        assert br.parallel_count == 3
        assert br.wall_clock_ms == 120
        assert br.ok_count == 3
        assert br.err_count == 0


class TestIterationRecordAdditive:
    def test_iteration_record_defaults_to_empty_batches(self) -> None:
        rec = IterationRecord(index=0)
        assert rec.batches == []

    def test_asdict_serializes_batches_as_list_of_dicts(self) -> None:
        rec = IterationRecord(
            index=0,
            batches=[
                BatchRecord(batch_index=0, step_indices=[0, 1], parallel_count=2),
                BatchRecord(batch_index=1, step_indices=[3], parallel_count=1),
            ],
        )
        d = dataclasses.asdict(rec)
        assert isinstance(d["batches"], list)
        assert isinstance(d["batches"][0], dict)
        assert set(d["batches"][0].keys()) == {
            "batch_index",
            "step_indices",
            "parallel_count",
            "wall_clock_ms",
            "ok_count",
            "err_count",
        }


class TestPreT2FixtureAdditiveGuarantee:
    def test_iteration_dict_without_batches_key_reconstructs_with_empty_list(
        self,
    ) -> None:
        # Pre-T2 on-disk shape: no "batches" key. Additive default kicks in.
        old_iter = {
            "index": 0,
            "plan": {"rationale": "r", "steps": []},
            "tool_results": [{"tool": "fs_read", "path": "a.py"}],
            "cost_usd": 0.012,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "started_at": "2025-12-01T00:00:00+00:00",
            "ended_at": "2025-12-01T00:00:01+00:00",
            "exit_reason": None,
        }
        rec = IterationRecord(**old_iter)
        assert rec.batches == []

    def test_pre_t2_session_file_loads_with_empty_batches(
        self, tmp_path: Path
    ) -> None:
        sessions_dir = tmp_path / ".voss" / "sessions"
        sessions_dir.mkdir(parents=True)
        sid = "preT2sessab"
        on_disk = {
            "id": sid,
            "name": "pre-t2",
            "cwd": str(tmp_path),
            "model": "stub",
            "started_at": "2025-12-01T00:00:00+00:00",
            "updated_at": "2025-12-01T00:00:05+00:00",
            "total_cost_usd": 0.0,
            "turns": [],
            "runs": [
                {
                    "id": "runabc1",
                    "started_at": "2025-12-01T00:00:00+00:00",
                    "ended_at": "2025-12-01T00:00:05+00:00",
                    "iterations": [
                        {
                            "index": 0,
                            "plan": {},
                            "tool_results": [],
                            "cost_usd": 0.0,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "started_at": "2025-12-01T00:00:00+00:00",
                            "ended_at": "2025-12-01T00:00:01+00:00",
                            "exit_reason": None,
                            # NO "batches" key — pre-T2 fixture shape.
                        }
                    ],
                }
            ],
        }
        (sessions_dir / f"{sid}.json").write_text(json.dumps(on_disk))
        loaded, _ = load(sid, cwd=tmp_path)
        iter_dict = loaded.runs[0]["iterations"][0]
        # Reconstruct through the dataclass to prove the additive default
        # populates batches when the on-disk dict omits the key.
        rebuilt = IterationRecord(**iter_dict)
        assert rebuilt.batches == []


class TestMultiBatchRoundTrip:
    def test_runrecord_with_two_batches_roundtrips_via_asdict(self) -> None:
        b0 = BatchRecord(
            batch_index=0,
            step_indices=[0, 1, 2],
            parallel_count=3,
            wall_clock_ms=120,
            ok_count=3,
            err_count=0,
        )
        b1 = BatchRecord(
            batch_index=1,
            step_indices=[4, 5],
            parallel_count=2,
            wall_clock_ms=80,
            ok_count=1,
            err_count=1,
        )
        it = IterationRecord(index=0, batches=[b0, b1])
        run = RunRecord(id="r1", started_at="t0", ended_at="t1", iterations=[it])
        d = asdict(run)
        # JSON pass-through proves no dataclass-only objects leak through.
        round = json.loads(json.dumps(d))
        # Reconstruct: iterations → IterationRecord, batches → BatchRecord.
        iter_dicts = round["iterations"]
        rebuilt_iters: list[IterationRecord] = []
        for it_d in iter_dicts:
            batch_dicts = it_d.pop("batches", [])
            rebuilt = IterationRecord(**it_d)
            rebuilt.batches = [BatchRecord(**bd) for bd in batch_dicts]
            rebuilt_iters.append(rebuilt)
        run_d = dict(round)
        run_d["iterations"] = rebuilt_iters
        rebuilt_run = RunRecord(**run_d)

        assert len(rebuilt_run.iterations[0].batches) == 2
        assert rebuilt_run.iterations[0].batches[0].batch_index == 0
        assert rebuilt_run.iterations[0].batches[1].batch_index == 1
        # All six fields preserved on both.
        assert rebuilt_run.iterations[0].batches[0].step_indices == [0, 1, 2]
        assert rebuilt_run.iterations[0].batches[0].parallel_count == 3
        assert rebuilt_run.iterations[0].batches[0].wall_clock_ms == 120
        assert rebuilt_run.iterations[0].batches[0].ok_count == 3
        assert rebuilt_run.iterations[0].batches[0].err_count == 0
        assert rebuilt_run.iterations[0].batches[1].step_indices == [4, 5]
        assert rebuilt_run.iterations[0].batches[1].parallel_count == 2
        assert rebuilt_run.iterations[0].batches[1].wall_clock_ms == 80
        assert rebuilt_run.iterations[0].batches[1].ok_count == 1
        assert rebuilt_run.iterations[0].batches[1].err_count == 1

    def test_session_file_preserves_batches_through_save_and_load(
        self, tmp_path: Path
    ) -> None:
        b0 = BatchRecord(
            batch_index=0,
            step_indices=[0, 1, 2],
            parallel_count=3,
            wall_clock_ms=120,
            ok_count=3,
            err_count=0,
        )
        b1 = BatchRecord(
            batch_index=1,
            step_indices=[4, 5],
            parallel_count=2,
            wall_clock_ms=80,
            ok_count=2,
            err_count=0,
        )
        it = IterationRecord(index=0, batches=[b0, b1])
        run = RunRecord(id="r1", started_at="t0", ended_at="t1", iterations=[it])

        session = SessionRecord.new(cwd=tmp_path, model="stub")
        session.runs.append(asdict(run))
        save(session, EpisodicMemory(capacity=10))

        loaded, _ = load(session.id, cwd=tmp_path)
        batches_on_disk = loaded.runs[0]["iterations"][0]["batches"]
        assert len(batches_on_disk) == 2
        assert batches_on_disk[0]["batch_index"] == 0
        assert batches_on_disk[1]["batch_index"] == 1
        assert batches_on_disk[0]["step_indices"] == [0, 1, 2]
        assert batches_on_disk[0]["parallel_count"] == 3
        assert batches_on_disk[0]["wall_clock_ms"] == 120
        assert batches_on_disk[0]["ok_count"] == 3
        assert batches_on_disk[0]["err_count"] == 0
        assert batches_on_disk[1]["step_indices"] == [4, 5]
        assert batches_on_disk[1]["parallel_count"] == 2
        assert batches_on_disk[1]["wall_clock_ms"] == 80
