import requests, json, os
from core.config import get_api_base_url, TOKEN_FILE

_access_token = None
_refresh_token = None
_current_username = None
_current_full_name = None
_current_role = None

def load_tokens():
    global _access_token, _refresh_token, _current_username, _current_full_name, _current_role
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            _access_token = data.get("access")
            _refresh_token = data.get("refresh")
            _current_username = data.get("username")
            _current_full_name = data.get("full_name")
            _current_role = data.get("role")

def save_tokens():
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access": _access_token,
            "refresh": _refresh_token,
            "username": _current_username,
            "full_name": _current_full_name,
            "role": _current_role,
        }, f)

def login(username, password):
    global _access_token, _refresh_token, _current_username, _current_full_name, _current_role
    _current_username = None
    _current_full_name = None
    _current_role = None
    url = _build_url("token/")
    resp = requests.post(url, json={"username": username, "password": password})
    if resp.status_code == 200:
        data = resp.json()
        _access_token = data.get("access")
        _refresh_token = data.get("refresh")
        _current_username = username
        _current_full_name = data.get("full_name") or data.get("username")
        _current_role = data.get("role")
        save_tokens()
        return True
    return False

def get_access_token():
    return _access_token

def get_refresh_token():
    return _refresh_token

def refresh_access_token():
    """Refresh token ile yeni access alır."""
    global _access_token, _refresh_token, _current_full_name, _current_role
    if not _refresh_token:
        return False
    url = _build_url("token/refresh/")
    resp = requests.post(url, json={"refresh": _refresh_token})
    if resp.status_code == 200:
        data = resp.json()
        _access_token = data.get("access")
        if data.get("full_name"):
            _current_full_name = data.get("full_name")
        if data.get("role"):
            _current_role = data.get("role")
        save_tokens()
        return True
    return False

def logout():
    global _access_token, _refresh_token, _current_username, _current_full_name, _current_role
    _access_token, _refresh_token, _current_username, _current_full_name, _current_role = None, None, None, None, None
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)


def get_current_username():
    return _current_username


def get_current_full_name():
    return _current_full_name or _current_username


def get_current_role():
    return _current_role


def change_password(current_password: str, new_password: str, new_password_confirm: str):
    token = get_access_token()
    if not token:
        return False, "Oturum doğrulanamadı."

    url = _build_url("change-password/")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "current_password": current_password,
        "new_password": new_password,
        "new_password_confirm": new_password_confirm,
    }
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 401 and refresh_access_token():
        token = get_access_token()
        headers["Authorization"] = f"Bearer {token}" if token else headers.get("Authorization")
        resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 200:
        return True, "Şifre güncellendi."
    try:
        data = resp.json()
        detail = data.get("detail") if isinstance(data, dict) else str(data)
    except ValueError:
        detail = resp.text or "Şifre güncellenemedi."
    if isinstance(detail, list):
        detail = "\n".join(map(str, detail))
    return False, detail
def _build_url(endpoint):
    base = get_api_base_url().rstrip('/')
    endpoint = endpoint.lstrip('/')
    return f"{base}/{endpoint}"
