# 05. Yönetim — Admin Paneli, Deployment, Güvenlik

## 1. Admin Paneli (`/admin/`)

Özel `CustomAdminSite` (`kutuphane_app/admin.py`) — `/admin/` adresinde çalışır. Başlık: "Kütüphane Yönetim Sistemi".

### Yedekleme (pg_dump + cron)
Admin panelde yedekle/geri yükle arayüzü **yoktur**; yedekleme sunucu tarafında `pg_dump` ile yapılır:
- `scripts/yedekle.sh [prod|staging]` → `pg_dump -Fc` + `openssl` (AES-256-CBC/PBKDF2) → `/var/backups/kutuphane/kutuphane_<ortam>_<zaman>.dump.enc`; varsayılan 14 gün saklama.
- Zamanlama: `/etc/cron.d/kutuphane-yedek` (kaynak: `scripts/cron.d/kutuphane-yedek`) → her gün 03:30.
- Geri yükleme: `scripts/geri-yukle.sh <yedek.dump.enc> [prod|staging]` → `pg_restore --clean --if-exists --no-owner`.
- Gereksinim: `/etc/kutuphane/.env` içinde `DB_*` ve `YEDEK_SIFRE` tanımlı olmalı.

### Kayıtlı Modeller ve Özel Alanlar
- **Rol** listesi: bağlı `loan_policy` değerlerini gösterir (süre, max kitap, günlük ceza).
- **Üye**: liste/arama/filtre + kayıt düzenleme. Toplu öğrenci girişi **masaüstü K9.13** ile yapılır; admin panelde içe/dışa aktarma **yoktur** (tek aktarım yolu K9.13).
- **Arşivleme** (Öğrenci değişiklik listesinden): kriter = `aktif=False` VE (pasif_tarihi 3+ yıl önce VEYA pasif_tarihi boşsa kayıt_tarihi 3+ yıl önce). Onayda transaction içinde `ArsivBatch` + `ArsivUye` + `ArsivOdunc` oluşturulur, JSON paket kaydedilir, **canlı öğrenci ve ödünç kayıtları silinir**.
- **Kullanıcılar (User)**: Personel/operatör hesapları standart Django **Users** admin'inden yönetilir; admin = `is_superuser`. `Personel` tablosu kaldırılmıştır.
- **Sayım Oturumu**: kalemleri salt-okunur inline.
- **LoanPolicy / RoleLoanPolicy / NotificationSettings**: listelenir, sistem ayarları olmayan alanlar düzenlenebilir.

### Şablonlar (`kutuphane/templates/admin/`)
- `uye_change_list.html` — "Arşive Taşı (ön izleme)" butonu.
- `uye_arsiv_onizleme.html` — arşiv ön izleme + onay.

### Yönetim Yüzü Sınırı
- **Masaüstü** — günlük operasyon: kitap/nüsha, ödünç/iade, üye yönetimi ve **dönem başı toplu öğrenci aktarımı** (K9.13; Ayarlar → Öğrenci Aktarımı, yalnız admin).
- **Admin paneli** — nadiren değişen/bakım işleri: ayar tabloları (Sinif, Rol, LoanPolicy, RoleLoanPolicy, NotificationSettings, KurumAyarlari), kullanıcılar, arşivleme.
- **Yedekleme** — `pg_dump` + cron (sunucu tarafı; admin arayüzü yok).

## 2. Deployment

Detaylı rehber: `kutuphane/django_deployment_checklist.md` ve `kutuphane/SERVER_SETUP.md`.

### Sunucu Ayarı (`setup_backend_service.sh`)
- `.env` içinden okunur: `/etc/kutuphane/.env` ve sonra `<proje>/kutuphane/.env` (yoksa varsayılanlar).
- Gunicorn WSGI; WhiteNoise statik dosyaları servis eder; `collectstatic` gerekir.
- Cron: `/etc/cron.d/kutuphane-scheduler` → `python manage.py run_scheduled_tasks` her 15 dk.

### Eski Veri Aktarımı (tek seferlik)
Eski sistemden yalnız **katalog** aktarılır (Yazar/Kategori/Kitap/KitapNusha/Raf + Rol/RoleLoanPolicy/LoanPolicy); üye/ödünç/arşiv/personel aktarılmaz (öğrenciler masaüstü K9.13 ile eklenir).
1. Eski makinede: `sudo -u postgres pg_dump <db> -Fc -f /tmp/kutuphane_eski.dump` → dosyayı hedefe kopyala.
2. Aktarım (`scripts/eski_veri_aktar.sh`, hedef DB'ye göre):
   - **Local:** `bash kutuphane/scripts/eski_veri_aktar.sh <dump> local`
   - **Sunucu:** dump'ı sunucuya kopyala → `sudo bash kutuphane/scripts/eski_veri_aktar.sh <dump> prod` (veya `staging`)
   Betik dump'ı geçici DB'ye (`<DB_NAME>_eski`) yükler, **dry-run raporu** gösterir, `EVET` onayıyla uygular, geçici DB'yi siler. Prod DB'ye istemciden bağlanılmaz; sunucuda çalıştırılır.
3. `manage.py eski_veri_aktar` **idempotenttir**: doğal anahtarlarla (barkod, ad, isbn veya başlık+yazar) eşleşen kayıtlar tekrar oluşturulmaz. Rol adları kanonikleştirilir (`öğrenci`→`Öğrenci`).
4. Eski `oduncte` nüshalar, ödünç geçmişi aktarılmadığından `mevcut`a çevrilir (`--odunctekileri-mevcut-yap`).

### Ortam Değişkenleri (`settings.py` `load_env`)
| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SECRET_KEY` | (güvensiz yedek) | Üretimde `.env`'den verilmeli; DEBUG=False iken boş bırakılırsa sunucu **başlamaz** (fail-fast) |
| `DEBUG` | false | `"true"` yalnızca geliştirmede |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Virgülle ayrık |
| `DB_NAME` | `kutuphane` | |
| `DB_USER` | `kutuphane` | |
| `DB_PASSWORD` | — | |
| `DB_HOST` | `localhost` | |
| `DB_PORT` | `5432` | |
| `FIELD_ENCRYPTION_KEY` | (yoksa `SECRET_KEY`) | Kişisel veri alan şifrelemesi anahtarı; ayrı tutulması önerilir (rotasyonda veriyi bozmaz) |
| `YEDEK_SIFRE` | — | `scripts/yedekle.sh` pg_dump yedeğini şifrelemek için (zorunlu); güçlü tutulmalı, paylaşılmamalı |

### Bazı Önemli Ayarlar
- `LANGUAGE_CODE = 'tr'`, `TIME_ZONE = 'Europe/Istanbul'`, `USE_TZ = True`.
- DRF: `IsAuthenticated` global, `JWTAuthentication` global.
- `MEDIA_ROOT` → `kutuphane/media`; `STATIC_ROOT` → `kutuphane/staticfiles`.

## 3. Güvenlik

- **API**: Tüm uçlar JWT korumalı; yalnızca `health` açık. Öğrenci bilgileri yetkisiz erişime kapalı (masaüstü/mobil istemciler token ile konuşur).
- **Admin**: Django session kimliği; admin = `is_superuser`; operatör/giriş hesapları Django `User`'dır.
- **Yedekleme**: Admin panelde yedek/geri yükle **yok**; `scripts/yedekle.sh` ile `pg_dump -Fc` alınır ve `openssl` (AES-256) ile şifrelenir (`YEDEK_SIFRE`). Geri yükleme `scripts/geri-yukle.sh` ile `pg_restore --clean` — **yıkıcıdır**, onay ister.
- **Header temizliği**: `SafeHeaderMiddleware` ASCII olmayan/çok satırlı header değerlerini temizler (masaüstü `requests` istemcisinin RecursionError vermemesi için).
- **Şifreler**: Django `make_password`/`check_password` (tek kaynak: `User.password`).
- **Yetki**: Admin = `is_superuser`; operatör = Uye bağı olmayan `User`; editör = `Uye.rol="Editör"` (kitap düzenleme). Üye uçları salt-okunur ve kendine ait.

## 4. Veritabanı (PostgreSQL) Kurulumu
```sql
CREATE DATABASE kutuphane;
CREATE USER kutuphane_user WITH PASSWORD '...';
ALTER ROLE kutuphane_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE kutuphane TO kutuphane_user;
```
Sonra `python manage.py migrate` ve `createsuperuser`.

## 5. Fixture'lar
- `ilk_veri.json` / `odunc_veri.json` — örnek veri (120 öğrenci, 180+ nüsha, 160 ödünç).
- `generate_fixture.py` — `ilk_veri.json`'u **yeni şemaya** göre yeniden üretir (rol + roleloanpolicy dahil).
- `generate_odunc_fixture.py` — Django kurulu ve veri yüklü DB için ödünç fixture'ı üretir.
- ⚠️ Depodaki `ilk_veri.json` **eski şema** (rol'da `odunc_suresi_gun` vs. alanları var) — mevcut modele yüklenemez. Düzeltmek için `generate_fixture.py` çalıştırılmalı.

## 6. Test
- `kutuphane_app/tests.py`: 16 çekirdek test — ödünç politikası, checkout akışı, barkod üretimi, alan şifreleme, personel yetkileri.
- `python manage.py test` ile çalıştırılır (test DB için PostgreSQL kullanıcısının `CREATEDB` yetkisi gerekir).
- Ayrıntılı test planı dosyası: `kutuphane_backend_test_plan.xlsx`.