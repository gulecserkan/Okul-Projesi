"""Ödünç politikası yardımcı fonksiyonları."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Optional, Dict

from django.utils import timezone

from .models import LoanPolicy, RoleLoanPolicy


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
    role_overrides: Dict[int, "RolePolicyOverride"]
    penalty_max_per_loan: Decimal
    penalty_max_per_student: Decimal

    @classmethod
    def from_policy(cls, policy: LoanPolicy) -> "LoanPolicySnapshot":
        overrides = {}
        for rp in RoleLoanPolicy.objects.select_related("role").all():
            overrides[rp.role_id] = RolePolicyOverride(
                duration=rp.duration,
                max_items=rp.max_items,
                delay_grace_days=rp.delay_grace_days,
                penalty_delay_days=rp.penalty_delay_days,
                shift_weekend=rp.shift_weekend,
                penalty_max_per_loan=Decimal(rp.penalty_max_per_loan) if rp.penalty_max_per_loan is not None else None,
                penalty_max_per_student=Decimal(rp.penalty_max_per_student) if rp.penalty_max_per_student is not None else None,
                daily_penalty_rate=Decimal(rp.daily_penalty_rate) if rp.daily_penalty_rate is not None else None,
            )

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
            role_overrides=overrides,
            penalty_max_per_loan=Decimal(policy.penalty_max_per_loan or 0),
            penalty_max_per_student=Decimal(policy.penalty_max_per_student or 0),
        )


def get_snapshot() -> LoanPolicySnapshot:
    policy = LoanPolicy.get_solo()
    return LoanPolicySnapshot.from_policy(policy)


@dataclass(frozen=True)
class RolePolicyOverride:
    duration: Optional[int] = None
    max_items: Optional[int] = None
    delay_grace_days: Optional[int] = None
    penalty_delay_days: Optional[int] = None
    shift_weekend: Optional[bool] = None
    penalty_max_per_loan: Optional[Decimal] = None
    penalty_max_per_student: Optional[Decimal] = None
    daily_penalty_rate: Optional[Decimal] = None


def ensure_aware(dt):
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _get_role_override(snapshot: LoanPolicySnapshot, role) -> Optional[RolePolicyOverride]:
    if role is None:
        return None
    return snapshot.role_overrides.get(role.id)


def _resolve_shift_weekend(snapshot: LoanPolicySnapshot, role) -> bool:
    override = _get_role_override(snapshot, role)
    if override and override.shift_weekend is not None:
        return bool(override.shift_weekend)
    return snapshot.shift_weekend


def shift_weekend(due, snapshot: LoanPolicySnapshot, role=None):
    due = ensure_aware(due)
    if due is None:
        return None

    if _resolve_shift_weekend(snapshot, role):
        while due.weekday() >= 5:
            due = due + timedelta(days=1)

    return due


def _resolve_grace_days(snapshot: LoanPolicySnapshot, role) -> int:
    override = _get_role_override(snapshot, role)
    if override and override.delay_grace_days is not None:
        return max(0, int(override.delay_grace_days))
    return max(0, int(snapshot.delay_grace_days))


def apply_grace_and_weekend(due, snapshot: LoanPolicySnapshot, role=None):
    due = ensure_aware(due)
    if due is None:
        return None

    grace_days = _resolve_grace_days(snapshot, role)
    if grace_days:
        due = due + timedelta(days=grace_days)

    return shift_weekend(due, snapshot, role)


def compute_effective_due(due, snapshot: LoanPolicySnapshot, role=None):
    return apply_grace_and_weekend(due, snapshot, role)


def compute_assigned_due(start, duration_days: int, snapshot: LoanPolicySnapshot, role=None):
    if duration_days <= 0:
        duration_days = snapshot.default_duration or 0
    due = ensure_aware(start) + timedelta(days=duration_days)
    return shift_weekend(due, snapshot, role)


def compute_overdue_days(due, snapshot: LoanPolicySnapshot, role=None, *, now=None) -> int:
    effective_due = compute_effective_due(due, snapshot, role)
    if effective_due is None:
        return 0
    if now is None:
        now = timezone.now()
    if effective_due >= now:
        return 0
    return max((now.date() - effective_due.date()).days, 0)


def calculate_penalty(
    snapshot: LoanPolicySnapshot,
    role,
    overdue_days: int,
    penalty_delay_days: int,
    *,
    other_active_penalties: Optional[Decimal] = None,
    rate: Optional[Decimal] = None,
) -> Optional[Decimal]:
    if rate is None:
        rate = daily_penalty_rate_for_role(snapshot, role)
    if rate in (None, 0):
        return None
    chargeable = overdue_days - max(0, penalty_delay_days)
    if chargeable <= 0:
        return None
    penalty = Decimal(rate) * Decimal(chargeable)

    max_per_loan = penalty_max_per_loan_for_role(snapshot, role)
    if max_per_loan and max_per_loan > 0:
        penalty = min(penalty, max_per_loan)

    if other_active_penalties is not None:
        other_active_penalties = Decimal(other_active_penalties)
    else:
        other_active_penalties = Decimal("0")

    max_per_student = penalty_max_per_student_for_role(snapshot, role)
    if max_per_student and max_per_student > 0:
        remaining = max_per_student - other_active_penalties
        if remaining <= 0:
            return Decimal("0.00")
        penalty = min(penalty, remaining)

    return penalty.quantize(Decimal("0.01"))


def max_items_for_role(role, snapshot: LoanPolicySnapshot) -> Optional[int]:
    override = _get_role_override(snapshot, role)
    if override and override.max_items is not None:
        value = int(override.max_items)
        return value if value > 0 else None

    return snapshot.default_max_items or None


def duration_for_role(role, snapshot: LoanPolicySnapshot) -> int:
    override = _get_role_override(snapshot, role)
    if override and override.duration is not None and override.duration > 0:
        return int(override.duration)
    return snapshot.default_duration


def grace_days_for_role(snapshot: LoanPolicySnapshot, role) -> int:
    return _resolve_grace_days(snapshot, role)


def penalty_delay_for_role(snapshot: LoanPolicySnapshot, role) -> int:
    override = _get_role_override(snapshot, role)
    if override and override.penalty_delay_days is not None:
        return max(0, int(override.penalty_delay_days))
    return max(0, int(snapshot.penalty_delay_days))


def shift_weekend_for_role(snapshot: LoanPolicySnapshot, role) -> bool:
    return _resolve_shift_weekend(snapshot, role)


def penalty_max_per_loan_for_role(snapshot: LoanPolicySnapshot, role) -> Decimal:
    override = _get_role_override(snapshot, role)
    if override and override.penalty_max_per_loan is not None:
        return Decimal(override.penalty_max_per_loan)
    return snapshot.penalty_max_per_loan


def penalty_max_per_student_for_role(snapshot: LoanPolicySnapshot, role) -> Decimal:
    override = _get_role_override(snapshot, role)
    if override and override.penalty_max_per_student is not None:
        return Decimal(override.penalty_max_per_student)
    return snapshot.penalty_max_per_student


def daily_penalty_rate_for_role(snapshot: LoanPolicySnapshot, role) -> Decimal:
    override = _get_role_override(snapshot, role)
    if override and override.daily_penalty_rate is not None:
        return Decimal(override.daily_penalty_rate)
    return Decimal("0.00")
