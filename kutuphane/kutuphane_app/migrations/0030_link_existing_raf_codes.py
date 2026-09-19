from django.db import migrations


def link_existing_raf_codes(apps, schema_editor):
    """Mevcut serbest metin raf_kodu değerlerini Raf kayıtlarına taşı."""
    KitapNusha = apps.get_model("kutuphane_app", "KitapNusha")
    Raf = apps.get_model("kutuphane_app", "Raf")

    codes = (
        KitapNusha.objects.exclude(raf_kodu__isnull=True)
        .exclude(raf_kodu="")
        .distinct("raf_kodu")
        .values_list("raf_kodu", flat=True)
    )
    by_code = {}
    for code in codes:
        raf, _ = Raf.objects.get_or_create(ad=code)
        by_code[code] = raf

    for nusha in KitapNusha.objects.exclude(raf_kodu__isnull=True).exclude(raf_kodu=""):
        nusha.raf = by_code[nusha.raf_kodu]
    KitapNusha.objects.bulk_update(
        [n for n in KitapNusha.objects.all() if n.raf], ["raf"]
    )


def unlink_raf_codes(apps, schema_editor):
    KitapNusha = apps.get_model("kutuphane_app", "KitapNusha")
    KitapNusha.objects.update(raf=None)


class Migration(migrations.Migration):
    dependencies = [
        ("kutuphane_app", "0029_raf_kitap_kapak_url_kitapnusha_raf"),
    ]

    operations = [
        migrations.RunPython(link_existing_raf_codes, unlink_raf_codes),
    ]