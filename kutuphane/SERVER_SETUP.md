## Backend (Django) Kurulum Rehberi

Bu proje Django 5.2 üzerinde çalışır ve PostgreSQL veritabanı kullanır. Aşağıdaki adımlar Ubuntu/Debian tabanlı bir sunucu içindir; farklı işletim sistemlerinde paket adlarını uyarlayın.

### 1. Ön gereksinimler

- Python 3.11
- PostgreSQL 14+ (varsayılan bağlantı `kutuphane_db` / `kutuphane_user`)
- Gerekli sistem paketleri:

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev build-essential \
                 libpq-dev postgresql postgresql-contrib git
```

### 2. Veritabanını hazırlayın

```bash
sudo -u postgres psql
CREATE DATABASE kutuphane_db;
CREATE USER kutuphane_user WITH PASSWORD '12345678';
ALTER ROLE kutuphane_user SET client_encoding TO 'UTF8';
ALTER ROLE kutuphane_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE kutuphane_user SET timezone TO 'Europe/Istanbul';
GRANT ALL PRIVILEGES ON DATABASE kutuphane_db TO kutuphane_user;
\q
```

> `kutuphane/kutuphane/settings.py` içindeki `DATABASES` bölümünü farklı kullanıcı/parola kullanacaksanız güncelleyin veya ortam değişkenleri üzerinden yönetin.

### 3. Kaynak kodu alın

```bash
git clone <repo-url> kutuphane-server
cd kutuphane-server/kutuphane
```

### 4. Sanal ortam ve bağımlılıklar

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Bağımlılık listesi `requirements.txt` içindedir. Sunucuyu taşırken sadece bu dosya yeterlidir.

### 5. Migrasyon ve süper kullanıcı

```bash
python manage.py migrate
python manage.py createsuperuser
```

Opsiyonel: Deneme verisi oluşturmak için `generate_fixture.py` veya `generate_odunc_fixture.py` scriptlerini çalıştırabilirsiniz.

### 6. Çalıştırma

Geliştirme için:

```bash
python manage.py runserver 0.0.0.0:8000
```

Üretim ortamında bir WSGI sunucusu (Gunicorn/Uvicorn) ve ters proxy (Nginx) önerilir. Statik dosyaları servis etmek için `python manage.py collectstatic` komutunu çalıştırmayı unutmayın.

### 7. Masaüstü istemcisine bağlantı

- Backend çalıştığında `/api/token/` endpoint’i masaüstü istemcisi tarafından kullanılacaktır.
- Sunucu adresini istemci tarafındaki “Ayarlar → Sunucu” sekmesinden güncelleyin (örn. `http://sunucu-adresi:8000/api`).

### 8. Bakım / Güncelleme

1. Kod güncellemesi çekildikten sonra `source venv/bin/activate` ve `pip install -r requirements.txt` ile yeni paketleri kurun.
2. `python manage.py migrate` ile yeni şema değişikliklerini uygulayın.
3. Servisi yeniden başlatın (örn. systemd ile).

Bu adımlar tamamlandığında Django backend’i temiz bir veritabanıyla çalışır durumda olacaktır.
