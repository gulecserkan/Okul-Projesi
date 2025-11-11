#!/usr/bin/env bash
set -euo pipefail

APP_NAME="kutuphane"
APP_TITLE="Kütüphane"
APP_COMMENT="Okul kütüphanesi masaüstü istemcisi"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$SCRIPT_DIR"
ICON_SRC="${APP_ROOT}/resources/icons/library.png"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
EXEC_WRAPPER="${HOME}/.local/bin/${APP_NAME}"
DESKTOP_FILE="${DESKTOP_DIR}/${APP_NAME}.desktop"
ICON_TARGET="${ICON_DIR}/${APP_NAME}.png"

mkdir -p "$DESKTOP_DIR" "$ICON_DIR" "${HOME}/.local/bin"

cat <<LAUNCH > "$EXEC_WRAPPER"
#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${APP_ROOT}"
if [ ! -d "$APP_ROOT" ]; then
    echo "Uygulama dizini bulunamadı: $APP_ROOT" >&2
    exit 1
fi
cd "$APP_ROOT"
source "$APP_ROOT/venv/bin/activate"
exec python "$APP_ROOT/main.py" "$@"
LAUNCH
chmod +x "$EXEC_WRAPPER"

install -m 644 "$ICON_SRC" "$ICON_TARGET"

cat <<DESKTOP > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=${APP_TITLE}
Comment=${APP_COMMENT}
Exec=${EXEC_WRAPPER}
Icon=${APP_NAME}
Terminal=false
Categories=Education;Office;
StartupNotify=true
DESKTOP

update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Kütüphane masaüstü kısayolu ${DESKTOP_FILE} konumuna yüklendi."
