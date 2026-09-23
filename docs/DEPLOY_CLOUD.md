# Cloud Ubuntu Kurulum Rehberi — Kütüphane Sistemi

Bu rehber, sıfır (boş) bir Ubuntu sunucusuna kütüphane sistemini kurar:

- **PostgreSQL** yalnız Docker konteynerı olarak (internete kapalı, `127.0.0.1:5432`)
- **Django + API** native: venv + Gunicorn + systemd (nginx arkasında, `127.0.0.1:8000`)
- **Nginx** ters proxy; kök adres (`/`) → **genel kitap kataloğu web sayfası** (K11),
  `/api/*` → arka planda DRF/JWT API'si
- Firewall, SSH güvenliği, yedekleme, zamanlanmış işler (cron)
- Güncelleme akışı: bu makinede geliştir → test → **git etiketi** → staging →
  prod (`scripts/deploy.sh` / `rollback.sh`, bkz. 12-13)

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
useradd --system --create-home --home-dir /home/kutuphane --shell /bin/bash kutuphane || true
install -d -o "$APP_USER" -g "$APP_USER" /srv/kutuphane
mkdir -p /etc/kutuphane /var/log/kutuphane /var/backups/kutuphane
chown "$APP_USER":"$APP_USER" /var/log/kutuphane /var/backups/kutuphane
```

> Sunucu, kodu **git ile** takip eder (bkz. 5); bunun için salt-okunur deploy
> anahtarı gerekir. Güncellemeler etiketli sürümlerle yapılır.
>
> **Dizin düzeni (monorepo):** repo kökü `/srv/kutuphane`, Django uygulaması
> `/srv/kutuphane/kutuphane` (manage.py burada), venv `/srv/kutuphane/venv`.

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
- `KUTUPHANE_ENV_FILE` ortam değişkeniyle başka bir sır dosyası gösterilebilir
  (staging için `/etc/kutuphane/staging.env`, bkz. 13). Verilmezse bu dosya okunur.
- Faz B'de bu dosya güncellenecek (bkz. 11).

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

## 5. Kodu içeri al (git)

Sunucu, kodu **git etiketiyle** takip eder. Önce GitHub deposuna salt-okunur
**deploy key** eklenir:

```bash
# SUNUCU: kutuphane kullanıcısı için SSH anahtarı üret (varsayılan ~/.ssh)
sudo -u kutuphane ssh-keygen -t ed25519 -N '' -C 'deploy@kutuphane'

# Genel anahtarı görüntüle (kopyala)
cat /home/kutuphane/.ssh/id_ed25519.pub
```

GitHub → depo → **Settings → Deploy keys → Add deploy key** → genel anahtarı
yapıştır, **"Allow write access" işaretleme** (salt-okunur yeterli).

```bash
# SUNUCU: repoyu klonla (boş /srv/kutuphane içine)
sudo -u kutuphane git clone git@github.com:gulecserkan/Okul-Projesi.git /srv/kutuphane

# Kontrol: Django uygulaması alt klasörde olmalı
ls /srv/kutuphane/kutuphane/manage.py
```

> Bundan sonraki güncellemeler elle dosya kopyalamayla değil, `scripts/deploy.sh`
> ile etiketli sürüm çekilerek yapılır (bkz. 12).

> **Alternatif (git kullanmak istemezsen):** kod bu makineden `rsync` ile de
> gönderilebilir; ancak sürüm takibi ve kolay geri dönüş için git önerilir.

## 6. Python, bağımlılıklar, veritabanı

```bash
REPO=/srv/kutuphane
APP=/srv/kutuphane/kutuphane
VENV=/srv/kutuphane/venv

sudo -u kutuphane python3 -m venv "$VENV"
sudo -u kutuphane "$VENV/bin/pip" install --upgrade pip
sudo -u kutuphane "$VENV/bin/pip" install -r "$APP/requirements.txt"

# DB'yi hazırla: şema + statik + admin + (ops.) deneme verisi
sudo -u kutuphane env -C "$APP" "$VENV/bin/python" manage.py migrate
sudo -u kutuphane env -C "$APP" "$VENV/bin/python" manage.py collectstatic --noinput
sudo -u kutuphane env -C "$APP" "$VENV/bin/python" manage.py createsuperuser

# Deneme/ilk verisi yüklemek istersen (opsiyonel):
sudo -u kutuphane env -C "$APP" "$VENV/bin/python" manage.py loaddata "$APP/ilk_veri.json"
```

Doğrulama (DB hazır mı, kitap var mı):

```bash
sudo -u kutuphane env -C "$APP" "$VENV/bin/python" manage.py shell -c \
  "from kutuphane_app.models import Kitap; print('kitap sayısı:', Kitap.objects.count())"
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
WorkingDirectory=/srv/kutuphane/kutuphane
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
*/15 * * * * kutuphane env -C /srv/kutuphane/kutuphane /srv/kutuphane/venv/bin/python manage.py run_scheduled_tasks >> /var/log/kutuphane/scheduler.log 2>&1
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
        alias /srv/kutuphane/kutuphane/media/;
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
40 2 * * * root tar -czf /var/backups/kutuphane/media_$(date +\%F).tar.gz -C /srv/kutuphane/kutuphane media && find /var/backups/kutuphane -name 'media_*' -mtime +14 -delete
EOF
chmod 644 /etc/cron.d/kutuphane-backup
```

Geri yükleme (`-Fc` özel format → `pg_restore`):

```bash
zcat /var/backups/kutuphane/pg_2026-09-24.dump.gz \
  | docker exec -i kutuphane-postgres pg_restore -U kutuphane -d kutuphane --clean --if-exists
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

## 12. Güncelleme akışı (geliştirme → yayın)

Akış: bu makinede geliştir → testler yeşil → etiketle → önce **staging**'de
dene → sonra **prod**'a al. Sunucuda dosya elle düzenlenmez.

**YEREL (bu makine):**

```bash
# 1) Testler yeşil olmalı
cd kutuphane && venv/bin/python manage.py test kutuphane_app
# (mobil/masaüstü değiştiyse: flutter analyze && flutter test)

# 2) Sürüm işaretle
#    VERSION ve docs/CHANGELOG.md güncelle, sonra:
git add -A && git commit -m "ozet"
git tag v1.1.0
git push origin V2.0 --tags
```

**SUNUCU — önce staging:**

```bash
sudo bash /srv/kutuphane-staging/kutuphane/scripts/deploy.sh staging v1.1.0
#   → SSH tüneliyle göz at (yerel makineden):
#     ssh -L 8001:127.0.0.1:8001 kutuphane@<SERVER_IP>   ve  http://127.0.0.1:8001/
```

**SUNUCU — sorun yoksa prod:**

```bash
sudo bash /srv/kutuphane/kutuphane/scripts/deploy.sh prod v1.1.0
```

**Geri dönüş:**

```bash
sudo bash /srv/kutuphane/kutuphane/scripts/rollback.sh prod v1.0.0
```

`deploy.sh` sırasıyla: etiketi çeker → `pip install` → **migration öncesi yedek
alır** → `migrate` → `collectstatic` → servisi yeniden başlatır → `/api/health/`
ile doğrular. Başarısızsa hata ile çıkar ve geri dönüş komutunu yazdırır.
Log: `/var/log/kutuphane/deploy.log`.

> Kısa kesinti (gunicorn restart ~1-2 sn) kabul edilir; yedek sayesinde risk düşük.

## 13. Staging ortamı (aynı sunucu, ek port + DB)

Prod'u etkilemeden yeni sürümü denemek için. Kod: `/srv/kutuphane-staging`
(ayrı klon), uygulama `/srv/kutuphane-staging/kutuphane`, venv aynı yapıda.

```bash
# 1) İkinci veritabanı (aynı konteyner)
docker exec kutuphane-postgres psql -U kutuphane -d postgres -c 'CREATE DATABASE kutuphane_staging;'

# 2) Ayrı .env (sırlar ayrı; DB hedefi staging)
cp /etc/kutuphane/.env /etc/kutuphane/staging.env
sed -i 's/^DB_NAME=.*/DB_NAME=kutuphane_staging/' /etc/kutuphane/staging.env
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(50))')|" /etc/kutuphane/staging.env
sed -i 's/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=127.0.0.1,localhost/' /etc/kutuphane/staging.env
chmod 600 /etc/kutuphane/staging.env

# 3) Ayrı kod klonu + venv
install -d -o kutuphane -g kutuphane /srv/kutuphane-staging
sudo -u kutuphane git clone git@github.com:gulecserkan/Okul-Projesi.git /srv/kutuphane-staging
sudo -u kutuphane python3 -m venv /srv/kutuphane-staging/venv
sudo -u kutuphane /srv/kutuphane-staging/venv/bin/pip install -r /srv/kutuphane-staging/kutuphane/requirements.txt
sudo -u kutuphane env -C /srv/kutuphane-staging/kutuphane \
  KUTUPHANE_ENV_FILE=/etc/kutuphane/staging.env /srv/kutuphane-staging/venv/bin/python manage.py migrate
```

`KUTUPHANE_ENV_FILE` sayesinde staging, prod'dan farklı `.env` okur
(`settings.py` bu değişkeni destekler; verilmezse `/etc/kutuphane/.env`).

systemd servisi (8001):

```bash
cat > /etc/systemd/system/kutuphane-staging.service <<'SVC'
[Unit]
Description=Kutuphane Staging (Gunicorn)
After=network.target docker.service

[Service]
User=kutuphane
Group=kutuphane
WorkingDirectory=/srv/kutuphane-staging/kutuphane
Environment="PATH=/srv/kutuphane-staging/venv/bin"
Environment="KUTUPHANE_ENV_FILE=/etc/kutuphane/staging.env"
ExecStart=/srv/kutuphane-staging/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8001 kutuphane.wsgi:application
Restart=always
RestartSec=5
StandardOutput=append:/var/log/kutuphane/staging.log
StandardError=append:/var/log/kutuphane/staging.log

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable --now kutuphane-staging
```

> Staging dışa **açılmaz** (127.0.0.1:8001). Erişim için SSH tüneli kullan:
> `ssh -L 8001:127.0.0.1:8001 kutuphane@<SERVER_IP>` → tarayıcı `http://127.0.0.1:8001/`.
> Canlı test verisi gerekiyorsa staging'e prod'dan **maskelenmiş** kopya yükle (Ek A).

## 14. Hızlı başvuru

| Katman | Port | Nerede |
|---|---|---|
| PostgreSQL (Docker) | 127.0.0.1:5432 | `kutuphane-postgres`; DB: `kutuphane` (prod) + `kutuphane_staging` |
| Django/Gunicorn — prod | 127.0.0.1:8000 | `kutuphane-backend.service` · `/srv/kutuphane` |
| Django/Gunicorn — staging | 127.0.0.1:8001 | `kutuphane-staging.service` · `/srv/kutuphane-staging` |
| Nginx | 80 → (443 Faz B) | `/etc/nginx/sites-available/kutuphane` |
| Sırlar | — | `/etc/kutuphane/.env`, `/etc/kutuphane/staging.env` (root, 600) |
| Yayın betikleri | — | `kutuphane/scripts/deploy.sh`, `rollback.sh` |
| Loglar | — | `/var/log/kutuphane/` (gunicorn, staging, deploy, scheduler) |
| Yedekler | — | `/var/backups/kutuphane/` (DB + media, 14 gün) |
| Cron | — | `/etc/cron.d/kutuphane-scheduler`, `kutuphane-backup` |

---

## Ek A. Prod verisinin lokale kopyası (opsiyonel)

Geliştirme **varsayılan olarak lokal örnek veriyle** yürür. Gerçekçi veri
gerektiğinde prod'dan kopya alınır; **kurallar:**

- Lokal makine **asla** prod/staging DB'sine bağlanmaz; yalnız bu makinedeki
  yerel PostgreSQL (`127.0.0.1:5432`) kullanılır.
- Prod kopyası **ayrı bir veritabanı adına** yüklenir (prod DB'ye dokunulmaz).
- Öğrenci/üye kişisel verisi içerdiği için **maskelenmiş** kopya tercih edilir;
  ham veriyi lokalde kalıcı tutma.

```bash
# SUNUCU: kopyayı al
docker exec kutuphane-postgres pg_dump -U kutuphane kutuphane -Fc | gzip > /tmp/prod_kopya.dump.gz

# (YEREL) dosyayı indir
scp kutuphane@<SERVER_IP>:/tmp/prod_kopya.dump.gz /tmp/

# YEREL: ayrı DB adına yükle (prod DB adıyla çakışmasın)
createdb -h 127.0.0.1 -U kutuphane kutuphane_kopya
gunzip -c /tmp/prod_kopya.dump.gz | pg_restore -h 127.0.0.1 -U kutuphane -d kutuphane_kopya --clean --if-exists

# YEREL: bu kopyayla çalışmak için lokal .env'de DB_NAME=kutuphane_kopya yap
# (iş bitince DB_NAME'i normale döndür).
```

> **KVKK notu:** Mümkünse üye e-postalarını/iletişim bilgilerini maskeleyerek
> kullan (ör. `UPDATE kutuphane_app_uye SET ...`); şifreler zaten hash'li gelir.