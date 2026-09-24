#!/usr/bin/env bash
#
# Kütüphane geri dönüş (rollback) betiği.
#
#   Kullanım: sudo bash scripts/rollback.sh <prod|staging> <onceki-tag>
#   Örnek   : sudo bash scripts/rollback.sh prod v1.0.0
#
# Kodu önceki etikete döndürür ve servisi yeniden başlatır.
# NOT: Veritabanı otomatik geri alınmaz. Yeni sürüm şemayı geriye uyumsuz
# biçimde değiştirdiyse, deploy sırasında alınan yedeği elle geri yükle
# (aşağıdaki mesajda komut yazdırılır).
#
set -euo pipefail

if [[ "${KUTUPHANE_ROLLBACK_REEXEC:-0}" != "1" ]]; then
  _tmp="$(mktemp /tmp/kutuphane-rollback.XXXXXX.sh)"
  cp "$0" "$_tmp"
  KUTUPHANE_ROLLBACK_REEXEC=1 exec bash "$_tmp" "$@"
fi

ORTAM="${1:-}"
TAG="${2:-}"

if [[ "$ORTAM" != "prod" && "$ORTAM" != "staging" ]]; then
  echo "Kullanım: $0 <prod|staging> <onceki-tag>" >&2
  exit 2
fi
if [[ -z "$TAG" ]]; then
  echo "Hata: geri dönülecek etiket (tag) verilmedi." >&2
  exit 2
fi

case "$ORTAM" in
  prod)
    REPO=/srv/kutuphane
    SERVICE=kutuphane-backend
    PORT=8000
    ;;
  staging)
    REPO=/srv/kutuphane-staging
    SERVICE=kutuphane-staging
    PORT=8001
    ;;
esac
APP="$REPO/kutuphane"
VENV="$REPO/venv"

BACKUP_DIR=/var/backups/kutuphane
LOG=/var/log/kutuphane/deploy.log
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

log "ROLLBACK başladı — ortam=$ORTAM tag=$TAG"

cd "$REPO"
runuser -u kutuphane -- git fetch --tags --prune
runuser -u kutuphane -- git checkout --force "$TAG"
runuser -u kutuphane -- "$VENV/bin/pip" install -q -r "$APP/requirements.txt"
runuser -u kutuphane -- env -C "$APP" "$VENV/bin/python" manage.py migrate --noinput
runuser -u kutuphane -- env -C "$APP" "$VENV/bin/python" manage.py collectstatic --noinput

systemctl restart "$SERVICE"

for _ in 1 2 3 4 5; do
  sleep 2
  if curl -fsS "http://127.0.0.1:${PORT}/api/health/" >/dev/null 2>&1; then
    log "BAŞARILI — $ORTAM $TAG sürümüne dönüldü"
    echo "Şema sorunu yaşıyorsan yedeği geri yükle:"
    echo "  ls -t $BACKUP_DIR/pre_${ORTAM}_*.dump.gz | head -1"
    echo "  zcat <yedek> | sudo -u postgres pg_restore -d <DB_NAME> --clean --if-exists"
    exit 0
  fi
done

log "HATA — rollback sonrası sağlık kontrolü başarısız. journalctl -u $SERVICE"
exit 1
