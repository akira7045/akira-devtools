#!/bin/sh
# Install the AKIRA dev tools as commands on your PATH.
# Nothing is copied into site-packages; we just symlink the single-file scripts.
# Usage:  ./install.sh              -> installs to ~/.local/bin
#         PREFIX=/usr/local ./install.sh  -> installs to /usr/local/bin (may need sudo)
set -eu

SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX="${PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin"

mkdir -p "$BIN"

for tool in apidiff secretscan jsonl2csv dupfind envcheck; do
  target="$SRC_DIR/$tool/$tool.py"
  if [ ! -f "$target" ]; then
    echo "missing: $target" >&2
    exit 1
  fi
  chmod +x "$target" 2>/dev/null || true
  ln -sf "$target" "$BIN/$tool"
  echo "linked $BIN/$tool -> $target"
done

echo
case ":$PATH:" in
  *":$BIN:"*) echo "OK. $BIN is on your PATH." ;;
  *) echo "NOTE: add $BIN to your PATH, e.g.:  export PATH=\"$BIN:\$PATH\"" ;;
esac
