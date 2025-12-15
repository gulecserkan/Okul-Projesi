from core.config import get_api_base_url
from core.utils import api_request


def _base_url(resource: str = "ogrenciler/"):
    base = get_api_base_url().rstrip('/')
    return f"{base}/{resource.lstrip('/')}"


def _default_list(resp):
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def extract_error(resp):
    try:
        data = resp.json()
    except ValueError:
        return resp.text or "Bilinmeyen hata"
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        errors = []
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                errors.append(f"{key}: {', '.join(map(str, value))}")
            else:
                errors.append(f"{key}: {value}")
        if errors:
            return "\n".join(errors)
    return str(data)


def list_students(params=None):
    """Tüm sayfaları çekerek öğrenci listesini döndürür.

    DRF pagination kullanıldığında yalnızca ilk sayfa geliyordu;
    bu da "kayıt silindi" gibi görünen durumlara yol açıyordu.
    """
    url = _base_url()
    query = params or {}
    results = []
    safety_page_limit = 50  # sonsuz döngü koruması

    for _ in range(safety_page_limit):
        resp = api_request("GET", url, params=query)
        if resp.status_code != 200:
            break
        try:
            data = resp.json()
        except ValueError:
            break

        if isinstance(data, dict) and "results" in data:
            results.extend(data.get("results") or [])
            next_url = data.get("next")
            if not next_url:
                break
            url = next_url
            query = None  # next URL zaten parametreyi içeriyor
            continue

        if isinstance(data, list):
            results = data
        break

    return results


def create_student(payload):
    return api_request("POST", _base_url(), json=payload)


def update_student(student_id, payload):
    url = _base_url(f"ogrenciler/{student_id}/")
    return api_request("PUT", url, json=payload)


def patch_student(student_id, payload):
    url = _base_url(f"ogrenciler/{student_id}/")
    return api_request("PATCH", url, json=payload)


def delete_student(student_id):
    url = _base_url(f"ogrenciler/{student_id}/")
    return api_request("DELETE", url)


def list_classes():
    resp = api_request("GET", _base_url("siniflar/"))
    return _default_list(resp)


def list_roles():
    resp = api_request("GET", _base_url("roller/"))
    return _default_list(resp)


def student_has_loans(student_id):
    """Öğrencinin açık (oduncte/gecikmis) ödünç kaydı var mı?
    Backend `oduncler/?ogrenci=` filtresini desteklemeyebileceği için
    güvenilir yol olarak fast-query'i kullanıyoruz.
    """
    if not student_id:
        return False
    # Öğrenci no'yu alıp fast-query üzerinden aktif odunçları çek
    stu = get_student(student_id)
    if not stu:
        return False
    no = stu.get("ogrenci_no") or stu.get("no")
    if not no:
        return False
    base = get_api_base_url().rstrip('/')
    url = f"{base}/fast-query/?q={no}"
    resp = api_request("GET", url)
    if resp.status_code != 200:
        return False
    try:
        data = resp.json() or {}
    except ValueError:
        return False
    if isinstance(data, dict) and (data.get("type") == "student"):
        loans = data.get("active_loans") or []
        return len(loans) > 0
    return False


def get_student(student_id):
    resp = api_request("GET", _base_url(f"ogrenciler/{student_id}/"))
    if resp.status_code == 200:
        try:
            return resp.json()
        except ValueError:
            return None
    return None
