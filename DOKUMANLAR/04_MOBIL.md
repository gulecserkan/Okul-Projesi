# 04. Mobil Uygulama (Flutter)

Tek Flutter uygulaması: `mobil/kutuphane/`. Django API'sine bağlanır ve **rol bazlı** çalışır:
giriş yapan hesabın `tip`'ine göre farklı bölümler gösterir.

> **Güncel (mobil v2):** Mobil **salt-okunur ağırlıklı bir asistan**; tezgâh ve yönetim masaüstünde.
> - `tip=personel` → kitap yönetimi + **Sorgu** aracı (operatör/admin).
> - `role=editor` (üye + Editör rolü) → kitap **düzenleme/fotoğraf**; ödünç/iade **yok**.
> - `tip=uye` (öğrenci/öğretmen) → salt-okunur **kitaplar + ödünçlerim + ceza**.
> - **Mobilde ödünç verme ve iade yoktur** (yalnız masaüstünde).
> Eski `mobil/ogrenci/` mock uygulaması kaldırıldı (geçmişte git tarihinde).

```
mobil/
└── kutuphane/   → TEK UYGULAMA (personel + üye, rol bazlı)
```

---

## Dizin Yapısı (`lib/`)

| Dosya/klasör | Görev |
|---|---|
| `main.dart` | Oturum durum makinesi; `tip`'e göre yönlendirme (üye/şifre/personel); tema |
| `api/library_api.dart` | Tek API istemcisi (package:http). Tüm uç çağrıları |
| `models/auth.dart` | `AuthTokens` (access, refresh, full_name, role, **tip, ogrenciNo, parolaDegistirilsin**) |
| `models/book.dart` | `BookSummary`, `BookDetail`, `BookImageSlot`, `Category`, `Author` |
| `screens/connection_screen.dart` | Sunucu adresi + handshake (`GET /api/health/`) |
| `screens/login_screen.dart` | Giriş (`POST /api/token/`) — personel veya üye |
| `screens/force_password_screen.dart` | İlk girişte şifre değiştirme (üye) |
| `screens/uye_home_screen.dart` | Üye ekranı: **Kitaplar** + **Ödünçlerim** (aktif/geçmiş, kalan gün) + **Ceza** |
| `screens/book_list_screen.dart` | Personel ana ekranı: arama, filtre, menü, şifre değiştirme |
| `screens/query_screen.dart` | **Sorgu** (personel, salt-okunur): barkod/üye no ile hızlı sorgu — ödünç/iade yok |
| `screens/book_detail_screen.dart` | Açıklama düzenleme + 5 resim slotu (yükleme/kırpma/silme) |
| `screens/barcode_scanner_screen.dart` | Kamera ile barkod/QR tarama (mobile_scanner) |
| `screens/image_gallery_screen.dart` | Tam ekran zoomlu galeri (photo_view) |
| `storage/session_storage.dart` | shared_preferences: sunucu, token, tip, tema, son giriş zamanı |
| `theme/app_theme.dart` | 5 tema (Varsayılan, Gece Mavi/Pembe, Gündüz Mavi/Pembe) |

---

## Başlangıç / Kimlik Akışı

1. Kayıtlı sunucu adresi yoksa → `ConnectionScreen` (6 sn time-out handshake).
2. Token yoksa → `LoginScreen`; `POST /api/token/` → tokenlar + `full_name/role/tip` kaydedilir.
3. Token varsa ama **15 dakikadan eskiyse** → temizle, yeniden giriş iste.
4. Taze ise → `POST /api/token/refresh/` ile yenile (hata olursa sessizce temizler).
5. Yönlendirme:
   - `parolaDegistirilsin == true` → `ForcePasswordScreen` (zorunlu).
   - `tip == 'uye'` ve `role != 'editor'` → `UyeHomeScreen`.
   - `role == 'editor'` → `BookListScreen` (kitap düzenleme/fotoğraf).
   - aksi halde (`personel`) → `BookListScreen`.
6. `401` gelirse otomatik çıkış yapılır.

---

## Kullanılan API Uçları

| Yöntem | Uç | İstemci metodu |
|---|---|---|
| GET | `/api/health/` | `handshake()` |
| POST | `/api/token/` | `login()` |
| POST | `/api/token/refresh/` | `refreshToken()` |
| GET | `/api/kategoriler/` | `fetchCategories()` |
| GET | `/api/yazarlar/` | `fetchAuthors()` |
| GET | `/api/raf-kodlari/` | `fetchShelfCodes()` |
| POST | `/api/change-password/` | `changePassword()` (üye ilk girişte de kullanır) |
| GET | `/api/kitaplar/` | `fetchBooks()` — `q, kategori, yazar, page, min/max_image_count, aciklama_var, raf_query, raf_prefix, isbn, barkod` |
| GET | `/api/kitaplar/<id>/` | `fetchBookDetail()` |
| PATCH | `/api/kitaplar/<id>/` | `updateBook()` — yalnız personel (üye 403 alır) |
| GET | `/api/uye-gecmis/<no>/` | `fetchStudentHistory()` — üye yalnız kendi numarası |
| GET | `/api/uye-ceza/<no>/` | `fetchStudentPenalties()` — üye yalnız kendi numarası |
| GET | `/api/fast-query/?q=` | `fastQuery()` — barkod/üye no/ISBN/başlık hızlı sorgu (**yalnız personel**) |

---

## Özellikler

**Personel (`tip=personel`)**
- **Sorgu** (üst bardan, salt-okunur): barkod / üye no / ISBN / başlık ile hızlı sorgu (`fast-query`).
  - Üye sonucu: üye bilgisi + pasif üye uyarısı + ceza özeti + aktif ödünçler (barkod, iade tarihi, gecikme, ceza).
  - Nüsha sonucu: durum (mevcut/ödünçte/kayıp/hasarlı) + raf + kimin elinde.
  - ISBN/başlık sonucu: nüsha özeti (toplam/mevcut/ödünçte) + öneriler.
  - **Ödünç verme/iade butonu yoktur** — "Bilgiler görüntüleme amaçlıdır; ödünç/iade masaüstünde yapılır."
- Kitap arama: metin + akıllı tür tespiti; filtreler (kategori, yazar, raf, "resim yok"/"açıklama yok"); barkod kamera.
- Kitap detay: açıklama kaydetme; 5 resim (kamera/galeri, 3:4 kırpma, silme, tam ekran galeri).
- Şifre değiştirme; sunucu değiştirme; tema seçimi; oturum kalıcılığı.

**Editör (`role=editor`)**
- Personel kitap listesi + detay; özellikle **kitap görseli çekme/yükleme** (kamera/galeri, kırpma, silme).
- Ödünç/iade işlemleri yoktur; Sorgu aracı da kapalıdır (`fast-query` personel yetkisi gerektirir).

**Üye (`tip=uye`, öğrenci/öğretmen)**
- Kitaplar sekmesi: arama + liste; kitaba dokununca salt-okunur detay (yazar, kategori, yıl, ISBN, raf, açıklama).
- Ödünçlerim sekmesi: **Aktif / Geçmiş** ayrımı; iade tarihine kalan gün; gecikenler kırmızı uyarı.
- Ceza sekmesi: ödenmemiş toplam + kayıt listesi (kitap, barkod, iade tarihi, tutar).
- İlk girişte şifre değiştirme ekranı.

---

## Notlar / Açık İşler (mobil)

- **State yönetimi:** vanilya `StatefulWidget` + `setState` (provider/bloc/riverpod yok).
- **Dil:** Türkçe arayüz.

### Tamamlanan iyileştirmeler
- **Mobil v2 kapsamı** (salt-okunur asistan): ödünç/iade mobilde kaldırıldı; yerine personel için **Sorgu** (read-only) geldi.
- **Üye:** Ceza sekmesi; Ödünçlerim aktif/geçmiş + kalan gün/gecikme uyarısı.
- `firstOrNull` artık `collection` paketinden (yerel tanımlar kaldırıldı).
- Varsayılan sunucu adresi `lib/app_config.dart` içinde; `--dart-define=KUTUPHANE_SERVER=...` ile değiştirilebilir.
- Uygulama kimliği `com.example.kutuphane` (Android/iOS/macOS/Linux); web/windows/README adları `Kütüphane`.
- Personel listesinde **sayfalama** (`page_size=50`, sonsuz kaydırma) ve debug sorgu satırı kaldırıldı.
- **401** artık sessiz çıkış yerine kullanıcıya bildirilir ("Oturum süresi doldu, lütfen tekrar giriş yapın."), login ekranında bilgi olarak gösterilir.
- Widget testleri: bağlantı, giriş, şifre değiştirme, üye ana ekran (ödünçlerim+ceza), personel kitap listesi ve sorgu (`test/`).

### Açık
- Mobilde geri kalan işler: bkz. `08_YAPILACAKLAR.md` §6.
