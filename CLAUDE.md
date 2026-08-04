# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SecureShip is a customer-support chat app: a React frontend talks to a FastAPI backend that runs an LLM agent (via LiteLLM, e.g. local Ollama or a hosted provider) which can look up shipments for a customer. Access to shipment data is gated behind an in-chat identity verification + OTP flow — the core design constraint of this codebase is that **the LLM is never trusted to authorize data access**; only server-side session state is.

Note: `README.md`'s "Repository skeleton" section and `docs/diagrams/*.md` describe an illustrative/target architecture written ahead of the real implementation — e.g. they describe a WebSocket/SSE-capable chat transport, a Redis-backed session store, and an Auth0-protected admin panel. None of that is implemented today: chat is a plain synchronous `POST` returning one JSON response, all session/OTP state lives in Postgres (no in-memory or Redis store), and the admin panel (`/admin`) has no auth guard. Treat the actual `backend/app/` and `frontend/src/` trees as authoritative over those docs.

## Commands

### Backend (from `backend/`)

```bash
uv sync                                    # install deps
uv run fastapi dev main.py                 # run dev server (http://localhost:8000)
uv run ruff check .                        # lint
uv run alembic upgrade head                # apply migrations
uv run alembic revision --autogenerate -m "message"   # create a migration after editing app/models.py
uv run python ../scripts/seed_data.py      # seed 30 customers / 50 shipments (deterministic, idempotent — truncates and re-seeds)
```

There is no automated test suite yet (no `tests/` directory on either side) — don't assume test commands from stale docs; verify backend changes by running the dev server and calling the endpoints, or ask before adding a whole new test harness.

### Frontend (from `frontend/`)

```bash
npm install
npm run dev            # vite dev server, proxies /api -> http://localhost:8000 (or VITE_API_PROXY_TARGET)
npm run build           # tsc -b && vite build
npm run lint            # oxlint
npm run lint:fix        # oxlint --fix
npm run lint:ci         # oxlint with type-aware checking (requires backend types generated)
npm run api:sync        # pulls backend's /openapi.json (api:pull) and regenerates src/api/generated via orval (api:gen)
```

`src/api/generated/**` is Orval-generated from the backend's OpenAPI schema — never hand-edit it; change the FastAPI routers/schemas and re-run `npm run api:sync` instead.

### Local infra

Postgres 16 on `localhost:5432` (db `secureship`, user/pass `user`/`pass`), started either via bare `podman run`/`podman start postgres` or `podman-compose up -d postgres` (don't mix both — they bind the same port). Full stack (`frontend`+`backend`+`postgres`) also runs via `docker-compose.yml`; the LLM itself is expected to run on the host (Ollama at `host.docker.internal:11434`), not in a container.

## Architecture

### Backend layering (`backend/app/`)

Dependency direction: `routers` → `agent` → `services`/`tools` → `repositories` → `llm`.

- `routers/` — HTTP transport only, no business logic. `chat.py` (`POST /api/chat`), `auth.py` (`POST /api/auth/verify-code`), `sessions.py` (list/patch, used by admin), `shipments.py` / `packages.py` (admin read endpoints), `health.py`.
- `agent/` — the agentic loop, decoupled from persistence. `agent.py`'s `Agent.execute_turn` builds the message list (system prompt + history + new prompt), forces `tool_choice=["verify_identity"]` when the session isn't `VERIFIED`, and loops LLM → tool dispatch → LLM until the model stops calling tools. It takes an immutable `AgentSession` snapshot (`session.py`) as input and never touches the DB or persists anything — the router does that before and after calling it. `prompts.py` holds `SYSTEM_PROMPT`.
- `services/` — `auth_context.py` defines `AuthContext` (session_id/customer_id/state — the only data tools are allowed to authorize against), `dispatch.py`'s `dispatch_tool_call` is the single code path allowed to invoke a tool handler, `identity_gate.py`'s `enforce_gate` is the one-condition predicate for "is this session allowed to call a verification-gated tool", `sms_mock.py` logs OTP codes to the console instead of sending real SMS.
- `tools/` — one module per tool (`verify_identity.py`, `request_identity_info.py`, `lookup_shipments.py`, `escalate_to_human.py`), each a class decorated with `@tool(name, schema, requires_verification)` from `tool_registry.py`. Tools are constructed per-request via FastAPI DI (`dependencies.py::get_tool_registry`) so they get fresh repository instances, then registered into a shared `TOOL_REGISTRY` dict keyed by name.
- `repositories/` — DB access: `chat_sessions.py`, `customers.py`, `shipments.py`, `packages.py`, `session_verification.py` (OTP lifecycle), `session_state_machine.py` (`SessionStateValidator` — the allow-list of valid `ChatSessionState` transitions plus per-state invariants, e.g. `VERIFIED` requires `customer_id` set).
- `llm/` — the provider-agnostic port. `base.py` defines `LLMClient`/`LLMMessage`/`ToolCall`/`LLMCompletion` (no SDK imports allowed here — enforced by the file's own docstring); `litellm_client.py` is the concrete adapter.
- `dependencies.py` — the only place concrete adapters are wired to abstract ports and where tool instances are assembled into the registry. Swapping LLM providers is a `Settings`-only change (`LLM_MODEL`/`LLM_API_BASE`/`LLM_API_KEY`, see `core/config.py`), never a code change in `services/`, `tools/`, or `llm/base.py`.
- `models.py` — SQLAlchemy models: `Customer`, `Shipment`, `Package`, `ChatSession` (auth state + JSONB `transcript`), `SessionVerification` (one-to-one with `ChatSession`; OTP code hash/attempts/expiry/status — fully persisted in Postgres, not an in-memory or Redis store), `AdminUser` (defined but not yet wired to any auth flow). Schema changes go through Alembic (`alembic/versions/`), not manual SQL.

### The auth-gate / OTP flow (the load-bearing part of this codebase)

- `ChatSessionState` (`schemas/sessions.py`): `anonymous → collecting_identity → code_sent → awaiting_code → verified`, plus `code_expired` (recoverable — can retry from `anonymous`/`collecting_identity`/`code_sent`) and `escalated_to_human` (reachable from any state). `repositories/session_state_machine.py::SessionStateValidator` is the single source of truth for which transitions are legal and enforces invariants like "VERIFIED requires customer_id set" — `ChatSessionRepository.update_session` calls it on every state change.
- The `Agent` runs a single loop regardless of verification state; what changes is which tools are available/forced. While unverified, `tool_choice` is forced to `verify_identity` so the model can't ignore the gate. `request_identity_info` and `verify_identity` are `requires_verification=False` (public — that's how the flow bootstraps); `lookup_shipments` is `requires_verification=True`.
- **Enforcement boundary is `services/dispatch.py::dispatch_tool_call`, not the prompt.** For every tool call, it looks up the `ToolSpec` in the registry and, if `requires_verification` is set, calls `identity_gate.enforce_gate(context)` before the handler ever runs. Tool handlers derive `customer_id` exclusively from the server-built `AuthContext` — a model- or user-supplied customer/user id is never accepted as authorization input (see `lookup_shipments.py`'s comment on this). If you add a new tool that touches customer data, register it with `requires_verification=True` and take its scope from `AuthContext`, never from tool-call arguments.
- `verify_identity` matches name+phone against `Customer`, creates a `SessionVerification` row (SHA-256 code hash, 7-minute expiry), and returns the **same neutral message whether or not a customer matched** (enumeration-proofing) — the model is told "code sent" either way and never sees the code itself. `POST /api/auth/verify-code` (`routers/auth.py`) is the only path that can move a session to `VERIFIED`; it enforces the 3-attempt limit and expiry, hashes the submitted code before comparing, and returns neutral `incorrect`/`expired`/`verified` results.
- There is no SSE/WebSocket streaming and no "pending turn" resumption today: `POST /api/chat` is a single request/response cycle. When a turn requires verification, `ChatResponse.verification_required` is set, the frontend opens the OTP modal, and after a successful `verify-code` call the user simply sends their next message as a normal turn (the original message is not auto-resent).

### Frontend structure (`frontend/src/`)

- `api/generated/` — Orval output (react-query hooks + TS types) from the backend OpenAPI schema. Regenerate via `npm run api:sync`, don't hand-edit.
- `api/url.ts` — `resolveApiUrl`, used for the couple of hand-written `fetch` calls (e.g. closing a session) that bypass the generated client.
- `App.tsx` — three routes: `/` (`WelcomePage`), `/chat` (`ChatPage`), `/admin` (`AdminPage`, currently unauthenticated).
- `pages/ChatPage.tsx` — owns chat state (messages, session id/state) using the generated `useChatApiChatPost`/`useVerifyCodeApiAuthVerifyCodePost` mutation hooks directly (no streaming hook layer); opens `OtpVerificationModal` when a response has `verification_required: true`, and closes a session via a PATCH to `/api/sessions/{id}`.
- `components/Chat/` — `ChatPanel`, `ChatInput`, `MessageContent`, `OtpVerificationModal`, `ChatCloseModal`.
- `pages/AdminPage.tsx` + `components/Admin/` — sidebar-driven admin dashboard with three tabs (sessions/shipments/packages), each backed by its own `*Table.tsx` component built on the shared generic `DataTable` + `Pagination` components (client requests pages via the `limit`/`offset` query params the list endpoints expose).
- Styling is Tailwind v4 (via `@tailwindcss/vite`), React 19 with the React Compiler enabled through a `@rolldown/plugin-babel` Babel plugin in `vite.config.ts` (not the standard `babel-plugin-react-compiler` wiring — check that file before assuming compiler behavior).

### Diagrams

`docs/diagrams/*.md` are Mermaid docs covering system architecture, the data-model ERD, the identity-gating state machine, tool-calling sequence, human-escalation sequence, and local dev topology. As noted above, some of these (system architecture, in particular) describe a target design that's ahead of the current implementation — cross-check against the routers/services described here before relying on them for wire-protocol or auth-storage details. If asked to create/edit a diagram, follow `.github/instructions/mermaid.instructions.md` (write `.mmd` files, validate with the Mermaid VS Code extension tools, don't hand-edit diagrams managed by Mermaid Chart sync).

## Project conventions (from `.github/copilot-instructions.md`)

- Keep changes minimal in scope — only touch what's directly requested; don't refactor or add features beyond the ask, and don't introduce side effects on unrelated behavior.
- Extract logic into components/services when a change would touch more than one concern; never leave business logic in a page component.
- For any change touching more than 2 files, or introducing a new data flow, propose a concise plan and wait for approval before writing code.
