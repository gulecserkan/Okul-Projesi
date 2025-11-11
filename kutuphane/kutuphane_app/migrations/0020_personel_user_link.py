from django.db import migrations, models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password


def link_personel_to_user(apps, schema_editor):
    Personel = apps.get_model("kutuphane_app", "Personel")
    User = get_user_model()

    for personel in Personel.objects.all():
        password_raw = personel.sifre_hash or User.objects.make_random_password()
        hashed = make_password(password_raw)
        personel.sifre_hash = hashed

        user, created = User.objects.get_or_create(
            username=personel.kullanici_adi,
            defaults={
                "first_name": personel.ad_soyad,
                "password": hashed,
                "is_staff": True,
            },
        )
        if not created:
            user.password = hashed
            user.first_name = personel.ad_soyad
            if not user.is_staff:
                user.is_staff = True
            user.save()

        personel.user_id = user.id
        personel.save(update_fields=["sifre_hash", "user"])


def unlink_personel_user(apps, schema_editor):
    Personel = apps.get_model("kutuphane_app", "Personel")
    for personel in Personel.objects.all():
        personel.user_id = None
        personel.save(update_fields=["user"])


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0019_odunckaydi_penalty_payment_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="personel",
            name="sifre_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="personel",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="personel",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(link_personel_to_user, unlink_personel_user),
    ]
