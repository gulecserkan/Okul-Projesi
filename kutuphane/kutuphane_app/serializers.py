from rest_framework import serializers
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
)

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'

class SinifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sinif
        fields = '__all__'

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
        fields = '__all__'

class YazarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Yazar
        fields = '__all__'

class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kategori
        fields = '__all__'

class KitapBaseSerializer(serializers.ModelSerializer):
    kategori = KategoriSerializer(read_only=True)
    yazar = YazarSerializer(read_only=True)
    yazar_id = serializers.PrimaryKeyRelatedField(
        source='yazar', queryset=Yazar.objects.all(), write_only=True, required=False, allow_null=True
    )
    kategori_id = serializers.PrimaryKeyRelatedField(
        source='kategori', queryset=Kategori.objects.all(), write_only=True, required=False, allow_null=True
    )
    nusha_sayisi = serializers.IntegerField(read_only=True)

    class Meta:
        model = Kitap
        fields = [
            'id',
            'baslik',
            'yayin_yili',
            'isbn',
            'yazar',
            'kategori',
            'yazar_id',
            'kategori_id',
            'nusha_sayisi',
        ]


class KitapSerializer(KitapBaseSerializer):
    """Listelemeler için özet serializer (resimsiz)."""
    pass


class KitapDetailSerializer(KitapBaseSerializer):
    class Meta(KitapBaseSerializer.Meta):
        fields = KitapBaseSerializer.Meta.fields + [
            'aciklama',
            'resim1',
            'resim2',
            'resim3',
            'resim4',
            'resim5',
        ]

class KitapNushaSerializer(serializers.ModelSerializer):
    kitap = KitapSerializer(read_only=True)
    kitap_id = serializers.PrimaryKeyRelatedField(
        source='kitap', queryset=Kitap.objects.all(), write_only=True
    )
    barkod = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = KitapNusha
        fields = ['id', 'kitap', 'kitap_id', 'barkod', 'durum', 'raf_kodu']

    def create(self, validated_data):
        # Otomatik barkod üretimi (KIT000001, KIT000002, ...) 6 hane
        barkod = validated_data.get('barkod')
        if not barkod:
            from .models import KitapNusha
            import re
            prefix = 'KIT'
            max_n = 0
            for code in KitapNusha.objects.filter(barkod__startswith=prefix).values_list('barkod', flat=True):
                m = re.match(r'^%s(\d+)$' % prefix, code or '')
                if m:
                    try:
                        n = int(m.group(1))
                        if n > max_n:
                            max_n = n
                    except Exception:
                        continue
            validated_data['barkod'] = f"{prefix}{max_n+1:06d}"
        return super().create(validated_data)


class OduncKaydiSerializer(serializers.ModelSerializer):
    ogrenci = OgrenciSerializer(read_only=True)
    kitap_nusha = KitapNushaSerializer(read_only=True)

    class Meta:
        model = OduncKaydi
        fields = '__all__'

class PersonelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personel
        fields = '__all__'


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
