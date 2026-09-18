# Veri migration'ı: mevcut düz metin alanları şifrele.
#
# Şifreleme alan tipine geçerken hâlihazırda düz metin depolanmış kayıtlar
# ilk okumada prefix kontrolü sayesinde sorunsuz okunur; bu migration onları
# elle yeniden kaydederek (get_prep_value -> encrypt) kalıcı olarak şifreler.
from django.db import migrations


def encrypt_existing_rows(apps, schema_editor):
    Ogrenci = apps.get_model("kutuphane_app", "Ogrenci")
    NotificationSettings = apps.get_model("kutuphane_app", "NotificationSettings")

    targets = [
        (Ogrenci, ("telefon", "eposta")),
        (NotificationSettings, ("email_username", "email_password", "sms_api_key")),
    ]
    for model, fields in targets:
        for obj in model.objects.all():
            changed = False
            for field in fields:
                raw = getattr(obj, field, None)
                if raw and not str(raw).startswith("gAAAA"):
                    setattr(obj, field, raw)  # get_prep_value şifreler
                    changed = True
            if changed:
                obj.save(update_fields=fields)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0025_alter_notificationsettings_email_password_and_more"),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_rows, noop),
    ]