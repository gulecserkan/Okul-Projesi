# 04. Mobil Uygulama (Flutter)

Tek Flutter uygulaması: `mobil/kutuphane/`. Django API'sine bağlanır ve **rol bazlı** çalışır:
giriş yapan hesabın `tip`'ine göre farklı bölümler gösterir.

> **Güncel (K9):** İki ayrı uygulama (öğretmen + öğrenci mock) **tek uygulamaya** indirildi.
> - `tip=personel` → kitap yönetimi (ekle/düzenle, resim, barkod tarama).
> - `tip=uye` (öğrenci/öğretmen) → salt-okunur **gezinti/arama + ödünçlerim**.
> - Üye girişi: kullanıcı adı = `ogrenci_no` + başlangıç şifresi; **ilk girişte şifre değiştirme zorunlu**.
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
| `screens/uye_home_screen.dart` | Üye ekranı: **Kitaplar** (gezinti/arama) + **Ödünçlerim** |
| `screens/book_list_screen.dart` | Personel ana ekranı: arama, filtre, menü, şifre değiştirme |
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
   - `tip == 'uye'` → `UyeHomeScreen`.
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
| GET | `/api/student-history/<no>/` | `fetchStudentHistory()` — üye yalnız kendi numarası |
| GET | `/api/student-penalties/<no>/` | `fetchStudentPenalties()` — üye yalnız kendi numarası |

---

## Özellikler

**Personel (`tip=personel`)**
- Kitap arama: metin + akıllı tür tespiti (rakam ağırlıklı ise ISBN/barkod gibi davranır).
- Filtreler: kategori, yazar, raf kodu, "resim yok"/"açıklama yok", sıfırla, çek-yenile.
- Barkod kamera tarama → arama tetikler.
- Kitap detay: açıklama kaydetme; 5 resim (kamera/galeri, 3:4 kırpma, silme, tam ekran galeri).
- Şifre değiştirme; sunucu değiştirme; tema seçimi; oturum kalıcılığı.

**Üye (`tip=uye`)**
- Kitaplar sekmesi: arama + liste; kitaba dokununca salt-okunur detay (yazar, kategori, yıl, ISBN, raf, açıklama).
- Ödünçlerim sekmesi: kendi ödünç geçmişi (kitap, ödünç/iade tarihi, durum).
- İlk girişte şifre değiştirme ekranı.

---

## Notlar / Açık İşler (mobil)

- **State yönetimi:** vanilya `StatefulWidget` + `setState` (provider/bloc/riverpod yok).
- **Dil:** Türkçe arayüz.
- `firstOrNull` genişletmesi iki yerde yeniden tanımlı (`library_api.dart`, `barcode_scanner_screen.dart`) — `collection` paketi kullanılabilir.
- Varsayılan sunucu adresi hardcoded: `http://192.168.1.12:8000` (connection_screen.dart).
- Android `applicationId/namespace` hâlâ `com.example.ogretmen` (klasör/paket `kutuphane` oldu; gerekirse uygulama kimliği de güncellenebilir).
- Personel listesinde sayfalama ve debug sorgu satırının kaldırılması.
- 401'de kullanıcıya bilgi; şu an sessiz token temizliği.
