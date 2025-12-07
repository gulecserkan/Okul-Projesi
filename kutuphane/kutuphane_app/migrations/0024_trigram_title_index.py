from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0023_inventorysession_inventoryitem"),
    ]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name="kitap",
            index=GinIndex(
                name="kitap_baslik_trgm",
                fields=["baslik"],
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]
