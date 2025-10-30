"""Zamanlanmış görevler ve arka plan işlemleri için yardımcı fonksiyonlar."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .loan_policy import (
    LoanPolicySnapshot,
    calculate_penalty,
    compute_effective_due,
    get_snapshot,
)
from .models import OduncKaydi

def iter_open_loans(lock=False):
    qs = (
        OduncKaydi.objects
        .filter(durum__in=["oduncte", "gecikmis"], teslim_tarihi__isnull=True)
        .select_related("ogrenci", "kitap_nusha", "kitap_nusha__kitap")
        .prefetch_related("ogrenci__rol")
    )
    if lock:
        qs = qs.select_for_update()
    return qs


def update_overdue_loans(now=None):
    """Açık ödünç kayıtlarını tarayıp gecikenleri günceller."""

    if now is None:
        now = timezone.now()

    snapshot = get_snapshot()

    updated_overdue = 0
    reverted = 0
    recalculated = 0
    total_penalty = Decimal("0")

    with transaction.atomic():
        for loan in iter_open_loans(lock=True):
            due = loan.iade_tarihi
            effective_due = compute_effective_due(due, snapshot)
            if not effective_due:
                continue

            is_overdue = effective_due < now
            overdue_days = 0
            if is_overdue:
                overdue_days = max((now.date() - effective_due.date()).days, 0)

            fields = []
            penalty_value = None

            if is_overdue:
                rol = getattr(loan.ogrenci, "rol", None)
                rate = getattr(rol, "gecikme_ceza_gunluk", None)
                penalty_value = calculate_penalty(rate, overdue_days, snapshot)
                if penalty_value is not None:
                    total_penalty += penalty_value

                if loan.durum != "gecikmis":
                    loan.durum = "gecikmis"
                    fields.append("durum")
                    updated_overdue += 1
            else:
                if loan.durum == "gecikmis":
                    loan.durum = "oduncte"
                    fields.append("durum")
                    reverted += 1

            # Ceza güncellemesi
            if penalty_value is None and loan.gecikme_cezasi:
                loan.gecikme_cezasi = None
                fields.append("gecikme_cezasi")
                recalculated += 1
            elif penalty_value is not None and loan.gecikme_cezasi != penalty_value:
                loan.gecikme_cezasi = penalty_value
                fields.append("gecikme_cezasi")
                recalculated += 1

            if fields:
                loan.save(update_fields=fields)

    return {
        "updated_overdue": updated_overdue,
        "reverted": reverted,
        "recalculated": recalculated,
        "total_penalty": total_penalty,
    }
