import logging
import unicodedata
from typing import Any


logger = logging.getLogger(__name__)


def _sanitize_header_value(value: Any) -> Any:
    """
    HTTP protokolü yalnızca ASCII ve tek satırlı başlıklara izin verir.
    ASCII dışı karakterler Requests tarafında RecursionError tetiklediği için
    başlıkları normalize edip güvenli hale getiriyoruz.
    """
    if not isinstance(value, str):
        return value
    if (
        all(ord(ch) < 128 for ch in value)
        and "\r" not in value
        and "\n" not in value
    ):
        return value

    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = (
        normalized.encode("ascii", "ignore")
        .decode("ascii")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )
    return ascii_value or "safe-value"


class SafeHeaderMiddleware:
    """Yanıt başlıklarını ASCII-safe hale getirir."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for key, value in list(response.items()):
            sanitized = _sanitize_header_value(value)
            if sanitized != value:
                logger.warning(
                    "SafeHeaderMiddleware sanitized header %s: %r -> %r",
                    key,
                    value,
                    sanitized,
                )
                response[key] = sanitized
        return response
