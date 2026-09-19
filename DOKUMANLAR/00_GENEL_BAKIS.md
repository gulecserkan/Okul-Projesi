# 00. Genel Bakış — Kütüphane Yönetim Sistemi

Okul kütüphaneleri için geliştirilen **kitap ödünç verme, takip, sayım ve yönetim sistemi**.
Tek merkezî REST API (Django) üzerinden dört farklı istemci tarafından kullanılır.

## Proje Yapısı

```
Okul-Projesi/
├── kutuphane/                  # Django backend (REST API + admin paneli)
├── kutuphane_desktop/          # PyQt5 masaüstü istemcisi (kasiyer terminali)
├── masaustu/                   # Flutter masaüstü istemcisi (personel/admin)
├── mobil/
│   └── kutuphane/              # Flutter mobil uygulama (personel + üye, rol bazlı)
└── e-okulöğrenciListesiToKutuphaneCSV.bas  # LibreOffice Basic: e-okul raporu → CSV
```

## Mimari Özet

```
                    ┌─────────────────────────────┐
                    │   PostgreSQL (tek veritabanı)│
                    └──────────▲──────────────────┘
                               │ Django ORM
                    ┌──────────┴──────────────────┐
                    │    Django REST API          │
                    │   (JWT kimlik doğrulama)    │
                    │   WhiteNoise (statik)       │
                    └──▲───────▲───────▲───────▲──┘
               HTTP+JWT │       │       │       │
       ┌─────────────┐ ┌┴──────┐┌┴──────┐┌┴─────┐
       │ Masaüstü    │ │Flutter││Flutter││Admin │
       │ (PyQt5)     │ │Öğretmen││Öğrenci││ /admin│
       └─────────────┘ └───────┘└───────┘└──────┘
```

## Katmanlar ve Görevleri

| Katman | Teknoloji | Sorumlu olduğu iş |
|---|---|---|
| **Backend** `kutuphane/` | Django 5.2, DRF 3.16, simplejwt, PostgreSQL, WhiteNoise, import-export | Tüm iş mantığı: ödünç, ceza politikası, sayım, arşiv, istatistik, backup/restore |
| **Masaüstü (eski, PyQt5)** `kutuphane_desktop/` | PyQt5 5.15, requests | Kasiyer terminali (referans): hızlı arama, ödünç/iade, etiket ve fiş yazdırma |
| **Masaüstü (Flutter)** `masaustu/` | Flutter | Kütüphane personeli: kitap/öğrenci/ödünç/katalog yönetimi, etiket/işlem ekranları |
| **Mobil (tek uygulama)** `mobil/kutuphane/` | Flutter, http, shared_preferences, image_picker, mobile_scanner | Rol bazlı: `personel` → kitap yönetimi; `üye` → gezinti + ödünçlerim |
| **VBA** `e-okul...bas` | LibreOffice Basic | e-okul sınıf listesi raporunu `uye_no,ad,soyad,sinif` CSV'sine dönüştürür |

## Kimlik Doğrulama

- API tamamen **JWT** korumalıdır (`rest_framework_simplejwt`).
- `POST /api/token/` → access + refresh token; yanıta ve token claim'lerine `full_name`, `role` ve `tip` (`personel`/`uye`) eklenir.
- `POST /api/token/refresh/` ile yenilenir.
- Tek açık uç: `GET /api/health/`.
- Kişiler: **iki tablo** — `User` (kimlik; operatör/admin/giriş yapan üye) ve `Uye` (kütüphane kişisi: öğrenci/öğretmen/editör). `Uye.user` opsiyonel 1:1 bağlantıdır. `Personel` tablosu kaldırılmıştır; admin = `is_superuser`.
- Admin paneli Django içi oturum (session) kimliği kullanır.

## Zamanlanmış İşler (Cron)

- Giriş noktası: `python manage.py run_scheduled_tasks` → `jobs.run_scheduled_jobs()`.
- `/etc/cron.d/kutuphane-scheduler` 15 dakikada bir çalıştırır (bkz. `setup_backend_service.sh`).
- Yaptıkları:
  1. **Günlük bir kez** → geciken ödünçlerin cezasını hesaplar/geri alır (`update_overdue_loans`).
  2. **Kanala göre planlanmış** → e-posta/SMS/mobil bildirimleri `dispatch_notifications()` ile yollar (henüz placeholder — gerçek gönderim yok).

## Veri Akışı — Yeni Kitap Ödünç Verme (checkout)

1. Masaüstü/mobil kullanıcı barkod veya no okutur → `GET /api/fast-query/?barkod=...`
2. Sunucu sırasıyla **barkod → ISBN → kitap başlığı → öğrenci no** tanır; öğrencinin aktif ödünçleri, ceza özeti ve rol politikası ile yanıt döner.
3. Masaüstü iletişim bilgisi eksikse kullanıcıyı uyarır, sayım limiti kontrol eder (`max_items_for_role`).
4. `POST /api/checkout/` `{uye_no, barkod}` → sunucu doğrular, `iade_tarihi` hesaplar (rol süresi + hafta sonu kaydırma), kaydı açıp nüshayı `oduncte` yapar.
5. İade/acil: `PATCH /api/oduncler/<id>/` durumu `teslim|kayip|hasarli|iptal`; kayıp/hasarlıda kalan ceza nüshaya işlenir.

## Yedekleme / Swiss Army Knife

- **Backup:** Admin → Sistem Ayarları → "Sistemi Yedekle" → `backups/backup_YYYYMMDD_HHMMSS.json` + tarayıcıya indirilir.
- **Restore:** Admin → Sistem Ayarları → "Sistemi Geri Yükle": `EVET` + 6 haneli güvenlik kodu → tüm veri silinir (`flush`) → JSON yüklenir.
- **Arşivleme:** 3+ yıl pasif öğrenciler ödünç geçmişiyle `ArsivBatch`'e snapshot'lanır, canlı veriden silinir.

## Kurulum (Özet)

Backend: bkz. `kutuphane/SERVER_SETUP.md` ve `kutuphane/readme.md`
Masaüstü: bkz. `kutuphane_desktop/DESKTOP_SETUP.md`

## İlgili Dokümanlar

- `01_SUNUCU_API.md` — tüm API uçları ve örnek istek/yanıtlar
- `02_VERITABANI.md` — veri modeli, ilişkiler, ceza formülleri
- `03_MASUSTU.md` — masaüstü istemcisi detayları
- `04_MOBIL.md` — mobil uygulamalar ve eksikleri
- `05_YONETIM.md` — admin, deployment, güvenlik
- `06_BILINEN_SORUNLAR.md` — tespit edilen sorunlar ve açık işler