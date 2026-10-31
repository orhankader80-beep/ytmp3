#!/usr/bin/env python3
"""YouTube -> MP3 indirici (modern arayüz, USB / taşınabilir mod destekli)."""
import json
import subprocess
from datetime import datetime
import os
import shutil
import sys
import threading
import webbrowser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
LIB_DIR = APP_DIR / "lib"
PORTABLE = (APP_DIR / "PORTABLE").exists()
# Uygulama içinden indirilen yeni yt-dlp sürümü (yazılabilir yerde durur)
GUNCEL_DIR = APP_DIR if PORTABLE else Path.home() / ".local" / "share" / "ytmp3"
YTDLP_ZIP = GUNCEL_DIR / "yt-dlp.zip"
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
# Uygulamanın yeni sürümleri burada yayınlanır
DEPO = "orhankader80-beep/ytmp3"
SURUM_URL = f"https://raw.githubusercontent.com/{DEPO}/main/surum.json"

if LIB_DIR.is_dir():
    sys.path.insert(0, str(LIB_DIR))
if YTDLP_ZIP.is_file():
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

VERSION = "3.2"
CONFIG_FILE = (APP_DIR / "ayarlar.json") if PORTABLE else Path.home() / ".config" / "ytmp3" / "ayarlar.json"

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


def surum_tuple(v):
    return tuple(int(x) for x in str(v).split(".") if x.isdigit())


def uygulama_surumu_kontrol():
    """Yeni uygulama sürümü varsa bilgisini (dict) döndürür, yoksa None."""
    import urllib.request
    istek = urllib.request.Request(SURUM_URL, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(istek, timeout=15) as r:
        bilgi = json.loads(r.read().decode("utf-8"))
    return bilgi if surum_tuple(bilgi["surum"]) > surum_tuple(VERSION) else None


def uygulamayi_guncelle(bilgi):
    """Yeni sürümü indirip kurar. Başarılıysa True döndürür."""
    import urllib.request
    if PORTABLE:
        # USB kopyası: sadece program dosyası değiştirilir
        yeni = APP_DIR / "ytmp3.py.yeni"
        with urllib.request.urlopen(bilgi["py"], timeout=60) as r, open(yeni, "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(yeni, APP_DIR / "ytmp3.py")
        os.sync()
        return True
    onbellek = Path.home() / ".cache" / "ytmp3"
    onbellek.mkdir(parents=True, exist_ok=True)
    deb = onbellek / f"ytmp3_{bilgi['surum']}_all.deb"
    with urllib.request.urlopen(bilgi["deb"], timeout=120) as r, open(deb, "wb") as f:
        shutil.copyfileobj(r, f)
    if shutil.which("pkexec"):
        # Şifre penceresi açılır, paket kurulur
        sonuc = subprocess.run(["pkexec", "apt-get", "install", "-y", "--reinstall", str(deb)],
                               capture_output=True, text=True)
        if sonuc.returncode == 0:
            return True
        if sonuc.returncode in (126, 127):  # şifre penceresi iptal edildi
            raise RuntimeError("Kurulum iptal edildi.")
        raise RuntimeError((sonuc.stderr or sonuc.stdout).strip()[-400:])
    # pkexec yoksa Pardus paket kurucusunu aç
    subprocess.Popen(["xdg-open", str(deb)])
    return False


def ytdlp_guncelle():
    """En yeni yt-dlp'yi indirir. Yeni sürüm numarasını döndürür."""
    import urllib.request
    GUNCEL_DIR.mkdir(parents=True, exist_ok=True)
    gecici = YTDLP_ZIP.with_suffix(".tmp")
    with urllib.request.urlopen(YTDLP_URL, timeout=60) as r, open(gecici, "wb") as f:
        shutil.copyfileobj(r, f)
    import zipfile
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
    if hedef.exists():
        shutil.rmtree(hedef / "lib", ignore_errors=True)
    hedef.mkdir(parents=True, exist_ok=True)
    shutil.copy2(APP_DIR / "ytmp3.py", hedef / "ytmp3.py")
    if LIB_DIR.is_dir():
        shutil.copytree(LIB_DIR, hedef / "lib", ignore=shutil.ignore_patterns("__pycache__"))
    if YTDLP_ZIP.is_file():
        shutil.copy2(YTDLP_ZIP, hedef / "yt-dlp.zip")
    (hedef / "PORTABLE").write_text("")
    (hedef / "BASLAT.sh").write_text(BASLAT_SH, encoding="utf-8")
    (hedef / "NASIL_ACILIR.txt").write_text(
        "Bu USB'yi herhangi bir Pardus / Linux bilgisayara takın.\n"
        "YTMP3 klasöründe sağ tık > 'Terminalde aç' deyip şunu yazın:\n\n"
        "    bash BASLAT.sh\n\n"
        "İndirilen müzikler USB'deki 'Muzikler' klasörüne kaydedilir.\n", encoding="utf-8")
    (Path(usb_yolu) / "Muzikler").mkdir(exist_ok=True)
    os.sync()
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
    """Taşınabilir modda USB'deki ffmpeg'i kullan (BASLAT.sh çalıştırılabilir kopya hazırlar)."""
    kopya = os.environ.get("YTMP3_FFMPEG")
    if kopya and Path(kopya).exists():
        return kopya
    return None


class Ayarlar(dict):
    def __init__(self):
        super().__init__(
            tema="dark", kalite="192", kapak=True, klasor=varsayilan_klasor(), mod="pc",
            renk="Kırmızı", ozel_renk="", ad="", baslik="YouTube MP3", boyut="Normal",
            dosya_adi="Şarkı adı", playlist_klasor=True, numara=True,
            bildirim=True, ses=True, klasoru_ac=False, pano_otomatik=True, gecmis=[])
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
        if not PORTABLE:
            ctk.CTkButton(bar, text="🔌 USB'ye taşı", width=120, command=self.usb_tasi, **IKINCIL).pack(side="right")

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
                tamam = uygulamayi_guncelle(bilgi)
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("Güncelleme", f"Kurulamadı:\n{err}"))
                self.ui(durum="⚠ Güncelleme kurulamadı", detay=err)
                self.after(0, self._guncelle_btn_normal)
                return
            if tamam:
                def bitir():
                    messagebox.showinfo("Güncelleme", f"Sürüm {bilgi['surum']} kuruldu!\nProgram yeniden açılıyor.")
                    self.yeniden_baslat()
                self.after(0, bitir)
            else:
                self.ui(durum="Kurulum penceresi açıldı", detay="Kurduktan sonra programı yeniden açın")
                self.after(0, self._guncelle_btn_normal)
        threading.Thread(target=is_, daemon=True).start()

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
        k_bi = kutu(o, 0, "Bitince masaüstü bildirimi göster", "bildirim")
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
        os.execv(sys.executable, [sys.executable, str(APP_DIR / "ytmp3.py")])

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
            webbrowser.open(Path(k).as_uri())

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

        islemciler = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                       "preferredquality": self.ayar["kalite"]},
                      {"key": "FFmpegMetadata"}]
        if self.ayar["kapak"]:
            islemciler.append({"key": "EmbedThumbnail"})
        secenekler = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(hedef, self._dosya_sablonu()),
            "postprocessors": islemciler,
            "writethumbnail": bool(self.ayar["kapak"]),
            "progress_hooks": [hook],
            "windowsfilenames": usb,  # USB (FAT32) için güvenli dosya adları
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        if ffmpeg_yolu():
            secenekler["ffmpeg_location"] = ffmpeg_yolu()

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

    def _dosya_sablonu(self):
        return DOSYA_ADLARI.get(self.ayar["dosya_adi"], "%(title)s") + ".%(ext)s"

    def bitti(self, basarili, hatali, hedef):
        self.ayar.kaydet()
        if basarili or hatali:
            ozet = f"{basarili} şarkı indirildi" + (f", {hatali} hata" if hatali else "")
            if self.ayar["bildirim"] and shutil.which("notify-send"):
                subprocess.Popen(["notify-send", "-i", "ytmp3", "-a", "YouTube MP3",
                                  "İndirme tamamlandı" if not hatali else "İndirme bitti", ozet])
            if self.ayar["ses"]:
                ses = "/usr/share/sounds/freedesktop/stereo/complete.oga"
                if Path(ses).exists() and shutil.which("paplay"):
                    subprocess.Popen(["paplay", ses])
                else:
                    self.bell()
            if self.ayar["klasoru_ac"] and basarili:
                webbrowser.open(Path(hedef).as_uri())
        self.calisiyor = False
        self.indir_btn.configure(state="normal", text="⬇  MP3 Olarak İndir")
        self.iptal_btn.configure(state="disabled")
        self.cubuk.set(0)
        self.ui(durum=f"Bitti: {basarili} başarılı, {hatali} hatalı", detay=f"Kayıt yeri: {hedef}")
        if basarili and not hatali:
            self.link_kutu.delete("1.0", "end")

    def kapat(self):
        self._ayarlari_topla()
        self.ayar.kaydet()
        self.iptal = True
        self.destroy()


if __name__ == "__main__":
    Uygulama().mainloop()
