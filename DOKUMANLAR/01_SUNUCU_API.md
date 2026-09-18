# 01. Sunucu REST API

Django REST Framework. Tüm uçlar varsayılan olarak **JWT + IsAuthenticated** ile korunur (tek istisna `health`).

- Temel URL: `http://<sunucu>:8000/`
- Kimlik: `Authorization: Bearer <access_token>`
- Sayfalama: `page`/`page_size` parametresi verilirse `{count, next, previous, results}`; verilmezse düz liste döner (sayfa boyutu 50, max 200). Öğrenci/nüsha/ödünç listelerinde büyük veri → otomatik sayfalama.
- Oran sınırları (throttle): `anon` 20/dk, kullanıcı 120/dk; token alma/refreshta `login` 10/dk (brute-force koruması).
- Tarih/saat: UTC, ISO 8601.

## 1. Kimlik Doğrulama

| Yöntem | Uç | Açıklama |
|---|---|---|
| POST | `/api/token/` | `{username, password}` → `{access, refresh, full_name, role}` |
| POST | `/api/token/refresh/` | `{refresh}` → yeni token + `full_name`, `role` |
| POST | `/api/change-password/` | `{eski_sifre, yeni_sifre, yeni_sifre2}` → User + Personel.sifre_hash güncellenir |
| GET | `/api/health/` | Açık uç. `{status:"ok", timestamp}` |

## 2. Temel CRUD (ModelViewSet)

| Uç | Özellik |
|---|---|
| `/api/roller/` | Rol CRUD |
| `/api/siniflar/` | Sınıf CRUD |
| `/api/ogrenciler/` | Öğrenci CRUD |
| `/api/yazarlar/` | Yazar CRUD |
| `/api/kategoriler/` | Kategori CRUD |
| `/api/kitaplar/` | Kitap CRUD (zengin filtrelerle) |
| `/api/nushalar/` | Kitap nüshası CRUD (otomatik barkod: `KIT000123`) |
| `/api/oduncler/` | Ödünç kaydı CRUD (`?durum=`) |
| `/api/personel/` | Personel CRUD — **yazma (POST/PUT/PATCH/DELETE) yalnızca admin** (süper/staff veya `rol=admin`); yanıt `{id, ad_soyad, kullanici_adi, rol}` (sifre_hash dışarı verilmez); `kullanici_adi`/`rol` güncellemede değiştirilemez |

### Kitaplar — Filtreler
`?yazar=` `?kategori=` `?q=` (başlık içinde geçen) `?isbn=` `?barkod=` / `?barcode=`
`?raf_query=` `?raf=` `?raf_kodu=` `?raf_prefix=` (raf kodu ön eki)
`?image_count=` `?min_image_count=` `?max_image_count=` `?aciklama_var=`
`?page=` `?page_size=`

Liste yanıtı `KitapSerializer` (özet, resimsiz); detay `GET /api/kitaplar/<id>/` `KitapDetailSerializer` (açıklama + resim1..5 absolute URL).

### Nüshalar — Filtreler
`?kitap=` / `?kitap_id=` `?barkod=` (tırnak temizlenir, iexact) `?prefix=` (barkod başlangıcı) `?kitap__isbn=` / `?kitap_isbn=`

## 3. İş Akışı Uçları (özel)

| Yöntem | Uç | Açıklama |
|---|---|---|
| GET | `/api/fast-query/?q=...` | **Tür tanıyan hızlı arama.** `?barkod=`, `?isbn=`, `?baslik=`, `?ogrenci_no=` veya tek `q`. Sıra: barkod → ISBN → başlık (trigram ≥0.2, 10 öneri) → öğrenci no. Öğrenci yanıtına aktif ödünçler + geçmiş + ceza özeti + rol politikası eklenir. |
| POST | `/api/checkout/` | `{ogrenci_no, barkod}` → ödünç açar. Doğrular: rol bloklu mu, aktif ödünç limiti (isteğe bağlı `max_allowed`), nüsha durumu, mükerrer aktif ödünç. `iade_tarihi` hesabı: rol süresi + hafta sonu kaydırma; `?iade_tarihi=` ile elle geçersiz kılınabilir. |
| GET | `/api/student-history/<ogrenci_no>/` | Öğrencinin tüm ödünç geçmişi (iptal hariç, yeniden eskiye) |
| GET | `/api/student-penalties/<ogrenci_no>/` | Ceza özeti `{outstanding_total, outstanding_count, entries, has_more}` + öğrenci |
| GET | `/api/book-history/<barkod>/` | Nüshanın geçmişi + aynı kitabın TÜM nüshalarının durumu (aktifler başta) |
| GET | `/api/raf-kodlari/` | Benzersiz raf kodu listesi |
| POST | `/api/penalties/<int:pk>/pay/` | `{amount}` birebir ceza tahsilatı; ödeme alanlarını günceller, güncel özeti döner |
| POST | `/api/logs/` | Denetim günlüğü yazar `{islem, detay}` (IP otomatik) |
| POST | `/api/jobs/update-overdue/` | Geciken ödünçleri günceller; `{updated_overdue, reverted, recalculated, total_penalty}` |

## 4. Sayım (Inventory)

| Yöntem | Uç | Açıklama |
|---|---|---|
| CRUD | `/api/inventory-sessions/` | `?status=active|completed|canceled` (virgülle ayrık, listelemede) |
| GET | `/api/inventory-sessions/<id>/items/?status=&q=&limit=&offset=` | Sayım kalemleri (limit max 1000) |
| POST | `/api/inventory-sessions/<id>/mark/` | `{barkod}` veya `{item_id}` ile kalemi `seen` yapar; `{note}` eklenebilir |
| POST | `/api/inventory-sessions/<id>/complete/` | `{status: completed|canceled}` |

Oturum açılışta nüsha filtreleri çözülür, anlık `InventoryItem` seti oluşturulur (`total_items`, `progress`).

## 5. İstatistik (`/api/istatistik/` + alt uç)

| Uç | Açıklama |
|---|---|
| `/en_cok_okuyan_ogrenci/?ay=YYYY-MM` | Ay bazlı en çok okuyan liste |
| `/en_az_okuyan_ogrenci/` | En az okuyanlar |
| `/ogrenci_toplam/?ogrenci_id=` | Öğrencinin okuma toplamı |
| `/en_cok_okuyan_sinif/` | Sınıf bazlı sıralama |
| `/sinif_dagilimi/?sinif_id=` | Okuma dağılımı |
| `/en_cok_okunan_kitaplar/?limit=` | Ödünçlenen kitaplar (varsayılan 10) |
| `/kategori_dagilimi/` | Kategori bazlı okuma |
| `/odunc_trend/?ay=` | Aylık trend (DATE_TRUNC) |
| `/en_cok_geciken/?limit=` | En çok geciken öğrenciler |
| `/toplam_ceza/?ay=` | Gecikme cezası toplamı |

## 6. Ayarlar

| Yöntem | Uç | Açıklama |
|---|---|---|
| GET/PUT/PATCH | `/api/settings/loans/` | Global `LoanPolicy` singleton (rol limitleri boş gelir) |
| GET/PUT | `/api/settings/loans/roles/` | Tüm rol politikaları; PUT liste kabul eder (update_or_create per rol; hepsi None ise siler) |
| GET/PUT/PATCH | `/api/settings/notifications/` | `NotificationSettings` singleton |

## 7. Örnek İstekler

### Token Al
```bash
curl -s -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"kutuphaneci","password":"sifre"}'
```

### Hızlı Arama (Öğrenci)
```bash
curl -s "http://127.0.0.1:8000/api/fast-query/?q=12345" \
  -H "Authorization: Bearer <access>"
```

### Ödünç Verme
```bash
curl -s -X POST http://127.0.0.1:8000/api/checkout/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"ogrenci_no":"12345","barkod":"KIT000001"}'
```

### Ceza Ödeme
```bash
curl -s -X POST http://127.0.0.1:8000/api/penalties/12/pay/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"amount":"4.50"}'
```

## 8. Kullanılan Bağımlılıklar

`Django 5.2.7`, `djangorestframework 3.16.1`, `djangorestframework_simplejwt 5.5.1`, `django-import-export 4.3.10`, `psycopg2-binary 2.9.10`, `whitenoise 6.11.0`, `pillow 12.0.0`, `gunicorn 23.0.0`, `Faker 37.8.0`.

Not: Redis/Memcached/Celery yok — zamanlı işler cron ile `manage.py` komutları üzerinden yürütülür.