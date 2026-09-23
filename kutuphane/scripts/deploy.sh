#!/usr/bin/env bash
#
# Kütüphane sunucu yayın betiği.
#
#   Kullanım: sudo bash scripts/deploy.sh <prod|staging> <tag>
#   Örnek   : sudo bash scripts/deploy.sh prod v1.1.0
#
# Sunucu düzeni (monorepo): repo kökü /srv/kutuphane, Django uygulaması
# /srv/kutuphane/kutuphane (manage.py burada).
#
# Yaptığı iş: etiketi çeker → bağımlılıkları kurar → YEDEK alır →
# migration + collectstatic → servisi yeniden başlatır → sağlık kontrolü.
# Sağlık kontrolü başarısız olursa hata ile çıkar (geri dönüş: rollback.sh).
#
set -euo pipefail

# Betik, git checkout sırasında kendi kendini değiştirmesin diye geçici
# kopyadan yeniden çalıştırılır.
if [[ "${KUTUPHANE_DEPLOY_REEXEC:-0}" != "1" ]]; then
  _tmp="$(mktemp /tmp/kutuphane-deploy.XXXXXX.sh)"
  cp "$0" "$_tmp"
  KUTUPHANE_DEPLOY_REEXEC=1 exec bash "$_tmp" "$@"
fi

ORTAM="${1:-}"
TAG="${2:-}"

if [[ "$ORTAM" != "prod" && "$ORTAM" != "staging" ]]; then
  echo "Kullanım: $0 <prod|staging> <tag>" >&2
  exit 2
fi
if [[ -z "$TAG" ]]; then
  echo "Hata: sürüm etiketi (tag) verilmedi. Örnek: $0 $ORTAM v1.1.0" >&2
  exit 2
fi

case "$ORTAM" in
  prod)
    REPO=/srv/kutuphane
    SERVICE=kutuphane-backend
    ENVFILE=/etc/kutuphane/.env
    PORT=8000
    ;;
  staging)
    REPO=/srv/kutuphane-staging
    SERVICE=kutuphane-staging
    ENVFILE=/etc/kutuphane/staging.env
    PORT=8001
    ;;
esac
APP="$REPO/kutuphane"
VENV="$REPO/venv"

BACKUP_DIR=/var/backups/kutuphane
LOG=/var/log/kutuphane/deploy.log
mkdir -p "$BACKUP_DIR" "$(dirname "$LOG")"

log() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

get_env() {
  # .env dosyasındaki bir anahtarın değerini güvenle okur (source etmeden).
  grep -E "^$1=" "$ENVFILE" | tail -1 | cut -d= -f2-
}

if [[ ! -f "$ENVFILE" ]]; then
  echo "Hata: ortam dosyası bulunamadı: $ENVFILE" >&2
  exit 2
fi

DB_USER="$(get_env DB_USER)"
DB_NAME="$(get_env DB_NAME)"
if [[ -z "$DB_USER" || -z "$DB_NAME" ]]; then
  echo "Hata: $ENVFILE içinde DB_USER/DB_NAME tanımlı değil." >&2
  exit 2
fi

log "DEPLOY başladı — ortam=$ORTAM tag=$TAG db=$DB_NAME"

cd "$REPO"
PREV="$(runuser -u kutuphane -- git describe --tags --exact-match 2>/dev/null \
        || runuser -u kutuphane -- git rev-parse --short HEAD)"

runuser -u kutuphane -- git fetch --tags --prune
runuser -u kutuphane -- git checkout --force "$TAG"

runuser -u kutuphane -- "$VENV/bin/pip" install -q -r "$APP/requirements.txt"

log "Migration öncesi yedek alınıyor ($DB_NAME)"
docker exec kutuphane-postgres pg_dump -U "$DB_USER" "$DB_NAME" -Fc \
  | gzip > "$BACKUP_DIR/pre_${ORTAM}_${TAG}_$(date +%F_%H%M%S).dump.gz"

runuser -u kutuphane -- env -C "$APP" "$VENV/bin/python" manage.py migrate --noinput
runuser -u kutuphane -- env -C "$APP" "$VENV/bin/python" manage.py collectstatic --noinput

systemctl restart "$SERVICE"

for _ in 1 2 3 4 5; do
  sleep 2
  if curl -fsS "http://127.0.0.1:${PORT}/api/health/" >/dev/null 2>&1; then
    log "BAŞARILI — $ORTAM $TAG yayında (önceki: $PREV)"
    exit 0
  fi
done

log "HATA — sağlık kontrolü başarısız. Geri dönüş: sudo bash scripts/rollback.sh $ORTAM $PREV"
exit 1
