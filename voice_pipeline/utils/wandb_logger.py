"""
Weights & Biases (wandb) integration for voice pipeline metrics tracking.
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import wandb, but make it optional
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    wandb = None  # type: ignore
    logger.warning("wandb not installed. Install with: pip install wandb")


class WandbLogger:
    """
    Centralized wandb logger for voice pipeline metrics.
    Handles session-level run initialization and metric logging.
    """

    def __init__(self, session_id: str, enabled: Optional[bool] = False):
        """
        Initialize wandb logger for a voice session.

        Args:
            session_id: Unique session identifier
            enabled: Override to enable/disable wandb. If None, checks WANDB_MODE env var
        """
        self.session_id = session_id
        self.run = None
        self._step_counter = 0

        # Check if wandb is enabled
        if enabled is None:
            wandb_mode = os.getenv("WANDB_MODE", "disabled").lower()
            enabled = wandb_mode != "disabled" and WANDB_AVAILABLE

        self.enabled = enabled and WANDB_AVAILABLE

        if not WANDB_AVAILABLE and enabled:
            logger.warning(
                "wandb logging requested but wandb is not installed. "
                "Install with: pip install wandb"
            )
            self.enabled = False

        if self.enabled:
            self._initialize_run()

    def _initialize_run(self) -> None:
        """Initialize a wandb run for this voice session."""
        if not self.enabled or not WANDB_AVAILABLE:
            return

        try:
            # Get wandb config from environment
            project = os.getenv("WANDB_PROJECT", "FrontShiftAI_Voice")
            entity = os.getenv("WANDB_ENTITY")
            api_key = os.getenv("WANDB_API_KEY")

            # Configure wandb
            if api_key:
                wandb.login(key=api_key, relogin=True)

            # Create session-specific run name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = f"voice_session_{self.session_id[:8]}_{timestamp}"

            # Initialize run with session metadata
            self.run = wandb.init(
                project=project,
                entity=entity,
                name=run_name,
                tags=["voice_pipeline", "livekit"],
                config={
                    "session_id": self.session_id,
                    "session_type": "voice_agent",
                    "start_time": datetime.now().isoformat(),
                },
                reinit=True,
            )

            logger.info(
                f"✅ wandb run initialized: {run_name}",
                extra={
                    "session_id": self.session_id,
                    "wandb_run_id": self.run.id if self.run else None,
                    "wandb_url": self.run.url if self.run else None,
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to initialize wandb run: {e}",
                extra={"session_id": self.session_id},
                exc_info=True
            )
            self.enabled = False

    def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None) -> None:
        """
        Log metrics to wandb.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step counter (auto-increments if not provided)
        """
        if not self.enabled or not self.run:
            return

        try:
            if step is None:
                step = self._step_counter
                self._step_counter += 1

            # Add timestamp to metrics
            metrics_with_ts = {
                **metrics,
                "timestamp": datetime.now().isoformat(),
            }

            wandb.log(metrics_with_ts, step=step)

            logger.debug(
                "Logged metrics to wandb",
                extra={
                    "session_id": self.session_id,
                    "step": step,
                    "metric_count": len(metrics)
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to log metrics to wandb: {e}",
                extra={"session_id": self.session_id, "metrics": metrics},
                exc_info=True
            )

    def log_rag_metrics(
        self,
        query: str,
        total_duration: float,
        backend_duration: float,
        retrieval_duration: float,
        generation_duration: float,
        sources_count: int,
        cache_hit: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Log RAG-specific metrics."""
        metrics = {
            "rag/total_duration": total_duration,
            "rag/backend_duration": backend_duration,
            "rag/retrieval_duration": retrieval_duration,
            "rag/generation_duration": generation_duration,
            "rag/network_overhead": total_duration - backend_duration,
            "rag/sources_count": sources_count,
            "rag/cache_hit": 1 if cache_hit else 0,
            "rag/error": 1 if error else 0,
            "rag/query_length": len(query),
        }

        if error:
            metrics["rag/error_type"] = str(error)

        self.log_metrics(metrics)

    def log_stt_metrics(
        self,
        duration: float,
        audio_duration: float,
        speech_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log STT-specific metrics."""
        metrics = {
            "stt/duration": duration,
            "stt/audio_duration": audio_duration,
            "stt/error": 1 if error else 0,
        }

        if audio_duration > 0:
            metrics["stt/realtime_factor"] = duration / audio_duration

        self.log_metrics(metrics)

    def log_llm_metrics(
        self,
        duration: float,
        ttft: Optional[float] = None,
        completion_tokens: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        tokens_per_second: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log LLM-specific metrics."""
        metrics = {
            "llm/duration": duration,
            "llm/error": 1 if error else 0,
        }

        if ttft is not None:
            metrics["llm/ttft"] = ttft
        if completion_tokens is not None:
            metrics["llm/completion_tokens"] = completion_tokens
        if prompt_tokens is not None:
            metrics["llm/prompt_tokens"] = prompt_tokens
        if tokens_per_second is not None:
            metrics["llm/tokens_per_second"] = tokens_per_second

        if completion_tokens and prompt_tokens:
            metrics["llm/total_tokens"] = completion_tokens + prompt_tokens

        self.log_metrics(metrics)

    def log_tts_metrics(
        self,
        duration: float,
        ttfb: Optional[float] = None,
        audio_duration: Optional[float] = None,
        characters_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log TTS-specific metrics."""
        metrics = {
            "tts/duration": duration,
            "tts/error": 1 if error else 0,
        }

        if ttfb is not None:
            metrics["tts/ttfb"] = ttfb
        if audio_duration is not None:
            metrics["tts/audio_duration"] = audio_duration
        if characters_count is not None:
            metrics["tts/characters_count"] = characters_count

        if audio_duration and duration > 0:
            metrics["tts/realtime_factor"] = audio_duration / duration

        self.log_metrics(metrics)

    def log_vad_metrics(
        self,
        idle_time: Optional[float] = None,
        inference_duration: Optional[float] = None,
        inference_count: Optional[int] = None,
    ) -> None:
        """Log VAD-specific metrics."""
        metrics = {}

        if idle_time is not None:
            metrics["vad/idle_time"] = idle_time
        if inference_duration is not None:
            metrics["vad/inference_duration"] = inference_duration
        if inference_count is not None:
            metrics["vad/inference_count"] = inference_count

        if metrics:
            self.log_metrics(metrics)

    def log_session_summary(
        self,
        total_queries: int = 0,
        total_errors: int = 0,
        session_duration: Optional[float] = None,
    ) -> None:
        """Log session summary metrics."""
        metrics = {
            "session/total_queries": total_queries,
            "session/total_errors": total_errors,
            "session/error_rate": total_errors / total_queries if total_queries > 0 else 0,
        }

        if session_duration is not None:
            metrics["session/duration"] = session_duration

        self.log_metrics(metrics)

    def finish(self) -> None:
        """Finish the wandb run."""
        if not self.enabled or not self.run:
            return

        try:
            wandb.finish()
            logger.info(
                "✅ wandb run finished",
                extra={
                    "session_id": self.session_id,
                    "total_steps": self._step_counter,
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to finish wandb run: {e}",
                extra={"session_id": self.session_id},
                exc_info=True
            )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.finish()
