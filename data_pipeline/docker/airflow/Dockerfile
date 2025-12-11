FROM apache/airflow:3.0.0-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        gfortran \
    && rm -rf /var/lib/apt/lists/*
USER airflow

WORKDIR /opt/airflow

# Copy requirements from the correct path
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copy project files (these will be overridden by volume mounts in docker-compose)
COPY data_pipeline/dags /opt/airflow/dags
COPY data_pipeline/data /opt/airflow/data
COPY data_pipeline/config /opt/airflow/config

ENV VISION_MODEL_API_URL=http://vm-api:8000
