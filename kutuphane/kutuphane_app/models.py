from django.db import models
from django.contrib.postgres.indexes import GinIndex
from datetime import time
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.core.validators import EmailValidator
from django.utils import timezone

from .encryption import EncryptedCharField
from .turkish import fold


# --- Sınıflar ---
class Sinif(models.Model):
    ad = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.ad


# --- Roller (Öğrenci / Öğretmen / Personel gibi) ---
class Rol(models.Model):
    ad = models.CharField(
        max_length=50, unique=True, verbose_name="Rol adı",
        help_text="Öğrenci, Öğretmen, Editör gibi rol adı.",
    )  # Öğrenci, Öğretmen vb.

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roller"

    def __str__(self):
        return self.ad


class RoleLoanPolicy(models.Model):
    role = models.OneToOneField(
        Rol, on_delete=models.CASCADE, related_name="loan_policy",
        verbose_name="Rol",
        help_text="Bu ödünç kurallarının geçerli olduğu rol.",
    )
    duration = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Ödünç süresi (gün)",
        help_text="Kitabın kaç gün ödünç verileceği. Boşsa genel Ödünç Politikası değeri kullanılır.",
    )
    max_items = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="En fazla kitap",
        help_text="Bu roldeki bir üyenin aynı anda alabileceği kitap sayısı. Boşsa genel değer.",
    )
    delay_grace_days = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="İade toleransı (gün)",
        help_text="Ceza başlamadan önce tanınan ek gün. Boşsa genel değer.",
    )
    penalty_delay_days = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Ceza gecikmesi (gün)",
        help_text="Toleranstan sonra cezanın başlaması için geçen ek gün. Boşsa genel değer.",
    )
    shift_weekend = models.BooleanField(
        null=True, blank=True, verbose_name="Hafta sonu kaydır",
        help_text="İade tarihi hafta sonuna denk gelirse sonraki iş gününe kaydırılır.",
    )
    penalty_max_per_loan = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        verbose_name="Ceza tavanı – kitap (₺)",
        help_text="Tek ödünç kaydı için en yüksek ceza (0 = sınırsız). Boşsa genel değer.",
    )
    penalty_max_per_student = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        verbose_name="Ceza tavanı – üye (₺)",
        help_text="Bir üyenin toplam cezasının üst sınırı (0 = sınırsız). Boşsa genel değer.",
    )
    daily_penalty_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name="Günlük ceza (₺)",
        help_text="Gecikme başladıktan sonra her gün için uygulanan tutar (0 = ceza yok).",
    )

    class Meta:
        verbose_name = "Rol Ödünç Kuralı"
        verbose_name_plural = "Rol Ödünç Kuralları"

    def __str__(self):
        return f"{self.role.ad} ödünç ayarları"


@receiver(post_save, sender=Rol)
def ensure_role_policy(sender, instance, created, **kwargs):
    if created:
        RoleLoanPolicy.objects.get_or_create(role=instance)


# --- Üyeler (öğrenci / öğretmen / editör) ---
class Uye(models.Model):
    ad = models.CharField(max_length=50)
    soyad = models.CharField(max_length=50)
    # Personel/editör için zorunlu değil; öğrencide doğrulama ile zorunlu.
    uye_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    sinif = models.ForeignKey('Sinif', on_delete=models.SET_NULL, null=True)
    rol = models.ForeignKey('Rol', on_delete=models.SET_NULL, null=True)
    telefon = EncryptedCharField(max_length=512, blank=True, null=True)
    eposta = EncryptedCharField(
        max_length=512,
        blank=True,
        null=True,
        validators=[EmailValidator()],
    )
    kayit_tarihi = models.DateTimeField(auto_now_add=True)
    # 🔹 yeni alanlar:
    aktif = models.BooleanField(default=True)
    pasif_tarihi = models.DateTimeField(blank=True, null=True)
    # Üye mobil girişi (öğrenci/öğretmen/editör). Opsiyonel bağlantı.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uye",
    )
    # İlk girişte şifre değiştirme zorunluluğu (basit başlangıç şifresi).
    parola_degistirilsin = models.BooleanField(default=False)
    # Türkçe arama anahtarı (fold edilmiş: ad, soyad, no, sınıf, rol)
    arama = models.CharField(max_length=400, blank=True, default="")

    def save(self, *args, **kwargs):
        # Üye numarası büyük/küçük harf duyarsız: kanonik biçim BÜYÜK harf.
        if self.uye_no is not None:
            self.uye_no = str(self.uye_no).strip().upper() or None
        self.arama = self._build_arama()
        super().save(*args, **kwargs)

    def _build_arama(self):
        parts = [self.ad or "", self.soyad or "", self.uye_no or ""]
        if self.sinif_id:
            parts.append(self.sinif.ad or "")
        if self.rol_id:
            parts.append(self.rol.ad or "")
        return fold(" ".join(parts))

    def __str__(self):
        return f"{self.ad} {self.soyad} ({self.uye_no})"


@receiver(post_save, sender=Sinif)
def refresh_sinif_arama(sender, instance, **kwargs):
    for o in Uye.objects.filter(sinif=instance).only("id"):
        o.save(update_fields=["arama"])


@receiver(post_save, sender=Rol)
def refresh_rol_arama(sender, instance, **kwargs):
    for o in Uye.objects.filter(rol=instance).only("id"):
        o.save(update_fields=["arama"])


# 🔹 Arşiv paketini temsil eden üst kayıt
class ArsivBatch(models.Model):
    aciklama = models.CharField(max_length=200, blank=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    json_dosya = models.FileField(upload_to='arsiv/', blank=True, null=True)  # indirilebilir JSON

    def __str__(self):
        return f"Arşiv #{self.id} - {self.olusturma_tarihi:%Y-%m-%d %H:%M}"


# 🔹 Arşivde öğrenci fotoğrafı (snapshot)
class ArsivUye(models.Model):
    batch = models.ForeignKey(ArsivBatch, on_delete=models.CASCADE, related_name='arsiv_uyeler')
    uye_no = models.CharField(max_length=20)
    ad = models.CharField(max_length=50)
    soyad = models.CharField(max_length=50)
    sinif_ad = models.CharField(max_length=20, blank=True, null=True)
    rol_ad = models.CharField(max_length=50, blank=True, null=True)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    eposta = models.EmailField(blank=True, null=True)
    kayit_tarihi = models.DateTimeField(blank=True, null=True)
    pasif_tarihi = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.uye_no} - {self.ad} {self.soyad}"


# 🔹 Arşivde ödünç kayıtları (snapshot)
class ArsivOdunc(models.Model):
    batch = models.ForeignKey(ArsivBatch, on_delete=models.CASCADE, related_name='arsiv_oduncler')
    uye_no = models.CharField(max_length=20)
    kitap_baslik = models.CharField(max_length=200)
    barkod = models.CharField(max_length=50)
    odunc_tarihi = models.DateTimeField()
    iade_tarihi = models.DateTimeField()
    teslim_tarihi = models.DateTimeField(blank=True, null=True)
    durum = models.CharField(max_length=20)
    gecikme_cezasi = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.uye_no} - {self.kitap_baslik} ({self.barkod})"


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
# --- Raflar (Katalog: admin yönetir; nüsha > Raf FK) ---
class Raf(models.Model):
    ad = models.CharField(max_length=50, unique=True)
    aciklama = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.ad

    class Meta:
        ordering = ("ad",)


class Kitap(models.Model):
    baslik = models.CharField(max_length=200)
    yazar = models.ForeignKey(Yazar, on_delete=models.SET_NULL, null=True)
    kategori = models.ForeignKey(Kategori, on_delete=models.SET_NULL, null=True)
    yayin_yili = models.IntegerField(blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True)
    # Öğretmen görüşü / uzman değerlendirmesi; üye inceleme ekranında görüntülenir.
    aciklama = models.TextField(
        blank=True,
        help_text="Öğretmen görüşü: kitap hakkında uzman değerlendirmesi; üye inceleme ekranında gösterilir.",
    )
    # İnternetten çekilen kapak görseli (Google Books vb.) — açık URL.
    kapak_url = models.CharField(max_length=500, blank=True, null=True)
    # Kitap inceleme görselleri (kullanıcı yüklü): resim1 = ön kapak,
    # resim2 = arka kapak, resim3..5 = önsöz/giriş/tanıtım sayfaları.
    resim1 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim2 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim3 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim4 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    resim5 = models.ImageField(upload_to="kitap_resimleri/", blank=True, null=True)
    # Türkçe arama anahtarı (fold edilmiş: başlık, isbn, yazar, kategori, raf kodları)
    arama = models.CharField(max_length=800, blank=True, default="")

    def save(self, *args, **kwargs):
        self.arama = self._build_arama()
        super().save(*args, **kwargs)

    def _build_arama(self):
        parts = [self.baslik or ""]
        if self.isbn:
            parts.append(self.isbn)
        if self.yazar_id:
            parts.append(self.yazar.ad_soyad or "")
        if self.kategori_id:
            parts.append(self.kategori.ad or "")
        raf_kodlari = KitapNusha.objects.filter(kitap_id=self.pk).values_list(
            "raf_kodu", flat=True
        )
        parts.extend(r for r in raf_kodlari if r)
        raf_adlari = KitapNusha.objects.filter(
            kitap_id=self.pk, raf__isnull=False
        ).values_list("raf__ad", flat=True)
        parts.extend(r for r in raf_adlari if r)
        return fold(" ".join(parts))

    def __str__(self):
        return self.baslik

    class Meta:
        indexes = [
            GinIndex(
                name="kitap_baslik_trgm",
                fields=["baslik"],
                opclasses=["gin_trgm_ops"],
            ),
        ]


def _delete_replaced_images(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    image_fields = ["resim1", "resim2", "resim3", "resim4", "resim5"]
    for field in image_fields:
        old_file = getattr(old, field, None)
        new_file = getattr(instance, field, None)
        if old_file and old_file != new_file:
            # Temizle, aksi halde diskte eski dosya kalır
            old_file.delete(save=False)


pre_save.connect(_delete_replaced_images, sender=Kitap)


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
    raf = models.ForeignKey(
        "Raf", on_delete=models.SET_NULL, null=True, blank=True, related_name="nushalar"
    )

    def save(self, *args, **kwargs):
        if self.raf_id and not self.raf_kodu:
            self.raf_kodu = self.raf.ad
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.kitap.baslik} - {self.barkod}"


@receiver(post_save, sender=KitapNusha)
def refresh_kitap_arama(sender, instance, **kwargs):
    if kwargs.get("created"):
        instance.kitap.save(update_fields=["arama"])
        return
    try:
        old = KitapNusha.objects.get(pk=instance.pk)
    except KitapNusha.DoesNotExist:
        instance.kitap.save(update_fields=["arama"])
        return
    if old.raf_kodu != instance.raf_kodu or old.raf_id != instance.raf_id:
        instance.kitap.save(update_fields=["arama"])


@receiver(post_save, sender=Yazar)
def refresh_yazar_arama(sender, instance, **kwargs):
    for k in Kitap.objects.filter(yazar=instance).only("id"):
        k.save(update_fields=["arama"])


@receiver(post_save, sender=Kategori)
def refresh_kategori_arama(sender, instance, **kwargs):
    for k in Kitap.objects.filter(kategori=instance).only("id"):
        k.save(update_fields=["arama"])


# --- Ödünç Kayıtları ---
class OduncKaydi(models.Model):
    uye = models.ForeignKey(Uye, on_delete=models.CASCADE)
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
    gecikme_cezasi_odendi = models.BooleanField(default=False)
    gecikme_odeme_tarihi = models.DateTimeField(blank=True, null=True)
    gecikme_odeme_tutari = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    # K10: kayıp/hasarlı kapatmada açıklama (require_damage_note)
    kapanis_notu = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.uye} - {self.kitap_nusha}"


class InventorySession(models.Model):
    STATUS_CHOICES = [
        ("active", "Aktif"),
        ("completed", "Tamamlandı"),
        ("canceled", "İptal Edildi"),
    ]

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inventory_sessions",
        null=True,
        blank=True,
    )
    filters = models.JSONField(default=dict, blank=True)
    total_items = models.PositiveIntegerField(default=0)
    seen_items = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Sayım Oturumu"
        verbose_name_plural = "Sayım Oturumları"

    def __str__(self):
        return f"Sayım #{self.id} - {self.name}"

    @property
    def progress(self):
        if not self.total_items:
            return 0.0
        return min(1.0, self.seen_items / float(self.total_items))

    def mark_completed(self, status="completed"):
        self.status = status
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])


class InventoryItem(models.Model):
    session = models.ForeignKey(InventorySession, on_delete=models.CASCADE, related_name="items")
    kitap_nusha = models.ForeignKey(KitapNusha, on_delete=models.CASCADE, related_name="inventory_items")
    barkod = models.CharField(max_length=50)
    kitap_baslik = models.CharField(max_length=200)
    raf_kodu = models.CharField(max_length=20, blank=True, null=True)
    durum = models.CharField(max_length=20, blank=True)
    seen = models.BooleanField(default=False)
    seen_at = models.DateTimeField(blank=True, null=True)
    seen_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inventory_checks",
        null=True,
        blank=True,
    )
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("session", "kitap_nusha")
        ordering = ("-seen", "raf_kodu", "barkod")
        verbose_name = "Sayım Kalemi"
        verbose_name_plural = "Sayım Kalemleri"

    def __str__(self):
        return f"{self.barkod} @ {self.session_id}"


class AuditLog(models.Model):
    kullanici = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="log_kayitlari",
    )
    islem = models.CharField(max_length=100)
    detay = models.TextField(blank=True)
    ip_adresi = models.GenericIPAddressField(blank=True, null=True)
    olusturma_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-olusturma_zamani"]
        verbose_name = "Log Kaydı"
        verbose_name_plural = "Log Kayıtları"

    def __str__(self):
        user = self.kullanici.get_full_name() if self.kullanici else "Bilinmeyen"
        return f"{self.olusturma_zamani:%Y-%m-%d %H:%M} - {user} - {self.islem}"


class LoanPolicy(models.Model):
    """
    Ödünç sürecine ilişkin genel ayarların tutulduğu tekil kayıt.
    Masaüstü ve diğer istemciler aynı kaynaktan beslenir.
    """

    singleton_key = models.CharField(max_length=50, unique=True, default="default")
    default_duration = models.PositiveIntegerField(
        default=15, verbose_name="Varsayılan ödünç süresi (gün)",
        help_text="Rol için özel değer tanımlı değilse kitabın kaç gün ödünç verileceği.",
    )
    default_max_items = models.PositiveIntegerField(
        default=2, verbose_name="Varsayılan en fazla kitap",
        help_text="Rol için özel değer yoksa bir üyenin aynı anda alabileceği kitap sayısı.",
    )
    delay_grace_days = models.PositiveIntegerField(
        default=0, verbose_name="Varsayılan iade toleransı (gün)",
        help_text="Bu kadar gün gecikme cezasız kabul edilir.",
    )
    penalty_delay_days = models.PositiveIntegerField(
        default=0, verbose_name="Varsayılan ceza gecikmesi (gün)",
        help_text="Toleranstan sonra cezanın başlaması için geçen ek gün.",
    )
    shift_weekend = models.BooleanField(
        default=False, verbose_name="Hafta sonu kaydır",
        help_text="İade tarihi hafta sonuna denk gelirse sonraki iş gününe kaydırılır.",
    )

    auto_extend_enabled = models.BooleanField(
        default=False, verbose_name="Otomatik uzatma açık",
        help_text="Süre dolarken ödünç otomatik uzatılır (aşağıdaki gün/limit kullanılır).",
    )
    auto_extend_days = models.PositiveIntegerField(
        default=0, verbose_name="Otomatik uzatma süresi (gün)",
        help_text="Otomatik uzatmada iade tarihinin kaç gün öteleneceği.",
    )
    auto_extend_limit = models.PositiveIntegerField(
        default=0, verbose_name="Otomatik uzatma limiti (kez)",
        help_text="Bir ödünç kaydının en fazla kaç kez uzatılabileceği.",
    )

    quarantine_days = models.PositiveIntegerField(
        default=0, verbose_name="Karantina (gün)",
        help_text="İade edilen nüshanın yeniden ödünç verilebilmesi için beklenecek gün.",
    )
    require_damage_note = models.BooleanField(
        default=False, verbose_name="Hasarlı iade için not zorunlu",
        help_text="Kayıp/hasarlı iade kapatılırken açıklama girilmesi zorunlu olur.",
    )
    require_shelf_code = models.BooleanField(
        default=False, verbose_name="Raf kodu zorunlu",
        help_text="Yeni nüsha eklerken raf seçilmesi zorunlu olur.",
    )

    quiet_hours_enabled = models.BooleanField(
        default=False, verbose_name="Sessiz saatler açık",
        help_text="Belirtilen aralıkta bildirim gönderimi ertelenir.",
    )
    quiet_hours_start = models.TimeField(
        default=time(22, 0), verbose_name="Sessiz saat başlangıcı",
        help_text="Sessiz aralığın başlangıcı (SS:DD).",
    )
    quiet_hours_end = models.TimeField(
        default=time(8, 0), verbose_name="Sessiz saat bitişi",
        help_text="Bitiş; başlangıçtan küçükse gece yarısını aşar (ör. 22:00–08:00).",
    )

    penalty_max_per_loan = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="Ceza tavanı – kitap (₺)",
        help_text="Tek ödünç kaydı için en yüksek ceza (0 = sınırsız).",
    )
    penalty_max_per_student = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="Ceza tavanı – üye (₺)",
        help_text="Bir üyenin toplam cezasının üst sınırı (0 = sınırsız).",
    )
    kayip_hasar_cezasi = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="Kayıp/hasarlı cezası (₺)",
        help_text="Kayıp/hasarlı nüsha için önerilen ek ceza tutarı (TL). Sıfırsa öneri üretilmez."
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

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

    printer_warning_enabled = models.BooleanField(
        default=True, verbose_name="Açılışta yazıcı uyarısı",
        help_text="Uygulama açılışında yazıcı sorunu varsa uyarı gösterilir.",
    )

    due_reminder_enabled = models.BooleanField(
        default=True, verbose_name="İade hatırlatma açık",
        help_text="İade tarihi yaklaşan üyelere hatırlatma gönderilir.",
    )
    due_reminder_days_before = models.PositiveIntegerField(
        default=1, verbose_name="Kaç gün önce hatırlat",
        help_text="İade tarihinden kaç gün önce hatırlatma yapılacağı.",
    )
    due_reminder_email_enabled = models.BooleanField(default=True, verbose_name="Hatırlatma – e-posta")
    due_reminder_sms_enabled = models.BooleanField(default=True, verbose_name="Hatırlatma – SMS")
    due_reminder_mobile_enabled = models.BooleanField(default=True, verbose_name="Hatırlatma – mobil")

    due_overdue_enabled = models.BooleanField(
        default=True, verbose_name="Gecikme bildirimi açık",
        help_text="İade tarihi geçen üyelere gecikme bildirimi gönderilir.",
    )
    due_overdue_days_after = models.PositiveIntegerField(
        default=0, verbose_name="Gecikmeden kaç gün sonra",
        help_text="İade tarihi geçtikten kaç gün sonra bildirim gönderileceği.",
    )
    overdue_email_enabled = models.BooleanField(default=True, verbose_name="Gecikme – e-posta")
    overdue_sms_enabled = models.BooleanField(default=True, verbose_name="Gecikme – SMS")
    overdue_mobile_enabled = models.BooleanField(default=True, verbose_name="Gecikme – mobil")

    email_enabled = models.BooleanField(default=False, verbose_name="E-posta gönderimi açık")
    email_sender = models.CharField(max_length=120, blank=True, verbose_name="Gönderen adresi")
    email_smtp_host = models.CharField(max_length=120, blank=True, verbose_name="SMTP sunucu")
    email_smtp_port = models.PositiveIntegerField(default=587, verbose_name="SMTP portu")
    email_use_tls = models.BooleanField(default=True, verbose_name="TLS kullan")
    email_username = EncryptedCharField(max_length=512, blank=True, verbose_name="SMTP kullanıcı")
    email_password = EncryptedCharField(max_length=512, blank=True, verbose_name="SMTP şifre")
    email_schedule_enabled = models.BooleanField(default=False, verbose_name="E-posta zamanlama açık")
    email_schedule_hour = models.PositiveSmallIntegerField(default=9, verbose_name="E-posta saat")
    email_schedule_minute = models.PositiveSmallIntegerField(default=0, verbose_name="E-posta dakika")
    email_schedule_timezone = models.CharField(max_length=64, blank=True, verbose_name="E-posta saat dilimi")

    sms_enabled = models.BooleanField(default=False, verbose_name="SMS gönderimi açık")
    sms_provider = models.CharField(max_length=120, blank=True, verbose_name="SMS sağlayıcı")
    sms_api_url = models.CharField(max_length=255, blank=True, verbose_name="SMS API URL")
    sms_api_key = EncryptedCharField(max_length=512, blank=True, verbose_name="SMS API anahtarı")
    sms_schedule_enabled = models.BooleanField(default=False, verbose_name="SMS zamanlama açık")
    sms_schedule_hour = models.PositiveSmallIntegerField(default=9, verbose_name="SMS saat")
    sms_schedule_minute = models.PositiveSmallIntegerField(default=0, verbose_name="SMS dakika")
    sms_schedule_timezone = models.CharField(max_length=64, blank=True, verbose_name="SMS saat dilimi")

    mobile_enabled = models.BooleanField(default=False, verbose_name="Mobil bildirim açık")
    mobile_schedule_enabled = models.BooleanField(default=False, verbose_name="Mobil zamanlama açık")
    mobile_schedule_hour = models.PositiveSmallIntegerField(default=9, verbose_name="Mobil saat")
    mobile_schedule_minute = models.PositiveSmallIntegerField(default=0, verbose_name="Mobil dakika")
    mobile_schedule_timezone = models.CharField(max_length=64, blank=True, verbose_name="Mobil saat dilimi")

    reminder_subject = models.CharField(max_length=200, blank=True, verbose_name="Hatırlatma konusu")
    reminder_body = models.TextField(blank=True, verbose_name="Hatırlatma metni")

    overdue_subject = models.CharField(max_length=200, blank=True, verbose_name="Gecikme konusu")
    overdue_body = models.TextField(blank=True, verbose_name="Gecikme metni")

    overdue_last_run = models.DateField(blank=True, null=True, verbose_name="Gecikme son çalışma")
    email_schedule_last_run = models.DateTimeField(blank=True, null=True, verbose_name="E-posta son çalışma")
    sms_schedule_last_run = models.DateTimeField(blank=True, null=True, verbose_name="SMS son çalışma")
    mobile_schedule_last_run = models.DateTimeField(blank=True, null=True, verbose_name="Mobil son çalışma")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Bildirim Ayarı"
        verbose_name_plural = "Bildirim Ayarları"

    def __str__(self):
        return "Varsayılan bildirim ayarları"

    @classmethod
    def get_solo(cls):
        settings, _ = cls.objects.get_or_create(singleton_key="default")
        return settings


class KurumAyarlari(models.Model):
    """Kurum/kütüphane kimlik bilgileri (fiş ve etiketlerde kullanılır)."""

    singleton_key = models.CharField(max_length=50, unique=True, default="default")
    kutuphane_adi = models.CharField(
        max_length=150, blank=True, verbose_name="Kütüphane adı",
        help_text="Fiş ve etiketlerde görünen kütüphane adı.",
    )
    okul_adi = models.CharField(max_length=150, blank=True, verbose_name="Okul adı")
    adres = models.CharField(max_length=255, blank=True, verbose_name="Adres")
    telefon = models.CharField(max_length=40, blank=True, verbose_name="Telefon")
    eposta = models.CharField(max_length=120, blank=True, verbose_name="E-posta")
    website = models.CharField(max_length=150, blank=True, verbose_name="Web sitesi")
    logo_url = models.CharField(
        max_length=500, blank=True, verbose_name="Logo URL",
        help_text="Fiş/etiketlerde kullanılacak logo görselinin açık adresi.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Kurum Bilgileri"
        verbose_name_plural = "Kurum Bilgileri"

    def __str__(self):
        return self.kutuphane_adi or "Kurum Bilgileri"

    @classmethod
    def get_solo(cls):
        kurum, _ = cls.objects.get_or_create(singleton_key="default")
        return kurum
