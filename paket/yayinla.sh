#!/usr/bin/env bash
# Yeni sürüm yayınlar.
# 1) ytmp3.py içinde VERSION ve YENILIKLER'i güncelleyin
# 2) bash paket/yayinla.sh
# GitHub, Linux (.deb) ve Windows (.exe) dosyalarını kendisi derleyip yayınlar (~10 dk).
set -e
cd "$(dirname "$0")/.."
VER="$(grep -oP '^VERSION = "\K[^"]+' ytmp3.py)"
DEPO="$(grep -oP '^DEPO = "\K[^"]+' ytmp3.py)"
git add -A
git commit -m "Sürüm $VER" || true
git tag "v$VER"
git pull --rebase origin main
git push origin main "v$VER"
echo "Derleniyor: https://github.com/$DEPO/actions"
