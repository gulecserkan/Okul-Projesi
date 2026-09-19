"""Kitap meta verisi arama — K7.1/K7.5 (çok kaynaklı).

Kaynaklar:
  - Google Books API (`GOOGLE_BOOKS_API_KEY`; ISBN aramasında `isbn:` öneki)
  - Open Library (anahtarsız; ISBN ve başlık araması + kapak)

Manuel giriş birincildir; bu modül yalnızca formdaki "Doldur" akışına veri
önerisi sağlar. Ağ hatası/429 sonuçları önbelleklenmez; başarılı (boş dahil)
aramalar 7 gün saklanır. Sonuçlar kaynak etiketi (`kaynak`) taşır.
"""

import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

from .turkish import fold

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
_GOOGLE_URL = "https://www.googleapis.com/books/v1/volumes"
_OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
_OPENLIBRARY_ISBN_URL = "https://openlibrary.org/isbn/{isbn}.json"
_OPENLIBRARY_COVER_BY_ID = "https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"

_ISBN_CLEAN_RE = re.compile(r"[^0-9Xx]")
_USER_AGENT = "kutuphane/1.0 (+okul kutuphanesi)"
_OL_FIELDS = "title,author_name,first_publish_year,isbn,cover_i,language,publisher"


def normalize_isbn(value):
    """ISBN'den tire/boşluk ayıklar; 10/13 haneli büyük harfli dize döner."""
    if not value:
        return ""
    return _ISBN_CLEAN_RE.sub("", str(value)).upper()


def _isbn10_to_13(isbn10):
    if len(isbn10) != 10 or not isbn10[:9].isdigit():
        return isbn10
    core = "978" + isbn10[:9]
    total = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core))
    return core + str((10 - total % 10) % 10)


def _isbn_key(value):
    """Tekilleştirme için ISBN'i ISBN-13 biçimine indirger (mümkünse)."""
    norm = normalize_isbn(value)
    if len(norm) == 10 and norm[:9].isdigit():
        return _isbn10_to_13(norm)
    return norm


def looks_like_isbn(value):
    norm = normalize_isbn(value)
    return len(norm) in (10, 13) and norm[:1].isdigit()


def _fetch_json(url, timeout=8):
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def lookup_books(q="", isbn=""):
    """Google Books + Open Library birleşik araması.

    `q` başlık/yazar metni veya ISBN olabilir; `isbn` açıkça da verilebilir.
    Dönüş: `(results, error_code)` — `error_code`: None | "429" | "bad_gateway"
    | "not_found".
    """
    q = (q or "").strip()
    isbn = normalize_isbn(isbn)
    if not isbn and looks_like_isbn(q):
        isbn, q = normalize_isbn(q), ""

    cache_key = "kitap_ara:" + fold(q) + ("|" + isbn if isbn else "")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, ("not_found" if not cached else None)

    merged = []
    errors = []

    if isbn:
        for provider in (_google_books, _open_library):
            items, err = provider(q, isbn=isbn)
            merged += items
            if err:
                errors.append(err)

    if len(q) >= 3:
        for provider in (_google_books, _open_library):
            items, err = provider(q)
            merged += items
            if err:
                errors.append(err)

    results = _merge(merged, isbn)

    if not results and errors:
        return [], ("429" if "429" in errors else "bad_gateway")

    cache.set(cache_key, results, CACHE_TTL_SECONDS)
    return results, ("not_found" if not results else None)


def _google_books(q, isbn=""):
    """Google Books sağlayıcısı; `(results, error)` döner."""
    params = {"country": "TR", "maxResults": 5}
    params["q"] = ("isbn:" + isbn) if isbn else q
    key = getattr(settings, "GOOGLE_BOOKS_API_KEY", "")
    if key:
        params["key"] = key
    url = _GOOGLE_URL + "?" + urlencode(params)
    try:
        data = _fetch_json(url)
    except HTTPError as e:
        return [], ("429" if e.code == 429 else "bad_gateway")
    except Exception:
        return [], "bad_gateway"
    return [_google_item(it) for it in (data.get("items") or [])[:5]], None


def _google_item(it):
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
    return {
        "baslik": vi.get("title") or "",
        "yazar": (vi.get("authors") or [""])[0],
        "yayin_yili": int(yil_raw[:4]) if yil_raw[:4].isdigit() else None,
        "isbn": isbns[0] if isbns else "",
        "aciklama": (vi.get("description") or "")[:2000],
        "kapak_url": cover,
        "kaynak": "google",
    }


def _open_library(q, isbn=""):
    """Open Library sağlayıcısı; `(results, error)` döner."""
    try:
        if isbn:
            edition = _fetch_json(_OPENLIBRARY_ISBN_URL.format(isbn=isbn))
            items = [_ol_edition_item(edition, isbn)]
        else:
            params = {"q": q, "limit": 5, "fields": _OL_FIELDS}
            data = _fetch_json(_OPENLIBRARY_SEARCH_URL + "?" + urlencode(params))
            items = [_ol_search_item(d) for d in (data.get("docs") or [])[:5]]
    except HTTPError as e:
        if e.code == 404:
            return [], None
        return [], ("429" if e.code == 429 else "bad_gateway")
    except Exception:
        return [], "bad_gateway"
    return items, None


def _ol_cover(cover_i):
    return _OPENLIBRARY_COVER_BY_ID.format(cover_i=cover_i) if cover_i else None


def _ol_search_item(d):
    isbns = d.get("isbn") or []
    yil = d.get("first_publish_year")
    return {
        "baslik": d.get("title") or "",
        "yazar": (d.get("author_name") or [""])[0],
        "yayin_yili": int(yil) if isinstance(yil, int) else None,
        "isbn": isbns[0] if isbns else "",
        "aciklama": "",
        "kapak_url": _ol_cover(d.get("cover_i")),
        "kaynak": "openlibrary",
    }


def _ol_edition_item(edition, isbn):
    covers = edition.get("covers") or []
    isbns = edition.get("isbn_13") or edition.get("isbn_10") or []
    yil_raw = str(edition.get("publish_date") or "")
    return {
        "baslik": edition.get("title") or "",
        "yazar": (edition.get("by_statement") or "").strip().rstrip("."),
        "yayin_yili": int(yil_raw[:4]) if yil_raw[:4].isdigit() else None,
        "isbn": (isbns[0] if isbns else isbn),
        "aciklama": "",
        "kapak_url": _ol_cover(covers[0] if covers else None),
        "kaynak": "openlibrary",
    }


def _dedupe_key(item, isbn=""):
    key = _isbn_key(item.get("isbn"))
    if not key and isbn:
        key = isbn
    if key:
        return "isbn:" + key
    return "t:" + fold(item.get("baslik")) + "|" + fold(item.get("yazar") or "")


def _enrich(target, extra):
    for field in ("yazar", "yayin_yili", "isbn", "aciklama"):
        if not target.get(field) and extra.get(field):
            target[field] = extra[field]
    if not target.get("kapak_url") and extra.get("kapak_url"):
        target["kapak_url"] = extra["kapak_url"]


def _merge(items, isbn=""):
    out = []
    seen = {}
    for item in items:
        if not item.get("baslik"):
            continue
        key = _dedupe_key(item, isbn)
        if key in seen:
            _enrich(seen[key], item)
            continue
        seen[key] = item
        out.append(item)
    return out
