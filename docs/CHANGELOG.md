# CHANGELOG

Bu proje [Semantic Versioning](https://semver.org/) benzeri bir düzen kullanır:
`MAJOR.MINOR.PATCH`. Yayınlar git etiketiyle (`vX.Y.Z`) işaretlenir ve
sunucuya yalnızca etiketli sürümler gönderilir (bkz. `docs/DEPLOY_CLOUD.md`).

## [Unreleased]

- (geliştirme sürüyor)

## [1.1.5] — 2026-09-26

Android mobil uygulaması için sürümlü dağıtım ve uygulama içi güncelleme (K13).

### Backend
- `GET /api/mobil/surum/` (auth'suz): `MOBIL_DIST_DIR/surum.json`'dan sürüm bilgisi
  döner (`surum`, `surumKodu`, `minSurumKodu`, `apkUrl`); yapılandırma/dosya yoksa 404.
- `settings.MOBIL_DIST_DIR` (env ile verilir).
- Testler: `MobilSurumApiTests` (3).

### Mobil
- Bağımlılıklar: `url_launcher`, `package_info_plus`.
- Açılışta sürüm kontrolü: `minSurumKodu` altı **zorunlu**, üstü **opsiyonel** bildirim;
  "Güncelle" APK'yı tarayıcıda açar. Sunucuya ulaşılamazsa sessizce atlanır.
- Android **kalıcı release imzası** (`key.properties` + `mobil/keystore/`, git dışı).
- Testler: `mobil_surum_test` + `update_dialog_test`.

### Sunucu / dağıtım
- `/srv/kutuphane-mobil/` (repo dışı) + nginx `/mobil/` alias; `MOBIL_DIST_DIR` env.
- `mobil/yukle_apk.sh`: APK + `surum.json` + `index.html` üretir/yükler.
- `docs/MOBIL_YAYIN.md`; `IS_KURALLARI.md` K13.

## [1.1.4] — 2026-09-26

Düzeltme: şifre verildikten sonra üye no değişince mobil/üye girişi bozuluyordu.

### Backend
- `UyeSerializer`: `uye_no` değiştiğinde bağlı giriş hesabının kullanıcı adı
  güncellenir (giriş: kullanıcı adı = üye no, K9.5.1); numara başka bir hesapla
  çakışıyorsa hata döner.
- Testlerde hızlı şifre hash'i (MD5) — tam süit ~142 sn → ~6 sn (yalnız test modunda).
- Testler: `UyeGirisHesabiSenkronTests` (2).

## [1.1.3] — 2026-09-26

Kitap detay sayfası görsel iyileştirmesi ve görsel büyütme.

### Web (kök katalog, K11)
- Detay sayfası yeniden tasarlandı: sticky üst çubuk, galeri + küçük görsel
  şeridi, nüsha için **istatistik kartları** (toplam/kütüphanede/ödünçte,
  kayıp-hasarlı), durum bandı, raf çipleri ve açıklama bloğu.
- Görsele tıklayınca **lightbox** ile büyütme: ‹ › gezinme, sayı göstergesi,
  Esc/ok tuşları ve dışına tıklayınca kapanma.
- Testler güncellendi (toplam 131 test).

## [1.1.2] — 2026-09-26

Genel web kataloğunda kitap detay sayfası ve ana sayfa hızlı filtreleri.

### Web (kök katalog, K11)
- Kitap kartına tıklayınca `/kitap/<id>/` detay sayfası: nüsha özeti
  (toplam/mevcut/ödünçte, kayıp-hasarlı), hepsi ödünçteyse **en yakın iade
  tarihi**, açıklama, raf numarası ve yüklenen görseller için **slider**.
- Ana sayfada hızlı filtre: **kategori** seçimi + **yazar** (datalist) araması;
  sayfalama aktif filtreleri korur.
- Testler: katalog filtre + detay sayfası (toplam 130 test).

## [1.1.1] — 2026-09-26

Düzeltme: mobil editör kitap görsellerinde ön kapak (`resim1`) yüklenemiyordu.

### Backend
- `KitapDetailSerializer`: `resim1..resim5` yazılabilir `ImageField` — editör/admin
  multipart PATCH ile görsel yükleyebilir, JSON `null` ile silebilir (önceden
  `resim1` read-only olduğu için ön kapak yüklemesi sessizce yok sayılıyordu).
- Testler: editör resim1 yükleme/silme, öğrenci 403 (toplam 123 test).

## [1.1.0] — 2026-09-26

Dönem başı toplu öğrenci içe aktarma, arşiv/kayıp kuralı ve şifreli yedekleme
altyapısı; masaüstü ve admin yönetimi sadeleştirildi.

### Backend (Django + DRF + PostgreSQL)
- **K9.13 — Toplu öğrenci içe aktarma (dönem başı senkronu):** masaüstünden CSV;
  `dry_run` önizleme + tek atomik uygulama; sınıf normalize (`5/A` → `5-A`),
  eksik sınıf oluşturma, çakışma/mezun yönetimi; yetki personel/admin. Admin
  paneldeki üye içe/dışa aktarma kaldırıldı; tek aktarım yolu bu madde
- **K2.8 — Arşiv kayıp kuralı:** arşivlenen öğrencinin kapatılmamış
  (`oduncte`/`gecikmis`) ödünçlerinin nüshası `kayip` yapılır; katalog korunur
- Yeni şema migration'ları ve `eski_veri_aktar` yönetim komutu + `eski_veri_aktar.sh`
- `django-import-export` bağımlılığı ve admin entegrasyonu kaldırıldı

### Yedekleme / Altyapı
- **Şifreli DB yedeği:** `scripts/yedekle.sh` (`pg_dump -Fc` + `openssl`),
  `scripts/geri-yukle.sh` ve `scripts/cron.d/kutuphane-yedek` (günlük 03:30,
  14 gün saklama). `/etc/kutuphane/.env` içinde `YEDEK_SIFRE` gerektirir
- `docs/DEPLOY_CLOUD.md`: yedek/geri yükleme bölümü ve `ALLOWED_HOSTS`
  (`127.0.0.1,localhost`) güncellendi

### Masaüstü (Flutter, Linux)
- Öğrenci içe aktarma **Ayarlar** sekmesine taşındı (yalnız admin); eski ayar
  sekmeleri ve üye içe/dışa aktarma arayüzü kaldırıldı
- Admin alanları Türkçeleştirildi; arşiv hatırlatması eklendi

## [1.0.0] — 2026-09-24

İlk yayın. Kütüphane yönetim sistemi: Django + DRF backend, Flutter masaüstü
ve mobil istemciler.

### Backend (Django + DRF + PostgreSQL)
- Ödünç/iade politikası ve iş kuralları (`rules.py`, `loan_policy.py`)
- Barkod/nüsha yönetimi, raf kodu; kayıp/hasarlı kapanış notu
- Üye, kitap, kategori, yazar, sınıf, rol yönetimi
- JWT kimlik doğrulama; admin/personel rol ayrımı, şifre değiştirme
- Planlı görevler: gecikme/ceza bildirimleri, sessiz saatler
- KVKK: hassas alan şifreleme (`FIELD_ENCRYPTION_KEY`)
- **Genel web kataloğu (K11):** kök adreste (`/`) kimliksiz, salt-okunur
  kitap listesi + Türkçe harf duyarsız arama; `/api/*` aynı sunucuda
- Sağlık kontrolü: `GET /api/health/`

### Masaüstü (Flutter, Linux)
- Genel bakış, kitaplar/üyeler listeleri, hızlı ödünç/iade akışları
- Sunucu adresi ayarı; rol bazlı yetkiler

### Mobil (Flutter)
- Salt-okunur kapsam: sorgu, üye ödünç/ceza görüntüleme
- Görsel kitap gezintisi/inceleme, galeri, kapak resimleri
- Öğrenci (üye) ve personel giriş akışı; şifre değiştirme
- "Beni hatırla" (şifresiz oturum yenileme), otomatik sunucu erişim kontrolü
- Sunucu ayarı yalnızca giriş akışında; erişilemezse belirgin uyarı

### Altyapı / Dokümantasyon
- Bulut Ubuntu kurulum rehberi (`docs/DEPLOY_CLOUD.md`); PostgreSQL **native**
  (apt, Docker yok) — düşük kaynaklı VPS için tercih edildi
- Sunucu işletim güvenlik protokolü (`docs/SUNUCU_ISLETIM_SAFETY.md`)
- Yayın/güncelleme betikleri (`kutuphane/scripts/deploy.sh`,
  `rollback.sh`) ve iş kuralları (`docs/IS_KURALLARI.md`)
