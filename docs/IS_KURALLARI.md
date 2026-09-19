# İŞ KURALLARI — Kütüphane Yönetim Sistemi

> Bu doküman, tüm katmanların (backend, masaüstü, mobil) uyması **zorunlu** iş kurallarının
> tek kaynağıdır. Kurallardan herhangi biriyle çelişen bir değişiklik yapılmadan önce
> bu doküman güncellenmeli ve `kutuphane_app/rules.py` ile senkron tutulmalıdır.
> Yeni bir özellik/ekleme yapılırken **AGENTS.md**'deki kontrol adımına uyulur.

- Sürüm: 1.1
- Durum: Faz C — kitap/nüsha CRUD + katalog + otomatik kapak (test bekliyor)
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
| K4.2 | Admin-only `nüsha durum düzeltme` (yanlış işaretlenmiş durum için) | Evet |
| K4.3 | **Nüsha silme:** herhangi bir `OduncKaydi` kaydı varsa **silinemez** (geçmiş korunur; durum kayıp/hasarli kullanılır) | `can_delete_nusha` |
| K4.4 | **Kitap silme:** tüm nüshalarının `OduncKaydi`'si boşsa silinebilir; değilse **silinemez** | `can_delete_kitap` |
| K4.5 | Kayıp/hasarli nüsha arama sonuçlarında görünür kalır (bulunabilirlik) ama ödünç verilemez | `CheckoutView` (mevcut) |
| K4.6 | Kitap ekleme/düzenleme, nüsha ekleme, nüsha rafını değiştirme **tüm personel** yetkilidir | `KitapViewSet`/`KitapNushaViewSet` |
| K4.7 | Nüsha oluştururken `raf` verilirse `raf_kodu` otomatik raf adıyla doldurulur; `raf` verilmezse serbest metin `raf_kodu` korunur | `KitapNusha.save()` |
| K4.8 | **Durum düzeltme sınırları:** hedef yalnız `mevcut`/`kayip`/`hasarli`; `oduncte` hedefi reddedilir; **açık ödünç kaydı** (`oduncte`/`gecikmis`) olan nüshada düzeltme reddedilir | `can_duzelt_nusha`, `KitapNushaViewSet.durum_duzelt` |
| K4.9 | Kitap silme yetkisi yalnız `admin`; silme öncesi `can_delete_kitap` koşulu (K4.4) denetlenir | `KitapViewSet`, `get_permissions` |

Not: `OduncKaydi.kitap_nusha` FK `CASCADE` + `KitapNusha.kitap` FK `CASCADE` → K4.3/K4.4
olmadan **geçmiş sessizce silinir**.

---

## 5. ROLLER & YETKİ

| Rol | Yetkiler |
|---|---|
| `admin` (Personel.rol) + superuser/staff | Tüm yönetim: öğrenci aktif/pasif, silme, katalog yönetimi (Faz C), personel yönetimi, ayarlar, nüsha düzeltme |
| `personel` (Personel.rol) | Ödünç/İade, arama, görüntüleme, öğrenci düzenleme (CRUD fazı), rapor |

- **K5.1** `IsAdminPersonel` aşağıdakilere uygulanır: personel CRUD, öğrenci durum action,
  katalog yönetimi/merge (yazar/kategori/raf + `kitaplar/{id}/birles/`), nüsha durum düzeltme,
  kitap/nüsha silme, ayarlar.
- **K5.2** `IsAuthenticated` altındaki tüm endpoint'ler token gerektirir.

---

## 6. REFERANS VERİLER (Yazar / Kategori / Raf)

| # | Kural | İşlenir |
|---|---|---|
| K6.1 | Yazar/kategori/raf eklemede `fold` normalizasyonlu **kopya uyarısı** (çocuk/cocuk tespiti) | rules + kitap formu / katalog UI |
| K6.2 | **Birleştirme (merge):** aynı yazım varyantı iki kayıt birleştirilir; kitaplar hedefe taşınır, kaynak silinir, `arama` alanları tazelenir | Faz C (admin): yazar/kategori/raf + `kitaplar/{id}/birles/` |
| K6.3 | Raf kök çözüm: ayrı `Raf` modeli + `KitapNusha.raf` FK (rafta dropdown; kopya kod engeli) | Evet |
| K6.4 | Referans kopyalanması sonrası `arama` denormalizasyonu (yazar/kategori/yeni raf) sinyallerle tazelenir | Mevcut + Faz C |
| K6.5 | **Çift kitap tespiti** (`fold`-normalize başlık grupları — `kitaplar/cift/`) ve tek tıkla birleştirme admin'e açık | `KitapViewSet.cift`/`birles` |
| K6.6 | Katalog yazma işlemleri (yazar/kategori/raf ekle, düzenle, sil, birleştir) **yalnız admin** | Yazar/Kategori/RafViewSet `get_permissions` |

Not: Akıllı raf öneri sistemi (rafların program tarafından düzenli tutulması) ertelendi
— şekillendirme sonradan yapılacak.

---

## 7. İNTERNET / OTOMATİK KATALOG (Faz C)

| # | Kural | İşlenir |
|---|---|---|
| K7.1 | Kitap eklerken başlık/ISBN ile otomatik veri+kapak çekme (Google Books, en çok 5 sonuç) **yardımcı** yoldur; manuel giriş birincildir | Evet — `POST /api/kitap-google/` |
| K7.2 | Çekilen veri el ile doğrulanmadan kaydetme onayı ister (form "Google'dan Doldur" + kullanıcı düzenler, kaydeder) | Evet |
| K7.3 | İnternet yoksa/başarısızsa otomatik çekme gizlenir/sessizce biter, manuel giriş devam eder | Evet |
| K7.4 | Kapak **dosya yüklenmez**; `kapak_url` alanına internet adresi depolanır (Google kitaplı adreslerde `zoom=2` kullanılır) | Evet |
| K7.5 | Google araması `.env`'deki `GOOGLE_BOOKS_API_KEY` ile yapılır (anonim 429 havuzuna düşülmez); başarılı aramalar 7 gün önbelleklenir, ağ hatası/429 önbelleklenmez; istemci ardışık aramalar arasında en az 3 sn bekler; doldurma **akıllı birleştirir** (Google alanı boşsa mevcut değer korunur, doluysa Google değeri yazılır) | Evet — `kutuphane_app/book_lookup.py` |

---

## 8. KİTAP KAYIT AKIŞI — Çift Kayıt Önleme (Faz C)

| # | Kural | İşlenir |
|---|---|---|
| K8.1 | Yeni kitap kaydında **normalize ISBN birebir** eşleşme (rakam+X, `978-975-08-1522-1` ≡ `9789750815221`); ISBN yoksa **fold(başlık)** birebir. Eşleşen kayıt varsa kayıt bloklanır ve istemciye seçenek sunulur (mevcuda nüsha ekle / ayrı kayıt oluştur / iptal) | Evet — `POST /api/kitaplar/` → `409` |
| K8.2 | Kullanıcı bilinçli şekilde ayrı kayıt isterse `force=true` ile kayıt oluşur; otomatik/akılsız çift oluşumu engellenir, bilinçli çift admin'in `cift`+`birles` (K6.1/K6.2) akışına kalır | Evet |
| K8.3 | Eşleşen kayda "nüsha ekle" akışı mevcut `POST /api/nushalar/` üzerinden yürür; barkod verilmezse otomatik `KIT######` üretilir (K4.1) | Evet |
| K8.4 | Yeni kitap kaydı çiftsiz tamamlanınca istemci detay ekranına gider ve nüsha ekleme akışını başlatır (kitap 0 nüsha ile oluşur) | Evet |

> Not: K8 eşleşmesi **kayıt anında kesin** kontroldür; formdaki canlı "benzer kayıtlar" önizlemesi (başlıkta arama) bilgilendirme amaçlıdır ve engellemez.

---

## 9. Test Sorumlulukları

Her kural için en az bir test:
- `rules.py` birim testleri (matris K3.1, çift yazım K3.2, pasif_tarihi K2.1-2).
- API: `kapat` her senaryo (K3.1-3.6), ham PATCH kilidi (K3.7), pasif checkout (K2.3),
  öğrenci durum yetkisi (K2.6), silme kısıtları (K2.7, K4.3-4.4).
- Flutter widget: kapat diyaloğu + ceza önerisi; admin gating (K5).
- K8: ISBN/başlık çakışma → 409, `force` bypass, farklı kitap → 201 (K8.1-8.2).
- K7.5: anahtar URL'de; ikinci arama önbellekten gelir (ağ yok); 429 yanıtı.
- E2E canlı smoke: checkout → kapat döngüsü.