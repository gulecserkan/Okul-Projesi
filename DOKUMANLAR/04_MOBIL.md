# 04. Mobil Uygulamalar (Flutter)

İki ayrı Flutter uygulaması. Aynı Django API'sine bağlanırlar.

```
mobil/
├── ogrenci/     → ÖĞRENCİ UYGULAMASI (Prototip — backend bağlantısı YOK)
└── ogretmen/    → ÖĞRETMEN/ADMIN UYGULAMASI (Tam işlevsel)
```

> **Önemli:** İki uygulama olgunluk olarak çok farklı. Öğretmen uygulaması gerçek API ile çalışır;
> öğrenci uygulaması yalnızca ekran görünümüdür (mock veri, tüm butonlar ölü, sıfır ağ çağrısı).

---

## I. Öğretmen Uygulaması — `ogretmen/` (işlevsel)

### Dizin Yapısı (`lib/`)
| Dosya/klasör | Görev |
|---|---|
| `main.dart` | Giriş/oturum durum makinesi; tema yönetimi; yönlendirme (Connection→Login→BookList) |
| `api/library_api.dart` | Tek API istemcisi (package:http). Tüm uç çağrıları burada |
| `models/auth.dart` | `AuthTokens` (access, refresh, full_name, role) |
| `models/book.dart` | `BookSummary`, `BookDetail`, `BookImageSlot`, `Category`, `Author` |
| `screens/connection_screen.dart` | Sunucu adresi + handshake (`GET /api/health/`) |
| `screens/login_screen.dart` | Personel girişi (`POST /api/token/`) |
| `screens/book_list_screen.dart` | Ana ekran: arama, filtre, menü, şifre değiştirme |
| `screens/book_detail_screen.dart` | Açıklama düzenleme + 5 resim slotu (yükleme/kırpma/silme) |
| `screens/barcode_scanner_screen.dart` | Kamera ile barkod/QR tarama (mobile_scanner) |
| `screens/image_gallery_screen.dart` | Tam ekran zoomlu galeri (photo_view) |
| `storage/session_storage.dart` | shared_preferences: sunucu, token, tema, son giriş zamanı |
| `theme/app_theme.dart` | 5 tema (Varsayılan, Gece Mavi/Pembe, Gündüz Mavi/Pembe) |

### Başlangıç / Kimlik Akışı
1. Kayıtlı sunucu adresi yoksa → `ConnectionScreen` (6 sn time-out handshake).
2. Token yoksa → `LoginScreen`; `POST /api/token/` → tokenlar + full_name/role kaydedilir.
3. Token varsa ama **15 dakikadan eskiyse** → temizle, yeniden giriş iste.
4. Taze ise → `POST /api/token/refresh/` ile yenile (hata olursa sessizce temizler).
5. Ana ekran açılır; `401` gelirse otomatik çıkış yapılır.

### Kullanılan API Uçları
| Yöntem | Uç | İstemci metodu |
|---|---|---|
| GET | `/api/health/` | `handshake()` |
| POST | `/api/token/` | `login()` |
| POST | `/api/token/refresh/` | `refreshToken()` |
| GET | `/api/kategoriler/` | `fetchCategories()` |
| GET | `/api/yazarlar/` | `fetchAuthors()` |
| GET | `/api/raf-kodlari/` | `fetchShelfCodes()` |
| POST | `/api/change-password/` | `changePassword()` |
| GET | `/api/kitaplar/` | `fetchBooks()` — `q, kategori, yazar, page, min/max_image_count, aciklama_var, raf_query, raf_prefix, isbn, barkod` |
| GET | `/api/kitaplar/<id>/` | `fetchBookDetail()` |
| PATCH | `/api/kitaplar/<id>/` | `updateBook()` — multipart (resim yükleme) veya JSON (silme/anahtar alanı) |

`fetchBooks` kodda `page`, `shelfPrefix`, `minImageCount` destekler ama arayüz bunları göndermiyor (UI'de sayfalama kullanılmıyor).

### Özellikler
- Kitap arama: metin + akıllı tür tespiti (rakam ağırlıklı ise ISBN/barkod gibi davranır).
- Filtreler: kategori, yazar, raf kodu (alt sayfa + manuel giriş), "sitil resim yok" / "açıklama yok", sıfırla, çek-yenile.
- Barkod kamera tarama → arama tetikler.
- Kitap detay: açıklama kaydetme; 5 resim (kamera/galleriden, 3:4 kırpma, tek tek silme, tam ekran galeri).
- Şifre değiştirme; sunucu değiştirme; tema seçimi; oturum/session kalıcılığı.

### Varsayılan/Notlar
- Varsayılan sunucu adresi hardcoded: `http://192.168.1.12:8000` (connection_screen.dart:33).
- Android manifest'te CAMERA, READ_MEDIA_IMAGES, READ_EXTERNAL_STORAGE, FileProvider, UCropActivity mevcut; iOS'ta kamera/fotoğraf kütüphanesi açıklamaları tanımlı.

---

## II. Öğrenci Uygulaması — `ogrenci/` (prototip)

### Dizin Yapısı (`lib/`)
| Dosya | Görev |
|---|---|
| `main.dart` | `MaterialApp` → `StudentHomePage` |
| `screens/home_page.dart` | **Tek ekran** (787 satır): başlık, 6 hızlı eylem, ödünç listesi, öneriler, duyurular |
| `theme/app_themes.dart` | 4 tema (Meltem, Gün Batımı, Gece, Rengarenk) |
| `data/mock_data.dart` | Hardcoded örnek veri (öğrenci "Uluğbey Çetin", 2 kitap, 3 öneri, 2 duyuru) |
| `models/` | `StudentInfo`, `BorrowedBook`, `SuggestedBook`, `Announcement` |

### Durum
- **Ağ bağlantısı yok** — tek model data, hiçbir `http`/`dio` import'u yok (http yalnızca google_fonts bağımlılığı).
- Tüm hızlı eylem butonları ve AppBar butonları (bildirim, QR) **boş** (`onTap: () {}`).
- Tema değişimi bellekte — uygulama kapanınca sıfırlanır.
- Ödünç teslim tarihi renkleri (geçikmiş kırmızı / ≤2 gün amber / ok yeşil), okuma puanı, haftalık hedef çubuğu görsel olarak mevcut (mock puan: 7/10).

### İleride Bağlanacak Uçlar (öneri)
| Özellik | Önerilen uç |
|---|---|
| Giriş | `POST /api/token/` (personel/öğrenci rolüne göre) |
| Ödünçlerim & geçmiş | `GET /api/student-history/<no>/`, `GET /api/student-penalties/<no>/` |
| Kitap arama | `GET /api/kitaplar/?q=` + `GET /api/fast-query/` |
| Öneriler/duyurular | API'de karşılık yok — sunucu tarafında model/uç eklenmeli |

---

## III. Ortak Notlar

- **State yönetimi:** İkisinde de vanilya `StatefulWidget` + `setState`. provider/bloc/riverpod yok.
- **Dil:** Türkçe arayüz.
- **Duplikasyon:** `firstOrNull` genişletmesi iki yerde yeniden tanımlanmış (`library_api.dart`, `barcode_scanner_screen.dart`) — `collection` paketi kullanılabilir.
- **README'ler** varsayılan Flutter şablonu — özelleştirilmemiş.

## Açık İşler (mobil)
- Öğrenci uygulamasının backend'e bağlanması (en büyük boşluk).
- Öğretmen listesinde sayfalama ve debug sorgu satırının kaldırılması/özelleştirilmesi (kitap listesi kullanıcıya "Son sorgu: toplam=... listelenen=..." gösteriyor).
- 401'de kullanıcıya bilgi; sessiz token temizliği şu an sessiz.
- Her iki uygulamada kod yorumlarına TODO yok ama yukarıdaki boşluklar var.