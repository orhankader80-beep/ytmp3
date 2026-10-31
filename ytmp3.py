#!/usr/bin/env python3
"""YouTube -> MP3 indirici (Linux / Windows, USB ve telefon desteği)."""
import json
import subprocess
from datetime import datetime
import os
import shutil
import sys
import threading
import webbrowser
from pathlib import Path

WINDOWS = sys.platform == "win32"
DONDURULMUS = getattr(sys, "frozen", False)  # Windows .exe (PyInstaller) içinde mi?
APP_DIR = Path(sys.executable).resolve().parent if DONDURULMUS else Path(__file__).resolve().parent
LIB_DIR = APP_DIR / "lib"
PORTABLE = (APP_DIR / "PORTABLE").exists()

if WINDOWS:
    _yerel = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "ytmp3"
    _ayar_dizini = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "ytmp3"
else:
    _yerel = Path.home() / ".local" / "share" / "ytmp3"
    _ayar_dizini = Path.home() / ".config" / "ytmp3"
# Uygulama içinden indirilen yeni yt-dlp sürümü (yazılabilir yerde durur)
GUNCEL_DIR = APP_DIR if PORTABLE else _yerel
ONBELLEK = (APP_DIR / "onbellek") if PORTABLE else (
    _yerel / "onbellek" if WINDOWS else Path.home() / ".cache" / "ytmp3")
CONFIG_FILE = (APP_DIR / "ayarlar.json") if PORTABLE else _ayar_dizini / "ayarlar.json"
YTDLP_ZIP = GUNCEL_DIR / "yt-dlp.zip"
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
# Uygulamanın yeni sürümleri burada yayınlanır
DEPO = "orhankader80-beep/ytmp3"
SURUM_URL = f"https://raw.githubusercontent.com/{DEPO}/main/surum.json"
SURUMLER_SAYFASI = f"https://github.com/{DEPO}/releases/latest"

if LIB_DIR.is_dir():
    sys.path.insert(0, str(LIB_DIR))
if YTDLP_ZIP.is_file():
    if DONDURULMUS:
        # .exe içindeki eski yt-dlp yerine indirilen yenisini kullan
        import zipimport

        class _YtdlpZipBulucu:
            def find_spec(self, ad, yol=None, hedef=None):
                if ad != "yt_dlp" and not ad.startswith("yt_dlp."):
                    return None
                parcalar = ad.split(".")
                try:
                    return zipimport.zipimporter(os.path.join(str(YTDLP_ZIP), *parcalar[:-1])).find_spec(ad)
                except Exception:
                    return None
        sys.meta_path.insert(0, _YtdlpZipBulucu())
    else:
        sys.path.insert(0, str(YTDLP_ZIP))

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    import yt_dlp
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import sanitize_filename
except ImportError as e:
    print(f"Eksik kütüphane: {e}\nProgramı yeniden kurun.")
    sys.exit(1)

VERSION = "3.4"
YENILIKLER = [
    "Windows desteği: artık .exe kurulum dosyası var",
    "📱 Telefondan kullan: QR kodu okut, iPhone veya Android'den indir",
]

BASLAT_SH = r'''#!/usr/bin/env bash
# USB'den YouTube MP3'ü başlatır.  Kullanım:  bash BASLAT.sh
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
eksik=""
python3 -c "import tkinter" 2>/dev/null || eksik="$eksik python3-tk"
command -v ffmpeg >/dev/null || eksik="$eksik ffmpeg"
if [ -n "$eksik" ]; then
  echo "Bu bilgisayarda eksik paketler var:$eksik"
  read -rp "Şimdi kurulsun mu? (e/h): " c; [[ "$c" =~ ^[eE] ]] && sudo apt install -y $eksik
fi
exec python3 "$DIR/ytmp3.py"
'''


def diske_yaz():
    if hasattr(os, "sync"):
        os.sync()


def dosya_ac(yol):
    """Klasörü / dosyayı sistemin dosya yöneticisinde açar."""
    yol = str(yol)
    if WINDOWS:
        os.startfile(yol)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", yol])
    elif shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", yol])
    else:
        webbrowser.open(Path(yol).as_uri())


def indir_dosyaya(url, hedef, zaman=120):
    import urllib.request
    gecici = Path(str(hedef) + ".part")
    with urllib.request.urlopen(url, timeout=zaman) as r, open(gecici, "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(gecici, hedef)
    return hedef


def surum_tuple(v):
    return tuple(int(x) for x in str(v).split(".") if x.isdigit())


def uygulama_surumu_kontrol():
    """Yeni uygulama sürümü varsa bilgisini (dict) döndürür, yoksa None."""
    import urllib.request
    istek = urllib.request.Request(SURUM_URL, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(istek, timeout=15) as r:
        bilgi = json.loads(r.read().decode("utf-8"))
    if WINDOWS and not bilgi.get("exe_kurulum"):
        return None  # Bu sürümün Windows dosyası henüz yok
    return bilgi if surum_tuple(bilgi["surum"]) > surum_tuple(VERSION) else None


def uygulamayi_guncelle(bilgi):
    """Yeni sürümü indirip kurar.
    "tamam": kuruldu, yeniden başlat · "cik": kurulum başladı, program kapanmalı · "sayfa": sayfa açıldı"""
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    if WINDOWS:
        if PORTABLE or not DONDURULMUS:
            webbrowser.open(SURUMLER_SAYFASI)
            return "sayfa"
        kurulum = indir_dosyaya(bilgi["exe_kurulum"], ONBELLEK / f"YouTubeMP3-Kurulum-{bilgi['surum']}.exe")
        # Sessiz kurulum; bitince program kendiliğinden yeniden açılır
        subprocess.Popen([str(kurulum), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
        return "cik"
    if PORTABLE:
        # USB kopyası: sadece program dosyası değiştirilir
        indir_dosyaya(bilgi["py"], APP_DIR / "ytmp3.py", 60)
        diske_yaz()
        return "tamam"
    deb = indir_dosyaya(bilgi["deb"], ONBELLEK / f"ytmp3_{bilgi['surum']}_all.deb")
    if shutil.which("pkexec"):
        # Şifre penceresi açılır, paket kurulur
        sonuc = subprocess.run(["pkexec", "apt-get", "install", "-y", "--reinstall", str(deb)],
                               capture_output=True, text=True)
        if sonuc.returncode == 0:
            return "tamam"
        if sonuc.returncode in (126, 127):  # şifre penceresi iptal edildi
            raise RuntimeError("Kurulum iptal edildi.")
        raise RuntimeError((sonuc.stderr or sonuc.stdout).strip()[-400:])
    # pkexec yoksa Pardus paket kurucusunu aç
    subprocess.Popen(["xdg-open", str(deb)])
    return "sayfa"


def ytdlp_guncelle():
    """En yeni yt-dlp'yi indirir. Yeni sürüm numarasını döndürür."""
    import urllib.request
    import zipfile
    GUNCEL_DIR.mkdir(parents=True, exist_ok=True)
    gecici = YTDLP_ZIP.with_suffix(".tmp")
    with urllib.request.urlopen(YTDLP_URL, timeout=60) as r, open(gecici, "wb") as f:
        shutil.copyfileobj(r, f)
    with zipfile.ZipFile(gecici) as z:
        surum_kodu = z.read("yt_dlp/version.py").decode()
    os.replace(gecici, YTDLP_ZIP)
    for satir in surum_kodu.splitlines():
        if satir.startswith("__version__"):
            return satir.split("=")[1].strip().strip("'\"")
    return "?"


def usbye_kopyala(usb_yolu):
    """Programın taşınabilir kopyasını USB'ye yazar."""
    hedef = Path(usb_yolu) / "YTMP3"
    if DONDURULMUS:
        # Windows: program klasörünün tamamı kopyalanır, USB'de .exe'ye çift tıklanır
        shutil.copytree(APP_DIR, hedef, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("unins*", "ayarlar.json", "onbellek"))
        nasil = ("Bu USB'yi herhangi bir Windows bilgisayara takın.\n"
                 "YTMP3 klasöründeki 'YouTube MP3.exe' dosyasına çift tıklayın.\n\n")
    else:
        if hedef.exists():
            shutil.rmtree(hedef / "lib", ignore_errors=True)
        hedef.mkdir(parents=True, exist_ok=True)
        shutil.copy2(APP_DIR / "ytmp3.py", hedef / "ytmp3.py")
        if LIB_DIR.is_dir():
            shutil.copytree(LIB_DIR, hedef / "lib", ignore=shutil.ignore_patterns("__pycache__"))
        (hedef / "BASLAT.sh").write_text(BASLAT_SH, encoding="utf-8")
        nasil = ("Bu USB'yi herhangi bir Pardus / Linux bilgisayara takın.\n"
                 "YTMP3 klasöründe sağ tık > 'Terminalde aç' deyip şunu yazın:\n\n"
                 "    bash BASLAT.sh\n\n")
    if YTDLP_ZIP.is_file():
        shutil.copy2(YTDLP_ZIP, hedef / "yt-dlp.zip")
    (hedef / "PORTABLE").write_text("")
    (hedef / "NASIL_ACILIR.txt").write_text(
        nasil + "İndirilen müzikler USB'deki 'Muzikler' klasörüne kaydedilir.\n", encoding="utf-8")
    (Path(usb_yolu) / "Muzikler").mkdir(exist_ok=True)
    diske_yaz()
    return hedef

ACCENT = "#E5383B"
ACCENT_HOVER = "#BA181B"
RENKLER = {
    "Kırmızı": ("#E5383B", "#BA181B"), "Turuncu": ("#F77F00", "#C96500"),
    "Pembe": ("#E84393", "#B9316F"), "Mor": ("#8E44EC", "#6C2BC0"),
    "Mavi": ("#3A86FF", "#2667CC"), "Turkuaz": ("#00A8A8", "#007F7F"),
    "Yeşil": ("#2EB872", "#228B57"), "Gece": ("#4A5A70", "#34404F"),
}
DOSYA_ADLARI = {
    "Şarkı adı": "%(title)s",
    "Kanal - Şarkı adı": "%(uploader|Bilinmeyen)s - %(title)s",
    "Şarkı adı (Kanal)": "%(title)s (%(uploader|Bilinmeyen)s)",
}
BOYUTLAR = {"Küçük": 0.9, "Normal": 1.0, "Büyük": 1.15, "Çok büyük": 1.3}
TEMALAR = {"Sistem": "system", "Açık": "light", "Koyu": "dark"}


def masaustu_kisayolu():
    """Masaüstüne çift tıklanabilir kısayol koyar. Kısayolun yolunu döndürür."""
    import hashlib
    try:
        masaustu = Path(subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True,
                                       text=True).stdout.strip() or Path.home() / "Masaüstü")
    except OSError:
        masaustu = Path.home() / "Masaüstü"
    if not masaustu.is_dir():
        masaustu = Path.home() / "Desktop"
    masaustu.mkdir(parents=True, exist_ok=True)
    sistem = Path("/usr/share/applications/ytmp3.desktop")
    if sistem.is_file() and not PORTABLE:
        icerik = sistem.read_text(encoding="utf-8")
    else:
        icerik = ("[Desktop Entry]\nName=YouTube MP3\nComment=YouTube videolarını MP3 olarak indir\n"
                  f"Exec=python3 \"{APP_DIR / 'ytmp3.py'}\"\nIcon=ytmp3\nTerminal=false\nType=Application\n")
    hedef = masaustu / "ytmp3.desktop"
    hedef.write_text(icerik, encoding="utf-8")
    hedef.chmod(0o755)
    # "Güvenilmeyen uygulama" uyarısı çıkmasın (GNOME / XFCE)
    if shutil.which("gio"):
        ozet = hashlib.sha256(hedef.read_bytes()).hexdigest()
        for anahtar, deger in (("metadata::trusted", "true"), ("metadata::xfce-exe-checksum", ozet)):
            subprocess.run(["gio", "set", "-t", "string", str(hedef), anahtar, deger], capture_output=True)
    return hedef


def koyulas(renk, oran=0.8):
    r_, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % (int(r_ * oran), int(g * oran), int(b * oran))


def selamla(ad):
    saat = datetime.now().hour
    s = ("İyi geceler" if saat < 6 else "Günaydın" if saat < 12 else
         "İyi günler" if saat < 18 else "İyi akşamlar")
    return f"{s}, {ad} 👋" if ad else s + " 👋"


IKINCIL = dict(fg_color=("gray82", "gray30"), hover_color=("gray72", "gray24"), text_color=("gray10", "gray92"))


def varsayilan_klasor():
    if PORTABLE:
        return str(APP_DIR.parent / "Muzikler")
    for ad in ("Müzik", "Music", "İndirilenler", "Downloads"):
        p = Path.home() / ad
        if p.is_dir():
            return str(p / "YouTube MP3")
    return str(Path.home() / "YouTube MP3")


def usb_listesi():
    """Takılı USB / harici diskleri bulur: [(ad, yol, bos_gb)]"""
    if WINDOWS:
        import ctypes
        import string
        k32 = ctypes.windll.kernel32
        surucler = []
        maske = k32.GetLogicalDrives()
        for i, harf in enumerate(string.ascii_uppercase):
            kok = f"{harf}:\\"
            if not maske >> i & 1 or k32.GetDriveTypeW(kok) != 2:  # 2 = çıkarılabilir disk
                continue
            etiket = ctypes.create_unicode_buffer(261)
            k32.GetVolumeInformationW(kok, etiket, 261, None, None, None, None, 0)
            try:
                bos = shutil.disk_usage(kok).free / 1024**3
            except OSError:
                continue
            surucler.append((f"{etiket.value or 'USB'} ({harf}:)", kok, bos))
        return surucler
    user = os.environ.get("USER") or Path.home().name
    surucler = []
    for kok in (Path("/media") / user, Path("/run/media") / user, Path("/media")):
        if not kok.is_dir():
            continue
        for d in sorted(kok.iterdir()):
            try:
                if d.is_dir() and os.path.ismount(d):
                    bos = shutil.disk_usage(d).free / 1024**3
                    if not any(s[1] == str(d) for s in surucler):
                        surucler.append((d.name, str(d), bos))
            except OSError:
                pass
    return surucler


def ffmpeg_yolu():
    """Windows'ta programla gelen ffmpeg'i, Linux'ta sistemdekini kullan."""
    gomulu = APP_DIR / "ffmpeg"
    if (gomulu / "ffmpeg.exe").exists():
        return str(gomulu)
    kopya = os.environ.get("YTMP3_FFMPEG")
    if kopya and Path(kopya).exists():
        return kopya
    return None



# ---------------------------------------------------------------------------
# 📱 Telefondan kullanım: aynı Wi-Fi'deki telefon tarayıcıdan bağlanır
# ---------------------------------------------------------------------------
TELEFON_SAYFASI = r"""<!doctype html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="__RENK__">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="manifest" href="/manifest.json?k=__ANAHTAR__">
<link rel="apple-touch-icon" href="/ikon.png">
<title>YouTube MP3</title>
<style>
:root{--a:__RENK__;--bg:#f2f2f5;--kart:#fff;--yazi:#16161a;--soluk:#6b6b76;--cizgi:#e2e2e8}
@media (prefers-color-scheme:dark){:root{--bg:#121214;--kart:#1e1e22;--yazi:#f1f1f4;--soluk:#9a9aa6;--cizgi:#2e2e34}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--yazi);font:16px/1.4 -apple-system,system-ui,Segoe UI,Roboto,sans-serif;
padding:max(16px,env(safe-area-inset-top)) 16px 32px}
.ust{display:flex;align-items:center;gap:12px;margin:8px 0 18px}
.logo{width:44px;height:44px;border-radius:12px;background:var(--a);color:#fff;display:grid;place-items:center;font-size:20px}
h1{font-size:21px;margin:0}.alt{color:var(--soluk);font-size:13px}
.kart{background:var(--kart);border-radius:18px;padding:16px;margin-bottom:14px;border:1px solid var(--cizgi)}
input{width:100%;font-size:16px;padding:14px;border-radius:12px;border:1px solid var(--cizgi);background:var(--bg);color:var(--yazi)}
.kalite{display:flex;gap:6px;margin:12px 0}
.kalite button{flex:1;padding:10px 0;border-radius:10px;border:1px solid var(--cizgi);background:var(--bg);color:var(--yazi);font-size:15px}
.kalite button.secili{background:var(--a);border-color:var(--a);color:#fff}
.buyuk{width:100%;padding:15px;border:0;border-radius:14px;background:var(--a);color:#fff;font-size:17px;font-weight:600}
.buyuk:disabled{opacity:.5}
.is .baslik{font-weight:600;word-break:break-word}.is .durum{color:var(--soluk);font-size:13px;margin:4px 0 8px}
.cubuk{height:8px;border-radius:4px;background:var(--cizgi);overflow:hidden}.cubuk i{display:block;height:100%;background:var(--a);width:0;transition:width .4s}
.dosya{display:block;margin-top:10px;padding:12px;text-align:center;border-radius:12px;background:var(--a);color:#fff;text-decoration:none;font-weight:600}
.hata{color:#e5383b}.bos{text-align:center;color:var(--soluk);font-size:14px;padding:8px}
.not{color:var(--soluk);font-size:12px;text-align:center;margin-top:18px}
</style></head><body>
<div class="ust"><div class="logo">▶</div><div><h1>YouTube MP3</h1><div class="alt">Bilgisayarınız üzerinden indirir</div></div></div>
<div class="kart">
 <input id="link" type="url" inputmode="url" placeholder="YouTube linkini yapıştır" autocomplete="off">
 <div class="kalite" id="kalite"><button data-k="128">128</button><button data-k="192">192</button><button data-k="256">256</button><button data-k="320">320</button></div>
 <button class="buyuk" id="indir">⬇ MP3 Olarak İndir</button>
</div>
<div id="isler"></div>
<div class="not">İpucu: Paylaş menüsünden "Ana Ekrana Ekle" ile uygulama gibi kullanabilirsiniz.</div>
<script>
const K="__ANAHTAR__";let kalite="__KALITE__";
const kb=document.querySelectorAll("#kalite button");
function ks(){kb.forEach(b=>b.classList.toggle("secili",b.dataset.k==kalite))}
kb.forEach(b=>b.onclick=()=>{kalite=b.dataset.k;ks()});ks();
const btn=document.getElementById("indir"),link=document.getElementById("link");
btn.onclick=async()=>{const u=link.value.trim();if(!u){link.focus();return}
 btn.disabled=true;
 try{const r=await fetch("/api/indir?k="+K,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:u,kalite})});
  if(!r.ok)throw 0;link.value="";yenile()}catch(e){alert("Bilgisayara ulaşılamadı. Program açık mı?")}
 btn.disabled=false};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
async function yenile(){try{const r=await fetch("/api/isler?k="+K);const isler=await r.json();
 const d=document.getElementById("isler");
 if(!isler.length){d.innerHTML='<div class="bos">Henüz indirme yok</div>';return}
 d.innerHTML=isler.map(j=>`<div class="kart is"><div class="baslik">${esc(j.baslik)}</div>
  <div class="durum ${j.durum=="hata"?"hata":""}">${esc(j.mesaj)}</div>
  ${j.durum=="bitti"||j.durum=="hata"?"":`<div class="cubuk"><i style="width:${Math.round(j.oran*100)}%"></i></div>`}
  ${j.dosyalar.map((f,i)=>`<a class="dosya" href="/dosya/${j.id}/${i}?k=${K}" download>⬇ ${esc(f)}</a>`).join("")}</div>`).join("")
}catch(e){}}
yenile();setInterval(yenile,1200);
</script></body></html>"""


def yerel_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def ikon_png(boyut=180):
    """Ana ekran ikonu (kırmızı kare + ▶) için küçük bir PNG üretir."""
    import struct
    import zlib
    r_, g, b = (int(ACCENT[i:i + 2], 16) for i in (1, 3, 5))
    satirlar = []
    for y in range(boyut):
        satir = bytearray([0])
        for x in range(boyut):
            ux, uy = x / boyut, y / boyut
            ucgen = 0.38 <= ux <= 0.68 and abs(uy - 0.5) <= (0.68 - ux) * 0.58
            satir += bytes((255, 255, 255) if ucgen else (r_, g, b))
        satirlar.append(bytes(satir))

    def parca(tur, veri):
        return struct.pack(">I", len(veri)) + tur + veri + struct.pack(">I", zlib.crc32(tur + veri) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", boyut, boyut, 8, 2, 0, 0, 0))
            + parca(b"IDAT", zlib.compress(b"".join(satirlar), 9)) + parca(b"IEND", b""))


class TelefonSunucusu:
    def __init__(self, uygulama):
        import queue
        import secrets
        self.app = uygulama
        if not uygulama.ayar.get("telefon_anahtar"):
            uygulama.ayar["telefon_anahtar"] = secrets.token_urlsafe(9)
            uygulama.ayar.kaydet()
        self.anahtar = uygulama.ayar["telefon_anahtar"]
        self.isler = {}
        self.sira = 0
        self.kuyruk = queue.Queue()
        self.httpd = None
        self.adres = ""
        self.klasor = ONBELLEK / "telefon"
        shutil.rmtree(self.klasor, ignore_errors=True)  # önceki oturumun dosyaları

    def calisiyor(self):
        return self.httpd is not None

    def baslat(self):
        from http.server import ThreadingHTTPServer
        isleyici = self._isleyici_sinifi()
        for port in (8765, 8766, 8767, 8768, 0):
            try:
                self.httpd = ThreadingHTTPServer(("0.0.0.0", port), isleyici)
                break
            except OSError:
                continue
        self.httpd.daemon_threads = True
        port = self.httpd.server_address[1]
        self.adres = f"http://{yerel_ip()}:{port}/?k={self.anahtar}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        threading.Thread(target=self._isci, daemon=True).start()

    def durdur(self):
        if self.httpd:
            h, self.httpd = self.httpd, None
            threading.Thread(target=lambda: (h.shutdown(), h.server_close()), daemon=True).start()
            self.kuyruk.put(None)

    # --- indirme işleri ---
    def is_ekle(self, url, kalite):
        self.sira += 1
        is_id = str(self.sira)
        self.isler[is_id] = dict(id=is_id, url=url, kalite=kalite, baslik=url, durum="sirada",
                                 mesaj="Sırada bekliyor...", oran=0.0, dosyalar=[], yollar=[])
        self.kuyruk.put(is_id)
        return is_id

    def _isci(self):
        while self.httpd is not None:
            is_id = self.kuyruk.get()
            if is_id is None:
                return
            j = self.isler[is_id]
            klasor = self.klasor / is_id
            klasor.mkdir(parents=True, exist_ok=True)

            def kanca(d, j=j):
                if d["status"] == "downloading":
                    toplam = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    if toplam:
                        j["oran"] = d.get("downloaded_bytes", 0) / toplam
                    j["mesaj"] = "Bilgisayar indiriyor..."
                elif d["status"] == "finished":
                    j["oran"], j["mesaj"] = 1.0, "MP3'e dönüştürülüyor..."
            try:
                j.update(durum="indiriliyor", mesaj="Bilgi alınıyor...")
                secenekler = self.app.ydl_secenekleri(str(klasor), kanca, guvenli_ad=True, kalite=j["kalite"])
                secenekler["outtmpl"] = os.path.join(str(klasor), "%(playlist_index&{:02d} - |)s"
                                                     + self.app._dosya_sablonu())
                with YoutubeDL(secenekler) as ydl:
                    bilgi = ydl.extract_info(j["url"], download=True)
                j["baslik"] = (bilgi or {}).get("title") or j["url"]
                yollar = sorted(klasor.glob("*.mp3"))
                if not yollar:
                    raise RuntimeError("MP3 oluşturulamadı")
                j.update(yollar=[str(p) for p in yollar], dosyalar=[p.name for p in yollar], durum="bitti",
                         mesaj=f"✔ Hazır · {len(yollar)} dosya" if len(yollar) > 1 else "✔ Hazır, telefona kaydedin")
                self.app.log(f"📱 ✔ {j['baslik']}")
            except Exception as e:
                j.update(durum="hata", mesaj=f"Hata: {str(e)[:150]}")
                self.app.log(f"📱 ✘ {j['url']}: {str(e)[:100]}")

    def _isleyici_sinifi(self):
        from http.server import BaseHTTPRequestHandler
        from urllib.parse import urlparse, parse_qs, quote
        import hmac
        sunucu = self

        class Isleyici(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _gonder(self, kod, govde, tur="application/json; charset=utf-8", ek=None):
                if isinstance(govde, str):
                    govde = govde.encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", tur)
                self.send_header("Content-Length", str(len(govde)))
                self.send_header("Cache-Control", "no-store")
                for k, v in (ek or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(govde)

            def _yetkili(self, q):
                return hmac.compare_digest(q.get("k", [""])[0], sunucu.anahtar)

            def do_GET(self):
                u = urlparse(self.path)
                q = parse_qs(u.query)
                if u.path == "/ikon.png":
                    return self._gonder(200, ikon_png(), "image/png")
                if not self._yetkili(q):
                    return self._gonder(403, "<h2 style='font-family:sans-serif'>Bağlantı geçersiz. "
                                             "Bilgisayardaki QR kodu yeniden okutun.</h2>", "text/html; charset=utf-8")
                if u.path == "/":
                    sayfa = (TELEFON_SAYFASI.replace("__ANAHTAR__", sunucu.anahtar).replace("__RENK__", ACCENT)
                             .replace("__KALITE__", sunucu.app.ayar["kalite"]))
                    return self._gonder(200, sayfa, "text/html; charset=utf-8")
                if u.path == "/manifest.json":
                    return self._gonder(200, json.dumps({
                        "name": "YouTube MP3", "short_name": "YT MP3", "display": "standalone",
                        "start_url": f"/?k={sunucu.anahtar}", "theme_color": ACCENT, "background_color": ACCENT,
                        "icons": [{"src": "/ikon.png", "sizes": "180x180", "type": "image/png"}]}))
                if u.path == "/api/isler":
                    liste = [{k: v for k, v in j.items() if k != "yollar"} for j in sunucu.isler.values()]
                    return self._gonder(200, json.dumps(liste[::-1][:30], ensure_ascii=False))
                if u.path.startswith("/dosya/"):
                    try:
                        _, _, is_id, no = u.path.split("/")
                        yol = Path(sunucu.isler[is_id]["yollar"][int(no)])
                        veri = yol.read_bytes()
                    except (ValueError, KeyError, IndexError, OSError):
                        return self._gonder(404, "{}")
                    return self._gonder(200, veri, "audio/mpeg", {
                        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(yol.name)}"})
                self._gonder(404, "{}")

            def do_POST(self):
                u = urlparse(self.path)
                if not self._yetkili(parse_qs(u.query)) or u.path != "/api/indir":
                    return self._gonder(403, "{}")
                try:
                    uzunluk = min(int(self.headers.get("Content-Length", 0)), 10000)
                    veri = json.loads(self.rfile.read(uzunluk) or b"{}")
                    url = str(veri.get("url", "")).strip()
                    kalite = str(veri.get("kalite", "192"))
                    if not url.startswith(("http://", "https://")) or kalite not in ("128", "192", "256", "320"):
                        raise ValueError
                except ValueError:
                    return self._gonder(400, "{}")
                self._gonder(200, json.dumps({"id": sunucu.is_ekle(url, kalite)}))
        return Isleyici


class Ayarlar(dict):
    def __init__(self):
        super().__init__(
            tema="dark", kalite="192", kapak=True, klasor=varsayilan_klasor(), mod="pc",
            renk="Kırmızı", ozel_renk="", ad="", baslik="YouTube MP3", boyut="Normal",
            dosya_adi="Şarkı adı", playlist_klasor=True, numara=True,
            bildirim=True, ses=True, klasoru_ac=False, pano_otomatik=True, gecmis=[], son_surum="",
            telefon_anahtar="")
        try:
            self.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass

    def kaydet(self):
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(self, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass


class Uygulama(ctk.CTk):
    def __init__(self):
        global ACCENT, ACCENT_HOVER
        self.ayar = Ayarlar()
        if self.ayar["ozel_renk"]:
            ACCENT, ACCENT_HOVER = self.ayar["ozel_renk"], koyulas(self.ayar["ozel_renk"])
        else:
            ACCENT, ACCENT_HOVER = RENKLER.get(self.ayar["renk"], RENKLER["Kırmızı"])
        olcek = BOYUTLAR.get(self.ayar["boyut"], 1.0)
        ctk.set_widget_scaling(olcek)
        ctk.set_window_scaling(olcek)
        ctk.set_appearance_mode(self.ayar["tema"])
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title(self.ayar["baslik"] or "YouTube MP3")
        ikon = Path(getattr(sys, "_MEIPASS", APP_DIR)) / "ikon.ico"
        if WINDOWS and ikon.exists():
            self.iconbitmap(str(ikon))
        self.geometry("760x780")
        self.minsize(620, 600)
        self.calisiyor = False
        self.iptal = False
        self.usb_map = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._ust_bar()
        self._ayar_karti()
        self._liste_karti()
        self._alt_bar()
        self.mod_degisti(self.ayar["mod"])
        self.protocol("WM_DELETE_WINDOW", self.kapat)
        self._gecmisi_yukle()
        self.after(1500, self.arka_planda_kontrol)
        self.after(800, self.yenilikleri_goster)
        if self.ayar["pano_otomatik"]:
            self.after(400, self.panodan_otomatik)

    # ---------- Arayüz ----------
    def _ust_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        bar.grid_columnconfigure(1, weight=1)

        logo = ctk.CTkLabel(bar, text="▶", width=44, height=44, corner_radius=12,
                            fg_color=ACCENT, text_color="white", font=ctk.CTkFont(size=20, weight="bold"))
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ctk.CTkLabel(bar, text=self.ayar["baslik"] or "YouTube MP3", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=1, sticky="w")
        alt = selamla(self.ayar["ad"].strip())
        alt += "  ·  USB'den çalışıyor" if PORTABLE else f"  ·  Sürüm {VERSION}"
        ctk.CTkLabel(bar, text=alt, text_color=("gray40", "gray60"),
                     font=ctk.CTkFont(size=12)).grid(row=1, column=1, sticky="w")

        self.tema_sw = ctk.CTkSwitch(bar, text="Koyu tema", command=self.tema_degistir,
                                     progress_color=ACCENT)
        self.tema_sw.grid(row=0, column=2, rowspan=2)
        if ctk.get_appearance_mode() == "Dark":
            self.tema_sw.select()
        ctk.CTkButton(bar, text="⚙", width=40, height=40, corner_radius=20, font=ctk.CTkFont(size=18),
                      command=self.ayarlar_penceresi, **IKINCIL).grid(row=0, column=3, rowspan=2, padx=(12, 0))

    def _ayar_karti(self):
        kart = ctk.CTkFrame(self, corner_radius=16)
        kart.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        kart.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(kart, text="Video veya playlist linkleri", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(16, 4))
        self.link_kutu = ctk.CTkTextbox(kart, height=80, corner_radius=10, border_width=1,
                                        font=ctk.CTkFont(size=13))
        self.link_kutu.grid(row=1, column=0, columnspan=3, sticky="ew", padx=18)
        ctk.CTkButton(kart, text="📋 Panodan yapıştır", width=150, height=28, fg_color="transparent",
                      border_width=1, text_color=("gray20", "gray85"), command=self.yapistir).grid(
            row=2, column=0, columnspan=3, sticky="e", padx=18, pady=(6, 0))

        # Kalite
        ctk.CTkLabel(kart, text="Kalite").grid(row=3, column=0, sticky="w", padx=18, pady=(14, 0))
        self.kalite = ctk.CTkSegmentedButton(kart, values=["128", "192", "256", "320"],
                                             selected_color=ACCENT, selected_hover_color=ACCENT_HOVER)
        self.kalite.set(self.ayar["kalite"])
        self.kalite.grid(row=3, column=1, sticky="w", pady=(14, 0))
        self.kapak = ctk.CTkCheckBox(kart, text="Kapak resmi ekle", fg_color=ACCENT, hover_color=ACCENT_HOVER)
        if self.ayar["kapak"]:
            self.kapak.select()
        self.kapak.grid(row=3, column=2, sticky="e", padx=18, pady=(14, 0))

        # Kayıt yeri
        ctk.CTkLabel(kart, text="Kayıt yeri").grid(row=4, column=0, sticky="w", padx=18, pady=(14, 0))
        self.mod = ctk.CTkSegmentedButton(kart, values=["💻 Bilgisayar", "🔌 USB Bellek"],
                                          command=lambda v: self.mod_degisti("usb" if "USB" in v else "pc"),
                                          selected_color=ACCENT, selected_hover_color=ACCENT_HOVER)
        self.mod.grid(row=4, column=1, columnspan=2, sticky="w", pady=(14, 0))

        # Bilgisayar klasör satırı
        self.pc_satir = ctk.CTkFrame(kart, fg_color="transparent")
        self.pc_satir.grid_columnconfigure(0, weight=1)
        self.klasor = ctk.CTkEntry(self.pc_satir, height=34)
        self.klasor.insert(0, self.ayar["klasor"])
        self.klasor.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(self.pc_satir, text="Gözat", width=80, height=34, command=self.klasor_sec, **IKINCIL).grid(
            row=0, column=1, padx=(8, 0))

        # USB satırı
        self.usb_satir = ctk.CTkFrame(kart, fg_color="transparent")
        self.usb_satir.grid_columnconfigure(0, weight=1)
        self.usb_secim = ctk.CTkOptionMenu(self.usb_satir, values=["USB bulunamadı"], height=34,
                                           fg_color=("gray85", "gray25"), button_color=ACCENT,
                                           button_hover_color=ACCENT_HOVER, text_color=("gray10", "gray90"))
        self.usb_secim.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(self.usb_satir, text="⟳ Yenile", width=80, height=34, command=self.usb_yenile, **IKINCIL).grid(
            row=0, column=1, padx=(8, 0))
        ctk.CTkLabel(self.usb_satir, text="Dosyalar USB'de 'YouTube MP3' klasörüne kaydedilir.",
                     text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11)).grid(
            row=1, column=0, columnspan=2, sticky="w")

        self.indir_btn = ctk.CTkButton(kart, text="⬇  MP3 Olarak İndir", height=46, corner_radius=12,
                                       fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                       font=ctk.CTkFont(size=15, weight="bold"), command=self.baslat)
        self.indir_btn.grid(row=6, column=0, columnspan=3, sticky="ew", padx=18, pady=(16, 18))

    def _liste_karti(self):
        kart = ctk.CTkFrame(self, corner_radius=16)
        kart.grid(row=2, column=0, sticky="nsew", padx=24, pady=8)
        kart.grid_columnconfigure(0, weight=1)
        kart.grid_rowconfigure(3, weight=1)

        self.durum = ctk.CTkLabel(kart, text="Hazır", anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
        self.durum.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        self.cubuk = ctk.CTkProgressBar(kart, height=10, progress_color=ACCENT)
        self.cubuk.set(0)
        self.cubuk.grid(row=1, column=0, sticky="ew", padx=18)
        self.detay = ctk.CTkLabel(kart, text="", anchor="w", text_color=("gray40", "gray60"),
                                  font=ctk.CTkFont(size=11))
        self.detay.grid(row=2, column=0, sticky="ew", padx=18)
        self.gecmis = ctk.CTkTextbox(kart, corner_radius=10, font=ctk.CTkFont(size=12), state="disabled")
        self.gecmis.grid(row=3, column=0, sticky="nsew", padx=18, pady=(6, 16))

    def _alt_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 16))
        self.iptal_btn = ctk.CTkButton(bar, text="İptal", width=90, fg_color="gray40", hover_color="gray30",
                                       state="disabled", command=self.iptal_et)
        self.iptal_btn.pack(side="left")
        ctk.CTkButton(bar, text="📂 Klasörü aç", width=120, command=self.klasor_ac, **IKINCIL).pack(side="right")
        self.guncelle_btn = ctk.CTkButton(bar, text="🔄 Güncelle", width=110, command=self.guncelle, **IKINCIL)
        self.guncelle_btn.pack(side="right", padx=8)
        self.telefon_btn = ctk.CTkButton(bar, text="📱 Telefon", width=100, command=self.telefon_penceresi,
                                         **IKINCIL)
        self.telefon_btn.pack(side="right")
        if not PORTABLE:
            ctk.CTkButton(bar, text="🔌 USB'ye taşı", width=120, command=self.usb_tasi, **IKINCIL).pack(side="right", padx=(0, 8))

    # ---------- 📱 Telefondan kullan ----------
    def telefon_penceresi(self):
        if getattr(self, "_tel_pen", None) and self._tel_pen.winfo_exists():
            self._tel_pen.focus()
            return
        if getattr(self, "telefon", None) is None:
            self.telefon = TelefonSunucusu(self)
        if not self.telefon.calisiyor():
            try:
                self.telefon.baslat()
            except Exception as e:
                messagebox.showerror("Telefon", f"Bağlantı başlatılamadı:\n{e}")
                return
            self.telefon_btn.configure(text="📱 Telefon ●", text_color=ACCENT)
            self.log("📱 Telefon bağlantısı açıldı")
        p = self._tel_pen = ctk.CTkToplevel(self)
        p.title("Telefondan kullan")
        p.geometry("400x510")
        p.resizable(False, False)
        p.transient(self)
        ctk.CTkLabel(p, text="📱 Telefondan kullan", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(18, 2))
        ctk.CTkLabel(p, text="Telefonun kamerasıyla QR kodu okut", text_color=("gray40", "gray60")).pack()

        import tkinter as tk
        import qrcode
        qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(self.telefon.adres)
        qr.make(fit=True)
        matris = qr.get_matrix()
        hucre = max(4, 250 // len(matris))
        boyut = hucre * len(matris)
        tuval = tk.Canvas(p, width=boyut, height=boyut, bg="white", highlightthickness=0)
        for y, satir in enumerate(matris):
            for x, dolu in enumerate(satir):
                if dolu:
                    tuval.create_rectangle(x * hucre, y * hucre, (x + 1) * hucre, (y + 1) * hucre,
                                           fill="black", outline="")
        tuval.pack(pady=14)

        adres = ctk.CTkEntry(p, justify="center", font=ctk.CTkFont(size=11))
        adres.insert(0, self.telefon.adres)
        adres.configure(state="readonly")
        adres.pack(fill="x", padx=24)
        ctk.CTkLabel(p, justify="left", wraplength=350, font=ctk.CTkFont(size=12),
                     text_color=("gray30", "gray70"),
                     text="• Telefon ve bilgisayar aynı Wi-Fi'de olmalı\n"
                          "• Program açık kaldığı sürece çalışır\n"
                          "• iPhone ve Android'de tarayıcıdan çalışır, kurulum gerekmez").pack(
            anchor="w", padx=24, pady=10)

        def durdur():
            self.telefon.durdur()
            self.telefon_btn.configure(text="📱 Telefon", text_color=IKINCIL["text_color"])
            self.log("📱 Telefon bağlantısı kapatıldı")
            p.destroy()
        alt = ctk.CTkFrame(p, fg_color="transparent")
        alt.pack(fill="x", padx=24, pady=(4, 18), side="bottom")
        ctk.CTkButton(alt, text="Bağlantıyı kapat", command=durdur, **IKINCIL).pack(side="left")
        ctk.CTkButton(alt, text="Tamam", fg_color=ACCENT, hover_color=ACCENT_HOVER, width=100,
                      command=p.destroy).pack(side="right")

    def guncelle(self):
        if self.calisiyor:
            return
        self.guncelle_btn.configure(state="disabled", text="Bakılıyor...")
        self.ui(durum="Güncellemeler kontrol ediliyor...", detay="")

        def is_():
            # 1) Uygulamanın yeni sürümü
            try:
                bilgi = uygulama_surumu_kontrol()
            except Exception as e:
                bilgi, hata = None, str(e)
                self.ui(detay=f"Uygulama sürümü kontrol edilemedi: {hata}")
            if bilgi:
                self.after(0, lambda: self._uygulama_guncelle_sor(bilgi))
                return
            # 2) İndirme motoru (yt-dlp)
            try:
                self.ui(durum="İndirme motoru güncelleniyor...")
                yeni = ytdlp_guncelle()
                eski = yt_dlp.version.__version__
                if yeni == eski:
                    msg = f"Her şey güncel 👍\n\nUygulama: {VERSION}\nİndirme motoru: {yeni}"
                else:
                    msg = (f"Uygulama zaten güncel ({VERSION}).\n\nİndirme motoru güncellendi: "
                           f"{eski} → {yeni}\nProgram yeniden açılınca devreye girer.")
                self.after(0, lambda: messagebox.showinfo("Güncelleme", msg))
                self.ui(durum="Güncelleme tamamlandı", detay=f"Uygulama {VERSION} · yt-dlp {yeni}")
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("Güncelleme", f"Güncellenemedi:\n{err}"))
                self.ui(durum="⚠ Güncelleme başarısız", detay=err)
            self.after(0, self._guncelle_btn_normal)
        threading.Thread(target=is_, daemon=True).start()

    def _guncelle_btn_normal(self):
        self.guncelle_btn.configure(state="normal", text="🔄 Güncelle", width=110, **IKINCIL)

    def _uygulama_guncelle_sor(self, bilgi):
        notlar = bilgi.get("notlar", "")
        if not messagebox.askyesno(
                "Yeni sürüm var 🎉",
                f"YouTube MP3 {bilgi['surum']} çıktı (sizdeki: {VERSION}).\n\n{notlar}\n\nŞimdi kurulsun mu?"):
            self.ui(durum="Güncelleme ertelendi")
            self._guncelle_btn_normal()
            return
        self.guncelle_btn.configure(text="Kuruluyor...")
        self.ui(durum=f"Sürüm {bilgi['surum']} indiriliyor...", detay="Şifreniz istenebilir")

        def is_():
            try:
                sonuc = uygulamayi_guncelle(bilgi)
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("Güncelleme", f"Kurulamadı:\n{err}"))
                self.ui(durum="⚠ Güncelleme kurulamadı", detay=err)
                self.after(0, self._guncelle_btn_normal)
                return
            if sonuc == "cik":
                def kapat():
                    self._ayarlari_topla()
                    self.ayar.kaydet()
                    self.destroy()
                self.ui(durum="Kuruluyor...", detay="Program birazdan kendiliğinden yeniden açılacak")
                self.after(1500, kapat)
            elif sonuc == "tamam":
                def bitir():
                    messagebox.showinfo("Güncelleme", f"Sürüm {bilgi['surum']} kuruldu!\nProgram yeniden açılıyor.")
                    self.yeniden_baslat()
                self.after(0, bitir)
            else:
                self.ui(durum="İndirme sayfası açıldı", detay="Yeni sürümü kurduktan sonra programı yeniden açın")
                self.after(0, self._guncelle_btn_normal)
        threading.Thread(target=is_, daemon=True).start()

    def yenilikleri_goster(self):
        """Güncellemeden sonraki ilk açılışta yenilikleri gösterir."""
        onceki = self.ayar["son_surum"]
        self.ayar["son_surum"] = VERSION
        self.ayar.kaydet()
        if not onceki or onceki == VERSION:
            return
        p = ctk.CTkToplevel(self)
        p.title("Yenilikler")
        p.geometry("440x300")
        p.transient(self)
        p.after(100, p.grab_set)
        ctk.CTkLabel(p, text="🎉", font=ctk.CTkFont(size=40)).pack(pady=(18, 0))
        ctk.CTkLabel(p, text=f"Sürüm {VERSION}'e hoş geldin!", font=ctk.CTkFont(size=18, weight="bold")).pack()
        ctk.CTkLabel(p, text=f"{onceki} → {VERSION}", text_color=("gray40", "gray60")).pack(pady=(0, 10))
        ctk.CTkLabel(p, text="\n".join("•  " + y for y in YENILIKLER), justify="left", wraplength=380).pack(
            padx=24, anchor="w")
        ctk.CTkButton(p, text="Harika!", height=38, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      font=ctk.CTkFont(size=14, weight="bold"), command=p.destroy).pack(
            side="bottom", fill="x", padx=24, pady=18)

    def arka_planda_kontrol(self):
        """Açılışta sessizce bakar; yeni sürüm varsa butonu vurgular."""
        def is_():
            try:
                bilgi = uygulama_surumu_kontrol()
            except Exception:
                return
            if bilgi:
                self.after(0, lambda: self.guncelle_btn.configure(
                    text=f"🎉 Yeni sürüm {bilgi['surum']}", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                    text_color="white", width=150))
        threading.Thread(target=is_, daemon=True).start()

    def usb_tasi(self):
        surucler = usb_listesi()
        if not surucler:
            messagebox.showwarning("USB'ye taşı", "Takılı USB bellek bulunamadı.\n\n"
                                   "USB'yi takın, dosya yöneticisinde bir kez açın ve tekrar deneyin.")
            return
        pencere = ctk.CTkToplevel(self)
        pencere.title("USB'ye taşı")
        pencere.geometry("440x260")
        pencere.transient(self)
        pencere.after(100, pencere.grab_set)
        ctk.CTkLabel(pencere, text="Taşınabilir kopya oluştur", font=ctk.CTkFont(size=17, weight="bold")).pack(
            anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(pencere, justify="left", wraplength=400, text_color=("gray30", "gray70"),
                     text="Program USB'ye kopyalanır. USB'yi başka bir bilgisayara takıp "
                          "'BASLAT.sh' ile açabilirsiniz. Ayarlar ve müzikler USB'de kalır.").pack(
            anchor="w", padx=20)
        secenekler = {f"{ad}  ({bos:.1f} GB boş)": yol for ad, yol, bos in surucler}
        secim = ctk.CTkOptionMenu(pencere, values=list(secenekler), height=34, button_color=ACCENT,
                                  button_hover_color=ACCENT_HOVER, fg_color=("gray85", "gray25"),
                                  text_color=("gray10", "gray90"))
        secim.pack(fill="x", padx=20, pady=16)

        def kopyala():
            try:
                hedef = usbye_kopyala(secenekler[secim.get()])
                pencere.destroy()
                messagebox.showinfo("Tamam", f"Taşınabilir kopya hazır:\n{hedef}\n\n"
                                    "Başka bilgisayarda: YTMP3 klasöründe terminal açıp\n  bash BASLAT.sh")
            except Exception as e:
                messagebox.showerror("Hata", f"Kopyalanamadı:\n{e}")
        ctk.CTkButton(pencere, text="USB'ye kopyala", height=40, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      font=ctk.CTkFont(size=14, weight="bold"), command=kopyala).pack(fill="x", padx=20)

    # ---------- Kişiselleştirme ----------
    def ayarlar_penceresi(self):
        if getattr(self, "_ayar_pen", None) and self._ayar_pen.winfo_exists():
            self._ayar_pen.focus()
            return
        p = self._ayar_pen = ctk.CTkToplevel(self)
        p.title("Kişiselleştir")
        p.geometry("540x560")
        p.transient(self)
        p.after(100, p.grab_set)
        a = self.ayar
        kalin = ctk.CTkFont(size=13, weight="bold")
        kucuk = ctk.CTkFont(size=11)
        soluk = ("gray40", "gray60")

        sekme = ctk.CTkTabview(p, segmented_button_selected_color=ACCENT,
                               segmented_button_selected_hover_color=ACCENT_HOVER)
        sekme.pack(fill="both", expand=True, padx=16, pady=(8, 0))
        g, d, o = sekme.add("🎨 Görünüm"), sekme.add("⬇ İndirme"), sekme.add("⚙ Diğer")
        for t in (g, d, o):
            t.grid_columnconfigure(1, weight=1)

        def baslik(t, satir, yazi, aciklama=None):
            ctk.CTkLabel(t, text=yazi, font=kalin).grid(row=satir, column=0, sticky="nw", padx=8, pady=(12, 0))
            if aciklama:
                ctk.CTkLabel(t, text=aciklama, font=kucuk, text_color=soluk).grid(
                    row=satir + 1, column=0, sticky="nw", padx=8)

        # --- Görünüm ---
        baslik(g, 0, "Adın", "Açılışta seni selamlar")
        ad = ctk.CTkEntry(g, placeholder_text="ör. Mustafa")
        ad.insert(0, a["ad"])
        ad.grid(row=0, column=1, sticky="ew", padx=8, pady=(12, 0))

        baslik(g, 2, "Program adı")
        ust = ctk.CTkEntry(g)
        ust.insert(0, a["baslik"])
        ust.grid(row=2, column=1, sticky="ew", padx=8, pady=(12, 0))

        baslik(g, 3, "Renk")
        renk_cerceve = ctk.CTkFrame(g, fg_color="transparent")
        renk_cerceve.grid(row=3, column=1, sticky="w", padx=8, pady=(12, 0))
        secili = {"renk": a["renk"], "ozel": a["ozel_renk"]}
        dugmeler = {}

        def renk_isaretle():
            for isim, b in dugmeler.items():
                aktif = (isim == "Özel" and secili["ozel"]) or (isim == secili["renk"] and not secili["ozel"])
                b.configure(border_width=3 if aktif else 0, text="✓" if aktif else "")

        def renk_sec(isim):
            secili["renk"], secili["ozel"] = isim, ""
            renk_isaretle()

        def ozel_renk():
            from tkinter import colorchooser
            sonuc = colorchooser.askcolor(color=secili["ozel"] or ACCENT, parent=p, title="Renk seç")
            if sonuc and sonuc[1]:
                secili["ozel"] = sonuc[1].upper()
                dugmeler["Özel"].configure(fg_color=secili["ozel"], hover_color=koyulas(secili["ozel"]))
                renk_isaretle()

        for i, (isim, (c, h)) in enumerate(RENKLER.items()):
            b = ctk.CTkButton(renk_cerceve, text="", width=30, height=30, corner_radius=15, fg_color=c,
                              hover_color=h, border_color=("gray10", "white"), text_color="white",
                              command=lambda x=isim: renk_sec(x))
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3)
            dugmeler[isim] = b
        oc = secili["ozel"] or "gray50"
        dugmeler["Özel"] = ctk.CTkButton(renk_cerceve, text="", width=30, height=30, corner_radius=15,
                                         fg_color=oc, hover_color=koyulas(oc) if oc.startswith("#") else "gray40",
                                         border_color=("gray10", "white"), text_color="white", command=ozel_renk)
        dugmeler["Özel"].grid(row=0, column=4, rowspan=2, padx=(10, 3))
        ctk.CTkLabel(renk_cerceve, text="Özel", font=kucuk, text_color=soluk).grid(row=2, column=4)
        renk_isaretle()

        baslik(g, 4, "Tema")
        tema = ctk.CTkSegmentedButton(g, values=list(TEMALAR), selected_color=ACCENT,
                                      selected_hover_color=ACCENT_HOVER)
        tema.set({v: k for k, v in TEMALAR.items()}.get(a["tema"], "Koyu"))
        tema.grid(row=4, column=1, sticky="w", padx=8, pady=(12, 0))

        baslik(g, 5, "Yazı boyutu")
        boyut = ctk.CTkSegmentedButton(g, values=list(BOYUTLAR), selected_color=ACCENT,
                                       selected_hover_color=ACCENT_HOVER)
        boyut.set(a["boyut"])
        boyut.grid(row=5, column=1, sticky="w", padx=8, pady=(12, 0))

        # --- İndirme ---
        baslik(d, 0, "Dosya adı")
        dosya = ctk.CTkOptionMenu(d, values=list(DOSYA_ADLARI), fg_color=("gray85", "gray25"),
                                  button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                                  text_color=("gray10", "gray90"))
        dosya.set(a["dosya_adi"])
        dosya.grid(row=0, column=1, sticky="ew", padx=8, pady=(12, 0))

        def kutu(t, satir, yazi, anahtar, aciklama=None):
            c = ctk.CTkCheckBox(t, text=yazi, fg_color=ACCENT, hover_color=ACCENT_HOVER)
            if a[anahtar]:
                c.select()
            c.grid(row=satir, column=0, columnspan=2, sticky="w", padx=8, pady=(14, 0))
            if aciklama:
                ctk.CTkLabel(t, text=aciklama, font=kucuk, text_color=soluk).grid(
                    row=satir + 1, column=0, columnspan=2, sticky="w", padx=36)
            return c

        k_pk = kutu(d, 1, "Playlist'leri ayrı klasöre kaydet", "playlist_klasor",
                    "Her playlist kendi adını taşıyan bir klasöre iner")
        k_nu = kutu(d, 3, "Playlist şarkılarını numarala", "numara", "01 - Şarkı, 02 - Şarkı ...")
        k_ac = kutu(d, 5, "İndirme bitince klasörü aç", "klasoru_ac")

        # --- Diğer ---
        k_bi = kutu(o, 0, "Bitince masaüstü bildirimi göster" if not WINDOWS else "Bitince bildir", "bildirim")
        k_se = kutu(o, 1, "Bitince ses çal", "ses")
        k_pa = kutu(o, 2, "Açılışta panodaki YouTube linkini otomatik ekle", "pano_otomatik")

        def gecmis_sil():
            if messagebox.askyesno("Geçmiş", "İndirme geçmişi silinsin mi?", parent=p):
                a["gecmis"] = []
                self.gecmis.configure(state="normal")
                self.gecmis.delete("1.0", "end")
                self.gecmis.configure(state="disabled")
                a.kaydet()
        def kisayol():
            try:
                yol = masaustu_kisayolu()
                messagebox.showinfo("Kısayol", f"Masaüstüne kısayol eklendi:\n{yol}", parent=p)
            except Exception as e:
                messagebox.showerror("Kısayol", f"Eklenemedi:\n{e}", parent=p)
        if not WINDOWS:  # Windows'ta kurulum programı kısayolu zaten ekler
            ctk.CTkButton(o, text="🖥 Masaüstüne kısayol ekle", command=kisayol, **IKINCIL).grid(
                row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(24, 0))
        ctk.CTkButton(o, text="🗑 İndirme geçmişini temizle", command=gecmis_sil, **IKINCIL).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 0))
        ctk.CTkLabel(o, text=f"YouTube MP3 {VERSION}  ·  yt-dlp {yt_dlp.version.__version__}",
                     font=kucuk, text_color=soluk).grid(row=5, column=0, columnspan=2, sticky="w", padx=8, pady=(24, 0))

        def kaydet():
            onceki = (a["ad"], a["baslik"], a["renk"], a["ozel_renk"], a["boyut"])
            a.update(
                ad=ad.get().strip(), baslik=ust.get().strip() or "YouTube MP3",
                renk=secili["renk"], ozel_renk=secili["ozel"], tema=TEMALAR[tema.get()], boyut=boyut.get(),
                dosya_adi=dosya.get(), playlist_klasor=bool(k_pk.get()), numara=bool(k_nu.get()),
                klasoru_ac=bool(k_ac.get()), bildirim=bool(k_bi.get()), ses=bool(k_se.get()),
                pano_otomatik=bool(k_pa.get()))
            ctk.set_appearance_mode(a["tema"])
            self.tema_sw.select() if ctk.get_appearance_mode() == "Dark" else self.tema_sw.deselect()
            p.destroy()
            if onceki != (a["ad"], a["baslik"], a["renk"], a["ozel_renk"], a["boyut"]):
                self.yeniden_baslat()
            else:
                a.kaydet()

        alt = ctk.CTkFrame(p, fg_color="transparent")
        alt.pack(fill="x", padx=16, pady=14)
        ctk.CTkButton(alt, text="Kaydet", height=38, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      font=ctk.CTkFont(size=14, weight="bold"), command=kaydet).pack(side="right")
        ctk.CTkButton(alt, text="Vazgeç", height=38, width=90, command=p.destroy, **IKINCIL).pack(
            side="right", padx=8)

    def yeniden_baslat(self):
        """Renk / boyut gibi değişiklikler için pencereyi yeniden kurar."""
        if self.calisiyor:
            self.ayar.kaydet()
            messagebox.showinfo("Kişiselleştir", "Değişiklikler indirme bitip program yeniden açılınca görünecek.")
            return
        self._ayarlari_topla()
        self.ayar.kaydet()
        self.destroy()
        komut = [sys.executable] if DONDURULMUS else [sys.executable, str(APP_DIR / "ytmp3.py")]
        if WINDOWS:
            subprocess.Popen(komut)
            sys.exit(0)
        os.execv(komut[0], komut)

    def _ayarlari_topla(self):
        self.ayar.update(kalite=self.kalite.get(), kapak=bool(self.kapak.get()))
        if self.ayar["mod"] == "pc":
            self.ayar["klasor"] = self.klasor.get().strip()

    # ---------- Olaylar ----------
    def tema_degistir(self):
        self.ayar["tema"] = "dark" if self.tema_sw.get() else "light"
        ctk.set_appearance_mode(self.ayar["tema"])

    def yapistir(self):
        try:
            metin = self.clipboard_get()
            mevcut = self.link_kutu.get("1.0", "end").strip()
            self.link_kutu.insert("end", ("\n" if mevcut else "") + metin.strip())
        except Exception:
            pass

    def klasor_sec(self):
        k = filedialog.askdirectory(initialdir=self.klasor.get() or str(Path.home()))
        if k:
            self.klasor.delete(0, "end")
            self.klasor.insert(0, k)

    def mod_degisti(self, mod):
        self.ayar["mod"] = mod
        self.mod.set("🔌 USB Bellek" if mod == "usb" else "💻 Bilgisayar")
        if mod == "usb":
            self.pc_satir.grid_forget()
            self.usb_satir.grid(row=5, column=0, columnspan=3, sticky="ew", padx=18, pady=(10, 0))
            self.usb_yenile()
        else:
            self.usb_satir.grid_forget()
            self.pc_satir.grid(row=5, column=0, columnspan=3, sticky="ew", padx=18, pady=(10, 0))

    def usb_yenile(self):
        self.usb_map = {f"{ad}  ({bos:.1f} GB boş)": yol for ad, yol, bos in usb_listesi()}
        degerler = list(self.usb_map) or ["USB bulunamadı – takıp Yenile'ye basın"]
        self.usb_secim.configure(values=degerler)
        self.usb_secim.set(degerler[0])

    def hedef_klasor(self):
        if self.ayar["mod"] == "usb":
            yol = self.usb_map.get(self.usb_secim.get())
            return str(Path(yol) / "YouTube MP3") if yol else None
        return self.klasor.get().strip() or varsayilan_klasor()

    def klasor_ac(self):
        k = self.hedef_klasor()
        if k:
            Path(k).mkdir(parents=True, exist_ok=True)
            dosya_ac(k)

    def _gecmisi_yukle(self):
        if self.ayar["gecmis"]:
            self.gecmis.configure(state="normal")
            self.gecmis.insert("end", "\n".join(self.ayar["gecmis"]) + "\n")
            self.gecmis.see("end")
            self.gecmis.configure(state="disabled")

    def panodan_otomatik(self):
        try:
            metin = self.clipboard_get().strip()
        except Exception:
            return
        if ("youtube.com/" in metin or "youtu.be/" in metin) and "\n" not in metin \
                and metin not in self.link_kutu.get("1.0", "end"):
            self.link_kutu.insert("1.0", metin)
            self.ui(durum="📋 Panodaki link otomatik eklendi")

    def log(self, metin):
        zaman = datetime.now().strftime("%d.%m %H:%M")
        metin = f"{zaman}  {metin}"
        self.ayar["gecmis"] = (self.ayar["gecmis"] + [metin])[-200:]

        def yaz():
            self.gecmis.configure(state="normal")
            self.gecmis.insert("end", metin + "\n")
            self.gecmis.see("end")
            self.gecmis.configure(state="disabled")
        self.after(0, yaz)

    def ui(self, durum=None, detay=None, oran=None):
        def guncelle():
            if durum is not None:
                self.durum.configure(text=durum[:90])
            if detay is not None:
                self.detay.configure(text=detay[:110])
            if oran is not None:
                self.cubuk.set(oran)
        self.after(0, guncelle)

    def baslat(self):
        linkler = [l.strip() for l in self.link_kutu.get("1.0", "end").splitlines() if l.strip()]
        if not linkler:
            self.ui(durum="⚠ Önce en az bir link girin")
            return
        hedef = self.hedef_klasor()
        if not hedef:
            self.ui(durum="⚠ USB bellek seçilmedi")
            return
        try:
            Path(hedef).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.ui(durum=f"⚠ Klasör oluşturulamadı: {e}")
            return
        self.ayar.update(kalite=self.kalite.get(), kapak=bool(self.kapak.get()))
        if self.ayar["mod"] == "pc":
            self.ayar["klasor"] = hedef
        self.ayar.kaydet()
        self.calisiyor, self.iptal = True, False
        self.indir_btn.configure(state="disabled", text="İndiriliyor...")
        self.iptal_btn.configure(state="normal")
        threading.Thread(target=self.calistir, args=(linkler, hedef), daemon=True).start()

    def iptal_et(self):
        self.iptal = True
        self.ui(durum="İptal ediliyor...")

    def calistir(self, linkler, hedef):
        basarili, hatali = 0, 0
        usb = self.ayar["mod"] == "usb" or PORTABLE

        def hook(d):
            if self.iptal:
                raise KeyboardInterrupt
            if d["status"] == "downloading":
                toplam = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                inen = d.get("downloaded_bytes", 0)
                hiz = d.get("speed") or 0
                if toplam:
                    self.ui(oran=inen / toplam,
                            detay=f"{inen / 1e6:.1f} / {toplam / 1e6:.1f} MB  ·  {hiz / 1e6:.2f} MB/s")
            elif d["status"] == "finished":
                self.ui(oran=1, detay="MP3'e dönüştürülüyor...")

        secenekler = self.ydl_secenekleri(hedef, hook, guvenli_ad=usb)

        for i, url in enumerate(linkler, 1):
            if self.iptal:
                break
            self.ui(durum=f"({i}/{len(linkler)}) Bilgi alınıyor...", oran=0, detay="")
            try:
                with YoutubeDL(secenekler) as ydl:
                    bilgi = ydl.extract_info(url, download=False)
                    girdiler = list(bilgi.get("entries") or [bilgi])
                    liste = len(girdiler) > 1 or bool(bilgi.get("entries"))
                    klasor = hedef
                    if liste and self.ayar["playlist_klasor"]:
                        klasor = os.path.join(hedef, sanitize_filename(
                            bilgi.get("title") or "Playlist", restricted=False, is_id=False))
                    for j, g in enumerate(girdiler, 1):
                        if self.iptal or g is None:
                            continue
                        on_ek = f"{j:02d} - " if liste and self.ayar["numara"] else ""
                        ydl.params["outtmpl"]["default"] = os.path.join(
                            klasor, on_ek.replace("%", "%%") + self._dosya_sablonu())
                        ek = f" [{j}/{len(girdiler)}]" if len(girdiler) > 1 else ""
                        baslik = g.get("title", "?")
                        self.ui(durum=f"({i}/{len(linkler)}){ek} {baslik}")
                        try:
                            ydl.process_ie_result(g, download=True)
                            basarili += 1
                            self.log(f"✔ {baslik}")
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            hatali += 1
                            self.log(f"✘ {baslik}: {str(e)[:120]}")
            except KeyboardInterrupt:
                self.log("■ İptal edildi")
                break
            except Exception as e:
                hatali += 1
                self.log(f"✘ {url}: {str(e)[:120]}")

        self.after(0, lambda: self.bitti(basarili, hatali, hedef))

    def ydl_secenekleri(self, hedef, kanca, guvenli_ad=False, kalite=None):
        islemciler = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                       "preferredquality": kalite or self.ayar["kalite"]},
                      {"key": "FFmpegMetadata"}]
        if self.ayar["kapak"]:
            islemciler.append({"key": "EmbedThumbnail"})
        secenekler = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(hedef, self._dosya_sablonu()),
            "postprocessors": islemciler,
            "writethumbnail": bool(self.ayar["kapak"]),
            "progress_hooks": [kanca],
            "windowsfilenames": guvenli_ad or WINDOWS,  # USB (FAT32) / telefon için güvenli dosya adları
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        if ffmpeg_yolu():
            secenekler["ffmpeg_location"] = ffmpeg_yolu()
        return secenekler

    def _dosya_sablonu(self):
        return DOSYA_ADLARI.get(self.ayar["dosya_adi"], "%(title)s") + ".%(ext)s"

    def bitti(self, basarili, hatali, hedef):
        self.ayar.kaydet()
        if basarili or hatali:
            ozet = f"{basarili} şarkı indirildi" + (f", {hatali} hata" if hatali else "")
            if self.ayar["bildirim"] and not WINDOWS and shutil.which("notify-send"):
                subprocess.Popen(["notify-send", "-i", "ytmp3", "-a", "YouTube MP3",
                                  "İndirme tamamlandı" if not hatali else "İndirme bitti", ozet])
            if self.ayar["ses"] and WINDOWS:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif self.ayar["ses"]:
                ses = "/usr/share/sounds/freedesktop/stereo/complete.oga"
                if Path(ses).exists() and shutil.which("paplay"):
                    subprocess.Popen(["paplay", ses])
                else:
                    self.bell()
            if self.ayar["klasoru_ac"] and basarili:
                dosya_ac(hedef)
        self.calisiyor = False
        self.indir_btn.configure(state="normal", text="⬇  MP3 Olarak İndir")
        self.iptal_btn.configure(state="disabled")
        self.cubuk.set(0)
        self.ui(durum=f"Bitti: {basarili} başarılı, {hatali} hatalı", detay=f"Kayıt yeri: {hedef}")
        if basarili and not hatali:
            self.link_kutu.delete("1.0", "end")

    def kapat(self):
        if getattr(self, "telefon", None):
            self.telefon.durdur()
        self._ayarlari_topla()
        self.ayar.kaydet()
        self.iptal = True
        self.destroy()


if __name__ == "__main__":
    if "--surum" in sys.argv:
        print(f"YouTube MP3 {VERSION} | yt-dlp {yt_dlp.version.__version__} ({yt_dlp.__file__})")
        sys.exit(0)
    Uygulama().mainloop()
