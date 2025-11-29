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


settings.py içinde ayarları güncelle:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kutuphane',
        'USER': 'kutuphane_user',
        'PASSWORD': 'parola',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

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

backups/backup_YYYYMMDD_HHMMSS.json olarak kaydedilir

Aynı zamanda tarayıcıya indirilebilir

Restore

Admin → Sistem Ayarları → “♻️ Sistemi Geri Yükle”

Adım adım güvenlik onayı

Dosya yükleyerek veya mevcut yedekten seçerek geri yükleme yapılır

⚠️ Restore işlemi tüm mevcut verileri siler. Dikkatli kullanılmalıdır.

📦 Arşivleme

Pasif hale gelmiş ve 3+ yıl eski öğrenciler, ödünç kayıtlarıyla birlikte arşive taşınır.

Arşivlenen veriler ArsivBatch altında tutulur ve JSON dosyası olarak saklanır.

Admin üzerinden geçmiş arşivlere erişilebilir.

✅ Test Planı

Tüm CRUD ve admin fonksiyonları için detaylı bir test planı hazırlanmıştır.
📂 kutuphane_backend_test_plan.xlsx

🔒 Yayınlama (Deployment)

Detaylı adımlar: django_deployment_checklist.md

👨‍💻 Katkı

Proje Python/Django ile geliştirilmiştir.

Kod katkıları ve geliştirme önerileri için PR gönderilebilir.
