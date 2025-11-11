from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0018_notificationsettings_schedule_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="odunckaydi",
            name="gecikme_cezasi_odendi",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="odunckaydi",
            name="gecikme_odeme_tarihi",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="odunckaydi",
            name="gecikme_odeme_tutari",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
    ]
