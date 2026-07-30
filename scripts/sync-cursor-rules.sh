#!/usr/bin/env bash
set -euo pipefail
# Generates Cursor artifacts from canonical sources: .cursor/rules/*.mdc from rules/ and
# skills/, and .cursor/commands/*.md from commands/ (with skill bodies inlined).
# Run after editing any rule, skill, or command.

mkdir -p .cursor/rules

strip_frontmatter() {
  awk 'NR==1 && /^---/ { in_fm=1; next } in_fm && /^---/ { in_fm=0; next } in_fm { next } { print }' "$1"
}

get_description() {
  awk 'NR==1 && /^---/ { in_fm=1; next } in_fm && /^---/ { exit } in_fm && /^description:/ { sub(/^description: */, ""); print; exit }' "$1"
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

for md_file in rules/*.md; do
  name=$(basename "$md_file" .md)
  description=$(get_description "$md_file")
  [ -z "$description" ] && description="${name} standards"
  tmp=$(mktemp)
  strip_frontmatter "$md_file" > "$tmp"
  write_mdc ".cursor/rules/${name}.mdc" "$description" "true" "" "$tmp"
  rm "$tmp"
  echo "  rules/${name}.md → .cursor/rules/${name}.mdc"
done

# Skills become Cursor rules too, matching how Claude surfaces each one:
#   *-patterns      → Auto Attached (glob-scoped) — passive guidance while
#                     editing that language. Add a language by giving it a glob
#                     mapping in the case below.
#   everything else → Agent Requested (description only, no globs) — Cursor's
#                     agent pulls it in when relevant, like Claude auto-invoking
#                     a skill by its description.
for skill_dir in skills/*/; do
  name=$(basename "$skill_dir")           # e.g. commit, python-patterns
  skill_file="$skill_dir$name.md"
  [ -f "$skill_file" ] || { echo "  ⚠ $name: no $name.md — skipping"; continue; }
  description=$(get_description "$skill_file")

  case "$name" in
    *-patterns)
      lang=${name%-patterns}
      case "$lang" in
        python)     globs='["**/*.py"]' ;;
        typescript) globs='["**/*.ts", "**/*.tsx"]' ;;
        *)
          echo "  ⚠ $name: no glob mapping in sync-cursor-rules.sh — skipping"
          continue ;;
      esac
      [ -z "$description" ] && description="${lang} patterns"
      ;;
    *)
      # Agent Requested rules are selected purely by their description.
      if [ -z "$description" ]; then
        echo "  ⚠ $name: no description frontmatter — skipping (needed for Agent Requested rule)"
        continue
      fi
      globs=""
      ;;
  esac

  tmp=$(mktemp)
  strip_frontmatter "$skill_file" > "$tmp"
  write_mdc ".cursor/rules/${name}.mdc" "$description" "false" "$globs" "$tmp"
  rm "$tmp"
  echo "  ${skill_file} → .cursor/rules/${name}.mdc"
done

# Cursor slash commands (.cursor/commands/*.md). Cursor supports neither frontmatter nor
# @imports here, so each command is emitted with its skill body resolved inline — the
# opposite of the Claude command files, which are deliberately thin pointers.
mkdir -p .cursor/commands

for cmd_file in commands/*.md; do
  [ -f "$cmd_file" ] || continue
  name=$(basename "$cmd_file" .md)

  import=$(grep -oE '@[^[:space:]]+\.md' "$cmd_file" | head -1 || true)
  if [ -z "$import" ]; then
    echo "  ⚠ $name: no @import to resolve — skipping"
    continue
  fi

  # The import is written relative to the command file (@../skills/<n>/<n>.md).
  skill_file="commands/${import#@}"
  if [ ! -f "$skill_file" ]; then
    echo "  ⚠ $name: $import does not resolve — skipping"
    continue
  fi

  strip_frontmatter "$skill_file" > ".cursor/commands/${name}.md"
  echo "  ${cmd_file} + ${skill_file} → .cursor/commands/${name}.md"
done

echo ""
rule_count="$(find .cursor/rules -maxdepth 1 -type f -name '*.mdc' | wc -l | tr -d ' ')"
command_count="$(find .cursor/commands -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
echo "Done. $rule_count Cursor rules, $command_count Cursor commands written."
