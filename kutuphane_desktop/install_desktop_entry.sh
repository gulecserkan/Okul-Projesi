#!/usr/bin/env bash
set -euo pipefail

APP_NAME="kutuphane"
APP_TITLE="Kütüphane"
APP_COMMENT="Okul kütüphanesi masaüstü istemcisi"
APP_WMCLASS="kutuphane"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$SCRIPT_DIR"
ICON_SRC="${APP_ROOT}/resources/icons/library.png"

detect_user() {
    if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
        echo "${SUDO_USER}"
        return
    fi
    owner="$(stat -c '%U' "${APP_ROOT}" 2>/dev/null || true)"
    if [ -n "${owner}" ] && [ "${owner}" != "root" ]; then
        echo "${owner}"
        return
    fi
    echo "$(logname 2>/dev/null || echo root)"
}

TARGET_USER="$(detect_user)"
TARGET_GROUP="$(id -gn "${TARGET_USER}" 2>/dev/null || echo "${TARGET_USER}")"
TARGET_HOME="$(eval echo "~${TARGET_USER}")"
DESKTOP_DIR="${TARGET_HOME}/.local/share/applications"
ICON_DIR="${TARGET_HOME}/.local/share/icons/hicolor/256x256/apps"
BIN_DIR="${TARGET_HOME}/.local/bin"
EXEC_WRAPPER="${BIN_DIR}/${APP_NAME}"
DESKTOP_FILE="${DESKTOP_DIR}/${APP_NAME}.desktop"
ICON_TARGET="${ICON_DIR}/${APP_NAME}.png"

mkdir -p "$DESKTOP_DIR" "$ICON_DIR" "$BIN_DIR"

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
chown "${TARGET_USER}:${TARGET_GROUP}" "$EXEC_WRAPPER"

install -m 644 "$ICON_SRC" "$ICON_TARGET"
chown "${TARGET_USER}:${TARGET_GROUP}" "$ICON_TARGET"

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
StartupWMClass=${APP_WMCLASS}
DESKTOP
chown "${TARGET_USER}:${TARGET_GROUP}" "$DESKTOP_FILE"

sudo -u "${TARGET_USER}" update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache "${TARGET_HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Kütüphane masaüstü kısayolu ${DESKTOP_FILE} konumuna yüklendi."
