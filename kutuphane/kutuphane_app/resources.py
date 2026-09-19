# kutuphane_app/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.utils.timezone import now
from .models import Uye, Sinif, Rol

class UyeResource(resources.ModelResource):
    # Varsayılan KAPALI: True yalnızca "tam yoklama senkronu" yapılırken açılmalı.
    # Kısmi bir CSV (tek sınıf, yeni kayıtlar vb.) yüklendiğinde listede olmayan
    # öğrenciler pasifleştirilmez.
    pasiflestir = False

    sinif = fields.Field(
        column_name="sinif",
        attribute="sinif",
        widget=ForeignKeyWidget(Sinif, "ad"),
    )

    rol = fields.Field(
        column_name="rol",
        attribute="rol",
        widget=ForeignKeyWidget(Rol, "ad"),
    )

    class Meta:
        model = Uye
        import_id_fields = ('uye_no',)     # eşleşme anahtarı
        fields = ('uye_no', 'ad', 'soyad', 'sinif', 'rol')  # CSV’de beklenen minimum
        skip_unchanged = True
        report_skipped = True


    def before_import(self, dataset, *args, **kwargs):
        """Sürüm uyumlu: args/kwargs her çağrı şeklini karşılar."""
        self.gelen_ogr_no = set()

        headers = getattr(dataset, "headers", None)
        if dataset is not None and headers:
            try:
                idx = headers.index("uye_no")
                for row in dataset:
                    if len(row) > idx:
                        self.gelen_ogr_no.add(str(row[idx]).strip())
            except (ValueError, AttributeError):
                # 'uye_no' sütunu yoksa sessiz geç
                pass

        # ÖNEMLİ: parent çağrı
        return super().before_import(dataset, *args, **kwargs)

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        # Listede olmayanları pasifle — yalnızca tam senkron bilinçli olarak açılırsa.
        if self.pasiflestir and getattr(self, 'gelen_ogr_no', None) and not dry_run:
            adaylar = Uye.objects.exclude(uye_no__in=self.gelen_ogr_no).filter(aktif=True)
            adaylar.update(aktif=False, pasif_tarihi=now())
