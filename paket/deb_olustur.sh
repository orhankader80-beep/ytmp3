#!/usr/bin/env bash
# YouTube MP3 .deb paketini oluşturur.  Kullanım: bash paket/deb_olustur.sh
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
VER="$(grep -oP '^VERSION = "\K[^"]+' "$SRC/ytmp3.py")"
PY="${PY:-python3}"
B="$(mktemp -d)/ytmp3_${VER}_all"

mkdir -p "$B/DEBIAN" "$B/opt/ytmp3" "$B/usr/bin" "$B/usr/share/applications" \
         "$B/usr/share/icons/hicolor/scalable/apps"
cp "$SRC/ytmp3.py" "$B/opt/ytmp3/"
"$PY" -m pip install -q --no-cache-dir --no-compile --target "$B/opt/ytmp3/lib" yt-dlp customtkinter qrcode
rm -rf "$B/opt/ytmp3/lib/bin" "$B/opt/ytmp3/lib/share"
find "$B" -name __pycache__ -prune -exec rm -rf {} +

cat > "$B/usr/bin/ytmp3" <<'S'
#!/bin/sh
exec python3 /opt/ytmp3/ytmp3.py "$@"
S
chmod 755 "$B/usr/bin/ytmp3"

cat > "$B/usr/share/applications/ytmp3.desktop" <<'S'
[Desktop Entry]
Name=YouTube MP3
Comment=YouTube videolarını MP3 olarak indir
Exec=ytmp3
Icon=ytmp3
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Network;
Keywords=youtube;mp3;müzik;indir;
S

cat > "$B/usr/share/icons/hicolor/scalable/apps/ytmp3.svg" <<'S'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="28" fill="#E5383B"/>
  <path d="M48 36v40.5A14 14 0 1 0 56 89V52l32-8v24.5A14 14 0 1 0 96 81V28z" fill="#fff"/>
</svg>
S

BOYUT=$(du -sk "$B" | cut -f1)
cat > "$B/DEBIAN/control" <<S
Package: ytmp3
Version: $VER
Section: sound
Priority: optional
Architecture: all
Depends: python3 (>= 3.11), python3-tk, ffmpeg
Installed-Size: $BOYUT
Maintainer: YouTube MP3 <noreply@localhost>
Description: YouTube videolarini MP3 olarak indirme programi
 Modern arayuzlu YouTube -> MP3 indirici. Playlist destegi, kalite secimi,
 kapak resmi, USB bellege kaydetme ve USB'ye tasinabilir kopya olusturma.
S

cat > "$B/DEBIAN/postinst" <<'S'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
exit 0
S
sed 's/^exit 0$/[ "$1" = remove ] || [ "$1" = purge ] \&\& rm -rf \/opt\/ytmp3\nexit 0/' "$B/DEBIAN/postinst" > "$B/DEBIAN/postrm"
chmod 755 "$B/DEBIAN/postinst" "$B/DEBIAN/postrm"

dpkg-deb --root-owner-group -Zxz --build "$B" "$SRC/ytmp3_${VER}_all.deb"
rm -rf "$(dirname "$B")"
echo "Hazır: $SRC/ytmp3_${VER}_all.deb"
