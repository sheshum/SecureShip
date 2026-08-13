# Frontend

React 19 + Vite + Tailwind v4. All commands run from the `frontend/` directory.

## Setup

```bash
npm install
```

## Development server

```bash
npm run dev             # http://localhost:5173 (proxies /api → http://localhost:8000)
```

## Build & preview

```bash
npm run build           # tsc -b && vite build
npm run preview         # preview the production build locally
```

## Linting

```bash
npm run lint            # oxlint (fast, no type-checking)
npm run lint:fix        # oxlint --fix
npm run lint:ci         # oxlint with type-aware checking (requires backend types generated)
```

## API client sync

`src/api/generated/` is Orval-generated from the backend's OpenAPI schema — **never hand-edit it**.

```bash
npm run api:sync        # pull /openapi.json from backend + regenerate hooks and types
```

The backend must be running at `http://localhost:8000` when you run this.

## Configuration

Create `frontend/.env.local` to override defaults:

```env
# Override backend proxy target (defaults to http://localhost:8000)
VITE_API_PROXY_TARGET=http://localhost:8000

# Auth0 — required for the /dashboard admin panel
VITE_AUTH0_DOMAIN=
VITE_AUTH0_CLIENT_ID=
VITE_AUTH0_AUDIENCE=
```

## Notes

- **React Compiler** is enabled via `babel-plugin-react-compiler` wired through `@rolldown/plugin-babel` in `vite.config.ts` — check that file before assuming standard compiler behavior.
- **Tailwind v4** is used via `@tailwindcss/vite` (not the PostCSS plugin).
- **Orval** generates react-query v5 hooks; the generated client lives in `src/api/generated/`.
