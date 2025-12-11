"""Evaluation runner that loads curated test questions and scores them via eval_judge."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from chat_pipeline.evaluation.eval_judge import (
    build_rag_inputs,
    compute_performance_metrics,
    evaluate_with_llm,
)
from chat_pipeline.rag.pipeline import PipelineResult
from chat_pipeline.evaluation.judge_client import JudgeClient
from chat_pipeline.utils.runtime_env import consecutive_failure_limit, task_timeout_seconds
from chat_pipeline.rag.config_manager import get_generation_config

logger = logging.getLogger(__name__)

@dataclass
class EvaluationConfig:
    """User-supplied configuration for an evaluation run."""

    test_questions_dir: Path
    output_dir: Path
    max_examples: Optional[int] = None
    wandb_project: Optional[str] = None
    wandb_entity: Optional[str] = None
    disable_wandb: bool = False
    dataset_label: Optional[str] = None
    slice_fields: List[str] = field(default_factory=lambda: ["category", "company_name"])
    wandb_tags: List[str] = field(default_factory=list)
    wandb_run_name: Optional[str] = None


@dataclass
class EvaluationExample:
    """Single query/answer pair plus annotations."""

    query: str
    reference_answer: str
    reference_contexts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricResult:
    """Container for computed metric values."""

    precision: Optional[float] = None
    recall: Optional[float] = None
    latency_total: Optional[float] = None
    latency_breakdown: Dict[str, float] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    groundedness: Optional[float] = None
    answer_relevance: Optional[float] = None
    conciseness: Optional[float] = None
    retrieval_diversity: Optional[float] = None
    reranker_gain: Optional[float] = None
    coherence: Optional[float] = None
    factual_correctness: Optional[float] = None
    hallucination_score: Optional[float] = None
    structure_adherence: Optional[float] = None
    cost_per_query: Optional[float] = None
    memory_utilization: Optional[float] = None
    throughput_qps: Optional[float] = None


def _iter_question_records(root: Path) -> Iterable[Tuple[str, Dict[str, Any]]]:
    if not root.exists():
        raise FileNotFoundError(f"Test question directory not found: {root}")

    # Support a single dataset file directly under the root (e.g., .../slices/dataset.jsonl).
    direct_files = [
        path
        for path in (
            root / "dataset.json",
            root / "dataset.jsonl",
        )
        if path.exists()
    ]
    if direct_files:
        dataset_file = direct_files[0]
        try:
            with dataset_file.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except Exception:
                        logger.debug("Skipping malformed JSON line in %s", dataset_file)
                        continue
                    if isinstance(payload, dict):
                        yield root.name, payload
        except Exception as exc:
            logger.warning("Failed to load %s: %s", dataset_file, exc)
        return

    for category_dir in sorted(root.iterdir()):
        if not category_dir.is_dir():
            continue
        dataset_file = category_dir / "dataset.json"
        jsonl_file = category_dir / "dataset.jsonl"
        if not dataset_file.exists() and jsonl_file.exists():
            dataset_file = jsonl_file
        if not dataset_file.exists():
            logger.debug("Skipping %s (dataset.json/jsonl not found)", category_dir)
            continue
        try:
            with dataset_file.open("r", encoding="utf-8") as handle:
                first_non_ws = ""
                while True:
                    char = handle.read(1)
                    if not char:
                        break
                    if not char.isspace():
                        first_non_ws = char
                        break
                handle.seek(0)
                if first_non_ws == "[":
                    payload = json.load(handle)
                    records = payload if isinstance(payload, list) else []
                else:
                    records = []
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.debug("Skipping malformed JSON line in %s", dataset_file)
            for record in records:
                if isinstance(record, dict):
                    yield category_dir.name, record
        except Exception as exc:
            logger.warning("Failed to load %s: %s", dataset_file, exc)


def _record_to_example(category: str, record: Dict[str, Any]) -> Optional[EvaluationExample]:
    question = (
        record.get("new_question")
        or record.get("original_question")
        or record.get("question")
        or record.get("prompt")
    )
    if not question or not isinstance(question, str):
        return None
    reference_answer = (
        record.get("new_solution")
        or record.get("original_solution")
        or record.get("answer")
        or ""
    )
    metadata: Dict[str, Any] = {
        "category": category,
        "source": record.get("source"),
        "company_name": record.get("company") or record.get("company_name"),
    }
    # Carry through additional metadata fields when present (e.g., slice/domain/difficulty).
    for key in ("slice", "domain", "difficulty"):
        if record.get(key) is not None:
            metadata[key] = record[key]
    return EvaluationExample(
        query=question.strip(),
        reference_answer=str(reference_answer or ""),
        reference_contexts=record.get("reference_contexts") or [],
        metadata=metadata,
    )


def _load_test_examples(root: Path, max_examples: Optional[int]) -> List[EvaluationExample]:
    examples: List[EvaluationExample] = []
    for category, record in _iter_question_records(root):
        example = _record_to_example(category, record)
        if example:
            examples.append(example)
        if max_examples is not None and len(examples) >= max_examples:
            break
    if not examples:
        raise RuntimeError(f"No evaluation questions found under {root}")
    logger.info("Loaded %s evaluation questions from %s", len(examples), root)
    return examples


class WandbTracker:
    def __init__(self, config: EvaluationConfig):
        self.enabled = not config.disable_wandb
        self._run = None
        self._tags = list(config.wandb_tags or [])
        if not self.enabled:
            logger.info("W&B logging disabled via CLI flag.")
            return
        try:
            import wandb
        except ImportError:
            logger.warning("wandb not installed; skipping experiment tracking.")
            self.enabled = False
            return
        project = config.wandb_project or os.getenv("WANDB_PROJECT") or "rag-eval"
        entity = config.wandb_entity or os.getenv("WANDB_ENTITY")
        self._run = wandb.init(
            project=project,
            entity=entity,
            config={"test_dir": str(config.test_questions_dir)},
            tags=self._tags or None,
            name=self._build_run_name(config),
        )

    @staticmethod
    def _sanitize_key(value: str) -> str:
        return value.lower().replace(" ", "_").replace("/", "_")

    def _build_run_name(self, config: EvaluationConfig) -> Optional[str]:
        if config.wandb_run_name:
            return config.wandb_run_name
        label = config.dataset_label or config.test_questions_dir.name
        return f"eval-{self._sanitize_key(label)}"

    def log_summary(
        self,
        dataset_label: str,
        summary: Dict[str, Any],
        slice_metrics: Dict[str, float],
        fallback_count: int,
    ) -> None:
        if not self.enabled or self._run is None:
            return
        try:
            import wandb
        except ImportError:
            return

        payload: Dict[str, Any] = {}
        safe_label = self._sanitize_key(dataset_label or "dataset")
        for key, value in (summary or {}).items():
            if isinstance(value, (int, float)):
                payload[f"{safe_label}.{key}"] = float(value)
        payload.update(slice_metrics or {})
        payload["backend_fallback_count"] = fallback_count
        payload["dataset_label"] = dataset_label
        wandb.log(payload)

    def log_artifacts(self, artifacts: Dict[str, Path]) -> None:
        if not self.enabled or self._run is None or not artifacts:
            return
        try:
            import wandb
        except ImportError:
            return

        import time as _time

        for name, path in artifacts.items():
            if not path or not path.exists():
                continue
            artifact = wandb.Artifact(f"{name}-{int(_time.time())}", type="evaluation")
            artifact.add_file(str(path))
            self._run.log_artifact(artifact)

    def finish(self) -> None:
        if not self.enabled or self._run is None:
            return
        try:
            import wandb

            wandb.finish()
        except Exception as exc:
            logger.warning("Failed to finish W&B run: %s", exc)


class EvaluationRunner:
    """Coordinates dataset loading, judge execution, and metric aggregation."""

    def __init__(
        self,
        config: EvaluationConfig,
        config_overrides: Optional[Dict[str, Any]] = None,
        *,
        mode: str = "full",
    ):
        self.config = config
        self.results: List[MetricResult] = []
        self._examples: List[Tuple[EvaluationExample, MetricResult]] = []
        self._example_records: List[Dict[str, Any]] = []
        self._judge_client = JudgeClient()
        self._wandb = WandbTracker(config)
        self._config_overrides = config_overrides or {}
        self._expected_backend = self._resolve_expected_backend(self._config_overrides)
        self.backend_fallbacks = 0
        self.mode = mode

    def run(self) -> None:
        if self.mode == "judge":
            self._run_judge_from_artifacts()
            return

        examples = _load_test_examples(self.config.test_questions_dir, self.config.max_examples)
        task_timeout = task_timeout_seconds()
        max_failures = consecutive_failure_limit()
        consecutive_failures = 0
        for idx, example in enumerate(examples, start=1):
            start = time.perf_counter()
            try:
                answer, contexts, pipeline_result, metrics = self._generate_with_timeout(
                    example, task_timeout, judge=self.mode == "full"
                )
                if self.mode == "full":
                    self.results.append(metrics)
                    self._examples.append((example, metrics))
                self._persist_intermediate(example, metrics, answer, contexts, idx, pipeline_result.generation_backend)
                consecutive_failures = 0
            except FuturesTimeout:
                consecutive_failures += 1
                logger.error("Evaluation timed out for query '%s' after %.0fs", example.query, task_timeout)
            except Exception as exc:
                consecutive_failures += 1
                logger.exception("Evaluation failed for query '%s': %s", example.query, exc)
            finally:
                duration = time.perf_counter() - start
                logger.debug("Processed example %s in %.2fs", idx, duration)
            if consecutive_failures >= max_failures:
                raise RuntimeError(f"Aborting after {consecutive_failures} consecutive evaluation failures.")

        self._export_examples()
        self._write_generation_meta()

        if self.mode == "generate":
            logger.info("Generation-only mode complete. Run judge-only mode to score results.")
            return

        summary_artifact = self._export_summary()
        bias_artifact = self._export_bias_report()
        self._finalize_reporting(summary_artifact, bias_artifact)

    def _evaluate_example(self, example: EvaluationExample) -> Tuple[MetricResult, str, List[str]]:
        answer, contexts, pipeline_result = build_rag_inputs(
            example.query,
            example.metadata.get("company_name"),
            config_overrides=self._config_overrides,
        )
        scores = evaluate_with_llm(
            example.query,
            contexts,
            answer,
            model="gpt-4o-mini",
            judge_client=self._judge_client,
        )
        perf = compute_performance_metrics(pipeline_result, answer, contexts)
        combined = {**scores, **perf}
        backend_used = pipeline_result.generation_backend or os.getenv("GENERATION_BACKEND") or "auto"
        self._record_backend_usage(backend_used)
        latency_total = perf.get("latency")
        metric = MetricResult(
            precision=scores.get("precision"),
            recall=scores.get("recall"),
            latency_total=latency_total,
            latency_breakdown=pipeline_result.timings or {},
            retrieval_diversity=scores.get("retrieval_diversity"),
            reranker_gain=scores.get("reranker_gain"),
            context_precision=scores.get("context_precision"),
            context_recall=scores.get("context_recall"),
            groundedness=scores.get("groundedness"),
            answer_relevance=scores.get("relevance"),
            conciseness=scores.get("conciseness"),
            coherence=scores.get("coherence"),
            factual_correctness=scores.get("factual_correctness"),
            hallucination_score=scores.get("hallucination"),
            structure_adherence=scores.get("structure_adherence"),
            cost_per_query=perf.get("cost_per_query"),
            memory_utilization=perf.get("memory_utilization"),
            throughput_qps=perf.get("throughput"),
            token_usage={"total": int(perf.get("token_usage", 0))},
        )
        return metric, answer, contexts

    def _generate_with_timeout(
        self,
        example: EvaluationExample,
        timeout: float,
        *,
        judge: bool,
    ) -> Tuple[str, List[str], PipelineResult, MetricResult]:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._generate_example, example, judge)
            return future.result(timeout=timeout)

    def _generate_example(
        self,
        example: EvaluationExample,
        judge: bool,
    ) -> Tuple[str, List[str], PipelineResult, MetricResult]:
        answer, contexts, pipeline_result = build_rag_inputs(
            example.query,
            example.metadata.get("company_name"),
            config_overrides=self._config_overrides,
        )
        backend_used = pipeline_result.generation_backend or os.getenv("GENERATION_BACKEND") or "auto"
        self._record_backend_usage(backend_used)
        perf = compute_performance_metrics(pipeline_result, answer, contexts)
        perf["token_usage_dict"] = {"total": int(perf.get("token_usage", 0))}
        scores = None
        if judge:
            scores = evaluate_with_llm(
                example.query,
                contexts,
                answer,
                model="gpt-4o-mini",
                judge_client=self._judge_client,
            )
        metric = self._build_metric_result(scores, perf, pipeline_result.timings or {})
        return answer, contexts, pipeline_result, metric

    def _build_metric_result(
        self,
        scores: Optional[Dict[str, float]],
        perf: Dict[str, Any],
        latency_breakdown: Dict[str, float],
    ) -> MetricResult:
        token_usage_dict = perf.get("token_usage_dict") or {}
        if not isinstance(token_usage_dict, dict):
            token_usage_dict = {"total": int(perf.get("token_usage", 0))}
        return MetricResult(
            precision=scores.get("precision") if scores else None,
            recall=scores.get("recall") if scores else None,
            retrieval_diversity=scores.get("retrieval_diversity") if scores else None,
            reranker_gain=scores.get("reranker_gain") if scores else None,
            context_precision=scores.get("context_precision") if scores else None,
            context_recall=scores.get("context_recall") if scores else None,
            groundedness=scores.get("groundedness") if scores else None,
            answer_relevance=scores.get("relevance") if scores else None,
            conciseness=scores.get("conciseness") if scores else None,
            coherence=scores.get("coherence") if scores else None,
            factual_correctness=scores.get("factual_correctness") if scores else None,
            hallucination_score=scores.get("hallucination") if scores else None,
            structure_adherence=scores.get("structure_adherence") if scores else None,
            latency_total=perf.get("latency"),
            latency_breakdown=latency_breakdown,
            token_usage=token_usage_dict,
            cost_per_query=perf.get("cost_per_query"),
            memory_utilization=perf.get("memory_utilization"),
            throughput_qps=perf.get("throughput"),
        )

    def _run_judge_from_artifacts(self) -> None:
        self._load_generation_meta()
        examples_path = self.config.output_dir / "examples.jsonl"
        if not examples_path.exists():
            raise FileNotFoundError(f"No stored generation outputs found at {examples_path}")
        updated_records: List[Dict[str, Any]] = []
        with examples_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                example = EvaluationExample(
                    query=record.get("question", ""),
                    reference_answer="",
                    reference_contexts=[],
                    metadata=record.get("metadata") or {},
                )
                answer = record.get("answer", "")
                contexts = record.get("contexts") or []
                stored_metrics = record.get("metrics") or {}
                scores = evaluate_with_llm(
                    example.query,
                    contexts,
                    answer,
                    model="gpt-4o-mini",
                    judge_client=self._judge_client,
                )
                perf = self._perf_from_stored_metrics(stored_metrics)
                latency_breakdown = stored_metrics.get("latency_breakdown") or {}
                metric = self._build_metric_result(scores, perf, latency_breakdown)
                self.results.append(metric)
                self._examples.append((example, metric))
                record["metrics"] = metric.__dict__
                updated_records.append(record)
        self._example_records = updated_records
        self._export_examples()
        summary_artifact = self._export_summary()
        bias_artifact = self._export_bias_report()
        self._finalize_reporting(summary_artifact, bias_artifact)

    def _write_generation_meta(self) -> None:
        meta_path = self.config.output_dir / "generation_meta.json"
        payload = {
            "backend_fallbacks": self.backend_fallbacks,
            "generated_at": datetime.utcnow().isoformat(),
        }
        meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_generation_meta(self) -> None:
        meta_path = self.config.output_dir / "generation_meta.json"
        if not meta_path.exists():
            return
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        self.backend_fallbacks = int(payload.get("backend_fallbacks", 0))

    @staticmethod
    def _perf_from_stored_metrics(stored: Dict[str, Any]) -> Dict[str, Any]:
        token_usage_dict = stored.get("token_usage") or {}
        token_total = token_usage_dict.get("total")
        return {
            "latency": stored.get("latency_total"),
            "token_usage": token_total,
            "token_usage_dict": token_usage_dict,
            "cost_per_query": stored.get("cost_per_query"),
            "memory_utilization": stored.get("memory_utilization"),
            "throughput": stored.get("throughput_qps"),
        }

    def _finalize_reporting(
        self,
        summary_artifact: Optional[Tuple[Path, Dict[str, Any]]],
        bias_artifact: Optional[Tuple[Path, Dict[str, Any]]],
    ) -> None:
        summary_data = summary_artifact[1] if summary_artifact else {}
        bias_data = bias_artifact[1] if bias_artifact else {}
        dataset_label = self.config.dataset_label or self.config.test_questions_dir.name
        slice_metrics = self._build_slice_metric_payload(bias_data)
        if summary_data or slice_metrics:
            self._wandb.log_summary(dataset_label, summary_data or {}, slice_metrics, self.backend_fallbacks)
        artifact_payload: Dict[str, Path] = {}
        if summary_artifact:
            artifact_payload["summary"] = summary_artifact[0]
        if bias_artifact:
            artifact_payload["bias_report"] = bias_artifact[0]
        self._wandb.log_artifacts(artifact_payload)
        self._wandb.finish()

    def _resolve_expected_backend(self, overrides: Optional[Dict[str, Any]]) -> str:
        overrides = overrides or {}
        backend = (
            ((overrides.get("generation") or {}).get("backend"))
            or os.getenv("GENERATION_BACKEND")
            or get_generation_config().get("backend")
        )
        return str(backend).lower() if backend else "auto"

    def _record_backend_usage(self, backend_used: Optional[str]) -> None:
        if self._expected_backend in (None, "auto"):
            return
        if backend_used is None:
            self.backend_fallbacks += 1
            return
        if backend_used.lower() != self._expected_backend:
            self.backend_fallbacks += 1

    def _build_slice_metric_payload(self, bias_report: Optional[Dict[str, Any]]) -> Dict[str, float]:
        payload: Dict[str, float] = {}
        metrics = (bias_report or {}).get("metrics") or {}
        for field, entries in metrics.items():
            for entry in entries or []:
                slice_value = str(entry.get("slice_value", "unknown"))
                base = f"slice.{field}.{slice_value}".lower().replace(" ", "_")
                count = entry.get("count")
                if isinstance(count, (int, float)):
                    payload[f"{base}.count"] = float(count)
                for metric_name, metric_value in (entry.get("metrics") or {}).items():
                    if isinstance(metric_value, (int, float)):
                        payload[f"{base}.{metric_name}"] = float(metric_value)
        return payload

    def _persist_intermediate(
        self,
        example: EvaluationExample,
        metrics: MetricResult,
        answer: str,
        contexts: List[str],
        index: int,
        generation_backend: Optional[str],
    ) -> None:
        record = {
            "index": index,
            "question": example.query,
            "category": example.metadata.get("category"),
            "metadata": example.metadata,
            "answer": answer,
            "contexts": contexts,
            "metrics": metrics.__dict__,
            "generation_backend": generation_backend,
        }
        self._example_records.append(record)

    def _export_examples(self) -> None:
        if not self._example_records:
            logger.warning("No examples to write.")
            return
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        examples_path = self.config.output_dir / "examples.jsonl"
        with examples_path.open("w", encoding="utf-8") as handle:
            for record in self._example_records:
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
        logger.info("Wrote consolidated examples to %s", examples_path)

    def _export_summary(self) -> Optional[Tuple[Path, Dict[str, Any]]]:
        if not self.results:
            logger.warning("No evaluation results to summarize.")
            return None
        summary = {}
        count = len(self.results)
        for field in (
            "precision",
            "recall",
            "retrieval_diversity",
            "reranker_gain",
            "context_precision",
            "context_recall",
            "groundedness",
            "answer_relevance",
            "conciseness",
            "coherence",
            "factual_correctness",
            "hallucination_score",
            "structure_adherence",
            "cost_per_query",
            "memory_utilization",
            "throughput_qps",
            "latency_total",
        ):
            values = [getattr(result, field) for result in self.results if getattr(result, field) is not None]
            if values:
                summary[field] = sum(values) / len(values)
        summary["examples"] = count
        summary_path = self.config.output_dir / "summary.json"
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
        logger.info("Wrote evaluation summary to %s", summary_path)
        return summary_path, summary

    def _export_bias_report(self) -> Optional[Tuple[Path, Dict[str, Any]]]:
        if not self._examples:
            logger.info("No examples to compute bias report.")
            return None

        slice_fields = self.config.slice_fields or []
        dataset_label = self.config.dataset_label or self.config.test_questions_dir.name
        bias_metrics = ("groundedness", "answer_relevance", "factual_correctness")

        # Build per-slice aggregates.
        aggregates: Dict[str, Dict[str, Dict[str, float]]] = {}
        counts: Dict[str, Dict[str, int]] = {}

        for example, metrics in self._examples:
            for field in slice_fields:
                value = (example.metadata or {}).get(field)
                if value in (None, ""):
                    continue
                aggregates.setdefault(field, {}).setdefault(value, {})
                counts.setdefault(field, {}).setdefault(value, 0)
                counts[field][value] += 1
                for metric_name in bias_metrics:
                    metric_value = getattr(metrics, metric_name, None)
                    if metric_value is None:
                        continue
                    aggregates[field][value].setdefault(metric_name, 0.0)
                    aggregates[field][value][metric_name] += float(metric_value)

        # Convert sums to averages.
        report: Dict[str, Any] = {
            "dataset": dataset_label,
            "slice_fields": slice_fields,
            "metrics": {},
        }

        for field, values in aggregates.items():
            field_report = []
            for value, metric_sums in values.items():
                count = counts[field][value]
                averaged = {name: total / count for name, total in metric_sums.items() if count > 0}
                field_report.append(
                    {
                        "slice_value": value,
                        "count": count,
                        "metrics": averaged,
                    }
                )
            report["metrics"][field] = field_report

        bias_path = self.config.output_dir / "bias_report.json"
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        with bias_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
        logger.info("Wrote bias report to %s", bias_path)
        return bias_path, report



def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG evaluation harness.")
    parser.add_argument(
        "--test-dir",
        default=Path("chat_pipeline/evaluation/test_questions"),
        type=Path,
        help="Directory containing generated test question folders.",
    )
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for evaluation artifacts.")
    parser.add_argument("--max-examples", type=int, help="Limit number of questions to evaluate.")
    parser.add_argument("--wandb-project", help="Weights & Biases project name.")
    parser.add_argument("--wandb-entity", help="Weights & Biases entity/team.")
    parser.add_argument("--disable-wandb", action="store_true", help="Disable Weights & Biases logging.")
    parser.add_argument(
        "--dataset-label",
        help="Optional label to include in reports (e.g., 'main', 'slices'). Defaults to test-dir name.",
    )
    parser.add_argument(
        "--slice-fields",
        help="Comma-separated metadata fields to slice bias metrics on (e.g., category,company_name).",
    )
    return parser.parse_args()


def main() -> None:
    from chat_pipeline.utils.logger import setup_logging
    setup_logging(level=os.getenv("EVAL_RUNNER_LOG_LEVEL"))
    args = _parse_args()
    config = EvaluationConfig(
        test_questions_dir=args.test_dir,
        output_dir=args.output_dir,
        max_examples=args.max_examples,
        wandb_project=args.wandb_project,
        wandb_entity=args.wandb_entity,
        disable_wandb=args.disable_wandb,
        dataset_label=args.dataset_label,
        slice_fields=[item.strip() for item in args.slice_fields.split(",")] if args.slice_fields else ["category", "company_name"],
    )
    runner = EvaluationRunner(config)
    runner.run()


if __name__ == "__main__":
    main()
