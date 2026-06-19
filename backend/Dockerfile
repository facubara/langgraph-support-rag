# syntax=docker/dockerfile:1
# Single-stage image: the app is pure Python and runs the API + dashboard from one process.
FROM python:3.13-slim AS runtime

# - PYTHONDONTWRITEBYTECODE: no .pyc clutter in the image / mounted volume
# - PYTHONUNBUFFERED: logs stream straight to `docker logs`
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first so the layer caches across code-only changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code (data/runtime is created at runtime and lives on a mounted volume).
COPY app ./app

# Run as an unprivileged user; pre-create the runtime dir so it's writable.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/runtime \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness without bundling curl: hit /health from the interpreter that's already here.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status==200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
