# İŞ KURALLARI — Kütüphane Yönetim Sistemi

> Bu doküman, tüm katmanların (backend, masaüstü, mobil) uyması **zorunlu** iş kurallarının
> tek kaynağıdır. Kurallardan herhangi biriyle çelişen bir değişiklik yapılmadan önce
> bu doküman güncellenmeli ve `kutuphane_app/rules.py` ile senkron tutulmalıdır.
> Yeni bir özellik/ekleme yapılırken **AGENTS.md**'deki kontrol adımına uyulur.

- Sürüm: 1.0
- Durum: Taslak (Faz A — onay bekliyor)
- Tarih: 2026-09-19

---

## 1. Genel İlkeler

- **R1.1 — Tek doğruluk kaynağı:** Bir kural koda yazılmadan önce bu tabloya işlenir;
  kod `rules.py` üzerinden bu kuralları uygular, view içinde kural tekrarı yapılmaz.
- **R1.2 — Veri korunur:** Kullanıcı/kitap geçmişi asla sessizce silinmez. Silme yalnızca
  hiçbir etkileşim kaydı olmayan varlıklar için mümkündür; diğerleri pasife alınır.
- **R1.3 — Geçişler doğrulanır:** Durum geçişleri yalnızca geçiş matrisindeki izinli
  yönlerde yapılabilir; çift/gereksiz yazım reddedilir.
- **R1.4 — Atomiklik:** Bir varlığın birden çok kaydını etkileyen işlemler
  `transaction.atomic()` içinde yapılır (örn. ödünç kapatma + nüsha durumu).
- **R1.5 — Yetki:** Hassas işlemler yalnızca `admin` rotlu personel (ve superuser/staff)
  tarafından yapılır (`IsAdminPersonel`).

---

## 2. ÖĞRENCİ — Aktif / Pasif

| # | Koşul | Aksiyon | Etkilenen yer | İşlenir |
|---|---|---|---|---|
| K2.1 | `aktif=True → False` | `pasif_tarihi` = şimdi (otomatik) | `rules.apply_student_status` | Evet |
| K2.2 | `aktif=False → True` | `pasif_tarihi` = `NULL` (temizlenir) | `rules.apply_student_status` | Evet |
| K2.3 | Pasif öğrenci ödünç verme | Reddedilir: "Pasif öğrenci (mezun/nakil/tasdikname) ödünç alamaz" | `CheckoutView` | ✓ mevcut (views.py:1062) |
| K2.4 | Pasif edilirken aktif ödüncü varsa | İşlem **yapılır ama** uyarı döner; kitaplar otomatik kapatılmaz (fiziksel toplama kullanıcı işi) | kapat/status response, masaüstü uyarı | Evet |
| K2.5 | Pasif öğrencinin geçmişi | Kayıtlar **korunur**, silinmez; arşiv akışı 3 yıl sonra devreye girer | admin arşiv, geçmiş ekranları | Mevcut (admin) |
| K2.6 | `aktif/pasif` değişimi yetkisi | Yalnız `admin` (`IsAdminPersonel`) | `OgrenciViewSet` durum action | Evet |
| K2.7 | Öğrenci silme (CRUD) | **Hiçbir `OduncKaydi` kaydı yoksa** silinebilir; varsa sileme reddedilir, pasife alınır | `can_delete_ogrenci` | Evet |

Not: Öğrenci→ödünç FK'sı `CASCADE` olduğundan, silme kurallarına uyulmazsa **tüm geçmiş
SESSİZCE silinir**. Bu yüzden K2.7 zorunludur.

---

## 3. ÖDÜNÇ KAYDI — Durum Geçişleri

### 3.1 Geçiş matrisi

| Başlangıç | → Teslim | → Kayıp | → Hasarli | → İptal |
|---|---|---|---|---|
| `oduncte` | ✅ | ✅ | ✅ | ✅ |
| `gecikmis` | ✅ | ✅ | ✅ | ✅ |
| `teslim` | ❌ | ❌ | ❌ | ❌ |
| `kayip` | ❌ | ❌ | ❌ | ❌ |
| `hasarli` | ❌ | ❌ | ❌ | ❌ |
| `iptal` | ❌ | ❌ | ❌ | ❌ |

- **K3.1 — Tek yön:** yalnızca açık durumlardan (`oduncte`/`gecikmis`) kapanışa izinli;
  kapanmış bir kayıtla yapılan her değişiklik **400** döner.
- **K3.2 — Çift iade yasak:** Kapanmış kayda ikinci bir kapatma talebi **400**.
- **K3.3 — `teslim_tarihi`:** `iptal` hariç tüm kapanışlarda **zorunlu** (olay tarihi).
  `iptal` işleminde `teslim_tarihi` temizlenir.
- **K3.4 — Nüsha senkronu:** kapanışta nüsha durumu birebir güncellenir (tek işlemde):
  - `teslim`/`iptal` → nüsha `mevcut`
  - `kayip` → nüsha `kayip`
  - `hasarli` → nüsha `hasarli`
- **K3.5 — Ceza:** kapanışta `gecikme_cezasi` belirtilebilir (hesaplanmış gecikme cezası
  veya kayıp/hasar ek tutarı). `kayip`/`hasarli` için `LoanPolicy.kayip_hasar_cezasi`
  tabanlı **otomatik öneri** sunulur; kullanıcı düzenleyebilir.
- **K3.6 — Ödeme:** `gecikme_cezasi_odendi` + tarih + tutar tek bir kapanışta veya
  ayrı `PenaltyPaymentView` ile işlenir; ödeme alanları dolu ceza değiştirilemez.
- **K3.7 — Yetki:** kapatma `IsAuthenticated`; ham `PATCH /api/oduncler/{id}` ile
  `durum`/`teslim_tarihi`/`gecikme_cezasi` değiştirilemez (serializer read-only).
- **K3.8 — Gecikme geçişi:** `oduncte↔gecikmis` yalnızca `jobs.update_overdue_loans`
  izinli (kullanıcı kapatması dışında).

### 3.2 Ceza hesabı (özet)

- `overdue_days` → grace+weekend efektif vade sonrası takvim günü.
- `ceza = günlük oran × (overdue_days − penalty_delay_days)`, loan/öğrenci tavanlarıyla.
- Günlük oran rol override'ından gelir; yoksa `0.00` (ceza üretilmez).
- Kayıp/hasarlı ek tutarı: `LoanPolicy.kayip_hasar_cezasi` (otomatik öneri kaynağı).

---

## 4. NÜSHA — Durum ve Silme

| # | Kural | İşlenir |
|---|---|---|
| K4.1 | Nüsha durumu yalnızca checkout / kapat endpoint'leriyle değişir; ham `PATCH /nushalar` ile durum yazılamaz | Evet |
| K4.2 | Admin-only `nüsha durum düzeltme` (yanlış işaretlenmiş durum için) | Faz C |
| K4.3 | **Nüsha silme:** herhangi bir `OduncKaydi` kaydı varsa **silinemez** (geçmiş korunur; durum kayıp/hasarli kullanılır) | `can_delete_nusha` |
| K4.4 | **Kitap silme:** tüm nüshalarının `OduncKaydi`'si boşsa silinebilir; değilse **silinemez** | `can_delete_kitap` |
| K4.5 | Kayıp/hasarli nüsha arama sonuçlarında görünür kalır (bulunabilirlik) ama ödünç verilemez | `CheckoutView` (mevcut) |

Not: `OduncKaydi.kitap_nusha` FK `CASCADE` + `KitapNusha.kitap` FK `CASCADE` → K4.3/K4.4
olmadan **geçmiş sessizce silinir**.

---

## 5. ROLLER & YETKİ

| Rol | Yetkiler |
|---|---|
| `admin` (Personel.rol) + superuser/staff | Tüm yönetim: öğrenci aktif/pasif, silme, katalog yönetimi (Faz C), personel yönetimi, ayarlar, nüsha düzeltme |
| `personel` (Personel.rol) | Ödünç/İade, arama, görüntüleme, öğrenci düzenleme (CRUD fazı), rapor |

- **K5.1** `IsAdminPersonel` aşağıdakilere uygulanır: personel CRUD, öğrenci durum action,
  katalog yönetimi/merge, nüsha düzeltme, ayarlar.
- **K5.2** `IsAuthenticated` altındaki tüm endpoint'ler token gerektirir.

---

## 6. REFERANS VERİLER (Yazar / Kategori / Raf)

| # | Kural | İşlenir |
|---|---|---|
| K6.1 | Yazar/kategori/raf eklemede `fold` normalizasyonlu **kopya uyarısı** (çocuk/cocuk tespiti) | Faz A (rules) / C (UI) |
| K6.2 | **Birleştirme (merge):** aynı yazım varyantı iki kayıt birleştirilir; kitaplar hedefe taşınır, kaynak silinir, `arama` alanları tazelenir | Faz C (admin) |
| K6.3 | Raf kök çözüm: ayrı `Raf` modeli + `KitapNusha.raf` FK (rafta dropdown; kopya kod engeli) | Faz C |
| K6.4 | Referans kopyalanması sonrası `arama` denormalizasyonu (yazar/kategori/yeni raf) sinyallerle tazelenir | Mevcut + Faz C |

Not: Akıllı raf öneri sistemi (rafların program tarafından düzenli tutulması) ertelendi
— şekillendirme sonradan yapılacak.

---

## 7. İNTERNET / OTOMATİK KATALOG (Faz C)

| # | Kural | İşlenir |
|---|---|---|
| K7.1 | Kitap eklerken barkod/ISBN ile otomatik veri+kapak çekme (Google Books) **yardımcı** yoldur; manuel giriş birincildir | Faz C |
| K7.2 | Çekilen veri el ile doğrulanmadan kaydetme onayı ister | Faz C |
| K7.3 | İnternet yoksa/başarısızsa otomatik çekme gizlenir, manuel giriş devam eder | Faz C |

---

## 8. Test Sorumlulukları

Her kural için en az bir test:
- `rules.py` birim testleri (matris K3.1, çift yazım K3.2, pasif_tarihi K2.1-2).
- API: `kapat` her senaryo (K3.1-3.6), ham PATCH kilidi (K3.7), pasif checkout (K2.3),
  öğrenci durum yetkisi (K2.6), silme kısıtları (K2.7, K4.3-4.4).
- Flutter widget: kapat diyaloğu + ceza önerisi; admin gating (K5).
- E2E canlı smoke: checkout → kapat döngüsü.