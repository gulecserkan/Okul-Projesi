from django.db import migrations, models


def migrate_role_limits(apps, schema_editor):
    LoanPolicy = apps.get_model("kutuphane_app", "LoanPolicy")
    RoleLoanPolicy = apps.get_model("kutuphane_app", "RoleLoanPolicy")
    Rol = apps.get_model("kutuphane_app", "Rol")

    try:
        policy = LoanPolicy.objects.get(singleton_key="default")
    except LoanPolicy.DoesNotExist:
        return

    limits = policy.role_limits or []
    if not isinstance(limits, list):
        return

    for entry in limits:
        role_name = (entry or {}).get("role")
        if not role_name:
            continue
        try:
            role = Rol.objects.get(ad=role_name)
        except Rol.DoesNotExist:
            continue
        defaults = {}
        dur = entry.get("duration")
        if isinstance(dur, int) and dur > 0:
            defaults["duration"] = dur
        max_items = entry.get("max_items")
        if isinstance(max_items, int) and max_items > 0:
            defaults["max_items"] = max_items
        if defaults:
            RoleLoanPolicy.objects.update_or_create(role=role, defaults=defaults)


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0011_loanpolicy_penalty_caps"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoleLoanPolicy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("duration", models.PositiveIntegerField(blank=True, null=True)),
                ("max_items", models.PositiveIntegerField(blank=True, null=True)),
                ("delay_grace_days", models.PositiveIntegerField(blank=True, null=True)),
                ("penalty_delay_days", models.PositiveIntegerField(blank=True, null=True)),
                ("shift_weekend", models.BooleanField(blank=True, null=True)),
                (
                    "role",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="loan_policy",
                        to="kutuphane_app.rol",
                    ),
                ),
            ],
        ),
        migrations.RunPython(migrate_role_limits, migrations.RunPython.noop),
    ]
