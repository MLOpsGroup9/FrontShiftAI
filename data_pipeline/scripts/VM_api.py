import base64
import io
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, model_validator
from transformers import AutoModelForImageTextToText, AutoProcessor


"""
Expose a microservice that generates captions for individual or batches of images.
The service is designed to run as an Airflow task and defaults to the compact SmolVLM
instruct model.
This module adds production safeguards around input validation, logging, and health checks.
"""


BASE_DIR = Path(__file__).resolve().parents[1]  # one level up from scripts/
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs" / "processed_pdf_log")).expanduser()
ALLOWED_IMAGE_ROOT = Path(os.getenv("CAPTION_IMAGE_ROOT", BASE_DIR / "data" / "parsed")).expanduser().resolve()

LOG_DIR.mkdir(parents=True, exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "processed_pdf.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("vision_model_api")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info("Using device: %s", device)


MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", 5 * 1024 * 1024))  # 5 MiB default
MAX_IMAGE_SIDE = int(os.getenv("MAX_IMAGE_SIDE", 4096))  # Prevent decompression bombs
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", 4096 * 4096))
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", 8))
ALLOWED_IMAGE_ROOT = Path(os.getenv("CAPTION_IMAGE_ROOT", ".")).expanduser().resolve()
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_IMAGE_FORMATS = {fmt.strip(".") for fmt in ALLOWED_IMAGE_EXTENSIONS}


class ModelLoader(str, Enum):
    VISION_TO_SEQ = "vision-to-seq"


@dataclass(frozen=True)
class ModelBundle:
    """Container for the cached model assets."""

    key: str
    model: torch.nn.Module
    processor: Any
    tokenizer: Optional[Any] = None


MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "smolvlm-256m-instruct": {
        "repo_id": "HuggingFaceTB/SmolVLM-256M-Instruct",
        "loader": ModelLoader.VISION_TO_SEQ,
        "max_new_tokens": 96,
        "prompt": "<image>\nDescribe the image in detail.",
    },
}

MODEL_ALIASES: Dict[str, str] = {
    "default": "smolvlm-256m-instruct",
    "smolvlm": "smolvlm-256m-instruct",
    "smolvlm256-instruct": "smolvlm-256m-instruct",
    "smolvlm-256m-instruct": "smolvlm-256m-instruct",
}

DEFAULT_MODEL_KEY = "smolvlm-256m-instruct"


class ImagePayload(BaseModel):
    """Input payload for a single image."""

    image_path: Optional[str] = Field(
        default=None,
        description="Path to an image accessible on the service host.",
    )
    # image_b64: Optional[str] = Field(
    #     default=None,
    #     description="Base64 encoded image bytes.",
    # )

    # @model_validator(mode="after")
    # def validate_source(cls, values: "ImagePayload") -> "ImagePayload":
    #     if bool(values.image_path) == bool(values.image_b64):
    #         raise ValueError("Provide exactly one of `image_path` or `image_b64`.")
    #     return values


class CaptionRequest(ImagePayload):
    """Request body for single-image caption generation."""

    model_name: Optional[str] = Field(
        default=DEFAULT_MODEL_KEY,
        description="Model identifier or alias. Defaults to the compact SmolVLM instruct model.",
    )


class CaptionResponse(BaseModel):
    """Response body for a single caption."""

    caption: str
    model_name: str
    source: str
    inference_seconds: float


class BatchCaptionRequest(BaseModel):
    """Request body for batch captioning."""

    images: List[ImagePayload]
    model_name: Optional[str] = Field(
        default=DEFAULT_MODEL_KEY,
        description="Model identifier or alias applied to the entire batch.",
    )


class BatchCaptionResponse(BaseModel):
    """Response body for batch captioning results."""

    results: List[CaptionResponse]
    batch_inference_seconds: float


def _normalise_model_key(model_name: Optional[str]) -> str:
    """Resolve user-provided alias to a known model key."""
    if not model_name:
        return DEFAULT_MODEL_KEY
    key = model_name.strip().lower()
    for variant in ("–", "—", "‑", "_"):
        key = key.replace(variant, "-")
    resolved = MODEL_ALIASES.get(key, key)
    if resolved not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{model_name}'. "
            f"Available options: {sorted(MODEL_REGISTRY.keys())}",
        )
    return resolved


@lru_cache(maxsize=len(MODEL_REGISTRY))
def _load_model_bundle(model_key: str) -> ModelBundle:
    """Load and cache a model bundle for the given key."""
    config = MODEL_REGISTRY[model_key]
    repo_id = config["repo_id"]

    try:
        if config["loader"] != ModelLoader.VISION_TO_SEQ:
            raise ValueError(f"Unsupported loader type {config['loader']}")

        processor = AutoProcessor.from_pretrained(repo_id)
        tokenizer = None
        model = AutoModelForImageTextToText.from_pretrained(repo_id)
    except Exception as exc: 
        logger.exception("Failed loading model '%s': %s", repo_id, exc)
        raise RuntimeError(f"Failed to load model '{repo_id}': {exc}") from exc

    model.to(device)
    model.eval()
    logger.info("Loaded model '%s' on %s", repo_id, device)
    return ModelBundle(key=model_key, model=model, processor=processor, tokenizer=tokenizer)


def _ensure_within_allowed_root(resolved_path: Path) -> None:
    """Ensure the resolved path lives under the allowed root directory."""
    try:
        resolved_path.relative_to(ALLOWED_IMAGE_ROOT)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Image path is outside of the allowed directory.",
        ) from exc


def _decode_base64_image(encoded: str) -> bytes:
    """Decode a base64 image while enforcing size constraints."""
    estimated_bytes = len(encoded) * 3 // 4
    if estimated_bytes > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image exceeds maximum allowed size of {MAX_IMAGE_BYTES} bytes.",
        )
    try:
        return base64.b64decode(encoded, validate=True)
    except (base64.binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image payload: {exc}") from exc


def _validate_image_constraints(image: Image.Image) -> None:
    """Validate image size, format, and dimension constraints."""
    if image.format:
        fmt = image.format.lower()
        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format '{fmt}'. "
                f"Allowed formats: {sorted(ALLOWED_IMAGE_FORMATS)}",
            )

    width, height = image.size
    if width > MAX_IMAGE_SIDE or height > MAX_IMAGE_SIDE:
        raise HTTPException(
            status_code=400,
            detail=f"Image dimensions {width}x{height} exceed maximum side length of {MAX_IMAGE_SIDE}px.",
        )
    if width * height > MAX_IMAGE_PIXELS:
        raise HTTPException(
            status_code=400,
            detail=f"Image contains {width * height} pixels which exceeds the limit of {MAX_IMAGE_PIXELS}.",
        )


def _load_image(payload: ImagePayload) -> Image.Image:
    """Load an image from disk or from a base64-encoded string, enforcing security limits."""
    if payload.image_path:
        path_obj = Path(payload.image_path).expanduser()
        if not path_obj.is_absolute():
            path_obj = (ALLOWED_IMAGE_ROOT / path_obj).resolve()
        resolved_path = path_obj.resolve()
        _ensure_within_allowed_root(resolved_path)

        if not resolved_path.is_file():
            raise HTTPException(status_code=404, detail=f"Image path not found: {resolved_path}")
        if resolved_path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{resolved_path.suffix}'. "
                f"Allowed extensions: {sorted(ALLOWED_IMAGE_EXTENSIONS)}",
            )
        if resolved_path.stat().st_size > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Image file exceeds maximum allowed size of {MAX_IMAGE_BYTES} bytes.",
            )
        try:
            with resolved_path.open("rb") as infile:
                image = Image.open(infile)
                image.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to open image at '{resolved_path}': {exc}",
            ) from exc
    else:
        encoded = payload.image_b64 or ""
        image_bytes = _decode_base64_image(encoded)
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail=f"Failed to decode base64 image payload: {exc}") from exc

    _validate_image_constraints(image)
    return image.convert("RGB")


def _generate_caption(image: Image.Image, bundle: ModelBundle) -> str:
    """Generate a caption with the selected model bundle."""
    config = MODEL_REGISTRY[bundle.key]

    if config["loader"] == ModelLoader.VISION_TO_SEQ:
        prompt = config.get("prompt") or "Describe the image."
        inputs = bundle.processor(
            text=[prompt],
            images=[image],
            return_tensors="pt",
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            output_ids = bundle.model.generate(
                **inputs,
                max_new_tokens=config.get("max_new_tokens", 96),
            )
        caption = bundle.processor.batch_decode(output_ids, skip_special_tokens=True)[0]
        return caption.strip()

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported loader configuration for model '{bundle.key}'",
    )


def _describe_source(payload: ImagePayload, index: int) -> str:
    """Return a human-readable identifier for the image source."""
    if payload.image_path:
        path_obj = Path(payload.image_path)
        return str((ALLOWED_IMAGE_ROOT / path_obj).resolve()) if not path_obj.is_absolute() else str(path_obj)
    return f"inline_base64_{index}"


def _get_model_bundle(model_name: Optional[str]) -> ModelBundle:
    """Wrapper to normalise model name and handle load errors."""
    model_key = _normalise_model_key(model_name)
    try:
        return _load_model_bundle(model_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@asynccontextmanager
async def preload_models(_app: FastAPI) -> AsyncIterator[None]:
    """Load all configured models during startup so readiness reflects availability."""
    start = time.perf_counter()
    for key in MODEL_REGISTRY:
        _get_model_bundle(key)
    elapsed = time.perf_counter() - start
    logger.info("Preloaded %d model(s) in %.2f seconds", len(MODEL_REGISTRY), elapsed)
    yield


app = FastAPI(title="Vision Transformer Captioning Service", lifespan=preload_models)


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that logs unhandled exceptions."""
    logger.exception(
        "Unhandled error processing %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["health"])
def health() -> Dict[str, str]:
    """Basic health endpoint for liveness/readiness probes."""
    return {"status": "ok", "device": str(device)}


@app.post("/caption", response_model=CaptionResponse)
def caption(request: CaptionRequest) -> CaptionResponse:
    """Generate a caption for a single image."""
    bundle = _get_model_bundle(request.model_name)

    image = _load_image(request)
    start = time.perf_counter()
    caption_text = _generate_caption(image, bundle)
    inference_seconds = time.perf_counter() - start

    source = _describe_source(request, index=0)
    logger.info(
        "Caption generated using model '%s' for source '%s' in %.2f seconds",
        bundle.key,
        source,
        inference_seconds,
    )
    return CaptionResponse(
        caption=caption_text,
        model_name=bundle.key,
        source=source,
        inference_seconds=round(inference_seconds, 4),
    )


@app.post("/batch_caption", response_model=BatchCaptionResponse)
def batch_caption(request: BatchCaptionRequest) -> BatchCaptionResponse:
    """Generate captions for a batch of images."""
    if not request.images:
        raise HTTPException(status_code=400, detail="Request must contain at least one image.")
    if len(request.images) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(request.images)} exceeds limit of {MAX_BATCH_SIZE}.",
        )

    bundle = _get_model_bundle(request.model_name)

    results: List[CaptionResponse] = []
    start_batch = time.perf_counter()

    for idx, payload in enumerate(request.images):
        image = _load_image(payload)
        start = time.perf_counter()
        caption_text = _generate_caption(image, bundle)
        inference_seconds = time.perf_counter() - start
        source = _describe_source(payload, index=idx)
        results.append(
            CaptionResponse(
                caption=caption_text,
                model_name=bundle.key,
                source=source,
                inference_seconds=round(inference_seconds, 4),
            )
        )
        logger.info(
            "Batch item %d captioned using model '%s' in %.2f seconds",
            idx,
            bundle.key,
            inference_seconds,
        )

    batch_seconds = time.perf_counter() - start_batch
    logger.info(
        "Batch captioned (%d images) using model '%s' in %.2f seconds",
        len(results),
        bundle.key,
        batch_seconds,
    )

    return BatchCaptionResponse(results=results, batch_inference_seconds=round(batch_seconds, 4))


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))