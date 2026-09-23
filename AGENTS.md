# AGENTS.md — Kütüphane Yönetim Sistemi

Monorepo bölümleri:

- `kutuphane/` — Django + DRF backend (PostgreSQL). Venv: `kutuphane/venv`.
- `masaustu/` — Flutter masaüstü istemcisi (Linux; Flutter stable 3.47.5).
- `kutuphane_desktop/` — eski PyQt5 istemcisi (REFERANS: akış/tasarım kaynağı, değiştirilmez).
- `docs/` — iş kuralları ve faz planlaması.

## ZORUNLU — Her değişiklikte iş kuralları gözden geçirilir (Faz A)

1. `docs/IS_KURALLARI.md` oku; yapacağın ekleme/düzeltme mevcut bir kuralla
   çelişiyor mu, yeni bir kural gerektiriyor mu (`K` numarasıyla)?
2. Yeni/çelişen kural varsa ÖNCE dokümanı güncelle, sonra kodu yaz.
3. Kurallar `kutuphane/kutuphane_app/rules.py` üzerinden uygulanır;
   view içine kural tekrarı eklenmez.
4. Durum geçişlerini ihlal eden ham PATCH/UPDATE eklenmez
   (nüsha/ödünç durumu yalnızca checkout + `kapat` + görev işleriyle değişir).

## Komutlar

- Backend testleri: `cd kutuphane && venv/bin/python manage.py test kutuphane_app`
- Backend çalıştırma: `cd kutuphane && venv/bin/python manage.py runserver 0.0.0.0:8000 --noreload`
  (Sunucu başlatılırsa arka planda `setsid + nohup`, `--noreload`; log: `/tmp/opencode/runserver.log`)
- Flutter analiz: `cd masaustu && flutter analyze`
- Flutter test: `cd masaustu && flutter test`
- Flutter build: `cd masaustu && flutter build linux --debug`
- Git: dal `V2.0`; commit + push yalnızca kullanıcı isterse.

## Notlar

- Sunucu adresi masaüstünde ayarlanabilir (`AppConfig.apiBaseUrl`, login ekranı).
- Login yanıtı `role` içerir (`admin`/`personel`); hassas aksiyonlar admin'e açık.
- Eski masaüstündeki silme/durum mantığı yeni katmanla senkron tutulmaz;
  kuralların kaynağı `docs/IS_KURALLARI.md` + `rules.py`'dir.

## Geliştirme ortamı ve yayın akışı

- **Veritabanı:** Geliştirme yalnız bu makinedeki yerel PostgreSQL ile yapılır
  (`127.0.0.1:5432`, DB `kutuphane`, `DB_PASSWORD=kutuphane_dev`). Prod/staging
  DB'sine bu makineden **bağlanılmaz**; istemciler DB'ye değil API'ye bağlanır.
- **Sırlar:** Yerel `.env` (gitignored) ↔ sunucu `/etc/kutuphane/.env`
  (`KUTUPHANE_ENV_FILE` ile staging'e ayrılır). Sırlar git'e girmez.
- **Yayınlama:** testler yeşil → `VERSION` + `docs/CHANGELOG.md` güncelle →
  `git tag vX.Y.Z` + push → staging'e al → doğrula → prod'a al:
  `sudo bash kutuphane/scripts/deploy.sh <prod|staging> <tag>`
  (geri dönüş: `rollback.sh`). Ayrıntı: `docs/DEPLOY_CLOUD.md` (12-13).
- **İlkeler:** her değişiklikte `docs/IS_KURALLARI.md` gözden geçirilir; yeni
  kural varsa önce doküman, sonra kod. Commit/push yalnız kullanıcı isterse.