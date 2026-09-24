# CHANGELOG

Bu proje [Semantic Versioning](https://semver.org/) benzeri bir düzen kullanır:
`MAJOR.MINOR.PATCH`. Yayınlar git etiketiyle (`vX.Y.Z`) işaretlenir ve
sunucuya yalnızca etiketli sürümler gönderilir (bkz. `docs/DEPLOY_CLOUD.md`).

## [Unreleased]

- (geliştirme sürüyor)

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
