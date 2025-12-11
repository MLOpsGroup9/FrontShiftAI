import json
from pathlib import Path

import pytest

from chat_pipeline.evaluation.evaluation_runner import (
    EvaluationConfig,
    EvaluationRunner,
    MetricResult,
    _load_test_examples,
    _record_to_example,
    WandbTracker,
)


def test_record_to_example_builds_expected_metadata():
    record = {
        "new_question": " What is the policy? ",
        "new_solution": "Answer",
        "company": "Acme",
        "source": "handbook",
        "reference_contexts": ["c1", "c2"],
    }

    example = _record_to_example("policies", record)

    assert example.query == "What is the policy?"
    assert example.reference_answer == "Answer"
    assert example.reference_contexts == ["c1", "c2"]
    assert example.metadata["category"] == "policies"
    assert example.metadata["company_name"] == "Acme"
    assert example.metadata["source"] == "handbook"


def test_load_test_examples_reads_json_payload(tmp_path: Path):
    test_dir = tmp_path / "category"
    test_dir.mkdir()
    dataset = [{"question": "q1", "answer": "a1"}, {"prompt": "q2", "answer": "a2"}]
    (test_dir / "dataset.json").write_text(json.dumps(dataset), encoding="utf-8")

    examples = _load_test_examples(tmp_path, max_examples=None)

    assert len(examples) == 2
    assert examples[0].query == "q1"
    assert examples[1].query == "q2"


def test_load_test_examples_raises_when_empty(tmp_path: Path):
    tmp_path.mkdir(exist_ok=True)
    with pytest.raises(RuntimeError):
        _load_test_examples(tmp_path, max_examples=None)


def test_wandb_tracker_respects_disable_flag(monkeypatch):
    cfg = EvaluationConfig(
        test_questions_dir=Path("/tmp/questions"),
        output_dir=Path("/tmp/output"),
        disable_wandb=True,
    )
    tracker = WandbTracker(cfg)
    # Should be disabled without attempting any wandb import/calls.
    assert tracker.enabled is False


def test_persist_intermediate_writes_answer_and_contexts(tmp_path: Path):
    runner = object.__new__(EvaluationRunner)
    runner.config = EvaluationConfig(
        test_questions_dir=tmp_path,
        output_dir=tmp_path,
    )
    runner._example_records = []

    example = _record_to_example(
        "category",
        {"question": "q", "answer": "a", "company": "ACME"},
    )
    metrics = MetricResult(precision=1.0)

    runner._persist_intermediate(
        example=example,
        metrics=metrics,
        answer="answer text",
        contexts=["ctx1", "ctx2"],
        index=1,
        generation_backend="local",
    )
    runner._export_examples()

    data = (tmp_path / "examples.jsonl").read_text(encoding="utf-8").strip().splitlines()
    written = [json.loads(line) for line in data]
    assert written[0]["answer"] == "answer text"
    assert written[0]["contexts"] == ["ctx1", "ctx2"]
