from django.db import models
from datetime import time
from django.db.models.signals import post_save
from django.dispatch import receiver


# --- Sınıflar ---
class Sinif(models.Model):
    ad = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.ad


# --- Roller (Öğrenci / Öğretmen / Personel gibi) ---
class Rol(models.Model):
    ad = models.CharField(max_length=50, unique=True)  # Öğrenci, Öğretmen vb.

    def __str__(self):
        return self.ad


class RoleLoanPolicy(models.Model):
    role = models.OneToOneField(Rol, on_delete=models.CASCADE, related_name="loan_policy")
    duration = models.PositiveIntegerField(null=True, blank=True)
    max_items = models.PositiveIntegerField(null=True, blank=True)
    delay_grace_days = models.PositiveIntegerField(null=True, blank=True)
    penalty_delay_days = models.PositiveIntegerField(null=True, blank=True)
    shift_weekend = models.BooleanField(null=True, blank=True)
    penalty_max_per_loan = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    penalty_max_per_student = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    daily_penalty_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.role.ad} ödünç ayarları"


@receiver(post_save, sender=Rol)
def ensure_role_policy(sender, instance, created, **kwargs):
    if created:
        RoleLoanPolicy.objects.get_or_create(role=instance)


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
    aciklama = models.TextField(blank=True)
    resim1 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim2 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim3 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim4 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim5 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)

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

    penalty_max_per_loan = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    penalty_max_per_student = models.DecimalField(max_digits=8, decimal_places=2, default=0)

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


class NotificationSettings(models.Model):
    singleton_key = models.CharField(max_length=50, unique=True, default="default")

    printer_warning_enabled = models.BooleanField(default=True)

    due_reminder_enabled = models.BooleanField(default=True)
    due_reminder_days_before = models.PositiveIntegerField(default=1)
    due_reminder_email_enabled = models.BooleanField(default=True)
    due_reminder_sms_enabled = models.BooleanField(default=True)
    due_reminder_mobile_enabled = models.BooleanField(default=True)

    due_overdue_enabled = models.BooleanField(default=True)
    due_overdue_days_after = models.PositiveIntegerField(default=0)
    overdue_email_enabled = models.BooleanField(default=True)
    overdue_sms_enabled = models.BooleanField(default=True)
    overdue_mobile_enabled = models.BooleanField(default=True)

    email_enabled = models.BooleanField(default=False)
    email_sender = models.CharField(max_length=120, blank=True)
    email_smtp_host = models.CharField(max_length=120, blank=True)
    email_smtp_port = models.PositiveIntegerField(default=587)
    email_use_tls = models.BooleanField(default=True)
    email_username = models.CharField(max_length=120, blank=True)
    email_password = models.CharField(max_length=255, blank=True)
    email_schedule_enabled = models.BooleanField(default=False)
    email_schedule_hour = models.PositiveSmallIntegerField(default=9)
    email_schedule_minute = models.PositiveSmallIntegerField(default=0)
    email_schedule_timezone = models.CharField(max_length=64, blank=True)

    sms_enabled = models.BooleanField(default=False)
    sms_provider = models.CharField(max_length=120, blank=True)
    sms_api_url = models.CharField(max_length=255, blank=True)
    sms_api_key = models.CharField(max_length=255, blank=True)
    sms_schedule_enabled = models.BooleanField(default=False)
    sms_schedule_hour = models.PositiveSmallIntegerField(default=9)
    sms_schedule_minute = models.PositiveSmallIntegerField(default=0)
    sms_schedule_timezone = models.CharField(max_length=64, blank=True)

    mobile_enabled = models.BooleanField(default=False)
    mobile_schedule_enabled = models.BooleanField(default=False)
    mobile_schedule_hour = models.PositiveSmallIntegerField(default=9)
    mobile_schedule_minute = models.PositiveSmallIntegerField(default=0)
    mobile_schedule_timezone = models.CharField(max_length=64, blank=True)

    reminder_subject = models.CharField(max_length=200, blank=True)
    reminder_body = models.TextField(blank=True)

    overdue_subject = models.CharField(max_length=200, blank=True)
    overdue_body = models.TextField(blank=True)

    overdue_last_run = models.DateField(blank=True, null=True)
    email_schedule_last_run = models.DateTimeField(blank=True, null=True)
    sms_schedule_last_run = models.DateTimeField(blank=True, null=True)
    mobile_schedule_last_run = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bildirim Ayarı"
        verbose_name_plural = "Bildirim Ayarları"

    def __str__(self):
        return "Varsayılan bildirim ayarları"

    @classmethod
    def get_solo(cls):
        settings, _ = cls.objects.get_or_create(singleton_key="default")
        return settings
