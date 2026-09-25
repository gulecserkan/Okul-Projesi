📚 Kütüphane Yönetim Sistemi (Django Backend)

Bu proje, okul kütüphaneleri için geliştirilen bir kitap ödünç verme, takip ve yönetim sistemi backend’idir.
Masaüstü uygulaması ve mobil istemci (Flutter) tarafından kullanılacak bir REST API sunar.

🚀 Özellikler

Django + Django REST Framework tabanlı backend

PostgreSQL veritabanı desteği

CRUD API’leri:

Öğrenci, Sınıf, Rol

Yazar, Kategori, Kitap, Kitap Nüsha

Ödünç Kayıtları

Üye (öğrenci / öğretmen / editör)

İstatistik API’leri:

En çok okuyan öğrenciler

En çok okunan kitaplar

Sınıf bazlı okuma raporları

Toplam gecikme cezaları

Admin Paneli Geliştirmeleri:

Öğrenci içe/dışa aktarma (CSV/JSON)

Arşivleme (3+ yıl pasif öğrenciler + ödünç geçmişi)

Yedekleme sunucu tarafında `pg_dump` + cron (`scripts/yedekle.sh`, `scripts/geri-yukle.sh`)

Etiket / Barkod desteği (termal yazıcı entegrasyonu için backend hazır)

📥 Öğrenci CSV içe aktarma formatı (masaüstü K9.13)
- Toplu giriş yalnız masaüstü uygulamadan yapılır; admin panelde içe/dışa aktarma yoktur.
- Başlık satırı zorunlu; ayraç `,` / `;` / `\t` otomatik algılanır.
- Kolonlar: `ogrenci_no` (veya `uye_no`), `ad`, `soyad`, `sinif`[, `rol`]; sınıf `5/A`→`5-A` normalize edilir.
- Kodlama: UTF-8 (bozuksa CP1254 uyumlu çözülür).

🛠️ Kurulum
1. Depoyu klonla
git clone <repo-url>
cd kutuphane

2. Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate

3. Gereksinimleri yükle
pip install -r requirements.txt

4. PostgreSQL veritabanı oluştur
CREATE DATABASE kutuphane;
CREATE USER kutuphane_user WITH PASSWORD 'parola';
ALTER ROLE kutuphane_user SET client_encoding TO 'utf8';
ALTER ROLE kutuphane_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE kutuphane TO kutuphane_user;


settings.py içinde ayarları güncelle (veya kök dizinde `.env` kullan — önerilen):

```
SECRET_KEY=...
DB_NAME=kutuphane
DB_USER=kutuphane_user
DB_PASSWORD=parola
DB_HOST=localhost
# Kişisel veri şifrelemesi için ayrı anahtar (önerilir; boşsa SECRET_KEY devreye girer)
FIELD_ENCRYPTION_KEY=...
# Üretimde (DEBUG=False) SECRET_KEY boşken sunucu başlamaz (fail-fast).
```

Not: Telefon/e-posta ve bildirim kredileri alan düzeyinde şifreli saklanır;
şifrelenmiş alanlar üzerinde kısmi arama (`icontains`) yapılamaz.

5. Migration çalıştır
python manage.py migrate
python manage.py createsuperuser

6. Sunucuyu başlat
python manage.py runserver

📡 API Endpoint’leri

Ana URL: http://127.0.0.1:8000/api/

/roller/ → Rol CRUD

/siniflar/ → Sınıf CRUD

/uyeler/ → Öğrenci CRUD

/yazarlar/ → Yazar CRUD

/kategoriler/ → Kategori CRUD

/kitaplar/ → Kitap CRUD

/nushalar/ → Kitap nüshaları

/oduncler/ → Ödünç kayıtları

/uyeler/ → Üye CRUD (öğrenci/öğretmen/editör)

/istatistik/ → İstatistik raporları

🔑 Admin Paneli

Admin URL: http://127.0.0.1:8000/admin/

Ek Özellikler:

Öğrenci Yönetimi (liste/arama/düzenleme)

Arşivleme işlemleri

Ayar tabloları (Rol, LoanPolicy, RoleLoanPolicy, NotificationSettings, KurumAyarlari)

🗄️ Yedekleme ve Geri Yükleme (sunucu tarafı)

Backup

scripts/yedekle.sh → pg_dump -Fc + openssl ile şifreli /var/backups/kutuphane/kutuphane_<ortam>_<zaman>.dump.enc

Cron: /etc/cron.d/kutuphane-yedek (her gün 03:30, 14 gün saklama)

Gereksinim: /etc/kutuphane/.env içinde YEDEK_SIFRE

Restore

scripts/geri-yukle.sh <yedek.dump.enc> [prod|staging]

pg_restore --clean --if-exists (mevcut nesneler değiştirilir)

⚠️ Geri yükleme yıkıcıdır; öncesinde güncel yedek alınmalıdır. Admin panelde yedek arayüzü yoktur.

📦 Arşivleme

Pasif hale gelmiş ve 3+ yıl eski öğrenciler, ödünç kayıtlarıyla birlikte arşive taşınır.

Arşivlenen veriler ArsivBatch altında tutulur ve JSON dosyası olarak saklanır.

Admin üzerinden geçmiş arşivlere erişilebilir.

✅ Test Planı

Çekirdek testler: `cd kutuphane && python manage.py test`

- Ödünç politikası (ceza, limit, hafta sonu kayması)
- Checkout API akışı
- Barkod otomatik üretimi (MAX + retry)
- Alan şifrelemesi (KVKK)
- Yetki sınırlamaları (K9: admin/operatör/editör/üye)

Detaylı uç test planı: kutuphane_backend_test_plan.xlsx

🔒 Yayınlama (Deployment)

Detaylı adımlar: django_deployment_checklist.md

👨‍💻 Katkı

Proje Python/Django ile geliştirilmiştir.

Kod katkıları ve geliştirme önerileri için PR gönderilebilir.
