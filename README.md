# SecureShip

### Repository skeleton (reference shape, not generated for you)

This is an **illustrative directory layout only** — there is no starter scaffold provided alongside this README. Per Section 7, teams use Claude Code in Week 1 to generate the actual project from scratch; this tree exists so a team has something to point Claude Code at ("set up a repo shaped roughly like this") rather than starting from a totally blank prompt.

```text
secureship/
├── docker-compose.yml
├── README.md                      # team's own README — AI-drafted, human-corrected (Section 7.1)
├── docs/
│   ├── certificates/               # Skilljar certs from Section 2's parallel learning track
│   └── diagrams/                   # Section 6 diagrams, regenerated against real build (Week 5)
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── orval.config.ts             # Section 4.8 — points at backend's /openapi.json
│   └── src/
│       ├── api/
│       │   └── generated/          # Orval output — generated hooks + types, DO NOT hand-edit (Section 4.8)
│       ├── components/
│       │   ├── ChatWindow/         # Epic A — the core chat UI
│       │   ├── CodeModal/          # Epic C — on-demand 6-digit code modal
│       │   └── EscalationBanner/   # Epic G — cosmetic human-handoff theater
│       ├── admin/                  # Epic E — admin panel (Auth0-protected)
│       │   ├── CustomerManager/
│       │   ├── ShipmentManager/
│       │   └── ChatSessionViewer/  # OPTIONAL bonus (Section 8, Week 5) — read-only session browser
│       └── lib/
│           ├── chatTransport.ts    # HTTP fetch OR WebSocket client — Section 6.3/6.3b decision lives here
│           └── chatStore.ts        # Zustand store — WS path only (Section 4.8); not needed on the HTTP path
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # app entrypoint, health-check route
│   ├── routes/
│   │   ├── chat.py                 # /chat (HTTP) or the WS gateway — Epic A/B/C/D
│   │   ├── verify.py               # /verify-code — Epic C
│   │   ├── admin.py                # /admin/* — Epic E, protected by Auth0 middleware
│   │   └── _types_chat_events.py   # WS PATH ONLY — dummy, never-called endpoints whose sole job
│   │                               #   is exporting the WS message-envelope Pydantic models into
│   │                               #   the OpenAPI schema for Orval/openapi-typescript (Section 4.8)
│   ├── tools/                      # Epic F — the enforcement layer, called by the model via tool-calling
│   │   ├── verify_identity.py
│   │   ├── send_verification_code.py
│   │   ├── check_verification_code.py
│   │   └── lookup_shipments.py     # ALWAYS scoped to session.customer_id — see Section 6.3 note
│   ├── llm/
│   │   └── ollama_client.py        # wraps calls to localhost:11434 (or host.docker.internal — Section 4.7)
│   ├── models/                     # ORM models: Customer, Shipment, Package, ChatSession (Section 4.4/4.6)
│   └── db/
│       └── session.py              # Postgres connection (and the JSONB ChatSession persistence — Section 4.6)
│
└── scripts/
    └── seed_data.py                 # Section 4.4 — mock data generation, schema-conformant
```


### Local dev setup

1. Install Podman CLI from [Podman.io](https://podman.io/)

2. Install `podman-compose`

```bash
brew install podman-compose
```

3. Start the database

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

Subsequent runs — just start the existing container:

```bash
podman start postgres
```

This runs Postgres 16 on `localhost:5432` with database `secureship` (user `user`, password `pass`) — the same configuration as the `postgres` service in `docker-compose.yml`. The backend and the scripts below connect via the `DATABASE_URL` env var and default to exactly this instance, so no configuration is needed for local dev.

> Alternatively, `podman-compose up -d postgres` from the repo root starts the same database via compose — but don't mix the two approaches, since both bind port 5432.

4. Install backend dependencies

```bash
cd ./backend
uv sync
```

5. Initialize the database schema (run migrations)

```bash
# from ./backend
uv run alembic upgrade head
```

The schema is defined as SQLAlchemy models in `backend/app/models.py` (see `docs/diagrams/data-model-ERD.md`) and applied through Alembic migrations. Re-run this command whenever you pull changes that include a new migration.

When you change the models yourself, generate a new migration and apply it:

```bash
# from ./backend
uv run alembic revision --autogenerate -m "describe your change"
uv run alembic upgrade head
```

6. Seed mock data (Section 4.4)

```bash
# from ./backend
uv run python ../scripts/seed_data.py
```

Generates 30 customers, 50 shipments (realistic status distribution, including a few `exception` cases), and 1–3 packages per shipment. The script is deterministic (fixed random seed) and idempotent — re-running truncates and re-seeds, so it's safe to run anytime you want a clean dataset.

7. Start backend server

```bash
# from ./backend
uv run fastapi dev main.py
```

8. Start frontend server

```bash
cd ./frontend
npm install
npm run dev

```