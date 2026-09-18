# 06. Bilinen Sorunlar ve Açık İşler

Son iki commit üzerinden yapılan tarama; düzeltme önerileriyle birlikte.

## A. Kesin Tespit Edilen Sorunlar (kod)

Durum etiketleri: ✅ çözüldü (dalda) · ⏳ açık

| # | Sorun | Konum | Öneri |
|---|---|---|---|
| 1 | ✅ `settings_local.py` ölü kod silindi | — | kaldırıldı |
| 2 | ✅ `AuditLog` `/admin/`'de görünüyor (kayıt doğru) | `kutuphane_app/admin.py:278` | mevcut |
| 3 | ⏳ `ilk_veri.json` eski şema; `roleloanpolicy` satırı yok | `kutuphane/ilk_veri.json` | `python generate_fixture.py` ile yeniden üretmek |
| 4 | ⏳ `dispatch_notifications()` yer tutucu — kanal gönderimi yok | `kutuphane_app/jobs.py` | kanal gerçeklemelerini doldurmak |
| 5 | ⏳ Desktop'ta 3 ölü dosya | `printing/label_maker_qt.py`, `receipt_printer_tmp.py`, `ui/login_window copy.py` | Flutter geçişinde değerlendirilecek |
| 6 | ⏳ Öğretmen mobil debug bilgisi | `mobil/ogretmen/...` | gizle/sil |
| 7 | ⏳ `firstOrNull` iki yerde yeniden tanımlı | `mobil/...` | `collection` paketi |
| 8 | ⏳ Öğrenci mobil uygulaması tamamen mock | `mobil/ogrenci/` | backend'den beslemek |
| 9 | ✅ JWT/tüm dişlisel maddeler — rate limiting eklendi | `todo.md` | güncellendi; cache/Sentry hâlâ açık |
| 10 | ✅ Ölü `settings_local.py` ve `system_restore_*` şablonları silindi | — | temizlendi |
| 11 | ✅ `apps.py` branding'i `admin_site` ile uyumlu hale getirildi (`VERSION` dosyası eklendi) | `kutuphane_app/apps.py` | `VERSION` kökte oluşturuldu |
| 12 | ✅ `VERSION` repo kökünde oluşturuldu | repo kökü | — |

## B. Açık İş Akışları (henüz uygulanmamış)

| # | Konu | Detay |
|---|---|---|
| 1 | **Fiş**: yalnızca `fine_payment` yazdırılıyor; `debt_statement` ("borcu yoktur") ve `general_notice` şablonları tanımlı ama arayüzde tetikleyen yok | öğrenci detayına / yönetici arayüzüne buton eklemek |
| 2 | **Rapor/istatistik sayfası** (desktop) — tasarım birlikte yapılacak | `kutuphane_desktop/todos` |
| 3 | **Ayarlar altı istatistik sekmesi**: gecikme + toplam ceza istatistikleri | `kutuphane_desktop/todos` |
| 4 | **Cron yapılandırması**: `/etc/cron.d/kutuphane-scheduler` — 15 dk aralığın deployment'da aktifleştirilmesi | `setup_backend_service.sh:85-87` |
| 5 | **.deb paketleme** (sunucu + masaüstü) + CI/CD | `kutuphane_desktop/todos` "PAKET HALİNE GETİRME" |
| 6 | **Öğrenci uygulaması**: ana ekranda "Kitap ara / Ödünçlerim / Favoriler / Randevu / Danış / Profilim" butonları ölü; bildirim + QR butonları da boş | backend bağlantısı planı |
| 7 | **Gerçek bildirimler**: e-posta (SMTP) / SMS / mobil kanalların implementation'ı | `jobs.dispatch_notifications()` |

## C. Mimari Notlar / Dikkat Edilecekler

1. **Postgres'e bağımlılık**: trigram (`pg_trgm`), `ArrayAgg`, `DATE_TRUNC`, `TrigramSimilarity`. DB PostgreSQL değilse çalışmaz.
2. **Arşiv & restore yıkıcıdır**: `arsiv_onayla` canlı öğrenciyi siliyor; restore önce `flush`. Yedek alınmadan yapılmamalı.
3. ✅ **CSV içe aktarma pasifleştirme**: artık varsayılan kapalı (`OgrenciResource.pasiflestir=False`); kısmi CSV güvenle yüklenir.
4. ⏳ **JWT tek doğrulama** — DRF permission seviyesinde rol ayrımı yalnızca personel yazma işlemleri için var (`IsAdminPersonel`); diğer uçlarda iş mantığı rollerde.
5. **Zaman dilimi**: `TIME_ZONE='Europe/Istanbul'`, `USE_TZ=True`; istemciler UTC ISO gönderir.
6. ✅ **Barkod**: sunucu otomatik üretir (`KIT`+6 hane); artık tek `MAX` sorgusu + IntegrityError retry — çakışma riski yok denecek kadar az.
7. **Anahtar teslim ssh** proje dışı; docs'ta yok (güvenlik notu: `~/.git-credentials` token içeriyor — paylaşılmamalı).

## D. İyileştirme Önerileri (öncelikli)

1. Öğrenci mobil uygulamasını backend'e bağlamak (en değerli boşluk).
2. `dispatch_notifications()` gerçeklemesi (e-posta önceliği).
3. Fiş türlerinin arayüze bağlanması.
4. ✅ Ölü kod temizliği + Faz 1 sonrası A başlığı sorunlarının çoğu çözüldü.
5. ✅ Rate limiting eklendi; ⏳ cache / Sentry (todo.md'de planlı).
6. `.deb` paket + CI/CD.