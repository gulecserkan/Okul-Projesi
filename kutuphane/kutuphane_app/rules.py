"""İş kuralları — tek doğruluk kaynağı (bkz. docs/IS_KURALLARI.md).

Kurallar view katmanında tekrarlanmaz; bu modül üzerinden uygulanır.
"""

from __future__ import annotations

from django.utils import timezone

from .models import OduncKaydi
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
def apply_student_status(ogrenci, aktif: bool) -> list:
    """K2.1-K2.4: aktif/pasif geçişi; pasif_tarihi otomatik; uyarı döner."""
    aktif = bool(aktif)
    warnings = []
    if aktif:
        ogrenci.pasif_tarihi = None
    else:
        ogrenci.pasif_tarihi = timezone.now()
        aktif_sayi = OduncKaydi.objects.filter(
            ogrenci=ogrenci, durum__in=["oduncte", "gecikmis"]
        ).count()
        if aktif_sayi:
            warnings.append(
                f"Bu öğrencinin {aktif_sayi} aktif ödüncü var; kitapları toplayın."
            )
    ogrenci.aktif = aktif
    ogrenci.save(update_fields=["aktif", "pasif_tarihi"])
    return warnings


# --- Silme kuralları (K2.7, K4.3, K4.4) ---
def can_delete_ogrenci(ogrenci) -> bool:
    """Etkileşim (ödünç kaydı) yoksa silinebilir; aksi halde pasife alınır."""
    return not OduncKaydi.objects.filter(ogrenci=ogrenci).exists()


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