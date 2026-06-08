#!/usr/bin/env bash
set -euo pipefail
# Generates .cursor/rules/*.mdc from canonical sources in rules/ and
# skills/python-patterns/. Run after editing any rule or that skill.

mkdir -p .cursor/rules

strip_frontmatter() {
  awk 'NR==1 && /^---/ { in_fm=1; next } in_fm && /^---/ { in_fm=0; next } in_fm { next } { print }' "$1"
}

write_mdc() {
  local out="$1" description="$2" always_apply="$3" globs="$4"
  shift 4
  {
    echo "---"
    echo "description: $description"
    [ -n "$globs" ] && echo "globs: $globs"
    echo "alwaysApply: $always_apply"
    echo "---"
    echo ""
    cat "$@"
  } > "$out"
}

declare -A descriptions=(
  ["tdd"]="TDD: write failing tests before implementation, red-green-refactor"
  ["no-inline-imports"]="Keep imports at top of module, no inline imports"
  ["observability"]="Structured logging, contextual errors, no silent exceptions"
  ["code-quality"]="Lint, format, type checks, tests, and security scans before merge"
  ["standards"]="Frontend, backend, deployment, and API design conventions"
)

for md_file in rules/*.md; do
  name=$(basename "$md_file" .md)
  tmp=$(mktemp)
  strip_frontmatter "$md_file" > "$tmp"
  write_mdc ".cursor/rules/${name}.mdc" "${descriptions[$name]}" "true" "" "$tmp"
  rm "$tmp"
  echo "  rules/${name}.md → .cursor/rules/${name}.mdc"
done

tmp=$(mktemp)
strip_frontmatter "skills/python-patterns/python-patterns.md" > "$tmp"
write_mdc ".cursor/rules/python-patterns.mdc" \
  "Python patterns: framework selection, async, type hints, project structure" \
  "false" '["**/*.py"]' "$tmp"
rm "$tmp"
echo "  skills/python-patterns/python-patterns.md → .cursor/rules/python-patterns.mdc"

echo ""
echo "Done. $(ls .cursor/rules/*.mdc | wc -l | tr -d ' ') Cursor rules written."
