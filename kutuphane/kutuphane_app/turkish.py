import unicodedata


def fold(text):
    """
    Türkçe'ye uygun, aksan- ve harf-duyarsız arama anahtarı üretir.

    Kapsar:
      - İ → i  (noktalı büyük i)  → "ilber" ile "İlber" eşleşir
      - I → ı  (noktasız büyük ı)  → adi büyük harf "I" alt kümesi ı'ya döner
      - ç→c, ş→s, ğ→g, ö→o, ü→u, â→a, î→i (NFKD aksan ayırma)
    """
    if text is None:
        return ""
    s = text.replace("İ", "i").replace("I", "ı").lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))