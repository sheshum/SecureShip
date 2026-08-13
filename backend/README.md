# Backend

FastAPI + SQLAlchemy + LiteLLM. All commands run from the `backend/` directory.

## Setup

```bash
uv sync                  # install dependencies
```

## Development server

```bash
uv run fastapi dev main.py          # http://localhost:8000
```

## Database

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Create a new migration after editing app/models.py
uv run alembic revision --autogenerate -m "describe your change"

# Seed 30 customers / 50 shipments / packages (deterministic, idempotent)
uv run python ../scripts/seed_data.py
```

## Environment variables

Copy to `backend/.env` and fill in values as needed.

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/secureship

# LLM — defaults to local Ollama; swap to any LiteLLM-supported provider
LLM_MODEL=ollama_chat/llama3.2
LLM_API_BASE=http://localhost:11434
LLM_API_KEY=                          # leave blank for Ollama

# Auth0 — only needed for the /dashboard admin panel
AUTH0_DOMAIN=
AUTH0_AUDIENCE=

# Optional tuning
AUTH_SESSION_TTL_SECONDS=1800
OTP_TTL_SECONDS=300
OTP_MAX_ATTEMPTS=5
OTP_RESEND_COOLDOWN_SECONDS=45
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

## Linting

```bash
# Check for issues
uv run ruff check .

# Auto-fix safe issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Combined: fix + format
uv run ruff check --fix . && uv run ruff format .

# Check formatting without modifying
uv run ruff format --check .

# Show unsafe fixes available (apply with --unsafe-fixes — use with caution)
uv run ruff check --unsafe-fixes .

# Stats
uv run ruff check . --statistics
```
