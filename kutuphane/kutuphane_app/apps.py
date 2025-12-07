from django.apps import AppConfig
from django.contrib import admin
import os


def get_version(default="dev"):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates = [
        os.path.join(base_dir, "VERSION"),
        os.path.join(base_dir, "..", "VERSION"),
    ]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                ver = f.read().strip()
                if ver:
                    return ver
        except OSError:
            continue
    return default


class KutuphaneAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kutuphane_app'

    def ready(self):
        ver = get_version()
        admin.site.site_header = f"Kütüphane Yönetim Sistemi - Versiyon {ver}"
        admin.site.site_title = f"Kütüphane Admin | {ver}"
        admin.site.index_title = "Yönetim Paneli"
