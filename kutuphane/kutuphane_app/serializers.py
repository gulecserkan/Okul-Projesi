from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer as BaseTokenObtainPairSerializer,
    TokenRefreshSerializer as BaseTokenRefreshSerializer,
)

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


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = "__all__"


class SinifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sinif
        fields = "__all__"


class OgrenciSerializer(serializers.ModelSerializer):
    sinif = SinifSerializer(read_only=True)
    sinif_id = serializers.PrimaryKeyRelatedField(
        source="sinif", queryset=Sinif.objects.all(), write_only=True, required=False, allow_null=True
    )
    rol_id = serializers.PrimaryKeyRelatedField(
        source="rol", queryset=Rol.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Ogrenci
        fields = "__all__"


class YazarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Yazar
        fields = "__all__"


class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kategori
        fields = "__all__"


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

    class Meta:
        model = Kitap
        fields = [
            "id",
            "baslik",
            "yayin_yili",
            "isbn",
            "yazar",
            "kategori",
            "yazar_id",
            "kategori_id",
            "nusha_sayisi",
        ]


class KitapSerializer(KitapBaseSerializer):
    """Listelemeler için özet serializer (resimsiz)."""

    pass


class KitapDetailSerializer(KitapBaseSerializer):
    class Meta(KitapBaseSerializer.Meta):
        fields = KitapBaseSerializer.Meta.fields + [
            "aciklama",
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

    class Meta:
        model = KitapNusha
        fields = ["id", "kitap", "kitap_id", "barkod", "durum", "raf_kodu"]

    def create(self, validated_data):
        barkod = validated_data.get("barkod")
        if not barkod:
            from .models import KitapNusha
            import re

            prefix = "KIT"
            max_n = 0
            for code in KitapNusha.objects.filter(barkod__startswith=prefix).values_list("barkod", flat=True):
                m = re.match(r"^%s(\d+)$" % prefix, code or "")
                if m:
                    try:
                        n = int(m.group(1))
                        if n > max_n:
                            max_n = n
                    except Exception:
                        continue
            validated_data["barkod"] = f"{prefix}{max_n+1:06d}"
        return super().create(validated_data)


class OduncKaydiSerializer(serializers.ModelSerializer):
    ogrenci = OgrenciSerializer(read_only=True)
    kitap_nusha = KitapNushaSerializer(read_only=True)

    class Meta:
        model = OduncKaydi
        fields = "__all__"


class PersonelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personel
        fields = "__all__"


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
    def get_token(cls, user):
        token = super().get_token(user)
        personel = getattr(user, "personel", None)
        if personel:
            token["full_name"] = personel.ad_soyad
            token["role"] = personel.rol
        else:
            token["full_name"] = user.get_full_name() or user.username
            token["role"] = getattr(user, "role", "")
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        token = self.get_token(self.user)
        data["full_name"] = token.get("full_name")
        data["role"] = token.get("role")
        return data


class TokenRefreshSerializer(BaseTokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.token_class(attrs["refresh"])
        data["full_name"] = refresh.get("full_name")
        data["role"] = refresh.get("role")
        return data
