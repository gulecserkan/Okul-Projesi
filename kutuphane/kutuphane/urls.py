from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework import routers
from kutuphane_app.admin import admin_site
from kutuphane_app.views import (
    IstatistikViewSet,
    RolViewSet,
    SinifViewSet,
    UyeViewSet,
    YazarViewSet,
    KategoriViewSet,
    KitapViewSet,
    KitapNushaViewSet,
    RafViewSet,
    GoogleBooksView,
    OduncKaydiViewSet,
    OduncKapatView,
    FastQueryView,
    BookHistoryView,
    UyeGecmisView,
    UyeCezaView,
    CheckoutView,
    HealthCheckView,
    MobilSurumView,
    MasaustuSurumView,
    ChangePasswordView,
    BookCatalogView,
    BookDetailPublicView,
    LoanPolicyView,
    RoleLoanPolicyView,
    NotificationSettingsView,
    KurumAyarlariView,
    PenaltyPaymentView,
    UpdateOverdueLoansView,
    AuditLogView,
    InventorySessionViewSet,
    ShelfCodeListView,
)

from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from kutuphane_app.serializers import TokenObtainPairSerializer, TokenRefreshSerializer


class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
    throttle_scope = "login"


class TokenRefreshView(BaseTokenRefreshView):
    serializer_class = TokenRefreshSerializer
    throttle_scope = "login"

router = routers.DefaultRouter()
router.register(r'roller', RolViewSet)
router.register(r'siniflar', SinifViewSet)
router.register(r'uyeler', UyeViewSet)
router.register(r'yazarlar', YazarViewSet)
router.register(r'kategoriler', KategoriViewSet)
router.register(r'raflar', RafViewSet)
router.register(r'kitaplar', KitapViewSet)
router.register(r'nushalar', KitapNushaViewSet)
router.register(r'oduncler', OduncKaydiViewSet)
router.register(r'istatistik', IstatistikViewSet, basename="istatistik")
router.register(r'inventory-sessions', InventorySessionViewSet, basename="inventory-session")

urlpatterns = [
    #path('admin/', admin.site.urls),
    path('admin/', admin_site.urls),
    path('api/', include(router.urls)),
    path('api/fast-query/', FastQueryView.as_view(), name="fast-query"),
    path('api/kitap-google/', GoogleBooksView.as_view(), name="kitap-google"),
    path('api/book-history/<str:barkod>/', BookHistoryView.as_view(), name="book-history"),
    path('api/uye-gecmis/<str:uye_no>/', UyeGecmisView.as_view(), name="uye-gecmis"),
    path('api/uye-ceza/<str:uye_no>/', UyeCezaView.as_view(), name="uye-ceza"),
    path('api/health/', HealthCheckView.as_view(), name="health"),
    path('api/mobil/surum/', MobilSurumView.as_view(), name="mobil-surum"),
    path('api/masaustu/surum/', MasaustuSurumView.as_view(), name="masaustu-surum"),
    path('api/checkout/', CheckoutView.as_view(), name="checkout"),
    path('api/oduncler/<int:pk>/kapat/', OduncKapatView.as_view(), name="loan-close"),
    path('api/raf-kodlari/', ShelfCodeListView.as_view(), name="shelf-codes"),
    path('api/change-password/', ChangePasswordView.as_view(), name="change-password"),
    path('api/settings/loans/', LoanPolicyView.as_view(), name="loan-policy-settings"),
    path('api/settings/loans/roles/', RoleLoanPolicyView.as_view(), name="role-loan-policy-settings"),
    path('api/settings/notifications/', NotificationSettingsView.as_view(), name="notification-settings"),
    path('api/settings/kurum/', KurumAyarlariView.as_view(), name="kurum-settings"),
    path('api/penalties/<int:pk>/pay/', PenaltyPaymentView.as_view(), name="penalty-pay"),
    path('api/jobs/update-overdue/', UpdateOverdueLoansView.as_view(), name="update-overdue-loans"),
    path('api/logs/', AuditLogView.as_view(), name="audit-log"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("kitap/<int:pk>/", BookDetailPublicView.as_view(), name="kitap-detay"),
    path("", BookCatalogView.as_view(), name="katalog"),
]

if settings.DEBUG==True:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
