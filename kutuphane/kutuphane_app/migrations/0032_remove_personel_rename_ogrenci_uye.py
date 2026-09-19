from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def personel_to_user(apps, schema_editor):
    """Personel kayıtlarını User'a yansıtır (rol=admin → is_superuser).

    Personel tablosu kaldırılmadan önce çalışır.
    """
    Personel = apps.get_model("kutuphane_app", "Personel")
    User = apps.get_model("auth", "User")
    for p in Personel.objects.all():
        user = p.user
        if user is None:
            user, _ = User.objects.get_or_create(
                username=p.kullanici_adi,
                defaults={"password": "!"},
            )
        user.is_superuser = (p.rol == "admin")
        user.is_staff = (p.rol == "admin")
        if not user.first_name and p.ad_soyad:
            user.first_name = p.ad_soyad
        user.save()
        if p.user_id != user.id:
            p.user = user
            p.save(update_fields=["user"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0031_ogrenci_parola_degistirilsin_ogrenci_user"),
    ]

    operations = [
        # 1) Personel → User rol yansıt, sonra Personel'i kaldır
        migrations.RunPython(personel_to_user, noop),
        migrations.DeleteModel(name="Personel"),
        # 2) Ogrenci → Uye
        migrations.RenameModel(old_name="Ogrenci", new_name="Uye"),
        migrations.RenameField(
            model_name="uye", old_name="ogrenci_no", new_name="uye_no"
        ),
        migrations.RenameField(
            model_name="odunckaydi", old_name="ogrenci", new_name="uye"
        ),
        # 3) Arşiv modelleri de üye terminolojisine
        migrations.RenameModel(old_name="ArsivOgrenci", new_name="ArsivUye"),
        migrations.RenameField(
            model_name="arsivuye", old_name="ogrenci_no", new_name="uye_no"
        ),
        migrations.RenameField(
            model_name="arsivodunc", old_name="ogrenci_no", new_name="uye_no"
        ),
        migrations.AlterField(
            model_name="arsivuye",
            name="batch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="arsiv_uyeler",
                to="kutuphane_app.arsivbatch",
            ),
        ),
        # 4) Uye.uye_no opsiyonel (personel/editör için)
        migrations.AlterField(
            model_name="uye",
            name="uye_no",
            field=models.CharField(
                blank=True, max_length=20, null=True, unique=True
            ),
        ),
        # 5) Uye.user related_name = "uye"
        migrations.AlterField(
            model_name="uye",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="uye",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
