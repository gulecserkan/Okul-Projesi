# 05. Yönetim — Admin Paneli, Deployment, Güvenlik

## 1. Admin Paneli (`/admin/`)

Özel `CustomAdminSite` (`kutuphane_app/admin.py:118`) — `/admin/` adresinde çalışır. Başlık: "Kütüphane Yönetim Sistemi".

### Sistem Araçları (özel URL'ler)
| Rota | Fonksiyon |
|---|---|
| `/admin/system/ayarlar/` | Hub sayfası: Yedekle / Geri Yükle butonları (`admin/system_settings.html`) |
| `/admin/system/backup/` | `dumpdata` (contenttypes, auth.permission, admin.logentry, sessions hariç) → şifreli `backups/backup_YYYYMMDD_HHMMSS.json.enc` (FerNet; kişisel veriler düz metin içerdiği için) → aynı şifreli dosya indirilir |
| `/admin/system/restore/` | Geri yükleme akışı: `EVET` + 6 haneli güvenlik kodu; `.json.enc` (şifresi çözülür) veya eski düz metin `.json` yüklenir/seçilir → `flush` + `loaddata` (**tüm veri silinir**). Seçilen dosya `backups/` diziniyle sınırlıdır (path traversal koruması) |

### Kayıtlı Modeller ve Özel Alanlar
- **Rol** listesi: bağlı `loan_policy` değerlerini gösterir (süre, max kitap, günlük ceza).
- **Üye** (`ImportExportModelAdmin`): CSV/JSON içe-dışa aktarma (`uye_no,ad,soyad,sinif,rol`; UTF-8; başlık satırı zorunlu; virgül ayraçlı, tırnaksız). CSV'de olmayan üyeleri pasife çekmek **varsayılan olarak kapalıdır**; yalnızca "tam yoklama senkronu" bilinçli yapılırken `UyeResource.pasiflestir=True` ile açılır (kısmi CSV yüklerken sınıf listesi dışındakiler silinmesin diye).
- **Arşivleme** (Öğrenci değişiklik listesinden): kriter = `aktif=False` VE (pasif_tarihi 3+ yıl önce VEYA pasif_tarihi boşsa kayıt_tarihi 3+ yıl önce). Onayda transaction içinde `ArsivBatch` + `ArsivUye` + `ArsivOdunc` oluşturulur, JSON paket kaydedilir, **canlı öğrenci ve ödünç kayıtları silinir**.
- **Kullanıcılar (User)**: Personel/operatör hesapları standart Django **Users** admin'inden yönetilir; admin = `is_superuser`. `Personel` tablosu kaldırılmıştır.
- **Sayım Oturumu**: kalemleri salt-okunur inline.
- **LoanPolicy / RoleLoanPolicy / NotificationSettings**: listelenir, sistem ayarları olmayan alanlar düzenlenebilir.

### Şablonlar (`kutuphane/templates/admin/`)
- `index.html` — Sistem Araçları modülü ekler.
- `ogrenci_change_list.html` — "Arşive Taşı (ön izleme)" butonu.
- `system_settings.html`, `system_restore_form.html` — backup/restore arayüzü.
- `ogrenci_arsiv_onizleme.html` — arşiv ön izleme + onay.
- `import_export/export.html` — Türkçe etiketli dışa aktarma sayfası.

> Not: Eski `system_restore_start/confirm/code.html` şablonları kaldırıldı; güncel akış tek form (`system_restore_form.html`).

## 2. Deployment

Detaylı rehber: `kutuphane/django_deployment_checklist.md` ve `kutuphane/SERVER_SETUP.md`.

### Sunucu Ayarı (`setup_backend_service.sh`)
- `.env` içinden okunur: `/etc/kutuphane/.env` ve sonra `<proje>/kutuphane/.env` (yoksa varsayılanlar).
- Gunicorn WSGI; WhiteNoise statik dosyaları servis eder; `collectstatic` gerekir.
- Cron: `/etc/cron.d/kutuphane-scheduler` → `python manage.py run_scheduled_tasks` her 15 dk.

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

### Bazı Önemli Ayarlar
- `LANGUAGE_CODE = 'tr'`, `TIME_ZONE = 'Europe/Istanbul'`, `USE_TZ = True`.
- DRF: `IsAuthenticated` global, `JWTAuthentication` global.
- `MEDIA_ROOT` → `kutuphane/media`; `STATIC_ROOT` → `kutuphane/staticfiles`.

## 3. Güvenlik

- **API**: Tüm uçlar JWT korumalı; yalnızca `health` açık. Öğrenci bilgileri yetkisiz erişime kapalı (masaüstü/mobil istemciler token ile konuşur).
- **Admin**: Django session kimliği; admin = `is_superuser`; operatör/giriş hesapları Django `User`'dır.
- **Restore**: `EVET` + dinamik 6 haneli kod — yanlışlıkla veri kaybını önler; kullanılmış/geçersiz kodlar reddedilir; dosya seçimi `backups/` ile sınırlıdır. Yine de **yıkıcıdır** (flush sonrası load).
- **Header temizliği**: `SafeHeaderMiddleware` ASCII olmayan/çok satırlı header değerlerini temizler (masaüstü `requests` istemcisinin RecursionError vermemesi için).
- **Şifreler**: Django `make_password`/`check_password` (tek kaynak: `User.password`).
- **Yedekleme**: Disk ve indirilen dosya **şifrelidir** (`.json.enc`); şifreleme anahtarı `.env`'de sağlanır. Eski düz metin `.json` yedekler restore'da hâlâ kabul edilir.
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