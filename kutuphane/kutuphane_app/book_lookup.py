"""Google Books arama — K7.5 (anahtar + 7 gün önbellek).

Manuel giriş birincildir; bu modül yalnızca formdaki "Google'dan Doldur"
akışına veri önerisi sağlar. Ağ hatası/429 sonuçları önbelleklenmez;
başarılı (boş dahil) aramalar 7 gün saklanır.
"""

import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

from .turkish import fold

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
_GOOGLE_URL = "https://www.googleapis.com/books/v1/volumes"


def google_books_lookup(q):
    """Google Books'tan TR filtreli kitap önerileri döner.

    Dönüş: `(results, error_code)` — `error_code` şunlardan biri:
      - `None`        → sonuç hazır (boş da olabilir, `not_found` değil)
      - `"429"`       → kota aşıldı
      - `"bad_gateway"` → ağ/API hatası
      - `"not_found"` → sonuç bulunamadı
    """
    cache_key = "kitap_google:" + fold(q)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, ("not_found" if not cached else None)

    params = {"q": q, "country": "TR", "maxResults": 5}
    key = getattr(settings, "GOOGLE_BOOKS_API_KEY", "")
    if key:
        params["key"] = key
    url = _GOOGLE_URL + "?" + urlencode(params)
    try:
        req = Request(url, headers={"User-Agent": "kutuphane/1.0"})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return [], ("429" if e.code == 429 else "bad_gateway")
    except Exception:
        return [], "bad_gateway"

    results = _parse_items(data)
    cache.set(cache_key, results, CACHE_TTL_SECONDS)
    return results, ("not_found" if not results else None)


def _parse_items(data):
    results = []
    for it in (data.get("items") or [])[:5]:
        vi = it.get("volumeInfo") or {}
        ids = vi.get("industryIdentifiers") or []
        isbns = [
            i.get("identifier")
            for i in ids
            if i.get("type") in ("ISBN_13", "ISBN_10")
        ]
        cover = None
        images = vi.get("imageLinks") or {}
        if images.get("thumbnail"):
            cover = images["thumbnail"].replace("zoom=1", "zoom=2")
        yil_raw = str(vi.get("publishedDate") or "")
        yayin_yili = int(yil_raw[:4]) if yil_raw[:4].isdigit() else None
        results.append(
            {
                "baslik": vi.get("title") or "",
                "yazar": (vi.get("authors") or [""])[0],
                "yayin_yili": yayin_yili,
                "isbn": isbns[0] if isbns else "",
                "aciklama": (vi.get("description") or "")[:2000],
                "kapak_url": cover,
            }
        )
    return results