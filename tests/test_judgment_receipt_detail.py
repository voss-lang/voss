from dataclasses import asdict, replace
import json

from voss_runtime.judgments import JudgmentReceipt


def _receipt():
    return JudgmentReceipt(
        "c1", "code_recall", "r1", "jev-1.13.0", "jev-1.13.0", "shadow", "ok", None,
        1, 10, 2, 0.0001, 0.0, 12.5, {"order": {"type": "choice"}}, None,
    )


def test_positional_construction_defaults_detail_to_none():
    receipt = _receipt()
    assert receipt.detail is None
    assert receipt.schema_version == 1


def test_replace_detail_keeps_other_fields_and_round_trips():
    receipt = _receipt()
    updated = replace(receipt, detail={"order": ["code:a.py:000"], "trimmed": True})
    assert {**asdict(updated), "detail": None} == asdict(receipt)
    assert json.loads(json.dumps(asdict(updated))) == asdict(updated)


def test_detail_is_last_key():
    assert list(asdict(_receipt()))[-1] == "detail"
