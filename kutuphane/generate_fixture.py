import json
import random
from faker import Faker
from datetime import datetime

fake = Faker("tr_TR")

# --- Global veri deposu ---
data = []
pk_counter = {
    "sinif": 1,
    "rol": 1,
    "ogrenci": 1,
    "yazar": 1,
    "kategori": 1,
    "kitap": 1,
    "kitapnusha": 1,
    "roleloanpolicy": 1,
}

# --- Genel ekleme fonksiyonu ---
def add(model, fields):
    pk = pk_counter[model]
    pk_counter[model] += 1
    data.append({"model": f"kutuphane_app.{model}", "pk": pk, "fields": fields})
    return pk


# --- Sınıflar ---
sinif_adlari = ["5-A","5-B","5-C","6-A","6-B","6-C","7-A","7-B","7-C","8-A","8-B","8-C"]
siniflar = [add("sinif", {"ad": s}) for s in sinif_adlari]

# --- Roller ---
rol_ogr = add("rol", {
    "ad": "Öğrenci",
})
rol_ogrt = add("rol", {
    "ad": "Öğretmen",
})

add("roleloanpolicy", {
    "role": rol_ogr,
    "duration": 15,
    "max_items": 3,
    "delay_grace_days": 0,
    "penalty_delay_days": 0,
    "shift_weekend": False,
    "penalty_max_per_loan": "0.00",
    "penalty_max_per_student": "0.00",
    "daily_penalty_rate": "0.50",
})

add("roleloanpolicy", {
    "role": rol_ogrt,
    "duration": 30,
    "max_items": 10,
    "delay_grace_days": 0,
    "penalty_delay_days": 0,
    "shift_weekend": False,
    "penalty_max_per_loan": "0.00",
    "penalty_max_per_student": "0.00",
    "daily_penalty_rate": "0.00",
})

# --- Öğrenciler (her sınıfta 10 öğrenci) ---
for idx, s_id in enumerate(siniflar):
    s_ad = sinif_adlari[idx]
    for i in range(1, 11):
        ogr_no = f"{s_ad.replace('-', '')}{i:02d}"  # örn: 5A01
        add("ogrenci", {
            "ad": fake.first_name(),
            "soyad": fake.last_name(),
            "ogrenci_no": ogr_no[:20],
            "sinif": s_id,
            "rol": rol_ogr,
            "telefon": fake.phone_number()[:20],
            "eposta": fake.email(),
            "kayit_tarihi": fake.date_time_this_decade().isoformat()
        })


# --- Yazarlar (20 adet) ---
yazar_isimleri = [
    "Sabahattin Ali", "Orhan Pamuk", "Yaşar Kemal", "Elif Şafak", "Nazım Hikmet",
    "Peyami Safa", "Halide Edip Adıvar", "Cemil Meriç", "Ahmet Hamdi Tanpınar", "Oğuz Atay",
    "İlber Ortaylı", "Halil İnalcık", "Zülfü Livaneli", "Mehmet Akif Ersoy", "Can Yücel",
    "Refik Halit Karay", "Tarık Buğra", "Sezai Karakoç", "Necip Fazıl Kısakürek", "Attilâ İlhan"
]
yazarlar = [add("yazar", {"ad_soyad": y}) for y in yazar_isimleri]


# --- Kategoriler (4 adet) ---
kategori_adlari = ["Roman", "Tarih", "Bilim", "Çocuk"]
kategoriler = [add("kategori", {"ad": k}) for k in kategori_adlari]


# --- Kitaplar (her kategoriden 20 kitap) ---
kitap_listeleri = {
    "Roman": ["Kürk Mantolu Madonna", "Masumiyet Müzesi", "Tutunamayanlar", "Saatleri Ayarlama Enstitüsü", "Tehlikeli Oyunlar",
              "Serenad", "İnce Memed", "İstanbul Hatırası", "Aşk", "Benim Adım Kırmızı",
              "Eylül", "Çalıkuşu", "Fatih Harbiye", "Sinekli Bakkal", "Sefiller",
              "Suç ve Ceza", "Anna Karenina", "Yeraltından Notlar", "Kırmızı Pazartesi", "Dönüşüm"],
    "Tarih": ["Osmanlı Tarihi", "Devlet-i Aliyye", "Atatürk ve Cumhuriyet", "Türklerin Tarihi", "Osmanlı Padişahları",
              "Selçuklular Tarihi", "İslam Medeniyeti", "Tarih ve Toplum", "Tarih Boyunca Türkler", "Türkiye Cumhuriyeti Tarihi",
              "Roma Tarihi", "Ortaçağ Avrupası", "Fransız Devrimi", "Modern Avrupa Tarihi", "Soğuk Savaş",
              "İslam Tarihi", "Ortadoğu Tarihi", "İpek Yolu", "Osmanlı’da Günlük Hayat", "Büyük Selçuklu"],
    "Bilim": ["Kozmos", "Zamanın Kısa Tarihi", "Atomun Yapısı", "Büyük Tasarım", "Evrim",
              "Kuantum Fiziği", "Genetik Bilim", "Kara Delikler", "Bilim Tarihi", "Felsefe ve Bilim",
              "Matematiğin Tarihi", "Kimya Deneyleri", "Astronomi Atlası", "Bilgisayar Bilimleri", "Yapay Zeka",
              "Nörobilim", "Beyin ve Zihin", "Doğa Bilimleri", "Enerji Kaynakları", "Fizik İlkeleri"],
    "Çocuk": ["Keloğlan Masalları", "Nasreddin Hoca Fıkraları", "La Fontaine Masalları", "Andersen Masalları", "Pinokyo",
              "Harry Potter", "Alice Harikalar Diyarında", "Küçük Prens", "Peter Pan", "Heidi",
              "Robin Hood", "Pamuk Prenses", "Çizmeli Kedi", "Uyuyan Güzel", "Rapunzel",
              "Kırmızı Başlıklı Kız", "Hansel ve Gratel", "Çocuk Kalbi", "Karlar Kraliçesi", "Define Adası"]
}

kitaplar = []
for kat_adi, basliklar in kitap_listeleri.items():
    kat_id = kategoriler[kategori_adlari.index(kat_adi)]
    for baslik in basliklar:
        kitaplar.append(add("kitap", {
            "baslik": baslik,
            "yazar": random.choice(yazarlar),
            "kategori": kat_id,
            "yayin_yili": random.randint(1930, 2020),
            "isbn": str(fake.isbn13()),
            "aciklama": "",
            "resim1": None,
            "resim2": None,
            "resim3": None,
            "resim4": None,
            "resim5": None,
        }))


# --- Kitap Nüshaları ---
for kitap_id in kitaplar:
    for _ in range(random.randint(1,4)):
        add("kitapnusha", {
            "kitap": kitap_id,
            "barkod": f"KIT{pk_counter['kitapnusha']:05d}",
            "durum": "mevcut",
            "raf_kodu": f"R{random.randint(1,50)}",
        })


# --- JSON çıktısı ---
with open("ilk_veri.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("ilk_veri.json dosyası oluşturuldu ✅")
