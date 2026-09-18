# Yapılacaklar (TODO)

Bu dosya, backend tarafında (Faz 1 iyileştirmeleri sonrası) kalan geliştirmeleri listeler.

## Tamamlananlar (faz1-backend-iyilestirme dalında)
- [x] JWT token tabanlı kullanıcı doğrulama (simplejwt, login throttle)
- [x] Personel sifre_hash sızıntısı kapatıldı; personel yazma işlemleri admin-only
- [x] SECRET_KEY fail-fast (DEBUG=False)
- [x] TLS/çerez sıkılaştırma ve CSRF_TRUSTED_ORIGINS
- [x] DRF rate limiting (anon 20/dk, user 120/dk, login 10/dk)
- [x] N+1 sorgular (select_related) + büyük listelerde sayfalama
- [x] Barkod üretimi tek MAX sorgusu + IntegrityError retry
- [x] Kişisel veri alan şifrelemesi (telefon/e-posta/bildirim kredileri)
- [x] Yedekler diskte şifreli (.json.enc), restore yol denetimli
- [x] CSV içe aktarmada yanlış pasifleştirme engellendi (bilinçli bayrak)
- [x] Çekirdek testler (16)

## Güvenlik & Kimlik
- [ ] İki faktörlü doğrulama veya zorunlu şifre rotasyonu
- [ ] Login başarısızlık kilidi (kullanıcı başına)

## Raporlama & İstatistik
- [ ] Haftalık / aylık raporlama (PDF / Excel çıktısı)
- [ ] Gelişmiş filtreleme (sınıf bazlı, tarih aralığına göre)
- [ ] Dashboard grafikleri için ek endpointler

## Performans & Güvenlik
- [ ] Cache kullanımı (Redis veya Memcached) — ağır istatistik uçlarında
- [ ] Loglama ve hata izleme (Sentry entegrasyonu)
- [ ] `FIELD_ENCRYPTION_KEY` anahtar rotasyonu aracı/komutu

## Deployment & Test
- [ ] Docker Compose ile hızlı kurulum
- [ ] CI/CD pipeline (GitHub Actions veya GitLab CI)
- [ ] Test coverage raporu; kalan uçlar için testler

## Masaüstü / Mobil (Faz 0+)
- [ ] Masaüstü uygulamasının Flutter'a taşınması (Linux desktop)
- [ ] Mobil istemci (Flutter) ile entegrasyon testleri
- [ ] CUPS/lp tabanlı yazdırma entegrasyonu