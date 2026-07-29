## Implementation style

- Keep changes minimal in scope. Only touch what is directly requested.
- Do not add features, refactor, or improve code beyond what was asked.
- Do not introduce side effects on unrelated behaviour when making a change.
- Extract logic into components or services when the result would touch more than one concern; never leave business logic in a page component.

## Plan before code

For any change that touches more than 2 files, or that introduces a new data flow, propose a concise implementation plan and wait for explicit approval before writing any code.

## Project conventions

- Backend layering is strict: routers → services → repositories → llm. Do not skip layers.
- The LLM must never authorize data access. Authorization is enforced in `llm/tools.py::execute_tool_call` via `AuthContext` only.
- `src/api/generated/` is Orval-generated — never hand-edit it. Change FastAPI routers/schemas and re-run `npm run api:sync`.
- Tests are plain `unittest.TestCase`. Always run with `uv run python -m unittest`, not pytest.
- Tailwind v4 via `@tailwindcss/vite`. React 19 with React Compiler enabled via Babel in `vite.config.ts`.

<!-- mermaid-ai-skills:start -->
## Mermaid Diagrams

When the user asks to create, edit, or visualize a diagram, follow the
instructions in `.github/instructions/mermaid.instructions.md`.
<!-- mermaid-ai-skills:end -->
