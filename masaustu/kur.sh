#!/usr/bin/env bash
#
# Kütüphane masaüstü uygulaması kurulum betiği (paket içinde gelir).
# Paketi açtığınız klasörde çalıştırın:
#
#   mkdir -p ~/.local/share/kutuphane-masaustu
#   tar -xzf kutuphane-masaustu-vX.Y.Z-linux-x64.tar.gz -C ~/.local/share/kutuphane-masaustu
#   bash ~/.local/share/kutuphane-masaustu/kur.sh
#
# Kısayol: uygulama menüsüne + masaüstüne yazılır. Masaüstü kısayolu istenmiyorsa
#   MASAUSTU_MASAUSTU_KISAYOL=0 bash kur.sh
#
set -euo pipefail

INSTALL="$(cd "$(dirname "$0")" && pwd)"
EXE="$INSTALL/masaustu"
chmod +x "$EXE"

APPDIR="${HOME}/.local/share/applications"
mkdir -p "$APPDIR"

ICON=""
if [[ -f "$INSTALL/data/flutter_assets/assets/library.png" ]]; then
  mkdir -p "${HOME}/.local/share/icons"
  cp -f "$INSTALL/data/flutter_assets/assets/library.png" \
        "${HOME}/.local/share/icons/kutuphane-masaustu.png"
  ICON="${HOME}/.local/share/icons/kutuphane-masaustu.png"
fi

cat > "$APPDIR/kutuphane-masaustu.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Kütüphane Yönetim Sistemi
Comment=Okul kütüphanesi yönetim uygulaması (personel/admin)
Exec=$EXE
${ICON:+Icon=$ICON}
Terminal=false
Categories=Office;Education;
DESK
chmod +x "$APPDIR/kutuphane-masaustu.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPDIR" >/dev/null 2>&1 || true
fi

# Masaüstü kısayolu: XDG_DESKTOP_DIR -> xdg-user-dir -> ~/Desktop / ~/Masaüstü
MASADESI="${XDG_DESKTOP_DIR:-}"
if [[ -z "$MASADESI" ]] && command -v xdg-user-dir >/dev/null 2>&1; then
  MASADESI="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
fi
[[ -n "$MASADESI" && "$MASADESI" == "$HOME" ]] && MASADESI=""
if [[ -z "$MASADESI" && -d "${HOME}/Masaüstü" ]]; then
  MASADESI="${HOME}/Masaüstü"
elif [[ -z "$MASADESI" && -d "${HOME}/Desktop" ]]; then
  MASADESI="${HOME}/Desktop"
fi

KISAYOL="${APPDIR}/kutuphane-masaustu.desktop"
if [[ "${MASAUSTU_MASAUSTU_KISAYOL:-1}" == "1" && -n "$MASADESI" ]]; then
  mkdir -p "$MASADESI"
  cp -f "$KISAYOL" "${MASADESI}/kutuphane-masaustu.desktop"
  chmod +x "${MASADESI}/kutuphane-masaustu.desktop"
  # GNOME "güvenilmeyen uygulama" uyarısını kaldır (yoksa atlanır)
  if command -v gio >/dev/null 2>&1; then
    gio set "${MASADESI}/kutuphane-masaustu.desktop" metadata::trusted true \
      >/dev/null 2>&1 || true
  fi
  echo "Masaüstü kısayolu: ${MASADESI}/kutuphane-masaustu.desktop"
fi

echo "Kuruldu: $INSTALL"
echo "Menüde 'Kütüphane Yönetim Sistemi' olarak görünür."
echo "Sunucu adresini uygulamanın giriş ekranından ayarlayın (varsayılan http://127.0.0.1:8000/api)."
echo "Uygulama açılışta güncellemeleri bu kurulum klasörüne otomatik uygular."
