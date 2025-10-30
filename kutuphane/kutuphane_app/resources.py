# kutuphane_app/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.utils.timezone import now
from .models import Ogrenci, Sinif

class OgrenciResource(resources.ModelResource):
    sinif = fields.Field(
        column_name="sinif",
        attribute="sinif",
        widget=ForeignKeyWidget(Sinif, "ad"),
    )

    class Meta:
        model = Ogrenci
        import_id_fields = ('ogrenci_no',)     # eşleşme anahtarı
        fields = ('ogrenci_no', 'ad', 'soyad', 'sinif')  # CSV’de beklenen minimum
        skip_unchanged = True
        report_skipped = True


    def before_import(self, dataset, *args, **kwargs):
        """Sürüm uyumlu: args/kwargs her çağrı şeklini karşılar."""
        self.gelen_ogr_no = set()

        headers = getattr(dataset, "headers", None)
        if dataset is not None and headers:
            try:
                idx = headers.index("ogrenci_no")
                for row in dataset:
                    if len(row) > idx:
                        self.gelen_ogr_no.add(str(row[idx]).strip())
            except (ValueError, AttributeError):
                # 'ogrenci_no' sütunu yoksa sessiz geç
                pass

        # ÖNEMLİ: parent çağrı
        return super().before_import(dataset, *args, **kwargs)

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        # Listede olmayanları pasifle
        if getattr(self, 'gelen_ogr_no', None) and not dry_run:
            adaylar = Ogrenci.objects.exclude(ogrenci_no__in=self.gelen_ogr_no).filter(aktif=True)
            adaylar.update(aktif=False, pasif_tarihi=now())
