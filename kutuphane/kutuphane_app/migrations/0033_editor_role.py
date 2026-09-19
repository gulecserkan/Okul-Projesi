from django.db import migrations


def create_editor_role(apps, schema_editor):
    """'Editör' rolünü oluşturur; ödünç politikasını Öğretmen ile aynı yapar."""
    Rol = apps.get_model("kutuphane_app", "Rol")
    RoleLoanPolicy = apps.get_model("kutuphane_app", "RoleLoanPolicy")

    editor, _ = Rol.objects.get_or_create(ad="Editör")
    if RoleLoanPolicy.objects.filter(role=editor).exists():
        return

    fields = (
        "duration",
        "max_items",
        "delay_grace_days",
        "penalty_delay_days",
        "shift_weekend",
        "penalty_max_per_loan",
        "penalty_max_per_student",
        "daily_penalty_rate",
    )
    defaults = {}
    teacher = Rol.objects.filter(ad="Öğretmen").first()
    if teacher is not None:
        tp = RoleLoanPolicy.objects.filter(role=teacher).first()
        if tp is not None:
            defaults = {f: getattr(tp, f) for f in fields}
    RoleLoanPolicy.objects.create(role=editor, **defaults)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0032_remove_personel_rename_ogrenci_uye"),
    ]

    operations = [
        migrations.RunPython(create_editor_role, noop),
    ]
