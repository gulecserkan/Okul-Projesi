# 05. Yönetim — Admin Paneli, Deployment, Güvenlik

## 1. Admin Paneli (`/admin/`)

Özel `CustomAdminSite` (`kutuphane_app/admin.py:118`) — `/admin/` adresinde çalışır. Başlık: "Kütüphane Yönetim Sistemi".

### Sistem Araçları (özel URL'ler)
| Rota | Fonksiyon |
|---|---|
| `/admin/system/ayarlar/` | Hub sayfası: Yedekle / Geri Yükle butonları (`admin/system_settings.html`) |
| `/admin/system/backup/` | `dumpdata` (contenttypes, auth.permission, admin.logentry, sessions hariç) → `backups/backup_YYYYMMDD_HHMMSS.json` → dosya indirilir |
| `/admin/system/restore/` | Geri yükleme akışı: kullanıcı `EVET` yazar + 6 haneli güvenlik kodu girer; JSON dosyası yükler veya `backups/`'tan seçer → `flush` + `loaddata` (**tüm veri silinir**) |

### Kayıtlı Modeller ve Özel Alanlar
- **Rol** listesi: bağlı `loan_policy` değerlerini gösterir (süre, max kitap, günlük ceza).
- **Öğrenci** (`ImportExportModelAdmin`): CSV/JSON içe-dışa aktarma (`ogrenci_no,ad,soyad,sinif,rol`; UTF-8; başlık satırı zorunlu; virgül ayraçlı, tırnaksız). CSV'de olmayan aktif öğrenciler `after_import`'ta **pasife çekilir**.
- **Arşivleme** (Öğrenci değişiklik listesinden): kriter = `aktif=False` VE (pasif_tarihi 3+ yıl önce VEYA pasif_tarihi boşsa kayıt_tarihi 3+ yıl önce). Onayda transaction içinde `ArsivBatch` + `ArsivOgrenci` + `ArsivOdunc` oluşturulur, JSON paket kaydedilir, **canlı öğrenci ve ödünç kayıtları silinir**.
- **Personel**: şifre belirleme/sıfırlama; `save_model` otomatik eşleşen Django `User` oluşturur (`is_staff=True`).
- **Sayım Oturumu**: kalemleri salt-okunur inline.
- **LoanPolicy / RoleLoanPolicy / NotificationSettings**: listelenir, sistem ayarları olmayan alanlar düzenlenebilir.

### Şablonlar (`kutuphane/templates/admin/`)
- `index.html` — Sistem Araçları modülü ekler.
- `ogrenci_change_list.html` — "Arşive Taşı (ön izleme)" butonu.
- `system_settings.html`, `system_restore_form.html` — backup/restore arayüzü.
- `ogrenci_arsiv_onizleme.html` — arşiv ön izleme + onay.
- `import_export/export.html` — Türkçe etiketli dışa aktarma sayfası.

> Not: `system_restore_start/confirm/code.html` şablonları **eski** ve kullanılmıyor; güncel akış tek form (`system_restore_form.html`).

## 2. Deployment

Detaylı rehber: `kutuphane/django_deployment_checklist.md` ve `kutuphane/SERVER_SETUP.md`.

### Sunucu Ayarı (`setup_backend_service.sh`)
- `.env` içinden okunur: `/etc/kutuphane/.env` ve sonra `<proje>/kutuphane/.env` (yoksa varsayılanlar).
- Gunicorn WSGI; WhiteNoise statik dosyaları servis eder; `collectstatic` gerekir.
- Cron: `/etc/cron.d/kutuphane-scheduler` → `python manage.py run_scheduled_tasks` her 15 dk.

### Ortam Değişkenleri (`settings.py` `load_env`)
| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SECRET_KEY` | (güvensiz yedek) | Üretimde `.env`'den verilmeli |
| `DEBUG` | false | `"true"` yalnızca geliştirmede |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Virgülle ayrık |
| `DB_NAME` | `kutuphane` | |
| `DB_USER` | `kutuphane` | |
| `DB_PASSWORD` | — | |
| `DB_HOST` | `localhost` | |
| `DB_PORT` | `5432` | |

### Bazı Önemli Ayarlar
- `LANGUAGE_CODE = 'tr'`, `TIME_ZONE = 'Europe/Istanbul'`, `USE_TZ = True`.
- DRF: `IsAuthenticated` global, `JWTAuthentication` global.
- `MEDIA_ROOT` → `kutuphane/media`; `STATIC_ROOT` → `kutuphane/staticfiles`.

## 3. Güvenlik

- **API**: Tüm uçlar JWT korumalı; yalnızca `health` açık. Öğrenci bilgileri yetkisiz erişime kapalı (masaüstü/mobil istemciler token ile konuşur).
- **Admin**: Django session kimliği; Personel↔User eşleşmesi otomatik.
- **Restore**: `EVET` + dinamik 6 haneli kod — yanlışlıkla veri kaybını önler. Yine de **yıkıcıdır** (flush sonrası load).
- **Header temizliği**: `SafeHeaderMiddleware` ASCII olmayan/çok satırlı header değerlerini temizler (masaüstü `requests` istemcisinin RecursionError vermemesi için).
- **Şifreler**: Django `make_password`/`check_password`; Personel'de de ayrıca `sifre_hash` tutulur, değişiklikte eşzamanlanır.
- **Yedekleme**: JSON dosyası kişisel veri (öğrenci) içerir; indirilen dosya kurum içinde muhafaza edilmelidir.

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
- `kutuphane_app/tests.py` mevcut (CRUD + iş akışı testleri).
- `python manage.py test` ile çalıştırılır.
- Ayrıntılı test planı dosyası: bkz. readme'de bahsi geçen `kutuphane_backend_test_plan.xlsx`.