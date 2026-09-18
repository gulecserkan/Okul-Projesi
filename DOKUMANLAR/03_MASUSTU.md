# 03. Masaüstü İstemcisi (PyQt5)

Klasör: `kutuphane_desktop/` — Kütüphanenin kasa/ege terminali. Django API'sine `requests` ile bağlanır.

## Çalıştırma

```bash
cd kutuphane_desktop
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Kurulum detayları: `DESKTOP_SETUP.md`

## Dizin Yapısı

| Klasör | Görev |
|---|---|
| `core/` | config (settings.json/token.json okuma), utils (oturum, yardımcılar), version, log_helpers |
| `api/` | Sunucu API istemcisi: `auth`, `books`, `inventory`, `loans`, `logs`, `roles`, `settings`, `students`, `system` |
| `ui/` | Pencere ve diyaloglar |
| `widgets/` | Özel widget'lar (hızlı sonuç paneli, kitap tablosu, nilüfer...) |
| `printing/` | Etiket (`label_maker_qt`, `template_renderer`) ve fiş (`receipt_printer`) yazdırma + `printer_guard` |

## Başlangıç Akışı (main.py)

1. `settings.json`'u okur; sunucu adresi `api.base_url`'den gelir (Ayarlar → Sunucu ile değiştirilebilir).
2. `token.json` varsa otomatik giriş dener; yoksa LoginWindow açar.
3. Giriş: `POST /api/token/` (JWT). Başarıda `token.json`'a yazılır.
4. Ana pencere açılır; geciken ödünçleri tazelemek için `POST /api/jobs/update-overdue/` tetiklenir.

### Oturum Notu (geliştirme davranışı)
- `token.json` varsa login atlanır ve direkt anasayfa açılır.
- Çıkışta `token.json` silinir (debug kapalıysa).
- Oturum sona erdiğinde/broadcast'te LoginWindow yeniden açılır.

## Ana Pencere Arayüzü

Sol taraf menü + içerik alanları. Ana modüller:

- **Hızlı Arama**: Barkod/no/yazar/kitap girişi; `GET /api/fast-query/` sonucunu türüne göre panel gösterir.
- **Kitap Yönetimi**: listeleme, yeni kayıt, düzenleme, sınıflandırma (kategori/yazar), kapak resimleri, raf kodu.
- **Nüsha Yönetimi**: kopya ekleme/çıkarma, barkod, boyut.
- **Öğrenci Yönetimi**: arama, pasife çekme, silme (sadece ödünç yoksa), durum ikonu delegeleri.
- **Ödünç / İade**: okutma akışı, kayıp/hasarlı kontrolleri, ceza diyaloğu.
- **Sayım**: oturum açma, kalem tarama, ilerleme.
- **Ayarlar**: sunucu, ödünç politikası, ceza, bildirim, yazıcı, fiş şablonları.

## Kritik İş Akışları

### Ödünç Verme
1. Okut → `fast-query/` öğrenci eşleşirse: aktif ödünçler, ceza özeti sunulur.
2. İletişim bilgisi eksikse `ContactReminderDialog` → eksik bilgiyi `ContactEditDialog` ile toplar.
3. Rol limiti aşılmışsa `MaxLoansDialog` uyarır.
4. `CheckoutConfirmDialog` onayı → `POST /api/checkout/`.
5. (İsteğe bağlı) Etiket yazdırma sorulur.

### İade / Kayıp / Hasarlı
- `POST /api/oduncler/<id>/` PATCH `durum` → `teslim|kayip|hasarli|iptal`.
- İade alındığında `teslim_tarihi` otomatik UTC now.
- Nüsha durumu da güncellenir: teslim/iptal→`mevcut`, kayıp→`kayip`, hasarli→`hasarli`.
- Kayıp/hasarlıda `LossPenaltyDialog` → kalan ceza `extra_payload` ile `gecikme_cezasi`'ne eklenir.

### Ceza Tahsilatı
- `POST /api/penalties/<id>/pay/` `{"amount": "12.50"}`.
- `penaltyPaid` sinyali yayınlar; gecikme tablosu yenilenir; `fine_payment` fişi yazdırılır.

### Gecikme Tespiti (desktop tarafı)
- Kitap tablosu `oduncler/?durum=oduncte` + `?durum=gecikmis` çeker.
- `effective_due = iade_tarihi + grace + weekend_shift`.
- Satır renklendirme: normal / aktif / uyarı / gecikmiş / kayıp-hasarlı.

## Yazdırma

### Etiket (Barkod)
- `untitled.json` = 55×40 mm @203 dpi şablon (Code128).
- `LabelEditorDialog` ile şablon düzenlenir → `template_renderer.render_template_to_image`.
- `print_label_batch`: LabelWithMark medya, termal 203 dpi, opsiyonel -90°.
- `printer_guard.py`: yazıcı hazır mı, media tipi `LabelWithMark` mi → değilse `lpoptions` ile otomatik düzeltir veya uyarır.

### Fiş (Receipt)
- 70 mm termal, `QPrinter.HighResolution`, `print_*` fonksiyonları.
- Şablonlar `{{ anahtar }}` placeholder'lı; `build_receipt_context(summary)` ile zenginleştirilir.
- Hazır şablonlar: `fine_payment` (ceza tahsilatı, kodda aktif), `debt_statement` ("borcu yoktur" — arayüz bağlantısı yok), `general_notice` (bilgilendirme — arayüz bağlantısı yok).
- `check_receipt_printer_status()` pencerede uyarı bandı gösterir.

## Ayarlar Senkronizasyonu

- Rol ödünç limitleri sunucudan çekilip `settings.json["role_loans"]` içine cache'lenir.
- `PenaltySettingsWidget` ceza rol tablosunu `update_role_loan_policies` ile günceller.
- Bildirim + SMTP + SMS kredileri `settings.json["notifications"]` altında tutulur.

## Ölü Kod (temizlenecek adaylar)
- `printing/label_maker_qt.py` — hiçbir yerden import edilmiyor (eski etiket motoru).
- `printing/receipt_printer_tmp.py` — yedek/deneme fiş kodu.
- `ui/login_window copy.py` — eski login arayüzü kopyası.

## Açık Görevler (desktop taraflı, `todos` 'dan özet)
- FİŞ: "bilgilendirme/genel fiş" ve "borcu yoktur" fişlerinin kullanıcı arayüzünden erişilebilir olması (henüz sadece `fine_payment` tetikleniyor).
- RAPOR: rapor/istatistik sayfası (beraber tasarlanacak).
- İSTATİSTİK: Ayarlar altına gecikme/toplam ceza istatistik sekmesi.
- PAKET: sunucu + masaüstü `.deb` paketi, CI, `.env` ile gizli bilgi yönetimi.
- BİLDİRİM: sms/mail/mobil ayarları kaydediliyor; gerçek gönderim yok (sunucu tarafında `dispatch_notifications` bekleniyor).