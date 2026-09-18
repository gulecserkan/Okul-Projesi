# 06. Bilinen Sorunlar ve Açık İşler

Son iki commit üzerinden yapılan tarama; düzeltme önerileriyle birlikte.

## A. Kesin Tespit Edilen Sorunlar (kod)

| # | Sorun | Konum | Öneri |
|---|---|---|---|
| 1 | `settings_local.py` ölü kod — hiçbir yerde import edilmiyor; `APPEND_SLASH=False` etkisiz | `kutuphane/kutuphane/settings_local.py` | ya silin ya settings'e gerçekçi olarak bağlanın |
| 2 | `AuditLog` yanlış admin site'e kayıtlı → `/admin/`'de görünmüyor | `kutuphane_app/admin.py:278` | `admin_site.register(AuditLog)` olarak değiştirin (mevcut `@admin.register` default site'e yazar) |
| 3 | Depodaki `ilk_veri.json` eski şema (rol: `odunc_suresi_gun` vb.); `roleloanpolicy` satırı yok → mevcut DB'ye yükleme başarısız | `kutuphane/ilk_veri.json` | `python generate_fixture.py` ile yeniden üretmek |
| 4 | API yanıtlarındaki bildirim `*_last_run` alanları excluded, ama `dispatch_notifications()` yer tutucu — ayarlar kaydediliyor, gönderim yok | `kutuphane_app/jobs.py:278-286` | kanal gerçeklemelerini doldurmak |
| 5 | Desktop'ta 3 ölü dosya | `printing/label_maker_qt.py`, `printing/receipt_printer_tmp.py`, `ui/login_window copy.py` | yeniden kullanılmayacaksa arşivle/sil |
| 6 | Öğretmen mobil listesinde kullanıcıya debug bilgisi görünüyor ("Son sorgu: toplam=... listelenen=...") ve `dev.log` | `mobil/ogretmen/lib/screens/book_list_screen.dart:148-152, 667, 680` | debug satırını gizle/sil |
| 7 | `firstOrNull` iki yerde yeniden tanımlı | `library_api.dart`, `barcode_scanner_screen.dart` | `collection` paketi kullanın |
| 8 | Öğrenci mobil uygulaması tamamen mock — ağ yok | `mobil/ogrenci/` | backend'den beslenecek şekilde bağlamak |
| 9 | `readme.md` `todo.md`'de JWT "yapılacak" olarak listeleniyor ama JWT zaten tam çalışıyor | `kutuphane/todo.md` | hesapları güncelle (rate limiting, cache, Sentry hâlâ açık) |
| 10 | `settings_local.py` `APPEND_SLASH` etkisizdi; kaldırılan `system_restore_start/confirm/code.html` şablonları hâlâ duruyor | `kutuphane/templates/admin/` | ölü şablonları temizlemek |
| 11 | `apps.py` versiyon/branding'i default admin site'e yazıyor ama `/admin/` custom `admin_site` | `kutuphane_app/apps.py`, `urls.py` | custom site inner header'ında zaten sabit; uyumsuzluk kozmetik |
| 12 | `VERSION` dosyası repo kökünde yok → uygulama sürümü startup'ta "dev" görünür | repo kökü | İstenirse kökte `VERSION` dosyası oluşturulabilir |

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
3. **CSV içe aktarma pasifleştirme**: CSV'de olmayan mevcut aktif öğrenciler pasife çekiliyor — toplu güncelleme dikkat ister.
4. **JWT tek doğrulama** — DRF permission seviyesinde rol ayrımı yok (ör. "yalnızca admin öğrenci siler" gibi kısıt DRF'te yok; iş mantığı uçlardadır).
5. **Zaman dilimi**: `TIME_ZONE='Europe/Istanbul'`, `USE_TZ=True`; istemciler UTC ISO gönderir.
6. **Barkod**: sunucu otomatik üretir (`KIT`+6 hane); `KitapNushaSerializer.create` içinde sıra varsayımı vardır — çok eşzamanlı yaratımda çakışma riski düşük ama mevcut.
7. **Anahtar teslim ssh** proje dışı; docs'ta yok (güvenlik notu: `~/.git-credentials` codeberg token içeriyor — paylaşılmamalı).

## D. İyileştirme Önerileri (öncelikli)

1. Öğrenci mobil uygulamasını backend'e bağlamak (en değerli boşluk).
2. `dispatch_notifications()` gerçeklemesi (e-posta önceliği).
3. Fiş türlerinin arayüze bağlanması.
4. Ölü kod temizliği + `nil` sorunların düzeltilmesi (A başlığı).
5. Rate limiting / cache / Sentry (todo.md'de planlı).
6. `.deb` paket + CI/CD.