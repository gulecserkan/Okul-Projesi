from django.utils.crypto import get_random_string
from django.core.files.storage import default_storage
from django.conf import settings
import os, json, io, datetime

from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.utils.timezone import now
from django.db import transaction
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponse
from django.core import management
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django import forms
from django.contrib.auth.hashers import make_password

from import_export.admin import ImportExportModelAdmin

from .resources import OgrenciResource
from .models import (
    Rol, Sinif, Ogrenci, Yazar, Kategori, Kitap, KitapNusha,
    OduncKaydi, Personel, AuditLog,
    ArsivBatch, ArsivOgrenci, ArsivOdunc,
    LoanPolicy, RoleLoanPolicy, NotificationSettings,
    InventorySession, InventoryItem
)

# --- Custom Admin Site ---
class CustomAdminSite(admin.AdminSite):
    site_header = "Kütüphane Yönetim Sistemi"
    site_title = "Kütüphane Admin"
    index_title = "Kontrol Paneli"

    restore_code = None

    def system_restore_view(self, request):
        backups_dir = settings.BASE_DIR / "backups"
        backups_dir.mkdir(exist_ok=True)

        if request.method == "GET":
            backup_files = sorted(os.listdir(backups_dir), reverse=True)
            self.restore_code = get_random_string(6).upper()
            return render(request, "admin/system_restore_form.html", {
                "code": self.restore_code,
                "backup_files": backup_files,
            })

        elif request.method == "POST":
            confirm = request.POST.get("confirm", "")
            code = request.POST.get("code", "")
            file = request.FILES.get("json_file")
            selected_file = request.POST.get("selected_file")

            if confirm != "EVET":
                return HttpResponse("Hata: 'EVET' yazmanız gerekiyor.", status=400)
            if code != self.restore_code:
                return HttpResponse("Hata: Güvenlik kodu yanlış.", status=400)

            if file:
                path = default_storage.save("restore.json", file)
            elif selected_file:
                path = backups_dir / selected_file
                if not path.exists():
                    return HttpResponse("Hata: Seçilen yedek bulunamadı.", status=400)
            else:
                return HttpResponse("Hata: Dosya seçilmedi.", status=400)

            management.call_command("flush", "--noinput")
            full_path = os.path.join(settings.MEDIA_ROOT, path)  # gerçek tam yol
            management.call_command("loaddata", full_path)
            return HttpResponse("✅ Restore işlemi tamamlandı.")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("system/ayarlar/", self.admin_view(self.system_settings_view), name="system-settings"),
            path("system/backup/", self.admin_view(self.system_backup_view), name="system-backup"),
            path("system/restore/", self.admin_view(self.system_restore_view), name="system-restore"),
        ]
        return custom_urls + urls

    def system_settings_view(self, request):
        return render(request, "admin/system_settings.html")

    def system_backup_view(self, request):
        backups_dir = settings.BASE_DIR / "backups"
        backups_dir.mkdir(exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.json"
        filepath = backups_dir / filename

        buffer = io.StringIO()
        management.call_command("dumpdata", stdout=buffer, indent=2)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(buffer.getvalue())

        response = HttpResponse(buffer.getvalue(), content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


admin_site = CustomAdminSite(name="custom_admin")

# --- Inline ---
class KitapNushaInline(admin.TabularInline):
    model = KitapNusha
    extra = 1

# --- Model Admin’leri ---
class SinifAdmin(admin.ModelAdmin):
    list_display = ("ad",)
    search_fields = ("ad",)
admin_site.register(Sinif, SinifAdmin)

class RolAdmin(admin.ModelAdmin):
    list_display = ("ad", "get_duration", "get_max_items", "get_daily_penalty")
    search_fields = ("ad",)

    def _policy(self, obj):
        return getattr(obj, "loan_policy", None)

    def get_duration(self, obj):
        policy = self._policy(obj)
        return getattr(policy, "duration", None)

    get_duration.short_description = "Süre"

    def get_max_items(self, obj):
        policy = self._policy(obj)
        return getattr(policy, "max_items", None)

    get_max_items.short_description = "Maks. Kitap"

    def get_daily_penalty(self, obj):
        policy = self._policy(obj)
        value = getattr(policy, "daily_penalty_rate", None)
        if value is None:
            return "0.00"
        return f"{value:.2f}"

    get_daily_penalty.short_description = "Günlük Ceza"
admin_site.register(Rol, RolAdmin)

class YazarAdmin(admin.ModelAdmin):
    list_display = ("ad_soyad",)
    search_fields = ("ad_soyad",)
admin_site.register(Yazar, YazarAdmin)

class KategoriAdmin(admin.ModelAdmin):
    list_display = ("ad",)
    search_fields = ("ad",)
admin_site.register(Kategori, KategoriAdmin)

class KitapAdmin(admin.ModelAdmin):
    list_display = ("baslik", "yazar", "kategori", "yayin_yili", "isbn")
    search_fields = ("baslik", "isbn", "yazar__ad_soyad")
    list_filter = ("kategori", "yayin_yili")
    inlines = [KitapNushaInline]
admin_site.register(Kitap, KitapAdmin)

class KitapNushaAdmin(admin.ModelAdmin):
    list_display = ("kitap", "barkod", "durum", "raf_kodu")
    search_fields = ("barkod", "kitap__baslik")
    list_filter = ("durum",)
admin_site.register(KitapNusha, KitapNushaAdmin)

class OduncKaydiAdmin(admin.ModelAdmin):
    list_display = ("ogrenci", "kitap_nusha", "odunc_tarihi", "iade_tarihi", "teslim_tarihi", "durum", "gecikme_cezasi")
    list_filter = ("durum", "ogrenci__sinif", "ogrenci__rol")
    search_fields = ("ogrenci__ad", "ogrenci__soyad", "kitap_nusha__barkod", "kitap_nusha__kitap__baslik")
    date_hierarchy = "odunc_tarihi"
    raw_id_fields = ("ogrenci", "kitap_nusha")
admin_site.register(OduncKaydi, OduncKaydiAdmin)

class PersonelAdminForm(forms.ModelForm):
    password = forms.CharField(
        label="Yeni şifre",
        widget=forms.PasswordInput,
        required=False,
        help_text="Şifreyi değiştirmek isterseniz doldurun."
    )
    password_confirm = forms.CharField(
        label="Yeni şifre (tekrar)",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = Personel
        fields = ("ad_soyad", "kullanici_adi", "rol")

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        pw_confirm = cleaned.get("password_confirm")
        if pw or pw_confirm:
            if pw != pw_confirm:
                raise forms.ValidationError("Yeni şifre alanları uyuşmuyor.")
            if not pw:
                raise forms.ValidationError("Şifre boş olamaz.")
        return cleaned


class PersonelAdmin(admin.ModelAdmin):
    form = PersonelAdminForm
    list_display = ("ad_soyad", "kullanici_adi", "rol")
    search_fields = ("ad_soyad", "kullanici_adi")
    list_filter = ("rol",)

    def save_model(self, request, obj, form, change):
        raw_password = form.cleaned_data.get("password")

        # Kullanıcı kaydı yoksa oluştur
        if not obj.user:
            user = User.objects.create_user(
                username=obj.kullanici_adi,
                password=raw_password or User.objects.make_random_password(),
                first_name=obj.ad_soyad,
                is_staff=True,
            )
            obj.user = user
        else:
            obj.user.username = obj.kullanici_adi
            obj.user.first_name = obj.ad_soyad
            if raw_password:
                obj.user.set_password(raw_password)
            obj.user.save()

        if raw_password:
            obj.set_password(raw_password)
        elif not change and not obj.sifre_hash:
            # yeni kayıtta şifre verilmemişse rasgele oluştur
            generated = User.objects.make_random_password()
            obj.set_password(generated)
            obj.user.set_password(generated)
            obj.user.save()

        super().save_model(request, obj, form, change)
admin_site.register(Personel, PersonelAdmin)


class InventoryItemInline(admin.TabularInline):
    model = InventoryItem
    extra = 0
    can_delete = False
    fields = ("barkod", "kitap_baslik", "raf_kodu", "durum", "seen", "seen_at", "seen_by", "note")
    readonly_fields = fields
    ordering = ("-seen", "raf_kodu", "barkod")


class InventorySessionAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "total_items", "seen_items", "created_at", "created_by")
    list_filter = ("status", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at", "started_at", "completed_at", "total_items", "seen_items", "filters", "created_by")
    inlines = [InventoryItemInline]


admin_site.register(InventorySession, InventorySessionAdmin)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("olusturma_zamani", "kullanici", "islem", "ip_adresi")
    list_filter = ("islem", "kullanici")
    search_fields = ("islem", "detay", "kullanici__username", "kullanici__first_name", "kullanici__last_name")

# --- Ogrenci + import-export + ARŞİV Özel URL + İşlem ---
class OgrenciAdmin(ImportExportModelAdmin):
    resource_class = OgrenciResource
    list_display = ("ogrenci_no", "ad", "soyad", "sinif", "rol", "aktif", "kayit_tarihi", "pasif_tarihi")
    list_filter = ("sinif", "rol", "aktif")
    search_fields = ("ogrenci_no", "ad", "soyad", "eposta")
    date_hierarchy = "kayit_tarihi"

    # Üstte özel buton göstermek için (şablonda link var)
    change_list_template = "admin/kutuphane_app/ogrenci_change_list.html"

    # Özel URL’ler (önizleme / onay)
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "arsiv_onizleme/",
                self.admin_site.admin_view(self.arsiv_onizleme),
                name="ogrenci-arsiv-onizleme",
            ),
            path(
                "arsiv_onayla/",
                self.admin_site.admin_view(self.arsiv_onayla),
                name="ogrenci-arsiv-onayla",
            ),
        ]
        return custom_urls + urls

    # 3+ yıl pasif (veya pasif_tarihi boş ama 3+ yıl önce kaydedilmiş) adayları göster
    def arsiv_onizleme(self, request):
        uc_yil_once = now().replace(year=now().year - 3)
        adaylar = Ogrenci.objects.filter(
            Q(aktif=False) &
            (Q(pasif_tarihi__lt=uc_yil_once) |
             (Q(pasif_tarihi__isnull=True) & Q(kayit_tarihi__lt=uc_yil_once)))
        )
        return render(request, "admin/ogrenci_arsiv_onizleme.html", {
            "adaylar": adaylar,
            "toplam": adaylar.count(),
        })

    # Adayları arşive taşı + JSON paket üret + canlı DB’den temizle
    def arsiv_onayla(self, request):
        uc_yil_once = now().replace(year=now().year - 3)
        hedef = Ogrenci.objects.filter(
            Q(aktif=False) &
            (Q(pasif_tarihi__lt=uc_yil_once) |
             (Q(pasif_tarihi__isnull=True) & Q(kayit_tarihi__lt=uc_yil_once)))
        )

        if not hedef.exists():
            messages.warning(request, "Arşivlenecek uygun öğrenci yok.")
            return redirect("..")

        with transaction.atomic():
            batch = ArsivBatch.objects.create(aciklama="3+ yıl pasif öğrenciler")

            json_ogrenciler: list[dict] = []
            json_oduncler: list[dict] = []
            nusha_ids, kitap_ids = set(), set()

            # Öğrencileri arşive yaz + JSON’a ekle
            for o in hedef.select_related("sinif", "rol"):
                ArsivOgrenci.objects.create(
                    batch=batch,
                    ogrenci_no=o.ogrenci_no,
                    ad=o.ad,
                    soyad=o.soyad,
                    sinif_ad=o.sinif.ad if o.sinif else None,
                    rol_ad=o.rol.ad if o.rol else None,
                    telefon=o.telefon,
                    eposta=o.eposta,
                    kayit_tarihi=o.kayit_tarihi,
                    pasif_tarihi=o.pasif_tarihi,
                )
                json_ogrenciler.append({
                    "ogrenci_no": o.ogrenci_no,
                    "ad": o.ad,
                    "soyad": o.soyad,
                    "sinif": o.sinif.ad if o.sinif else None,
                    "rol": o.rol.ad if o.rol else None,
                    "telefon": o.telefon,
                    "eposta": o.eposta,
                    "kayit_tarihi": o.kayit_tarihi.isoformat() if o.kayit_tarihi else None,
                    "pasif_tarihi": o.pasif_tarihi.isoformat() if o.pasif_tarihi else None,
                })

            # Öğrencilerin ödünç kayıtlarını topla → arşive yaz + JSON
            oduncler = (OduncKaydi.objects
                        .select_related("kitap_nusha", "kitap_nusha__kitap", "ogrenci")
                        .filter(ogrenci__in=hedef))
            for k in oduncler:
                nusha = k.kitap_nusha
                kitap = nusha.kitap if nusha else None

                ArsivOdunc.objects.create(
                    batch=batch,
                    ogrenci_no=k.ogrenci.ogrenci_no if k.ogrenci else "",
                    kitap_baslik=kitap.baslik if kitap else "",
                    barkod=nusha.barkod if nusha else "",
                    odunc_tarihi=k.odunc_tarihi,
                    iade_tarihi=k.iade_tarihi,
                    teslim_tarihi=k.teslim_tarihi,
                    durum=k.durum,
                    gecikme_cezasi=k.gecikme_cezasi,
                )
                json_oduncler.append({
                    "ogrenci_no": k.ogrenci.ogrenci_no if k.ogrenci else "",
                    "kitap_baslik": kitap.baslik if kitap else "",
                    "barkod": nusha.barkod if nusha else "",
                    "odunc_tarihi": k.odunc_tarihi.isoformat(),
                    "iade_tarihi": k.iade_tarihi.isoformat(),
                    "teslim_tarihi": k.teslim_tarihi.isoformat() if k.teslim_tarihi else None,
                    "durum": k.durum,
                    "gecikme_cezasi": float(k.gecikme_cezasi) if k.gecikme_cezasi is not None else None,
                })

                if nusha: nusha_ids.add(nusha.id)
                if kitap: kitap_ids.add(kitap.id)

            # İlişkili nüsha + kitap snapshot’larını da JSON’a ekleyelim
            nushalar_qs = KitapNusha.objects.select_related("kitap").filter(id__in=nusha_ids)
            json_nushalar = [{
                "barkod": n.barkod,
                "raf_kodu": n.raf_kodu,
                "durum": n.durum,
                "kitap_id": n.kitap_id,
                "kitap_baslik": n.kitap.baslik if n.kitap else None
            } for n in nushalar_qs]

            kitaplar_qs = Kitap.objects.select_related("yazar", "kategori").filter(id__in=kitap_ids)
            json_kitaplar = [{
                "id": k.id,
                "baslik": k.baslik,
                "yazar": k.yazar.ad_soyad if k.yazar else None,
                "kategori": k.kategori.ad if k.kategori else None,
                "yayin_yili": k.yayin_yili,
                "isbn": k.isbn
            } for k in kitaplar_qs]

            # JSON paketi oluştur ve batch’e dosya olarak kaydet
            paket = {
                "batch": {
                    "id": batch.id,
                    "aciklama": batch.aciklama,
                    "olusturma_tarihi": now().isoformat()
                },
                "ogrenciler": json_ogrenciler,
                "oduncler": json_oduncler,
                "nushalar": json_nushalar,
                "kitaplar": json_kitaplar,
            }
            json_bytes = json.dumps(paket, ensure_ascii=False, indent=2).encode("utf-8")
            batch.json_dosya.save(f"arsiv_{batch.id}.json", ContentFile(json_bytes), save=True)

            # Temizlik: önce ödünçler, sonra öğrenciler
            oduncler.delete()
            hedef.delete()

        messages.success(request, f"{len(json_ogrenciler)} öğrenci arşive taşındı.")
        return redirect("..")

# kayıt
admin_site.register(Ogrenci, OgrenciAdmin)


class ArsivBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "aciklama", "olusturma_tarihi", "json_dosya")
    date_hierarchy = "olusturma_tarihi"
    search_fields = ("aciklama",)
admin_site.register(ArsivBatch, ArsivBatchAdmin)

class ArsivOgrenciAdmin(admin.ModelAdmin):
    list_display = ("batch", "ogrenci_no", "ad", "soyad", "sinif_ad", "rol_ad", "pasif_tarihi")
    list_filter = ("batch", "rol_ad", "sinif_ad")
    search_fields = ("ogrenci_no", "ad", "soyad")
admin_site.register(ArsivOgrenci, ArsivOgrenciAdmin)

class ArsivOduncAdmin(admin.ModelAdmin):
    list_display = ("batch", "ogrenci_no", "kitap_baslik", "barkod", "odunc_tarihi", "iade_tarihi", "teslim_tarihi", "durum")
    list_filter = ("batch", "durum")
    date_hierarchy = "odunc_tarihi"
    search_fields = ("ogrenci_no", "kitap_baslik", "barkod")
admin_site.register(ArsivOdunc, ArsivOduncAdmin)


class LoanPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "default_duration",
        "default_max_items",
        "delay_grace_days",
        "penalty_delay_days",
        "shift_weekend",
    )


admin_site.register(LoanPolicy, LoanPolicyAdmin)


class RoleLoanPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "duration",
        "max_items",
        "delay_grace_days",
        "penalty_delay_days",
        "daily_penalty_rate",
    )


admin_site.register(RoleLoanPolicy, RoleLoanPolicyAdmin)


class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "printer_warning_enabled",
        "due_reminder_enabled",
        "due_overdue_enabled",
        "email_enabled",
        "sms_enabled",
        "mobile_enabled",
    )


admin_site.register(NotificationSettings, NotificationSettingsAdmin)


admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)
