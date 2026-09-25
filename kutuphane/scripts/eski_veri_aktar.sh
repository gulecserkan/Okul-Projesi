#!/usr/bin/env bash
#
# Eski kütüphane PostgreSQL dump'ından katalog verisini aktarır.
#
#   Kullanım: bash scripts/eski_veri_aktar.sh <kutuphane_eski.dump> <local|prod|staging>
#   Örnek (local)  : bash kutuphane/scripts/eski_veri_aktar.sh ~/Masaüstü/kutuphane_eski.dump local
#   Örnek (sunucu) : sudo bash /srv/kutuphane/kutuphane/scripts/eski_veri_aktar.sh /root/kutuphane_eski.dump prod
#
# Yaptığı iş: dump'ı geçici bir DB'ye (<DB_NAME>_eski) yükler →
# `manage.py eski_veri_aktar` ile ÖNCE dry-run raporu üretir → onay sonrası
# uygular → geçici DB'yi siler.
#
# target = local : bu makinedeki geliştirme DB'si (kutuphane/.env, kutuphane/venv).
# target = prod/staging : sunucudaki servis DB'si. Prod DB'ye istemciden
#   bağlanılmaz; bu betiği SUNUCUDA çalıştırın (dump'ı önce sunucuya kopyalayın).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOSYA="${1:-}"
ORTAM="${2:-prod}"

if [[ -z "$DOSYA" || ! -f "$DOSYA" ]]; then
  echo "Kullanım: $0 <kutuphane_eski.dump> <local|prod|staging>" >&2
  exit 2
fi

case "$ORTAM" in
  local)
    APP="$(cd "$SCRIPT_DIR/.." && pwd)"
    VENV="$APP/venv"
    ENVFILE="$APP/.env"
    ;;
  prod)
    ENVFILE=/etc/kutuphane/.env
    APP=/srv/kutuphane/kutuphane
    VENV=/srv/kutuphane/venv
    ;;
  staging)
    ENVFILE=/etc/kutuphane/staging.env
    APP=/srv/kutuphane-staging/kutuphane
    VENV=/srv/kutuphane-staging/venv
    ;;
  *)
    echo "Geçersiz hedef: $ORTAM (local|prod|staging)" >&2
    exit 2
    ;;
esac

[[ -d "$APP" ]] || { echo "Hata: uygulama dizini yok: $APP" >&2; exit 2; }
[[ -x "$VENV/bin/python" ]] || { echo "Hata: venv bulunamadı: $VENV" >&2; exit 2; }
[[ -f "$ENVFILE" ]] || { echo "Hata: ortam dosyası yok: $ENVFILE" >&2; exit 2; }

get_env() { grep -E "^$1=" "$ENVFILE" | tail -1 | cut -d= -f2-; }
DB_NAME="$(get_env DB_NAME)"
DB_USER="$(get_env DB_USER)"
DB_PASSWORD="$(get_env DB_PASSWORD)"
DB_HOST="$(get_env DB_HOST)"
DB_PORT="$(get_env DB_PORT)"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

ESKI_DB="${DB_NAME}_eski"

pg() { env PGPASSWORD="$DB_PASSWORD" "$@" -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; }
run_manage() {
  ( cd "$APP" && KUTUPHANE_ENV_FILE="$ENVFILE" "$VENV/bin/python" manage.py \
      eski_veri_aktar --eski-db "$ESKI_DB" "$@" )
}

echo "Hedef : $ORTAM  (hedef DB: $DB_NAME, geçici DB: $ESKI_DB)"
echo "Dump  : $DOSYA"

echo "1/5 Geçici veritabanı oluşturuluyor…"
pg dropdb --if-exists "$ESKI_DB"
pg createdb "$ESKI_DB"

echo "2/5 Dump yükleniyor…"
pg pg_restore --no-owner --no-privileges -d "$ESKI_DB" "$DOSYA"

echo "3/5 Dry-run raporu:"
run_manage --dry-run --odunctekileri-mevcut-yap

read -r -p "4/5 '$DB_NAME' üzerine UYGULAMAK için EVET yazın: " ONAY
if [[ "$ONAY" != "EVET" ]]; then
  echo "İptal edildi; geçici DB siliniyor."
  pg dropdb --if-exists "$ESKI_DB"
  exit 1
fi

run_manage --odunctekileri-mevcut-yap

echo "5/5 Geçici veritabanı siliniyor…"
pg dropdb --if-exists "$ESKI_DB"

echo "Tamamlandı: $DB_NAME güncellendi."
