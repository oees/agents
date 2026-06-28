#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
COMMANDS_DIR="$HOME/.claude/commands"
SKILLS_DIR="$HOME/.claude/skills"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

echo "Removing commands..."
for cmd in "$REPO/commands"/*.md; do
  name=$(basename "$cmd")
  target="$COMMANDS_DIR/$name"
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$cmd" ]; then
    rm "$target"
    echo "  ✓ $name"
  fi
done

echo ""
echo "Removing skills..."
for skill_dir in "$REPO/skills"/*/; do
  name=$(basename "$skill_dir")
  target="$SKILLS_DIR/$name"
  if [ -L "$target" ] && [ "$(readlink "$target")" = "${skill_dir%/}" ]; then
    rm "$target"
    echo "  ✓ $name"
  fi
done

echo ""
echo "Removing rules..."
if [ -f "$CLAUDE_MD" ]; then
  for rule in "$REPO/rules"/*.md; do
    import="@$rule"
    if grep -qF "$import" "$CLAUDE_MD" 2>/dev/null; then
      grep -vF "$import" "$CLAUDE_MD" > "$CLAUDE_MD.tmp" && mv "$CLAUDE_MD.tmp" "$CLAUDE_MD"
      echo "  ✓ $(basename $rule)"
    fi
  done
fi

echo ""
echo "Done. Uninstalled."
