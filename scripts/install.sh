#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
COMMANDS_DIR="$HOME/.claude/commands"
SKILLS_DIR="$HOME/.claude/skills"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

mkdir -p "$COMMANDS_DIR" "$SKILLS_DIR"
touch "$CLAUDE_MD"

echo "Installing commands..."
for cmd in "$REPO/commands"/*.md; do
  name=$(basename "$cmd")
  target="$COMMANDS_DIR/$name"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "  ⚠ skipped $name — a non-symlink file already exists at $target"
    continue
  fi
  ln -sf "$cmd" "$target"
  echo "  ✓ $name"
done

echo ""
echo "Installing skills..."
# Commands import @../skills/<name>/... which resolves from ~/.claude/commands/
# to ~/.claude/skills/, so the skills must live there too.
for skill_dir in "$REPO/skills"/*/; do
  name=$(basename "$skill_dir")
  target="$SKILLS_DIR/$name"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "  ⚠ skipped $name — a non-symlink file already exists at $target"
    continue
  fi
  ln -sfn "${skill_dir%/}" "$target"
  echo "  ✓ $name"
done

echo ""
echo "Installing rules..."
for rule in "$REPO/rules"/*.md; do
  import="@$rule"
  if grep -qF "$import" "$CLAUDE_MD" 2>/dev/null; then
    echo "  · $(basename $rule) already present"
    continue
  fi
  echo "$import" >> "$CLAUDE_MD"
  echo "  ✓ $(basename $rule)"
done

echo ""
echo "Done. Commands, skills, and rules are now active globally in Claude Code."
echo "Review $REPO/.claude/settings.json to adopt shared permissions and hooks."
