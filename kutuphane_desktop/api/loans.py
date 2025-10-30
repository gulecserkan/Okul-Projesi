from datetime import datetime, timezone

from core.config import get_api_base_url
from core.utils import api_request
from api import students as student_api


def _base_url(resource="oduncler/"):
    base = get_api_base_url().rstrip("/")
    return f"{base}/{resource.lstrip('/')}"


def _default_list(resp):
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            return data["results"]
        if "count" in data and "results" not in data:
            return data
    if isinstance(data, list):
        return data
    return []


def list_student_open_loans(student_id):
    """Öğrencinin açık ödünçlerini listeler (fast-query üzerinden güvenilir)."""
    if not student_id:
        return []
    stu = student_api.get_student(student_id)
    if not stu:
        return []
    no = stu.get("ogrenci_no") or stu.get("no")
    if not no:
        return []
    base = get_api_base_url().rstrip('/')
    url = f"{base}/fast-query/?q={no}"
    resp = api_request("GET", url)
    try:
        data = resp.json() or {}
    except ValueError:
        data = {}
    if isinstance(data, dict) and data.get("type") == "student":
        return data.get("active_loans") or []
    return []


def update_loan_status(loan_id, durum, teslim_tarihi=None, extra_payload=None):
    payload = {"durum": durum}
    if teslim_tarihi is not None:
        payload["teslim_tarihi"] = teslim_tarihi
    elif durum in {"teslim", "kayip", "hasarli"}:
        payload["teslim_tarihi"] = datetime.now(timezone.utc).isoformat()
    if extra_payload:
        payload.update(extra_payload)
    return api_request("PATCH", _base_url(f"oduncler/{loan_id}/"), json=payload)


def update_copy_status(copy_id, durum):
    if not copy_id:
        return None
    return api_request("PATCH", _base_url(f"nushalar/{copy_id}/"), json={"durum": durum})


def extract_error(resp):
    try:
        data = resp.json()
    except ValueError:
        return resp.text or "Bilinmeyen hata"
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        messages = []
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                messages.append(f"{key}: {', '.join(map(str, value))}")
            else:
                messages.append(f"{key}: {value}")
        if messages:
            return "\n".join(messages)
    return str(data)
