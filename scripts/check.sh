#!/usr/bin/env bash
set -euo pipefail
# Validates the agents tooling end to end:
#   1. init-repo.sh produces a complete .claude/ + .cursor/ tree
#   2. every @-import in the generated commands resolves to a real file
#   3. every @rule import in the generated .claude/CLAUDE.md resolves
# Run locally before pushing, and in CI on every PR. Exits non-zero on the
# first broken import so a deleted/renamed skill can never reach main again.

REPO="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

note_fail() { echo "  ✗ $1"; fail=1; }

# resolve_import <importing-file> <@import>: succeeds if the target exists.
resolve_import() {
  local dir rel
  dir="$(dirname "$1")"
  rel="${2#@}"
  [ -f "$dir/$rel" ]
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Running init-repo.sh into a throwaway target..."
bash "$REPO/scripts/init-repo.sh" "$TMP" >/dev/null

CLAUDE_DIR="$TMP/.claude"

echo ""
echo "Checking required directories are present and non-empty..."
for d in rules commands skills loops; do
  if [ -d "$CLAUDE_DIR/$d" ] && [ -n "$(ls -A "$CLAUDE_DIR/$d")" ]; then
    echo "  ✓ .claude/$d"
  else
    note_fail ".claude/$d is missing or empty"
  fi
done

echo ""
echo "Checking command imports resolve..."
for cmd in "$CLAUDE_DIR/commands"/*.md; do
  [ -f "$cmd" ] || continue
  while IFS= read -r imp; do
    [ -n "$imp" ] || continue
    if resolve_import "$cmd" "$imp"; then
      echo "  ✓ $(basename "$cmd") → $imp"
    else
      note_fail "$(basename "$cmd") imports $imp — target not found"
    fi
  done < <(grep -oE '@[^[:space:]]+\.md' "$cmd" || true)
done

echo ""
echo "Checking rule imports in .claude/CLAUDE.md resolve..."
if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
  while IFS= read -r imp; do
    [ -n "$imp" ] || continue
    if resolve_import "$CLAUDE_DIR/CLAUDE.md" "$imp"; then
      echo "  ✓ $imp"
    else
      note_fail "CLAUDE.md imports $imp — target not found"
    fi
  done < <(grep -oE '@[^[:space:]]+\.md' "$CLAUDE_DIR/CLAUDE.md" || true)
else
  note_fail ".claude/CLAUDE.md was not generated"
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "All checks passed."
else
  echo "Checks failed. See ✗ lines above."
fi
exit "$fail"
