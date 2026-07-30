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
AGENTS_DIR="$TMP/.agents"

echo ""
echo "Checking required directories are present and non-empty..."
for d in rules commands skills; do
  if [ -d "$CLAUDE_DIR/$d" ] && [ -n "$(ls -A "$CLAUDE_DIR/$d")" ]; then
    echo "  ✓ .claude/$d"
  else
    note_fail ".claude/$d is missing or empty"
  fi
done
# Loops live in the vendor-neutral .agents/ namespace, not under .claude/.
if [ -d "$AGENTS_DIR/loops" ] && [ -n "$(ls -A "$AGENTS_DIR/loops")" ]; then
  echo "  ✓ .agents/loops"
else
  note_fail ".agents/loops is missing or empty"
fi

echo ""
echo "Checking loop templates are well-formed..."
for loop in "$AGENTS_DIR/loops"/*.md; do
  [ -f "$loop" ] || continue
  name="$(basename "$loop")"

  # loops/README.md is the operator manual that ships alongside the templates, not a
  # loop — it has no tier, no config block, and several H1-free sections.
  [ "$name" = "README.md" ] && { echo "  · $name (operator manual, not a loop)"; continue; }

  # Filename encodes the risk tier: tier-<n>-<kebab-case-purpose>.md
  if ! printf '%s' "$name" | grep -qE '^tier-[0-9]+-[a-z0-9-]+\.md$'; then
    note_fail "$name does not match tier-<n>-<kebab-name>.md"
    continue
  fi

  # A loop must contain its H1 exactly once. Catches the duplicated-paste class of
  # bug, where a truncated copy of the file is prepended to the real one. Lines inside
  # fenced code blocks are skipped — a `#` there is a shell comment, not a heading.
  h1_count="$(awk '/^```/ { fenced = !fenced; next } !fenced && /^# / { n++ } END { print n+0 }' "$loop")"
  if [ "$h1_count" -ne 1 ]; then
    note_fail "$name has $h1_count H1 headings — expected exactly 1 (duplicated content?)"
    continue
  fi

  # Every loop is configured by exactly one per-repo config block.
  cfg_count="$(grep -cF 'PER-REPO CONFIG' "$loop" || true)"
  if [ "$cfg_count" -ne 1 ]; then
    note_fail "$name has $cfg_count 'PER-REPO CONFIG' blocks — expected exactly 1"
    continue
  fi

  echo "  ✓ $name"

  # Advisory only: an unsupervised loop should say how to stop it. Warned, not failed,
  # so the existing tier-0/1/2 templates do not block CI until they catch up.
  if ! grep -qF '## Stopping the loop' "$loop"; then
    echo "  ⚠ $name: no '## Stopping the loop' section — on-call has no documented kill switch"
  fi
done

echo ""
echo "Checking tier-3 orchestration contracts..."
tier3_loop="$AGENTS_DIR/loops/tier-3-queue-driven-delivery.md"
if [ -f "$tier3_loop" ]; then
  step_zero="$(
    awk '
      /^## Step 0/ { capture = 1 }
      /^## Role: CODER/ { capture = 0 }
      capture { print }
    ' "$tier3_loop"
  )"

  if printf '%s\n' "$step_zero" | grep -qF \
    'If no open PR carries your stage label, exit'; then
    note_fail "tier-3 Step 0 applies a checker-only cheap exit to every role"
  else
    echo "  ✓ tier-3 cheap exits are role-specific"
  fi

  if grep -qF \
    'plus approved checkpoint PRs parked at' \
    "$tier3_loop"; then
    echo "  ✓ tier-3 merger can resume approved checkpoints"
  else
    note_fail "tier-3 merger cannot select approved stage:human checkpoints"
  fi

  if grep -qF \
    'even when no PR is ready to merge.' \
    "$tier3_loop"; then
    echo "  ✓ tier-3 watchdog runs without a merge candidate"
  else
    note_fail "tier-3 watchdog exits when no PR is ready to merge"
  fi
else
  note_fail "tier-3 loop is missing"
fi

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
