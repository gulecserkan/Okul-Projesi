#!/usr/bin/env bash
#
# Kütüphane masaüstü uygulaması kurulum betiği (paket içinde gelir).
# Paketi açtığınız klasörde çalıştırın:
#
#   mkdir -p ~/.local/share/kutuphane-masaustu
#   tar -xzf kutuphane-masaustu-vX.Y.Z-linux-x64.tar.gz -C ~/.local/share/kutuphane-masaustu
#   bash ~/.local/share/kutuphane-masaustu/kur.sh
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

echo "Kuruldu: $INSTALL"
echo "Menüde 'Kütüphane Yönetim Sistemi' olarak görünür."
echo "Sunucu adresini uygulamanın giriş ekranından ayarlayın (varsayılan http://127.0.0.1:8000/api)."
echo "Uygulama açılışta güncellemeleri bu kurulum klasörüne otomatik uygular."
