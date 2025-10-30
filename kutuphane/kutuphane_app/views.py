from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Count, Sum, Avg, Q
from datetime import timedelta
from django.utils.timezone import now, make_aware, is_naive
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    Ogrenci,
    Sinif,
    Rol,
    Yazar,
    Kategori,
    Kitap,
    KitapNusha,
    OduncKaydi,
    Personel,
    LoanPolicy,
)
from .serializers import (
    OgrenciSerializer,
    SinifSerializer,
    RolSerializer,
    YazarSerializer,
    KategoriSerializer,
    KitapSerializer,
    KitapNushaSerializer,
    OduncKaydiSerializer,
    PersonelSerializer,
    LoanPolicySerializer,
)
from .loan_policy import (
    calculate_penalty,
    compute_assigned_due,
    compute_effective_due,
    compute_overdue_days,
    duration_for_role,
    get_snapshot,
    max_items_for_role,
    LoanPolicySnapshot,
)

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    #permission_classes=[IsAuthenticated]

class SinifViewSet(viewsets.ModelViewSet):
    queryset = Sinif.objects.all()
    serializer_class = SinifSerializer

class OgrenciViewSet(viewsets.ModelViewSet):
    queryset = Ogrenci.objects.all()
    serializer_class = OgrenciSerializer

class YazarViewSet(viewsets.ModelViewSet):
    queryset = Yazar.objects.all()
    serializer_class = YazarSerializer

class KategoriViewSet(viewsets.ModelViewSet):
    queryset = Kategori.objects.all()
    serializer_class = KategoriSerializer

class KitapViewSet(viewsets.ModelViewSet):
    queryset = Kitap.objects.all()
    serializer_class = KitapSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        yazar_id = self.request.query_params.get("yazar")
        if yazar_id:
            qs = qs.filter(yazar_id=yazar_id)
        kategori_id = self.request.query_params.get("kategori")
        if kategori_id:
            qs = qs.filter(kategori_id=kategori_id)
        arama = self.request.query_params.get("q")
        if arama:
            qs = qs.filter(baslik__icontains=arama)
        return qs.annotate(nusha_sayisi=Count('nushalar', distinct=True))

class KitapNushaViewSet(viewsets.ModelViewSet):
    queryset = KitapNusha.objects.all()
    serializer_class = KitapNushaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        kitap = self.request.query_params.get('kitap') or self.request.query_params.get('kitap_id')
        if kitap:
            qs = qs.filter(kitap_id=kitap)
        barkod = self.request.query_params.get('barkod')
        if barkod:
            qs = qs.filter(barkod=barkod)
        prefix = self.request.query_params.get('prefix')
        if prefix:
            qs = qs.filter(barkod__startswith=prefix)
        isbn = self.request.query_params.get('kitap__isbn') or self.request.query_params.get('kitap_isbn')
        if isbn:
            qs = qs.filter(kitap__isbn=isbn)
        return qs

class OduncKaydiViewSet(viewsets.ModelViewSet):
    queryset = OduncKaydi.objects.all()
    serializer_class = OduncKaydiSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        durum = self.request.query_params.get("durum")
        if durum:
            qs = qs.filter(durum=durum)
        return qs

class PersonelViewSet(viewsets.ModelViewSet):
    queryset = Personel.objects.all()
    serializer_class = PersonelSerializer

class IstatistikViewSet(viewsets.ViewSet):

    # 1. En çok okuyan öğrenci
    @action(detail=False, methods=['get'])
    def en_cok_okuyan_ogrenci(self, request):
        ay = int(request.query_params.get('ay', 0))
        qs = Ogrenci.objects.annotate(okunan=Count('odunckaydi'))
        if ay > 0:
            baslangic = now() - timedelta(days=30*ay)
            qs = Ogrenci.objects.annotate(
                okunan=Count('odunckaydi', filter=Q(odunckaydi__odunc_tarihi__gte=baslangic))
            )
        ogr = qs.order_by('-okunan').first()
        if ogr:
            return Response({"ogrenci": str(ogr), "okunan_sayi": ogr.okunan})
        return Response({"mesaj": "Veri bulunamadı"})

    # 2. En az okuyan öğrenci
    @action(detail=False, methods=['get'])
    def en_az_okuyan_ogrenci(self, request):
        ogr = Ogrenci.objects.annotate(okunan=Count('odunckaydi')).order_by('okunan').first()
        if ogr:
            return Response({"ogrenci": str(ogr), "okunan_sayi": ogr.okunan})
        return Response({"mesaj": "Veri bulunamadı"})

    # 3. Bir öğrencinin toplam ödünç sayısı
    @action(detail=False, methods=['get'])
    def ogrenci_toplam(self, request):
        ogr_id = request.query_params.get('ogrenci_id')
        toplam = OduncKaydi.objects.filter(ogrenci_id=ogr_id).count()
        return Response({"ogrenci_id": ogr_id, "toplam_odunc": toplam})

    # 4. En çok okuyan sınıf
    @action(detail=False, methods=['get'])
    def en_cok_okuyan_sinif(self, request):
        sinif = Sinif.objects.annotate(
            okunan=Count('ogrenci__odunckaydi')
        ).order_by('-okunan').first()
        if sinif:
            return Response({"sinif": sinif.ad, "okunan_sayi": sinif.okunan})
        return Response({"mesaj": "Veri yok"})

    # 5. Sınıf dağılımı (öğrencilerin ödünç sayısı)
    @action(detail=False, methods=['get'])
    def sinif_dagilimi(self, request):
        sinif_id = request.query_params.get('sinif_id')
        ogrenciler = Ogrenci.objects.filter(sinif_id=sinif_id).annotate(
            okunan=Count('odunckaydi')
        ).values("id", "ad", "soyad", "okunan")
        return Response(list(ogrenciler))

    # 6. En çok okunan kitaplar (ilk 10)
    @action(detail=False, methods=['get'])
    def en_cok_okunan_kitaplar(self, request):
        limit = int(request.query_params.get('limit', 10))
        kitaplar = Kitap.objects.annotate(
            okunma=Count('nushalar__odunckaydi')
        ).order_by('-okunma')[:limit]
        return Response([{"kitap": k.baslik, "okunma": k.okunma} for k in kitaplar])

    # 7. Kategori bazlı okuma dağılımı
    @action(detail=False, methods=['get'])
    def kategori_dagilimi(self, request):
        kategoriler = Kategori.objects.annotate(
            okunma=Count('kitap__nushalar__odunckaydi')
        ).values("ad", "okunma")
        return Response(list(kategoriler))

    # 8. Zaman bazlı ödünç trendi (son X ay)
    @action(detail=False, methods=['get'])
    def odunc_trend(self, request):
        ay = int(request.query_params.get('ay', 6))
        baslangic = now() - timedelta(days=30*ay)
        qs = (OduncKaydi.objects
              .filter(odunc_tarihi__gte=baslangic)
              .extra(select={'ay': "DATE_TRUNC('month', odunc_tarihi)"})
              .values('ay')
              .annotate(sayi=Count('id'))
              .order_by('ay'))
        return Response(list(qs))

    # 9. En çok geciken öğrenciler
    @action(detail=False, methods=['get'])
    def en_cok_geciken(self, request):
        limit = int(request.query_params.get('limit', 5))
        ogrenciler = (Ogrenci.objects
            .annotate(gecikme=Count('odunckaydi', filter=Q(odunckaydi__gecikme_cezasi__gt=0)))
            .order_by('-gecikme')[:limit])
        return Response([{"ogrenci": str(o), "gecikme": o.gecikme} for o in ogrenciler])

    # 10. Toplam ceza miktarı
    @action(detail=False, methods=['get'])
    def toplam_ceza(self, request):
        qs = OduncKaydi.objects.all()
        ay = request.query_params.get('ay')  # örn: ?ay=3
        if ay:
            baslangic = now() - timedelta(days=30*int(ay))
            qs = qs.filter(odunc_tarihi__gte=baslangic)
        toplam = qs.aggregate(ceza=Sum('gecikme_cezasi'))["ceza"] or 0
        return Response({"toplam_ceza": float(toplam)})
    

class StudentHistoryView(ListAPIView):
    serializer_class = OduncKaydiSerializer

    def get_queryset(self):
        ogrenci_no = self.kwargs["ogrenci_no"]
        return (
            OduncKaydi.objects
            .filter(ogrenci__ogrenci_no=ogrenci_no)
            .exclude(durum="iptal")
            .select_related("kitap_nusha__kitap", "ogrenci")
            .order_by("-odunc_tarihi")
        )

class FastQueryView(APIView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response({"error": "No query provided"}, status=status.HTTP_400_BAD_REQUEST)

        policy_instance = LoanPolicy.get_solo()
        policy_snapshot = LoanPolicySnapshot.from_policy(policy_instance)
        policy_data = LoanPolicySerializer(policy_instance).data

        # 1. Barkod kontrolü
        try:
            nusha = KitapNusha.objects.select_related("kitap", "kitap__yazar", "kitap__kategori").get(barkod=q)
            loan = (
                OduncKaydi.objects
                .filter(kitap_nusha=nusha, durum="oduncte")
                .select_related("ogrenci")
                .first()
            )
            history = (
                OduncKaydi.objects
                .filter(kitap_nusha=nusha)
                .exclude(durum__in=["oduncte", "iptal"])
                .select_related("ogrenci")
                .order_by("-odunc_tarihi")[:5]
            )
            return Response({
                "type": "book_copy",
                "copy": {
                    "id": nusha.id,
                    "barkod": nusha.barkod,
                    "durum": nusha.durum,
                    "raf_kodu": nusha.raf_kodu,
                },
                "book": {
                    "id": nusha.kitap.id,
                    "baslik": nusha.kitap.baslik,
                    "yazar": nusha.kitap.yazar.ad_soyad if nusha.kitap.yazar else None,
                    "kategori": nusha.kitap.kategori.ad if nusha.kitap.kategori else None,
                    "isbn": nusha.kitap.isbn,
                },
                "policy": policy_data,
                "loan": self._serialize_loan(loan, policy_snapshot, include_student=True, include_copy=False) if loan else None,
                "history": [
                    self._serialize_loan(h, policy_snapshot, include_student=True, include_copy=False)
                    for h in history
                ]
            })
        except KitapNusha.DoesNotExist:
            pass

        # 2. ISBN kontrolü
        kitap = Kitap.objects.filter(isbn=q).select_related("yazar", "kategori").first()
        if kitap:
            return Response({
                "type": "isbn",
                "exists": True,
                "book": {
                    "id": kitap.id,
                    "baslik": kitap.baslik,
                    "yazar": kitap.yazar.ad_soyad if kitap.yazar else None,
                    "kategori": kitap.kategori.ad if kitap.kategori else None,
                    "isbn": kitap.isbn,
                },
                "copy_summary": self._isbn_copy_summary(kitap),
                "policy": policy_data,
            })
        if len(q) >= 10 and q.replace("-", "").isdigit():
            return Response({"type": "isbn", "exists": False})

        # 3. Öğrenci numarası kontrolü
        ogrenci = Ogrenci.objects.filter(ogrenci_no=q).select_related("sinif", "rol").first()
        if ogrenci:
            aktif_oduncler = (
                OduncKaydi.objects
                .filter(ogrenci=ogrenci, durum__in=["oduncte", "gecikmis"])
                .select_related("kitap_nusha__kitap")
            )
            history = (
                OduncKaydi.objects
                .filter(ogrenci=ogrenci)
                .exclude(durum__in=["oduncte", "iptal"])
                .select_related("kitap_nusha__kitap")
                .order_by("-odunc_tarihi")[:5]
            )
            return Response({
                "type": "student",
                "student": {
                    "id": ogrenci.id,
                    "ad": ogrenci.ad,
                    "soyad": ogrenci.soyad,
                    "no": ogrenci.ogrenci_no,
                    "sinif": ogrenci.sinif.ad if ogrenci.sinif else None,
                    "rol": ogrenci.rol.ad if ogrenci.rol else None,
                    "aktif": ogrenci.aktif,
                    "pasif_tarihi": ogrenci.pasif_tarihi,
                },
                "policy": policy_data,
                "active_loans": [
                    self._serialize_loan(od, policy_snapshot, include_copy=True)
                    for od in aktif_oduncler
                ],
                "history": [
                    self._serialize_loan(h, policy_snapshot, include_copy=True, include_student=False)
                    for h in history
                ]
            })

        # 4. Hiçbir şey bulunmadı
        return Response({"type": "not_found"})

    def _isbn_copy_summary(self, kitap):
        copies_qs = (
            KitapNusha.objects
            .filter(kitap=kitap)
            .order_by("barkod")
            .values("id", "durum", "barkod")
        )

        copies = list(copies_qs)
        total = len(copies)

        active_loan_ids = set(
            OduncKaydi.objects
            .filter(
                kitap_nusha__kitap=kitap,
                durum__in=["oduncte", "gecikmis"],
            )
            .values_list("kitap_nusha_id", flat=True)
        )

        loaned = 0
        available = 0
        for copy in copies:
            copy_id = copy.get("id")
            durum = (copy.get("durum") or "").lower()

            if copy_id in active_loan_ids or durum in {"oduncte", "gecikmis"}:
                loaned += 1
                continue

            if durum in {"kayip", "hasarli"}:
                continue

            available += 1

        first_barcode = next((c.get("barkod") for c in copies if c.get("barkod")), None)

        return {
            "count": total,
            "loaned": loaned,
            "available": available,
            "first_barkod": first_barcode,
        }

    def _serialize_loan(self, loan, snapshot, include_student=False, include_copy=True):
        if loan is None:
            return None

        copy = getattr(loan, "kitap_nusha", None)
        book = getattr(copy, "kitap", None) if copy else None

        effective_due = compute_effective_due(loan.iade_tarihi, snapshot)
        overdue_days = compute_overdue_days(loan.iade_tarihi, snapshot)

        rol = getattr(getattr(loan, "ogrenci", None), "rol", None)
        rate = getattr(rol, "gecikme_ceza_gunluk", None)
        penalty = calculate_penalty(rate, overdue_days, snapshot) if overdue_days > 0 else None

        data = {
            "id": loan.id,
            "odunc_tarihi": loan.odunc_tarihi,
            "iade_tarihi": loan.iade_tarihi,
            "teslim_tarihi": loan.teslim_tarihi,
            "durum": loan.durum,
            "effective_iade_tarihi": effective_due.isoformat() if effective_due else None,
            "overdue_days": overdue_days,
            "is_overdue": overdue_days > 0,
            "penalty_preview": str(penalty) if penalty is not None else None,
        }

        if include_copy and copy:
            data["kitap_nusha"] = {
                "id": copy.id,
                "barkod": copy.barkod,
                "raf_kodu": copy.raf_kodu,
            }
            data.setdefault("kitap", getattr(book, "baslik", None))
            data.setdefault("barkod", getattr(copy, "barkod", None))

            if book:
                data["kitap_nusha"]["kitap"] = {
                    "id": book.id,
                    "baslik": book.baslik,
                    "isbn": book.isbn,
                }

        if include_student and hasattr(loan, "ogrenci") and loan.ogrenci:
            ogr = loan.ogrenci
            data["ogrenci"] = {
                "id": ogr.id,
                "ad": ogr.ad,
                "soyad": ogr.soyad,
                "ogrenci_no": ogr.ogrenci_no,
                "aktif": ogr.aktif,
                "pasif_tarihi": ogr.pasif_tarihi,
            }

        return data

    

class CheckoutView(APIView):
    """
    Bir öğrencinin belirli bir barkoda sahip kitabı ödünç almasını sağlar.
    POST /api/checkout/  -> {"ogrenci_no": "...", "barkod": "..."}
    """
    def post(self, request):
        ogrenci_no = (request.data.get("ogrenci_no") or "").strip()
        barkod = (request.data.get("barkod") or "").strip()

        if not ogrenci_no or not barkod:
            return Response({"error": "ogrenci_no ve barkod gerekli"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ogrenci = Ogrenci.objects.select_related("rol").get(ogrenci_no=ogrenci_no)
        except Ogrenci.DoesNotExist:
            return Response({"error": "Öğrenci bulunamadı"}, status=status.HTTP_404_NOT_FOUND)

        snapshot = get_snapshot()

        aktif_sayi = OduncKaydi.objects.filter(
            ogrenci=ogrenci,
            durum__in=["oduncte", "gecikmis"]
        ).count()

        role_limit = max_items_for_role(ogrenci.rol, snapshot)
        if role_limit is not None and aktif_sayi >= role_limit:
            return Response(
                {"error": f"Öğrencinin aktif ödünç sayısı üst limit olan {role_limit} değerine ulaştı"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            nusha = KitapNusha.objects.select_related("kitap").get(barkod=barkod)
        except KitapNusha.DoesNotExist:
            return Response({"error": "Nüsha bulunamadı"}, status=status.HTTP_404_NOT_FOUND)

        if nusha.durum == "oduncte":
            return Response({"error": "Bu nüsha zaten ödünçte"}, status=status.HTTP_400_BAD_REQUEST)

        aktif_kayit_var = OduncKaydi.objects.filter(
            kitap_nusha=nusha,
            durum__in=["oduncte", "gecikmis"]
        ).exists()
        if aktif_kayit_var:
            return Response({"error": "Bu nüsha aktif ödünç kaydına sahip"}, status=status.HTTP_400_BAD_REQUEST)

        max_allowed = request.data.get("max_allowed")
        if max_allowed:
            try:
                max_allowed = int(max_allowed)
            except (TypeError, ValueError):
                max_allowed = None
            if max_allowed and OduncKaydi.objects.filter(
                ogrenci=ogrenci,
                durum__in=["oduncte", "gecikmis"]
            ).count() >= max_allowed:
                return Response({"error": "Öğrencinin aktif ödünç sayısı limitte"}, status=status.HTTP_400_BAD_REQUEST)

        due_override = request.data.get("iade_tarihi")
        iade_tarihi = None
        if due_override:
            parsed = parse_datetime(due_override)
            if parsed is None:
                return Response({"error": "Geçersiz iade_tarihi formatı"}, status=status.HTTP_400_BAD_REQUEST)
            if is_naive(parsed):
                parsed = make_aware(parsed, timezone.get_current_timezone())
            iade_tarihi = parsed

        if iade_tarihi is None:
            gun_sayisi = duration_for_role(ogrenci.rol, snapshot)
            iade_tarihi = compute_assigned_due(now(), gun_sayisi, snapshot)

        with transaction.atomic():
            odunc = OduncKaydi.objects.create(
                ogrenci=ogrenci,
                kitap_nusha=nusha,
                iade_tarihi=iade_tarihi,
                durum="oduncte"
            )

            if nusha.durum != "oduncte":
                nusha.durum = "oduncte"
                nusha.save(update_fields=["durum"])

        serializer = OduncKaydiSerializer(odunc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HealthCheckView(APIView):
    """Basit sağlık kontrolü: sunucu ve kimlik doğrulama altyapısı çalışıyor mu?"""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        data = {
            "status": "ok",
            "timestamp": now().isoformat(),
        }
        return Response(data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data or {}
        current_password = (data.get("current_password") or "").strip()
        new_password = (data.get("new_password") or "").strip()
        new_password_confirm = (data.get("new_password_confirm") or "").strip()

        if not current_password or not new_password or not new_password_confirm:
            return Response({"detail": "Tüm alanlar zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != new_password_confirm:
            return Response({"detail": "Yeni şifre alanları birbiriyle uyuşmuyor."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({"detail": "Mevcut şifre doğru değil."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({"detail": "Şifre güncellendi."}, status=status.HTTP_200_OK)


class LoanPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        policy = LoanPolicy.get_solo()
        serializer = LoanPolicySerializer(policy)
        return Response(serializer.data)

    def put(self, request):
        return self._update_policy(request, partial=False)

    def patch(self, request):
        return self._update_policy(request, partial=True)

    def _update_policy(self, request, partial):
        policy = LoanPolicy.get_solo()
        serializer = LoanPolicySerializer(policy, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookHistoryView(APIView):
    """
    Belirli bir barkodun geçmişini ve aynı ISBN'e sahip TÜM nüshaların durumlarını döndürür.
    GET /api/book-history/<barkod>/
    """
    def get(self, request, barkod):
        try:
            # 1️⃣ Nüsha bilgisi
            nusha = KitapNusha.objects.select_related("kitap").get(barkod=barkod)
            kitap = nusha.kitap

            # 2️⃣ Bu nüshanın geçmişi
            history_qs = (
                OduncKaydi.objects
                .filter(kitap_nusha=nusha)
                .select_related("ogrenci", "kitap_nusha__kitap")
                .order_by("-odunc_tarihi")
            )

            history_data = []
            for rec in history_qs:
                history_data.append({
                    "ogrenci": {
                        "ad": rec.ogrenci.ad,
                        "soyad": rec.ogrenci.soyad,
                    },
                    "odunc_tarihi": rec.odunc_tarihi,
                    "iade_tarihi": rec.iade_tarihi,
                    "teslim_tarihi": rec.teslim_tarihi,
                    "durum": rec.durum,
                })

            # 3️⃣ Aynı kitaba (ID bazlı) ait TÜM nüshalar (kendisi dahil)
            all_copies_qs = (
                KitapNusha.objects
                .filter(kitap_id=kitap.id)
                .order_by("raf_kodu")
            )

            all_copies = []
            for c in all_copies_qs:
                # o nüshanın en son ödünç kaydı
                last_loan = (
                    OduncKaydi.objects
                    .filter(kitap_nusha=c)
                    .exclude(durum="iptal")
                    .select_related("ogrenci")
                    .order_by("-odunc_tarihi")
                    .first()
                )

                latest_any = (
                    OduncKaydi.objects
                    .filter(kitap_nusha=c)
                    .select_related("ogrenci")
                    .order_by("-odunc_tarihi")
                    .first()
                )
                if latest_any and latest_any.durum == "iptal":
                    last_loan = None

                if last_loan:
                    durum = last_loan.durum
                    son_islem = last_loan.teslim_tarihi or last_loan.iade_tarihi or last_loan.odunc_tarihi
                    ogrenci_ad = f"{last_loan.ogrenci.ad} {last_loan.ogrenci.soyad}"
                else:
                    durum = "kütüphanede"
                    son_islem = None
                    ogrenci_ad = ""

                all_copies.append({
                    "barkod": c.barkod,
                    "raf_kodu": c.raf_kodu,
                    "durum": durum,
                    "son_islem": son_islem,
                    "ogrenci": ogrenci_ad,
                    "aktif": (c.barkod == barkod),  # 🔹 aktif nüsha
                })

            # 🔹 aktif nüsha hep listenin başına gelsin
            all_copies.sort(key=lambda x: not x["aktif"])

            return Response({
                "book": {
                    "baslik": kitap.baslik,
                    "isbn": kitap.isbn,
                },
                "copy": {
                    "barkod": nusha.barkod,
                    "raf_kodu": nusha.raf_kodu,
                },
                "history": history_data,
                "all_copies": all_copies,
            })

        except KitapNusha.DoesNotExist:
            return Response({"error": "Nüsha bulunamadı"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
