# SecureShip

A customer-support chat app where a React frontend talks to a FastAPI backend running an LLM agent. The agent can look up shipments for a verified customer. Access to shipment data is gated behind an in-chat identity verification + OTP flow — the core constraint is that **the LLM is never trusted to authorize data access**; only server-side session state is.

## Folder structure

```text
secureship/
├── docker-compose.yml
├── backend/              # FastAPI + SQLAlchemy + LiteLLM
│   ├── main.py
│   ├── alembic/          # database migrations
│   └── app/
│       ├── agent/        # LLM agentic loop
│       ├── core/         # settings / config
│       ├── llm/          # provider-agnostic LLM port
│       ├── models.py     # SQLAlchemy ORM models
│       ├── repositories/ # DB access layer
│       ├── routers/      # HTTP endpoints
│       ├── schemas/      # Pydantic request/response schemas
│       ├── services/     # auth context, dispatch, OTP gate
│       └── tools/        # LLM tool definitions
├── frontend/             # React 19 + Vite + Tailwind v4
│   └── src/
│       ├── api/generated/  # Orval-generated hooks — do not hand-edit
│       ├── auth/           # Auth0 provider wiring
│       ├── components/     # Chat UI, OTP modal, Admin tables
│       └── pages/          # ChatPage, AdminPage, WelcomePage
├── docs/diagrams/        # Mermaid architecture + ERD diagrams
└── scripts/
    ├── seed_data.py
    └── setup-hooks.sh
```

## Prerequisites

- [Podman](https://podman.io/) (or Docker) for the database container
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- Node.js 20+ and npm
- An LLM accessible via [LiteLLM](https://docs.litellm.ai/) — local [Ollama](https://ollama.com/) works out of the box

## Local dev setup

### 1. Start the database

First time — create the container:

```bash
podman run -d --name postgres \
  -e POSTGRES_DB=secureship \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=pass \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16
```

Subsequent runs:

```bash
podman start postgres
```

> Alternatively, `podman-compose up -d postgres` from the repo root — but don't mix the two approaches; both bind port 5432.

### 2. Set up and start the backend

```bash
cd backend
uv sync                                       # install dependencies
uv run alembic upgrade head                   # apply DB migrations
uv run python ../scripts/seed_data.py         # seed 30 customers / 50 shipments
uv run fastapi dev main.py                    # http://localhost:8000
```

See [backend/README.md](backend/README.md) for all backend commands, environment variables, and linting.

### 3. Set up and start the frontend

```bash
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

See [frontend/README.md](frontend/README.md) for all frontend commands and configuration.

### 4. Enable git hooks (recommended)

```bash
# from repo root
./scripts/setup-hooks.sh
```

Installs hooks from `.githooks/`: `pre-commit` lints staged files, `pre-push` runs full lint + migration sanity checks.

## Running the full stack with Docker Compose

```bash
# from repo root
podman-compose up --build
```

This starts `postgres`, `backend` (port 8000), and `frontend` (port 3000). The LLM is expected on the host at `http://host.docker.internal:11434` (e.g. Ollama). Configure `LLM_MODEL` in `backend/.env`.

## Architecture

See [`docs/diagrams/`](docs/diagrams/) for Mermaid diagrams covering:

- High-level system architecture
- Data model ERD
- Identity-gating state machine
- Tool-calling sequence
- Human escalation sequence
