"""İş kuralları — tek doğruluk kaynağı (bkz. docs/IS_KURALLARI.md).

Kurallar view katmanında tekrarlanmaz; bu modül üzerinden uygulanır.
"""

from __future__ import annotations

import csv as _csv
import io as _io
import re

from django.db import transaction
from django.utils import timezone

from .models import Kategori, Kitap, KitapNusha, OduncKaydi, Raf, Rol, Sinif, Uye, Yazar
from .turkish import fold

# --- Ödünç kapanış geçişleri (K3) ---
ODUNC_ACIK_DURUMLAR = {"oduncte", "gecikmis"}
ODUNC_KAPANIS_DURUMLARI = ["teslim", "kayip", "hasarli", "iptal"]

# K3.4 — kapanış → nüsha durum senkronu
NUSHA_KAPANIS_MAP = {
    "teslim": "mevcut",
    "iptal": "mevcut",
    "kayip": "kayip",
    "hasarli": "hasarli",
}


def validate_transition(loan, yeni_durum, *, teslim_tarihi=None):
    """K3.1-K3.3: ödünç kapanış geçişini doğrular."""
    if yeni_durum not in ODUNC_KAPANIS_DURUMLARI:
        return False, f"Geçersiz kapanış durumu: {yeni_durum}"
    if loan.durum not in ODUNC_ACIK_DURUMLAR:
        return False, "Bu kayıt zaten kapanmış; tekrar işlem yapılamaz."
    if yeni_durum != "iptal" and not teslim_tarihi:
        return False, "teslim_tarihi (işlem tarihi) zorunludur."
    return True, None


# --- Öğrenci aktif/pasif (K2) ---
def apply_student_status(uye, aktif: bool) -> list:
    """K2.1-K2.4: aktif/pasif geçişi; pasif_tarihi otomatik; uyarı döner."""
    aktif = bool(aktif)
    warnings = []
    if aktif:
        uye.pasif_tarihi = None
    else:
        uye.pasif_tarihi = timezone.now()
        aktif_sayi = OduncKaydi.objects.filter(
            uye=uye, durum__in=["oduncte", "gecikmis"]
        ).count()
        if aktif_sayi:
            warnings.append(
                f"Bu öğrencinin {aktif_sayi} aktif ödüncü var; kitapları toplayın."
            )
    uye.aktif = aktif
    uye.save(update_fields=["aktif", "pasif_tarihi"])
    return warnings


# --- Silme kuralları (K2.7, K4.3, K4.4) ---
def can_delete_uye(uye) -> bool:
    """Etkileşim (ödünç kaydı) yoksa silinebilir; aksi halde pasife alınır."""
    return not OduncKaydi.objects.filter(uye=uye).exists()


def can_delete_nusha(nusha) -> bool:
    """Hiçbir ödünç kaydı yoksa nüsha silinebilir."""
    return not OduncKaydi.objects.filter(kitap_nusha=nusha).exists()


def can_delete_kitap(kitap) -> bool:
    """Tüm nüshaların ödünç kaydı boşsa kitap silinebilir."""
    return not OduncKaydi.objects.filter(kitap_nusha__kitap=kitap).exists()


# --- Kayıp/hasarlı ceza önerisi (K3.5) ---
def suggested_loss_penalty(snapshot):
    """Politikadaki kayıp/hasarlı cezası; sıfırsa öneri üretilmez."""
    val = getattr(snapshot, "kayip_hasar_cezasi", None)
    if val is None:
        return None
    return val if val > 0 else None


# --- Referans veri tekilliği (K6.1) ---
def fold_duplicate(queryset, value, field="ad"):
    """fold-normalize edilmiş kopya var mı? Eşleşen ilk kaydı döndürür."""
    target = fold(str(value)).strip()
    if not target:
        return None
    for row in queryset:
        row_value = fold(str(getattr(row, field) or "")).strip()
        if row_value and row_value == target:
            return row
    return None


# --- Nüsha durum düzeltmesi (K4.8) ---
NUSHA_DUZELTILEBILIR_DURUMLAR = {"mevcut", "kayip", "hasarli"}

OPEN_LOAN_DURUMLARI = ("oduncte", "gecikmis")


def can_duzelt_nusha(nusha, yeni_durum) -> tuple:
    """K4.8: durum düzeltmesi yalnız mevcut/kayıp/hasarlı arası (admin).

    Kural: açık ödünç kaydı olan nüshanın durumu admin düzeltmesiyle değişmez;
    ödünçteki nüsha ancak kapat akışıyla kapanır."""
    if nusha.durum == yeni_durum:
        return True, None
    if yeni_durum not in NUSHA_DUZELTILEBILIR_DURUMLAR:
        return False, "Durum düzeltmesi yalnızca mevcut/kayıp/hasarlı arasında yapılabilir."
    if OduncKaydi.objects.filter(
        kitap_nusha=nusha, durum__in=OPEN_LOAN_DURUMLARI
    ).exists():
        return False, "Nüsha ödünçte; önce ödünç kaydı kapatılmalı."
    return True, None


# --- Kitap kayıt akışı — çift kayıt önleme (K8) ---
_ISBN_STRIP = re.compile(r"[^0-9X]")


def _normalize_isbn(value):
    """ISBN'i karşılaştırılabilir forma sokar (978-975-08-1522-1 → 9789750815221)."""
    s = _ISBN_STRIP.sub("", str(value or "").upper())
    return s


def similar_kitap(baslik, isbn=None, exclude_id=None):
    """K8.1: yeni kayıtta mevcut eşleşme arar.

    Öncelik: normalize ISBN birebir eşleşme; aksi halde fold(başlık) birebir.
    `(benzerler, isbn_eslesme)` döner; ISBN eşleşenler ilk sıradadır.
    """
    isbn_norm = _normalize_isbn(isbn)
    baslik_norm = fold(str(baslik or "")).strip()
    rows = Kitap.objects.only("id", "baslik", "isbn")
    if exclude_id is not None:
        rows = rows.exclude(pk=exclude_id)
    isbn_hits, baslik_hits = [], []
    for k in rows:
        if isbn_norm and _normalize_isbn(k.isbn) == isbn_norm:
            isbn_hits.append(k)
        elif baslik_norm and baslik_norm == fold(k.baslik or "").strip():
            baslik_hits.append(k)
    return isbn_hits + baslik_hits, bool(isbn_hits)


# --- Referans birleştirme (K6.2) ---
def merge_referential(model, hedef, kaynak):
    """K6.2: kaynağı hedefe birleştirir ve kaynağı siler.

    Çocuk kayıtlar hedefe taşınır, arama alanları tazelenir, kaynak silinir."""
    if model is Yazar:
        Kitap.objects.filter(yazar=kaynak).update(yazar=hedef)
        for k in Kitap.objects.filter(yazar=hedef).only("id"):
            k.save(update_fields=["arama"])
    elif model is Kategori:
        Kitap.objects.filter(kategori=kaynak).update(kategori=hedef)
        for k in Kitap.objects.filter(kategori=hedef).only("id"):
            k.save(update_fields=["arama"])
    elif model is Raf:
        KitapNusha.objects.filter(raf=kaynak).update(raf=hedef, raf_kodu=hedef.ad)
        for n in KitapNusha.objects.filter(raf=hedef).only("id"):
            n.save(update_fields=["raf_kodu"])
    else:
        raise ValueError(f"Birleştirilemeyen model: {model}")
    kaynak.delete()


# --- Üye rol atama yetkisi (K9.5.2) ---
def rol_degisikligi_izinli(hedef_rol_ad, *, is_superuser) -> bool:
    """Öğrenci dışı rol (Öğretmen/Editör) ataması yalnız admin'dir.

    Personel, üye kaydında/düzenlemesinde rolü boşaltamaz ve yalnız Öğrenci
    atayabilir. `ben-ekle` kaldırıldı (K9.6); bu kural serializer katmanından
    çağrılır ve self-servis bulunmadığından yalnız personel kayıtlarına uygulanır."""
    if is_superuser:
        return True
    return hedef_rol_ad is not None and hedef_rol_ad == "Öğrenci"


# --- Toplu öğrenci içe aktarma (K9.13) ---
_SAYI_BASLIKLARI = {"uye_no", "ogrenci_no", "no", "numara"}
_ALAN_BASLIKLARI = {"ad": "ad", "soyad": "soyad", "sinif": "sinif", "rol": "rol"}


def _baslik_key(value) -> str:
    """CSV başlıklarını karşılaştırmak için Türkçe-duyarsız anahtar (Sınıf→sinif)."""
    return fold(value).replace("ı", "i").strip()


def _csv_ayrac(sample: str) -> str:
    try:
        return _csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except _csv.Error:
        return ","


def _sinif_normalize(value) -> str:
    """K9.13: CSV sınıfını DB biçimine çevirir (5/A → 5-A, 5a → 5-A)."""
    s = (value or "").strip().upper()
    if not s:
        return ""
    s = re.sub(r"\s*/\s*", "-", s)
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(\d+)\s*-?\s*([A-ZÇĞİÖŞÜ])$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return s


def parse_ogrenci_csv(text: str):
    """K9.13: CSV metnini satır sözlüklerine çevirir.

    Döner: `(satirlar, hata)`. Başlıkta zorunlu sütun eksikse hata metni döner.
    """
    text = text or ""
    sample = text[:2048]
    delimiter = _csv_ayrac(sample)
    rows = list(_csv.reader(_io.StringIO(text), delimiter=delimiter))
    if not rows:
        return None, "CSV boş."
    idx: dict = {}
    for i, h in enumerate(rows[0]):
        key = _baslik_key(h)
        if key in _SAYI_BASLIKLARI:
            idx["uye_no"] = i
        elif key in _ALAN_BASLIKLARI:
            idx[_ALAN_BASLIKLARI[key]] = i
    eksik = [a for a in ("uye_no", "ad", "soyad") if a not in idx]
    if eksik:
        adlar = {"uye_no": "uye_no/ogrenci_no", "ad": "ad", "soyad": "soyad"}
        return None, "CSV başlığında şu sütun(lar) eksik: " + ", ".join(
            adlar[a] for a in eksik
        )
    parsed = []
    for satir_no, raw in enumerate(rows[1:], start=2):
        if not any((c or "").strip() for c in raw):
            continue

        def _get(alan):
            i = idx.get(alan)
            if i is None or i >= len(raw):
                return ""
            return (raw[i] or "").strip()

        parsed.append(
            {
                "satir": satir_no,
                "uye_no": _get("uye_no"),
                "ad": _get("ad"),
                "soyad": _get("soyad"),
                "sinif": _get("sinif"),
                "rol": _get("rol") if "rol" in idx else "",
            }
        )
    return parsed, None


def _hedef_rol(rol_raw, *, is_superuser):
    """K9.13 + K9.5.2: varsayılan Öğrenci; öğrenci dışı rol yalnız admin."""
    ad = (rol_raw or "").strip()
    if not ad or _baslik_key(ad) == "ogrenci":
        return "Öğrenci", None
    if not is_superuser:
        return None, "Öğrenci dışı rol ataması yalnızca yönetici tarafından yapılabilir."
    if not Rol.objects.filter(ad=ad).exists():
        return None, f"Tanımsız rol: {ad}"
    return ad, None


def _mevcut_uyeler():
    """Tüm üyelerin `uye_no → Uye` haritası (rol/aktiflik ayrımı için)."""
    return {
        u.uye_no.upper(): u
        for u in Uye.objects.select_related("sinif", "rol").all()
        if u.uye_no
    }


def _ogrenci_analiz(parsed, *, is_superuser, yeniden_kullan):
    """K9.13: satırları sınıflandırır (DB'ye dokunmaz)."""
    mevcut = _mevcut_uyeler()
    sinif_map = {fold(s.ad): s for s in Sinif.objects.all()}
    sinif_adlari = {}  # fold(ad) → normalize ad (mevcut + üretilecek)
    yeni_siniflar_fold = set()
    gorulen = set()
    satirlar = []
    for r in parsed:
        uye_no = (r["uye_no"] or "").strip().upper()
        ad = (r["ad"] or "").strip()
        soyad = (r["soyad"] or "").strip()
        norm_sinif = _sinif_normalize(r["sinif"])
        rol_ad, rol_hata = _hedef_rol(r["rol"], is_superuser=is_superuser)

        islem, sebep = "yeni", None
        if not uye_no:
            islem, sebep = "hata", "Üye no boş."
        elif not ad or not soyad:
            islem, sebep = "hata", "Ad veya soyad boş."
        elif rol_hata:
            islem, sebep = "hata", rol_hata
        elif uye_no in gorulen:
            islem, sebep = "hata", "CSV içinde aynı üye no birden fazla geçiyor."
        else:
            gorulen.add(uye_no)
            var = mevcut.get(uye_no)
            if var is None:
                islem = "yeni"
            elif not (var.rol and var.rol.ad == "Öğrenci"):
                rol_adi = var.rol.ad if var.rol else "rolsüz"
                islem, sebep = (
                    "hata",
                    f"{rol_adi} kaydıyla aynı üye no; bu satır dokunulmadı.",
                )
            elif var.aktif or yeniden_kullan:
                islem = "yenileme"
            else:
                islem, sebep = (
                    "cakisma",
                    "Pasif (mezun) kayıtla aynı üye no; varsayılan olarak atlandı.",
                )

        if norm_sinif:
            key = fold(norm_sinif)
            sinif_adlari[key] = norm_sinif
            if key not in sinif_map:
                yeni_siniflar_fold.add(key)

        satirlar.append(
            {
                "satir": r["satir"],
                "uye_no": uye_no,
                "ad": ad,
                "soyad": soyad,
                "sinif": norm_sinif,
                "rol": rol_ad or (r["rol"] or "").strip(),
                "islem": islem,
                "sebep": sebep,
            }
        )

    # Pasife çekilecekler: aktif öğrenci olup CSV'de numarası geçmeyenler.
    # CSV'de geçen her numara (hatalı satırlar dâhil) korunur; veri hatalı diye
    # öğrenci pasife çekilmez.
    csv_nolar = {(r["uye_no"] or "").strip().upper() for r in parsed if r["uye_no"]}
    pasife = [
        {"uye_no": u.uye_no, "ad": u.ad, "soyad": u.soyad}
        for key, u in mevcut.items()
        if u.rol and u.rol.ad == "Öğrenci" and u.aktif and key not in csv_nolar
    ]

    ozet = {
        "toplam": len(parsed),
        "yeni": sum(1 for s in satirlar if s["islem"] == "yeni"),
        "yenileme": sum(1 for s in satirlar if s["islem"] == "yenileme"),
        "cakisma": sum(1 for s in satirlar if s["islem"] == "cakisma"),
        "hatali": sum(1 for s in satirlar if s["islem"] == "hata"),
        "pasife_cekilecek": len(pasife),
    }
    return {
        "ozet": ozet,
        "satirlar": satirlar,
        "pasife_cekilecekler": pasife,
        "yeni_siniflar": sorted(sinif_adlari[k] for k in yeni_siniflar_fold),
    }


def ogrenci_aktar(
    csv_text, *, is_superuser=False, dry_run=True, yeniden_kullan=False
):
    """K9.13: dönem başı toplu öğrenci içe aktarma.

    Önizleme (`dry_run=True`) DB'ye dokunmaz; uygulamada tek `atomic` işlem:
    (1) tüm aktif Öğrenciler pasife çekilir, (2) CSV satırları `uye_no`'dan
    eşlenir — yok → yeni, önceden aktif → yenile+aktif, önceden pasif → çakışma,
    (3) listede olmayanlar pasif kalır. Öğretmen/Editör dokunulmaz.
    """
    parsed, hata = parse_ogrenci_csv(csv_text)
    if hata:
        return {"hata": hata}

    analiz = _ogrenci_analiz(
        parsed, is_superuser=is_superuser, yeniden_kullan=yeniden_kullan
    )
    sonuc = {
        "dry_run": bool(dry_run),
        "ozet": analiz["ozet"],
        "satirlar": analiz["satirlar"],
        "pasife_cekilecekler": analiz["pasife_cekilecekler"],
        "yeni_siniflar": analiz["yeni_siniflar"],
    }
    if dry_run:
        return sonuc

    snapshot = _mevcut_uyeler()
    rol_cache = {r.ad: r for r in Rol.objects.all()}
    with transaction.atomic():
        Uye.objects.filter(rol__ad="Öğrenci", aktif=True).update(
            aktif=False, pasif_tarihi=timezone.now()
        )

        sinif_map = {fold(s.ad): s for s in Sinif.objects.all()}
        for ad in analiz["yeni_siniflar"]:
            key = fold(ad)
            if key not in sinif_map:
                obj, _ = Sinif.objects.get_or_create(ad=ad)
                sinif_map[key] = obj

        for s in analiz["satirlar"]:
            if s["islem"] in ("hata", "cakisma"):
                continue
            sinif = sinif_map.get(fold(s["sinif"])) if s["sinif"] else None
            rol = rol_cache.get(s["rol"]) or rol_cache.get("Öğrenci")
            if s["islem"] == "yeni":
                Uye.objects.create(
                    ad=s["ad"],
                    soyad=s["soyad"],
                    uye_no=s["uye_no"],
                    sinif=sinif,
                    rol=rol,
                    aktif=True,
                )
            else:  # yenileme
                u = snapshot.get(s["uye_no"])
                if u is None:  # güvenlik ağı
                    continue
                u.ad = s["ad"]
                u.soyad = s["soyad"]
                u.sinif = sinif
                u.rol = rol
                u.aktif = True
                u.pasif_tarihi = None
                u.save()

    sonuc["uygulandi"] = True
    return sonuc
