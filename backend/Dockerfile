FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

FROM base AS deps

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

FROM base AS runtime

COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

COPY main.py ./
COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "fastapi", "dev", "main.py"]