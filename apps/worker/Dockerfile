# Build from the repo root so the shared schemas are in the context:
#   docker build -f apps/worker/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Kolkata

WORKDIR /app
COPY packages/schemas packages/schemas
COPY apps/worker apps/worker
RUN pip install ./packages/schemas ./apps/worker \
    && useradd --create-home citebell

USER citebell
CMD ["citebell-worker", "scheduler"]
