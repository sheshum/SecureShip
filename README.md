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

3. Start backend server

```
cd ./backend
uv sync
uv run fastapi dev main.py
```
