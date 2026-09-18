"""
Alan düzeyinde şifreleme (KVKK / kişisel veri).

FerNet (AES-128-CBC + HMAC) tabanlı, `cryptography` kütüphanesiyle uygulanır.

- Anahtar: settings.FIELD_ENCRYPTION_KEY (yoksa SECRET_KEY).
- Şifrelenmiş değerler `gAAAA...` önekiyle saklanır; decrypt işlemi bu öneki
  görmeyen (eski düz metin) değerleri olduğu gibi döndürür. Böylece mevcut
  verinin geçişi sorunsuzdur; kaydedildiğinde otomatik şifrelenir.

Dikkat:
- Bu alanlar üzerinde `icontains` vb. belirsiz arama yapılamaz (şifreli metin).
- Rastgele IV nedeniyle unique kısıtı/test etme alanlarda kullanılamaz.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from django.conf import settings
from django.db import models

_TOKEN_PREFIX = "gAAAA"


def _get_key() -> bytes:
    raw = getattr(settings, "FIELD_ENCRYPTION_KEY", None) or settings.SECRET_KEY
    digest = hashlib.sha256(str(raw).encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_str(value):
    if value is None:
        return None
    value = str(value)
    if value == "":
        return value
    return Fernet(_get_key()).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_str(value):
    if value is None:
        return None
    if isinstance(value, str) and value.startswith(_TOKEN_PREFIX):
        try:
            return Fernet(_get_key()).decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            return None
    return value  # eski düz metin veya okunamayan değer


class EncryptedCharField(models.CharField):
    """
    Düz metin CharField + alan düzeyinde şifreleme.

    Yazma: get_prep_value'da şifreler (kayıt + tam eşleşme sorguları birlikte çalışır).
    Okuma: from_db_value / to_python'da çözer.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 512)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return decrypt_str(value)

    def to_python(self, value):
        return decrypt_str(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_str(value)


class EncryptedTextField(models.TextField):
    """EncryptedCharField'in sınırsız uzunluklu sürümü."""

    def from_db_value(self, value, expression, connection):
        return decrypt_str(value)

    def to_python(self, value):
        return decrypt_str(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_str(value)