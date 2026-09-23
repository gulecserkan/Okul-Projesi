# Cloud Ubuntu Kurulum Rehberi — Kütüphane Sistemi

Bu rehber, sıfır (boş) bir Ubuntu sunucusuna kütüphane sistemini kurar:

- **PostgreSQL** yalnız Docker konteynerı olarak (internete kapalı, `127.0.0.1:5432`)
- **Django + API** native: venv + Gunicorn + systemd (nginx arkasında, `127.0.0.1:8000`)
- **Nginx** ters proxy; kök adres (`/`) → **genel kitap kataloğu web sayfası** (K11),
  `/api/*` → arka planda DRF/JWT API'si
- Firewall, SSH güvenliği, yedekleme, zamanlanmış işler (cron)

**İki faz:** Faz A → ham IP üzerinden HTTP ile yayına alma; Faz B → alan adı + HTTPS (Let's Encrypt).

> Varsayımlar: Ubuntu **24.04 LTS**, root (veya sudo yetkili) kullanıcı erişimi, SSH.
> Not: tüm komutlar sunucuda kök kabukta çalıştırılır — aksi belirtilmedikçe. "YEREL" etiketli bloklar bu makinede çalışır.

## 0. Değişkenler

Kendine göre doldur ve kopyala:

```bash
SERVER_IP=1.2.3.4            # bulut sunucunun genel IPv4 adresi
DOMAIN=                     # Faz B dolacak (örn. kutuphane.ornekokul.k12.tr)
APP_USER=kutuphane
APP_DIR=/srv/kutuphane
DB_PASSWORD='<güçlü-rastgele-parola>'   # PostgreSQL
```

---

## 1. Temel sistem kurulumu

```bash
export SERVER_IP=1.2.3.4
export APP_USER=kutuphane
export DB_PASSWORD='<güçlü-parola>'

apt update
apt -y upgrade
apt -y install \
  python3 python3-venv python3-dev build-essential libpq-dev \
  nginx curl ufw git fail2ban unattended-upgrades \
  docker.io docker-compose-v2 rsync

# otomatik güvenlik güncellemelerini etkinleştir (sessiz)
systemctl enable --now unattended-upgrades
```

## 2. Uygulama kullanıcısı ve dizinler

```bash
useradd --system --create-home --home-dir /srv/kutuphane --shell /bin/bash kutuphane || true
mkdir -p /etc/kutuphane /var/log/kutuphane /var/backups/kutuphane
chown "$APP_USER":"$APP_USER" /srv/kutuphane /var/log/kutuphane /var/backups/kutuphane
```

> `rsync` ile içeri yükleme için kullanıcının SSH anahtarı gerekir (bkz. 6.1).

## 3. `.env` (sırlar) — `/etc/kutuphane/.env`

Django ayarları bu yolu zaten okur (`settings.py` → `ENV_FILE`). Root'a özel:

```bash
SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
cat > /etc/kutuphane/.env <<EOF
DEBUG=false
SECRET_KEY=${SECRET_KEY}
FIELD_ENCRYPTION_KEY=${SECRET_KEY}
GOOGLE_BOOKS_API_KEY=
ALLOWED_HOSTS=${SERVER_IP}
CSRF_TRUSTED_ORIGINS=http://${SERVER_IP}
SECURE_SSL_REDIRECT=false
DB_NAME=kutuphane
DB_USER=kutuphane
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=127.0.0.1
DB_PORT=5432
EOF
chown root:root /etc/kutuphane/.env
chmod 600 /etc/kutuphane/.env
```

- `DEBUG=false` → ayarlar `SECRET_KEY` zorlar (yukarıda ürettik).
- `FIELD_ENCRYPTION_KEY` yalnız ilk kurulumda üret; sonradan değiştirilirse şifreli alanlar okunamaz.
- `GOOGLE_BOOKS_API_KEY` varsa doldur (K7.5, isteğe bağlı).
- Faz B'de bu dosya güncellenecek (bkz. 9).

## 4. PostgreSQL — Docker

`docker-compose.yml`'ı `/etc/kutuphane/` içine koy:

```bash
cat > /etc/kutuphane/docker-compose.yml <<'YML'
services:
  db:
    image: postgres:16-alpine
    container_name: kutuphane-postgres
    restart: unless-stopped
    env_file: /etc/kutuphane/.env
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      TZ: Europe/Istanbul
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - kutuphane_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  kutuphane_pgdata:
YML

cd /etc/kutuphane
docker compose up -d
docker compose ps          # healthy görene kadar bekleyin (~10 sn)
```

> Port **yalnız 127.0.0.1**'e bağlı → veritabanı internete kapalı.
> Her yeniden başlatmada veri volume'da kalır.

## 5. Kodu içeri yükle (YEREL)

Bu makineden çalıştır (önce SSH anahtarını kopyala):

```bash
# 6.1'deki anahtarla, sunucuda /srv/kutuphane boşken:
ssh-copy-id kutuphane@<SERVER_IP>

rsync -avz --delete -e ssh \
  --exclude 'venv' --exclude '.env' --exclude '__pycache__' \
  --exclude '*.pyc' --exclude 'media' --exclude 'staticfiles' \
  ./kutuphane/ kutuphane@<SERVER_IP>:/srv/kutuphane/
```

> `media/` içeride başlangıçta boş; üretimdeki yüklenen görselleri asla bu yönetimle ezme.
> Mevcut görseller varsa ayrıca: `rsync -avz -e ssh ./kutuphane/media/ kutuphane@IP:/srv/kutuphane/media/`

## 6. Python, bağımlılıklar, veritabanı

```bash
cd /srv/kutuphane
sudo -u kutuphane python3 -m venv venv
sudo -u kutuphane venv/bin/pip install --upgrade pip
sudo -u kutuphane venv/bin/pip install -r requirements.txt

# DB'yi hazırla: şema + statik + admin + (ops.) deneme verisi
sudo -u kutuphane venv/bin/python manage.py migrate
sudo -u kutuphane venv/bin/python manage.py collectstatic --noinput
sudo -u kutuphane venv/bin/python manage.py createsuperuser

# Deneme/ilk verisi yüklemek istersen (opsiyonel):
sudo -u kutuphane venv/bin/python manage.py loaddata ilk_veri.json
```

Doğrulama (DB hazır mı, katalog sunuyor mu):

```bash
sudo -u kutuphane venv/bin/python manage.py shell -c "from kutuphane_app.models import Kitap; print('kitap sayısı:', Kitap.objects.count())"
```

## 7. systemd — Gunicorn servisi

`setup_backend_service.sh` ile **aynı değil**: üretimde 0.0.0.0 yerine **127.0.0.1** bağlarız (nginx arkası). Servis dosyasını yaz:

```bash
cat > /etc/systemd/system/kutuphane-backend.service <<'SVC'
[Unit]
Description=Kutuphane Django Backend (Gunicorn)
After=network.target docker.service

[Service]
User=kutuphane
Group=kutuphane
WorkingDirectory=/srv/kutuphane
Environment="PATH=/srv/kutuphane/venv/bin"
ExecStart=/srv/kutuphane/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 kutuphane.wsgi:application
Restart=always
RestartSec=5
StandardOutput=append:/var/log/kutuphane/gunicorn.log
StandardError=append:/var/log/kutuphane/gunicorn.log

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable --now kutuphane-backend
journalctl -u kutuphane-backend --no-pager -n 20
```

> `--workers 3` küçük kurulum için; çok çekirdekli sunucuda `2*nproc+1` yap.

### Zamanlanmış işler (gecikme/bildirim)

```bash
cat > /etc/cron.d/kutuphane-scheduler <<EOF
*/15 * * * * kutuphane cd /srv/kutuphane && ./venv/bin/python manage.py run_scheduled_tasks >> /var/log/kutuphane/scheduler.log 2>&1
EOF
chmod 644 /etc/cron.d/kutuphane-scheduler
```

## 8. Nginx

```bash
cat > /etc/nginx/sites-available/kutuphane <<'NGX'
server {
    listen 80;
    listen [::]:80;
    server_name _;                 # Faz A: IP ile. Faz B: alan adıyla değişecek.

    client_max_body_size 25M;      # kapak/inceleme görseli yükleme

    location /media/ {
        alias /srv/kutuphane/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGX

ln -sf /etc/nginx/sites-available/kutuphane /etc/nginx/sites-enabled/kutuphane
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

> Kök adres `/` → Django `BookCatalogView` (genel katalog), `/api/*` aynı gunicorn'dan.
> Static (`/static/`) Whitenoise aracılığıyla gunicorn'dan gelir — ayrı ayar gerekmez.

### Veritabanı yedekleme (cron)

```bash
cat > /etc/cron.d/kutuphane-backup <<'EOF'
# PostgreSQL + media yedeği (günlük 02:30), 14 gün tut
30 2 * * * root mkdir -p /var/backups/kutuphane && docker exec kutuphane-postgres pg_dump -U kutuphane kutuphane -Fc | gzip > /var/backups/kutuphane/pg_$(date +\%F).dump.gz && find /var/backups/kutuphane -name 'pg_*' -mtime +14 -delete
40 2 * * * root tar -czf /var/backups/kutuphane/media_$(date +\%F).tar.gz -C /srv/kutuphane media && find /var/backups/kutuphane -name 'media_*' -mtime +14 -delete
EOF
chmod 644 /etc/cron.d/kutuphane-backup
```

Geri yükleme:

```bash
zcat /var/backups/kutuphane/pg_2026-09-24.dump.gz | docker exec -i kutuphane-postgres psql -U kutuphane kutuphane
```

## 9. Firewall ve SSH güvenliği

> **Önce** SSH anahtarınızı ekleyip test edin (aksi halde kendinizi kilitleyebilirsiniz).

```bash
# 1) Yerel makinede: ssh-keygen -t ed25519 ; ssh-copy-id root@IP
# 2) Root ile SSH anahtarıyla giriş doğrula  →  başka konsolda test edin

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status

# 3) SSH sertleştirme
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart ssh
```

- 8000 portu internete **açılmaz** (gunicorn 127.0.0.1; UFW'da yok).
- `fail2ban` kuruldu; yapılandırma gerekmez (varsayılan ayarlar yeterli).

## 10. Faz A doğrulama

```bash
curl -s http://<SERVER_IP>/api/health/                # {"status":"ok",...}
curl -s http://<SERVER_IP>/ | head -c 400             # HTML katalog (Kütüphane Kataloğu)
curl -s "http://<SERVER_IP>/?q=sefiller" | grep -c sefiller   # arama
```

- Tarayıcıda `http://<SERVER_IP>/` → kitap kataloğu görünür.
- Mobil uygulama: giriş ekranında sunucu adresini `http://<SERVER_IP>` yap → katalog/API bağlanır.
- Masaüstü: Ayarlar → Sunucu → `http://<SERVER_IP>`.
- `/admin/` ile yönetime giriş.

Sorun giderme: `journalctl -u kutuphane-backend --no-pager -n 100`, `tail /var/log/kutuphane/gunicorn.log`, `docker compose -f /etc/kutuphane/docker-compose.yml ps`.

---

## 11. Faz B — Alan adı + HTTPS

```bash
export DOMAIN=kutuphane.ornekokul.k12.tr
# DNS'te A kaydını SERVER_IP'e yönlendir (DNS sağlayıcısının paneline)

apt -y install certbot python3-certbot-nginx
certbot --nginx -d "$DOMAIN" --redirect     # 80→443 otomatik
```

`.env` güncelle:

```bash
sed -i "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=${SERVER_IP},${DOMAIN}/" /etc/kutuphane/.env
sed -i "s/^CSRF_TRUSTED_ORIGINS=.*/CSRF_TRUSTED_ORIGINS=https:\/\/${DOMAIN}/" /etc/kutuphane/.env
sed -i "s/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=true/" /etc/kutuphane/.env
systemctl restart kutuphane-backend
```

> `SECURE_SSL_REDIRECT=true` + nginx `--redirect` birlikte çalışır (X-Forwarded-Proto
> ayarı proxy'de hazır). `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` zaten `DEBUG=false`
> olduğundan açıktır.

Doğrulama: `curl -sI https://$DOMAIN/` → 200; mobil/ masaüstü adresi `https://$DOMAIN`'e çevrilir.

---

## 12. Güncelleme akışı (bakım)

```bash
# YEREL
rsync -avz --delete -e ssh --exclude 'venv' --exclude '.env' --exclude '__pycache__' \
  --exclude '*.pyc' --exclude 'media' --exclude 'staticfiles' \
  ./kutuphane/ kutuphane@<SERVER_IP>:/srv/kutuphane/

# SUNUCU
cd /srv/kutuphane
sudo -u kutuphane venv/bin/pip install -r requirements.txt
sudo -u kutuphane venv/bin/python manage.py migrate
sudo -u kutuphane venv/bin/python manage.py collectstatic --noinput
systemctl restart kutuphane-backend
```

## 13. Hızlı başvuru

| Katman | Port | Nerede |
|---|---|---|
| PostgreSQL (Docker) | 127.0.0.1:5432 | `kutuphane-postgres`, volume `kutuphane_pgdata` |
| Django/Gunicorn (systemd) | 127.0.0.1:8000 | `kutuphane-backend.service` |
| Nginx | 80 → (443 Faz B) | `/etc/nginx/sites-available/kutuphane` |
| Sırlar | — | `/etc/kutuphane/.env` (root, 600) |
| Loglar | — | `/var/log/kutuphane/` |
| Yedekler | — | `/var/backups/kutuphane/` (DB + media, 14 gün) |
| Cron | — | `/etc/cron.d/kutuphane-scheduler`, `kutuphane-backup` |