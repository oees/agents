#!/usr/bin/env bash
set -euo pipefail
# Copies rules, skills, and commands into a target repo's .claude/ directory
# so the whole team gets the tooling once .claude/ is committed.
# Usage: bash scripts/init-repo.sh [target-dir]   (defaults to current directory)

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$(pwd)}"
TARGET="$(cd "$TARGET" && pwd)"

CLAUDE_DIR="$TARGET/.claude"
RULES_DIR="$CLAUDE_DIR/rules"
COMMANDS_DIR="$CLAUDE_DIR/commands"
SKILLS_DIR="$CLAUDE_DIR/skills"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
SETTINGS_JSON="$CLAUDE_DIR/settings.json"

echo "Initialising agents tooling in: $TARGET"
echo ""

mkdir -p "$RULES_DIR" "$COMMANDS_DIR" "$SKILLS_DIR"
touch "$CLAUDE_MD"

echo "Copying rules..."
for rule in "$REPO/rules"/*.md; do
  name=$(basename "$rule")
  cp "$rule" "$RULES_DIR/$name"
  echo "  ✓ $name"
done

echo ""
echo "Updating .claude/CLAUDE.md..."
for rule in "$REPO/rules"/*.md; do
  import="@rules/$(basename "$rule")"
  if grep -qF "$import" "$CLAUDE_MD" 2>/dev/null; then
    echo "  · $(basename "$rule") already present"
    continue
  fi
  echo "$import" >> "$CLAUDE_MD"
  echo "  ✓ $import"
done

echo ""
echo "Copying skills..."
for skill_dir in "$REPO/skills"/*/; do
  name=$(basename "$skill_dir")
  mkdir -p "$SKILLS_DIR/$name"
  for f in "$skill_dir"*.md; do
    [ -f "$f" ] || continue
    cp "$f" "$SKILLS_DIR/$name/$(basename "$f")"
  done
  echo "  ✓ $name"
done

echo ""
echo "Copying commands..."
for cmd in "$REPO/commands"/*.md; do
  name=$(basename "$cmd")
  # Rewrite @skills/ → @../skills/ so imports resolve from .claude/commands/
  sed 's|@skills/|@../skills/|g' "$cmd" > "$COMMANDS_DIR/$name"
  echo "  ✓ $name"
done

echo ""
if [ -f "$SETTINGS_JSON" ]; then
  echo "settings.json already exists — skipped."
  echo "Review $REPO/.claude/settings.json to merge permissions and hooks manually."
else
  cp "$REPO/.claude/settings.json" "$SETTINGS_JSON"
  echo "Copied settings.json ✓"
fi

echo ""
echo "Done. Commit .claude/ to share the tooling with your team."
