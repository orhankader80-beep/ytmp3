# 🎵 YouTube MP3

YouTube videolarını ve playlist'leri MP3 olarak indiren, modern arayüzlü program.
**Windows** ve **Pardus / Linux**'ta çalışır; **iPhone ve Android**'den de kullanılabilir.

## İndir

👉 **[En son sürümün indirme sayfası](https://github.com/orhankader80-beep/ytmp3/releases/latest)**

| Cihaz | Hangi dosya | Nasıl kurulur |
|---|---|---|
| 🪟 Windows | `YouTubeMP3-Kurulum.exe` | Çift tıkla, **Kur**'a bas |
| 🪟 Windows (USB) | `YouTubeMP3-Tasinabilir-Windows.zip` | Zip'i USB'ye çıkar, `YouTube MP3.exe`'ye çift tıkla |
| 🐧 Pardus / Linux | `ytmp3_X.X_all.deb` | Çift tıkla, **Kur**'a bas (Pardus 23+) |
| 📱 iPhone / Android | — | Bilgisayardaki programda **📱 Telefon**'a bas, QR kodu okut |

> Windows ilk açılışta "Windows kişisel bilgisayarınızı korudu" diyebilir:
> **Ek bilgi → Yine de çalıştır**'a basın. (Program imzalı olmadığı için çıkar.)

## Özellikler

- Tek video veya playlist indirme, 128–320 kbps kalite
- MP3'e kapak resmi ve şarkı bilgisi ekleme
- 📱 Telefondan kullanma: aynı Wi-Fi'deki telefondan link gönder, MP3 telefona insin
- MP3'leri doğrudan USB belleğe kaydetme, USB'ye taşınabilir kopya oluşturma
- Kişiselleştirme: renk, tema, yazı boyutu, adınla karşılama, dosya adı biçimi
- 🔄 Güncelle butonu: hem programı hem indirme motorunu günceller

## Geliştirici için

- Yeni sürüm: `ytmp3.py` içinde `VERSION` ve `YENILIKLER`'i değiştir, sonra `bash paket/yayinla.sh`.
  GitHub Actions Linux `.deb` ve Windows `.exe` dosyalarını derleyip yayınlar, `surum.json`'u günceller.
- `paket/deb_olustur.sh` — .deb paketini yerelde oluşturur
- `paket/kurulum.iss` — Windows kurulum programı (Inno Setup)

Not: Yalnızca indirme hakkınız olan içerikler için kullanın.
