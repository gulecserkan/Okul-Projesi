from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework import routers
from kutuphane_app.admin import admin_site
from kutuphane_app.views import (
    IstatistikViewSet,
    RolViewSet,
    SinifViewSet,
    OgrenciViewSet,
    YazarViewSet,
    KategoriViewSet,
    KitapViewSet,
    KitapNushaViewSet,
    OduncKaydiViewSet,
    PersonelViewSet,
    FastQueryView,
    BookHistoryView,
    StudentHistoryView,
    StudentPenaltySummaryView,
    CheckoutView,
    HealthCheckView,
    ChangePasswordView,
    LoanPolicyView,
    RoleLoanPolicyView,
    NotificationSettingsView,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register(r'roller', RolViewSet)
router.register(r'siniflar', SinifViewSet)
router.register(r'ogrenciler', OgrenciViewSet)
router.register(r'yazarlar', YazarViewSet)
router.register(r'kategoriler', KategoriViewSet)
router.register(r'kitaplar', KitapViewSet)
router.register(r'nushalar', KitapNushaViewSet)
router.register(r'oduncler', OduncKaydiViewSet)
router.register(r'personel', PersonelViewSet)
router.register(r'istatistik', IstatistikViewSet, basename="istatistik")

urlpatterns = [
    #path('admin/', admin.site.urls),
    path('admin/', admin_site.urls),
    path('api/', include(router.urls)),
    path('api/fast-query/', FastQueryView.as_view(), name="fast-query"),
    path('api/book-history/<str:barkod>/', BookHistoryView.as_view(), name="book-history"),
    path('api/student-history/<str:ogrenci_no>/', StudentHistoryView.as_view(), name="student-history"),
    path('api/student-penalties/<str:ogrenci_no>/', StudentPenaltySummaryView.as_view(), name="student-penalties"),
    path('api/health/', HealthCheckView.as_view(), name="health"),
    path('api/checkout/', CheckoutView.as_view(), name="checkout"),
    path('api/change-password/', ChangePasswordView.as_view(), name="change-password"),
    path('api/settings/loans/', LoanPolicyView.as_view(), name="loan-policy-settings"),
    path('api/settings/loans/roles/', RoleLoanPolicyView.as_view(), name="role-loan-policy-settings"),
    path('api/settings/notifications/', NotificationSettingsView.as_view(), name="notification-settings"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
]

if settings.DEBUG==True:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
