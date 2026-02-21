#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/build-arch-package.sh [--pkgver VERSION] [--pkgrel REL]

Builds an Arch Linux package for autheos_message.py and copies artifacts to ./dist.
EOF
}

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP_FILE="$ROOT_DIR/autheos_message.py"

if [[ ! -f "$APP_FILE" ]]; then
  echo "Error: expected $APP_FILE" >&2
  exit 1
fi

if ! command -v makepkg >/dev/null 2>&1; then
  echo "Error: makepkg is not installed (install pacman base-devel)." >&2
  exit 1
fi

pkgver=""
pkgrel="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pkgver)
      pkgver="${2:-}"
      shift 2
      ;;
    --pkgrel)
      pkgrel="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$pkgver" ]]; then
  if git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    rev_count="$(git -C "$ROOT_DIR" rev-list --count HEAD 2>/dev/null || echo 0)"
    short_sha="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo local)"
    pkgver="0.1.0.r${rev_count}.g${short_sha}"
  else
    pkgver="0.1.0.local"
  fi
fi

if [[ ! "$pkgver" =~ ^[A-Za-z0-9._+]+$ ]]; then
  echo "Error: --pkgver may only contain letters, numbers, dots, underscores, and plus signs." >&2
  exit 1
fi

if [[ ! "$pkgrel" =~ ^[0-9]+$ ]]; then
  echo "Error: --pkgrel must be a positive integer." >&2
  exit 1
fi

build_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$build_dir"
}
trap cleanup EXIT

cp "$APP_FILE" "$build_dir/autheos_message.py"

cat >"$build_dir/PKGBUILD" <<EOF
pkgname=autheos-message
pkgver=${pkgver}
pkgrel=${pkgrel}
pkgdesc='Simple Hyprland message overlay with typewriter animation'
arch=('any')
url='https://github.com/autheos/autheos_message'
license=('custom')
depends=('python' 'python-gobject' 'gtk4' 'gtk4-layer-shell')
source=('autheos_message.py')
sha256sums=('SKIP')

package() {
  install -Dm755 "\$srcdir/autheos_message.py" "\$pkgdir/usr/bin/autheos_message"
}
EOF

(
  cd "$build_dir"
  makepkg -f --clean
)

mkdir -p "$ROOT_DIR/dist"
shopt -s nullglob
for artifact in "$build_dir"/autheos-message-"$pkgver"-"$pkgrel"-*.pkg.tar*; do
  cp "$artifact" "$ROOT_DIR/dist/"
done
cp "$build_dir/PKGBUILD" "$ROOT_DIR/dist/PKGBUILD.autheos-message"

echo "Built package artifacts:"
ls -1 "$ROOT_DIR"/dist/autheos-message-"$pkgver"-"$pkgrel"-*.pkg.tar* "$ROOT_DIR/dist/PKGBUILD.autheos-message"
