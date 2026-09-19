from django.db import migrations


def upper_uye_no(apps, schema_editor):
    """Mevcut üye numaralarını kanonik BÜYÜK harfe çevirir (harf duyarsız tekillik)."""
    Uye = apps.get_model("kutuphane_app", "Uye")
    for u in Uye.objects.exclude(uye_no__isnull=True).exclude(uye_no=""):
        up = str(u.uye_no).strip().upper()
        if up != u.uye_no:
            u.uye_no = up
            u.save(update_fields=["uye_no"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0033_editor_role"),
    ]

    operations = [
        migrations.RunPython(upper_uye_no, noop),
    ]
