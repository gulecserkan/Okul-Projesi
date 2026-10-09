# DEVIR.md — Kütüphane Sistemini Yeni Bilgisayara Taşıma ve Kurulum

Bu belge, bu projeyi **kütüphanedeki bilgisayarda** (eski kütüphane sisteminin
çalıştığı makine) sürdürecek kişi için hazırlandı. Kurulum adımlarını, taşınacak
dosyaları ve **eski sistemle çakışma analizini** içerir.

---

## 1. Mimari ve çakışma analizi (ÖNCE BUNU OKU)

Sistem üç parçadan oluşur:

| Parça | Teknoloji | Nerede çalışır |
|---|---|---|
| Backend + API | Django + DRF + PostgreSQL | Sunucu (`okulkitapligi.tr` / `89.252.153.171`) |
| Masaüstü istemci | Flutter (Linux) | Kütüphane bilgisayarı |
| Mobil istemci | Flutter (Android) | Telefonlar |

**Altın kural (AGENTS.md):** İstemciler **veritabanına değil, API'ye** bağlanır.

### Senaryo A — Veritabanı/sunucu uzakta (ÖNERİLEN, çakışma YOK)

Kütüphane bilgisayarına **yalnızca masaüstü istemci** kurulur; istemci
`https://okulkitapligi.tr/api` adresine bağlanır.

- Yerelde PostgreSQL/Django/nginx **kurulmaz** → eski sistemle hiçbir çakışma yok.
- Eski sistem hangi portu/DB'yi kullanıyorsa **hiç etkilenmez**.
- Eski sistem çalışmaya devam ederken yeni istemci paralel denenebilir.

> Geçiş tamamlanınca eski sistem kapatılır; o güne kadar ikisi de çalışabilir.

### Senaryo B — Yerel backend (yalnız test/geliştirme için)

Yerelde Django + PostgreSQL çalıştırılacaksa eski sistemle şu noktalar **çakışabilir**:

| Kaynak | Eski sistem (kontrol et) | Yeni sistem varsayılanı | Çakışma riski | Çözüm |
|---|---|---|---|---|
| PostgreSQL DB adı | `kutuphane` olabilir | `kutuphane` | **YÜKSEK** | Yeni DB adı: **`kutuphane_yeni`** |
| PostgreSQL kullanıcısı | `kutuphane`/başka | `kutuphane` | orta | Yeni kullanıcı: **`kutuphane_yeni`** |
| PostgreSQL portu | 5432 | 5432 | düşük | Aynı küme paylaşılır; **DB adı farklıysa sorun yok** |
| Gunicorn/Django | ? | `127.0.0.1:8000` | orta | Yeni sistem: **`127.0.0.1:8002`** |
| nginx (80/443) | kullanıyor olabilir | 80 | orta | Tek nginx; **yeni sistem ayrı `server_name` bloğu**; eski bloğa dokunma |
| systemd servis adı | ? | `kutuphane-backend` | orta | Yeni: **`kutuphane-yeni-backend`** |
| Uygulama config'i | ? | `~/.config/kutuphane_masaustu/` | düşük | Çakışırsa ad değiştir |
| Python/Flutter/opencode | — | — | **yok** | Ayrı kurulumlar, çakışmaz |

**ÇOK ÖNEMLİ:** `kutuphane/scripts/geri-yukle.sh` (`pg_restore --clean`) ve
`kutuphane/scripts/eski_veri_aktar.sh` **mevcut nesneleri siler**. Bu betikleri
**asla eski sistemin veritabanı adına** yöneltme. `DB_NAME` daima ayrı olmalı
(`kutuphane_yeni`).

**Sonuç / öneri:** Kütüphane bilgisayarında geçiş tamamlanana kadar **Senaryo A**
(yalnız istemci) uygula. Yerel backend gerekiyorsa **Senaryo B** kurallarına uy:
ayrı DB adı + ayrı port + ayrı servis adı.

---

## 2. Taşınacaklar

| Öğe | Git'te mi? | Nasıl taşınır |
|---|---|---|
| Proje kodu | ✅ evet | `git clone` |
| `kutuphane/.env` (DB şifresi, Google anahtarı) | ❌ **hayır (gizli)** | elle kopyala |
| `~/.ssh/id_ed25519` (GitHub) | ❌ gizli | elle kopyala |
| `~/.ssh/kutuphane` + `~/.ssh/config` (`cenuta`, `github-enes`) | ❌ gizli | elle kopyala |
| opencode sohbet geçmişi | ❌ | `~/.local/share/opencode` + `~/.config/opencode` |
| `~/.local/share/opencode/auth.json` (Groq/Google anahtarı) | ❌ gizli | elle kopyala |
| Masaüstü yazıcı ayarları | ❌ | `~/.config/kutuphane_masaustu/config.json` |
| `masaustu/flutter_0*.png` | commit'siz | gerekmiyor (ekran görüntüsü) |

> Gizli dosyaları (`.env`, `auth.json`, SSH anahtarları) `scp` veya şifreli bir
> ortamla taşı. Masaüstü **uygulaması** ayrıca taşınmaz; sunucudan internet
> üzerinden kurulur (bkz. 3.7).

---

## 3. Kurulum adımları

### 3.1 opencode + sohbet geçmişi

```bash
curl -fsSL https://opencode.ai/install | bash
opencode --version          # 1.18.x beklenir
```

Aynı sohbeti sürdürmek için (opencode **kapalıyken**) eski makineden kopyala:
- `~/.local/share/opencode` (opencode.db ~250 MB + storage/plans/tool-output)
- `~/.config/opencode` (`opencode.jsonc`, `skill/`; `node_modules` kopyalanmasa da olur)

> Aynı kullanıcı adı/ev yolu olursa birebir çalışır. Farklı kullanıcı adıysa
> sohbet yine açılır ama geçmişteki yollar eskiye işaret eder.

Yeni oturum başlatmak istenirse: geçmişi taşımadan `opencode` aç, Bölüm 8'deki
metni ilk mesaj olarak yapıştır.

### 3.2 Git + repo

```bash
git clone git@github.com:gulecserkan/Okul-Projesi.git
cd Okul-Projesi && git checkout V2.0
git log --oneline -1        # 5b9dd52 (1.1.15) beklenir
```

GitHub anahtarı yoksa: `~/.ssh/id_ed25519` (+ `.pub`) ve `~/.ssh/config` kopyala.

### 3.3 Flutter SDK 3.47.5 (masaüstü derlemesi için)

```bash
git clone https://github.com/flutter/flutter.git -b stable ~/development/flutter
cd ~/development/flutter && git checkout 6a19cca564    # sürüm 3.47.5
echo 'export PATH="$HOME/development/flutter/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc && flutter --version

# Linux masaüstü derleme bağımlılıkları
sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev

cd ~/Okul-Projesi/masaustu
flutter doctor                 # Linux toolchain yeşil olmalı
flutter pub get
flutter analyze
flutter test                   # 117 test beklenir
flutter build linux --release
```

### 3.4 Python 3.13 + venv (backend)

```bash
sudo apt install -y python3 python3-venv python3-dev build-essential libpq-dev

cd ~/Okul-Projesi/kutuphane
python3 -m venv venv
venv/bin/pip install -U pip
venv/bin/pip install -r requirements.txt

# .env dosyasını (gizli) buraya koy: kutuphane/.env
```

`kutuphane/.env` içeriği (değerleri eski makineden al):

```ini
DEBUG=true
DB_NAME=kutuphane_yeni
DB_USER=kutuphane_yeni
DB_PASSWORD=<güçlü-parola>
DB_HOST=localhost
DB_PORT=5432
GOOGLE_BOOKS_API_KEY=<anahtar>
```

### 3.5 PostgreSQL (yalnız YEREL backend için — Senaryo B)

```bash
sudo apt install -y postgresql
sudo systemctl enable --now postgresql
pg_lsclusters                  # port 5432 online mı?

# ESKİ SİSTEMDEN AYRI isimler kullan:
sudo -u postgres psql -c "CREATE USER kutuphane_yeni WITH PASSWORD '<parola>';"
sudo -u postgres psql -c "CREATE DATABASE kutuphane_yeni OWNER kutuphane_yeni;"

cd ~/Okul-Projesi/kutuphane
venv/bin/python manage.py migrate
venv/bin/python manage.py createsuperuser    # gerekirse
venv/bin/python manage.py runserver 127.0.0.1:8002 --noreload
```

> Sunucudan canlı verinin kopyasını yüklemek istersen: sunucuda
> `sudo -u postgres pg_dump -Fc kutuphane > yedek.dump`, yerelde
> `venv/.../pg_restore` ile **`kutuphane_yeni`** DB'sine yükle. Asla eski
> sistemin DB adına yükleme.

### 3.6 nginx + gunicorn (yalnız YEREL sunucu kurulacaksa)

Ubuntu/Debian'da tek nginx vardır; eski sistem de kullanıyorsa **mevcut site
bloğuna dokunmadan** yeni bir blok ekle (`/etc/nginx/sites-available/yeni-kutuphane`),
`server_name okulkitapligi.tr;` ile ayır. Gunicorn'u **`127.0.0.1:8002`** bağla.
Ayrıntı: `docs/DEPLOY_CLOUD.md` (Bölüm 7–8), ama servis adı ve portu
**çakışmayacak** şekilde değiştir.

### 3.7 Masaüstü istemci kurulumu (İNTERNET üzerinden)

İstemci, sunucunun servis ettiği paketten **internet üzerinden** kurulur;
USB/kopya gerekmez. Hedef bilgisayarda tek komut:

```bash
# Alan adı + HTTPS hazır olduğunda:
curl -fsSL https://okulkitapligi.tr/masaustu/uzaktan-kur.sh | bash

# HTTPS henüz yoksa IP ile (HTTP):
curl -fsSL http://89.252.153.171/masaustu/uzaktan-kur.sh | bash
```

Betik paketi indirir, `~/.local/share/kutuphane-masaustu` altına kurar, menü ve
masaüstü kısayolunu yazar. **Uygulama açılışta yeni sürümü sunucudan otomatik
günceller**; sonraki güncellemeler için yeniden kurulum gerekmez.

Kurulum sonrası:
- Giriş ekranından sunucu adresi:
  - Üretim: `https://okulkitapligi.tr/api`
  - Yerel test: `http://127.0.0.1:8002/api`
- Yazıcı/rolo ayarları **her bilgisayarda ayrı** yapılır
  (`~/.config/kutuphane_masaustu/config.json`).

> Geliştirme için kaynaktan derleme Bölüm 3.3'teki Flutter adımlarıyla yapılır;
> saha bilgisayarlarında gerek yoktur.

---

## 4. Ön kontrol taraması (kurulumdan ÖNCE, salt okunur)

Eski sistemi bozmamak için önce ne çalıştığını tespit et:

```bash
# PostgreSQL kümeleri / portları
pg_lsclusters
sudo -u postgres psql -c "\l"                     # mevcut DB adları
sudo -u postgres psql -c "\du"                    # mevcut kullanıcılar

# Dinlenen portlar
sudo ss -ltnp | grep -E ':80 |:443 |:8000 |:8001 |:8002 |:5432 '

# Servisler
systemctl list-units --type=service --all | grep -iE 'kutuphane|gunicorn|nginx|postgres'

# nginx
ls -l /etc/nginx/sites-enabled/

# Araçlar ve disk
command -v flutter python3 psql nginx node npm opencode || true
df -h /
```

Bu tarama sonucu Bölüm 1'deki tabloyu netleştirir. **Eski sistemin DB adı
öğrenilmeden hiçbir yere `--clean` geri yükleme yapılmaz.**

---

## 5. Doğrulama

```bash
# Backend (yerel)
curl -s http://127.0.0.1:8002/api/health/
cd Okul-Projesi/kutuphane && venv/bin/python manage.py test kutuphane_app

# Masaüstü
cd Okul-Projesi/masaustu && flutter analyze && flutter test

# Üretim
curl -s https://okulkitapligi.tr/api/health/
```

---

## 6. Mevcut durum (bu not yazılırken)

- Sürüm: **1.1.16** · dal `V2.0` (GitHub'a push edildi). Önceki: `5b9dd52` (1.1.15).
- Masaüstü testleri: **118/118** · analyze temiz (mobil sunucu adresi testleri dahil)
- Üretim sunucu: `89.252.153.171`, PostgreSQL `kutuphane` (~13 MB), günlük
  şifreli yedek + media arşivi çalışıyor. **Prod'a dokunulmadı.**
- Alan adı: `okulkitapligi.tr` (+`www`) → `89.252.153.171` A kayıtları Alastyr
  panelinden eklendi; DNS çözümü aktif.
- **HTTPS tamam:** Let's Encrypt/certbot (`CN=okulkitapligi.tr`, bitiş 2027-01-07,
  `certbot.timer` otomatik yenileme), nginx `server_name` + HTTP→HTTPS 301, `.env`
  `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` + güvenli çerezler. `https://.../api/health/` 200.
- Yerel tam sistem testi (backend + DB + istemci) henüz yapılmadı.
- Bekleyen: A4 rozet → 1.1.15 ile çözüldü; etiket kalibrasyon yönergesi (1.1.15);
  HTTPS'e garanti geçiş → 1.1.16 ile çözüldü.

## 7. Açık işler

1. ~~DNS kaydı~~ → yapıldı (Alastyr A kayıtları).
2. ~~HTTPS (nginx `server_name`, certbot, `.env`)~~ → yapıldı.
3. ~~İstemci adres önceliği `https://okulkitapligi.tr` + yayın~~ → 1.1.16 ile yapıldı.
4. Yerelde uçtan uca test (Senaryo B kurallarıyla) → sonra geçiş kararı.
5. Android `usesCleartextTraffic` daraltma + Play hazırlık (K13.12).

---

## 8. Yeni opencode oturumu için başlangıç metni

> Aşağıdaki metni yeni makinede opencode'un **ilk mesajı** olarak yapıştır.

Merhaba. Kütüphane Yönetim Sistemi'ni kütüphanedeki bilgisayarda sürdüreceğiz.
Monorepo: `~/Okul-Projesi`, dal `V2.0`, son sürüm `1.1.16`.
**Önce `docs/DEVIR.md`, `AGENTS.md`, `docs/IS_KURALLARI.md` ve
`docs/DEPLOY_CLOUD.md` dosyalarını oku.** Bu makinede **eski kütüphane sistemi
çalışıyor**; ona zarar vermeden ilerle. Varsayılan olarak **Senaryo A** (yalnız
masaüstü istemci, backend uzakta) uygula; yerel backend gerekiyorsa DEVIR.md
Bölüm 1'deki ayrı DB adı/port/servis kurallarına uy. Geri yükleme (`--clean`)
içeren hiçbir komutu **eski sistemin veritabanına** yöneltme. Kritik komutlardan
önce kısa açıkla ve onay al. İlk iş: `docs/DEVIR.md` Bölüm 4'teki ön kontrol
taramasını çalıştırıp makinedeki mevcut DB/port/servisleri raporla.
