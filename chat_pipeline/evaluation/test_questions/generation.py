import asyncio
import json
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import aiohttp
import torch
import yaml
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / "evaluation" / ".env"
load_dotenv(ENV_PATH)
load_dotenv()  # fallback to default .env discovery

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"generation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"

from chat_pipeline.utils.logger import setup_logging
setup_logging(level=os.getenv("GENERATION_LOG_LEVEL"), to_file=True, log_dir=LOG_DIR)
logger = logging.getLogger(__name__)


CONFIG_PATH = PROJECT_ROOT / "configs" / "test_set.yaml"
CATEGORY_DIR_MAP = {
    "general": Path(__file__).resolve().parent / "general",
    "domain": Path(__file__).resolve().parent / "domain",
    "domain_specific": Path(__file__).resolve().parent / "domain",
    "industry": Path(__file__).resolve().parent / "domain",
    "slices": Path(__file__).resolve().parent / "slices",
}
BATCH_SIZE_DEFAULT = 12
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0
HF_MAX_NEW_TOKENS = 512


def normalize_question(question: Any) -> str:
    if isinstance(question, str):
        normalized = question.strip()
        return normalized if normalized else ""
    return ""


def sanitize_question(text: str) -> str:
    if not isinstance(text, str):
        return ""
    sanitized = re.sub(r"^[\s\-*\d\.\)\(]+", "", text.strip())
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized.strip()


def fallback_record(original_question: str, _raw_output: str) -> Dict[str, Any]:
    return {
        "seed": original_question,
        "new_question": None,
    }


def parse_model_output(original_question: str, model_output: str) -> Dict[str, Any]:
    cleaned = model_output.strip()
    if not cleaned:
        return fallback_record(original_question, model_output)

    candidate_text = cleaned
    if not cleaned.startswith("{") or not cleaned.endswith("}"):
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            candidate_text = json_match.group(0)

    try:
        parsed = json.loads(candidate_text)
    except (json.JSONDecodeError, TypeError):
        parsed = None

    if isinstance(parsed, dict):
        question = parsed.get("new_question") or parsed.get("question")
        normalized = sanitize_question(question)
        normalized = normalize_question(normalized)
        if normalized:
            return {"seed": original_question, "new_question": normalized}

    stripped = re.split(r"[\n\r]+", cleaned.strip())
    for line in stripped:
        candidate = sanitize_question(line)
        normalized = normalize_question(candidate)
        if normalized:
            return {"seed": original_question, "new_question": normalized}

    return fallback_record(original_question, model_output)


@dataclass
class GenerationSettings:
    prompt_template: str
    temperature: float
    openai_model: str
    num_samples: int
    batch_size: int
    max_new_tokens: int


@dataclass
class CategoryConfig:
    canonical_name: str
    seeds: List[str]
    num_samples: int
    prompt: str
    output_path: Path


def _ensure_placeholder(prompt: str) -> str:
    if "{question}" not in prompt:
        raise ValueError("Prompt template must include a {question} placeholder.")
    return prompt


def _load_yaml_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Seed configuration not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("test_set.yaml must contain a mapping at the top level.")
    return payload


def _extract_model_settings(config: Dict[str, Any]) -> GenerationSettings:
    model_cfg = config.get("model") or {}
    prompt = (
        model_cfg.get("prompt_template")
        or model_cfg.get("prompt")
        or config.get("prompt_template")
        or config.get("prompt")
    )
    if not prompt:
        raise ValueError("A prompt template is required in test_set.yaml (prompt_template).")
    prompt = _ensure_placeholder(prompt)
    temperature = float(model_cfg.get("temperature", config.get("temperature", 0.0)))
    openai_model = model_cfg.get("openai_model") or config.get("openai_model") or "gpt-4o-mini"
    num_samples = int(model_cfg.get("num_samples", config.get("num_samples", 50)))
    if num_samples <= 0:
        raise ValueError("num_samples must be greater than zero.")
    batch_size = int(model_cfg.get("batch_size", config.get("batch_size", BATCH_SIZE_DEFAULT)))
    batch_size = max(1, batch_size)
    max_new_tokens = int(model_cfg.get("max_new_tokens", config.get("max_new_tokens", HF_MAX_NEW_TOKENS)))
    max_new_tokens = max(32, max_new_tokens)
    return GenerationSettings(
        prompt_template=prompt,
        temperature=temperature,
        openai_model=openai_model,
        num_samples=num_samples,
        batch_size=batch_size,
        max_new_tokens=max_new_tokens,
    )


def _iter_category_sections(config: Dict[str, Any]) -> Iterable[Tuple[str, Any]]:
    if "categories" in config and isinstance(config["categories"], dict):
        yield from config["categories"].items()
        return

    for key, value in config.items():
        if key in {"general", "domain", "domain_specific", "industry", "slices"}:
            yield key, value


def _extract_seed_list(data: Any) -> List[str]:
    def _parse_collection(collection: Sequence[Any]) -> List[str]:
        seeds: List[str] = []
        for item in collection:
            candidate = item
            if isinstance(item, dict):
                candidate = item.get("question") or item.get("q") or item.get("seed")
            normalized = normalize_question(candidate)
            if normalized:
                seeds.append(normalized)
        return seeds

    if isinstance(data, list):
        seeds = _parse_collection(data)
        if seeds:
            return seeds
        raise ValueError("Seed question entries must contain non-empty strings.")

    if isinstance(data, dict):
        candidates = data.get("seed_questions") or data.get("questions") or data.get("seeds") or []
        if isinstance(candidates, list):
            seeds = _parse_collection(candidates)
        else:
            seeds = _parse_collection([candidates])
        if seeds:
            return seeds

    raise ValueError("Each category must define seed questions (list).")


def _resolve_prompt(data: Any, default_prompt: str) -> str:
    if isinstance(data, dict):
        prompt = data.get("prompt_template") or data.get("prompt")
        if prompt:
            return _ensure_placeholder(prompt)
    return default_prompt


def _resolve_num_samples(data: Any, default: int) -> int:
    if isinstance(data, dict) and "num_samples" in data:
        try:
            value = int(data["num_samples"])
        except (TypeError, ValueError):
            raise ValueError("num_samples must be an integer.")
        if value <= 0:
            raise ValueError("num_samples must be positive.")
        return value
    return default


def _resolve_output_path(category_name: str) -> Path:
    base = CATEGORY_DIR_MAP.get(category_name, Path(__file__).resolve().parent / category_name)
    base.mkdir(parents=True, exist_ok=True)
    return base / "dataset.json"


def load_generation_plan() -> Tuple[GenerationSettings, List[CategoryConfig]]:
    config = _load_yaml_config()
    settings = _extract_model_settings(config)

    categories: List[CategoryConfig] = []
    for raw_name, data in _iter_category_sections(config):
        canonical = {
            "domain_specific": "domain",
            "industry": "domain",
        }.get(raw_name, raw_name)
        seeds = _extract_seed_list(data)
        prompt = _resolve_prompt(data, settings.prompt_template)
        num_samples = _resolve_num_samples(data, settings.num_samples)
        output_path = _resolve_output_path(canonical)
        categories.append(
            CategoryConfig(
                canonical_name=canonical,
                seeds=seeds,
                num_samples=num_samples,
                prompt=prompt,
                output_path=output_path,
            )
        )

    if not categories:
        raise ValueError("No categories found in test_set.yaml. Expected keys like general/domain/slices.")
    return settings, categories


class LLMEngine:
    """Manages multi-backend generation with graceful fallbacks."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        openai_model: str,
        temperature: float,
        max_new_tokens: int,
    ):
        self.session = session
        self.openai_model = openai_model
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
        self.inception_api_key = os.getenv("INCEPTION_LABS_API_KEY") or os.getenv("INCEPTION_API_KEY")
        self.inception_api_base = os.getenv("INCEPTION_API_BASE", "https://api.inceptionlabs.ai/v1").rstrip("/")
        self.mercury_model = os.getenv("MERCURY_MODEL", "mercury-1")

        self._hf_pipelines: Dict[str, Any] = {}

    async def generate(self, prompt: str) -> str:
        errors: List[str] = []

        if self.openai_api_key:
            try:
                return await self._call_openai(prompt)
            except Exception as exc:
                msg = f"OpenAI failure: {exc}"
                logger.warning(msg)
                errors.append(msg)

        if self.inception_api_key:
            try:
                return await self._call_inception(prompt)
            except Exception as exc:
                msg = f"Inception Mercury failure: {exc}"
                logger.warning(msg)
                errors.append(msg)

        try:
            return await self._call_hf_pipeline("llama", "meta-llama/Meta-Llama-3.1-8B-Instruct", prompt)
        except Exception as exc:
            msg = f"Llama 3.1 fallback failure: {exc}"
            logger.warning(msg)
            errors.append(msg)

        try:
            return await self._call_hf_pipeline("qwen", "Qwen/Qwen2.5-3B-Instruct", prompt)
        except Exception as exc:
            msg = f"Qwen fallback failure: {exc}"
            logger.warning(msg)
            errors.append(msg)

        raise RuntimeError("All generation backends failed: " + "; ".join(errors))

    async def _call_openai(self, prompt: str) -> str:
        url = f"{self.openai_api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_new_tokens,
        }
        delay = 1.0
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self.session.post(url, headers=headers, json=payload) as response:
                    text = await response.text()
                    if response.status != 200:
                        raise RuntimeError(f"OpenAI API error {response.status}: {text}")
                    data = json.loads(text)
                    choices = data.get("choices") or []
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content")
                        if isinstance(content, list):
                            return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
                        return str(content or "").strip()
                    if "output" in data:
                        return json.dumps(data["output"])
                    raise RuntimeError(f"Unexpected OpenAI response format: {data}")
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(delay)
                delay *= BACKOFF_FACTOR
        raise RuntimeError("OpenAI retries exhausted.")

    async def _call_inception(self, prompt: str) -> str:
        url = f"{self.inception_api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.inception_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.mercury_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_new_tokens,
        }
        async with self.session.post(url, headers=headers, json=payload) as response:
            text = await response.text()
            if response.status != 200:
                raise RuntimeError(f"Inception API error {response.status}: {text}")
            data = json.loads(text)
            choices = data.get("choices") or []
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
            if "content" in data:
                return str(data["content"]).strip()
            raise RuntimeError(f"Unexpected response from Inception Labs API: {data}")

    async def _call_hf_pipeline(self, key: str, model_name: str, prompt: str) -> str:
        pipe = await self._ensure_pipeline(key, model_name)

        def _run_generation() -> str:
            outputs = pipe(
                prompt,
                max_new_tokens=self.max_new_tokens,
                temperature=max(self.temperature, 0.2),
                do_sample=True,
            )
            if not outputs:
                raise RuntimeError("Pipeline returned no output.")
            generated = outputs[0].get("generated_text", "")
            return str(generated).strip()

        return await asyncio.to_thread(_run_generation)

    async def _ensure_pipeline(self, key: str, model_name: str):
        if key in self._hf_pipelines:
            return self._hf_pipelines[key]

        def _load_pipeline():
            logger.info("Loading Hugging Face pipeline: %s", model_name)
            device = 0 if torch.cuda.is_available() else -1
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            return pipeline(
                "text-generation",
                model=model_name,
                tokenizer=model_name,
                device=device,
                torch_dtype=dtype,
            )

        pipe = await asyncio.to_thread(_load_pipeline)
        self._hf_pipelines[key] = pipe
        return pipe


async def expand_questions_batch(
    engine: LLMEngine,
    batch_questions: List[str],
    prompt_template: str,
    existing_questions: Set[str],
) -> List[Dict[str, Any]]:
    async def _run(question: str) -> Dict[str, Any]:
        formatted_prompt = prompt_template.replace("{question}", question)
        try:
            model_output = await engine.generate(formatted_prompt)
            return parse_model_output(question, model_output)
        except Exception as exc:
            logger.error("Failed to expand question '%s': %s", question, exc)
            return fallback_record(question, str(exc))

    responses = await asyncio.gather(*[_run(question) for question in batch_questions])
    unique_records: List[Dict[str, Any]] = []
    seen_batch: Set[str] = set()
    for record in responses:
        candidate = normalize_question(record.get("new_question"))
        if not candidate or candidate in existing_questions or candidate in seen_batch:
            continue
        seen_batch.add(candidate)
        unique_records.append({"seed": record.get("seed"), "new_question": candidate})
    existing_questions.update(seen_batch)
    return unique_records


async def generate_category(
    engine: LLMEngine,
    spec: CategoryConfig,
    batch_size: int,
) -> List[Dict[str, Any]]:
    question_queue: deque[str] = deque(spec.seeds)
    generated_questions: Set[str] = set(spec.seeds)
    dataset: List[Dict[str, Any]] = []
    max_attempts = spec.num_samples * 10
    attempts = 0

    logger.info("Starting generation for category '%s' (target=%s)", spec.canonical_name, spec.num_samples)

    with tqdm(total=spec.num_samples, desc=f"{spec.canonical_name.title()} samples") as progress:
        while len(dataset) < spec.num_samples and attempts < max_attempts:
            batch_target = min(batch_size, spec.num_samples - len(dataset))
            current_batch: List[str] = []
            while len(current_batch) < batch_target:
                if not question_queue:
                    raise RuntimeError(f"Question pool exhausted for category {spec.canonical_name}")
                question = question_queue.popleft()
                current_batch.append(question)
                question_queue.append(question)

            batch_records = await expand_questions_batch(
                engine,
                current_batch,
                spec.prompt,
                generated_questions,
            )
            attempts += len(current_batch)

            for record in batch_records:
                question_text = record.get("new_question")
                if not question_text:
                    continue
                dataset.append(
                    {
                        "seed": record.get("seed"),
                        "question": question_text,
                        "category": spec.canonical_name,
                    }
                )
                progress.update(1)
                if len(dataset) >= spec.num_samples:
                    break

        if len(dataset) < spec.num_samples:
            logger.warning(
                "Category '%s' stopped early with %s/%s samples (max attempts reached).",
                spec.canonical_name,
                len(dataset),
                spec.num_samples,
            )
        else:
            logger.info("Completed category '%s' (%s samples).", spec.canonical_name, len(dataset))
    return dataset


def write_dataset(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info("Saved %s samples to %s (JSONL)", len(records), path)


async def generate_data() -> None:
    settings, categories = load_generation_plan()
    timeout = aiohttp.ClientTimeout(total=180)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        engine = LLMEngine(
            session,
            openai_model=settings.openai_model,
            temperature=settings.temperature,
            max_new_tokens=settings.max_new_tokens,
        )
        for spec in categories:
            try:
                records = await generate_category(engine, spec, settings.batch_size)
                write_dataset(spec.output_path, records)
            except Exception as exc:
                logger.exception("Failed to generate data for category '%s': %s", spec.canonical_name, exc)


def main() -> None:
    try:
        asyncio.run(generate_data())
    except KeyboardInterrupt:
        logger.warning("Generation interrupted by user.")
    except Exception as exc:
        logger.exception("Generation failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
