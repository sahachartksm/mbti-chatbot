# ====== AI Service (FastAPI + scikit-learn + SBERT) ======
FROM python:3.12-slim

# System deps (g++/gcc needed for some ML wheels; curl used by healthcheck fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache layer: install deps first
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source (volume mount will override in dev, but keep for prod build)
COPY . ./

# Ensure models dir exists (will be volume-mounted in compose)
RUN mkdir -p /app/models

# Force file-watching via polling (Windows Docker bind mounts need this)
ENV WATCHFILES_FORCE_POLLING=true
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Entrypoint: train if model missing, then run uvicorn with hot reload
CMD ["sh", "-c", "if [ ! -f models/mbti_model.pkl ]; then echo '>> Training model (first start)...'; python train.py; fi; exec uvicorn app:app --host 0.0.0.0 --port 8000 --reload"]
