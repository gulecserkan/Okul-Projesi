from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer as BaseTokenObtainPairSerializer,
    TokenRefreshSerializer as BaseTokenRefreshSerializer,
)

from .models import (
    Uye,
    Sinif,
    Rol,
    Yazar,
    Kategori,
    Raf,
    Kitap,
    KitapNusha,
    OduncKaydi,
    LoanPolicy,
    RoleLoanPolicy,
    NotificationSettings,
    AuditLog,
    InventorySession,
    InventoryItem,
)


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = "__all__"


class SinifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sinif
        fields = "__all__"


class UyeSerializer(serializers.ModelSerializer):
    sinif = SinifSerializer(read_only=True)
    sinif_id = serializers.PrimaryKeyRelatedField(
        source="sinif", queryset=Sinif.objects.all(), write_only=True, required=False, allow_null=True
    )
    rol_id = serializers.PrimaryKeyRelatedField(
        source="rol", queryset=Rol.objects.all(), write_only=True, required=False, allow_null=True
    )
    # K9: personel, üye (öğrenci/öğretmen) için başlangıç/yeni şifre belirler.
    sifre = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # K9: mevcut bir User hesabına bağlama (ör. personel/öğretmen kendini üye yapar).
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Uye
        exclude = ("arama", "user")
        extra_kwargs = {
            # K2.6: aktif/pasif değişimi yalnızca durum action (admin); düz PATCH kilili.
            "aktif": {"read_only": True},
            "pasif_tarihi": {"read_only": True},
            # Personel/editör için numara zorunlu değil (öğrencide doğrulama).
            "uye_no": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        rol = attrs.get("rol", getattr(self.instance, "rol", None))
        uye_no = attrs.get("uye_no", getattr(self.instance, "uye_no", None))
        if rol is not None and rol.ad == "Öğrenci" and not uye_no:
            raise serializers.ValidationError(
                {"uye_no": "Öğrenci için numara zorunludur."}
            )
        return attrs

    def create(self, validated_data):
        sifre = (validated_data.pop("sifre", "") or "").strip()
        uye = super().create(validated_data)
        if sifre:
            self._set_borrower_password(uye, sifre)
        return uye

    def update(self, instance, validated_data):
        sifre = (validated_data.pop("sifre", "") or "").strip()
        uye = super().update(instance, validated_data)
        if sifre:
            self._set_borrower_password(uye, sifre)
        return uye

    def _set_borrower_password(self, uye, raw_password):
        """Üye girişi: kullanıcı adı = uye_no; ilk girişte değiştirme zorunlu."""
        user = uye.user
        if user is None:
            user, _ = User.objects.get_or_create(username=uye.uye_no)
        user.set_password(raw_password)
        user.is_staff = False
        user.save()
        uye.user = user
        uye.parola_degistirilsin = True
        uye.save(update_fields=["user", "parola_degistirilsin"])


class YazarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Yazar
        fields = "__all__"

    def validate_ad_soyad(self, value):
        # K6.1: fold-normalize edilmiş birebir kopya eklenemez.
        from .rules import fold_duplicate

        qs = Yazar.objects.all()
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        existing = fold_duplicate(qs, value, field="ad_soyad")
        if existing is not None:
            raise serializers.ValidationError(f'"{existing}" zaten kayıtlı.')
        return value


class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kategori
        fields = "__all__"

    def validate_ad(self, value):
        from .rules import fold_duplicate

        qs = Kategori.objects.all()
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        existing = fold_duplicate(qs, value, field="ad")
        if existing is not None:
            raise serializers.ValidationError(f'"{existing}" zaten kayıtlı.')
        return value


class RafSerializer(serializers.ModelSerializer):
    class Meta:
        model = Raf
        fields = "__all__"

    def validate_ad(self, value):
        from .rules import fold_duplicate

        qs = Raf.objects.all()
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        existing = fold_duplicate(qs, value, field="ad")
        if existing is not None:
            raise serializers.ValidationError(f'"{existing}" zaten kayıtlı.')
        return value


class KitapBaseSerializer(serializers.ModelSerializer):
    kategori = KategoriSerializer(read_only=True)
    yazar = YazarSerializer(read_only=True)
    yazar_id = serializers.PrimaryKeyRelatedField(
        source="yazar", queryset=Yazar.objects.all(), write_only=True, required=False, allow_null=True
    )
    kategori_id = serializers.PrimaryKeyRelatedField(
        source="kategori", queryset=Kategori.objects.all(), write_only=True, required=False, allow_null=True
    )
    nusha_sayisi = serializers.IntegerField(read_only=True)
    image_count = serializers.IntegerField(read_only=True)
    aciklama_var = serializers.BooleanField(read_only=True)
    raf_kodlari = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Kitap
        fields = [
            "id",
            "baslik",
            "yayin_yili",
            "isbn",
            "aciklama",
            "kapak_url",
            "yazar",
            "kategori",
            "yazar_id",
            "kategori_id",
            "nusha_sayisi",
            "image_count",
            "aciklama_var",
            "raf_kodlari",
        ]
        extra_kwargs = {
            "baslik": {"required": True},
            "kapak_url": {"required": False, "allow_blank": True},
        }


class KitapSerializer(KitapBaseSerializer):
    """Listelemeler için özet serializer (resimsiz)."""

    pass


class KitapDetailSerializer(KitapBaseSerializer):
    class Meta(KitapBaseSerializer.Meta):
        fields = KitapBaseSerializer.Meta.fields + [
            "resim1",
            "resim2",
            "resim3",
            "resim4",
            "resim5",
        ]


class KitapNushaSerializer(serializers.ModelSerializer):
    kitap = KitapSerializer(read_only=True)
    kitap_id = serializers.PrimaryKeyRelatedField(
        source="kitap", queryset=Kitap.objects.all(), write_only=True
    )
    barkod = serializers.CharField(required=False, allow_blank=True)
    raf = RafSerializer(read_only=True)
    raf_id = serializers.PrimaryKeyRelatedField(
        source="raf", queryset=Raf.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = KitapNusha
        fields = ["id", "kitap", "kitap_id", "barkod", "durum", "raf_kodu", "raf", "raf_id"]

    def get_fields(self):
        fields = super().get_fields()
        # K4.1: nüsha durumu yalnızca checkout/kapat (ve admin düzeltme) ile değişir.
        fields["durum"].read_only = True
        return fields

    def create(self, validated_data):
        barkod = validated_data.get("barkod")
        if barkod:
            return super().create(validated_data)

        from django.db import IntegrityError, transaction
        from django.db.models import Func, IntegerField, Max, Value
        from django.db.models.functions import Cast

        prefix = "KIT"
        pattern = rf"^{prefix}\d+$"
        strip_expr = Func("barkod", Value(prefix), Value(""), function="regexp_replace")

        def _next_number():
            value = (
                KitapNusha.objects.filter(barkod__regex=pattern)
                .annotate(n=Cast(strip_expr, output_field=IntegerField()))
                .aggregate(m=Max("n"))["m"]
            )
            return (value or 0) + 1

        for _attempt in range(10):
            candidate = f"{prefix}{_next_number():06d}"
            try:
                with transaction.atomic():
                    payload = dict(validated_data)
                    payload["barkod"] = candidate
                    return super().create(payload)
            except IntegrityError:
                continue

        raise serializers.ValidationError(
            {"barkod": "Benzersiz barkod üretilemedi. Lütfen tekrar deneyin."}
        )


class OduncKaydiSerializer(serializers.ModelSerializer):
    uye = UyeSerializer(read_only=True)
    kitap_nusha = KitapNushaSerializer(read_only=True)

    class Meta:
        model = OduncKaydi
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        # K3.7: durum geçişleri yalnızca kapat endpoint'i üzerinden yapılır.
        for name in (
            "durum",
            "teslim_tarihi",
            "gecikme_cezasi",
            "gecikme_cezasi_odendi",
            "gecikme_odeme_tarihi",
            "gecikme_odeme_tutari",
        ):
            fields[name].read_only = True
        return fields


class LoanPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanPolicy
        exclude = ("singleton_key",)


class RoleLoanPolicySerializer(serializers.ModelSerializer):
    role_id = serializers.IntegerField(source="role.id", read_only=True)
    role_name = serializers.CharField(source="role.ad", read_only=True)

    class Meta:
        model = RoleLoanPolicy
        fields = (
            "role_id",
            "role_name",
            "duration",
            "max_items",
            "delay_grace_days",
            "penalty_delay_days",
            "shift_weekend",
            "penalty_max_per_loan",
            "penalty_max_per_student",
            "daily_penalty_rate",
        )


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        exclude = (
            "singleton_key",
            "created_at",
            "updated_at",
            "overdue_last_run",
            "email_schedule_last_run",
            "sms_schedule_last_run",
            "mobile_schedule_last_run",
        )


class InventoryItemSerializer(serializers.ModelSerializer):
    seen_by_name = serializers.CharField(source="seen_by.get_full_name", read_only=True)
    kitap_nusha_id = serializers.IntegerField(source="kitap_nusha.id", read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "session",
            "kitap_nusha",
            "kitap_nusha_id",
            "barkod",
            "kitap_baslik",
            "raf_kodu",
            "durum",
            "seen",
            "seen_at",
            "seen_by",
            "seen_by_name",
            "note",
        ]
        read_only_fields = (
            "session",
            "kitap_nusha",
            "kitap_nusha_id",
            "barkod",
            "kitap_baslik",
            "raf_kodu",
            "durum",
            "seen_at",
            "seen_by",
            "seen_by_name",
        )


class InventorySessionSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = InventorySession
        fields = [
            "id",
            "name",
            "description",
            "status",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
            "total_items",
            "seen_items",
            "progress",
            "filters",
            "created_by",
            "created_by_name",
        ]
        read_only_fields = (
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
            "total_items",
            "seen_items",
            "progress",
            "created_by",
            "created_by_name",
        )

    def get_progress(self, obj):
        if not obj or not obj.total_items:
            return 0.0
        try:
            return round(min(1.0, obj.seen_items / float(obj.total_items)), 4)
        except Exception:
            return 0.0


class AuditLogSerializer(serializers.ModelSerializer):
    kullanici_adi = serializers.CharField(source="kullanici.username", read_only=True)
    ad_soyad = serializers.CharField(source="kullanici.get_full_name", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "kullanici",
            "kullanici_adi",
            "ad_soyad",
            "islem",
            "detay",
            "ip_adresi",
            "olusturma_zamani",
        )
        read_only_fields = ("id", "kullanici_adi", "ad_soyad", "olusturma_zamani")
        extra_kwargs = {
            "kullanici": {"required": False, "allow_null": True},
            "detay": {"required": False, "allow_blank": True},
            "ip_adresi": {"required": False, "allow_null": True},
        }

    def validate_islem(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("İşlem açıklaması zorunludur.")
        return str(value).strip()

    def validate_detay(self, value):
        return str(value).strip() if value is not None else ""


class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    @classmethod
    def _claims(cls, user):
        """K9: hesap tipi + rol.

        - `is_superuser` → tip=personel, role=admin
        - `Uye` bağlı → tip=uye, role=Uye.rol.ad (editör ise 'editor')
        - aksi halde → tip=personel, role=personel (operatör)
        """
        uye = getattr(user, "uye", None)
        claims = {}
        if user.is_superuser:
            claims["tip"] = "personel"
            claims["full_name"] = user.get_full_name() or user.username
            claims["role"] = "admin"
        elif uye is not None:
            claims["tip"] = "uye"
            claims["full_name"] = f"{uye.ad} {uye.soyad}".strip()
            rol_ad = uye.rol.ad if uye.rol else "Öğrenci"
            claims["role"] = "editor" if rol_ad == "Editör" else rol_ad
        else:
            claims["tip"] = "personel"
            claims["full_name"] = user.get_full_name() or user.username
            claims["role"] = "personel"
        if uye is not None:
            claims["uye_id"] = uye.id
            claims["uye_no"] = uye.uye_no
            claims["parola_degistirilsin"] = bool(uye.parola_degistirilsin)
        else:
            claims["parola_degistirilsin"] = False
        return claims

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        for key, value in cls._claims(user).items():
            token[key] = value
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        token = self.get_token(self.user)
        for key in ("full_name", "role", "tip", "uye_id", "uye_no", "parola_degistirilsin"):
            if key in token:
                data[key] = token[key]
        return data


class TokenRefreshSerializer(BaseTokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.token_class(attrs["refresh"])
        for key in ("full_name", "role", "tip", "uye_id", "uye_no", "parola_degistirilsin"):
            if key in refresh:
                data[key] = refresh[key]
        return data
