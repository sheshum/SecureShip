### Ruff linter

```zsh
# Check for issues
uv run ruff check .

# Auto-fix safe issues
uv run ruff check --fix .

# Show unsafe fixes available
uv run ruff check --unsafe-fixes .

# Apply unsafe fixes (use with caution)
uv run ruff check --fix --unsafe-fixes .

# Format code
uv run ruff format .

# Check formatting without modifying
uv run ruff format --check .

# Combined: fix linting + format
uv run ruff check --fix . && uv run ruff format .

# Check specific file
uv run ruff check app/main.py

# Show statistics
uv run ruff check . --statistics
```