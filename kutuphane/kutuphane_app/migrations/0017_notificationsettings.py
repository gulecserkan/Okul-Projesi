from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0016_kitap_aciklama_and_images"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationSettings",
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
                ("singleton_key", models.CharField(default="default", max_length=50, unique=True)),
                ("printer_warning_enabled", models.BooleanField(default=True)),
                ("due_reminder_enabled", models.BooleanField(default=True)),
                ("due_reminder_days_before", models.PositiveIntegerField(default=1)),
                ("due_overdue_enabled", models.BooleanField(default=True)),
                ("due_overdue_days_after", models.PositiveIntegerField(default=0)),
                ("email_enabled", models.BooleanField(default=False)),
                ("email_sender", models.CharField(blank=True, max_length=120)),
                ("email_smtp_host", models.CharField(blank=True, max_length=120)),
                ("email_smtp_port", models.PositiveIntegerField(default=587)),
                ("email_use_tls", models.BooleanField(default=True)),
                ("email_username", models.CharField(blank=True, max_length=120)),
                ("email_password", models.CharField(blank=True, max_length=255)),
                ("sms_enabled", models.BooleanField(default=False)),
                ("sms_provider", models.CharField(blank=True, max_length=120)),
                ("sms_api_url", models.CharField(blank=True, max_length=255)),
                ("sms_api_key", models.CharField(blank=True, max_length=255)),
                ("mobile_enabled", models.BooleanField(default=False)),
                ("reminder_subject", models.CharField(blank=True, max_length=200)),
                ("reminder_body", models.TextField(blank=True)),
                ("overdue_subject", models.CharField(blank=True, max_length=200)),
                ("overdue_body", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Bildirim Ayarı",
                "verbose_name_plural": "Bildirim Ayarları",
            },
        ),
    ]
