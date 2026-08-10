#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

if [[ ! -d .githooks ]]; then
  echo "setup-hooks: .githooks directory not found"
  exit 1
fi

if [[ ! -f .githooks/pre-commit || ! -f .githooks/pre-push ]]; then
  echo "setup-hooks: expected hook files are missing"
  exit 1
fi

chmod +x .githooks/pre-commit .githooks/pre-push

git config core.hooksPath .githooks

echo "setup-hooks: configured core.hooksPath -> .githooks"
echo "setup-hooks: pre-commit and pre-push are executable"
