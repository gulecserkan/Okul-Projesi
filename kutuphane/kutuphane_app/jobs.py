"""Zamanlanmış görevler ve arka plan işlemleri için yardımcı fonksiyonlar."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .loan_policy import (
    LoanPolicySnapshot,
    calculate_penalty,
    compute_effective_due,
    compute_overdue_days,
    daily_penalty_rate_for_role,
    get_snapshot,
    penalty_delay_for_role,
)
from .models import OduncKaydi, NotificationSettings

def iter_open_loans(lock=False):
    qs = (
        OduncKaydi.objects
        .filter(durum__in=["oduncte", "gecikmis"], teslim_tarihi__isnull=True)
        .select_related("ogrenci", "ogrenci__rol", "ogrenci__rol__loan_policy", "kitap_nusha", "kitap_nusha__kitap")
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
            role = getattr(loan.ogrenci, "rol", None)
            effective_due = compute_effective_due(due, snapshot, role)
            if not effective_due:
                continue

            is_overdue = effective_due < now
            overdue_days = 0
            if is_overdue:
                overdue_days = compute_overdue_days(due, snapshot, role, now=now)

            fields = []
            penalty_value = None

            if is_overdue:
                rate = daily_penalty_rate_for_role(snapshot, role)
                if rate and rate > 0:
                    penalty_delay = penalty_delay_for_role(snapshot, role)
                    other_total = (
                        OduncKaydi.objects
                        .filter(ogrenci=loan.ogrenci, gecikme_cezasi__gt=0)
                        .exclude(pk=loan.pk)
                        .aggregate(total=Sum("gecikme_cezasi"))
                        .get("total")
                        or Decimal("0")
                    )
                    penalty_value = calculate_penalty(
                        snapshot,
                        role,
                        overdue_days,
                        penalty_delay,
                        other_active_penalties=other_total,
                        rate=rate,
                    )
                    if penalty_value is not None and penalty_value <= 0:
                        penalty_value = None
                else:
                    penalty_value = None

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


def get_notification_schedule():
    settings = NotificationSettings.get_solo()

    def channel_in_use(channel: str) -> bool:
        if channel == "email":
            if not settings.email_enabled:
                return False
            return (
                (settings.due_reminder_enabled and settings.due_reminder_email_enabled)
                or
                (settings.due_overdue_enabled and settings.overdue_email_enabled)
            )
        if channel == "sms":
            if not settings.sms_enabled:
                return False
            return (
                (settings.due_reminder_enabled and settings.due_reminder_sms_enabled)
                or
                (settings.due_overdue_enabled and settings.overdue_sms_enabled)
            )
        if channel == "mobile":
            if not settings.mobile_enabled:
                return False
            return (
                (settings.due_reminder_enabled and settings.due_reminder_mobile_enabled)
                or
                (settings.due_overdue_enabled and settings.overdue_mobile_enabled)
            )
        return False

    return {
        "email": {
            "enabled": settings.email_schedule_enabled and channel_in_use("email"),
            "hour": settings.email_schedule_hour,
            "minute": settings.email_schedule_minute,
            "timezone": settings.email_schedule_timezone or "",
        },
        "sms": {
            "enabled": settings.sms_schedule_enabled and channel_in_use("sms"),
            "hour": settings.sms_schedule_hour,
            "minute": settings.sms_schedule_minute,
            "timezone": settings.sms_schedule_timezone or "",
        },
        "mobile": {
            "enabled": settings.mobile_schedule_enabled and channel_in_use("mobile"),
            "hour": settings.mobile_schedule_hour,
            "minute": settings.mobile_schedule_minute,
            "timezone": settings.mobile_schedule_timezone or "",
        },
    }


def _schedule_windows(schedule: dict | None, reference=None):
    if not schedule or not schedule.get("enabled"):
        return None, None

    hour = int(schedule.get("hour", 0) or 0) % 24
    minute = int(schedule.get("minute", 0) or 0) % 60

    tz_name = schedule.get("timezone") or str(timezone.get_current_timezone())
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.get_current_timezone()

    now = reference or timezone.now()
    localized_now = now.astimezone(tz)
    target = localized_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if localized_now < target:
        next_target = target
        last_target = target - timedelta(days=1)
    else:
        next_target = target + timedelta(days=1)
        last_target = target

    return (
        last_target.astimezone(timezone.utc),
        next_target.astimezone(timezone.utc),
    )


def compute_next_schedule_run(schedule: dict | None, reference=None):
    """Verilen program için bir sonraki çalıştırma zamanını (UTC) döndür."""
    _, next_target = _schedule_windows(schedule, reference)
    return next_target


def compute_previous_schedule_run(schedule: dict | None, reference=None):
    """Verilen program için son çalıştırma zamanını (UTC) döndür."""
    last_target, _ = _schedule_windows(schedule, reference)
    return last_target


def is_schedule_due(schedule: dict | None, last_run: timezone.datetime | None, reference=None):
    """Son çalıştırma bilgisine göre programın şu anda tetiklenmesi gerekip gerekmediğini döndürür."""
    last_target, _ = _schedule_windows(schedule, reference)
    if last_target is None:
        return False
    if last_run is None:
        return True
    if not timezone.is_aware(last_run):
        last_run = timezone.make_aware(last_run)
    return last_run < last_target


def should_run_overdue(settings: NotificationSettings, reference=None):
    reference = reference or timezone.now()
    tz = timezone.get_current_timezone()
    local_now = reference.astimezone(tz)
    last_date = settings.overdue_last_run
    if last_date == local_now.date():
        return False
    return True


def mark_overdue_ran(settings: NotificationSettings, reference=None):
    tz = timezone.get_current_timezone()
    reference = reference or timezone.now()
    settings.overdue_last_run = reference.astimezone(tz).date()


def mark_channel_run(settings: NotificationSettings, channel: str, reference=None):
    reference = reference or timezone.now()
    field = f"{channel}_schedule_last_run"
    setattr(settings, field, reference)


def _channel_message_types(settings: NotificationSettings, channel: str):
    types = []
    if settings.due_reminder_enabled and getattr(settings, f"due_reminder_{channel}_enabled", False):
        types.append("due_reminder")
    if settings.due_overdue_enabled and getattr(settings, f"overdue_{channel}_enabled", False):
        types.append("overdue")
    return types


def dispatch_notifications(channel: str, types: list[str], when=None):
    """Seçilen kanal için bildirimi tetikleyin. Şimdilik gerçek gönderim değil, yer tutucu."""
    # TODO: E-posta/SMS/mobil gönderimleri burada uygulanacak.
    # Şimdilik sadece loglama yapılabilir.
    return {
        "channel": channel,
        "types": types,
        "timestamp": when.isoformat() if when else timezone.now().isoformat(),
    }


def run_scheduled_jobs(now=None):
    """
    Gecikmiş kayıt güncellemesi ve bildirim planlamalarını tek noktadan yürütür.
    Bu fonksiyon belirli aralıklarla (örn. her 15 dakikada bir) çağrılmalıdır.
    """
    now = now or timezone.now()
    settings = NotificationSettings.get_solo()
    summary = {}
    fields_to_update = set()

    if should_run_overdue(settings, now):
        result = update_overdue_loans(now=now)
        summary["overdue"] = result
        mark_overdue_ran(settings, now)
        fields_to_update.add("overdue_last_run")

    schedules = get_notification_schedule()
    for channel, schedule in schedules.items():
        last_run = getattr(settings, f"{channel}_schedule_last_run")
        if is_schedule_due(schedule, last_run, now):
            types = _channel_message_types(settings, channel)
            if not types:
                continue
            dispatch_result = dispatch_notifications(channel, types, when=now)
            summary[f"{channel}_notifications"] = dispatch_result
            mark_channel_run(settings, channel, now)
            fields_to_update.add(f"{channel}_schedule_last_run")

    if fields_to_update:
        settings.save(update_fields=list(fields_to_update))

    return summary
