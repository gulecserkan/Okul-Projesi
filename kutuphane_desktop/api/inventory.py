from core.config import get_api_base_url
from core.utils import api_request


def _base(path="inventory-sessions/"):
    base = get_api_base_url().rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _parse_response(resp):
    if resp is None:
        return False, None, "Sunucuya ulaşılamadı."
    if 200 <= resp.status_code < 300:
        try:
            data = resp.json()
        except ValueError:
            data = {}
        return True, data, None
    return False, None, _extract_error(resp)


def _extract_error(resp):
    if resp is None:
        return "Sunucuya ulaşılamadı."
    try:
        data = resp.json()
    except Exception:
        return resp.text or f"HTTP {resp.status_code}"
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, (list, tuple)):
            return "\n".join(map(str, detail))
        if detail:
            return str(detail)
        parts = []
        for key, value in data.items():
            if key == "detail":
                continue
            if isinstance(value, (list, tuple)):
                parts.append(f"{key}: {', '.join(map(str, value))}")
            else:
                parts.append(f"{key}: {value}")
        if parts:
            return "\n".join(parts)
    return str(data)


def list_sessions(params=None):
    resp = api_request("GET", _base("inventory-sessions/"), params=params or {})
    ok, data, error = _parse_response(resp)
    if not ok:
        return False, [], error
    if isinstance(data, dict) and "results" in data:
        return True, data["results"], None
    if isinstance(data, list):
        return True, data, None
    return True, [], None


def create_session(payload):
    resp = api_request("POST", _base("inventory-sessions/"), json=payload)
    ok, data, error = _parse_response(resp)
    return ok, data, error


def get_session(session_id):
    resp = api_request("GET", _base(f"inventory-sessions/{session_id}/"))
    return _parse_response(resp)


def fetch_items(session_id, params=None):
    resp = api_request("GET", _base(f"inventory-sessions/{session_id}/items/"), params=params or {})
    return _parse_response(resp)


def mark_item(session_id, payload):
    resp = api_request("POST", _base(f"inventory-sessions/{session_id}/mark/"), json=payload)
    return _parse_response(resp)


def complete_session(session_id, status_value="completed"):
    resp = api_request(
        "POST",
        _base(f"inventory-sessions/{session_id}/complete/"),
        json={"status": status_value},
    )
    return _parse_response(resp)


def delete_session(session_id):
    resp = api_request("DELETE", _base(f"inventory-sessions/{session_id}/"))
    ok, data, error = _parse_response(resp)
    if not ok and resp is not None and resp.status_code == 204:
        return True, None, None
    if resp is not None and resp.status_code == 204:
        return True, None, None
    return ok, data, error
