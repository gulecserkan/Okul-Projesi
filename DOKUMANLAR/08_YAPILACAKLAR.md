# 08. Yapılacaklar / Yol Haritası

> Bu dosya, **bilinçli olarak ertelenen** işleri tek yerde toplar. Bir iş burada
> listeliyse ya büyük bir fazdır ya da öncelik sırası sonraya bırakılmıştır.
> Yapıldığında ilgili satır güncellenir/çıkarılır ve gerekiyorsa `docs/IS_KURALLARI.md`
> ile `kutuphane_app/rules.py` senkronlanır (bkz. `AGENTS.md` Faz A adımı).

- Durum: V2.0 — masaüstü çekirdek akışları + K10 ayarları + yazıcı/fiş/etiket (K14) tamam; rulo/kağıt tipi/A4-dosya (K14.9–11) eklendi; mobil bekliyor.
- İlgili: `06_BILINEN_SORUNLAR.md` (teknik borç), `04_MOBIL.md` (mobil), `03_MASUSTU.md` (eski PyQt5 referansı).

---

> **13. Fire bası/durum:** K14 (fiş/etiket/yazıcı) `masaustu/`'de uygulandı — bkz.
> `docs/IS_KURALLARI.md` §14 ve `docs/CHANGELOG.md` [1.1.11]. Aşağıdaki Faz 2
> maddeleri tamamlanmış sayılır; yalnız detaylı/tema düzenleme ve PDF rapor fazı (3)
> ileride kaldı.

## 1. Faz 2 — Yazıcı, Etiket ve Fiş (tamamlandı — kapsam: K14)

Flutter masaüstünde (`masaustu/`) yazdırma **K14** ile eklendi: CUPS `lp`/`lpstat`
üzerinden (Linux), PDF Dart'ta üretilir (`pdf` paketi). Ayrıntı ve iş kuralları:
`docs/IS_KURALLARI.md` §14, `docs/CHANGELOG.md` [1.1.11]. Eski PyQt5 referansı
(`kutuphane_desktop/printing/`) tasarım kaynağı olarak duruyor; tema/editör ve
PDF rapor fazı (aşağıda §3) ileride genişletilebilir.

- [x] **Etiket basımı** — kitap detay›nüsha satırı, çoklu seçim + toplu, nüsha
  eklenince "basılsın mı?" önerisi. 57×40 mm, Code-128 barkod (K14.4).
  Still ayrıntı: `masaustu/lib/printing/label_pdf.dart`.
- [x] **Fiş basımı** — ödünç/iade otomatik, şifre fişi, "Borcu yoktur", ceza ödeme.
  70 mm termal (K14.2/14.3/14.7). Referans: `masaustu/lib/printing/receipt_pdf.dart`.
- [x] **KurumAyarlari entegrasyonu**: fiş/etiket başlığı + iletişim; yerel yedekle
  (K14.1).
- [x] `printer_warning_enabled` açılışta engelleyici olmayan uyarıya bağlı (K14.6).
- [x] CUPS/`lp` tabanlı yazdırma (Linux); `uzaktan-kur.sh` eksik `cups-client`/`cups`
  paketini otomatik kurar.
- [x] **Ortak rulo durumu (K14.9):** üst çubuk kalıcı çip (Fiş/Etiket/Pasif/Tanımlı
  Değil) + basım öncesi onay diyaloğu; `masaustu/lib/printing/rulo_durum.dart`.
- [x] **Kağıt tipi zorlanmaz, cihaz kalibrasyonu esas (K14.11):** PPD eşleyici ve
  `lp -o`/`lpadmin` ile zorlama kaldırıldı; yalnız ölçü (etiket genişlik/yükseklik,
  fiş genişliği) PDF yerleşimi için tutulur. Ayarlar›Yazıcılar "Termal rulo" bölümünde
  kayma/boşluk için kalibrasyon bilgi kutusu; ayrıntılı adımlar
  `docs/IS_KURALLARI.md` (4B-2074C destek notu).
- [x] **A4 "Dosyaya yaz" (K14.10):** `a4Bas` rotası — seçili A4 kuyruğu hazırsa `lp`,
  "Dosyaya yaz (PDF)" veya boş/pasif kuyrukta dosya kaydetme diyaloğu.
- [x] **Fiş/etiket içerik editörü (K14.12):** Ayarlar›Basım Şablonları — altı sahne
  (beş fiş + etiket), alan aç/kapa (zorunlu alanlar kilitli), sıralama, fiş/etiket
  kenar boşluğu, yapısal önizleme ve "Test bas". Tercihler yerel (`config.json` →
  `sablon`); `masaustu/lib/printing/sablon.dart` + `sablon_editor_screen.dart`.
  Etiket PDF'i `LabelElement` listesine, fiş satırları `kod` etiketine geçirildi;
  alt bilgi `take(2)` kısıtı kaldırıldı (adres/telefon/e-posta/web ayrı alan).
  Sıradaki: fiş rulosu alınınca donanım testi.

## 2. Gerçek Bildirimler (ertelendi)

`NotificationSettings` tam (kanallar, planlar, şablonlar, sessiz saatler, eşikler)
ama `jobs.dispatch_notifications()` **yer tutucu** — gerçek gönderim yok.

- [ ] E-posta (SMTP) gönderimi — `email_smtp_host/port/username/password/use_tls`.
- [ ] SMS gönderimi — `sms_provider/api_url/api_key`.
- [ ] Mobil bildirim (push) gönderimi.
- [ ] `due_reminder_days_before` / `due_overdue_days_after` eşiklerini gönderim
      seçiminde kullan.
- [ ] `reminder_subject/body`, `overdue_subject/body` şablonlarını doldur.
- [ ] Gerçek gönderim testleri (SMTP/SMS sağlayıcı mock'u).

## 3. Rapor / İstatistik (ertelendi)

- [ ] Masaüstü **rapor/istatistik sayfası**: gecikme + toplam ceza vb. (tasarım birlikte).
- [ ] Ayarlar altı **istatistik sekmesi** (gecikme + toplam ceza).
- [ ] Haftalık/aylık raporlama (PDF / Excel çıktısı).
- [ ] Dashboard grafikleri için ek endpoint'ler; gelişmiş filtre (sınıf/tarih aralığı).

## 4. Politika Entegrasyonu (ertelendi)

Ayarlarda tanımlı ama işleyişe bağlanmamış alanlar (K10):

- [ ] `auto_extend_enabled` / `auto_extend_days` / `auto_extend_limit` → süre dolunca
      otomatik uzatma (job veya iade anında).
- [ ] `quarantine_days` → iade edilen nüshanın X gün yeniden ödünç verilememesi.

> Not: `require_shelf_code`, `require_damage_note`, `quiet_hours_*` K10.5-K10.7 ile bağlandı.

## 5. Altyapı, Güvenlik ve Temizlik

- [ ] `ilk_veri.json` fixture'ını güncel şemayla yeniden üret (`generate_fixture.py`).
- [ ] Cache katmanı (Redis/Memcached) — ağır istatistik uçlarında.
- [ ] Loglama/hata izleme (Sentry).
- [ ] 2FA veya zorunlu şifre rotasyonu; login başarısızlık kilidi.
- [ ] `FIELD_ENCRYPTION_KEY` rotasyon aracı/komutu.
- [ ] `.deb` paketleme (sunucu + masaüstü) + CI/CD; Docker Compose.
- [ ] `/etc/cron.d/kutuphane-scheduler` deployment aktivasyonu (15 dk).
- [ ] Backup/restore uçtan uca testleri.

## 6. Mobil (devam eden)

Ayrıntı: `04_MOBIL.md`.

> **Kapsam kararı (mobil v2):** Mobil uygulama **salt-okunur asistan** olacak;
> ödünç verme/iade, yönetim, rapor ve yazdırma masaüstünde kalır.

- [x] Kolay temizlikler: 401 bildirimi, sayfalama + debug satırı, `collection`, uygulama adı, sunucu adresi.
- [x] **Mobil v2 kapsamı**: ödünç/iade mobilde kaldırıldı; personel için **Sorgu** (read-only).
- [x] Üye **Ödünçlerim** iyileştirme (aktif/geçmiş, kalan gün, gecikme uyarısı) + **Ceza** sekmesi.
- [x] Widget testleri (bağlantı/giriş/şifre/üye/ödünçlerim+ceza/kitap/**sorgu**).
- [ ] Katalog gezintisi zenginleştirme (kategori/raf filtreli, favoriler, kapak büyütme).
- [ ] **Kitap rezervasyonu/istek** (backend + `K` kuralı + masaüstü işleme + mobil görünüm) — Faz 2.
- [ ] State yönetimi (provider/bloc/riverpod) değerlendirmesi.
