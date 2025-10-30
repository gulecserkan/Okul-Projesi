from django.db import models
from datetime import time


# --- Sınıflar ---
class Sinif(models.Model):
    ad = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.ad


# --- Roller (Öğrenci / Öğretmen / Personel gibi) ---
class Rol(models.Model):
    ad = models.CharField(max_length=50, unique=True)  # Öğrenci, Öğretmen vb.
    odunc_suresi_gun = models.IntegerField(default=15)
    maksimum_kitap = models.IntegerField(default=3)
    gecikme_ceza_gunluk = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    def __str__(self):
        return self.ad


# --- Öğrenciler ---
class Ogrenci(models.Model):
    ad = models.CharField(max_length=50)
    soyad = models.CharField(max_length=50)
    ogrenci_no = models.CharField(max_length=20, unique=True)
    sinif = models.ForeignKey('Sinif', on_delete=models.SET_NULL, null=True)
    rol = models.ForeignKey('Rol', on_delete=models.SET_NULL, null=True)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    eposta = models.EmailField(blank=True, null=True)
    kayit_tarihi = models.DateTimeField(auto_now_add=True)
    # 🔹 yeni alanlar:
    aktif = models.BooleanField(default=True)
    pasif_tarihi = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.ad} {self.soyad} ({self.ogrenci_no})"


# 🔹 Arşiv paketini temsil eden üst kayıt
class ArsivBatch(models.Model):
    aciklama = models.CharField(max_length=200, blank=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    json_dosya = models.FileField(upload_to='arsiv/', blank=True, null=True)  # indirilebilir JSON

    def __str__(self):
        return f"Arşiv #{self.id} - {self.olusturma_tarihi:%Y-%m-%d %H:%M}"


# 🔹 Arşivde öğrenci fotoğrafı (snapshot)
class ArsivOgrenci(models.Model):
    batch = models.ForeignKey(ArsivBatch, on_delete=models.CASCADE, related_name='arsiv_ogrenciler')
    ogrenci_no = models.CharField(max_length=20)
    ad = models.CharField(max_length=50)
    soyad = models.CharField(max_length=50)
    sinif_ad = models.CharField(max_length=20, blank=True, null=True)
    rol_ad = models.CharField(max_length=50, blank=True, null=True)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    eposta = models.EmailField(blank=True, null=True)
    kayit_tarihi = models.DateTimeField(blank=True, null=True)
    pasif_tarihi = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.ogrenci_no} - {self.ad} {self.soyad}"


# 🔹 Arşivde ödünç kayıtları (snapshot)
class ArsivOdunc(models.Model):
    batch = models.ForeignKey(ArsivBatch, on_delete=models.CASCADE, related_name='arsiv_oduncler')
    ogrenci_no = models.CharField(max_length=20)
    kitap_baslik = models.CharField(max_length=200)
    barkod = models.CharField(max_length=50)
    odunc_tarihi = models.DateTimeField()
    iade_tarihi = models.DateTimeField()
    teslim_tarihi = models.DateTimeField(blank=True, null=True)
    durum = models.CharField(max_length=20)
    gecikme_cezasi = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.ogrenci_no} - {self.kitap_baslik} ({self.barkod})"


# --- Yazarlar ---
class Yazar(models.Model):
    ad_soyad = models.CharField(max_length=100)

    def __str__(self):
        return self.ad_soyad


# --- Kategoriler ---
class Kategori(models.Model):
    ad = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.ad


# --- Kitaplar (Eser Bilgisi) ---
class Kitap(models.Model):
    baslik = models.CharField(max_length=200)
    yazar = models.ForeignKey(Yazar, on_delete=models.SET_NULL, null=True)
    kategori = models.ForeignKey(Kategori, on_delete=models.SET_NULL, null=True)
    yayin_yili = models.IntegerField(blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.baslik


# --- Kitap Nüshaları (Fiziksel Kopya) ---
class KitapNusha(models.Model):
    kitap = models.ForeignKey(Kitap, on_delete=models.CASCADE, related_name="nushalar")
    barkod = models.CharField(max_length=50, unique=True)
    DURUM_SECENEKLERI = [
        ("mevcut", "Mevcut"),
        ("oduncte", "Ödünçte"),
        ("kayip", "Kayıp"),
        ("hasarli","Hasarlı")
    ]
    durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default="mevcut")
    raf_kodu = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.kitap.baslik} - {self.barkod}"


# --- Ödünç Kayıtları ---
class OduncKaydi(models.Model):
    ogrenci = models.ForeignKey(Ogrenci, on_delete=models.CASCADE)
    kitap_nusha = models.ForeignKey(KitapNusha, on_delete=models.CASCADE)
    odunc_tarihi = models.DateTimeField(auto_now_add=True)
    iade_tarihi = models.DateTimeField()  # beklenen tarih
    teslim_tarihi = models.DateTimeField(blank=True, null=True)
    DURUM_SECENEKLERI = [
        ("oduncte", "Ödünçte"),
        ("teslim", "Teslim Edildi"),
        ("gecikmis","Gecikmiş"),
        ("kayip","Kayıp"),
        ("hasarli","Hasarlı"),
        ("iptal","İptal")
    ]
    durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default="oduncte")
    gecikme_cezasi = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.ogrenci} - {self.kitap_nusha}"


# --- Kütüphane Personeli (opsiyonel) ---
class Personel(models.Model):
    ad_soyad = models.CharField(max_length=100)
    kullanici_adi = models.CharField(max_length=50, unique=True)
    sifre_hash = models.CharField(max_length=128)
    ROL_SECENEKLERI = [
        ("admin", "Admin"),
        ("personel", "Personel"),
    ]
    rol = models.CharField(max_length=20, choices=ROL_SECENEKLERI, default="personel")

    def __str__(self):
        return self.ad_soyad


class LoanPolicy(models.Model):
    """
    Ödünç sürecine ilişkin genel ayarların tutulduğu tekil kayıt.
    Masaüstü ve diğer istemciler aynı kaynaktan beslenir.
    """

    singleton_key = models.CharField(max_length=50, unique=True, default="default")
    default_duration = models.PositiveIntegerField(default=15)
    default_max_items = models.PositiveIntegerField(default=2)
    delay_grace_days = models.PositiveIntegerField(default=0)
    penalty_delay_days = models.PositiveIntegerField(default=0)
    shift_weekend = models.BooleanField(default=False)

    auto_extend_enabled = models.BooleanField(default=False)
    auto_extend_days = models.PositiveIntegerField(default=0)
    auto_extend_limit = models.PositiveIntegerField(default=0)

    quarantine_days = models.PositiveIntegerField(default=0)
    require_damage_note = models.BooleanField(default=False)
    require_shelf_code = models.BooleanField(default=False)

    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default=time(22, 0))
    quiet_hours_end = models.TimeField(default=time(8, 0))

    role_limits = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ödünç Politikası"
        verbose_name_plural = "Ödünç Politikası"

    def __str__(self):
        return "Varsayılan ödünç politikası"

    @classmethod
    def get_solo(cls):
        policy, _ = cls.objects.get_or_create(singleton_key="default")
        return policy
