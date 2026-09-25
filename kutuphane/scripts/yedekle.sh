#!/usr/bin/env bash
#
# Kütüphane periyodik PostgreSQL yedeği.
#
#   Kullanım: sudo bash scripts/yedekle.sh [prod|staging]
#   Örnek   : sudo bash scripts/yedekle.sh prod
#
# pg_dump -Fc ile tam veritabanı dökümü alır, openssl ile şifreler ve
# /var/backups/kutuphane altında saklar; RETENTION_DAYS günden eski
# yedekleri siler. Zamanlama: /etc/cron.d/kutuphane-yedek
# (kaynak: scripts/cron.d/kutuphane-yedek).
#
# Gereksinim: /etc/kutuphane/.env içinde DB_* ve YEDEK_SIFRE tanımlı olmalı.
#
set -euo pipefail

ORTAM="${1:-prod}"
case "$ORTAM" in
  prod)    ENVFILE=/etc/kutuphane/.env ;;
  staging) ENVFILE=/etc/kutuphane/staging.env ;;
  *) echo "Kullanım: $0 [prod|staging]" >&2; exit 2 ;;
esac

BACKUP_DIR=/var/backups/kutuphane
RETENTION_DAYS="${RETENTION_DAYS:-14}"
LOG=/var/log/kutuphane/yedek.log
mkdir -p "$BACKUP_DIR" "$(dirname "$LOG")"

log() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

get_env() { grep -E "^$1=" "$ENVFILE" | tail -1 | cut -d= -f2-; }

if [[ ! -f "$ENVFILE" ]]; then
  echo "Hata: ortam dosyası bulunamadı: $ENVFILE" >&2
  exit 2
fi

DB_NAME="$(get_env DB_NAME)"
DB_USER="$(get_env DB_USER)"
DB_HOST="$(get_env DB_HOST)"
DB_PORT="$(get_env DB_PORT)"
DB_PASSWORD="$(get_env DB_PASSWORD)"
YEDEK_SIFRE="$(get_env YEDEK_SIFRE)"

if [[ -z "$DB_NAME" || -z "$DB_USER" ]]; then
  echo "Hata: $ENVFILE içinde DB_NAME/DB_USER tanımlı değil." >&2
  exit 2
fi
if [[ -z "$YEDEK_SIFRE" ]]; then
  echo "Hata: YEDEK_SIFRE tanımlı değil (yedek şifrelemesi için zorunlu)." >&2
  exit 2
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/kutuphane_${ORTAM}_${STAMP}.dump.enc"
TMP="${OUT}.tmp"

cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

log "Yedek başlıyor — ortam=$ORTAM db=$DB_NAME"

PGPASSWORD="$DB_PASSWORD" pg_dump -Fc \
  -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass "pass:$YEDEK_SIFRE" -out "$TMP"

if [[ ! -s "$TMP" ]]; then
  log "HATA: yedek dosyası boş — geri yükleme kullanılamaz."
  exit 1
fi

mv "$TMP" "$OUT"
log "Yedek alındı: $OUT ($(du -h "$OUT" | cut -f1))"

find "$BACKUP_DIR" -type f -name "kutuphane_${ORTAM}_*.dump.enc" \
  -mtime +"$RETENTION_DAYS" -print -delete | while read -r old; do
  log "Saklama süresi doldu, silindi: $old"
done

log "Bitti."
