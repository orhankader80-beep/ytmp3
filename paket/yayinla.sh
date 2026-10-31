#!/usr/bin/env bash
# Yeni sürüm yayınlar: ytmp3.py içindeki VERSION'ı artırın, sonra:
#   bash paket/yayinla.sh "Bu sürümde neler var"
set -e
cd "$(dirname "$0")/.."
VER="$(grep -oP '^VERSION = "\K[^"]+' ytmp3.py)"
DEPO="$(grep -oP '^DEPO = "\K[^"]+' ytmp3.py)"
bash paket/deb_olustur.sh
mkdir -p dagitim && rm -f dagitim/*.deb && mv "ytmp3_${VER}_all.deb" dagitim/
sed -i -E "s/ytmp3_[0-9.]+_all\.deb/ytmp3_${VER}_all.deb/g" README.md
python3 - "$VER" "$DEPO" "${1:-Yeni sürüm}" <<'P'
import json, sys
v, depo, notlar = sys.argv[1:]
raw = f"https://raw.githubusercontent.com/{depo}/main"
json.dump({"surum": v, "notlar": notlar, "deb": f"{raw}/dagitim/ytmp3_{v}_all.deb", "py": f"{raw}/ytmp3.py"},
          open("surum.json", "w"), ensure_ascii=False, indent=2)
P
git add -A && git commit -m "Sürüm $VER" && git push origin main
echo "Sürüm $VER yayınlandı."
