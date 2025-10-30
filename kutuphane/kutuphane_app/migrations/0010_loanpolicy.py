from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0009_alter_kitapnusha_durum_alter_odunckaydi_durum"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoanPolicy",
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
                (
                    "singleton_key",
                    models.CharField(default="default", max_length=50, unique=True),
                ),
                ("default_duration", models.PositiveIntegerField(default=15)),
                ("default_max_items", models.PositiveIntegerField(default=2)),
                ("delay_grace_days", models.PositiveIntegerField(default=0)),
                ("penalty_delay_days", models.PositiveIntegerField(default=0)),
                ("shift_weekend", models.BooleanField(default=False)),
                ("auto_extend_enabled", models.BooleanField(default=False)),
                ("auto_extend_days", models.PositiveIntegerField(default=0)),
                ("auto_extend_limit", models.PositiveIntegerField(default=0)),
                ("quarantine_days", models.PositiveIntegerField(default=0)),
                ("require_damage_note", models.BooleanField(default=False)),
                ("require_shelf_code", models.BooleanField(default=False)),
                ("quiet_hours_enabled", models.BooleanField(default=False)),
                (
                    "quiet_hours_start",
                    models.TimeField(default=datetime.time(22, 0)),
                ),
                ("quiet_hours_end", models.TimeField(default=datetime.time(8, 0))),
                ("role_limits", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Ödünç Politikası",
                "verbose_name_plural": "Ödünç Politikası",
            },
        ),
    ]
