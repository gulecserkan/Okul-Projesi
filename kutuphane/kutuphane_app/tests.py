"""
Çekirdek testler: ödünç politikası, checkout akışı, barkod üretimi,
alan şifreleme (KVKK) ve personel güvenliği.
"""

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from kutuphane_app.models import (
    Kategori,
    Kitap,
    KitapNusha,
    LoanPolicy,
    Ogrenci,
    OduncKaydi,
    Personel,
    Rol,
    Sinif,
    Yazar,
)
from kutuphane_app.serializers import KitapNushaSerializer
from kutuphane_app.loan_policy import (
    calculate_penalty,
    compute_assigned_due,
    is_role_blocked,
)


def make_policy(**kw):
    defaults = dict(
        default_duration=15,
        default_max_items=2,
        delay_grace_days=0,
        penalty_delay_days=0,
        shift_weekend=False,
        auto_extend_enabled=False,
        auto_extend_days=0,
        auto_extend_limit=1,
        quarantine_days=0,
        require_damage_note=False,
        require_shelf_code=False,
        penalty_max_per_loan=Decimal("0"),
        penalty_max_per_student=Decimal("0"),
    )
    defaults.update(kw)
    policy, _ = LoanPolicy.objects.get_or_create(
        singleton_key="default", defaults=defaults
    )
    for key, value in defaults.items():
        setattr(policy, key, value)
    policy.save()
    return policy


def make_book_and_copy(baslik="Test Kitap", barkod=None):
    yazar, _ = Yazar.objects.get_or_create(ad_soyad="Test Yazar")
    kategori, _ = Kategori.objects.get_or_create(ad="Test Kategori")
    kitap = Kitap.objects.create(baslik=baslik, yazar=yazar, kategori=kategori)
    nusha = KitapNusha.objects.create(kitap=kitap, barkod=barkod or "KIT000900")
    return kitap, nusha


class LoanPolicyUnitTests(TestCase):
    def test_penalty_zero_rate(self):
        make_policy()
        self.assertIsNone(calculate_penalty(None, None, overdue_days=10, penalty_delay_days=0, rate=Decimal("0")))

    def test_penalty_with_grace_and_caps(self):
        make_policy(
            delay_grace_days=3,
            penalty_delay_days=2,
            penalty_max_per_loan=Decimal("5.00"),
            penalty_max_per_student=Decimal("8.00"),
        )
        snapshot = policy_snapshot()
        pen = calculate_penalty(snapshot, None, overdue_days=20, penalty_delay_days=2, rate=Decimal("0.50"))
        # chargeable = 20 - 2 = 18 -> 9.00 ama loan cap 5.00
        self.assertEqual(pen, Decimal("5.00"))

        pen2 = calculate_penalty(snapshot, None, overdue_days=1, penalty_delay_days=0, rate=Decimal("0.50"))
        self.assertEqual(pen2, Decimal("0.50"))  # 1 gun * 0.50 -> loan cap alti

    def test_assigned_due_weekend_shift(self):
        make_policy(default_duration=1, shift_weekend=True)
        friday = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        while friday.weekday() != 4:
            friday -= timedelta(days=1)
        due = compute_assigned_due(friday, 1, policy_snapshot())
        self.assertEqual(due.weekday(), 0)  # cumartesi -> pazartesi

    def test_role_blocked(self):
        make_policy(default_duration=0, default_max_items=2)
        self.assertTrue(is_role_blocked(policy_snapshot(), None))


class BarcodeGenerationTests(TestCase):
    def test_sequential_barcodes(self):
        yazar = Yazar.objects.create(ad_soyad="Otomatik Yazar")
        kategori = Kategori.objects.create(ad="Otomatik Kategori")
        kitap = Kitap.objects.create(baslik="Auto Barkod", yazar=yazar, kategori=kategori)
        s1 = KitapNushaSerializer(data={"kitap_id": kitap.id})
        s2 = KitapNushaSerializer(data={"kitap_id": kitap.id})
        self.assertTrue(s1.is_valid(), s1.errors)
        self.assertTrue(s2.is_valid(), s2.errors)
        n1 = s1.save()
        n2 = s2.save()
        self.assertEqual(n1.barkod, "KIT000001")
        self.assertEqual(n2.barkod, "KIT000002")

    def test_override_then_next(self):
        kitap, nusha = make_book_and_copy(barkod="KIT000099")
        s = KitapNushaSerializer(data={"kitap_id": kitap.id})
        self.assertTrue(s.is_valid(), s.errors)
        auto = s.save()
        self.assertEqual(auto.barkod, "KIT000100")


class EncryptionTests(TestCase):
    def test_sensitive_fields_encrypted_at_rest(self):
        sinif = Sinif.objects.create(ad="5-A")
        rol = Rol.objects.create(ad="Öğrenci")
        o = Ogrenci.objects.create(
            ad="Ali",
            soyad="Veli",
            ogrenci_no="T001",
            sinif=sinif,
            rol=rol,
            telefon="05321234567",
            eposta="ali@ornek.com",
        )
        with connection.cursor() as cur:
            cur.execute("SELECT telefon, eposta FROM kutuphane_app_ogrenci WHERE id=%s", [o.id])
            raw_telefon, raw_eposta = cur.fetchone()
        self.assertTrue(raw_telefon.startswith("gAAAA"))
        self.assertTrue(raw_eposta.startswith("gAAAA"))
        self.assertEqual(o.telefon, "05321234567")
        self.assertEqual(o.eposta, "ali@ornek.com")

    def test_legacy_plaintext_readable(self):
        sinif = Sinif.objects.create(ad="5-B")
        rol = Rol.objects.create(ad="Öğrenci")
        o = Ogrenci.objects.create(
            ad="Ayşe", soyad="Yılmaz", ogrenci_no="T002", sinif=sinif, rol=rol
        )
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE kutuphane_app_ogrenci SET telefon=%s WHERE id=%s",
                ["05551234567", o.id],
            )
        o.refresh_from_db()
        self.assertEqual(o.telefon, "05551234567")


class CheckoutAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testkutuphaneci", password="z1!")
        self.client.force_authenticate(self.user)
        make_policy()
        self.sinif = Sinif.objects.create(ad="6-A")
        self.rol = Rol.objects.create(ad="Öğrenci")
        self.ogrenci = Ogrenci.objects.create(
            ad="Mehmet",
            soyad="Demir",
            ogrenci_no="60123",
            sinif=self.sinif,
            rol=self.rol,
        )
        self.kitap, self.nusha = make_book_and_copy(barkod="KIT0000999")

    def test_successful_checkout(self):
        resp = self.client.post(
            "/api/checkout/", {"ogrenci_no": "60123", "barkod": "KIT0000999"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.nusha.refresh_from_db()
        self.assertEqual(self.nusha.durum, "oduncte")
        self.assertTrue(OduncKaydi.objects.filter(ogrenci=self.ogrenci).exists())

    def test_duplicate_checkout_rejected(self):
        self.client.post("/api/checkout/", {"ogrenci_no": "60123", "barkod": "KIT0000999"}, format="json")
        resp = self.client.post("/api/checkout/", {"ogrenci_no": "60123", "barkod": "KIT0000999"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_student_not_found(self):
        resp = self.client.post("/api/checkout/", {"ogrenci_no": "YOK999", "barkod": "KIT0000999"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_pasif_student_rejected(self):
        self.ogrenci.aktif = False
        self.ogrenci.save()
        resp = self.client.post("/api/checkout/", {"ogrenci_no": "60123", "barkod": "KIT0000999"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.nusha.refresh_from_db()
        self.assertEqual(self.nusha.durum, "mevcut")

    def test_max_items_reached(self):
        policy = make_policy(default_max_items=1)
        self.client.post("/api/checkout/", {"ogrenci_no": "60123", "barkod": "KIT0000999"}, format="json")
        kitap2, nusha2 = make_book_and_copy(baslik="İkinci Kitap", barkod="KIT0000989")
        resp = self.client.post("/api/checkout/", {"ogrenci_no": "60123", "barkod": nusha2.barkod}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        _ = kitap2
        _ = policy


class PersonelSecurityTests(APITestCase):
    def setUp(self):
        User.objects.create_user(username="admin", password="a1!", is_staff=True)
        self.normal_user = User.objects.create_user(username="person", password="p1!")
        self.client.force_authenticate(self.normal_user)

    def test_normal_user_cannot_create_personel(self):
        resp = self.client.post(
            "/api/personel/",
            {"ad_soyad": "Yeni Kişi", "kullanici_adi": "yeniki", "rol": "personel"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_normal_user_cannot_update_personel(self):
        admin_user = User.objects.get(username="admin")
        Personel.objects.create(
            ad_soyad="Mevcut", kullanici_adi="mevcut", rol="personel", user=admin_user
        )
        resp = self.client.patch("/api/personel/1/", {"ad_soyad": "Hack"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_and_update(self):
        self.client.force_authenticate(User.objects.get(username="admin"))
        resp = self.client.post(
            "/api/personel/",
            {"ad_soyad": "Yeni Kişi", "kullanici_adi": "yeniki", "rol": "personel"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        pid = resp.data["id"]
        upd = self.client.patch(f"/api/personel/{pid}/", {"ad_soyad": "Yeni Kişi 2"}, format="json")
        self.assertEqual(upd.status_code, status.HTTP_200_OK)
        self.assertEqual(upd.data["ad_soyad"], "Yeni Kişi 2")
        # kullanici_adi güncellemede kilitli
        upd2 = self.client.patch(
            f"/api/personel/{pid}/", {"kullanici_adi": "sifirlandi"}, format="json"
        )
        self.assertEqual(upd2.status_code, status.HTTP_200_OK)
        self.assertEqual(upd2.data["kullanici_adi"], "yeniki")

    def test_personel_list_hides_sensitive_fields(self):
        admin_user = User.objects.get(username="admin")
        Personel.objects.create(
            ad_soyad="Mevcut", kullanici_adi="mevcut1", rol="personel", user=admin_user
        )
        resp = self.client.get("/api/personel/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        first = data["results"][0] if isinstance(data, dict) and data.get("results") else data[0]
        self.assertNotIn("sifre_hash", first)
        self.assertNotIn("user", first)
        self.assertEqual(set(first.keys()), {"id", "ad_soyad", "kullanici_adi", "rol"})


def policy_snapshot():
    from kutuphane_app.loan_policy import get_snapshot

    return get_snapshot()


class SearchFilterAPITests(APITestCase):
    """Ogrenci/Kitap listelerinde q arama filtresi (Türkçe karakter duyarlı)."""

    def setUp(self):
        self.user = User.objects.create_user(username="testara", password="z1!")
        self.client.force_authenticate(self.user)
        self.sinif = Sinif.objects.create(ad="5-A")
        self.rol = Rol.objects.create(ad="Öğrenci")
        self.ogrenci = Ogrenci.objects.create(
            ad="İlber", soyad="Ortaylı", ogrenci_no="5A01", sinif=self.sinif, rol=self.rol
        )
        Ogrenci.objects.create(
            ad="Zeynep", soyad="Kaya", ogrenci_no="5A02", sinif=self.sinif, rol=self.rol
        )
        self.yazar = Yazar.objects.create(ad_soyad="Halil İnalcık")
        self.kategori = Kategori.objects.create(ad="Tarih")
        self.kitap = Kitap.objects.create(
            baslik="Osmanlı Tarihi", yazar=self.yazar, kategori=self.kategori
        )
        KitapNusha.objects.create(kitap=self.kitap, barkod="KIT000001", raf_kodu="R27")
        KitapNusha.objects.create(kitap=self.kitap, barkod="KIT000002", raf_kodu="R27")
        siir_kat = Kategori.objects.create(ad="Şiir")
        siir = Kitap.objects.create(
            baslik="Şiirler", yazar=Yazar.objects.create(ad_soyad="Orhan Veli"), kategori=siir_kat
        )
        KitapNusha.objects.create(kitap=siir, barkod="KIT000003", raf_kodu="R30")

    @staticmethod
    def _as_list(data):
        return data["results"] if isinstance(data, dict) else data

    def test_ogrenci_q_turkce_dot_duyarli(self):
        # küçük i → büyük İ ("ilber" ↔ "İlber")
        resp = self.client.get("/api/ogrenciler/", {"q": "ilber"})
        self.assertEqual([o["ogrenci_no"] for o in self._as_list(resp.data)], ["5A01"])

        resp = self.client.get("/api/ogrenciler/", {"q": "İlber"})
        self.assertEqual([o["ogrenci_no"] for o in self._as_list(resp.data)], ["5A01"])

        # büyük I alt okuduğu → ı ("ORTAYLI" ↔ "Ortaylı")
        resp = self.client.get("/api/ogrenciler/", {"q": "ORTAYLI"})
        self.assertEqual([o["ogrenci_no"] for o in self._as_list(resp.data)], ["5A01"])

        resp = self.client.get("/api/ogrenciler/", {"q": "ortayl"})
        self.assertEqual([o["ogrenci_no"] for o in self._as_list(resp.data)], ["5A01"])

        resp = self.client.get("/api/ogrenciler/", {"q": "kaya"})
        self.assertEqual([o["ogrenci_no"] for o in self._as_list(resp.data)], ["5A02"])

        resp = self.client.get("/api/ogrenciler/", {"q": "5-A"})
        self.assertEqual(len(self._as_list(resp.data)), 2)

        resp = self.client.get("/api/ogrenciler/", {"q": "YOKBÖYLE"})
        self.assertEqual(self._as_list(resp.data), [])

    def test_ogrenci_q_rol_aksani(self):
        # rol adı da aranabilir ("öğrenci" ↔ "ogrenci" ya da "ÖĞRENCİ")
        resp = self.client.get("/api/ogrenciler/", {"q": "ogrenci"})
        self.assertEqual(len(self._as_list(resp.data)), 2)

    def test_kitap_q_turkce_ve_join_alanlari(self):
        # başlıktaki ı → i ("osmanlı" ↔ "Osmanlı")
        resp = self.client.get("/api/kitaplar/", {"q": "osmanli"})
        self.assertEqual([k["baslik"] for k in self._as_list(resp.data)], ["Osmanlı Tarihi"])

        # yazar adındaki İ ("inalcik" ↔ "İnalcık")
        resp = self.client.get("/api/kitaplar/", {"q": "inalcik"})
        self.assertEqual([k["baslik"] for k in self._as_list(resp.data)], ["Osmanlı Tarihi"])

        # ş → s başlık ve kategori ("şiir")
        resp = self.client.get("/api/kitaplar/", {"q": "siir"})
        self.assertEqual([k["baslik"] for k in self._as_list(resp.data)], ["Şiirler"])

        # yazar: "orhan"
        resp = self.client.get("/api/kitaplar/", {"q": "orhan"})
        self.assertEqual([k["baslik"] for k in self._as_list(resp.data)], ["Şiirler"])

        # kategori: "tarih"
        resp = self.client.get("/api/kitaplar/", {"q": "tarih"})
        self.assertEqual([k["baslik"] for k in self._as_list(resp.data)], ["Osmanlı Tarihi"])

        # raf kodu — aynı kitabın iki nüşçesi eşleşse bile tek sonuç
        resp = self.client.get("/api/kitaplar/", {"q": "R27"})
        self.assertEqual(len(self._as_list(resp.data)), 1)

    def test_serializer_arama_gizli(self):
        resp = self.client.get("/api/ogrenciler/", {"q": "ilber"})
        row = self._as_list(resp.data)[0]
        self.assertNotIn("arama", row)