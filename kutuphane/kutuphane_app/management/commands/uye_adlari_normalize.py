"""
R1.7: Üye ad/soyad alanlarını Türkçe baş harf biçimine çevirir.

e-okul listeleri büyük harfli gelir ("YILDIRIM KIZIL"). İçe aktarma artık
normalize etse de (K9.13), daha önce eklenmiş kayıtlar elle düzeltilmelidir.

Kapsam: `ad` ve `soyad` alanı olan tüm üyeler (öğrenci, öğretmen, editör, personel).
`arama` alanı `Uye.save()` içinde yeniden kurulur (K6.4).
Öğrenci no, rol, sınıf, aktiflik, ödünç geçmişi dokunulmaz.

Kullanım:
  python manage.py uye_adlari_normalize --dry-run    # yalnızca önizleme
  python manage.py uye_adlari_normalize             # uygular (atomik)
  python manage.py uye_adlari_normalize --rol Ogrenci
  python manage.py uye_adlari_normalize --detay     # değişen isimleri listeler

Idempotenttir: ikinci çalıştırmada hiçbir kayıt değişmez.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from kutuphane_app.models import Uye
from kutuphane_app.turkish import bas_harf_buyut


class Command(BaseCommand):
    help = "Üye ad/soyad alanlarını Türkçe baş harf biçimine çevirir (R1.7)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Değişiklikleri uygulamadan, yalnızca say ve örnek listeler.",
        )
        parser.add_argument(
            "--rol",
            help="Yalnızca bu roldeki üyeler (örn. Ogrenci). Varsayılan: tümü.",
        )
        parser.add_argument(
            "--detay",
            action="store_true",
            help="Değişen her kaydı eski → yeni biçimiyle yazdır.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="En fazla N kaydı işle (0 = sınırsız).",
        )

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        detay = opts["detay"]
        limit = opts["limit"] or None

        qs = Uye.objects.select_related("rol").order_by("id")
        rol = (opts.get("rol") or "").strip()
        if rol:
            qs = qs.filter(rol__ad__iexact=rol)
        if limit:
            qs = qs[:limit]

        degisen = []
        for u in qs.iterator():
            yeni_ad = bas_harf_buyut(u.ad)
            yeni_soyad = bas_harf_buyut(u.soyad)
            if yeni_ad == u.ad and yeni_soyad == u.soyad:
                continue
            degisen.append((u, yeni_ad, yeni_soyad))

        self.stdout.write(
            f"Taranan: {qs.count()} | Değişecek kayıt: {len(degisen)}"
        )
        if not degisen:
            self.stdout.write(self.style.SUCCESS("Değiştirilecek kayıt yok."))
            return

        if detay or dry_run:
            for u, ad, soyad in degisen[: (200 if not detay else len(degisen))]:
                self.stdout.write(
                    f"  #{u.id} {u.uye_no or '-':<10} {u.ad} {u.soyad}"
                    f"  ->  {ad} {soyad}"
                )
            if not detay and len(degisen) > 200:
                self.stdout.write(f"  … ({len(degisen) - 200} kayıt daha)")

        if dry_run:
            self.stdout.write(self.style.WARNING("--dry-run: hiçbir değişiklik yapılmadı."))
            return

        with transaction.atomic():
            for u, ad, soyad in degisen:
                u.ad = ad
                u.soyad = soyad
                u.save()  # arama alanı yeniden kurulur (K6.4)

        self.stdout.write(
            self.style.SUCCESS(f"{len(degisen)} üyenin ad/soyadı normalize edildi.")
        )
