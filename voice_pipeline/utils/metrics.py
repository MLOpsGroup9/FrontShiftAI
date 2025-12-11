import logging
from datetime import datetime
from typing import Any, Dict, Optional

from livekit.agents.metrics import (
    STTMetrics,
    EOUMetrics,
    LLMMetrics,
    TTSMetrics,
    VADMetrics,
)

# Import wandb logger (optional dependency)
try:
    from voice_pipeline.utils.wandb_logger import WandbLogger
    WANDB_LOGGER_AVAILABLE = True
except ImportError:
    WANDB_LOGGER_AVAILABLE = False
    WandbLogger = None  # type: ignore


logger = logging.getLogger("voice_pipeline.metrics")


def _serialize_value(value: Any) -> Any:
    """Normalize enums/datetimes so logs stay JSON-serializable."""
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _metrics_payload(base_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure timestamp fields are ISO strings for structured logs."""
    payload = {}
    for key, value in base_fields.items():
        payload[key] = _serialize_value(value)
    return payload


class STTMetricsReporter:
    def __init__(self, wandb_logger: Optional[Any] = None) -> None:
        super().__init__()
        self.wandb_logger = wandb_logger

    async def on_stt_metrics_collected(self, metrics: STTMetrics) -> None:
        payload = _metrics_payload(
            {
                "metric_type": str(metrics.type),
                "label": metrics.label,
                "request_id": metrics.request_id,
                "timestamp": datetime.fromtimestamp(metrics.timestamp),
                "duration_seconds": metrics.duration,
                "speech_id": getattr(metrics, "speech_id", None),
                "error": getattr(metrics, "error", None),
                "streamed": metrics.streamed,
                "audio_duration_seconds": metrics.audio_duration,
            }
        )
        logger.info("stt_metrics_collected", extra={"metrics": payload})

        # Log to wandb if available
        if self.wandb_logger:
            self.wandb_logger.log_stt_metrics(
                duration=metrics.duration,
                audio_duration=metrics.audio_duration,
                speech_id=getattr(metrics, "speech_id", None),
                error=getattr(metrics, "error", None),
            )

    async def on_eou_metrics_collected(self, metrics: EOUMetrics) -> None:
        payload = _metrics_payload(
            {
                "metric_type": str(metrics.type),
                "label": metrics.label,
                "timestamp": datetime.fromtimestamp(metrics.timestamp),
                "end_of_utterance_delay_seconds": metrics.end_of_utterance_delay,
                "transcription_delay_seconds": metrics.transcription_delay,
                "speech_id": metrics.speech_id,
                "error": metrics.error,
            }
        )
        logger.info("eou_metrics_collected", extra={"metrics": payload})

        

class LLMMetricsReporter:
    def __init__(self, wandb_logger: Optional[Any] = None):
        super().__init__()
        self.wandb_logger = wandb_logger

    async def on_metrics_collected(self, metrics: LLMMetrics) -> None:
        payload = _metrics_payload(
            {
                "metric_type": str(metrics.type),
                "label": metrics.label,
                "request_id": metrics.request_id,
                "timestamp": datetime.fromtimestamp(metrics.timestamp),
                "duration_seconds": metrics.duration,
                "ttft_seconds": metrics.ttft,
                "cancelled": metrics.cancelled,
                "completion_tokens": metrics.completion_tokens,
                "prompt_tokens": metrics.prompt_tokens,
                "total_tokens": metrics.total_tokens,
                "tokens_per_second": metrics.tokens_per_second,
            }
        )
        logger.info("llm_metrics_collected", extra={"metrics": payload})

        # Log to wandb if available
        if self.wandb_logger:
            self.wandb_logger.log_llm_metrics(
                duration=metrics.duration,
                ttft=metrics.ttft,
                completion_tokens=metrics.completion_tokens,
                prompt_tokens=metrics.prompt_tokens,
                tokens_per_second=metrics.tokens_per_second,
                error=None,
            )
        


class TTSMetricsReporter:
    def __init__(self, wandb_logger: Optional[Any] = None):
        super().__init__()
        self.wandb_logger = wandb_logger

    async def on_metrics_collected(self, metrics: TTSMetrics) -> None:
        payload = _metrics_payload(
            {
                "metric_type": str(metrics.type),
                "label": metrics.label,
                "request_id": metrics.request_id,
                "timestamp": datetime.fromtimestamp(metrics.timestamp),
                "ttfb_seconds": metrics.ttfb,
                "duration_seconds": metrics.duration,
                "audio_duration_seconds": metrics.audio_duration,
                "cancelled": metrics.cancelled,
                "characters_count": metrics.characters_count,
                "streamed": metrics.streamed,
                "speech_id": metrics.speech_id,
                "error": metrics.error,
            }
        )
        logger.info("tts_metrics_collected", extra={"metrics": payload})

        # Log to wandb if available
        if self.wandb_logger:
            self.wandb_logger.log_tts_metrics(
                duration=metrics.duration,
                ttfb=metrics.ttfb,
                audio_duration=metrics.audio_duration,
                characters_count=metrics.characters_count,
                error=metrics.error,
            )
        


class VADMetricsReporter:
    def __init__(self, wandb_logger: Optional[Any] = None):
        super().__init__()
        self.wandb_logger = wandb_logger

    async def on_vad_event(self, event: VADMetrics) -> None:
        payload = _metrics_payload(
            {
                "metric_type": str(event.type),
                "timestamp": datetime.fromtimestamp(event.timestamp),
                "idle_time_seconds": event.idle_time,
                "inference_duration_total_seconds": event.inference_duration_total,
                "inference_count": event.inference_count,
                "speech_id": getattr(event, "speech_id", None),
                "error": getattr(event, "error", None),
            }
        )
        logger.info("vad_event", extra={"metrics": payload})

        # Log to wandb if available
        if self.wandb_logger:
            self.wandb_logger.log_vad_metrics(
                idle_time=event.idle_time,
                inference_duration=event.inference_duration_total,
                inference_count=event.inference_count,
            )


class RAGMetricsReporter:
    """Reporter for RAG query metrics and latency tracking."""

    def __init__(self, wandb_logger: Optional[Any] = None):
        super().__init__()
        self.wandb_logger = wandb_logger

    async def on_rag_query_start(
        self,
        session_id: str,
        query: str,
        top_k: int
    ) -> None:
        """Log when a RAG query starts."""
        payload = {
            "metric_type": "rag_query_start",
            "timestamp": datetime.now(),
            "session_id": session_id,
            "query": query,
            "top_k": top_k,
        }
        logger.info("rag_query_start", extra={"metrics": _metrics_payload(payload)})

    async def on_rag_query_complete(
        self,
        session_id: str,
        query: str,
        total_duration: float,
        backend_duration: float,
        retrieval_duration: float,
        generation_duration: float,
        sources_count: int,
        cache_hit: bool = False,
        error: Any = None
    ) -> None:
        """Log when a RAG query completes with detailed timing breakdown."""
        payload = {
            "metric_type": "rag_query_complete" if not error else "rag_query_error",
            "timestamp": datetime.now(),
            "session_id": session_id,
            "query": query,
            "total_duration_seconds": total_duration,
            "backend_duration_seconds": backend_duration,
            "retrieval_duration_seconds": retrieval_duration,
            "generation_duration_seconds": generation_duration,
            "network_overhead_seconds": total_duration - backend_duration,
            "sources_count": sources_count,
            "cache_hit": cache_hit,
            "error": str(error) if error else None,
        }

        log_method = logger.error if error else logger.info
        log_method(
            "rag_query_complete" if not error else "rag_query_error",
            extra={"metrics": _metrics_payload(payload)}
        )

        # Log to wandb if available
        if self.wandb_logger:
            self.wandb_logger.log_rag_metrics(
                query=query,
                total_duration=total_duration,
                backend_duration=backend_duration,
                retrieval_duration=retrieval_duration,
                generation_duration=generation_duration,
                sources_count=sources_count,
                cache_hit=cache_hit,
                error=str(error) if error else None,
            )
