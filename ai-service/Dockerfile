# ── Base image ───────────────────────────────────────────────────────────────
# Use the standard Python slim image for CPU-only deployments.
# For GPU support, swap this line with:
#   FROM nvidia/cuda:12.3.1-runtime-ubuntu22.04
# and add the nvidia runtime to your docker-compose service.
FROM python:3.11-slim

WORKDIR /app

# ── System packages needed by PyMuPDF / pdfplumber ───────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmupdf-dev \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .

# Install PyTorch CPU-only wheel first so we don't pull in ~3 GB CUDA packages.
# If GPU is available, remove the --index-url line and let torch auto-select.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY app ./app

# ── Pre-download the model at build time (optional, improves cold-start) ─────
# This step runs only when PREFETCH_MODEL is set to "true" at build time.
# Example: docker build --build-arg PREFETCH_MODEL=true …
ARG PREFETCH_MODEL=false
ARG AI_MODEL_NAME=Qwen/Qwen2-VL-2B-Instruct
RUN if [ "$PREFETCH_MODEL" = "true" ]; then \
      python -c "from transformers import AutoProcessor, Qwen2VLForConditionalGeneration; \
                 AutoProcessor.from_pretrained('${AI_MODEL_NAME}', trust_remote_code=True); \
                 Qwen2VLForConditionalGeneration.from_pretrained('${AI_MODEL_NAME}', trust_remote_code=True)"; \
    fi

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=10s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
