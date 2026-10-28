#!/usr/bin/env bash
set -euo pipefail
# Embed canonical rules in AGENTS.md without replacing project instructions.
# Usage: bash scripts/sync-codex-rules.sh [--check] [target-dir]

export LC_ALL=C
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CHECK=0
if [ "${1:-}" = '--check' ]; then
  CHECK=1
  shift
fi
if [ "$#" -gt 1 ] || [[ "${1:-}" = -* ]]; then
  echo 'Usage: sync-codex-rules.sh [--check] [target-dir]' >&2
  exit 1
fi
TARGET="$(cd "${1:-$REPO}" && pwd)"
AGENTS_MD="$TARGET/AGENTS.md"
BEGIN_MARKER='<!-- BEGIN OEES SHARED RULES -->'
END_MARKER='<!-- END OEES SHARED RULES -->'

if [ -L "$AGENTS_MD" ] || { [ -e "$AGENTS_MD" ] && [ ! -f "$AGENTS_MD" ]; }; then
  echo "Refusing to replace a symlink or non-file: $AGENTS_MD" >&2
  exit 1
fi

FIRST=0
LAST=0
if [ -f "$AGENTS_MD" ]; then
  if ! MARKERS="$(awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
    { line = $0; sub(/\r$/, "", line) }
    line == begin { starts++; first = NR }
    line == end { ends++; last = NR }
    END {
      if (starts == 0 && ends == 0) { print "0 0"; exit }
      if (starts != 1 || ends != 1 || first >= last) { exit 1 }
      print first, last
    }' "$AGENTS_MD")"; then
    echo "Malformed or multiple shared-rule markers in $AGENTS_MD; leaving it unchanged." >&2
    exit 1
  fi
  read -r FIRST LAST <<< "$MARKERS"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BLOCK="$TMP/block.md"
OUTPUT="$TMP/AGENTS.md"

{
  printf '%s\n\n' "$BEGIN_MARKER"
  cat <<'EOF'
## Shared engineering rules

Generated from `rules/*.md` in the OEES agents repository. Edit the
canonical rules and regenerate; keep project instructions outside this block.
Apply these rules to every task, including delegated work. Project-specific
instructions specialize the defaults. Report unresolved instruction conflicts.
EOF
  for rule in "$REPO/rules"/*.md; do
    printf '\n<!-- Source: rules/%s -->\n' "$(basename "$rule")"
    awk '{ sub(/\r$/, "") }
      NR == 1 && $0 == "---" { frontmatter = 1; next }
      frontmatter && $0 == "---" { frontmatter = 0; next }
      !frontmatter { print }' "$rule"
  done
  printf '\n%s\n' "$END_MARKER"
} > "$BLOCK"

if [ "$FIRST" -gt 0 ]; then
  head -n "$((FIRST - 1))" "$AGENTS_MD" > "$OUTPUT"
  cat "$BLOCK" >> "$OUTPUT"
  tail -n "+$((LAST + 1))" "$AGENTS_MD" >> "$OUTPUT"
else
  if [ -s "$AGENTS_MD" ]; then
    cat "$AGENTS_MD" > "$OUTPUT"
    printf '\n\n' >> "$OUTPUT"
  fi
  cat "$BLOCK" >> "$OUTPUT"
fi

if [ -s "$TARGET/AGENTS.override.md" ]; then
  echo "Warning: $TARGET/AGENTS.override.md takes precedence; reconcile it with the shared rules before using Codex." >&2
fi
if [ "$(wc -c < "$OUTPUT")" -gt 32768 ]; then
  echo "Warning: $AGENTS_MD exceeds Codex's default combined 32 KiB instruction limit; some guidance may not load." >&2
fi

if [ -f "$AGENTS_MD" ] && cmp -s "$OUTPUT" "$AGENTS_MD"; then
  echo "AGENTS.md shared rules are current: $TARGET"
elif [ "$CHECK" -eq 1 ]; then
  echo "AGENTS.md shared rules are missing or stale: $TARGET" >&2
  exit 1
else
  cat "$OUTPUT" > "$AGENTS_MD"
  echo "Updated AGENTS.md shared rules: $TARGET"
fi
