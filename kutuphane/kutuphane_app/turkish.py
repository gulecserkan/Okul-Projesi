import re
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


def bas_harf_buyut(text):
    """
    R1.7: Türkçe baş harf (title case) biçimine çevirir.

    Kapsam dışı: harf olmayan karakterler korunur, fazla boşluklar daraltılır.
    Kural: `i → İ`, `ı → I` (büyütürken); `I → ı`, `İ → i` (küçültürken).
    Böylece "İSMAİL" → "İsmail", "ISMAIL" → "Ismail", "isMail" → "Ismail".
    """
    if not text:
        return ""
    s = re.sub(r"\s+", " ", str(text)).strip()
    if not s:
        return ""
    sonuc = []
    bas_harf = True
    for ch in s:
        if ch.isalpha():
            if bas_harf:
                sonuc.append(ch.replace("i", "İ").replace("ı", "I").upper())
            else:
                sonuc.append(ch.replace("I", "ı").replace("İ", "i").lower())
            bas_harf = False
        else:
            sonuc.append(ch)
            bas_harf = True
    return "".join(sonuc)