# 08. Yapılacaklar / Yol Haritası

> Bu dosya, **bilinçli olarak ertelenen** işleri tek yerde toplar. Bir iş burada
> listeliyse ya büyük bir fazdır ya da öncelik sırası sonraya bırakılmıştır.
> Yapıldığında ilgili satır güncellenir/çıkarılır ve gerekiyorsa `docs/IS_KURALLARI.md`
> ile `kutuphane_app/rules.py` senkronlanır (bkz. `AGENTS.md` Faz A adımı).

- Durum: V2.0 — masaüstü çekirdek akışları + K10 ayarları tamam; mobil ve yazdırma bekliyor.
- İlgili: `06_BILINEN_SORUNLAR.md` (teknik borç), `04_MOBIL.md` (mobil), `03_MASUSTU.md` (eski PyQt5 referansı).

---

## 1. Faz 2 — Yazıcı, Etiket ve Fiş (ertelendi)

Flutter masaüstünde (`masaustu/`) **hiç yazdırma yok**. Etiket/fiş yalnız eski
PyQt5 istemcisinde (`kutuphane_desktop/printing/`) referans olarak duruyor.
`KurumAyarlari` modeli bu amaçla hazır (şu an yalnızca saklanıyor).

- [ ] **Etiket editörü + etiket basımı**
  - Barkod etiketi (kitap/nüsha), çoklu seçim + toplu basım.
  - Termal `LabelWithMark`, 203 dpi, opsiyonel -90° döndürme.
  - `printer_guard`: yazıcı hazır mı, medya `LabelWithMark` mı → değilse `lpoptions`
    ile otomatik düzelt veya uyar (K10 `printer_warning_enabled` burada devreye girer).
  - Referans: `kutuphane_desktop/printing/label_maker_qt.py`, `template_renderer.py`.
- [ ] **Fiş basımı**
  - Şablonlar: `fine_payment` (masaüstünde var), `debt_statement` ("borcu yoktur"),
    `general_notice` (bilgilendirme/genel) — 70 mm termal, `{{ anahtar }}` placeholder.
  - Arayüz tetikleyicileri: öğrenci detayı ve/veya yönetici ekranı (06 sorun #B1).
  - `build_receipt_context(summary)` benzeri zenginleştirme.
- [ ] **KurumAyarlari entegrasyonu**: fiş başlığı/iletişim ve etiket metinlerinde kullan.
- [ ] `printer_warning_enabled` ayarını açılışta yazıcı kontrolüne bağla.
- [ ] CUPS/`lp` tabanlı yazdırma (Linux) — paket/bağımlılık notları.

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
