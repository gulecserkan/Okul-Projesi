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

### 7. Systemd ile otomatik başlatma

Repository kökünde `setup_backend_service.sh` adlı bir script bulunur. Bu script, Gunicorn tabanlı bir systemd servisi ve zamanlanmış görev cron girdisini tek adımda kurar.

1. Proje dizininde (manage.py ile aynı konumda) `sudo ./setup_backend_service.sh` çalıştırın.
2. Script aşağıdakileri yapar:
   - `/etc/systemd/system/kutuphane-backend.service` dosyasını oluşturur ve anında başlatır (`systemctl enable --now kutuphane-backend`).
   - `/var/log/kutuphane/gunicorn.log` dosyalarına çıktı yönlendirir.
   - `/etc/cron.d/kutuphane-scheduler` dosyasıyla her 15 dakikada bir `python manage.py run_scheduled_tasks` komutunu tetikler; logları `/var/log/kutuphane/scheduler.log` içine yazar.

Servis durumunu `sudo systemctl status kutuphane-backend` ile, logları `sudo journalctl -u kutuphane-backend -f` komutuyla izleyebilirsiniz.

### 8. Zamanlanmış görevleri manuel ayarlama

Eğer cron girdisini manuel yazmak isterseniz `/etc/cron.d` altında şu satırı ekleyin:

```
*/15 * * * * <kullanıcı_adı> source /path/to/kutuphane/venv/bin/activate && cd /path/to/kutuphane && python manage.py run_scheduled_tasks >> /var/log/kutuphane/scheduler.log 2>&1
```

`run_scheduled_tasks`, gecikme kontrolü ve hatırlatma gibi arka plan işlerini yürütür.

### 9. Masaüstü istemcisine bağlantı

- Backend çalıştığında `/api/token/` endpoint’i masaüstü istemcisi tarafından kullanılacaktır.
- Sunucu adresini istemci tarafındaki “Ayarlar → Sunucu” sekmesinden güncelleyin (örn. `http://sunucu-adresi:8000/api`).

### 10. Bakım / Güncelleme

1. Kod güncellemesi çekildikten sonra `source venv/bin/activate` ve `pip install -r requirements.txt` ile yeni paketleri kurun.
2. `python manage.py migrate` ile yeni şema değişikliklerini uygulayın.
3. systemd servisini yeniden başlatın: `sudo systemctl restart kutuphane-backend`.

Bu adımlar tamamlandığında Django backend’i temiz bir veritabanıyla çalışır durumda olacaktır.
