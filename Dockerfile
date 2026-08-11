FROM python:3.13.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system fabcopilot \
    && adduser --system --ingroup fabcopilot fabcopilot \
    && mkdir -p /var/cache/fabcopilot \
    && chown fabcopilot:fabcopilot /var/cache/fabcopilot

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations

RUN python -m pip install --prefer-binary .

ENV HOME=/var/cache/fabcopilot \
    HF_HOME=/var/cache/fabcopilot/huggingface \
    HF_HUB_DISABLE_XET=1

USER fabcopilot

EXPOSE 8000

CMD ["uvicorn", "fabcopilot.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
