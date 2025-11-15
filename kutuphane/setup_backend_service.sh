#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Bu scripti sudo ile çalıştırın (örn. sudo ./setup_backend_service.sh)" >&2
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="kutuphane-backend"
USER_NAME="${SUDO_USER:-$(logname)}"
GROUP_NAME="$(id -gn "$USER_NAME")"
VENV_DIR="${PROJECT_ROOT}/venv"
GUNICORN_BIN="${VENV_DIR}/bin/gunicorn"
LOG_DIR="/var/log/kutuphane"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
CRON_FILE="/etc/cron.d/kutuphane-scheduler"
BIND_ADDRESS="0.0.0.0:8000"
WORKERS="3"

if [[ ! -x "$GUNICORN_BIN" ]]; then
    echo "gunicorn bulunamadı: $GUNICORN_BIN. Önce venv içinde 'pip install gunicorn' çalıştırın." >&2
    exit 1
fi

mkdir -p "$LOG_DIR"
chown "$USER_NAME":"$GROUP_NAME" "$LOG_DIR"

cat <<SERVICE > "$SERVICE_FILE"
[Unit]
Description=Kutuphane Django Backend
After=network.target

[Service]
User=${USER_NAME}
Group=${GROUP_NAME}
WorkingDirectory=${PROJECT_ROOT}
Environment="PATH=${VENV_DIR}/bin"
ExecStart=${GUNICORN_BIN} --workers ${WORKERS} --bind ${BIND_ADDRESS} kutuphane.wsgi:application
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/gunicorn.log
StandardError=append:${LOG_DIR}/gunicorn.log

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo "Systemd servisi oluşturuldu: $SERVICE_FILE"

touch "${LOG_DIR}/scheduler.log"
chown "$USER_NAME":"$GROUP_NAME" "${LOG_DIR}/scheduler.log"

cat <<CRON > "$CRON_FILE"
*/15 * * * * ${USER_NAME} source ${VENV_DIR}/bin/activate && cd ${PROJECT_ROOT} && python manage.py run_scheduled_tasks >> ${LOG_DIR}/scheduler.log 2>&1
CRON

chmod 644 "$CRON_FILE"
service cron reload >/dev/null 2>&1 || true

echo "Cron girdisi oluşturuldu: $CRON_FILE"
echo "Kurulum tamamlandı. Servis durumunu 'systemctl status ${SERVICE_NAME}' ile kontrol edebilirsiniz."
