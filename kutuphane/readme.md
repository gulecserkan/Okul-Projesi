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

Personel

İstatistik API’leri:

En çok okuyan öğrenciler

En çok okunan kitaplar

Sınıf bazlı okuma raporları

Toplam gecikme cezaları

Admin Paneli Geliştirmeleri:

Öğrenci içe/dışa aktarma (CSV/JSON)

Arşivleme (3+ yıl pasif öğrenciler + ödünç geçmişi)

Sistem ayarları sayfası:

Komple backup (yedekleme)

Komple restore (geri yükleme) — 3 adımlı güvenlik onaylı

Etiket / Barkod desteği (termal yazıcı entegrasyonu için backend hazır)

📥 Öğrenci CSV içe aktarma formatı
- Başlık satırı zorunlu, virgül ayraçlı, değerler yalın (tırnaksız) yazılabilir.
- Kolonlar: `ogrenci_no,ad,soyad,sinif,rol` (sinif ve rol mevcut ad alanlarıyla eşleşir).
- Kodlama: UTF-8

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

/ogrenciler/ → Öğrenci CRUD

/yazarlar/ → Yazar CRUD

/kategoriler/ → Kategori CRUD

/kitaplar/ → Kitap CRUD

/nushalar/ → Kitap nüshaları

/oduncler/ → Ödünç kayıtları

/personel/ → Personel CRUD

/istatistik/ → İstatistik raporları

🔑 Admin Paneli

Admin URL: http://127.0.0.1:8000/admin/

Ek Özellikler:

Öğrenci Yönetimi

CSV/JSON içe aktarma

Arşivleme işlemleri

Sistem Ayarları

Backup → JSON dosyası indirilebilir

Restore → JSON’dan geri yükleme (üçlü doğrulama ile)

🗄️ Yedekleme ve Geri Yükleme
Backup

Admin → Sistem Ayarları → “💾 Sistemi Yedekle”

backups/backup_YYYYMMDD_HHMMSS.json.enc olarak şifreli kaydedilir

Aynı şifreli dosya tarayıcıya indirilebilir (içerik düz metin telefon/e-posta içerdiği için şifrelidir)

Restore

Admin → Sistem Ayarları → “♻️ Sistemi Geri Yükle”

Adım adım güvenlik onayı (EVET + 6 haneli kod)

Dosya yükleyerek veya mevcut yedekten seçerek geri yükleme; hem yeni `.json.enc` hem eski düz metin `.json` desteklenir

⚠️ Restore işlemi tüm mevcut verileri siler. Dikkatli kullanılmalıdır.

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
- Personel yetki sınırlamaları

Detaylı uç test planı: kutuphane_backend_test_plan.xlsx

🔒 Yayınlama (Deployment)

Detaylı adımlar: django_deployment_checklist.md

👨‍💻 Katkı

Proje Python/Django ile geliştirilmiştir.

Kod katkıları ve geliştirme önerileri için PR gönderilebilir.
