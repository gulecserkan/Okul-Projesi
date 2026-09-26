#!/usr/bin/env bash
#
# Kütüphane masaüstü uygulaması — tek komutla uzaktan kurulum (K13.10).
#
# Hedef bilgisayarda:
#   bash <(curl -fsS http://89.252.153.171/masaustu/uzaktan-kur.sh)
#
# Sunucu adayları sırayla denenir (alan adı → genel IP). İlk yanıt verenden
# güncel paket indirilir ve ~/.local/share/kutuphane-masaustu içine kurulur.
# Elle origin vermek için: MASAUSTU_ORIGIN=https://ornek bash uzaktan-kur.sh
#
set -euo pipefail

INSTALL="${HOME}/.local/share/kutuphane-masaustu"

# Aday origin'ler (öncelik sıralı). İlk geçerli sürüm bilgisi veren seçilir.
ADAYLAR=()
[[ -n "${MASAUSTU_ORIGIN:-}" ]] && ADAYLAR+=("${MASAUSTU_ORIGIN}")
ADAYLAR+=("https://okulkitapligi.tr" "http://89.252.153.171")

command -v curl >/dev/null || { echo "Hata: curl bulunamadı." >&2; exit 1; }
command -v tar  >/dev/null || { echo "Hata: tar bulunamadı." >&2; exit 1; }

ORIGIN=""
PAKET_YOLU=""
for O in "${ADAYLAR[@]}"; do
  echo "Sunucu deneniyor: $O"
  S="$(curl -fsS --max-time 6 "$O/api/masaustu/surum/" 2>/dev/null)" || continue
  U="$(printf '%s' "$S" | sed -n 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
  if [[ -n "$U" ]]; then
    ORIGIN="$O"
    PAKET_YOLU="$U"
    break
  fi
done

[[ -n "$PAKET_YOLU" ]] || {
  echo "Hata: sunuculara ulaşılamadı." >&2
  echo "Sunucu adresini MASAUSTU_ORIGIN ile verebilirsiniz:" >&2
  echo "  MASAUSTU_ORIGIN=http://<adres> bash uzaktan-kur.sh" >&2
  exit 1
}

GECICI="$(mktemp -d)"
trap 'rm -rf "$GECICI"' EXIT

echo "Paket indiriliyor: ${ORIGIN}${PAKET_YOLU}"
curl -fL --retry 3 -o "$GECICI/paket.tar.gz" "${ORIGIN}${PAKET_YOLU}"

mkdir -p "$INSTALL"
echo "Açılıyor: $INSTALL"
tar -xzf "$GECICI/paket.tar.gz" -C "$INSTALL"

bash "$INSTALL/kur.sh"

echo
echo "Kurulum tamamlandı. Menüde 'Kütüphane Yönetim Sistemi' olarak görünür."
echo "Sunucu adresini uygulama giriş ekranından da değiştirebilirsiniz."
