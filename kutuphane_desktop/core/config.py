import json
import os
from urllib.parse import urlparse


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api"
TOKEN_FILE = "token.json"
SETTINGS_FILE = "settings.json"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)


def get_api_base_url():
    settings = load_settings()
    url = settings.get("api", {}).get("base_url", DEFAULT_API_BASE_URL)
    return normalize_api_base(url)


def set_api_base_url(url):
    settings = load_settings()
    api_cfg = settings.setdefault("api", {})
    api_cfg["base_url"] = normalize_api_base(url)
    save_settings(settings)


def normalize_api_base(url):
    if not url:
        return DEFAULT_API_BASE_URL
    url = url.strip()
    if '://' not in url:
        url = f"http://{url}"
    parsed = urlparse(url)
    path = parsed.path or ''
    if not path:
        path = '/api'
    else:
        segments = [seg for seg in path.split('/') if seg]
        if not segments or segments[-1].lower() != 'api':
            path = path.rstrip('/') + '/api'
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    return normalized.rstrip('/')


# backward compatibility – avoid using directly, prefer get_api_base_url()
API_BASE_URL = get_api_base_url()
