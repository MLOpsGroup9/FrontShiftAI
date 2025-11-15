"""LLM-as-a-judge script for the RAG pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Sequence

from chat_pipeline.rag.pipeline import PipelineConfig, PipelineResult, RAGPipeline
from chat_pipeline.evaluation.judge_client import JudgeClient

logger = logging.getLogger(__name__)

LLM_METRIC_GROUPS: Dict[str, Sequence[str]] = {
    "Retrieval Metrics": (
        "precision",
        "recall",
        "retrieval_diversity",
        "reranker_gain",
    ),
    "Context Quality": (
        "context_precision",
        "context_recall",
        "groundedness",
    ),
    "Answer Quality": (
        "relevance",
        "factual_correctness",
        "hallucination",
        "coherence",
        "conciseness",
        "structure_adherence",
    ),
}
LLM_SCORE_FIELDS: Sequence[str] = tuple(
    metric for group in LLM_METRIC_GROUPS.values() for metric in group
)
PERFORMANCE_FIELDS: Sequence[str] = (
    "latency",
    "token_usage",
    "cost_per_query",
    "memory_utilization",
    "throughput",
)
DEFAULT_COST_PER_1K_TOKENS = float(os.getenv("RAG_COST_PER_1K_TOKENS", "0.002"))


def _extract_contexts_from_metadata(metadata: Sequence[Dict[str, str]]) -> List[str]:
    contexts: List[str] = []
    for meta in metadata:
        value = next(
            (
                meta.get(key)
                for key in ("document", "text", "chunk", "content", "page_content")
                if meta.get(key)
            ),
            None,
        )
        if isinstance(value, str) and value.strip():
            contexts.append(value.strip())
    return contexts


def _collect_contexts(
    pipeline: RAGPipeline,
    query: str,
    company_name: str | None,
    config: PipelineConfig,
) -> List[str]:
    """Re-run the retrieval stage to capture the raw document strings."""

    try:
        docs, _ = pipeline._execute_retrieval(query, company_name, config)  # type: ignore[attr-defined]
        filtered_docs = [doc.strip() for doc in docs if isinstance(doc, str) and doc.strip()]
        logger.debug("Collected %d contexts via retrieval rerun.", len(filtered_docs))
        return filtered_docs
    except Exception as exc:
        logger.warning("Unable to re-run retrieval for context capture: %s", exc)
        return []


def _normalize_answer(answer: object) -> str:
    if isinstance(answer, str):
        return answer
    if hasattr(answer, "__iter__"):
        return "".join(str(chunk) for chunk in answer)  # type: ignore[arg-type]
    return str(answer)


def build_rag_inputs(query: str, company_name: str | None) -> tuple[str, List[str], PipelineResult]:
    logger.info("Running RAG pipeline for evaluation question.")
    pipeline = RAGPipeline()
    result: PipelineResult = pipeline.run(query=query, company_name=company_name, stream=False)
    answer = _normalize_answer(result.answer)
    contexts = _collect_contexts(pipeline, query, company_name, result.config)
    if not contexts:
        contexts = _extract_contexts_from_metadata(result.metadata)
        logger.debug("Using %d contexts extracted from metadata.", len(contexts))
    else:
        logger.debug("Using %d contexts from rerun retrieval.", len(contexts))
    return answer, contexts, result


def _build_judge_prompt(question: str, contexts: Sequence[str], answer: str) -> str:
    logger.debug("Constructing judge prompt (contexts=%d chars, answer=%d chars).", sum(len(c) for c in contexts), len(answer))
    context_block = "\n\n".join(contexts) if contexts else "No supporting context retrieved."
    metric_lines: List[str] = []
    for group, metrics in LLM_METRIC_GROUPS.items():
        metric_lines.append(f"{group}:")
        metric_lines.extend(f"- {metric}" for metric in metrics)
    metrics_text = "\n".join(metric_lines)
    return (
        "You are an impartial judge for a Retrieval-Augmented Generation system.\n"
        "Score each listed metric on a 0-5 scale where 0 is worst and 5 is best.\n"
        "Return ONLY a JSON object with numeric scores.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved Context:\n{context_block}\n\n"
        f"Assistant Answer:\n{answer}\n\n"
        "Metrics to score:\n"
        f"{metrics_text}\n"
        "Respond with JSON in the following shape:\n"
        '{"precision":0,"recall":0,"retrieval_diversity":0,"reranker_gain":0,'
        '"context_precision":0,"context_recall":0,"groundedness":0,"relevance":0,'
        '"factual_correctness":0,"hallucination":0,"coherence":0,"conciseness":0,'
        '"structure_adherence":0}'
    )


def _validate_scores(payload: Dict[str, object]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for field in LLM_SCORE_FIELDS:
        if field not in payload:
            raise ValueError(f"Missing score for '{field}'.")
        value = payload[field]
        if not isinstance(value, (int, float)):
            raise ValueError(f"Score for '{field}' must be numeric, received {type(value).__name__}.")
        scores[field] = float(value)
    return scores


def evaluate_with_llm(
    question: str,
    contexts: Sequence[str],
    answer: str,
    *,
    model: str = "gpt-4o-mini",
    retry_attempts: int = 1,
    judge_client: JudgeClient,
) -> Dict[str, float]:
    """Send the judge prompt to the OpenAI ChatCompletion API and parse the JSON response."""

    prompt = _build_judge_prompt(question, contexts, answer)
    attempts = 0
    last_exception: Exception | None = None

    while attempts <= retry_attempts:
        try:
            logger.info("Submitting judge request (attempt %d).", attempts + 1)
            raw_scores = judge_client.score(prompt, model_name=model)
            logger.debug("Judge raw response: %s", raw_scores)
            return _validate_scores(raw_scores)
        except Exception as exc:
            logger.warning("Judge attempt %d failed: %s", attempts + 1, exc)
            last_exception = exc
            attempts += 1

    raise RuntimeError("Judge model failed to return valid JSON.") from last_exception


def _calculate_latency(timings: Dict[str, float]) -> float:
    if "total" in timings:
        return max(float(timings["total"]), 0.0)
    total = sum(float(value) for value in timings.values())
    return max(total, 0.0)


def _estimate_token_usage(answer: str, contexts: Sequence[str]) -> int:
    combined_text = answer + " ".join(contexts)
    return max(1, int(len(combined_text) / 4))  # Approximate 4 characters per token.


def _estimate_memory_utilization(contexts: Sequence[str]) -> float:
    total_chars = sum(len(ctx) for ctx in contexts)
    return total_chars / 1024.0  # Rough kilobyte usage of cached contexts.


def compute_performance_metrics(result: PipelineResult, answer: str, contexts: Sequence[str]) -> Dict[str, float]:
    timings = result.timings or {}
    latency = _calculate_latency(timings) if timings else 0.0
    token_usage = _estimate_token_usage(answer, contexts)
    cost_per_query = (token_usage / 1000.0) * DEFAULT_COST_PER_1K_TOKENS
    memory_utilization = _estimate_memory_utilization(contexts)
    throughput = (1.0 / latency) if latency > 0 else 0.0
    metrics = {
        "latency": latency,
        "token_usage": float(token_usage),
        "cost_per_query": cost_per_query,
        "memory_utilization": memory_utilization,
        "throughput": throughput,
    }
    logger.debug("Performance metrics: %s", metrics)
    return metrics


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a RAG answer with an LLM judge.")
    parser.add_argument("question", help="User question to feed into the RAG pipeline.")
    parser.add_argument(
        "--company-name",
        help="Optional company filter propagated to the RAG retrievers.",
        default=None,
    )
    parser.add_argument(
        "--model",
        help="OpenAI ChatCompletion model to use (default: gpt-4o-mini).",
        default="gpt-4o-mini",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=os.getenv("EVAL_JUDGE_LOG_LEVEL", "INFO").upper(),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    logger.info("Initializing JudgeClient.")
    judge_client = JudgeClient()
    logger.info("Running evaluation for question: %s", args.question)

    try:
        answer, contexts, pipeline_result = build_rag_inputs(args.question, args.company_name)
    except Exception as exc:
        logger.exception("Failed to run RAG pipeline: %s", exc)
        sys.exit(2)

    try:
        scores = evaluate_with_llm(
            args.question,
            contexts,
            answer,
            model=args.model,
            judge_client=judge_client,
        )
    except Exception as exc:
        print(f"[eval_judge] LLM judge failed: {exc}", file=sys.stderr)
        sys.exit(3)

    performance_metrics = compute_performance_metrics(pipeline_result, answer, contexts)
    combined = {**scores, **performance_metrics}
    missing_fields = [
        field
        for field in (*LLM_SCORE_FIELDS, *PERFORMANCE_FIELDS)
        if field not in combined
    ]
    if missing_fields:
        logger.error("Missing metrics in final output: %s", ", ".join(missing_fields))
        raise RuntimeError(f"Missing metrics in final output: {', '.join(missing_fields)}")
    logger.info("Evaluation completed successfully.")
    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()
