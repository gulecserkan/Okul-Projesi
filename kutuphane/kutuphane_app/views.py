from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db import transaction
from django.db.models import Count, Sum, Avg, Q, F
from django.shortcuts import get_object_or_404
from datetime import timedelta
from decimal import Decimal, InvalidOperation
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
    RoleLoanPolicy,
    NotificationSettings,
    AuditLog,
    InventorySession,
    InventoryItem,
)
from .serializers import (
    OgrenciSerializer,
    SinifSerializer,
    RolSerializer,
    YazarSerializer,
    KategoriSerializer,
    KitapSerializer,
    KitapDetailSerializer,
    KitapNushaSerializer,
    OduncKaydiSerializer,
    PersonelSerializer,
    LoanPolicySerializer,
    RoleLoanPolicySerializer,
    NotificationSettingsSerializer,
    AuditLogSerializer,
    InventorySessionSerializer,
    InventoryItemSerializer,
)
from .loan_policy import (
    calculate_penalty,
    compute_assigned_due,
    compute_effective_due,
    compute_overdue_days,
    daily_penalty_rate_for_role,
    duration_for_role,
    grace_days_for_role,
    get_snapshot,
    max_items_for_role,
    is_role_blocked,
    penalty_delay_for_role,
    penalty_max_per_loan_for_role,
    penalty_max_per_student_for_role,
    shift_weekend_for_role,
    LoanPolicySnapshot,
)
from .jobs import update_overdue_loans


def serialize_book_payload(kitap, request=None):
    if not kitap:
        return None

    def abs_url(field):
        if not field:
            return None
        url = field.url if hasattr(field, "url") else str(field)
        if request is not None and url and not url.startswith("http"):
            return request.build_absolute_uri(url)
        return url

    return {
        "id": kitap.id,
        "baslik": kitap.baslik,
        "yazar": kitap.yazar.ad_soyad if kitap.yazar else None,
        "kategori": kitap.kategori.ad if kitap.kategori else None,
        "isbn": kitap.isbn,
        "aciklama": kitap.aciklama,
        "resim1": abs_url(getattr(kitap, "resim1", None)),
        "resim2": abs_url(getattr(kitap, "resim2", None)),
        "resim3": abs_url(getattr(kitap, "resim3", None)),
        "resim4": abs_url(getattr(kitap, "resim4", None)),
        "resim5": abs_url(getattr(kitap, "resim5", None)),
    }


def _decimal_to_str(value):
    if value in (None, "", 0):
        return "0.00"
    try:
        quantized = Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return "0.00"
    return format(quantized, "f")


def _client_ip_from_request(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def penalty_summary_for_student(ogrenci, limit=None):
    if not ogrenci:
        return {
            "outstanding_total": "0.00",
            "outstanding_count": 0,
            "entries": [],
            "has_more": False,
        }

    qs = (
        OduncKaydi.objects
        .filter(
            ogrenci=ogrenci,
            gecikme_cezasi__gt=0,
            gecikme_cezasi_odendi=False,
            teslim_tarihi__isnull=False,
        )
        .select_related("kitap_nusha__kitap")
        .order_by("-teslim_tarihi", "-iade_tarihi", "-odunc_tarihi")
    )

    total = qs.aggregate(total=Sum("gecikme_cezasi")).get("total") or Decimal("0")
    total_count = qs.count()

    limited_qs = qs
    if limit is not None:
        limited_qs = qs[:limit]

    entries = []
    for loan in limited_qs:
        copy = getattr(loan, "kitap_nusha", None)
        book = getattr(copy, "kitap", None) if copy else None
        entries.append({
            "id": loan.id,
            "kitap": getattr(book, "baslik", "") or "",
            "barkod": getattr(copy, "barkod", "") or "",
            "durum": loan.durum,
            "odunc_tarihi": loan.odunc_tarihi.isoformat() if loan.odunc_tarihi else None,
            "iade_tarihi": loan.iade_tarihi.isoformat() if loan.iade_tarihi else None,
            "teslim_tarihi": loan.teslim_tarihi.isoformat() if loan.teslim_tarihi else None,
            "gecikme_cezasi": _decimal_to_str(loan.gecikme_cezasi),
            "gecikme_cezasi_odendi": loan.gecikme_cezasi_odendi,
            "gecikme_odeme_tarihi": loan.gecikme_odeme_tarihi.isoformat() if loan.gecikme_odeme_tarihi else None,
        })

    has_more = bool(limit is not None and total_count > len(entries))

    return {
        "outstanding_total": _decimal_to_str(total),
        "outstanding_count": total_count,
        "entries": entries,
        "has_more": has_more,
    }

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

    def get_serializer_class(self):
        if self.action in ("list",):
            return KitapSerializer
        return KitapDetailSerializer

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
    permission_classes = [IsAuthenticated]


class InventorySessionViewSet(viewsets.ModelViewSet):
    queryset = InventorySession.objects.all().select_related("created_by")
    serializer_class = InventorySessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        action = getattr(self, "action", None)
        # Listeleme dışında (ör. /items/ aksiyonunda) status parametresi
        # oturumları filtreleyip 404 üretmesin.
        if action in (None, "list"):
            status_param = self.request.query_params.get("status")
            if status_param:
                statuses = [part.strip() for part in status_param.split(",") if part.strip()]
                if statuses:
                    qs = qs.filter(status__in=statuses)
        return qs

    def perform_create(self, serializer):
        filters = serializer.validated_data.get("filters") or {}
        copies = list(self._filter_copies(filters))
        if not copies:
            raise DRFValidationError({"detail": "Belirtilen filtrelere uyan nüsha bulunamadı."})
        user = self.request.user if getattr(self.request, "user", None) and self.request.user.is_authenticated else None
        with transaction.atomic():
            session = serializer.save(
                created_by=user,
                filters=filters,
                status="active",
                total_items=len(copies),
                seen_items=0,
            )
            batch = [
                InventoryItem(
                    session=session,
                    kitap_nusha=copy,
                    barkod=copy.barkod,
                    kitap_baslik=copy.kitap.baslik if copy.kitap else "",
                    raf_kodu=copy.raf_kodu,
                    durum=copy.durum,
                )
                for copy in copies
            ]
            InventoryItem.objects.bulk_create(batch, batch_size=500)

    def _filter_copies(self, filters):
        filters = filters or {}
        qs = KitapNusha.objects.select_related("kitap").all()
        raf_query = filters.get("raf_query")
        if raf_query:
            qs = qs.filter(raf_kodu__icontains=raf_query)
        raf_prefix = filters.get("raf_prefix")
        if raf_prefix:
            qs = qs.filter(raf_kodu__startswith=raf_prefix)
        durumlar = filters.get("durumlar")
        if isinstance(durumlar, (list, tuple)):
            qs = qs.filter(durum__in=durumlar)
        kitap_id = filters.get("kitap_id")
        if kitap_id:
            qs = qs.filter(kitap_id=kitap_id)
        kategori_id = filters.get("kategori_id")
        if kategori_id:
            qs = qs.filter(kitap__kategori_id=kategori_id)
        return qs.order_by("raf_kodu", "barkod")

    @action(detail=True, methods=["get"], url_path="items")
    def list_items(self, request, pk=None):
        session = self.get_object()
        status_filter = (request.query_params.get("status") or "unseen").lower()
        qs = session.items.select_related("kitap_nusha", "seen_by")
        if status_filter == "unseen":
            qs = qs.filter(seen=False)
        elif status_filter == "seen":
            qs = qs.filter(seen=True)
        search = request.query_params.get("q")
        if search:
            qs = qs.filter(
                Q(barkod__icontains=search)
                | Q(kitap_baslik__icontains=search)
                | Q(raf_kodu__icontains=search)
            )
        total = qs.count()
        try:
            limit = int(request.query_params.get("limit", 250))
        except (TypeError, ValueError):
            limit = 250
        limit = max(1, min(limit, 1000))
        try:
            offset = int(request.query_params.get("offset", 0))
        except (TypeError, ValueError):
            offset = 0
        offset = max(0, offset)
        items = qs[offset : offset + limit]
        serializer = InventoryItemSerializer(items, many=True)
        return Response(
            {
                "results": serializer.data,
                "count": total,
                "offset": offset,
                "limit": limit,
                "session": InventorySessionSerializer(session).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="mark")
    def mark_item(self, request, pk=None):
        session = self.get_object()
        if session.status != "active":
            return Response({"detail": "Yalnızca aktif sayımlarda değişiklik yapılabilir."}, status=status.HTTP_400_BAD_REQUEST)
        barkod = (request.data.get("barkod") or "").strip()
        item_id = request.data.get("item_id")
        if item_id:
            item = get_object_or_404(session.items.select_related("kitap_nusha"), pk=item_id)
        elif barkod:
            item = get_object_or_404(session.items.select_related("kitap_nusha"), barkod=barkod)
        else:
            return Response({"detail": "Barkod veya item_id alanı zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        seen_flag = request.data.get("seen")
        mark_seen = True if seen_flag is None else bool(seen_flag)
        note = request.data.get("note")

        changed = False
        if mark_seen and not item.seen:
            item.seen = True
            item.seen_at = timezone.now()
            item.seen_by = request.user
            changed = True
        elif not mark_seen and item.seen:
            item.seen = False
            item.seen_at = None
            item.seen_by = None
            changed = True

        if note is not None:
            item.note = note

        item.save(update_fields=["seen", "seen_at", "seen_by", "note"])

        if changed:
            session.seen_items = session.items.filter(seen=True).count()
            session.save(update_fields=["seen_items"])

        return Response(InventoryItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_session(self, request, pk=None):
        session = self.get_object()
        if session.status != "active":
            return Response({"detail": "Bu sayım zaten kapatılmış."}, status=status.HTTP_400_BAD_REQUEST)
        status_value = (request.data.get("status") or "completed").lower()
        if status_value not in {"completed", "canceled"}:
            status_value = "completed"
        session.status = status_value
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "completed_at"])
        return Response(InventorySessionSerializer(session).data)

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
            .annotate(gecikme=Count('odunckaydi', filter=Q(
                odunckaydi__gecikme_cezasi__gt=0,
                odunckaydi__gecikme_cezasi_odendi=False,
            )))
            .order_by('-gecikme')[:limit])
        return Response([{"ogrenci": str(o), "gecikme": o.gecikme} for o in ogrenciler])

    # 10. Toplam ceza miktarı
    @action(detail=False, methods=['get'])
    def toplam_ceza(self, request):
        qs = OduncKaydi.objects.filter(
            gecikme_cezasi__gt=0,
            gecikme_cezasi_odendi=False,
        )
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


class StudentPenaltySummaryView(APIView):
    def get(self, request, ogrenci_no):
        ogrenci = (
            Ogrenci.objects
            .filter(ogrenci_no=ogrenci_no)
            .select_related("sinif", "rol")
            .first()
        )
        if not ogrenci:
            return Response({"detail": "Öğrenci bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        summary = penalty_summary_for_student(ogrenci, limit=None)
        summary.update({
            "student": {
                "id": ogrenci.id,
                "ad": ogrenci.ad,
                "soyad": ogrenci.soyad,
                "ogrenci_no": ogrenci.ogrenci_no,
                "sinif": ogrenci.sinif.ad if ogrenci.sinif else None,
                "rol": ogrenci.rol.ad if ogrenci.rol else None,
            }
        })
        return Response(summary)

class FastQueryView(APIView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response({"error": "No query provided"}, status=status.HTTP_400_BAD_REQUEST)

        policy_instance = LoanPolicy.get_solo()
        policy_snapshot = LoanPolicySnapshot.from_policy(policy_instance)
        policy_data = LoanPolicySerializer(policy_instance).data
        policy_data["role_limits"] = []

        # 1. Barkod kontrolü
        try:
            nusha = KitapNusha.objects.select_related("kitap", "kitap__yazar", "kitap__kategori").get(barkod=q)
            loan = (
                OduncKaydi.objects
                .filter(kitap_nusha=nusha, durum__in=["oduncte", "gecikmis"])
                .select_related("ogrenci")
                .order_by("-odunc_tarihi")
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
                "book": serialize_book_payload(nusha.kitap, request),
                "policy": policy_data,
                "loan": self._serialize_loan(loan, policy_snapshot, include_student=True, include_copy=False) if loan else None,
                "penalty_summary": penalty_summary_for_student(loan.ogrenci, limit=10) if loan else None,
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
                "book": serialize_book_payload(kitap, request),
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
                "policy": {
                    **policy_data,
                    "role": self._serialize_role_policy(policy_snapshot, ogrenci.rol),
                },
                "penalty_summary": penalty_summary_for_student(ogrenci, limit=10),
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

        role = getattr(getattr(loan, "ogrenci", None), "rol", None)

        effective_due = compute_effective_due(loan.iade_tarihi, snapshot, role)
        overdue_days = compute_overdue_days(loan.iade_tarihi, snapshot, role)

        penalty = None
        if overdue_days > 0:
            rate = daily_penalty_rate_for_role(snapshot, role)
            other_total = Decimal("0")
            if rate and rate > 0:
                other_total = (
                    OduncKaydi.objects
                    .filter(
                        ogrenci=loan.ogrenci,
                        gecikme_cezasi__gt=0,
                        gecikme_cezasi_odendi=False,
                    )
                    .exclude(pk=loan.pk)
                    .aggregate(total=Sum("gecikme_cezasi"))
                    .get("total")
                    or Decimal("0")
                )
            penalty = calculate_penalty(
                snapshot,
                role,
                overdue_days,
                penalty_delay_for_role(snapshot, role),
                other_active_penalties=other_total,
                rate=rate,
            )
            if penalty is not None and penalty <= 0:
                penalty = None

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
            "policy": self._serialize_role_policy(snapshot, role),
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

    def _serialize_role_policy(self, snapshot, role):
        penalty_max_loan = penalty_max_per_loan_for_role(snapshot, role)
        penalty_max_student = penalty_max_per_student_for_role(snapshot, role)
        penalty_loan_str = f"{penalty_max_loan:.2f}" if penalty_max_loan is not None else None
        penalty_student_str = f"{penalty_max_student:.2f}" if penalty_max_student is not None else None
        daily_penalty = daily_penalty_rate_for_role(snapshot, role)
        daily_penalty_str = f"{daily_penalty:.2f}" if daily_penalty is not None else None
        blocked = is_role_blocked(snapshot, role)
        return {
            "duration": duration_for_role(role, snapshot),
            "max_items": max_items_for_role(role, snapshot),
            "delay_grace_days": grace_days_for_role(snapshot, role),
            "penalty_delay_days": penalty_delay_for_role(snapshot, role),
            "shift_weekend": shift_weekend_for_role(snapshot, role),
            "penalty_max_per_loan": penalty_loan_str,
            "penalty_max_per_student": penalty_student_str,
            "daily_penalty_rate": daily_penalty_str,
            "loan_blocked": blocked,
        }

    

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

        if is_role_blocked(snapshot, ogrenci.rol):
            return Response({"error": "Bu rol için ödünç işlemi yapılamıyor."}, status=status.HTTP_400_BAD_REQUEST)

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
        else:
            max_allowed = role_limit

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
            iade_tarihi = compute_assigned_due(now(), gun_sayisi, snapshot, ogrenci.rol)

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

        personel = getattr(user, "personel", None)
        if personel is not None:
            personel.sifre_hash = user.password
            personel.save(update_fields=["sifre_hash"])

        return Response({"detail": "Şifre güncellendi."}, status=status.HTTP_200_OK)


class LoanPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        policy = LoanPolicy.get_solo()
        serializer = LoanPolicySerializer(policy)
        data = serializer.data
        data["role_limits"] = []
        return Response(data)

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


class RoleLoanPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        policies = RoleLoanPolicy.objects.select_related("role").all()
        serializer = RoleLoanPolicySerializer(policies, many=True)
        return Response(serializer.data)

    def put(self, request):
        payload = request.data or []
        if not isinstance(payload, list):
            return Response({"detail": "Liste formatında veri bekleniyor."}, status=status.HTTP_400_BAD_REQUEST)

        role_map = {role.id: role for role in Rol.objects.all()}
        seen_ids = set()

        for entry in payload:
            if not isinstance(entry, dict):
                continue
            role_id = entry.get("role") or entry.get("role_id")
            if not role_id or role_id not in role_map:
                continue
            seen_ids.add(role_id)
            defaults = {}

            def _int_val(key):
                value = entry.get(key)
                if value in ("", None):
                    return None
                try:
                    ivalue = int(value)
                except (TypeError, ValueError):
                    return None
                return ivalue if ivalue >= 0 else None

            def _decimal_val(key):
                value = entry.get(key)
                if value in ("", None):
                    return None
                try:
                    dec_value = Decimal(str(value))
                except (InvalidOperation, TypeError, ValueError):
                    return None
                if dec_value < 0:
                    return None
                return dec_value.quantize(Decimal("0.01"))

            defaults["duration"] = _int_val("duration")
            defaults["max_items"] = _int_val("max_items")
            defaults["delay_grace_days"] = _int_val("delay_grace_days")
            defaults["penalty_delay_days"] = _int_val("penalty_delay_days")
            defaults["penalty_max_per_loan"] = _decimal_val("penalty_max_per_loan")
            defaults["penalty_max_per_student"] = _decimal_val("penalty_max_per_student")
            defaults["daily_penalty_rate"] = _decimal_val("daily_penalty_rate")

            shift_val = entry.get("shift_weekend")
            if isinstance(shift_val, bool):
                defaults["shift_weekend"] = shift_val
            elif shift_val in ("true", "True", 1, "1"):
                defaults["shift_weekend"] = True
            elif shift_val in ("false", "False", 0, "0"):
                defaults["shift_weekend"] = False
            else:
                defaults["shift_weekend"] = None

            # temizle: tüm alanlar None ise kaydı sil
            if all(value in (None, "") for value in defaults.values()):
                RoleLoanPolicy.objects.filter(role_id=role_id).delete()
            else:
                RoleLoanPolicy.objects.update_or_create(role_id=role_id, defaults=defaults)

        # İsteğe bağlı: payload'da olmayan rollerin ayarlarını silmeyeceğiz (manuel kontrol)

        policies = RoleLoanPolicy.objects.select_related("role").all()
        serializer = RoleLoanPolicySerializer(policies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings = NotificationSettings.get_solo()
        serializer = NotificationSettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, *, partial):
        settings_obj = NotificationSettings.get_solo()
        serializer = NotificationSettingsSerializer(settings_obj, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuditLogView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        incoming = request.data or {}
        if hasattr(incoming, "dict"):
            incoming = incoming.dict()

        islem = incoming.get("islem") or incoming.get("action")
        detay = incoming.get("detay") or incoming.get("detail") or ""
        ip_adresi = (
            incoming.get("ip_adresi")
            or incoming.get("ipAddress")
            or incoming.get("ip_address")
            or _client_ip_from_request(request)
        )

        serializer = AuditLogSerializer(
            data={
                "islem": islem,
                "detay": detay,
                "ip_adresi": ip_adresi,
            }
        )
        serializer.is_valid(raise_exception=True)
        log = serializer.save(kullanici=request.user if request.user.is_authenticated else None)
        return Response(AuditLogSerializer(log).data, status=status.HTTP_201_CREATED)


class PenaltyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            loan = OduncKaydi.objects.select_related("ogrenci").get(pk=pk)
        except OduncKaydi.DoesNotExist:
            return Response({"error": "Kayıt bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        if loan.gecikme_cezasi is None or loan.gecikme_cezasi <= 0:
            return Response({"error": "Bu kayıt için ödenecek ceza bulunmuyor."}, status=status.HTTP_400_BAD_REQUEST)

        if loan.gecikme_cezasi_odendi:
            return Response({"error": "Ceza zaten ödenmiş."}, status=status.HTTP_400_BAD_REQUEST)

        if loan.teslim_tarihi is None:
            return Response({"error": "Kitap teslim edilmeden ceza tahsil edilemez."}, status=status.HTTP_400_BAD_REQUEST)

        amount = request.data.get("amount")
        try:
            amount_dec = Decimal(str(amount)) if amount is not None else Decimal(loan.gecikme_cezasi)
        except (InvalidOperation, TypeError, ValueError):
            return Response({"error": "Geçersiz tutar."}, status=status.HTTP_400_BAD_REQUEST)

        amount_dec = amount_dec.quantize(Decimal("0.01"))
        expected = Decimal(loan.gecikme_cezasi).quantize(Decimal("0.01"))
        if amount_dec != expected:
            return Response({"error": "Ödeme tutarı ceza tutarıyla uyuşmuyor."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            loan.gecikme_cezasi_odendi = True
            loan.gecikme_odeme_tarihi = timezone.now()
            loan.gecikme_odeme_tutari = amount_dec
            loan.save(update_fields=["gecikme_cezasi_odendi", "gecikme_odeme_tarihi", "gecikme_odeme_tutari"])

        summary = penalty_summary_for_student(loan.ogrenci, limit=10)
        return Response(
            {
                "detail": "Ceza ödemesi kaydedildi.",
                "summary": summary,
                "loan_id": loan.id,
            },
            status=status.HTTP_200_OK,
        )


class UpdateOverdueLoansView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            result = update_overdue_loans()
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if isinstance(result, dict) and "total_penalty" in result:
            try:
                total_penalty = result.get("total_penalty")
                if total_penalty is not None:
                    result["total_penalty"] = format(Decimal(total_penalty), ".2f")
            except Exception:
                result["total_penalty"] = str(result.get("total_penalty"))

        return Response(
            {
                "detail": "Gecikme kayıtları güncellendi.",
                "result": result,
            },
            status=status.HTTP_200_OK,
        )


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
                "book": serialize_book_payload(kitap, request),
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
