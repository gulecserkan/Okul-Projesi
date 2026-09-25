#!/usr/bin/env bash
#
# Kütüphane şifreli yedeğinden veritabanı geri yükleme.
#
#   Kullanım: sudo bash scripts/geri-yukle.sh <yedek.dump.enc> [prod|staging]
#   Örnek   : sudo bash scripts/geri-yukle.sh /var/backups/kutuphane/kutuphane_prod_20260101_033000.dump.enc prod
#
# UYARI: --clean ile mevcut nesneler SİLİNİP yeniden oluşturulur.
# Gereksinim: /etc/kutuphane/.env içinde DB_* ve YEDEK_SIFRE tanımlı olmalı.
#
set -euo pipefail

DOSYA="${1:-}"
ORTAM="${2:-prod}"

if [[ -z "$DOSYA" || ! -f "$DOSYA" ]]; then
  echo "Kullanım: $0 <yedek.dump.enc> [prod|staging]" >&2
  exit 2
fi

case "$ORTAM" in
  prod)    ENVFILE=/etc/kutuphane/.env ;;
  staging) ENVFILE=/etc/kutuphane/staging.env ;;
  *) echo "Geçersiz ortam: $ORTAM" >&2; exit 2 ;;
esac

get_env() { grep -E "^$1=" "$ENVFILE" | tail -1 | cut -d= -f2-; }

DB_NAME="$(get_env DB_NAME)"
DB_USER="$(get_env DB_USER)"
DB_HOST="$(get_env DB_HOST)"
DB_PORT="$(get_env DB_PORT)"
DB_PASSWORD="$(get_env DB_PASSWORD)"
YEDEK_SIFRE="$(get_env YEDEK_SIFRE)"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

TMP="$(mktemp /tmp/kutuphane-restore.XXXXXX.dump)"
trap 'rm -f "$TMP"' EXIT

echo "DİKKAT: '$DB_NAME' veritabanı '$DOSYA' ile DEĞİŞTİRİLECEK (mevcut nesneler silinir)."
read -r -p "Onaylamak için EVET yazın: " ONAY
if [[ "$ONAY" != "EVET" ]]; then
  echo "İptal edildi." >&2
  exit 1
fi

openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$YEDEK_SIFRE" -in "$DOSYA" -out "$TMP"

PGPASSWORD="$DB_PASSWORD" pg_restore --clean --if-exists --no-owner \
  -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$TMP"

echo "Geri yükleme tamamlandı: $DB_NAME"
