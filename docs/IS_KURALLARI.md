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
| K2.6 | `aktif/pasif` değişimi yetkisi | Yalnız `admin` (`IsAdminPersonel`) | `UyeViewSet` durum action | Evet |
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
| K6.1 | Yazar/kategori/raf eklemede **%100 aynı** (normalize) kayıt eklenemez; çok **benzer** (yazım hatası) kayıt varsa liste gösterilip onay sorulur (kitap formu yazar ekleme + katalog UI) | `rules.fold_duplicate` + serializer `validate_*` + istemci `normalizeTr`/`similarityTr` |
| K6.2 | **Birleştirme (merge):** aynı yazım varyantı iki kayıt birleştirilir; kitaplar hedefe taşınır, kaynak silinir, `arama` alanları tazelenir | Faz C (admin): yazar/kategori/raf + `kitaplar/{id}/birles/` |
| K6.3 | Raf kök çözüm: ayrı `Raf` modeli + `KitapNusha.raf` FK (rafta dropdown; kopya kod engeli) | Evet |
| K6.4 | Referans kopyalanması sonrası `arama` denormalizasyonu (yazar/kategori/yeni raf) sinyallerle tazelenir | Mevcut + Faz C |
| K6.5 | **Çift kitap tespiti** (`fold`-normalize başlık grupları — `kitaplar/cift/`) ve tek tıkla birleştirme admin'e açık | `KitapViewSet.cift`/`birles` |
| K6.6 | Katalog yazma işlemleri (düzenle, sil, birleştir) **yalnız admin**; **yazar ekleme** kitap girişinde tüm personel (kategori/raf ekleme admin'de kalır) | Yazar/Kategori/RafViewSet `get_permissions` |

Not: Akıllı raf öneri sistemi (rafların program tarafından düzenli tutulması) ertelendi
— şekillendirme sonradan yapılacak.

---

## 7. İNTERNET / OTOMATİK KATALOG (Faz C)

| # | Kural | İşlenir |
|---|---|---|
| K7.1 | Kitap eklerken başlık/yazar/ISBN ile otomatik veri+kapak çekme (Google Books + Open Library, kaynak başına en çok 5 sonuç) **yardımcı** yoldur; manuel giriş birincildir | Evet — `POST /api/kitap-google/` |
| K7.2 | Çekilen veri el ile doğrulanmadan kaydetme onayı ister (form "Doldur" + kullanıcı düzenler, kaydeder) | Evet |
| K7.3 | İnternet yoksa/başarısızsa otomatik çekme gizlenir/sessizce biter, manuel giriş devam eder | Evet |
| K7.4 | Kapak **dosya yüklenmez**; `kapak_url` alanına internet adresi depolanır (Google kitaplı adreslerde `zoom=2` kullanılır). Adres doluysa form önizlemede kapak görselini **resim olarak gösterir**; görsele tıklayınca büyük (yakınlaştırılabilir) önizleme açılır; görsel yüklenemezse sessizce/hata metniyle geçilir | Evet |
| K7.5 | Arama Google Books (`.env` `GOOGLE_BOOKS_API_KEY`) + Open Library (anahtarsız) ile yapılır; başarılı aramalar 7 gün önbelleklenir, ağ hatası/429 önbelleklenmez; istemci ardışık aramalar arasında en az 3 sn bekler; doldurma **akıllı birleştirir** (gelen alan boşsa mevcut değer korunur, doluysa gelen değer yazılır) | Evet — `kutuphane_app/book_lookup.py` |
| K7.6 | **ISBN önceliği:** ISBN alanı doluysa (veya arama metni ISBN ise) tire/boşluk normalize edilip `isbn:` ile aranır; kaynaklar ISBN'e göre tekilleştirilir, eksik alan/kapak diğer kaynaktan tamamlanır | Evet |
| K7.7 | Sonuçlar **kapak görselli liste** olarak sunulur; kullanıcı seçer, küçük kapağa tıklayınca büyük önizleme açılır. Tek sonuç varsa doğrudan doldurulur. Kapak hiçbir kaynakta yoksa boş bırakılır | Evet |

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

## 9. KİMLİK VE ÜYE MODELİ (K9)

**İki tablo:** `User` (kimlik) + `Uye` (kişi). `Personel` tablosu kaldırıldı.
`Uye` = kütüphane kişisi (öğrenci/öğretmen/editör); ödünç/iade/ceza buraya bağlı.
`Uye.user` **opsiyonel** 1:1 bağlantıdır.

| # | Kural | İşlenir |
|---|---|---|
| K9.1 | Token `tip` taşır: `personel` (operatör/admin) veya `uye` (Uye bağlantılı). `role`: `admin`\|`personel`\|`editor`\|`ogretmen`\|`ogrenci`. Üye için `uye_no` da eklenir | `TokenObtainPairSerializer` |
| K9.2 | **Admin = `is_superuser`** (Django admin + tüm masaüstü). Personel kaydı kavramı yoktur | `IsAdminPersonel` |
| K9.3 | **Operatör** = Uye bağı olmayan normal User; masaüstü yönetimi. **Editör** = `Uye.rol="Editör"` → öğretmen gibi ödünç + **kitap düzenleme** | `IsPersonel` / `IsEditor` |
| K9.4 | **Üye uçları salt-okunur ve kendine ait**: kitap/kategori/yazar listesi açık; `uye-gecmis`/`uye-ceza` yalnız kendi numarası. Personel uçları (`uyeler`, `oduncler`, `nushalar`, `istatistik`, `checkout`, ayarlar...) üyeye **kapalı**; editör yalnız kitap düzenleme uçlarına erişir | `IsPersonel` + `IsEditor` + `requester_uye` |
| K9.5 | Üye girişi: kullanıcı adı = `uye_no`; personel **basit başlangıç şifresi** belirler; ilk girişte **şifre değiştirme zorunlu** (`parola_degistirilsin`). `uye_no` personel/editör için opsiyonel, öğrencide zorunlu; **büyük harfe normalize edilir** ve arama/giriş **harf duyarsızdır** (5a01 ≡ 5A01) | `Uye.save`, `UyeSerializer`, `CaseInsensitiveModelBackend` |
| K9.5.1 | Okul numarası/sınıfı olmayan **Öğretmen/Editör**, masaüstü formunda `uye_no` = **TC kimlik no** ile kaydedilir (sınıf boş bırakılır); kullanıcı adı bu TC olur. TC `uye_no` hücresinde **düz metin** tutulur ve arama/listelerde görünür (KVKK: mahrem görülürse ayrı şifreli `tc_no` alanına taşınır) | masaüstü form + `UyeSerializer` |
| K9.5.2 | **Öğrenci dışı rol (Öğretmen/Editör) ataması yalnız admin**; personel üye kaydında/düzenlemesinde rolü boşaltamaz ve yalnız **Öğrenci** atar | `UyeSerializer.validate` + `rules.rol_degisikligi_izinli` |
| K9.5.3 | Yeni üye formunda şifre alanı **yoktur**; kayıt sonrası **"Şifre eklensin mi?"** sorusu sorulur — **Evet** → şifre penceresi (`Şifre Ver`), **Şimdi değil** → üye şifresiz kaydedilir (sonradan `Şifre Ver` ile tanımlanır) | masaüstü `StudentFormDialog` + `PasswordDialog` |
| K9.6 | Masaüstü hesabı (personel/admin) **yalnız User'dır**, `Uye`'ye bağlı değildir; `Uye→User` yalnız şifre verilince oluşturulur (kullanıcı adı = `uye_no`). **Self-servis (ben-ekle) yoktur.** Ödünç alacak kişiler **üye kaydı** ile ayrılır ve kayıt yetkisi: **admin → öğretmen/editör**, **personel → öğrenci** | `UyeSerializer._set_borrower_password` |
| K9.7 | Uygulama ayrışımı: **masaüstü** yalnız **personel/admin** (`tip=personel`, üye girişi reddedilir); **mobil** yalnız **üye** (`tip=uye`, personel/admin girişi reddedilir). Mobil: `uye` → gezinti + ödünçlerim; `editor` → **iki bölümlü ekran** (Editör: kitap düzenleme + Üye: üyenin aynısı, bkz. K9.12); ilk girişte şifre ekranı | giriş ekranları (masaüstü `AuthApi.login`, mobil `LoginScreen`) |
| K9.8 | Üye **kendi şifresini değiştirebilir**: üye/editör ekranındaki **"Şifre"** düğmesi (ikona + metin, çıkış düğmesi grubunda) → mevcut yeni şifre formu (`POST /api/change-password/`, JWT üzerinden `request.user`) | mobil `UyeHomeScreen`/`BookListScreen` + `ChangePasswordView` |
| K9.9 | Üye **kitap gezintisi/incelemesi** görsel ve teşvik edicidir (kullanıcıyı kütüphaneye yönlendirir): mobil `Kitaplar` sekmesinde **kapak ızgarası ↔ yatay raf** geçişi, **kategori çipleri**, **yazar filtresi**, **sıralama** (başlık/yazar/yayın yılı/nüsha), **"Sadece görselli"** (`min_image_count=1`) ve **"Öğretmen görüşü olan"** (`aciklama_var=1`) anahtarları; tam sayfa inceleme ekranında görseller **"sanki kitap elindeymiş gibi"** gösterilir. **resim1 = ön kapak, resim2 = arka kapak, resim3..5 = önsöz/giriş/tanıtım sayfaları**; **`aciklama` = öğretmen görüşü** (uzman değerlendirmesi) ve inceleme ekranında bölüm başlığı olarak sunulur. Liste yanıtı üye gezintisine yetecek alanları içerir (`kapak_url`, `resim1`, `image_count`, `aciklama_var`, `aciklama`) | mobil `UyeHomeScreen` + `BookInspectScreen`, `KitapBaseSerializer` |
| K9.10 | **Sunucu adresi ayarı yalnız giriş akışındadır**: üye ve editör iç ekranlarında sunucu değiştirme **yoktur**. Giriş ekranında ayar, **kayıtlı sunucuya erişilemediğinde belirginleşir** (`/api/health/` kontrolü başarısız → "Kayıtlı sunucuya erişilemiyor" kutusu + "Sunucu değiştir"); erişim varken yalnız küçük `Sunucu: <adres>` bilgisi gösterilir. İlk kurulum/sunucu ulaşılamazlığında adres girişi el sıkışma ekranındadır (masaüstünde ayar login/yönetim ekranındandır) | mobil `LoginScreen` + `ConnectionScreen` (masaüstü `AppConfig.apiBaseUrl`) |
| K9.11 | Mobil **hızlı giriş**: giriş ekranındaki **"Beni hatırla"** anahtarı açıkken kullanıcı adı/şifre **saklanmaz**; oturum, saklanan **refresh token ile yenilenir** (otomatik giriş, ~30 gün). Anahtar kapalıysa oturum **15 dk** içinde tazelenmemişse yeniden giriş istenir. **Çıkış** token'ları temizler; şifre hiçbir zaman cihazda saklanmaz | mobil `LoginScreen` + `SessionStorage` + `_KutuphaneAppState` |
| K9.12 | **Mobil editör ekranı iki bölümlüdür** (alt gezinme çubuğu ile): **1) Editör** — mevcut kitap düzenleme ekranı; **2) Üye** — normal üyeye görünen üç sekmeli bölümün **birebir aynısı** (`Kitaplar`/`Ödünçlerim`/`Ceza`). Editöre özel ayrı "ödünçlerim" görünümü **kaldırılır**; ödünç ve ceza bilgisi yalnız üye bölümünden görülür. Bölümler arası geçişte her bölümün durumu korunur | mobil `EditorHomeScreen` + `main.dart` |

> Not: `Rol` (Öğrenci/Öğretmen/Editör) ödünç grubudur ve `RoleLoanPolicy` ile süre/limit/ceza belirler; Editör politikası Öğretmen ile aynıdır.

---

## 10. AYARLAR (K10)

| # | Kural | İşlenir |
|---|---|---|
| K10.1 | Ayar **görüntüleme** personel; **düzenleme (PUT/PATCH) yalnız admin** — ödünç politikası, rol bazlı ceza, bildirim, kurum | `LoanPolicyView` / `RoleLoanPolicyView` / `NotificationSettingsView` / `KurumAyarlariView` `get_permissions` |
| K10.2 | **Kurum bilgileri** (kütüphane/okul adı, adres, telefon, e-posta, web, logo_url) tekil kayıt; fiş/etiketlerde kullanılır | `KurumAyarlari.get_solo`, `/api/settings/kurum/` |
| K10.3 | Ödünç politikası ve rol bazlı ceza (süre/limit/tolerans/ceza gecikmesi/hafta sonu/günlük ceza/tavan) sunucudan yönetilir | `settings/loans`, `settings/loans/roles` |
| K10.4 | Masaüstü **Ayarlar** sekmeli: Görünüm · Sunucu · Ödünç Politikası · Ceza (Rol) · Bildirim · Kurum · Hesap; admin değilse düzenleme alanları kapalı | `masaustu/lib/screens/settings_screen.dart` |
| K10.5 | `require_shelf_code` açıkken **yeni nüshada raf kodu zorunlu** (raf seçilmeli); kapalıysa opsiyonel | `KitapNushaSerializer.validate` |
| K10.6 | `require_damage_note` açıkken **kayıp/hasarlı kapatmada açıklama (not) zorunlu**; not `OduncKaydi.kapanis_notu`'na yazılır | `OduncKapatView`, `ReturnDialog` |
| K10.7 | `quiet_hours_*` açıkken **sessiz saatlerde bildirim gönderimi ertelenir** (gecikme güncellemesi yine çalışır); aralık gece yarısını aşabilir | `jobs._in_quiet_hours`, `run_scheduled_jobs` |

---

## 11. GENEL WEB KATALOG (K11)

| # | Kural | İşlenir |
|---|---|---|
| K11.1 | Kök adres (`/`) **kimliksiz, salt-okunur genel kitap kataloğu** sunar: kapak (kapak_url; yoksa resim1), başlık, yazar, kategori, yıl, varsa öğretmen görüşü (`aciklama`) listelenir; `?q=` ile Türkçe harf duyarsız arama (başlık/yazar/kategori/isbn → `arama` alanı) ve sayfalama vardır | `BookCatalogView` + `templates/katalog.html` |
| K11.2 | Katalog ile API aynı sunucuda birlikte çalışır: katalog kimlik istemez, `/api/*` (DRF, JWT) arka planda hizmet vermeye devam eder; katalogda hassas veri sunulmaz | `kutuphane/urls.py` |

---

## 12. Test Sorumlulukları

Her kural için en az bir test:
- `rules.py` birim testleri (matris K3.1, çift yazım K3.2, pasif_tarihi K2.1-2).
- API: `kapat` her senaryo (K3.1-3.6), ham PATCH kilidi (K3.7), pasif checkout (K2.3),
  üye durum yetkisi (K2.6), silme kısıtları (K2.7, K4.3-4.4).
- Flutter widget: kapat diyaloğu + ceza önerisi; admin gating (K5).
- K8: ISBN/başlık çakışma → 409, `force` bypass, farklı kitap → 201 (K8.1-8.2).
- K7.5: anahtar URL'de; ikinci arama önbellekten gelir (ağ yok); 429 yanıtı; ISBN önceliği (`isbn:` + Open Library `/isbn/`); kaynak birleştirme/tekilleştirme + kapak yedekleme (K7.5-K7.7).
- K9: superuser token `role=admin`; üye girişi (`tip=uye`, `uye_no`, `parola_degistirilsin`); üye personel ucuna 403; editör kitap ekleyebilir / üye listesine 403; kendi/başkası geçmiş kapsamı; şifre değişince bayrak kalkar (K9.1-K9.6).
- K10: kurum/ödünç/rol/bildirim GET personel 200; PUT/PATCH personel 403, admin 200 (K10.1-K10.2).
- K10.5-K10.7: raf kodu zorunlu nüsha reddi/raf ile kabul; kayıp/hasarlı notsuz kapatma 400, notlu kapanış notu saklar; sessiz saatte bildirim atlanır, kapalıyken normal (K10IsleyisEntegrasyonTests).
- K11: kök adres 200 + kitap başlıkları; kimlik gerektirmeme; büyük/küçük harfle arama; sonuç-yok mesajı (KatalogWebTests).
- K9.12: editör ekranında iki bölüm (Editör/Üye) alt gezinmesi; üye bölümü üç sekmeyi (Kitaplar/Ödünçlerim/Ceza) gösterir (EditorHomeScreenTests).
- E2E canlı smoke: checkout → kapat döngüsü.