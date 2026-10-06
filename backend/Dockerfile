# AI-LifeOS backend image.
#
# Multi-stage: wheels are built once in a builder and copied into a slim
# runtime, so compilers and build headers never ship to production.
#
# Configuration is supplied entirely through environment variables at runtime
# (see .env.example). No secrets are baked into the image.

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
FROM python:3.10-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# psycopg2-binary ships prebuilt wheels, but build-essential and libpq-dev are
# kept here so the build still succeeds on platforms without one.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

COPY requirements.txt .

RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl is used by the compose healthcheck below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .

RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Run as a non-root user.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Note: migrations are NOT run at startup. Run them as a separate release step
# (`alembic upgrade head`) so a schema change is an explicit, ordered action
# rather than something that happens implicitly on every boot.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
