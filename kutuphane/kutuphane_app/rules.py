"""İş kuralları — tek doğruluk kaynağı (bkz. docs/IS_KURALLARI.md).

Kurallar view katmanında tekrarlanmaz; bu modül üzerinden uygulanır.
"""

from __future__ import annotations

import re

from django.utils import timezone

from .models import Kategori, Kitap, KitapNusha, OduncKaydi, Raf, Yazar
from .turkish import fold

# --- Ödünç kapanış geçişleri (K3) ---
ODUNC_ACIK_DURUMLAR = {"oduncte", "gecikmis"}
ODUNC_KAPANIS_DURUMLARI = ["teslim", "kayip", "hasarli", "iptal"]

# K3.4 — kapanış → nüsha durum senkronu
NUSHA_KAPANIS_MAP = {
    "teslim": "mevcut",
    "iptal": "mevcut",
    "kayip": "kayip",
    "hasarli": "hasarli",
}


def validate_transition(loan, yeni_durum, *, teslim_tarihi=None):
    """K3.1-K3.3: ödünç kapanış geçişini doğrular."""
    if yeni_durum not in ODUNC_KAPANIS_DURUMLARI:
        return False, f"Geçersiz kapanış durumu: {yeni_durum}"
    if loan.durum not in ODUNC_ACIK_DURUMLAR:
        return False, "Bu kayıt zaten kapanmış; tekrar işlem yapılamaz."
    if yeni_durum != "iptal" and not teslim_tarihi:
        return False, "teslim_tarihi (işlem tarihi) zorunludur."
    return True, None


# --- Öğrenci aktif/pasif (K2) ---
def apply_student_status(uye, aktif: bool) -> list:
    """K2.1-K2.4: aktif/pasif geçişi; pasif_tarihi otomatik; uyarı döner."""
    aktif = bool(aktif)
    warnings = []
    if aktif:
        uye.pasif_tarihi = None
    else:
        uye.pasif_tarihi = timezone.now()
        aktif_sayi = OduncKaydi.objects.filter(
            uye=uye, durum__in=["oduncte", "gecikmis"]
        ).count()
        if aktif_sayi:
            warnings.append(
                f"Bu öğrencinin {aktif_sayi} aktif ödüncü var; kitapları toplayın."
            )
    uye.aktif = aktif
    uye.save(update_fields=["aktif", "pasif_tarihi"])
    return warnings


# --- Silme kuralları (K2.7, K4.3, K4.4) ---
def can_delete_uye(uye) -> bool:
    """Etkileşim (ödünç kaydı) yoksa silinebilir; aksi halde pasife alınır."""
    return not OduncKaydi.objects.filter(uye=uye).exists()


def can_delete_nusha(nusha) -> bool:
    """Hiçbir ödünç kaydı yoksa nüsha silinebilir."""
    return not OduncKaydi.objects.filter(kitap_nusha=nusha).exists()


def can_delete_kitap(kitap) -> bool:
    """Tüm nüshaların ödünç kaydı boşsa kitap silinebilir."""
    return not OduncKaydi.objects.filter(kitap_nusha__kitap=kitap).exists()


# --- Kayıp/hasarlı ceza önerisi (K3.5) ---
def suggested_loss_penalty(snapshot):
    """Politikadaki kayıp/hasarlı cezası; sıfırsa öneri üretilmez."""
    val = getattr(snapshot, "kayip_hasar_cezasi", None)
    if val is None:
        return None
    return val if val > 0 else None


# --- Referans veri tekilliği (K6.1) ---
def fold_duplicate(queryset, value, field="ad"):
    """fold-normalize edilmiş kopya var mı? Eşleşen ilk kaydı döndürür."""
    target = fold(str(value)).strip()
    if not target:
        return None
    for row in queryset:
        row_value = fold(str(getattr(row, field) or "")).strip()
        if row_value and row_value == target:
            return row
    return None


# --- Nüsha durum düzeltmesi (K4.8) ---
NUSHA_DUZELTILEBILIR_DURUMLAR = {"mevcut", "kayip", "hasarli"}

OPEN_LOAN_DURUMLARI = ("oduncte", "gecikmis")


def can_duzelt_nusha(nusha, yeni_durum) -> tuple:
    """K4.8: durum düzeltmesi yalnız mevcut/kayıp/hasarlı arası (admin).

    Kural: açık ödünç kaydı olan nüshanın durumu admin düzeltmesiyle değişmez;
    ödünçteki nüsha ancak kapat akışıyla kapanır."""
    if nusha.durum == yeni_durum:
        return True, None
    if yeni_durum not in NUSHA_DUZELTILEBILIR_DURUMLAR:
        return False, "Durum düzeltmesi yalnızca mevcut/kayıp/hasarlı arasında yapılabilir."
    if OduncKaydi.objects.filter(
        kitap_nusha=nusha, durum__in=OPEN_LOAN_DURUMLARI
    ).exists():
        return False, "Nüsha ödünçte; önce ödünç kaydı kapatılmalı."
    return True, None


# --- Kitap kayıt akışı — çift kayıt önleme (K8) ---
_ISBN_STRIP = re.compile(r"[^0-9X]")


def _normalize_isbn(value):
    """ISBN'i karşılaştırılabilir forma sokar (978-975-08-1522-1 → 9789750815221)."""
    s = _ISBN_STRIP.sub("", str(value or "").upper())
    return s


def similar_kitap(baslik, isbn=None, exclude_id=None):
    """K8.1: yeni kayıtta mevcut eşleşme arar.

    Öncelik: normalize ISBN birebir eşleşme; aksi halde fold(başlık) birebir.
    `(benzerler, isbn_eslesme)` döner; ISBN eşleşenler ilk sıradadır.
    """
    isbn_norm = _normalize_isbn(isbn)
    baslik_norm = fold(str(baslik or "")).strip()
    rows = Kitap.objects.only("id", "baslik", "isbn")
    if exclude_id is not None:
        rows = rows.exclude(pk=exclude_id)
    isbn_hits, baslik_hits = [], []
    for k in rows:
        if isbn_norm and _normalize_isbn(k.isbn) == isbn_norm:
            isbn_hits.append(k)
        elif baslik_norm and baslik_norm == fold(k.baslik or "").strip():
            baslik_hits.append(k)
    return isbn_hits + baslik_hits, bool(isbn_hits)


# --- Referans birleştirme (K6.2) ---
def merge_referential(model, hedef, kaynak):
    """K6.2: kaynağı hedefe birleştirir ve kaynağı siler.

    Çocuk kayıtlar hedefe taşınır, arama alanları tazelenir, kaynak silinir."""
    if model is Yazar:
        Kitap.objects.filter(yazar=kaynak).update(yazar=hedef)
        for k in Kitap.objects.filter(yazar=hedef).only("id"):
            k.save(update_fields=["arama"])
    elif model is Kategori:
        Kitap.objects.filter(kategori=kaynak).update(kategori=hedef)
        for k in Kitap.objects.filter(kategori=hedef).only("id"):
            k.save(update_fields=["arama"])
    elif model is Raf:
        KitapNusha.objects.filter(raf=kaynak).update(raf=hedef, raf_kodu=hedef.ad)
        for n in KitapNusha.objects.filter(raf=hedef).only("id"):
            n.save(update_fields=["raf_kodu"])
    else:
        raise ValueError(f"Birleştirilemeyen model: {model}")
    kaynak.delete()


# --- Üye rol atama yetkisi (K9.5.2) ---
def rol_degisikligi_izinli(hedef_rol_ad, *, is_superuser) -> bool:
    """Öğrenci dışı rol (Öğretmen/Editör) ataması yalnız admin'dir.

    Personel, üye kaydında/düzenlemesinde rolü boşaltamaz ve yalnız Öğrenci
    atayabilir. `ben-ekle` kaldırıldı (K9.6); bu kural serializer katmanından
    çağrılır ve self-servis bulunmadığından yalnız personel kayıtlarına uygulanır."""
    if is_superuser:
        return True
    return hedef_rol_ad is not None and hedef_rol_ad == "Öğrenci"