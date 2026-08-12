## Implementation style

- Keep changes minimal in scope. Only touch what is directly requested.
- Do not add features, refactor, or improve code beyond what was asked.
- Do not introduce side effects on unrelated behaviour when making a change.
- Use modular approach and separation of concerns when implementing changes.

## Plan before code

For any change that touches more than 2 files, or that introduces a new data flow, propose a concise implementation plan and wait for explicit approval before writing any code.

## Database schema changes

Any request that involves adding, removing, or modifying tables, columns, constraints, or indexes **must** follow the full procedure in `.github/instructions/alembic.instructions.md` — regardless of which file is edited first. Read that file before making any change.

## Project conventions

- Backend layering is strict: routers → services → repositories → llm. Do not skip layers.
- The LLM must never authorize data access. Authorization is enforced in `services/dispatch.py::dispatch_tool_call` via `AuthContext` only.
- `src/api/generated/` is Orval-generated — never hand-edit it. Change FastAPI routers/schemas and re-run `npm run api:sync`.
- There is no test suite yet. If adding tests, use pytest and run with `uv run pytest`.
- Tailwind v4 via `@tailwindcss/vite`. React 19 with React Compiler enabled via Babel in `vite.config.ts`.
- Admin panel (`/dashboard`) is Auth0-protected: backend endpoints require a valid JWT with the `admin:all` permission (`require_admin_auth` in `dependencies.py`); frontend wraps the route in `ProtectedRoute`. No RBAC beyond that one permission check is implemented yet.

<!-- mermaid-ai-skills:start -->
## Mermaid Diagrams

When the user asks to create, edit, or visualize a diagram, follow the
instructions in `.github/instructions/mermaid.instructions.md`.
<!-- mermaid-ai-skills:end -->
