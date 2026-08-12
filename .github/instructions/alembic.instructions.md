---
applyTo: "**/models.py"
---
# Database schema change procedure

When `app/models.py` is edited, the full procedure below **must** be completed before the change is considered done. Do not stop after editing the model.

## Required steps (in order)

### 1. Generate the migration script
Run from `backend/`:
```bash
uv run alembic revision --autogenerate -m "<concise description of the schema change>"
```
The message must describe the schema change, not the file (e.g. `add_session_verification_table`, not `update_models`).

### 2. Review the generated migration file
Open the new file in `alembic/versions/` and verify:
- The `upgrade()` body matches the intended change exactly.
- The `downgrade()` body correctly reverses it.
- Alembic autogenerate **does not detect** the following — add them manually if needed:
  - `ondelete` / `onupdate` options on `ForeignKeyConstraint`
  - `CHECK` constraints
  - Custom `Enum` type changes (it may drop/recreate the type incorrectly)
  - Index changes on `UniqueConstraint` defined in `__table_args__`
- No unintended table drops or column removals are present.

### 3. Apply the migration
```bash
uv run alembic upgrade head
```
Confirm the output shows the new revision ID without errors.

### 4. Update Pydantic schemas if the API surface changed
If columns were added, removed, or renamed on a model that is exposed via a router, update the corresponding file in `app/schemas/`:

| Model | Schema file |
|---|---|
| `Customer` | `schemas/customers.py` |
| `Shipment` | `schemas/shipments.py` |
| `Package` | `schemas/packages.py` |
| `ChatSession` | `schemas/sessions.py` |
| `SessionVerification` | `schemas/verification.py` |

### 5. Update repositories if query logic is affected
If the change adds columns used in filtering/sorting, or removes columns referenced in queries, update the relevant file in `app/repositories/`.

### 6. Update the ERD diagram
Update `docs/diagrams/data-model-ERD.md` and `docs/diagrams/data-model-ERD.mmd` to reflect the new schema.
Validate with `mermaid-diagram-validator` and preview with `mermaid-diagram-preview` before committing.

### 7. Regenerate frontend API types (if OpenAPI surface changed)
If step 4 changed any schema exposed by a router, run from `frontend/`:
```bash
npm run api:sync
```
Verify the diff in `src/api/generated/` is correct. Never hand-edit that directory.

## Checklist before committing
- [ ] Migration file generated and reviewed
- [ ] `alembic upgrade head` succeeded
- [ ] Schemas updated (if needed)
- [ ] Repositories updated (if needed)
- [ ] ERD diagram updated
- [ ] `npm run api:sync` run (if API surface changed)
