from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0015_move_role_settings_to_roleloanpolicy"),
    ]

    operations = [
        migrations.AddField(
            model_name="kitap",
            name="aciklama",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="kitap",
            name="resim1",
            field=models.ImageField(blank=True, null=True, upload_to="kitap_resimleri/"),
        ),
        migrations.AddField(
            model_name="kitap",
            name="resim2",
            field=models.ImageField(blank=True, null=True, upload_to="kitap_resimleri/"),
        ),
        migrations.AddField(
            model_name="kitap",
            name="resim3",
            field=models.ImageField(blank=True, null=True, upload_to="kitap_resimleri/"),
        ),
        migrations.AddField(
            model_name="kitap",
            name="resim4",
            field=models.ImageField(blank=True, null=True, upload_to="kitap_resimleri/"),
        ),
        migrations.AddField(
            model_name="kitap",
            name="resim5",
            field=models.ImageField(blank=True, null=True, upload_to="kitap_resimleri/"),
        ),
    ]
