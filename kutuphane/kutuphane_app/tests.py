"""
Çekirdek testler: ödünç politikası, checkout akışı, barkod üretimi,
alan şifreleme (KVKK) ve personel güvenliği.
"""

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
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
    Raf,
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
from kutuphane_app.rules import (
    apply_student_status,
    can_delete_kitap,
    can_delete_nusha,
    can_delete_ogrenci,
    suggested_loss_penalty,
    validate_transition,
)
from kutuphane_app.book_lookup import (
    lookup_books,
    looks_like_isbn,
    normalize_isbn,
)


class _FakeResp:
    """`urlopen` taklidi için basit yanıt nesnesi (JSON gövde)."""

    def __init__(self, payload):
        import json as _json

        self._body = _json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


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


class RulesUnitTests(TestCase):
    """rules.py saf kurallar — geçiş matrisi, pasif_tarihi, silme, ceza önerisi."""

    def setUp(self):
        make_policy()
        self.sinif = Sinif.objects.create(ad="6-A")
        self.rol = Rol.objects.create(ad="Öğrenci")
        self.ogrenci = Ogrenci.objects.create(
            ad="Ali", soyad="Veli", ogrenci_no="60001", sinif=self.sinif, rol=self.rol
        )
        self.kitap, self.nusha = make_book_and_copy(barkod="KIT0000800")

    def _loan(self, durum="oduncte"):
        return OduncKaydi.objects.create(
            ogrenci=self.ogrenci,
            kitap_nusha=self.nusha,
            iade_tarihi=timezone.now() + timedelta(days=15),
            durum=durum,
        )

    def test_transition_valid(self):
        ok, err = validate_transition(self._loan(), "teslim", teslim_tarihi=timezone.now())
        self.assertTrue(ok)
        self.assertIsNone(err)
        ok2, _ = validate_transition(self._loan(), "iptal", teslim_tarihi=None)
        self.assertTrue(ok2)

    def test_transition_invalid_durum(self):
        ok, err = validate_transition(self._loan(), "oduncte", teslim_tarihi=timezone.now())
        self.assertFalse(ok)
        self.assertIn("Geçersiz", err)

    def test_transition_closed_rejected(self):
        loan = self._loan("teslim")
        ok, err = validate_transition(loan, "kayip", teslim_tarihi=timezone.now())
        self.assertFalse(ok)
        self.assertIn("kapanmış", err)

    def test_transition_requires_teslim_date(self):
        ok, err = validate_transition(self._loan(), "kayip", teslim_tarihi=None)
        self.assertFalse(ok)
        self.assertIn("teslim_tarihi", err)

    def test_student_pasif_sets_date_and_warns(self):
        self._loan()
        warnings = apply_student_status(self.ogrenci, False)
        self.ogrenci.refresh_from_db()
        self.assertFalse(self.ogrenci.aktif)
        self.assertIsNotNone(self.ogrenci.pasif_tarihi)
        self.assertTrue(any("aktif ödüncü var" in w for w in warnings))

    def test_student_back_active_clears_date(self):
        apply_student_status(self.ogrenci, False)
        apply_student_status(self.ogrenci, True)
        self.ogrenci.refresh_from_db()
        self.assertTrue(self.ogrenci.aktif)
        self.assertIsNone(self.ogrenci.pasif_tarihi)

    def test_delete_rules(self):
        self.assertTrue(can_delete_ogrenci(self.ogrenci))
        self.assertTrue(can_delete_nusha(self.nusha))
        self.assertTrue(can_delete_kitap(self.kitap))
        self._loan()
        self.assertFalse(can_delete_ogrenci(self.ogrenci))
        self.assertFalse(can_delete_nusha(self.nusha))
        self.assertFalse(can_delete_kitap(self.kitap))

    def test_suggested_loss_penalty(self):
        make_policy(kayip_hasar_cezasi=Decimal("15.00"))
        snapshot = policy_snapshot()
        self.assertEqual(suggested_loss_penalty(snapshot), Decimal("15.00"))
        make_policy(kayip_hasar_cezasi=Decimal("0"))
        self.assertIsNone(suggested_loss_penalty(policy_snapshot()))


class LoanCloseAPITests(APITestCase):
    """POST /api/oduncler/{id}/kapat/ — atomik kapanış ve ham PATCH kilidi."""

    def setUp(self):
        self.user = User.objects.create_user(username="testkutuphaneci", password="z1!")
        self.client.force_authenticate(self.user)
        make_policy()
        self.sinif = Sinif.objects.create(ad="6-B")
        self.rol = Rol.objects.create(ad="Öğrenci")
        self.ogrenci = Ogrenci.objects.create(
            ad="Mehmet", soyad="Demir", ogrenci_no="60124", sinif=self.sinif, rol=self.rol
        )
        self.kitap, self.nusha = make_book_and_copy(barkod="KIT0000777")

    def _checkout(self):
        resp = self.client.post(
            "/api/checkout/", {"ogrenci_no": "60124", "barkod": "KIT0000777"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        return OduncKaydi.objects.get(ogrenci=self.ogrenci)

    def _close(self, loan_id, payload):
        return self.client.post(f"/api/oduncler/{loan_id}/kapat/", payload, format="json")

    def test_close_teslim(self):
        loan = self._checkout()
        resp = self._close(loan.id, {"durum": "teslim", "teslim_tarihi": timezone.now().isoformat()})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        loan.refresh_from_db()
        self.nusha.refresh_from_db()
        self.assertEqual(loan.durum, "teslim")
        self.assertIsNotNone(loan.teslim_tarihi)
        self.assertEqual(self.nusha.durum, "mevcut")

    def test_close_kayip_syncs_nusha(self):
        loan = self._checkout()
        resp = self._close(loan.id, {"durum": "kayip", "teslim_tarihi": timezone.now().isoformat()})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.nusha.refresh_from_db()
        self.assertEqual(self.nusha.durum, "kayip")

    def test_close_kayip_requires_teslim_date(self):
        loan = self._checkout()
        resp = self._close(loan.id, {"durum": "kayip"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.nusha.refresh_from_db()
        self.assertEqual(self.nusha.durum, "oduncte")

    def test_close_hasarli_with_penalty_and_paid(self):
        loan = self._checkout()
        resp = self._close(loan.id, {
            "durum": "hasarli",
            "teslim_tarihi": timezone.now().isoformat(),
            "gecikme_cezasi": "12.50",
            "gecikme_cezasi_odendi": True,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        loan.refresh_from_db()
        self.assertEqual(loan.durum, "hasarli")
        self.assertEqual(loan.gecikme_cezasi, Decimal("12.50"))
        self.assertTrue(loan.gecikme_cezasi_odendi)
        self.assertIsNotNone(loan.gecikme_odeme_tarihi)

    def test_close_iptal(self):
        loan = self._checkout()
        resp = self._close(loan.id, {"durum": "iptal"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        loan.refresh_from_db()
        self.nusha.refresh_from_db()
        self.assertEqual(loan.durum, "iptal")
        self.assertIsNone(loan.teslim_tarihi)
        self.assertEqual(self.nusha.durum, "mevcut")

    def test_double_close_rejected(self):
        loan = self._checkout()
        self._close(loan.id, {"durum": "teslim", "teslim_tarihi": timezone.now().isoformat()})
        resp = self._close(loan.id, {"durum": "kayip", "teslim_tarihi": timezone.now().isoformat()})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        loan.refresh_from_db()
        self.assertEqual(loan.durum, "teslim")

    def test_gecikmis_can_close(self):
        loan = self._checkout()
        OduncKaydi.objects.filter(id=loan.id).update(durum="gecikmis")
        resp = self._close(loan.id, {"durum": "teslim", "teslim_tarihi": timezone.now().isoformat()})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_odendi_requires_ceza(self):
        loan = self._checkout()
        resp = self._close(loan.id, {
            "durum": "teslim",
            "teslim_tarihi": timezone.now().isoformat(),
            "gecikme_cezasi_odendi": True,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_loan_durum_blocked(self):
        loan = self._checkout()
        resp = self.client.patch(f"/api/oduncler/{loan.id}/", {"durum": "teslim"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.durum, "oduncte")

    def test_patch_nusha_durum_blocked(self):
        self._checkout()
        resp = self.client.patch(f"/api/nushalar/{self.nusha.id}/", {"durum": "kayip"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.nusha.refresh_from_db()
        self.assertEqual(self.nusha.durum, "oduncte")


class OgrenciDurumAPITests(APITestCase):
    """POST /api/ogrenciler/{id}/durum/ — aktif/pasif, yalnızca admin."""

    def setUp(self):
        make_policy()
        self.admin_user = User.objects.create_user(username="admin2", password="a2!")
        Personel.objects.create(
            ad_soyad="Yönetici", kullanici_adi="admin2", rol="admin", user=self.admin_user
        )
        self.personel_user = User.objects.create_user(username="person2", password="p2!")
        Personel.objects.create(
            ad_soyad="Personel", kullanici_adi="person2", rol="personel", user=self.personel_user
        )
        self.sinif = Sinif.objects.create(ad="6-C")
        self.rol = Rol.objects.create(ad="Öğrenci")
        self.ogrenci = Ogrenci.objects.create(
            ad="Ayşe", soyad="Can", ogrenci_no="60125", sinif=self.sinif, rol=self.rol
        )

    def test_non_admin_forbidden(self):
        self.client.force_authenticate(self.personel_user)
        resp = self.client.post(f"/api/ogrenciler/{self.ogrenci.id}/durum/", {"aktif": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_forbidden(self):
        resp = self.client.post(f"/api/ogrenciler/{self.ogrenci.id}/durum/", {"aktif": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_pasif_sets_date_and_active_clears(self):
        self.client.force_authenticate(self.admin_user)
        resp = self.client.post(f"/api/ogrenciler/{self.ogrenci.id}/durum/", {"aktif": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.ogrenci.refresh_from_db()
        self.assertFalse(self.ogrenci.aktif)
        self.assertIsNotNone(self.ogrenci.pasif_tarihi)
        resp = self.client.post(f"/api/ogrenciler/{self.ogrenci.id}/durum/", {"aktif": True}, format="json")
        self.ogrenci.refresh_from_db()
        self.assertTrue(self.ogrenci.aktif)
        self.assertIsNone(self.ogrenci.pasif_tarihi)

    def test_admin_pasif_warns_active_loans(self):
        self.client.force_authenticate(self.admin_user)
        kitap, nusha = make_book_and_copy(barkod="KIT0000766")
        resp = self.client.post(
            "/api/checkout/", {"ogrenci_no": "60125", "barkod": nusha.barkod}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        resp = self.client.post(f"/api/ogrenciler/{self.ogrenci.id}/durum/", {"aktif": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        warnings = resp.data.get("warnings", [])
        self.assertTrue(any("aktif ödüncü var" in w for w in warnings))

class OgrenciCRUDAPITests(APITestCase):
    """Faz B: öğrenci oluşturma/düzenleme herkese, silme admin'e; aktif/pasif PATCH'e kapalı."""

    def setUp(self):
        self.admin_user = User.objects.create_user(username="admin", password="a1!", is_staff=True)
        self.personel_user = User.objects.create_user(username="person", password="p1!")
        self.client.force_authenticate(self.personel_user)

    def test_personel_can_create_student(self):
        resp = self.client.post(
            "/api/ogrenciler/",
            {"ad": "Yeni", "soyad": "Öğrenci", "ogrenci_no": "998877"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertTrue(resp.data["aktif"])
        self.assertIsNone(resp.data["pasif_tarihi"])

    def test_create_duplicate_no_rejected(self):
        self.client.post(
            "/api/ogrenciler/",
            {"ad": "İlk", "soyad": "Öğrenci", "ogrenci_no": "998877"},
            format="json",
        )
        resp = self.client.post(
            "/api/ogrenciler/",
            {"ad": "İkinci", "soyad": "Öğrenci", "ogrenci_no": "998877"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_personel_can_edit_profile_fields(self):
        ogrenci = Ogrenci.objects.create(ad="Eski", soyad="Ad", ogrenci_no="998877")
        resp = self.client.patch(
            f"/api/ogrenciler/{ogrenci.id}/",
            {"ad": "Yeni", "telefon": "0555 111 22 33"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["ad"], "Yeni")

    def test_patch_aktif_locked_read_only(self):
        ogrenci = Ogrenci.objects.create(ad="A", soyad="B", ogrenci_no="998877")
        resp = self.client.patch(f"/api/ogrenciler/{ogrenci.id}/", {"aktif": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ogrenci.refresh_from_db()
        self.assertTrue(ogrenci.aktif)

    def test_personel_cannot_delete(self):
        ogrenci = Ogrenci.objects.create(ad="A", soyad="B", ogrenci_no="998877")
        resp = self.client.delete(f"/api/ogrenciler/{ogrenci.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Ogrenci.objects.filter(pk=ogrenci.pk).exists())

    def test_admin_can_delete_if_no_history(self):
        self.client.force_authenticate(self.admin_user)
        ogrenci = Ogrenci.objects.create(ad="A", soyad="B", ogrenci_no="998877")
        resp = self.client.delete(f"/api/ogrenciler/{ogrenci.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ogrenci.objects.filter(pk=ogrenci.pk).exists())

    def test_admin_cannot_delete_student_with_history(self):
        self.client.force_authenticate(self.admin_user)
        ogrenci = Ogrenci.objects.create(ad="A", soyad="B", ogrenci_no="60126")
        kitap, nusha = make_book_and_copy(barkod="KIT0000777")
        resp = self.client.post(
            "/api/checkout/", {"ogrenci_no": "60126", "barkod": nusha.barkod}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        resp = self.client.delete(f"/api/ogrenciler/{ogrenci.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertTrue(Ogrenci.objects.filter(pk=ogrenci.pk).exists())
        _ = kitap


class KatalogAPITests(APITestCase):
    """Faz C: katalog CRUD (admin), raf modeli, nüsha durum düzeltme (K4.8),
    birleştirme (K6.2), çift kitap (K6.1), kitap/nüsha silme kuralları."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="a1!", is_staff=True)
        self.personel = User.objects.create_user(username="person", password="p1!")
        self.client.force_authenticate(self.personel)

    def test_personel_create_yazar_ok_update_forbidden(self):
        # K6.6 (revize): yazar ekleme kitap girişi için tüm personel; düzenle/sil admin.
        resp = self.client.post("/api/yazarlar/", {"ad_soyad": "Yeni"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        yazar_id = resp.data["id"]
        resp = self.client.patch(
            f"/api/yazarlar/{yazar_id}/", {"ad_soyad": "Değişti"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            f"/api/yazarlar/{yazar_id}/", {"ad_soyad": "Değişti"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_katalog_fold_duplicate_blocked(self):
        # K6.1: %100 aynı (fold) kayıt eklenemez; farklı ad serbest.
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            "/api/yazarlar/", {"ad_soyad": "Sabahattin Ali"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        resp = self.client.post(
            "/api/yazarlar/", {"ad_soyad": "sabahattin ali"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        resp = self.client.post(
            "/api/kategoriler/", {"ad": "Roman"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        resp = self.client.post(
            "/api/kategoriler/", {"ad": "roman"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        resp = self.client.post(
            "/api/yazarlar/", {"ad_soyad": "Orhan Kemal"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

    def test_raf_crud(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post("/api/raflar/", {"ad": "A2"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        rid = resp.data["id"]
        resp = self.client.patch(f"/api/raflar/{rid}/", {"aciklama": "Yazarlar A"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # raf listesi herkese açık
        self.client.force_authenticate(self.personel)
        resp = self.client.get("/api/raflar/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_nusha_create_via_api(self):
        kitap, _ = make_book_and_copy(barkod="KIT0000705")
        resp = self.client.post("/api/nushalar/", {"kitap_id": kitap.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertTrue(resp.data["barkod"].startswith("KIT"))

    def test_durum_duzelt_admin_only(self):
        kitap, nusha = make_book_and_copy(barkod="KIT0000706")
        resp = self.client.post(
            f"/api/nushalar/{nusha.id}/durum_duzelt/", {"durum": "kayip"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/nushalar/{nusha.id}/durum_duzelt/", {"durum": "kayip"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        nusha.refresh_from_db()
        self.assertEqual(nusha.durum, "kayip")
        # mevcut'a geri dön
        resp = self.client.post(
            f"/api/nushalar/{nusha.id}/durum_duzelt/", {"durum": "mevcut"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_durum_duzelt_oduncte_rejected(self):
        self.client.force_authenticate(self.admin)
        ogrenci = Ogrenci.objects.create(ad="A", soyad="B", ogrenci_no="60127")
        kitap, nusha = make_book_and_copy(barkod="KIT0000707")
        resp = self.client.post(
            "/api/checkout/", {"ogrenci_no": "60127", "barkod": "KIT0000707"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        resp = self.client.post(
            f"/api/nushalar/{nusha.id}/durum_duzelt/", {"durum": "mevcut"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("ödünçte", resp.data["error"])

    def test_duzelt_oduncte_target_rejected(self):
        self.client.force_authenticate(self.admin)
        kitap, nusha = make_book_and_copy(barkod="KIT0000708")
        resp = self.client.post(
            f"/api/nushalar/{nusha.id}/durum_duzelt/", {"durum": "oduncte"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kitap_cift_listesi(self):
        kitap1, _ = make_book_and_copy(baslik="Suç ve Ceza", barkod="KIT0000710")
        kitap2, _ = make_book_and_copy(baslik="suç ve ceza", barkod="KIT0000711")
        resp = self.client.get("/api/kitaplar/cift/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        keys = [r["anahtar"] for r in resp.data]
        self.assertTrue(any("suc ve ceza" == k for k in keys))
        _ = (kitap1, kitap2)

    def test_kitap_destroy_admin_personel_forbidden(self):
        kitap, _ = make_book_and_copy(barkod="KIT0000712")
        resp = self.client.delete(f"/api/kitaplar/{kitap.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        resp = self.client.delete(f"/api/kitaplar/{kitap.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_kitap_destroy_with_history_blocked(self):
        self.client.force_authenticate(self.admin)
        ogrenci = Ogrenci.objects.create(ad="A", soyad="B", ogrenci_no="60128")
        kitap, nusha = make_book_and_copy(barkod="KIT0000713")
        resp = self.client.post(
            "/api/checkout/", {"ogrenci_no": "60128", "barkod": "KIT0000713"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        resp = self.client.delete(f"/api/kitaplar/{kitap.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        resp = self.client.delete(f"/api/nushalar/{nusha.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kitap_create_duplicate_isbn_conflict(self):
        existing, _ = make_book_and_copy(
            baslik="Devlet-i Aliyye", barkod="KIT0000715"
        )
        existing.isbn = "978-975-08-1522-1"
        existing.save(update_fields=["isbn", "arama"])
        resp = self.client.post(
            "/api/kitaplar/",
            {"baslik": "Devlet-i Aliyye (ciltli)", "isbn": "9789750815221"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT, resp.content)
        self.assertTrue(resp.data["isbn_eslesme"])
        self.assertEqual(resp.data["benzerler"][0]["id"], existing.id)
        self.assertEqual(resp.data["benzerler"][0]["nusha_sayisi"], 1)

    def test_kitap_create_duplicate_isbn_force_ok(self):
        existing, _ = make_book_and_copy(
            baslik="Devlet-i Aliyye", barkod="KIT0000716"
        )
        existing.isbn = "978-975-08-1522-1"
        existing.save(update_fields=["isbn", "arama"])
        resp = self.client.post(
            "/api/kitaplar/",
            {"baslik": "Devlet-i Aliyye (ciltli)", "isbn": "9789750815221", "force": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertNotEqual(resp.data["id"], existing.id)

    def test_kitap_create_duplicate_title_conflict(self):
        existing, _ = make_book_and_copy(baslik="Suç ve Ceza", barkod="KIT0000717")
        resp = self.client.post(
            "/api/kitaplar/", {"baslik": "suç ve ceza"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT, resp.content)
        self.assertFalse(resp.data["isbn_eslesme"])
        self.assertEqual(resp.data["benzerler"][0]["id"], existing.id)

    def test_kitap_create_distinct_no_conflict(self):
        make_book_and_copy(baslik="Suç ve Ceza", barkod="KIT0000718")
        resp = self.client.post(
            "/api/kitaplar/", {"baslik": "Sefiller"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

    def test_yazar_birles(self):
        self.client.force_authenticate(self.admin)
        y1 = Yazar.objects.create(ad_soyad="Orhan Pamuk")
        y2 = Yazar.objects.create(ad_soyad="orpamuk")
        k1 = Kitap.objects.create(baslik="Kitap X", yazar=y1)
        resp = self.client.post(f"/api/yazarlar/{y1.id}/birles/", {"hedef_id": y2.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        k1.refresh_from_db()
        self.assertEqual(k1.yazar_id, y2.id)
        self.assertFalse(Yazar.objects.filter(pk=y1.pk).exists())

    def test_raf_birles(self):
        self.client.force_authenticate(self.admin)
        r1 = Raf.objects.create(ad="A1")
        r2 = Raf.objects.create(ad="A-1")
        kitap, nusha = make_book_and_copy(barkod="KIT0000714")
        nusha.raf = r1
        nusha.save()
        resp = self.client.post(f"/api/raflar/{r1.id}/birles/", {"hedef_id": r2.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        nusha.refresh_from_db()
        self.assertEqual(nusha.raf_id, r2.id)
        self.assertEqual(nusha.raf_kodu, "A-1")

    def test_google_books_endpoint(self):
        import unittest.mock as mock

        cache.clear()

        google_payload = {
            "items": [
                {
                    "volumeInfo": {
                        "title": "Sineklerin Tanrısı",
                        "authors": ["William Golding"],
                        "publishedDate": "1954",
                        "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9781234"}],
                        "description": "Klasik roman",
                        "imageLinks": {"thumbnail": "http://x/c.jpg?zoom=1"},
                    }
                }
            ]
        }

        def _route(req, **kwargs):
            if "googleapis.com" in req.full_url:
                return _FakeResp(google_payload)
            return _FakeResp({"docs": []})

        with mock.patch("kutuphane_app.book_lookup.urlopen", side_effect=_route):
            resp = self.client.post("/api/kitap-google/", {"q": "sineklerin tanrisi"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        first = resp.data["results"][0]
        self.assertEqual(first["baslik"], "Sineklerin Tanrısı")
        self.assertEqual(first["isbn"], "9781234")
        self.assertIn("zoom=2", first["kapak_url"])
        self.assertEqual(first["kaynak"], "google")

    def test_google_books_isbn_endpoint(self):
        import unittest.mock as mock

        cache.clear()

        def _route(req, **kwargs):
            if "googleapis.com" in req.full_url:
                return _FakeResp({"items": [{"volumeInfo": {
                    "title": "Daginik Zihinler",
                    "authors": ["Gabor Mate"],
                    "industryIdentifiers": [{"type": "ISBN_10", "identifier": "6051924736"}],
                }}]})
            return _FakeResp({"docs": []})

        with mock.patch("kutuphane_app.book_lookup.urlopen", side_effect=_route):
            resp = self.client.post(
                "/api/kitap-google/",
                {"q": "", "isbn": "978-605-192-473-1"},
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["results"][0]["baslik"], "Daginik Zihinler")

    def test_google_books_rete_limit_429(self):
        import unittest.mock as mock
        from io import BytesIO
        from urllib.error import HTTPError

        cache.clear()

        def _boom(req, **kwargs):
            raise HTTPError(req.full_url, 429, "Too Many Requests", {}, BytesIO(b""))

        with mock.patch("kutuphane_app.book_lookup.urlopen", side_effect=_boom):
            resp = self.client.post("/api/kitap-google/", {"q": "arnold"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS, resp.content)
        self.assertIn("429", resp.data["error"])


class BookLookupTests(TestCase):
    """K7.1/K7.5: çok kaynaklı arama, ISBN önceliği, önbellek, 429 davranışı."""

    def setUp(self):
        cache.clear()

    def _fake_http(self, routes, record):
        """`routes`: (url_parçası, payload) listesi; eşleşmeyen boş sözlük döner."""
        from unittest import mock

        def _capture(req, **kwargs):
            url = req.full_url
            record["urls"].append(url)
            for needle, payload in routes:
                if needle in url:
                    return _FakeResp(payload)
            return _FakeResp({})

        return mock.patch("kutuphane_app.book_lookup.urlopen", side_effect=_capture)

    def _record(self):
        return {"urls": []}

    def _google_urls(self, record):
        return [u for u in record["urls"] if "googleapis.com" in u]

    def test_normalize_and_detect_isbn(self):
        self.assertEqual(normalize_isbn("978-605-192-473-1"), "9786051924731")
        self.assertTrue(looks_like_isbn("978-605-192-473-1"))
        self.assertFalse(looks_like_isbn("Dağınık Zihinler"))

    def test_google_url_has_key_country_and_results(self):
        payload = {"items": [{"volumeInfo": {"title": "Kurtuluş Savaşı"}}]}
        record = self._record()
        with override_settings(GOOGLE_BOOKS_API_KEY="AIza_TEST_KEY"):
            with self._fake_http(
                [("googleapis.com", payload), ("openlibrary.org", {"docs": []})], record
            ):
                results, err = lookup_books("kurtulus savasi")
        self.assertIsNone(err)
        self.assertEqual(results[0]["baslik"], "Kurtuluş Savaşı")
        gurl = self._google_urls(record)[0]
        self.assertIn("key=AIza_TEST_KEY", gurl)
        self.assertIn("country=TR", gurl)

    def test_no_key_when_unset(self):
        record = self._record()
        with override_settings(GOOGLE_BOOKS_API_KEY=""):
            with self._fake_http(
                [("googleapis.com", {"items": []}), ("openlibrary.org", {"docs": []})], record
            ):
                _, err = lookup_books("deneme")
        self.assertEqual(err, "not_found")
        self.assertTrue(all("key=" not in u for u in self._google_urls(record)))

    def test_isbn_search_uses_isbn_prefix_and_ol_endpoint(self):
        record = self._record()
        google = {"items": [{"volumeInfo": {
            "title": "Daginik Zihinler",
            "industryIdentifiers": [{"type": "ISBN_10", "identifier": "6051924736"}],
        }}]}
        with self._fake_http(
            [("googleapis.com", google), ("openlibrary.org", {"docs": []})], record
        ):
            results, err = lookup_books(isbn="978-605-192-473-1")
        self.assertIsNone(err)
        self.assertEqual(results[0]["baslik"], "Daginik Zihinler")
        gurl = self._google_urls(record)[0]
        self.assertIn("9786051924731", gurl)
        self.assertIn("isbn", gurl)
        self.assertTrue(any("/isbn/9786051924731.json" in u for u in record["urls"]))

    def test_isbn_autodetected_from_q(self):
        record = self._record()
        with self._fake_http(
            [("googleapis.com", {"items": []}), ("openlibrary.org", {"docs": []})], record
        ):
            _, err = lookup_books("9786051924731")
        self.assertEqual(err, "not_found")
        self.assertIn("9786051924731", self._google_urls(record)[0])

    def test_merge_dedupes_and_takes_ol_cover(self):
        record = self._record()
        google = {"items": [{"volumeInfo": {
            "title": "Tutunamayanlar",
            "authors": ["Oğuz Atay"],
            "industryIdentifiers": [{"type": "ISBN_10", "identifier": "9754700117"}],
        }}]}
        ol_edition = {
            "title": "Tutunamayanlar",
            "by_statement": "Oguz Atay.",
            "covers": [8730101],
            "isbn_13": ["9789754700114"],
            "isbn_10": ["9754700117"],
        }
        with self._fake_http(
            [("googleapis.com", google), ("openlibrary.org", ol_edition)], record
        ):
            results, err = lookup_books(isbn="9754700117")
        self.assertIsNone(err)
        self.assertEqual(len(results), 1)
        self.assertIn("covers.openlibrary.org/b/id/8730101", results[0]["kapak_url"])
        self.assertEqual(results[0]["yazar"], "Oğuz Atay")

    def test_cache_hit_no_network(self):
        record = self._record()
        payload = {"items": [{"volumeInfo": {"title": "Devlet-i Aliyye"}}]}
        with self._fake_http(
            [("googleapis.com", payload), ("openlibrary.org", {"docs": []})], record
        ):
            r1, e1 = lookup_books("İlber Ortaylı")
            after_first = len(record["urls"])
            r2, e2 = lookup_books("İLBER ORTAYLI")
        self.assertEqual(len(record["urls"]), after_first)
        self.assertIsNone(e1)
        self.assertIsNone(e2)
        self.assertEqual(r1, r2)

    def test_empty_result_cached(self):
        record = self._record()
        with self._fake_http(
            [("googleapis.com", {"items": []}), ("openlibrary.org", {"docs": []})], record
        ):
            _, e1 = lookup_books("olmayan-kitap-xyz")
            after_first = len(record["urls"])
            _, e2 = lookup_books("olmayan-kitap-xyz")
        self.assertEqual(e1, "not_found")
        self.assertEqual(e2, "not_found")
        self.assertEqual(len(record["urls"]), after_first)

    def test_429_not_cached(self):
        import unittest.mock as mock
        from io import BytesIO
        from urllib.error import HTTPError

        def _boom(req, **kwargs):
            raise HTTPError(req.full_url, 429, "Too Many Requests", {}, BytesIO(b""))

        with mock.patch("kutuphane_app.book_lookup.urlopen", side_effect=_boom) as m:
            _, e1 = lookup_books("arnold")
            _, e2 = lookup_books("arnold")
        self.assertEqual(e1, "429")
        self.assertEqual(e2, "429")
        self.assertEqual(m.call_count, 4)

    def test_open_library_404_not_error_when_google_has_result(self):
        import unittest.mock as mock
        from io import BytesIO
        from urllib.error import HTTPError

        google = {"items": [{"volumeInfo": {"title": "Daginik Zihinler"}}]}

        def _route(req, **kwargs):
            if "googleapis.com" in req.full_url:
                return _FakeResp(google)
            raise HTTPError(req.full_url, 404, "Not Found", {}, BytesIO(b""))

        with mock.patch("kutuphane_app.book_lookup.urlopen", side_effect=_route):
            results, err = lookup_books(isbn="9786051924731")
        self.assertIsNone(err)
        self.assertEqual(results[0]["baslik"], "Daginik Zihinler")


class BorrowerAccountTests(APITestCase):
    """K9: borçlu (öğrenci/öğretmen) hesabı, token tipi, kapsam ve şifre akışı."""

    def setUp(self):
        self.sinif = Sinif.objects.create(ad="9-A")
        self.rol = Rol.objects.create(ad="Öğrenci")
        self.ogrenci = Ogrenci.objects.create(
            ad="Ali", soyad="Veli", ogrenci_no="9001",
            sinif=self.sinif, rol=self.rol,
        )
        self.diger = Ogrenci.objects.create(
            ad="Ayşe", soyad="Yılmaz", ogrenci_no="9002",
            sinif=self.sinif, rol=self.rol,
        )
        self.admin = User.objects.create_user(
            username="admin", password="a1!", is_staff=True
        )

    def _set_password(self, ogrenci, sifre):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            f"/api/ogrenciler/{ogrenci.id}/", {"sifre": sifre}, format="json"
        )
        self.client.force_authenticate(None)
        return resp

    def _login(self, username, password):
        return self.client.post(
            "/api/token/", {"username": username, "password": password}, format="json"
        )

    def test_superuser_token_is_admin(self):
        # K9: Personel kaydı olmayan superuser/staff admin sayılır.
        resp = self._login("admin", "a1!")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["tip"], "personel")
        self.assertEqual(resp.data["role"], "admin")

    def test_borrower_login_and_scope(self):
        resp = self._set_password(self.ogrenci, "ilk1234")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        login = self._login("9001", "ilk1234")
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.content)
        self.assertEqual(login.data["tip"], "ogrenci")
        self.assertEqual(login.data["role"], "Öğrenci")
        self.assertEqual(login.data["ogrenci_no"], "9001")
        self.assertTrue(login.data["parola_degistirilsin"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        # Personel uçları kapalı
        self.assertEqual(
            self.client.get("/api/ogrenciler/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get("/api/oduncler/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post("/api/kitaplar/", {"baslik": "X"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        # Kitap gezintisi açık
        self.assertEqual(self.client.get("/api/kitaplar/").status_code, status.HTTP_200_OK)
        # Kendi geçmişi açık; başkasınınki boş/dışlanmış
        self.assertEqual(
            self.client.get("/api/student-history/9001/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.get("/api/student-history/9002/").data, [])
        self.assertEqual(
            self.client.get("/api/student-penalties/9002/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_borrower_change_password_clears_flag(self):
        self._set_password(self.ogrenci, "ilk1234")
        login = self._login("9001", "ilk1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        resp = self.client.post(
            "/api/change-password/",
            {
                "current_password": "ilk1234",
                "new_password": "Guvenli!234",
                "new_password_confirm": "Guvenli!234",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.ogrenci.refresh_from_db()
        self.assertFalse(self.ogrenci.parola_degistirilsin)
        relogin = self._login("9001", "Guvenli!234")
        self.assertEqual(relogin.status_code, status.HTTP_200_OK, relogin.content)
        self.assertFalse(relogin.data["parola_degistirilsin"])
