FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VISION_MODEL_PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch stack before project requirements to leverage wheel caching.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision torchaudio

COPY data_pipeline/docker/vm_api/requirements.txt /tmp/requirements_vm.txt
RUN pip install --no-cache-dir -r /tmp/requirements_vm.txt && rm -rf /tmp/pip-*

COPY data_pipeline /app/data_pipeline

EXPOSE 8000

CMD ["uvicorn", "data_pipeline.scripts.VM_api:app", "--host", "0.0.0.0", "--port", "8000"]
