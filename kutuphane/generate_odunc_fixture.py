# generate_odunc_fixture.py
import os, json, random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kutuphane.settings")

import django
django.setup()

from django.db.models import Max
from kutuphane_app.models import Ogrenci, KitapNusha

def iso(dt):  # tz-aware ISO string
    return dt.isoformat()

def main():
    # Parametreler
    TOPLAM_KAYIT = 160       # toplam ödünç
    ORAN_TESLIM = 0.6        # %60'ı kapalı (teslim)
    MAX_GUN = 180            # son 6 ay içinden seç
    MAX_EK_GECIKME = 10      # max 10 gün gecikme

    ogrenci_ids = list(Ogrenci.objects.values_list("id", flat=True))
    nusha_ids   = list(KitapNusha.objects.values_list("id", flat=True))
    if not ogrenci_ids or not nusha_ids:
        print("ÖNCE: öğrenci ve nüsha fixture'ları yüklenmiş olmalı.")
        return

    # Mevcut en büyük pk'den devam et
    from kutuphane_app.models import OduncKaydi
    start_pk = (OduncKaydi.objects.aggregate(m=Max('id'))['m'] or 0) + 1
    pk = start_pk

    now = timezone.now()
    data = []

    # Aynı nüsha aynı anda iki kez 'oduncte' görünmesin:
    acik_say = int(TOPLAM_KAYIT * (1 - ORAN_TESLIM))
    kapali_say = TOPLAM_KAYIT - acik_say
    acik_nushalar = set(random.sample(nusha_ids, min(acik_say, len(nusha_ids))))

    # --- Kapalı (teslim edilmiş) kayıtlar ---
    for _ in range(kapali_say):
        ogr_id = random.choice(ogrenci_ids)
        nusha_id = random.choice(nusha_ids)

        ogr = Ogrenci.objects.select_related("rol__loan_policy").get(id=ogr_id)
        role_policy = getattr(ogr.rol, "loan_policy", None)
        duration_days = getattr(role_policy, "duration", None) or 15
        odunc_tarihi = now - timedelta(days=random.randint(7, MAX_GUN))
        iade_tarihi  = odunc_tarihi + timedelta(days=duration_days)

        # %30 geç iade, %70 zamanında/erken
        if random.random() < 0.3:
            gecikme_gun = random.randint(1, MAX_EK_GECIKME)
            teslim_tarihi = iade_tarihi + timedelta(days=gecikme_gun)
            rate = getattr(role_policy, "daily_penalty_rate", None)
            ceza_birim = Decimal(rate or 0)
            gecikme_cezasi = ceza_birim * gecikme_gun
        else:
            erken = random.randint(0, 5)
            teslim_tarihi = iade_tarihi - timedelta(days=erken)
            gecikme_cezasi = None

        data.append({
            "model": "kutuphane_app.odunckaydi",
            "pk": pk,
            "fields": {
                "ogrenci": ogr_id,
                "kitap_nusha": nusha_id,
                "odunc_tarihi": iso(odunc_tarihi),
                "iade_tarihi":  iso(iade_tarihi),
                "teslim_tarihi": iso(teslim_tarihi),
                "durum": "teslim",
                "gecikme_cezasi": (str(gecikme_cezasi) if gecikme_cezasi is not None else None),
            }
        })
        pk += 1  # <-- burada artır

    # --- Açık (halen ödünçte) kayıtlar ---
    for nusha_id in acik_nushalar:
        ogr_id = random.choice(ogrenci_ids)
        ogr = Ogrenci.objects.select_related("rol__loan_policy").get(id=ogr_id)
        role_policy = getattr(ogr.rol, "loan_policy", None)
        duration_days = getattr(role_policy, "duration", None) or 15
        odunc_tarihi = now - timedelta(days=random.randint(1, 30))  # açık kayıtlar genelde daha yeni
        iade_tarihi  = odunc_tarihi + timedelta(days=duration_days)

        data.append({
            "model": "kutuphane_app.odunckaydi",
            "pk": pk,
            "fields": {
                "ogrenci": ogr_id,
                "kitap_nusha": nusha_id,
                "odunc_tarihi": iso(odunc_tarihi),
                "iade_tarihi":  iso(iade_tarihi),
                "teslim_tarihi": None,
                "durum": "oduncte",
                "gecikme_cezasi": None,
            }
        })
        pk += 1  # <-- burada artır

    with open("odunc_veri.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"odunc_veri.json yazıldı. Kayıt sayısı: {len(data)}  (başlangıç pk: {start_pk})")

if __name__ == "__main__":
    main()
