FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations

FROM base AS runtime
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "harvest_edge.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test
RUN pip install --no-cache-dir '.[dev]'
COPY tests ./tests
COPY scripts ./scripts
CMD ["pytest", "-q"]