"""
Eski kütüphane veritabanından (kutuphane_eski) katalog verisini aktarır.

Kapsam (bkz. masaüstü db_aktarim_talimati.txt):
  - Yazar, Kategori, Kitap, KitapNusha (raf_kodu aynen korunur)
  - Raf (nüshalardaki raf_kodu değerlerinden türetilir)
  - Rol + RoleLoanPolicy (ödünç kuralları)
  - LoanPolicy (genel ödünç ayarları)

Aktarılmaz: üye/öğrenci, ödünç geçmişi, arşiv, personel, sayım, auditlog.

Kullanım:
  python manage.py eski_veri_aktar --eski-db kutuphane_eski
  python manage.py eski_veri_aktar --eski-db kutuphane_eski --dry-run
  python manage.py eski_veri_aktar --eski-db kutuphane_eski --odunctekileri-mevcut-yap

Idempotenttir: doğal anahtarlarla (barkod, kategori/raf adı, yazar adı,
kitap isbn veya başlık+yazar) eşleşen kayıtlar yeniden oluşturulmaz.
"""
import psycopg2
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from kutuphane_app.models import (
    Rol, RoleLoanPolicy, LoanPolicy, Yazar, Kategori, Raf, Kitap, KitapNusha,
)
from kutuphane_app.turkish import fold


def _fold(value):
    """Türkçe'ye uygun aksan/harf duyarsız anahtar (İ/I, ç/ş/ğ/ö/ü)."""
    return fold((value or "").strip())


class Command(BaseCommand):
    help = "Eski kutuphane DB'sinden katalog verisini aktarır (Yazar/Kategori/Kitap/Nüsha/Raf + ödünç kuralları)."

    def add_arguments(self, parser):
        parser.add_argument("--eski-db", default="kutuphane_eski",
                            help="Eski veriyi içeren veritabanı adı (varsayılan: kutuphane_eski).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Yalnızca rapor üret; hiçbir kayıt yazma (işlem geri alınır).")
        parser.add_argument("--odunctekileri-mevcut-yap", action="store_true",
                            help="Eski 'oduncte' nüshaları 'mevcut' yap (ödünçler aktarılmadığı için önerilir).")

    def _connect(self, eski_db):
        db = settings.DATABASES["default"]
        try:
            conn = psycopg2.connect(
                dbname=eski_db,
                user=db["USER"],
                password=db["PASSWORD"],
                host=db["HOST"] or "localhost",
                port=db["PORT"] or "5432",
            )
        except psycopg2.Error as exc:
            raise CommandError(f"Eski DB'ye bağlanılamadı ({eski_db}): {exc}")
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.kutuphane_app_kitap')")
        if cur.fetchone()[0] is None:
            raise CommandError(f"'{eski_db}' içinde beklenen kutuphane_app_* tabloları yok.")
        return conn, cur

    def handle(self, *args, **options):
        eski_db = options["eski_db"]
        dry = options["dry_run"]
        oduncte_mevcut = options["odunctekileri_mevcut_yap"]

        conn, cur = self._connect(eski_db)
        self.stdout.write(f"Eski kaynak: {eski_db}  (dry-run={dry}, oduncte→mevcut={oduncte_mevcut})")

        sayac = {}
        try:
            with transaction.atomic():
                self._rol_aktar(cur, sayac)
                self._politika_aktar(cur, sayac)
                self._yazar_aktar(cur, sayac)
                self._kategori_aktar(cur, sayac)
                self._raf_aktar(cur, sayac)
                self._kitap_aktar(cur, sayac)
                self._nusha_aktar(cur, sayac, oduncte_mevcut)
                self._arama_tazele(sayac)

                if dry:
                    transaction.set_rollback(True)
        finally:
            cur.close()
            conn.close()

        self.stdout.write(self.style.SUCCESS("Aktarım raporu:"))
        for key in sorted(sayac):
            self.stdout.write(f"  {key:22} {sayac[key]}")
        if dry:
            self.stdout.write(self.style.WARNING("DRY-RUN: hiçbir kayıt yazılmadı."))
        else:
            self.stdout.write(self.style.SUCCESS("Aktarım tamamlandı."))

    # --- adım adım ---
    def _rol_aktar(self, cur, sayac):
        rol_by_fold = {_fold(r.ad): r for r in Rol.objects.all()}
        # Eski sistemdeki rol adlarını yeni sistemin kanonik adlarına eşle.
        kanonik = {"ogrenci": "Öğrenci", "ogretmen": "Öğretmen", "editor": "Editör"}
        cur.execute("SELECT id, ad FROM kutuphane_app_rol ORDER BY id")
        rol_map = {}
        yeni = 0
        for oid, ad in cur.fetchall():
            key = _fold(ad)
            hedef = kanonik.get(key, (ad or "").strip())
            rol = rol_by_fold.get(_fold(hedef)) or rol_by_fold.get(key)
            if rol is None:
                rol = Rol.objects.create(ad=hedef)
                rol_by_fold[_fold(rol.ad)] = rol
                yeni += 1
            rol_map[oid] = rol
        sayac["rol_toplam"] = len(rol_map)
        sayac["rol_yeni"] = yeni
        self._rol_map = rol_map

    def _politika_aktar(self, cur, sayac):
        # RoleLoanPolicy
        cur.execute("""
            SELECT role_id, duration, max_items, delay_grace_days, penalty_delay_days,
                   shift_weekend, penalty_max_per_loan, penalty_max_per_student, daily_penalty_rate
            FROM kutuphane_app_roleloanpolicy
        """)
        n = 0
        for (role_id, duration, max_items, dgd, pdd, shift, pmpl, pmps, dpr) in cur.fetchall():
            rol = self._rol_map.get(role_id)
            if rol is None:
                continue
            RoleLoanPolicy.objects.update_or_create(
                role=rol,
                defaults=dict(
                    duration=duration, max_items=max_items, delay_grace_days=dgd,
                    penalty_delay_days=pdd, shift_weekend=shift,
                    penalty_max_per_loan=pmpl, penalty_max_per_student=pmps,
                    daily_penalty_rate=dpr,
                ),
            )
            n += 1
        sayac["roleloanpolicy"] = n

        # LoanPolicy (tekil)
        cur.execute("""
            SELECT default_duration, default_max_items, delay_grace_days, penalty_delay_days,
                   shift_weekend, auto_extend_enabled, auto_extend_days, auto_extend_limit,
                   quarantine_days, require_damage_note, require_shelf_code,
                   quiet_hours_enabled, quiet_hours_start, quiet_hours_end,
                   penalty_max_per_loan, penalty_max_per_student
            FROM kutuphane_app_loanpolicy LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            alanlar = [
                "default_duration", "default_max_items", "delay_grace_days", "penalty_delay_days",
                "shift_weekend", "auto_extend_enabled", "auto_extend_days", "auto_extend_limit",
                "quarantine_days", "require_damage_note", "require_shelf_code",
                "quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end",
                "penalty_max_per_loan", "penalty_max_per_student",
            ]
            lp, _ = LoanPolicy.objects.get_or_create(singleton_key="default")
            for alan, deger in zip(alanlar, row):
                setattr(lp, alan, deger)
            lp.save()
            sayac["loanpolicy"] = 1
        else:
            sayac["loanpolicy"] = 0

    def _yazar_aktar(self, cur, sayac):
        existing = {_fold(y.ad_soyad): y for y in Yazar.objects.all()}
        cur.execute("SELECT id, ad_soyad FROM kutuphane_app_yazar ORDER BY id")
        yazar_map = {}
        yeni = 0
        for oid, ad_soyad in cur.fetchall():
            name = (ad_soyad or "").strip()
            key = _fold(name)
            y = existing.get(key)
            if y is None:
                y = Yazar.objects.create(ad_soyad=name)
                existing[key] = y
                yeni += 1
            yazar_map[oid] = y
        sayac["yazar_toplam"] = len(yazar_map)
        sayac["yazar_yeni"] = yeni
        self._yazar_map = yazar_map

    def _kategori_aktar(self, cur, sayac):
        existing = {_fold(k.ad): k for k in Kategori.objects.all()}
        cur.execute("SELECT id, ad FROM kutuphane_app_kategori ORDER BY id")
        kategori_map = {}
        yeni = 0
        for oid, ad in cur.fetchall():
            name = (ad or "").strip()
            key = _fold(name)
            k = existing.get(key)
            if k is None:
                k = Kategori.objects.create(ad=name)
                existing[key] = k
                yeni += 1
            kategori_map[oid] = k
        sayac["kategori_toplam"] = len(kategori_map)
        sayac["kategori_yeni"] = yeni
        self._kategori_map = kategori_map

    def _raf_aktar(self, cur, sayac):
        existing = {_fold(r.ad): r for r in Raf.objects.all()}
        cur.execute("""
            SELECT DISTINCT raf_kodu FROM kutuphane_app_kitapnusha
            WHERE raf_kodu IS NOT NULL AND btrim(raf_kodu) <> ''
        """)
        raf_map = {}
        yeni = 0
        for (kod,) in cur.fetchall():
            name = (kod or "").strip()
            key = _fold(name)
            r = existing.get(key)
            if r is None:
                r = Raf.objects.create(ad=name)
                existing[key] = r
                yeni += 1
            raf_map[key] = r
        sayac["raf_toplam"] = len(raf_map)
        sayac["raf_yeni"] = yeni
        self._raf_map = raf_map

    def _kitap_aktar(self, cur, sayac):
        existing = list(Kitap.objects.select_related("yazar", "kategori"))
        by_isbn = {}
        by_baslik_yazar = {}
        for k in existing:
            if k.isbn:
                by_isbn.setdefault(k.isbn.strip(), k)
            by_baslik_yazar.setdefault((_fold(k.baslik), k.yazar_id), k)

        cur.execute("""
            SELECT id, baslik, yayin_yili, isbn, kategori_id, yazar_id, aciklama,
                   resim1, resim2, resim3, resim4, resim5
            FROM kutuphane_app_kitap ORDER BY id
        """)
        kitap_map = {}
        yeni = 0
        for (oid, baslik, yil, isbn, kat_id, yaz_id, aciklama,
             r1, r2, r3, r4, r5) in cur.fetchall():
            yazar = self._yazar_map.get(yaz_id)
            kategori = self._kategori_map.get(kat_id)
            isbn_s = (isbn or "").strip() or None

            k = by_isbn.get(isbn_s) if isbn_s else None
            if k is None:
                k = by_baslik_yazar.get((_fold(baslik), yazar.id if yazar else None))
            if k is None:
                k = Kitap(
                    baslik=baslik, yazar=yazar, kategori=kategori,
                    yayin_yili=yil, isbn=isbn_s, aciklama=aciklama or "",
                    resim1=r1 or None, resim2=r2 or None, resim3=r3 or None,
                    resim4=r4 or None, resim5=r5 or None,
                )
                k.save()
                if isbn_s:
                    by_isbn[isbn_s] = k
                by_baslik_yazar[(_fold(k.baslik), k.yazar_id)] = k
                yeni += 1
            kitap_map[oid] = k
        sayac["kitap_toplam"] = len(kitap_map)
        sayac["kitap_yeni"] = yeni
        self._kitap_map = kitap_map

    def _nusha_aktar(self, cur, sayac, oduncte_mevcut):
        existing_barkod = set(KitapNusha.objects.values_list("barkod", flat=True))
        cur.execute("""
            SELECT id, barkod, durum, raf_kodu, kitap_id
            FROM kutuphane_app_kitapnusha ORDER BY id
        """)
        atlanan = 0
        oduncte = 0
        toplu = []
        for (oid, barkod, durum, raf_kodu, kitap_id) in cur.fetchall():
            if barkod in existing_barkod:
                atlanan += 1
                continue
            kitap = self._kitap_map.get(kitap_id)
            if kitap is None:
                atlanan += 1
                continue
            d = durum or "mevcut"
            if d == "oduncte":
                oduncte += 1
                if oduncte_mevcut:
                    d = "mevcut"
            raf = self._raf_map.get(_fold(raf_kodu)) if raf_kodu else None
            toplu.append(KitapNusha(
                kitap=kitap, barkod=barkod, durum=d,
                raf_kodu=(raf_kodu or None), raf=raf,
            ))
            existing_barkod.add(barkod)
        if toplu:
            KitapNusha.objects.bulk_create(toplu, batch_size=500)
        sayac["nusha_yeni"] = len(toplu)
        sayac["nusha_atlanan"] = atlanan
        sayac["nusha_oduncte_kaynak"] = oduncte

    def _arama_tazele(self, sayac):
        # Nüshalar oluştuktan sonra Kitap.arama'yı raf kodlarıyla tazele.
        n = 0
        for k in {id(v): v for v in self._kitap_map.values()}.values():
            k.save()
            n += 1
        sayac["arama_tazelenen"] = n
