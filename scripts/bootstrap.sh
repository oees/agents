#!/usr/bin/env bash
set -euo pipefail
# Remote bootstrap: clones agents into a temp directory, runs init-repo.sh
# in the current directory, then cleans up. No permanent local clone needed.
# Usage: curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash

REPO_URL="https://github.com/oees/agents.git"
TARGET="$(pwd)"
TMPDIR="$(mktemp -d)"

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

echo "Fetching agents tooling..."
git clone --quiet --depth=1 "$REPO_URL" "$TMPDIR/agents"

bash "$TMPDIR/agents/scripts/init-repo.sh" "$TARGET"
