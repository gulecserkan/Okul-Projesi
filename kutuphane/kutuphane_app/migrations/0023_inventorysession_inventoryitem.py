from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0022_auditlog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InventorySession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Aktif"), ("completed", "Tamamlandı"), ("canceled", "İptal Edildi")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("filters", models.JSONField(blank=True, default=dict)),
                ("total_items", models.PositiveIntegerField(default=0)),
                ("seen_items", models.PositiveIntegerField(default=0)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="inventory_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Sayım Oturumu",
                "verbose_name_plural": "Sayım Oturumları",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("barkod", models.CharField(max_length=50)),
                ("kitap_baslik", models.CharField(max_length=200)),
                ("raf_kodu", models.CharField(blank=True, max_length=20, null=True)),
                ("durum", models.CharField(blank=True, max_length=20)),
                ("seen", models.BooleanField(default=False)),
                ("seen_at", models.DateTimeField(blank=True, null=True)),
                ("note", models.CharField(blank=True, max_length=200)),
                (
                    "kitap_nusha",
                    models.ForeignKey(
                        on_delete=models.CASCADE, related_name="inventory_items", to="kutuphane_app.kitapnusha"
                    ),
                ),
                (
                    "seen_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="inventory_checks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=models.CASCADE, related_name="items", to="kutuphane_app.inventorysession"
                    ),
                ),
            ],
            options={
                "verbose_name": "Sayım Kalemi",
                "verbose_name_plural": "Sayım Kalemleri",
                "ordering": ("-seen", "raf_kodu", "barkod"),
            },
        ),
        migrations.AlterUniqueTogether(
            name="inventoryitem",
            unique_together={("session", "kitap_nusha")},
        ),
    ]
