from django.db import migrations, models
from decimal import Decimal


def copy_role_settings(apps, schema_editor):
    Rol = apps.get_model("kutuphane_app", "Rol")
    RoleLoanPolicy = apps.get_model("kutuphane_app", "RoleLoanPolicy")

    for role in Rol.objects.all():
        defaults = {
            "duration": getattr(role, "odunc_suresi_gun", None),
            "max_items": getattr(role, "maksimum_kitap", None),
            "daily_penalty_rate": Decimal(getattr(role, "gecikme_ceza_gunluk", 0) or 0),
        }
        RoleLoanPolicy.objects.update_or_create(role=role, defaults=defaults)


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0014_roleloanpolicy_penalty_caps"),
    ]

    operations = [
        migrations.AddField(
            model_name="roleloanpolicy",
            name="daily_penalty_rate",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.RunPython(copy_role_settings, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="rol",
            name="gecikme_ceza_gunluk",
        ),
        migrations.RemoveField(
            model_name="rol",
            name="maksimum_kitap",
        ),
        migrations.RemoveField(
            model_name="rol",
            name="odunc_suresi_gun",
        ),
    ]
