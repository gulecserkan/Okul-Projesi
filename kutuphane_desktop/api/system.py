import requests
from core.config import get_api_base_url, normalize_api_base


def health_check(base_url=None, timeout=5):
    """Sunucunun sağlık durumunu kontrol eder."""
    base = normalize_api_base(base_url or get_api_base_url())
    url = f"{base}/health/"
    try:
        response = requests.get(url, timeout=timeout)
        ok = response.status_code == 200
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}
        return ok, data
    except requests.RequestException as exc:
        return False, {"error": str(exc)}
