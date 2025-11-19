"""Utility wrapper for selecting an LLM judge backend."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import torch
import requests
from openai import OpenAI
from transformers import pipeline

logger = logging.getLogger(__name__)

class JudgeClient:
    """Abstraction that prefers OpenAI GPT-4o-mini with HF fallbacks."""

    def __init__(self) -> None:
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.backend: str = "hf"
        self.client: OpenAI | None = None
        self.pipelines: Dict[str, Any] = {}

        if self.openai_key:
            logger.info("JudgeClient using OpenAI GPT-4o-mini backend.")
            self.client = OpenAI(api_key=self.openai_key)
            self.backend = "openai"
        else:
            logger.warning("OPENAI_API_KEY not set; falling back to open-source judge models.")

    def score(self, judge_prompt: str, model_name: str | None = None) -> Dict[str, Any]:
        """Return parsed JSON scores from the judge backend."""

        if self.backend == "openai":
            assert self.client is not None
            logger.debug("Calling OpenAI judge with model %s", model_name or "gpt-4o-mini")
            response = self.client.chat.completions.create(
                model=model_name or "gpt-4o-mini",
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0,
            )
            text = response.choices[0].message.content.strip()
        else:
            mercury_key = os.getenv("INCEPTION_API_KEY")
            if mercury_key:
                try:
                    text = self._call_mercury(judge_prompt, mercury_key)
                except Exception as exc:
                    logger.warning("Mercury judge failed: %s; falling back to HF.", exc)
                    model = os.getenv("JUDGE_MODEL", "Qwen/Qwen2.5-3B-Instruct")
                    text = self._run_pipeline("hf-judge", model, judge_prompt)
            else:
                model = os.getenv("JUDGE_MODEL", "Qwen/Qwen2.5-3B-Instruct")
                text = self._run_pipeline("hf-judge", model, judge_prompt)

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
        resp = requests.post(
            os.getenv("INCEPTION_API_BASE", "https://api.inceptionlabs.ai/v1") + "/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if "choices" in data and data["choices"]:
            message = data["choices"][0].get("message", {})
            return (message.get("content") or "").strip()
        if "content" in data:
            return (data.get("content") or "").strip()
        raise RuntimeError(f"Unexpected Mercury response: {data}")


__all__ = ["JudgeClient"]
