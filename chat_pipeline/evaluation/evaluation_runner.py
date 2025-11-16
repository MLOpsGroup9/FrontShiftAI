"""Evaluation runner that loads curated test questions and scores them via eval_judge."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from chat_pipeline.evaluation.eval_judge import (
    build_rag_inputs,
    compute_performance_metrics,
    evaluate_with_llm,
)
from chat_pipeline.evaluation.judge_client import JudgeClient

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

    for category_dir in sorted(root.iterdir()):
        if not category_dir.is_dir():
            continue
        dataset_file = category_dir / "dataset.json"
        if not dataset_file.exists():
            logger.debug("Skipping %s (dataset.json not found)", category_dir)
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
    metadata = {
        "category": category,
        "source": record.get("source"),
        "company_name": record.get("company") or record.get("company_name"),
    }
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
        try:
            self._run = wandb.init(project=project, entity=entity, config={"test_dir": str(config.test_questions_dir)})
        except Exception as exc:
            logger.warning("W&B initialization failed: %s. Continuing without W&B tracking.", exc)
            self.enabled = False
            self._run = None

    def log(self, payload: Dict[str, Any]) -> None:
        if not self.enabled or self._run is None:
            return
        try:
            import wandb

            wandb.log(payload)
        except Exception as exc:
            logger.warning("Failed to log metrics to W&B: %s", exc)

    def finish(self) -> None:
        if not self.enabled or self._run is None:
            return
        try:
            import wandb

            wandb.finish()
        except Exception as exc:
            logger.warning("Failed to finish W&B run: %s", exc)


class MLflowTracker:
    """MLflow tracking integration wrapper"""
    
    def __init__(self, config: EvaluationConfig):
        self.enabled = True
        self.tracker = None
        
        try:
            from chat_pipeline.tracking.mlflow_tracking import MLflowTracker as MLflowTrackerImpl
            
            self.tracker = MLflowTrackerImpl(
                experiment_name="FrontShiftAI-RAG-Evaluation"
            )
            
            if not self.tracker.enabled:
                self.enabled = False
                return
            
            run_name = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            tags = {
                "test_questions_dir": str(config.test_questions_dir),
                "environment": os.getenv("GITHUB_REF_NAME", "local"),
            }
            
            git_commit = os.getenv("GITHUB_SHA", "")
            if git_commit:
                tags["git_commit"] = git_commit[:7]
            
            self.tracker.start_run(run_name=run_name, tags=tags)
            
            # Store reference for backend tracking (will be updated after first evaluation)
            self.judge_backend_actual = None
            self.judge_model_actual = None
            
            # Initial params (will be updated after first evaluation)
            params = {
                "test_questions_dir": str(config.test_questions_dir),
                "max_examples": str(config.max_examples) if config.max_examples else "all",
                "output_dir": str(config.output_dir),
                "judge_model_requested": "gpt-4o-mini",
                "judge_model_actual": "to_be_determined",
                "judge_backend": "to_be_determined",
            }
            
            self.tracker.log_params(params)
            
            logger.info("MLflow tracking initialized")
            
        except ImportError:
            logger.warning("mlflow not installed; skipping MLflow tracking")
            self.enabled = False
        except Exception as e:
            logger.warning(f"MLflow initialization failed: {e}")
            self.enabled = False
    
    def log(self, payload: Dict[str, Any]) -> None:
        """Log metrics to MLflow"""
        if not self.enabled or self.tracker is None:
            return
        
        try:
            numeric_metrics = {
                k: v for k, v in payload.items()
                if isinstance(v, (int, float)) and k != "question"
            }
            
            if numeric_metrics:
                self.tracker.log_metrics(numeric_metrics)
        except Exception as e:
            logger.warning(f"Failed to log to MLflow: {e}")
    
    def log_artifacts(self, artifact_dir: str) -> None:
        """Log artifacts directory to MLflow"""
        if not self.enabled or self.tracker is None:
            return
        
        try:
            self.tracker.log_artifacts(artifact_dir)
        except Exception as e:
            logger.warning(f"Failed to log artifacts to MLflow: {e}")
    
    def update_judge_info(self, backend: str, model: str) -> None:
        """Update MLflow with actual judge backend used."""
        if not self.enabled or self.tracker is None:
            return
        
        if self.judge_backend_actual is None:
            # First time - log the actual backend
            self.judge_backend_actual = backend
            self.judge_model_actual = model
            
            try:
                # Update params with actual values
                self.tracker.log_params({
                    "judge_backend_actual": backend,
                    "judge_model_final": model
                })
                logger.info(f"Updated MLflow: judge using {backend} backend with {model}")
            except Exception as e:
                logger.warning(f"Failed to update judge info: {e}")
    
    def finish(self) -> None:
        """End MLflow run"""
        if not self.enabled or self.tracker is None:
            return
        
        try:
            self.tracker.end_run()
            logger.info("MLflow tracking finished")
        except Exception as e:
            logger.warning(f"Failed to finish MLflow run: {e}")


class EvaluationRunner:
    """Coordinates dataset loading, judge execution, and metric aggregation."""

    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.results: List[MetricResult] = []
        self._judge_client = JudgeClient()
        self._wandb = WandbTracker(config)
        self._mlflow = MLflowTracker(config)

    def run(self) -> None:
        examples = _load_test_examples(self.config.test_questions_dir, self.config.max_examples)
        for idx, example in enumerate(examples, start=1):
            start = time.perf_counter()
            try:
                metrics = self._evaluate_example(example)
                self.results.append(metrics)
                self._persist_intermediate(example, metrics, idx)
            except Exception as exc:
                logger.exception("Evaluation failed for query '%s': %s", example.query, exc)
            finally:
                duration = time.perf_counter() - start
                logger.debug("Processed example %s in %.2fs", idx, duration)

        self._export_summary()

        if self._mlflow.enabled:
            self._mlflow.log_artifacts(str(self.config.output_dir))

        self._wandb.finish()
        self._mlflow.finish()

    def _evaluate_example(self, example: EvaluationExample) -> MetricResult:
        answer, contexts, pipeline_result = build_rag_inputs(example.query, example.metadata.get("company_name"))
        scores = evaluate_with_llm(
            example.query,
            contexts,
            answer,
            model="gpt-4o-mini",
            judge_client=self._judge_client,
        )
        
        # Extract and log actual backend used
        backend_used = scores.pop("_backend_used", "unknown")
        model_used = scores.pop("_model_used", "unknown")
        
        # Update MLflow with actual backend (first time only)
        self._mlflow.update_judge_info(backend_used, model_used)
        
        perf = compute_performance_metrics(pipeline_result, answer, contexts)
        combined = {**scores, **perf}
        wandb_payload = {
            "question": example.query,
            "category": example.metadata.get("category"),
            **combined,
        }
        self._wandb.log(wandb_payload)
        self._mlflow.log(wandb_payload)
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
        return metric

    def _persist_intermediate(self, example: EvaluationExample, metrics: MetricResult, index: int) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "index": index,
            "question": example.query,
            "category": example.metadata.get("category"),
            "metrics": metrics.__dict__,
        }
        output_file = self.config.output_dir / f"example_{index:04d}.json"
        with output_file.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)

    def _export_summary(self) -> None:
        """Export evaluation summary with nested structure for quality gates."""
        if not self.results:
            logger.warning("No evaluation results to summarize.")
            return
        
        count = len(self.results)
        
        # Quality metrics from LLM judge (0-5 scale)
        quality_fields = [
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
        ]
        
        # Performance metrics
        performance_fields = [
            "latency_total",
            "cost_per_query",
            "memory_utilization",
            "throughput_qps",
        ]
        
        # Calculate average quality scores
        average_scores = {}
        for field in quality_fields:
            values = [
                getattr(result, field)
                for result in self.results
                if getattr(result, field) is not None
            ]
            if values:
                average_scores[field] = sum(values) / len(values)
        
        # Calculate average performance metrics
        performance = {}
        for field in performance_fields:
            values = [
                getattr(result, field)
                for result in self.results
                if getattr(result, field) is not None
            ]
            if values:
                performance[field] = sum(values) / len(values)
        
        # Add latency breakdown if available
        all_breakdowns = [
            r.latency_breakdown
            for r in self.results
            if r.latency_breakdown
        ]
        if all_breakdowns:
            avg_breakdown = {}
            for key in all_breakdowns[0].keys():
                values = [
                    bd.get(key, 0)
                    for bd in all_breakdowns
                    if key in bd
                ]
                if values:
                    avg_breakdown[key] = sum(values) / len(values)
            performance["latency_breakdown"] = avg_breakdown
        
        # Add token usage
        total_tokens = sum(
            r.token_usage.get("total", 0)
            for r in self.results
            if r.token_usage
        )
        performance["token_usage_total"] = total_tokens
        performance["token_usage_avg"] = (
            total_tokens / count if count > 0 else 0
        )
        
        # Structure for quality gates compatibility
        summary = {
            "average_scores": average_scores,
            "performance": performance,
            "metadata": {
                "total_examples": count,
                "timestamp": datetime.now().isoformat(),
                "test_questions_dir": str(self.config.test_questions_dir),
            },
        }
        
        summary_path = self.config.output_dir / "summary.json"
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
        
        logger.info("Wrote evaluation summary to %s", summary_path)
        logger.info(
            "Summary contains %d quality metrics and %d performance metrics",
            len(average_scores),
            len(performance),
        )



def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG evaluation harness.")
    parser.add_argument(
        "--test-dir",
        default=Path("ml_pipeline/evaluation/test_questions"),
        type=Path,
        help="Directory containing generated test question folders.",
    )
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for evaluation artifacts.")
    parser.add_argument("--max-examples", type=int, help="Limit number of questions to evaluate.")
    parser.add_argument("--wandb-project", help="Weights & Biases project name.")
    parser.add_argument("--wandb-entity", help="Weights & Biases entity/team.")
    parser.add_argument("--disable-wandb", action="store_true", help="Disable Weights & Biases logging.")
    return parser.parse_args()


def main() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=os.getenv("EVAL_RUNNER_LOG_LEVEL", "INFO").upper())
    args = _parse_args()
    config = EvaluationConfig(
        test_questions_dir=args.test_dir,
        output_dir=args.output_dir,
        max_examples=args.max_examples,
        wandb_project=args.wandb_project,
        wandb_entity=args.wandb_entity,
        disable_wandb=args.disable_wandb,
    )
    runner = EvaluationRunner(config)
    runner.run()


if __name__ == "__main__":
    main()
