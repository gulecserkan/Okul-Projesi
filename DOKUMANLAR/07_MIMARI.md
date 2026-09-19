# 07. Mimari — Kimlik ve Üye Modeli

## Karar
**İki tablo:** `User` (kimlik) + `Uye` (kişi). `Personel` tablosu kaldırılmıştır.
`Ogrenci` → **`Uye`** olarak yeniden adlandırılmıştır. **Admin = `is_superuser`.**

Neden tek tablo değil: Django'nun hazır `User` tablosuna alan eklenemez; "tek tablo"
ancak custom user model (`AUTH_USER_MODEL` değişimi) ile olur ve bu, proje ortasında
çok riskli bir göçtür. Ayrıca tek tablo girişsiz üyeyi imkânsız kılar ve auth ile domain
verisini karıştırır. İki tablo (auth + profil) Django'nun standart desenidir.

## Tablolar ve sorumluluklar
| Tablo | Sorumluluk | İçerik |
|---|---|---|
| `User` (Django auth) | Kimlik + yetki | Operatörler, admin, giriş yapan üyeler |
| `Uye` | Kütüphane kişisi | Ödünç/iade, ceza, iletişim, sınıf, rol |
| `Rol` | Üye rolü + ödünç politikası | **Editör / Öğretmen / Öğrenci** |

Bağlantı: `Uye.user` = **opsiyonel** 1:1 (`related_name="uye"`).

## Roller ve yetkiler
- **Admin**: `User.is_superuser` (Django admin + tüm masaüstü).
- **Operatör**: Uye bağı olmayan `User`; masaüstü yönetimi.
- **Editör**: `Uye.rol="Editör"` → **öğretmen gibi ödünç** + **kitap düzenleme**.
- **Öğretmen / Öğrenci**: `Uye.rol`; yalnız ödünç (düzenleme yok).

Ödünç politikası: `Rol` + `RoleLoanPolicy`. Editörün politikası Öğretmen ile aynıdır.

## Token claimleri
- `tip`: `personel` | `uye`
- `rol`: `admin` | `personel` | `editor` | `ogretmen` | `ogrenci`
- `uye_no` (üye için), `parola_degistirilsin`

Öncelik:
1. `is_superuser` → tip=personel, rol=admin
2. `Uye` bağı varsa → tip=uye, rol=`Uye.rol.ad` (Editör ise `editor`)
3. yoksa → tip=personel, rol=personel (operatör)

## İzin katmanı
- `IsAdminPersonel` = `is_superuser`.
- `IsPersonel` = superuser veya Uye bağı olmayan (operatör).
- `IsEditor` = superuser veya operatör veya `Uye.rol="Editör"`.
- `requester_uye(user)` = superuser/operatör için None; üye için `user.uye` (self-kapsam).

## Otomatik oluşturma kuralı
- **Uye → User:** Yalnız bir üyeye **şifre verildiğinde** `User` oluşturulur/bağlanır
  (`UyeSerializer.sifre`). Girişsiz üyede `user` boş kalır.
- **User → Uye:** Otomatik **değil**. Personel/öğretmen kendini
  **Ayarlar → "Kendimi üye olarak ekle"** (`POST /api/uyeler/ben-ekle/`) ile bağlar.
  Alternatif: Django admin → Üye → `user` alanında mevcut kullanıcıyı seç.

## Alan notları
- `Uye.uye_no`: **opsiyonel + benzersiz** (öğrencide zorunlu; personel/editörde boş).
- Personel/editör/admin'in öğrenci numarası olmadığından `uye_no` boş bırakılabilir.

## Veri göçü (0032)
1. Her `Personel` → ilgili `User`: `rol=admin` ise `is_superuser/is_staff=True`;
   `ad_soyad → first_name`.
2. `Personel` silinir.
3. `Ogrenci → Uye`, `ogrenci_no → uye_no`, `OduncKaydi.ogrenci → uye`.
4. Arşiv modelleri: `ArsivOgrenci → ArsivUye`, `ogrenci_no → uye_no`.
5. `uye_no` opsiyonel; `Uye.user` related_name `uye`.
6. (0033) `Rol="Editör"` + politikası (Öğretmen ile aynı).

## İstemciler
- **Masaüstü** (`masaustu/`): operatör/admin yönetimi; **Genel Bakış** sayfasında aktif ödünçler (ödünçte+gecikmiş) ve özet sayılar; aktif ödünç satırları **iade tarihine göre 4 renk** (kırmızı=gecikmiş, turuncu=bugün, sarı=≤3 gün, yeşil=normal; tema-duyarlı); Ayarlar'da self-servis üye ekleme.
- **Mobil** (`mobil/kutuphane/`): `personel`→yönetim; `editor`→düzenleme+Ödünçlerim;
  `uye`→gezinti+Ödünçlerim; ilk girişte şifre ekranı.

## API uç değişiklikleri
- `/api/ogrenciler/` → `/api/uyeler/`
- `/api/student-history/<no>/` → `/api/uye-gecmis/<no>/`
- `/api/student-penalties/<no>/` → `/api/uye-ceza/<no>/`
- `/api/personel/` **kaldırıldı**
- Yeni: `POST /api/uyeler/ben-ekle/`
