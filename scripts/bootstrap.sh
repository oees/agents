#!/usr/bin/env bash
set -euo pipefail
# Install OEES agent tooling: installs uv if missing, then runs `oees-agents init` at the latest tag.
# Usage: curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash -s -- [init flags]
REPO="https://github.com/oees/agents"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
REF="${OEES_AGENTS_REF:-$(git ls-remote --tags --refs "$REPO" 'v*' | sed 's#.*refs/tags/##' | sort -V | tail -n 1)}"
[ -n "$REF" ] || { echo "No release tag found in $REPO; set OEES_AGENTS_REF (for example main)." >&2; exit 1; }
exec uvx --from "git+$REPO@$REF" oees-agents init "$@"
