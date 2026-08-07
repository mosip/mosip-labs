FROM python:3.13-slim

# Required by the mosip/kattu docker-build reusable workflow's build-check step.
ARG SOURCE
ARG COMMIT_HASH
ARG COMMIT_ID
ARG BUILD_TIME
LABEL source=${SOURCE}
LABEL commit_hash=${COMMIT_HASH}
LABEL commit_id=${COMMIT_ID}
LABEL build_time=${BUILD_TIME}

# libgomp1 — required by PyTorch (sentence-transformers)
# curl     — used by K8s liveness probes
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app/MosipNexus/Server

# Dependency layer (cached unless pyproject.toml changes)
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync

# Application source (data/ excluded by .dockerignore — mount at runtime)
COPY . .

# Pre-cache HuggingFace embedding model (~1.1 GB)
ENV PYTHONPATH=/app/MosipNexus/Server
RUN uv run python -c \
    "from langchain_huggingface import HuggingFaceEmbeddings; \
     HuggingFaceEmbeddings(model_name='intfloat/multilingual-e5-base'); \
     print('HF model cached.')"

EXPOSE 8000 8002

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Default: FastAPI. Prefer 1 worker (shared HF model). Sessions now live in Postgres.
# Compose / K8s override workers and --limit-concurrency for load.
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "64"]
