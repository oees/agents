#!/usr/bin/env bash
set -euo pipefail
# Copies rules, skills, commands, and loops into a target repo's .claude/ and
# .cursor/rules/ directories so the whole team gets the tooling once committed.
# Usage: bash scripts/init-repo.sh [target-dir]   (defaults to current directory)

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$(pwd)}"
TARGET="$(cd "$TARGET" && pwd)"

CLAUDE_DIR="$TARGET/.claude"
# Rules are no longer copied to .claude/rules/. AGENTS.md is the single in-repo home for
# the rule text and Claude Code reaches it via an @import from .claude/CLAUDE.md.
LEGACY_RULES_DIR="$CLAUDE_DIR/rules"
COMMANDS_DIR="$CLAUDE_DIR/commands"
SKILLS_DIR="$CLAUDE_DIR/skills"
# Loops are tool-agnostic markdown that a scheduler points at by path, so they live in
# the neutral .agents/ namespace rather than under any one vendor's directory.
LOOPS_DIR="$TARGET/.agents/loops"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
SETTINGS_JSON="$CLAUDE_DIR/settings.json"
CURSOR_RULES_DIR="$TARGET/.cursor/rules"
CURSOR_COMMANDS_DIR="$TARGET/.cursor/commands"
# Codex discovers skills from $REPO_ROOT/.agents/skills/<name>/SKILL.md.
CODEX_SKILLS_DIR="$TARGET/.agents/skills"
AGENTS_MD="$TARGET/AGENTS.md"

echo "Initialising agents tooling in: $TARGET"
echo ""

mkdir -p "$COMMANDS_DIR" "$SKILLS_DIR" "$LOOPS_DIR" \
         "$CURSOR_RULES_DIR" "$CURSOR_COMMANDS_DIR" "$CODEX_SKILLS_DIR"
touch "$CLAUDE_MD"

echo "Updating .claude/CLAUDE.md..."
# One import instead of one per rule: the rule text lives in AGENTS.md, which every other
# assistant reads natively. From .claude/CLAUDE.md, ../AGENTS.md is the repo root.
AGENTS_IMPORT="@../AGENTS.md"

# Migration: strip the old per-rule imports, or a repo that re-bootstraps would load every
# rule twice — once from .claude/rules/ and once from AGENTS.md.
if grep -qE '^@rules/.*\.md$' "$CLAUDE_MD" 2>/dev/null; then
  tmp_cm="$(mktemp)"
  awk '!/^@rules\/.*\.md$/' "$CLAUDE_MD" > "$tmp_cm"
  mv "$tmp_cm" "$CLAUDE_MD"
  echo "  ✓ removed superseded @rules/*.md imports"
fi

if grep -qF "$AGENTS_IMPORT" "$CLAUDE_MD" 2>/dev/null; then
  echo "  · $AGENTS_IMPORT already present"
else
  echo "$AGENTS_IMPORT" >> "$CLAUDE_MD"
  echo "  ✓ $AGENTS_IMPORT"
fi

if [ -d "$LEGACY_RULES_DIR" ]; then
  echo "  ⚠ $LEGACY_RULES_DIR is now unused — safe to delete and commit"
fi

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
echo "Copying Codex skills..."
# Same content, Codex's layout: .agents/skills/<name>/SKILL.md. The name/description
# frontmatter our skills already carry is exactly what Codex requires, so this is a
# copy plus a rename — no transformation.
for skill_dir in "$REPO/skills"/*/; do
  name=$(basename "$skill_dir")
  src="$skill_dir$name.md"
  [ -f "$src" ] || { echo "  ⚠ $name: no $name.md — skipping"; continue; }
  mkdir -p "$CODEX_SKILLS_DIR/$name"
  cp "$src" "$CODEX_SKILLS_DIR/$name/SKILL.md"
  echo "  ✓ $name/SKILL.md"
done

echo ""
echo "Copying commands..."
for cmd in "$REPO/commands"/*.md; do
  name=$(basename "$cmd")
  # Commands import skills as @../skills/... which resolves from .claude/commands/
  # straight to .claude/skills/ — same string works for the global install too.
  cp "$cmd" "$COMMANDS_DIR/$name"
  echo "  ✓ $name"
done

echo ""
echo "Copying loops..."
for loop in "$REPO/loops"/*.md; do
  [ -f "$loop" ] || continue
  name=$(basename "$loop")
  cp "$loop" "$LOOPS_DIR/$name"
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
echo "Copying Cursor rules..."
for rule in "$REPO/.cursor/rules"/*.mdc; do
  name=$(basename "$rule")
  cp "$rule" "$CURSOR_RULES_DIR/$name"
  echo "  ✓ $name"
done

echo ""
echo "Copying Cursor commands..."
for cmd in "$REPO/.cursor/commands"/*.md; do
  [ -f "$cmd" ] || continue
  name=$(basename "$cmd")
  cp "$cmd" "$CURSOR_COMMANDS_DIR/$name"
  echo "  ✓ $name"
done

echo ""
echo "Writing AGENTS.md (Codex, Cursor, Copilot, Aider, …)..."
# Splices a marker-delimited block. An existing hand-written AGENTS.md is preserved.
bash "$REPO/scripts/sync-agents-md.sh" "$AGENTS_MD"

echo ""
echo "Done. Commit AGENTS.md, .claude/, .cursor/ and .agents/ to share the tooling."
