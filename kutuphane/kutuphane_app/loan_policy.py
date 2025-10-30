"""Ödünç politikası yardımcı fonksiyonları."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from .models import LoanPolicy


@dataclass(frozen=True)
class LoanPolicySnapshot:
    default_duration: int
    default_max_items: int
    delay_grace_days: int
    penalty_delay_days: int
    shift_weekend: bool
    auto_extend_enabled: bool
    auto_extend_days: int
    auto_extend_limit: int
    quarantine_days: int
    require_damage_note: bool
    require_shelf_code: bool
    role_limits: list

    @classmethod
    def from_policy(cls, policy: LoanPolicy) -> "LoanPolicySnapshot":
        return cls(
            default_duration=policy.default_duration,
            default_max_items=policy.default_max_items,
            delay_grace_days=policy.delay_grace_days,
            penalty_delay_days=policy.penalty_delay_days,
            shift_weekend=policy.shift_weekend,
            auto_extend_enabled=policy.auto_extend_enabled,
            auto_extend_days=policy.auto_extend_days,
            auto_extend_limit=policy.auto_extend_limit,
            quarantine_days=policy.quarantine_days,
            require_damage_note=policy.require_damage_note,
            require_shelf_code=policy.require_shelf_code,
            role_limits=policy.role_limits or [],
        )


def get_snapshot() -> LoanPolicySnapshot:
    policy = LoanPolicy.get_solo()
    return LoanPolicySnapshot.from_policy(policy)


def ensure_aware(dt):
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def shift_weekend(due, snapshot: LoanPolicySnapshot):
    due = ensure_aware(due)
    if due is None:
        return None

    if snapshot.shift_weekend:
        while due.weekday() >= 5:
            due = due + timedelta(days=1)

    return due


def apply_grace_and_weekend(due, snapshot: LoanPolicySnapshot):
    due = ensure_aware(due)
    if due is None:
        return None

    if snapshot.delay_grace_days:
        due = due + timedelta(days=snapshot.delay_grace_days)

    return shift_weekend(due, snapshot)


def compute_effective_due(due, snapshot: LoanPolicySnapshot):
    return apply_grace_and_weekend(due, snapshot)


def compute_assigned_due(start, duration_days: int, snapshot: LoanPolicySnapshot):
    if duration_days <= 0:
        duration_days = snapshot.default_duration or 0
    due = ensure_aware(start) + timedelta(days=duration_days)
    return shift_weekend(due, snapshot)


def compute_overdue_days(due, snapshot: LoanPolicySnapshot, *, now=None) -> int:
    effective_due = compute_effective_due(due, snapshot)
    if effective_due is None:
        return 0
    if now is None:
        now = timezone.now()
    if effective_due >= now:
        return 0
    return max((now.date() - effective_due.date()).days, 0)


def calculate_penalty(rate: Optional[Decimal], overdue_days: int, snapshot: LoanPolicySnapshot) -> Optional[Decimal]:
    if rate in (None, 0):
        return None
    chargeable = overdue_days - snapshot.penalty_delay_days
    if chargeable <= 0:
        return None
    penalty = Decimal(rate) * Decimal(chargeable)
    return penalty.quantize(Decimal("0.01"))


def max_items_for_role(role, snapshot: LoanPolicySnapshot) -> Optional[int]:
    if role is None:
        return snapshot.default_max_items or None

    # Rol için özel limit varsa kullan
    for entry in snapshot.role_limits:
        key = entry.get("role") or entry.get("name")
        if key and key == role.ad:
            value = entry.get("max_items")
            if isinstance(value, int) and value > 0:
                return value

    if getattr(role, "maksimum_kitap", None):
        return role.maksimum_kitap

    return snapshot.default_max_items or None


def duration_for_role(role, snapshot: LoanPolicySnapshot) -> int:
    value = getattr(role, "odunc_suresi_gun", None)
    if isinstance(value, int) and value > 0:
        return value
    return snapshot.default_duration
