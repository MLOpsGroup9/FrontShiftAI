"""Utility wrapper for selecting an LLM judge backend."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

import torch
import requests
from openai import OpenAI
from transformers import pipeline

from chat_pipeline.utils.runtime_env import (
    allow_heavy_fallbacks,
    remote_max_attempts,
    remote_retry_backoff,
    remote_retry_initial_delay,
    remote_timeout_seconds,
    remote_request_delay_seconds,
)

logger = logging.getLogger(__name__)
REMOTE_TIMEOUT = remote_timeout_seconds()
REMOTE_MAX_ATTEMPTS = remote_max_attempts()
REMOTE_BACKOFF = remote_retry_backoff()
REMOTE_BACKOFF_START = remote_retry_initial_delay()
REMOTE_MIN_DELAY = remote_request_delay_seconds()

class JudgeClient:
    """Abstraction that prefers OpenAI GPT-4o-mini with HF fallbacks."""

    def __init__(self) -> None:
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.backend: str = "hf"
        self.client: OpenAI | None = None
        self.pipelines: Dict[str, Any] = {}

        # Allow explicit override via JUDGE_BACKEND
        # If set to 'mercury' or 'inception', we skip OpenAI even if key is present.
        judge_backend_override = os.getenv("JUDGE_BACKEND", "").lower()

        if judge_backend_override in ("mercury", "inception"):
            logger.info("JudgeClient forced to use Mercury/Inception backend.")
            self.backend = "mercury"
        elif self.openai_key:
            logger.info("JudgeClient using OpenAI GPT-4o-mini backend.")
            self.client = OpenAI(api_key=self.openai_key)
            self.backend = "openai"
        else:
            logger.warning("OPENAI_API_KEY not set and no override; falling back to open-source judge models.")

    def score(self, judge_prompt: str, model_name: str | None = None) -> Dict[str, Any]:
        """Return parsed JSON scores from the judge backend."""

        if self.backend == "openai":
            assert self.client is not None
            logger.debug("Calling OpenAI judge with model %s", model_name or "gpt-4o-mini")
            response = self.client.chat.completions.create(
                model=model_name or "gpt-4o-mini",
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0,
                timeout=REMOTE_TIMEOUT,
            )
            text = response.choices[0].message.content.strip()
        elif self.backend == "mercury":
            # Explicit mercury backend logic
            mercury_key = os.getenv("INCEPTION_API_KEY")
            if mercury_key:
                try:
                    text = self._call_mercury(judge_prompt, mercury_key)
                except Exception as exc:
                    logger.warning("Mercury judge failed: %s; attempting heavy fallback.", exc)
                    text = self._run_hf_fallback(judge_prompt)
            else:
                logger.warning("JUDGE_BACKEND=mercury but INCEPTION_API_KEY not set.")
                text = self._run_hf_fallback(judge_prompt)
        else:
            # Fallback / Auto logic (legacy behavior if not openai and not mercury)
            mercury_key = os.getenv("INCEPTION_API_KEY")
            if mercury_key:
                try:
                    text = self._call_mercury(judge_prompt, mercury_key)
                except Exception as exc:
                    logger.warning("Mercury judge failed: %s; attempting heavy fallback.", exc)
                    text = self._run_hf_fallback(judge_prompt)
            else:
                text = self._run_hf_fallback(judge_prompt)

        try:
            return json.loads(self._extract_json(text))
        except Exception as exc:
            logger.error("Judge backend returned invalid JSON: %s", text)
            raise ValueError(f"Judge returned invalid JSON: {text}") from exc

    @staticmethod
    def _extract_json(text: str) -> str:
        if "{" in text and "}" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            return text[start:end]
        return text

    def _load_pipeline(self, key: str, model_name: str) -> Any:
        if key in self.pipelines:
            return self.pipelines[key]

        device = 0 if torch.cuda.is_available() else -1
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        logger.info("Loading judge pipeline: %s (device=%s)", model_name, "cuda" if device == 0 else "cpu")
        pipe = pipeline(
            "text-generation",
            model=model_name,
            tokenizer=model_name,
            device=device,
            torch_dtype=dtype,
        )
        self.pipelines[key] = pipe
        return pipe

    def _run_pipeline(self, key: str, model_name: str, prompt: str) -> str:
        pipe = self._load_pipeline(key, model_name)
        logger.debug("Running judge pipeline '%s' for prompt length %s", key, len(prompt))
        outputs = pipe(prompt, max_new_tokens=512, do_sample=False)
        if not outputs:
            raise RuntimeError(f"{model_name} returned no output.")
        text = outputs[0].get("generated_text", "").strip()
        if not text:
            raise RuntimeError(f"{model_name} returned empty output.")
        return text

    def _run_hf_fallback(self, prompt: str) -> str:
        if not allow_heavy_fallbacks():
            raise RuntimeError("Heavy HF judge fallback disabled. Enable CHAT_PIPELINE_ALLOW_HEAVY_FALLBACKS to use it.")
        model = os.getenv("JUDGE_MODEL", "Qwen/Qwen2.5-3B-Instruct")
        return self._run_pipeline("hf-judge", model, prompt)

    def _call_mercury(self, prompt: str, api_key: str) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": os.getenv("MERCURY_MODEL", "mercury"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0,
            "top_p": 0.9,
        }
        attempts = REMOTE_MAX_ATTEMPTS
        delay = REMOTE_BACKOFF_START
        last_exc: Exception | None = None
        base_url = os.getenv("INCEPTION_API_BASE", "https://api.inceptionlabs.ai/v1")
        for attempt in range(1, attempts + 1):
            try:
                if REMOTE_MIN_DELAY > 0 and attempt > 1:
                    time.sleep(REMOTE_MIN_DELAY)
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=REMOTE_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and data["choices"]:
                    message = data["choices"][0].get("message", {})
                    return (message.get("content") or "").strip()
                if "content" in data:
                    return (data.get("content") or "").strip()
                raise RuntimeError(f"Unexpected Mercury response: {data}")
            except Exception as exc:
                last_exc = exc
                logger.warning("Mercury judge attempt %s/%s failed: %s", attempt, attempts, exc)
                if attempt == attempts:
                    break
                time.sleep(delay)
                delay *= REMOTE_BACKOFF
        raise RuntimeError("Mercury judge backend failed after multiple attempts.") from last_exc


__all__ = ["JudgeClient"]
