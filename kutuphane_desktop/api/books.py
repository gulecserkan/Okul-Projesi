from core.utils import api_request
from core.config import get_api_base_url


def _base_url(resource: str = "kitaplar/"):
    base = get_api_base_url().rstrip('/')
    return f"{base}/{resource.lstrip('/')}"


def count_books_by_author(author_id):
    base = get_api_base_url().rstrip('/')
    url = f"{base}/kitaplar/?yazar={author_id}"
    resp = api_request("GET", url)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            if "count" in data:
                return data["count"]
            if "results" in data and isinstance(data["results"], list):
                return len(data["results"])
        return 0
    return 0


def count_books_by_category(category_id):
    base = get_api_base_url().rstrip('/')
    url = f"{base}/kitaplar/?kategori={category_id}"
    resp = api_request("GET", url)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            if "count" in data:
                return data["count"]
            if "results" in data and isinstance(data["results"], list):
                return len(data["results"])
        return 0
    return 0


def list_books(params=None):
    resp = api_request("GET", _base_url("kitaplar/"), params=params or {})
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def create_book(payload):
    return api_request("POST", _base_url("kitaplar/"), json=payload)


def update_book(book_id, payload):
    return api_request("PUT", _base_url(f"kitaplar/{book_id}/"), json=payload)


def patch_book(book_id, payload):
    return api_request("PATCH", _base_url(f"kitaplar/{book_id}/"), json=payload)


def delete_book(book_id):
    return api_request("DELETE", _base_url(f"kitaplar/{book_id}/"))


def list_authors():
    resp = api_request("GET", _base_url("yazarlar/"))
    if resp.status_code != 200:
        return []
    try:
        data = resp.json() or []
    except ValueError:
        return []
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data if isinstance(data, list) else []


def list_categories():
    resp = api_request("GET", _base_url("kategoriler/"))
    if resp.status_code != 200:
        return []
    try:
        data = resp.json() or []
    except ValueError:
        return []
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data if isinstance(data, list) else []


def list_copies_for_book(book_id):
    # Backend filtre ismi farklı olabilir; iki deneme yapalım
    base = get_api_base_url().rstrip('/')
    for qs in (f"nushalar/?kitap={book_id}", f"nushalar/?kitap_id={book_id}"):
        resp = api_request("GET", f"{base}/{qs}")
        if resp.status_code == 200:
            try:
                data = resp.json() or []
                return data if isinstance(data, list) else data.get("results", [])
            except Exception:
                return []
    return []


def get_next_barcode(prefix: str = "KIT", width: int = 6) -> str:
    """Sunucudan mevcut barkodları çekip bir sonraki 'KIT00...' kodunu tahmin eder."""
    base = get_api_base_url().rstrip('/')
    try:
        resp = api_request("GET", f"{base}/nushalar/?prefix={prefix}")
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        data = resp.json() or []
        max_n = 0
        for item in data if isinstance(data, list) else data.get('results', []):
            code = (item or {}).get('barkod') or ''
            if isinstance(code, str) and code.startswith(prefix):
                tail = code[len(prefix):]
                if tail.isdigit():
                    n = int(tail)
                    if n > max_n:
                        max_n = n
        return f"{prefix}{max_n+1:0{width}d}"
    except Exception:
        # Ağ hatasında güvenli varsayılan
        return f"{prefix}{1:0{width}d}"


def create_copy(book_id, barkod, raf_kodu=None):
    base = get_api_base_url().rstrip('/')
    payload = {"kitap_id": book_id, "barkod": barkod}
    if raf_kodu:
        payload["raf_kodu"] = raf_kodu
    return api_request("POST", f"{base}/nushalar/", json=payload)


def delete_copy(copy_id):
    base = get_api_base_url().rstrip('/')
    return api_request("DELETE", f"{base}/nushalar/{copy_id}/")


def extract_error(resp):
    try:
        data = resp.json()
    except Exception:
        return resp.text or "Bilinmeyen hata"
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        parts = []
        for k, v in data.items():
            if isinstance(v, (list, tuple)):
                parts.append(f"{k}: {', '.join(map(str, v))}")
            else:
                parts.append(f"{k}: {v}")
        if parts:
            return "\n".join(parts)
    return str(data)


def create_author(name: str):
    return api_request("POST", _base_url("yazarlar/"), json={"ad_soyad": name})


def create_category(name: str):
    return api_request("POST", _base_url("kategoriler/"), json={"ad": name})
