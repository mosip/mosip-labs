FROM python:3.13-slim

# libgomp1 — required by PyTorch (sentence-transformers)
# curl     — used by K8s liveness probes
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN pip install --no-cache-dir uv

WORKDIR /app/MosipNexus

# --- Dependency layer (cached unless pyproject.toml changes) ---
COPY pyproject.toml ./
# Generate uv.lock if not present; use it if it is (reproducible builds).
# Run `uv lock && git add uv.lock` before building to pin exact versions.
RUN uv sync

# --- Application source (data/ and secrets excluded by .dockerignore) ---
COPY . .

# --- Pre-cache the HuggingFace embedding model (~1.1 GB) ---
# This bakes the model into the image so pods start with zero download delay.
# The model is stored at /root/.cache/huggingface inside the image.
RUN uv run python -c \
    "from langchain_huggingface import HuggingFaceEmbeddings; \
     HuggingFaceEmbeddings(model_name='intfloat/multilingual-e5-base'); \
     print('HF model cached.')"

# PYTHONPATH ensures imports resolve from within /app/MosipNexus
ENV PYTHONPATH=/app/MosipNexus

EXPOSE 8000 8501

# Default: API server. K8s deployment-ui.yaml overrides this with streamlit.
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
