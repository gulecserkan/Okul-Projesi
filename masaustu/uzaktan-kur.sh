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
# Bağımlılıklar:
#   Uygulama önceden derlenmiş olduğundan Flutter GEREKMEZ; yalnız GTK3 çalışma
#   zamanı gerekir (masaüstü Pardus/Debian kurulumlarında hazır gelir). Eksik
#   temel paketler, parolasız sudo varsa otomatik kurulur; yoksa komut önerilir.
#   - Kapatmak için:            MASAUSTU_BAGIMLILIK=0
#   - Ek paket (örn. termal yazıcı USB için) eklemek için:
#       MASAUSTU_EK_PAKETLER="libusb-1.0-0" bash uzaktan-kur.sh
#
set -euo pipefail

INSTALL="${HOME}/.local/share/kutuphane-masaustu"

# --- Sistem bağımlılıkları (veri tabanlı) -----------------------------------
# Zorunlu çalışma zamanı kütüphaneleri (soname → kurulacak paket ipucu).
# Soname ile kontrol edilir; bazı dağıtımlarda paket adı değişebilir
# (örn. Ubuntu t64: libgtk-3-0t64) — apt alias'ı kendisi çözer.
declare -A ZORUNLU=(
  ["libgtk-3.so.0"]="libgtk-3-0"
)
# K14 yazdırma: `lpstat`/`lp` (CUPS istemcisi) fiş/etiket basımı için zorunludur.
declare -A CUPS_KOMMUT=(
  ["lpstat"]="cups-client cups"
)
# Ek/yeteneğe bağlı paketler boşlukla ayrılır (varsayılan boş):
#   USB termal yazıcı için: MASAUSTU_EK_PAKETLER="libusb-1.0-0"
BAGIMLILIK="${MASAUSTU_BAGIMLILIK:-1}"

_ldconfig() {
  if command -v ldconfig >/dev/null 2>&1; then command -v ldconfig
  elif [[ -x /sbin/ldconfig ]]; then echo /sbin/ldconfig
  fi
}

bagimliliklari_kur() {
  if [[ "$BAGIMLILIK" != "1" ]]; then
    echo "Bağımlılık kontrolü atlandı (MASAUSTU_BAGIMLILIK=0)."
    return 0
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get bulunamadı; bağımlılık kontrolü atlandı."
    return 0
  fi

  local eksik=() paket soname
  local ldconfig_bin
  ldconfig_bin="$(_ldconfig)"

  for soname in "${!ZORUNLU[@]}"; do
    if [[ -n "$ldconfig_bin" ]] && "$ldconfig_bin" -p 2>/dev/null | grep -q "$soname"; then
      continue
    elif [[ -z "$ldconfig_bin" ]] && dpkg-query -W -f='${Status}' "${ZORUNLU[$soname]}" 2>/dev/null | grep -q "install ok installed"; then
      continue
    fi
    eksik+=("${ZORUNLU[$soname]}")
  done

  for paket in ${MASAUSTU_EK_PAKETLER:-}; do
    dpkg-query -W -f='${Status}' "$paket" 2>/dev/null \
      | grep -q "install ok installed" || eksik+=("$paket")
  done

  # K14 yazdırma: lpstat/lp yoksa cups-client (+ cups) kurulur.
  for komut in "${!CUPS_KOMMUT[@]}"; do
    if command -v "$komut" >/dev/null 2>&1; then
      continue
    fi
    for pkt in ${CUPS_KOMMUT[$komut]}; do
      dpkg-query -W -f='${Status}' "$pkt" 2>/dev/null \
        | grep -q "install ok installed" || eksik+=("$pkt")
    done
  done

  if (( ${#eksik[@]} == 0 )); then
    echo "Sistem bağımlılıkları tam."
    return 0
  fi

  mapfile -t eksik < <(printf '%s\n' "${eksik[@]}" | sort -u)
  echo "Eksik sistem paketleri: ${eksik[*]}"
  if sudo -n true 2>/dev/null; then
    echo "Kuruluyor: ${eksik[*]}"
    if sudo apt-get install -y "${eksik[@]}"; then
      echo "Bağımlılıklar kuruldu."
    else
      echo "Uyarı: bazı bağımlılıklar kurulamadı." >&2
      echo "Elle deneyin: sudo apt-get install -y ${eksik[*]}" >&2
    fi
  else
    echo "Uyarı: kurulum için yönetici (sudo) gerekiyor. Elle çalıştırın:" >&2
    echo "  sudo apt-get install -y ${eksik[*]}" >&2
  fi
}

# Aday origin'ler (öncelik sıralı). İlk geçerli sürüm bilgisi veren seçilir.
ADAYLAR=()
[[ -n "${MASAUSTU_ORIGIN:-}" ]] && ADAYLAR+=("${MASAUSTU_ORIGIN}")
ADAYLAR+=("https://okulkitapligi.tr" "http://89.252.153.171")

command -v curl >/dev/null || { echo "Hata: curl bulunamadı." >&2; exit 1; }
command -v tar  >/dev/null || { echo "Hata: tar bulunamadı." >&2; exit 1; }

bagimliliklari_kur

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
