from django.db import migrations, models

from kutuphane_app.turkish import fold


def backfill_ogrenci(apps, schema_editor):
    Ogrenci = apps.get_model("kutuphane_app", "Ogrenci")
    Sinif = apps.get_model("kutuphane_app", "Sinif")
    Rol = apps.get_model("kutuphane_app", "Rol")
    sinif_cache = {s.id: s.ad for s in Sinif.objects.all()}
    rol_cache = {r.id: r.ad for r in Rol.objects.all()}
    for o in Ogrenci.objects.all().iterator():
        parts = [o.ad or "", o.soyad or "", o.ogrenci_no or ""]
        if o.sinif_id:
            parts.append(sinif_cache.get(o.sinif_id, ""))
        if o.rol_id:
            parts.append(rol_cache.get(o.rol_id, ""))
        o.arama = fold(" ".join(parts))
        o.save(update_fields=["arama"])


def backfill_kitap(apps, schema_editor):
    from collections import defaultdict

    Kitap = apps.get_model("kutuphane_app", "Kitap")
    Yazar = apps.get_model("kutuphane_app", "Yazar")
    Kategori = apps.get_model("kutuphane_app", "Kategori")
    KitapNusha = apps.get_model("kutuphane_app", "KitapNusha")
    yazar_cache = {y.id: y.ad_soyad for y in Yazar.objects.all()}
    kat_cache = {k.id: k.ad for k in Kategori.objects.all()}
    raf_by_kitap = defaultdict(list)
    for n in KitapNusha.objects.filter(raf_kodu__isnull=False).only("kitap_id", "raf_kodu"):
        raf_by_kitap[n.kitap_id].append(n.raf_kodu)
    for k in Kitap.objects.all().iterator():
        parts = [k.baslik or ""]
        if k.isbn:
            parts.append(k.isbn)
        if k.yazar_id:
            parts.append(yazar_cache.get(k.yazar_id, ""))
        if k.kategori_id:
            parts.append(kat_cache.get(k.kategori_id, ""))
        parts.extend(raf_by_kitap.get(k.id, []))
        k.arama = fold(" ".join(parts))
        k.save(update_fields=["arama"])


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0026_encrypt_sensitive_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="ogrenci",
            name="arama",
            field=models.CharField(blank=True, default="", max_length=400),
        ),
        migrations.AddField(
            model_name="kitap",
            name="arama",
            field=models.CharField(blank=True, default="", max_length=800),
        ),
        migrations.RunPython(backfill_ogrenci, migrations.RunPython.noop),
        migrations.RunPython(backfill_kitap, migrations.RunPython.noop),
    ]