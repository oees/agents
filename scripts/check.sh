#!/usr/bin/env bash
set -euo pipefail
# Validates the agents tooling end to end:
#   1. init-repo.sh produces complete Claude, Cursor and Codex instructions
#   2. every @-import in the generated commands resolves to a real file
#   3. every @rule import in the generated .claude/CLAUDE.md resolves
#   4. Codex generation preserves local instructions and rejects unsafe updates
# Run locally before pushing, and in CI on every PR.

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

BEGIN_MARKER='<!-- BEGIN OEES SHARED RULES -->'
END_MARKER='<!-- END OEES SHARED RULES -->'

run_check() {
  local description="$1"
  shift
  if "$@"; then
    echo "  ✓ $description"
  else
    note_fail "$description"
  fi
}

check_codex_install() {
  local target="$TMP/repo with spaces" rule body actual
  mkdir -p "$target" || return 1
  (cd / && bash "$REPO/scripts/init-repo.sh" "$target" >/dev/null) || return 1
  if [ ! -f "$target/AGENTS.md" ]; then
    echo "    init-repo.sh did not create AGENTS.md"
    return 1
  fi
  actual="$(cat "$target/AGENTS.md")"
  [ "$(grep -Fxc "$BEGIN_MARKER" "$target/AGENTS.md")" -eq 1 ] || return 1
  [ "$(grep -Fxc "$END_MARKER" "$target/AGENTS.md")" -eq 1 ] || return 1
  for rule in "$REPO/rules"/*.md; do
    body="$(awk 'NR == 1 && $0 == "---" { frontmatter = 1; next }
      frontmatter && $0 == "---" { frontmatter = 0; next }
      !frontmatter { print }' "$rule")"
    if [[ "$actual" != *"$body"* ]]; then
      echo "    AGENTS.md is missing the full body of $(basename "$rule")"
      return 1
    fi
  done
  if grep -Eq '^(description:|@rules/)' "$target/AGENTS.md"; then
    echo "    AGENTS.md contains frontmatter or unresolved rule imports"
    return 1
  fi
  cp "$target/AGENTS.md" "$TMP/installed-before.md" || return 1
  (cd / && bash "$REPO/scripts/init-repo.sh" "$target" >/dev/null) || return 1
  cmp -s "$target/AGENTS.md" "$TMP/installed-before.md"
}

check_codex_updates() {
  local instructions="$CODEX_FIXTURE/AGENTS.md"
  printf '%s\n' 'Local instructions before the block.' "$BEGIN_MARKER" \
    'Outdated shared instructions.' "$END_MARKER" \
    'Local instructions after the block.' > "$instructions" || return 1
  (cd / && bash "$CODEX_GENERATOR") || return 1
  [ "$(head -n 1 "$instructions")" = 'Local instructions before the block.' ] || return 1
  [ "$(tail -n 1 "$instructions")" = 'Local instructions after the block.' ] || return 1
  grep -Fqx 'Use the original test policy.' "$instructions" || return 1
  if grep -Fq 'Outdated shared instructions.' "$instructions"; then return 1; fi
  cp "$instructions" "$TMP/first-generation.md" || return 1
  bash "$CODEX_GENERATOR" "$CODEX_FIXTURE" || return 1
  cmp -s "$instructions" "$TMP/first-generation.md" || return 1
  printf '%s\n' '---' 'description: Fixture rule' '---' '# Test policy' \
    'Use the updated test policy.' > "$CODEX_FIXTURE/rules/example.md" || return 1
  bash "$CODEX_GENERATOR" "$CODEX_FIXTURE" || return 1
  grep -Fqx 'Use the updated test policy.' "$instructions" || return 1
  if grep -Fq 'Use the original test policy.' "$instructions"; then return 1; fi
  [ "$(head -n 1 "$instructions")" = 'Local instructions before the block.' ] || return 1
  [ "$(tail -n 1 "$instructions")" = 'Local instructions after the block.' ] || return 1
}

check_codex_invalid_markers() {
  local target="$TMP/invalid markers" variant
  mkdir -p "$target" || return 1
  for variant in unclosed orphan duplicate reversed; do
    case "$variant" in
      unclosed) printf '%s\n' 'Local policy.' "$BEGIN_MARKER" 'Stale policy.' ;;
      orphan) printf '%s\n' 'Local policy.' "$END_MARKER" ;;
      duplicate) printf '%s\n' "$BEGIN_MARKER" "$END_MARKER" "$BEGIN_MARKER" "$END_MARKER" ;;
      reversed) printf '%s\n' "$END_MARKER" 'Local policy.' "$BEGIN_MARKER" ;;
    esac > "$target/AGENTS.md" || return 1
    cp "$target/AGENTS.md" "$TMP/invalid-before.md" || return 1
    if bash "$CODEX_GENERATOR" "$target" > "$TMP/generator.log" 2>&1; then
      echo "    Generator accepted $variant markers"
      return 1
    fi
    if ! cmp -s "$target/AGENTS.md" "$TMP/invalid-before.md"; then
      echo "    Generator modified a file with $variant markers"
      return 1
    fi
  done
}

check_codex_symlink() {
  local target="$TMP/symlink target" original="$TMP/linked instructions.md"
  mkdir -p "$target" || return 1
  printf '%s\n' 'Do not modify these local instructions.' > "$original" || return 1
  cp "$original" "$TMP/symlink-before.md" || return 1
  ln -s "$original" "$target/AGENTS.md" || return 1
  if bash "$CODEX_GENERATOR" "$target" > "$TMP/generator.log" 2>&1; then
    echo "    Generator accepted a symlink AGENTS.md"
    return 1
  fi
  [ -L "$target/AGENTS.md" ] || return 1
  [ "$(readlink "$target/AGENTS.md")" = "$original" ] || return 1
  cmp -s "$original" "$TMP/symlink-before.md"
}

check_codex_check_mode() {
  local target="$TMP/check mode"
  mkdir -p "$target" || return 1
  if bash "$CODEX_GENERATOR" --check "$target" > "$TMP/generator.log" 2>&1; then
    echo "    --check accepted missing instructions"
    return 1
  fi
  [ ! -e "$target/AGENTS.md" ] || return 1
  printf '%s\n' 'Local policy.' > "$target/AGENTS.md" || return 1
  cp "$target/AGENTS.md" "$TMP/stale-before.md" || return 1
  if bash "$CODEX_GENERATOR" --check "$target" > "$TMP/generator.log" 2>&1; then
    echo "    --check accepted instructions without shared rules"
    return 1
  fi
  cmp -s "$target/AGENTS.md" "$TMP/stale-before.md" || return 1
  bash "$CODEX_GENERATOR" "$target" || return 1
  grep -Fqx 'Local policy.' "$target/AGENTS.md" || return 1
  cp "$target/AGENTS.md" "$TMP/fresh-before.md" || return 1
  bash "$CODEX_GENERATOR" --check "$target" || return 1
  cmp -s "$target/AGENTS.md" "$TMP/fresh-before.md" || return 1
  printf '%s\n' 'An additional canonical rule.' >> "$CODEX_FIXTURE/rules/example.md" || return 1
  if bash "$CODEX_GENERATOR" --check "$target" > "$TMP/generator.log" 2>&1; then
    echo "    --check accepted stale shared rule content"
    return 1
  fi
  cmp -s "$target/AGENTS.md" "$TMP/fresh-before.md"
}

check_codex_crlf() {
  local source="$TMP/CRLF source" target="$TMP/CRLF target" result=0
  mkdir -p "$source/scripts" "$source/rules" "$target" || return 1
  cp "$REPO/scripts/sync-codex-rules.sh" "$source/scripts/" || return 1
  printf '%s\r\n' '---' 'description: CRLF fixture rule' '---' \
    '# CRLF policy' 'Use the current CRLF policy.' > "$source/rules/example.md" || return 1
  printf '%s\r\n' 'Local instructions before the block.' '' > "$TMP/crlf-prefix.md" || return 1
  printf '%s\r\n' '' 'Local instructions after the block.' > "$TMP/crlf-suffix.md" || return 1
  {
    cat "$TMP/crlf-prefix.md"
    printf '%s\r\n' "$BEGIN_MARKER" 'Outdated CRLF policy.' "$END_MARKER"
    cat "$TMP/crlf-suffix.md"
  } > "$target/AGENTS.md" || return 1
  bash "$source/scripts/sync-codex-rules.sh" "$target" || return 1
  head -n 2 "$target/AGENTS.md" > "$TMP/crlf-prefix-after.md" || return 1
  tail -n 2 "$target/AGENTS.md" > "$TMP/crlf-suffix-after.md" || return 1
  if ! cmp -s "$TMP/crlf-prefix.md" "$TMP/crlf-prefix-after.md" || \
    ! cmp -s "$TMP/crlf-suffix.md" "$TMP/crlf-suffix-after.md"; then
    echo "    CRLF local instructions were not preserved byte-for-byte"
    result=1
  fi
  tr -d '\r' < "$target/AGENTS.md" > "$TMP/crlf-normalized.md" || return 1
  if [ "$(grep -Fxc "$BEGIN_MARKER" "$TMP/crlf-normalized.md")" -ne 1 ] || \
    [ "$(grep -Fxc "$END_MARKER" "$TMP/crlf-normalized.md")" -ne 1 ]; then
    echo "    CRLF update did not leave exactly one shared-rule block"
    result=1
  fi
  if grep -Fq 'Outdated CRLF policy.' "$target/AGENTS.md"; then
    echo "    CRLF update retained stale managed instructions"
    result=1
  fi
  if grep -Eq '^(description:|---$)' "$TMP/crlf-normalized.md"; then
    echo "    CRLF rule frontmatter was embedded in AGENTS.md"
    result=1
  fi
  grep -Fqx 'Use the current CRLF policy.' "$TMP/crlf-normalized.md" || return 1
  cp "$target/AGENTS.md" "$TMP/crlf-first-generation.md" || return 1
  bash "$source/scripts/sync-codex-rules.sh" "$target" || return 1
  cmp -s "$target/AGENTS.md" "$TMP/crlf-first-generation.md" || return 1
  return "$result"
}

echo ""
echo "Checking Codex instruction distribution..."
run_check 'Install in a spaced target embeds every canonical rule body' check_codex_install
if [ -f "$REPO/scripts/sync-codex-rules.sh" ]; then
  run_check 'Repository Codex guidance matches canonical rules' \
    bash "$REPO/scripts/sync-codex-rules.sh" --check
  CODEX_FIXTURE="$TMP/codex source"
  mkdir -p "$CODEX_FIXTURE/scripts" "$CODEX_FIXTURE/rules"
  cp "$REPO/scripts/sync-codex-rules.sh" "$CODEX_FIXTURE/scripts/"
  CODEX_GENERATOR="$CODEX_FIXTURE/scripts/sync-codex-rules.sh"
  printf '%s\n' '---' 'description: Fixture rule' '---' '# Test policy' \
    'Use the original test policy.' > "$CODEX_FIXTURE/rules/example.md"
  run_check 'Updates preserve local instructions and are idempotent' check_codex_updates
  run_check 'Malformed or multiple marker blocks are rejected without changes' check_codex_invalid_markers
  run_check 'Symlink instructions are rejected without changing the link or target' check_codex_symlink
  run_check '--check detects missing and stale content without modifying files' check_codex_check_mode
  run_check 'CRLF updates preserve local bytes, replace the block and strip frontmatter' check_codex_crlf
else
  note_fail 'scripts/sync-codex-rules.sh is missing'
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "All checks passed."
else
  echo "Checks failed. See ✗ lines above."
fi
exit "$fail"
