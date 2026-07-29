# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SecureShip is a customer-support chat app: a React frontend talks to a FastAPI backend that runs an LLM agent (via LiteLLM, e.g. local Ollama or a hosted provider) which can look up shipments for a customer. Access to shipment data is gated behind an in-chat identity verification + OTP flow — the core design constraint of this codebase is that **the LLM is never trusted to authorize data access**; only server-side session state is.

Note: `README.md`'s "Repository skeleton" section is an illustrative/aspirational layout written before the real implementation diverged from it (different router/service/tool file names, no WebSocket path, no admin panel yet). Treat the actual `backend/app/` and `frontend/src/` trees below as authoritative, not that README tree.

## Commands

### Backend (from `backend/`)

```bash
uv sync                                    # install deps
uv run fastapi dev main.py                 # run dev server (http://localhost:8000)
uv run python -m unittest discover -s tests -t .   # run all tests
uv run python -m unittest tests.test_otp_service   # run a single test module
uv run alembic upgrade head                # apply migrations
uv run alembic revision --autogenerate -m "message"   # create a migration after editing app/models.py
uv run python ../scripts/seed_data.py      # seed 30 customers / 50 shipments (deterministic, idempotent — truncates and re-seeds)
```

Tests are plain `unittest.TestCase` (no pytest dependency installed), so always invoke them through `python -m unittest`, not `pytest`.

### Frontend (from `frontend/`)

```bash
npm install
npm run dev            # vite dev server, proxies /api -> http://localhost:8000 (or VITE_API_PROXY_TARGET)
npm run build           # tsc -b && vite build
npm run lint            # oxlint
npm run lint:fix        # oxlint --fix
npm run lint:ci         # oxlint with type-aware checking (requires backend types generated)
npm run api:sync        # pulls backend's /openapi.json and regenerates src/api/generated via orval
```

`src/api/generated/**` is Orval-generated from the backend's OpenAPI schema — never hand-edit it; change the FastAPI routers/schemas and re-run `npm run api:sync` instead.

### Local infra

Postgres 16 on `localhost:5432` (db `secureship`, user/pass `user`/`pass`), started either via bare `podman run`/`podman start postgres` or `podman-compose up -d postgres` (don't mix both — they bind the same port). Full stack (`frontend`+`backend`+`postgres`) also runs via `docker-compose.yml`; the LLM itself is expected to run on the host (Ollama at `host.docker.internal:11434`), not in a container.

## Architecture

### Backend layering (`backend/app/`)

Strict dependency direction, enforced by file layout, not just convention:

- `routers/` — HTTP/SSE transport only. No business logic. (`chat.py`, `auth_verification.py`, `sessions.py`, `health.py`)
- `services/` — business logic. `chat.py` (`ChatService`) depends only on the `LLMClient` port (`llm/base.py`), never on a concrete SDK — this is explicit in the file's own docstring. `chat_streaming.py` holds the SSE event-shape helpers and the auth-gate decision logic shared by the two chat routes. `auth_session.py`, `otp.py`, `identity_verification.py`, `sms.py` implement the identity/OTP flow.
- `repositories/` — DB access (`chat_sessions.py`, `customers.py`, `shipments.py`).
- `llm/` — the provider-agnostic port. `base.py` defines `LLMClient`/`LLMMessage`/`ToolCall` (no SDK imports allowed here); `litellm_client.py` is the concrete adapter; `tools.py` defines the tool schemas the model can call plus `execute_tool_call`, which is where authorization is actually enforced.
- `dependencies.py` — the only place concrete adapters are wired to abstract ports (e.g. which `LLMClient` implementation is used). Swapping LLM providers is a `Settings`-only change (`LLM_MODEL`/`LLM_API_BASE`/`LLM_API_KEY`), never a code change in `services/` or `llm/base.py`.
- `models.py` — SQLAlchemy models: `Customer`, `Shipment`, `Package`, `ChatSession` (auth state + JSONB `transcript`), `AdminUser`. Schema changes go through Alembic (`alembic/versions/`), not manual SQL.

### The auth-gate / OTP flow (the load-bearing part of this codebase)

This is fully described in `Auth-OTP-Session-Gating-Implementation-Plan.md` and `docs/diagrams/conversation-identity-gating-state-machine.md` / `tooling-call-sequence.md` — read those before changing anything in this area. Short version:

- `ChatSession` state machine: `anonymous → collecting_identity → code_sent → awaiting_code → verified` (plus `escalated_to_human`). Durable state + full transcript live in Postgres (`chat_session` table). It's a **hybrid** store: `AuthSessionStore` (in-memory today, `InMemoryAuthSessionStore` in `services/auth_session.py`) holds short-lived, high-churn auth data — OTP code hash, attempt count, expiry, resend cooldown — keyed by `chat_session.id`. A Redis swap is the intended future migration path without touching authorization logic.
- The chat agent runs in one of two modes depending on whether the session is verified: `ChatService.agent_stream` (shipment tools available) or `ChatService.auth_gate_stream` (only `request_identity_info`/`verify_identity` tools available, forced via a system prompt). `routers/chat.py` decides which one to invoke per-turn based on `resolve_auth_gate()`.
- **Enforcement boundary is `llm/tools.py::execute_tool_call`, not the prompt.** Shipment tools always derive `customer_id` from `AuthContext` (built server-side from verified session state) — a model- or user-supplied customer/user id is never accepted as authorization input. If you add a new tool that touches customer data, it must take its scope from `AuthContext`, never from tool-call arguments.
- When a turn requires auth mid-stream, the backend persists a "pending turn" (`ChatSessionRepository.set_pending_turn`/`get_pending_turn`) so that after OTP verification the frontend can resume the original request via `POST /api/chat/continue` rather than resending it from scratch. `verify_code` in `routers/auth_verification.py` returns the `pending_turn_id` for exactly this purpose.

### SSE wire protocol (`/api/chat`, `/api/chat/continue`)

One JSON object per `data:` line, event types: `session`, `auth_state`, `token`, `tool_call`, `tool_result`, `show_code_modal`, `auth_required`, `error`, `done`. The shape of each is defined in `services/chat_streaming.py`; frontend parsing lives in `frontend/src/api/chatStream.ts`.

### Frontend structure (`frontend/src/`)

- `api/generated/` — Orval output (react-query hooks + Zod-less TS types) from the backend OpenAPI schema. Regenerate, don't edit.
- `api/chatStream.ts` — hand-written SSE client (fetch + ReadableStream, not the generated client) since Orval doesn't model streaming.
- `features/chat/useChatStream.ts` — wraps `chatStream.ts` in a hook (abort handling, streaming state).
- `features/chat/useChatSessions.ts` — session/message list state (append tokens, pending turns, placeholders).
- `pages/ChatPage.tsx` — orchestrates the above: sends chat requests, reacts to `auth_required`/`show_code_modal` SSE events by opening `OtpVerificationModal`, and resumes the pending turn via `continuePending` after successful OTP verification.
- Styling is Tailwind v4 (via `@tailwindcss/vite`), React 19 with the React Compiler enabled through a Babel plugin in `vite.config.ts` (not the standard `babel-plugin-react-compiler` wiring — check that file before assuming compiler behavior).

### Diagrams

`docs/diagrams/*.md` are Mermaid docs describing the system architecture, data model ERD, the identity-gating state machine, the tool-calling sequence, human-escalation sequence, and local dev topology — check these first when working on cross-cutting flows instead of re-deriving them from code. If asked to create/edit a diagram, follow `.github/instructions/mermaid.instructions.md` (write `.mmd` files, validate with the Mermaid VS Code extension tools, don't hand-edit diagrams managed by Mermaid Chart sync).
