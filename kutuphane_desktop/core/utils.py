# Ortak yardımcı fonksiyonlar
import datetime
from typing import Any

import requests
from api import auth

TURKISH_MONTHS = [
    "Oca", "Şub", "Mar", "Nis", "May", "Haz",
    "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"
]


class _OfflineResponse:
    """requests.Response benzeri hata yanıtı."""

    def __init__(self, url: str, error: BaseException):
        message = str(error) or error.__class__.__name__
        self.status_code = 0
        self.url = url
        self.text = message
        self.reason = message
        self.headers: dict[str, Any] = {}
        self.error_message = message
        self._error = message

    def json(self):  # pragma: no cover - yalnızca hata durumunda çağrılır
        raise ValueError(self._error)

    @property
    def ok(self) -> bool:
        return False


def format_date(value):
    """
    Girdi tarihini '01 Nis 2025' formatına çevirir. Desteklenen tipler:
    - datetime.datetime / datetime.date
    - ISO tarih/saat veya 'YYYY-MM-DD' benzeri stringler
    - Boş/string dışı değerler -> boş string
    """
    if value in (None, ""):
        return ""

    if isinstance(value, datetime.datetime):
        dt = value
    elif isinstance(value, datetime.date):
        dt = datetime.datetime.combine(value, datetime.time())
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        candidate = text.replace("Z", "+00:00")
        try:
            dt = datetime.datetime.fromisoformat(candidate)
        except ValueError:
            try:
                dt = datetime.datetime.strptime(text[:10], "%Y-%m-%d")
            except ValueError:
                return text
    else:
        return str(value)

    month_name = TURKISH_MONTHS[dt.month - 1]
    return f"{dt.day:02d} {month_name} {dt.year}"

def api_request(method, url, **kwargs):
    """
    Genel API çağrı fonksiyonu.
    - method: "GET", "POST", "PUT", "DELETE"
    - url: tam API endpoint'i
    - kwargs: data=..., json=..., params=... gibi requests argümanları
    """
    token = auth.get_access_token()
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, url, headers=headers, **kwargs)
    except requests.RequestException as exc:
        return _OfflineResponse(url, exc)

    # Eğer token süresi dolduysa → refresh et ve tekrar dene
    if resp.status_code == 401 and auth.refresh_access_token():
        token = auth.get_access_token()
        headers["Authorization"] = f"Bearer {token}"
        try:
            resp = requests.request(method, url, headers=headers, **kwargs)
        except requests.RequestException as exc:
            return _OfflineResponse(url, exc)

    setattr(resp, "error_message", None)
    return resp


def response_error_message(resp, fallback: str = "Sunucu hatası") -> str:
    """HTTP isteği sonrası kullanıcıya gösterilecek hata mesajını üretir."""
    if resp is None:
        return fallback

    message = getattr(resp, "error_message", None)
    if message:
        return message

    status = getattr(resp, "status_code", None)
    if status:
        return f"{fallback} (HTTP {status})"

    return fallback
