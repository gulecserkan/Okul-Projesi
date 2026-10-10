"""Zamanlanmış görevler ve arka plan işlemleri için yardımcı fonksiyonlar."""

from __future__ import annotations

import os
from datetime import timezone as dt_timezone
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
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
from .models import OduncKaydi, NotificationSettings, LoanPolicy, CihazBildirim

def iter_open_loans(lock=False):
    qs = (
        OduncKaydi.objects
        .filter(durum__in=["oduncte", "gecikmis"], teslim_tarihi__isnull=True)
        .select_related("uye", "uye__rol", "uye__rol__loan_policy", "kitap_nusha", "kitap_nusha__kitap")
        .prefetch_related("uye__rol")
    )
    if lock:
        qs = qs.select_for_update()
    return qs


def update_overdue_loans(now=None, *, use_lock=False):
    """Açık ödünç kayıtlarını tarayıp gecikenleri günceller."""

    if now is None:
        now = timezone.now()

    snapshot = get_snapshot()

    updated_overdue = 0
    reverted = 0
    recalculated = 0
    total_penalty = Decimal("0")

    with transaction.atomic():
        for loan in iter_open_loans(lock=use_lock):
            due = loan.iade_tarihi
            role = getattr(loan.uye, "rol", None)
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
                        .filter(
                            uye=loan.uye,
                            gecikme_cezasi__gt=0,
                            gecikme_cezasi_odendi=False,
                        )
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
            reset_paid_fields = False
            if penalty_value is None and loan.gecikme_cezasi:
                loan.gecikme_cezasi = None
                fields.append("gecikme_cezasi")
                recalculated += 1
                reset_paid_fields = True
            elif penalty_value is not None and loan.gecikme_cezasi != penalty_value:
                loan.gecikme_cezasi = penalty_value
                fields.append("gecikme_cezasi")
                recalculated += 1
                reset_paid_fields = True

            if reset_paid_fields:
                if loan.gecikme_cezasi_odendi:
                    loan.gecikme_cezasi_odendi = False
                    fields.append("gecikme_cezasi_odendi")
                if loan.gecikme_odeme_tarihi is not None:
                    loan.gecikme_odeme_tarihi = None
                    fields.append("gecikme_odeme_tarihi")
                if loan.gecikme_odeme_tutari is not None:
                    loan.gecikme_odeme_tutari = None
                    fields.append("gecikme_odeme_tutari")

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
        last_target.astimezone(dt_timezone.utc),
        next_target.astimezone(dt_timezone.utc),
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


def _fcm_app():
    """K15: firebase-admin uygulamasını temin eder.

    Servis hesabı tanımlı değilse veya firebase-admin kurulu değilse None döner;
    böylece kurulumsuz geliştirme ortamı bozulmaz (gönderim sessizce atlanır).
    """
    path = getattr(settings, "FCM_SERVICE_ACCOUNT", "") or os.environ.get(
        "FCM_SERVICE_ACCOUNT", ""
    )
    if not path or not os.path.exists(path):
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        return None
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(path))
    return firebase_admin


def _kitap_adi(loan):
    nusha = getattr(loan, "kitap_nusha", None)
    kitap = getattr(nusha, "kitap", None)
    return (
        getattr(kitap, "baslik", None)
        or getattr(kitap, "ad", None)
        or (getattr(nusha, "barkod", None) if nusha else None)
        or "Kitap"
    )


def _mobil_hedef_uyeler(now, settings_obj):
    """K15.3: mobil bildirim gönderilecek üyeleri ve kayıtlarını toplar."""
    tz = timezone.get_current_timezone()
    bugun = now.astimezone(tz).date()
    hedefler: dict[int, dict] = {}

    def ekle(loan, anahtar):
        hedef = hedefler.setdefault(
            loan.uye_id, {"uye": loan.uye, "hatirlatma": [], "gecikme": []}
        )
        hedef[anahtar].append(loan)

    if settings_obj.due_reminder_enabled and settings_obj.due_reminder_mobile_enabled:
        hedef_tarih = bugun + timedelta(days=settings_obj.due_reminder_days_before or 0)
        qs = (
            OduncKaydi.objects
            .filter(durum="oduncte", teslim_tarihi__isnull=True, iade_tarihi__date=hedef_tarih)
            .select_related("uye", "kitap_nusha__kitap")
        )
        for loan in qs:
            ekle(loan, "hatirlatma")

    if settings_obj.due_overdue_enabled and settings_obj.overdue_mobile_enabled:
        esik = bugun - timedelta(days=settings_obj.due_overdue_days_after or 0)
        qs = (
            OduncKaydi.objects
            .filter(durum="gecikmis", teslim_tarihi__isnull=True, iade_tarihi__date__lte=esik)
            .select_related("uye", "kitap_nusha__kitap")
        )
        for loan in qs:
            ekle(loan, "gecikme")

    return hedefler


def _mobil_icerik(veri):
    """Üyeye gönderilecek bildirim başlığı/gövdesi ve yönlendirme tipi."""
    hatirlatma = veri.get("hatirlatma") or []
    gecikme = veri.get("gecikme") or []
    if gecikme:
        adlar = ", ".join(_kitap_adi(l) for l in gecikme)
        return ("Gecikmiş ödünç", f"{adlar} için iade tarihi geçti. Lütfen iade edin.", "gecikme")
    adlar = ", ".join(_kitap_adi(l) for l in hatirlatma)
    return ("İade hatırlatma", f"{adlar} için iade tarihiniz yaklaşıyor.", "hatirlatma")


def _mobil_bildirim_gonder(now, settings_obj):
    """K15: mobil kanal FCM gönderimi. Token/yapılandırma yoksa sessizce atlar."""
    hedefler = _mobil_hedef_uyeler(now, settings_obj)
    if not hedefler:
        return {"channel": "mobile", "sent": 0, "failed": 0, "hedef": 0}

    tokenlar = {
        uye_id: list(
            CihazBildirim.objects.filter(uye_id=uye_id, aktif=True).values_list(
                "fcm_token", flat=True
            )
        )
        for uye_id in hedefler
    }

    app = _fcm_app()
    if app is None:
        return {
            "channel": "mobile",
            "sent": 0,
            "failed": 0,
            "hedef": len(hedefler),
            "reason": "fcm-yapilandirilmamis",
        }

    from firebase_admin import messaging

    sent = 0
    failed = 0
    gecersiz_tokenlar = []
    for uye_id, veri in hedefler.items():
        uye_tokens = tokenlar.get(uye_id) or []
        if not uye_tokens:
            continue
        title, body, tip = _mobil_icerik(veri)
        message = messaging.MulticastMessage(
            tokens=uye_tokens,
            notification=messaging.Notification(title=title, body=body),
            data={"tip": tip},
            android=messaging.AndroidConfig(priority="high"),
        )
        try:
            cevap = messaging.send_each_for_multicast(message)
        except Exception:
            failed += len(uye_tokens)
            continue
        sent += cevap.success_count
        failed += cevap.failure_count
        for idx, sonuc in enumerate(cevap.responses):
            if not sonuc.success and type(getattr(sonuc, "exception", None)).__name__ in (
                "UnregisteredError",
                "SenderIdMismatchError",
            ):
                gecersiz_tokenlar.append(uye_tokens[idx])

    if gecersiz_tokenlar:
        CihazBildirim.objects.filter(fcm_token__in=gecersiz_tokenlar).update(aktif=False)

    return {"channel": "mobile", "sent": sent, "failed": failed, "hedef": len(hedefler)}


def dispatch_notifications(channel: str, types: list[str], when=None):
    """Seçilen kanal için bildirim gönderimini tetikler.

    Mobil kanal (K15) gerçek FCM gönderimi yapar; e-posta/SMS henüz yer tutucudur.
    """
    when = when or timezone.now()
    if channel == "mobile":
        return _mobil_bildirim_gonder(when, NotificationSettings.get_solo())
    # TODO: E-posta/SMS gönderimleri burada uygulanacak.
    return {
        "channel": channel,
        "types": types,
        "timestamp": when.isoformat(),
    }


def _in_quiet_hours(policy, reference=None) -> bool:
    """K10: sessiz saatler açıksa ve şu an aralıkta ise True (bildirim ertelenir)."""
    if not getattr(policy, "quiet_hours_enabled", False):
        return False
    now = reference or timezone.now()
    local = now.astimezone(timezone.get_current_timezone())
    t = local.time()
    start = policy.quiet_hours_start
    end = policy.quiet_hours_end
    if start is None or end is None or start == end:
        return False
    if start < end:
        return start <= t < end
    return t >= start or t < end  # gece yarısını aşan aralık


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

    # K10: sessiz saatlerde bildirim gönderimi ertelenir (gecikme güncellemesi yine çalışır).
    if _in_quiet_hours(LoanPolicy.get_solo(), now):
        summary["quiet_hours"] = True
    else:
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
