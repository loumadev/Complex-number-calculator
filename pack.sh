#!/usr/bin/env bash
#
# Pack the project into xlouma.zip:
#   src/      <- all top-level source files (.py, .qss, ...)
#   resources/ <- resources/ as-is
#   docs/     <- docs/ as-is
#   tests/    <- tests/ as-is
# __pycache__ directories and .pyc files are omitted everywhere.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

ZIP="xlouma.zip"
rm -f "$ZIP"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/src" "$STAGE/resources" "$STAGE/docs" "$STAGE/tests"

# Sources: every top-level project file except the pack tool, the output zip,
# compiled artifacts and dotfiles (the glob already skips those)
for f in *; do
    [ -f "$f" ] || continue
    case "$f" in
        pack.sh|xlouma.zip|*.pyc) continue ;;
    esac
    cp -- "$f" "$STAGE/src/"
done

# Resources, docs and tests are copied as-is
cp -R resources/. "$STAGE/resources/"
cp -R docs/. "$STAGE/docs/"
cp -R tests/. "$STAGE/tests/"

# Omit any __pycache__ dirs and .pyc files that snuck in
find "$STAGE" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$STAGE" -type f -name '*.pyc' -delete

# Build the zip with the four directories at the top level
cd "$STAGE"
zip -r -q "$ROOT/$ZIP" src resources docs tests

echo "Created $ROOT/$ZIP"
