# CHANGELOG

Bu proje [Semantic Versioning](https://semver.org/) benzeri bir düzen kullanır:
`MAJOR.MINOR.PATCH`. Yayınlar git etiketiyle (`vX.Y.Z`) işaretlenir ve
sunucuya yalnızca etiketli sürümler gönderilir (bkz. `docs/DEPLOY_CLOUD.md`).

## [Unreleased]

## [1.1.15] — 2026-09-29

Yazıcı rozeti, etiket kalibrasyon yönergesi ve kapalı yazıcı uyarısı
(**yalnızca masaüstü istemcisi**; backend değişmedi, sunucuya deploy gerekmez).

- **R1.13 — Kuyruk rozeti yanıltıcıydı:** A4 yazıcısı açılır kutudan seçilmiş
  olmasına rağmen rozet "Seçilmedi" diyordu. Kayıtlı kuyruk adı CUPS'taki
  gerçek adla birebir karşılaştırılıyordu (`HP-LaserJet-1020` ≠
  `Hewlett-Packard-HP-LaserJet-1020`); küçük/harf ve boşluk farkı yok sayılmıyor.
  Seçili ama listede olmayan kuyruk artık **"Bulunamadı"** (kırmızı) gösteriyor ve
  tek ve açık bir eşleşme varsa **"Düzelt: …"** düğmesi çıkıyor.
- **R1.14 — "Etiketi taktım" sonrası kalibrasyon yönergesi:** Uygulama gap'i
  göndermediği (K14.11) için etiket değişince yazıcının kendi sensörü
  kalibrasyonu gerekiyordu; bu yalnız ayarlar ekranındaki bilgi kutusunda
  vardı. Artık **"Etiket rulosu taktım"** bildiriminden sonra kalibrasyon
  penceresi açılıyor: Tazga/4B gibi modellerde **LED mavi** (fabrika ayarı) ve
  **LED kırmızı** (gap/black-mark kalibrasyonu) adımları, diğer modellerde
  genel yönerge. Fiş bildiriminde pencere açılmaz (fişe dönüşte kalibrasyon
  gerekmez). Model `lpoptions` üzerinden okunur (`printer-make-and-model`).
- **R1.15 — Kapalı yazıcıda kuyruğa eklememe:** Yazıcı kapalı/bağlı değilken
  `lp` işi kabul edip kuyrukta bekletiyordu; uygulama "Yazdırıldı" deyip
  kâğıt çıkmıyordu. Artık kuyruk listesi alınabiliyorsa ve yazıcı çıkış
  yapamıyorsa iş hiç gönderilmiyor, "Yazıcıya ulaşılamıyor: … (devre dışı).
  Yazıcıyı açıp USB kablosunu kontrol edin" uyarısı veriliyor. Başarı mesajı
  "Yazdırıldı" yerine **"Yazıcıya iletildi (kuyruğa alındı)"**. Kuyruk listesi
  alınamıyorsa basım engellenmiyor.
- Testler: 9 yeni test (rozet/düzeltme, kalibrasyon penceresi, kapalı yazıcı);
  toplam 117 test.

## [1.1.14] — 2026-09-29

Termal rulo ölçüleri: fiş genişliği 55 mm'de de kullanılabilir ve ölçü
değişiklikleri artık kaybolmaz (**yalnızca masaüstü istemcisi**; backend
değişmedi, sunucuya deploy gerekmez).

- **R1.9 — Ayarlarda kaydetme tutarlılığı:** Açılır listeler/anahtarlar anında
  kaydedilirken ölçü alanlarının yalnızca "Rulo ayarlarını kaydet" ile
  kaydedilmesi "otomatik kaydediliyor" izlenimi bırakıyor ve kullanıcı fişi 55
  yazdığı hâlde 70 mm'de çıkıyordu. Artık **Enter**, **alandan çıkış** (odak
  kaybı) ve düğme aynı şekilde kaydeder; kaydedilmemiş değişiklik varken ekranda
  uyarı görünür ve düğme etkinleşir, temiz durumda pasiftir. Geçersiz/eksik giriş
  kaydedilen değere döner; virgüllü ondalık (`55,5`) kabul edilir.
- **R1.10 — Fiş genişliği ve satır sarması:** Fiş genişliği serbest mm değeri
  olarak **55 mm'de de çalışır**; değer PDF sayfa genişliğine, `lp -o
  media=Custom.WxHpt` ile yazıcıya bildirilen özel kağıda ve sayfa yüksekliği
  hesabına akar. Sayfa yüksekliği artık **satır sarmasını hesaba katar**
  (LiberationSans için yaklaşık karakter genişlikleriyle **üst sınır**
  tahmini → taşma yerine fazla boşluk): dar ruloda uzun kitap adı/kullanıcı satırı
  ikinci satıra sarıp fişin altının kırpılmasını engeller. Kağıt tipi/gap hâlâ
  yazıcının sensör kalibrasyonundadır.
- **R1.11 — Fişte alt boşluk (gerçek sayfa yüksekliği):** Sayfa yüksekliği
  tahminle hesaplanıyordu (satır aralığı katsayısı + sarma üst sınırı) ve 55 mm
  fişte **~16 mm** gereksiz alt boşluk bırakıyordu; kullanıcı fişi kısa
  görüyordu. Artık sayfa, **PDF'in gerçek dikey kullanımı ölçülerek** belirlenir:
  içerik sıkıştırılmamış, çok uzun bir ölçüm sayfasına basılır, yalnız içerik
  akışındaki `cm/Td/Tm/Tf/re` konumları okunup gerçek tepe/dip bulunur ve asıl
  sayfa buna göre kırpılır. Ölçüm başarısız olursa eski tahmine düşülür.
  Ölçüm sırasında **gömülü fontun ham baytları taranmaz** (sadece `/Contents`
  akışı okunur). Ayrıca ayraç satırlarının `spaceAfter` boşluğu hiç uygulanmıyordu,
  düzeltildi. 55 mm fiş **92.4 mm → 82.4 mm**; fiziksel ölçümde üst boşluk
  **5 mm**, alt boşluk **≤5 mm** (hedef 1.5 cm).
- **R1.12 — Termal rulo kip ve kırmızı ışık:** 4B-2074C'nin kuyruk varsayılanı
  `PaperType=Normal` (etiket/gap kipi); sonsuz rulo ile basılınca **gap sensörü
  bulunamayınca kırmızı LED yanıp sönüyor** ve basım güç döngüsü gerektiriyordu.
  Fiş basımı artık `PaperType=Continue` ile gider; PPD bu seçeneği bilmiyorsa
  `lp` hata döndürür, uygulama seçeneksiz tekrar dener. `GapsHeight` ve
  `PostAction` gönderilmez — **`TearOff` kalmalı**: `PostAction=None` denendi,
  fiş kesme yerinin arkasında kaldı ve kesilemedi.
- Ölçü değişiklikleri kaydedilmediğinde fişler 70 mm üretiliyordu; artık
  değişiklik yazıldığı anda `config.json`'a yazılır ve yeniden açılışta korunur.
- Testler: 3 yeni test (ölçüm sıkılığı, `PaperType` geçişi); toplam 108 test.

## [1.1.13] — 2026-09-28

Barkod okutma odak kilidi (**yalnızca masaüstü istemcisi**; backend değişmedi,
sunucuya deploy gerekmez).

- **R1.8 — Barkod okutma odak kilidi:** Barkod okuyucu klavye emülasyonudur (kodu
  harf harf + Enter yazar) ve Flutter tuşları **odaklı widget'a** verir. Kullanıcı
  Genel Bakış'ta bir karta/satıra/butona tıklayınca odak hızlı işlem alanından
  gidiyor ve sonraki okutmalar **sessizce kayboluyordu**. Artık **Genel Bakış hızlı
  işlem**, **Ödünç/İade arama** ve **Kitaplar arama** alanları görünürken odağını
  korur; odak kaybında post-frame'da geri verilir (sessiz, görsel uyarı yok).
  Geri verilmez: diyalog/kilit ekranı açıkken (üye no penceresi, iade/ceza diyaloğu,
  açılan detay ekranı odak kendisindendir), alan `enabled: false` iken (işlem sürüyor),
  ekran menüsü açıkken ve uygulama arka plandayken; alt-tab'dan dönünce `resumed`
  ile odak yeniden verilir. **Üyeler listesi araması kilitlenmez** (öğrencide barkod
  yoktur, numara elle girilir); Katalog ve Ayarlar'da da kilit yoktur.
- Yeni `masaustu/lib/widgets/odak_kilidi.dart` (`OdakKilitli`); `loan_screen.dart`
  ve `book_list_screen.dart` alanlarına `FocusNode` + kilit.
- Testler: 8 yeni test (5 birim + 3 ekran kablolaması); toplam 93 test.

## [1.1.12] — 2026-09-28

Öğrenci listesi içe aktarımı ve Türkçe arama düzeltmeleri. Masaüstü istemcisi
değişmedi (istemci güncelleme kontrolü sürüm koduna baktığı için yeniden derleme
gerekmez; `surumKodu` 3'te kalındı).

- **R1.6 — Türkçe metin araması:** Öğrenci listesi yükseltildi. Sayım (envanter)
  ekranındaki kitap adı araması, başlığında "İ" bulunan 207 kitapta (`"İnsan Olmak"`)
  hiç sonuç vermiyordu — Django `__icontains` filtresini
  `UPPER(sütun) LIKE UPPER(aranan)` olarak deriyor, `UPPER('i') = 'I'` olduğu için
  noktalı `İ` ile küçük `i` eşleşmiyordu. Arama artık fold edilmiş `arama` alanından
  yapılıyor; barkod/raf kodu araması korundu. Kural `docs/IS_KURALLARI.md` → R1.6'ya
  işlendi (Türkçe metin alanında doğrudan `__icontains` kullanılmaz).
- **R1.7 — Türkçe baş harf normalizasyonu:** e-okul listeleri büyük harfli geliyordu
  (`YILDIRIM KIZIL`). `turkish.bas_harf_buyut()` ile ad/soyad Türkçe baş harf
  biçimine çevrilir (`i→İ`, `ı→I`; `I→ı`, `İ→i`) — `İSMAİL→İsmail`,
  `YILDIRIM→Yıldırım`, `KIZIL→Kızıl`. Toplu içe aktarmada (K9.13) uygulanır ve
  **önizlemede normalize hâli görünür**; mevcut kayıtlar için
  `manage.py uye_adlari_normalize` komutu eklendi (atomik, idempotent, `--dry-run`).
- **Testler:** 3 yeni test sınıfı, 6 yeni test (baş harf dönüşümleri, öğrenci arama
  anahtarı, sayım ekranı araması, içe aktarmada isim normalizasyonu); toplam 146 test.

## [1.1.11] — 2026-09-27

Masaüstünde **yazıcı / fiş / etiket** alt yapısı ve içerik editörü eklendi (K14.1–K14.12) — CUPS
`lp`/`lpstat` üzerinden, hiçbir yazıcı adı sabit değil; kuyruklar açılışta algılanır,
Ayarlar›Yazıcılar'dan seçilir ve "Test et" ile doğrulanır. Kütüphane bilgisayarındaki
aynı kurulu pakette de çalışır. Fiş/etiket **ortak termal yazıcıda** rulo yönetimiyle,
A4 çıktısı ise "Dosyaya yaz" rotasıyla çalışır — backend/rules değişmedi.

- **Kurum bilgisi + yazıcı seçimi (K14.1, K14.5):** fiş/etiket başlığı ve iletişim
  `KurumAyarlari`'ndan (çekilemezse yerel yedek); canlı kuyruk listesi (`lpstat -p`) +
  durum, fiş/etiket/A4 seçimi, otomatik fiş anahtarları, fiş/etiket/A4 için **test basımı**.
- **Fiş basımı (K14.2, K14.3, K14.7):** ödünç ve iade anında otomatik fiş; Şifre Ver'de
  otomatik **şifre fişi**; öğrenci detayından manuel **"Borcu yoktur"** belgesi ve **ceza
  ödeme fişi**. Fiş 70 mm termal, başlık/iletişim `KurumAyarlari`'ndan.
- **Etiket basımı (K14.4):** kitap detay›nüsha satırında tek tek, çoklu seçim + toplu,
  ve nüsha eklenince "etiket basılsın mı?" önerisi. 57×40 mm, **Code-128** barkod.
- **Açılış denetimi (K14.6):** `NotificationSettings.printer_warning_enabled` açıkken
  seçili fiş yazıcısı hazır değilse engelleyici olmayan uyarı.
- **Ortak rulo durumu + kalıcı çip (K14.9):** fiş ve etiket aynı termal yazıcıya
  atanmışsa üst çubukta "Fiş rulosu / Etiket rulosu / Pasif / Tanımlı Değil" durumu
  her ekranda görünür; tıklayınca hızlı rulo değiştirme menüsü. Rulo uyuşmazlığında
  veya `tanımsız` durumda basım öncesi onay diyaloğu («X rulosu taktım → yazdır» /
  «Vazgeç»); yazıcı pasifse «Yine de dene». Ayrı yazıcılar seçiliyse bu akış kapalıdır.
- **Kağıt tipi zorlanmaz, cihaz kalibrasyonu esas alınır (K14.11):** uygulama
  `PaperType`/`GapsHeight` göndermez; ne job'a (`lp -o`) ne kuyruk varsayılanına
  (`lpadmin`) kağıt tipi yazılmaz, basımda yalnız PDF sayfa ölçüsü verilir. Gerekçe:
  4B-2074C gibi termal yazıcılar etiket uzunluğu/boşluğu kendi sensör kalibrasyonuyla
  ölçer ve `SIZE`/`GAP` değerlerini kendi belleğine yazar; zorlama etiketi iki etikete
  bölüyor ("biri yarım kaldı, diğerine yazdı") ve kalibrasyonu bozuyordu. Ayarlar›Yazıcılar›
  **Termal rulo** bölümü yalnız ölçüleri (etiket genişlik/yükseklik, fiş genişliği — PDF
  yerleşimi için) tutar; gap/kağıt türü alanları kaldırıldı. Kayma/boşluk hataları için
  markadan bağımsız **kalibrasyon bilgi kutusu** eklendi (ayrıntılı 4B-2074C adımları
  `docs/IS_KURALLARI.md`'de).
- **A4 "Dosyaya yaz" (K14.10):** A4 yazıcı seçimine «Dosyaya yaz (PDF)» seçeneği;
  A4 kuyruğu boş/pasifse çıktı otomatik dosya kaydetme diyaloğuna düşer. "Test A4"
  de bu rotadan çalışır (dosya yolu ekranda bildirilir).
- Taşınabilirlik: `uzaktan-kur.sh` eksik `cups-client`/`cups` paketini otomatik kurar;
  `pdf` paketi saf Dart (sistem paketi gerektirmez), PDF yazı tipleri uygulamayla birlikte
  gelir.
- **Fiş/etiket içerik editörü (K14.12):** Ayarlar›**Basım Şablonları** sekmesinde
  ödünç/iade/şifre/borcu yoktur/ceza fişleri ve etiket için hangi satırların
  basılacağı seçilir: alan **açılır/kapanır** (zorunlu alanlar kilitli — unvan,
  öğrenci, kitap, barkod, iade tarihi, şifre, tutar, etiket barkodu) ve
  **sıralanabilir**; fiş/etiket **kenar boşluğu** (0–8 mm) ayarlanır. Önizleme
  basımdaki satır listesinin aynısından üretilir (yapısal); doğrulama için
  "Test bas" kullanılır. Tercihler kütüphane bilgisayarında yerel saklanır
  (`config.json` → `sablon`), backend değişmez. Alan kapanınca ona ait ayraç çizgisi
  de düşer; alt bilgide adres/telefon/e-posta/web artık **dördü de** basılabilir
  (önceden ilk iki kaynak kırpılıyordu).

## [1.1.10] — 2026-09-27

Web katalog yenilendi, üye kitap gezintisi elden geçirildi ve oturum süresi
hatası düzeltildi. Mobil sürüm **1.1.6** (`surumKodu` 6) olarak yayınlandı.

- **Yazar seçimi düzeltmesi (K9.9):** A–Z şeridiyle bir harfe atlanınca, sabitlenen
  harf başlıkları üst üste yığılıp yazar listesini aşağı itiyor ve listeye
  ulaşılamıyordu; sabitlenen başlıklar kaldırıldı (başlıklar artık normal satır),
  şeritle atlama ve arama sorunsuz çalışır.
- **Güncelleme bildirimi düzeltmesi (K13.4):** güncelleme diyaloğu MaterialApp'ın
  **üstündeki** kök context ile açıldığından `Navigator` bulunamıyor ve diyalog
  hiç görünmüyordu; `MaterialApp.navigatorKey` üzerinden gösterilecek şekilde
  düzeltildi (açılışın yanında regresyon testi eklendi).
- **Yazar seçimi (K9.9):** çok uzun yazar listesi çekmeceden çıkarılıp **tam ekran
  "Yazar seç" ekranına** taşındı: Türkçe alfabetik gruplar, sabit harf başlıkları,
  sağ kenarda **A–Z şeridi** (dokun/kaydır ile atlama) ve arama. API yazarları
  artık alfabetik döndürür (`YazarViewSet`).
- **Genel web katalog (K11.1):** kategori ve yazar filtreleri arama çubuğundan
  **yan panellere** taşındı (kategoriler solda, yazarlar sağda; dikey kayan,
  seçili vurgulu bağlantı listeleri). Dar ekranda paneller gizlenir ve
  kenardan açılan **çekmece** olur. Arama çubuğu genişledi; başlık/üst alan
  **kurum verisiyle** (`KurumAyarlari`: kütüphane adı, okul adı, logo) doldurulur.
- **Üye kitap gezintisi (K9.9):** kategori/yazar filtreleri kitap alanını daraltan
  çip satırından **sol taraftan açılan otomatik gizlenen çekmeceye** taşındı
  (Kategoriler ve Yazarlar dokununca açılıp kapanan bölümler). Liste görünümü
  **iki satırlı yatay ızgaraya** çevrildi; kapak ızgarası aynı kaldı.
- **Oturum süresi hatası düzeltildi (K9.11):** access token ömrü 15 dk, refresh
  30 gün (`settings.SIMPLE_JWT`). Mobil istemci 401'de refresh ile otomatik
  yenileyip isteği tekrarlar (önceden 5 dk'da bir zorla çıkış yapıyordu).
  "Beni hatırla" kapalı süresi 12 saat → **15 dk** (kurala uygun). Arka plana
  alınınca "son aktiflik" güncellenir.

## [1.1.9] — 2026-09-26

Masaüstü uzaktan kurulumda sistem bağımlılığı yönetimi.

- `uzaktan-kur.sh`: sistem bağımlılığı kontrolü (GTK3 **soname**; parolasız sudo
  varsa otomatik kurar, yoksa komut önerir). `MASAUSTU_BAGIMLILIK=0` ile kapatılır;
  `MASAUSTU_EK_PAKETLER` (ör. termal yazıcı için `libusb-1.0-0`) ile genişletilir.
  Uygulama önceden derlendiğinden hedef makinede **Flutter gerekmez**.
- `mobil/yukle_apk.sh`: indirme sayfası metni sunucu adresinin otomatik seçildiğini belirtir.
- Doküman: `MASAUSTU_YAYIN.md` Bağımlılıklar bölümü; K13.10 güncellendi.

## [1.1.8] — 2026-09-26

Alan adı (`okulkitapligi.tr`) hazırlığı + akıllı sunucu adresi.

### Mobil + masaüstü
- **Akıllı sunucu adresi (K13.11):** açılışta adaylar paralel yoklanır
  (`https://okulkitapligi.tr` → `http://89.252.153.171`); kayıtlı/çalışan adres
  korunur, hiçbiri yoksa kullanıcıdan istenir. Alan adı + SSL aktif olunca
  uygulama güncellenmeden otomatik geçer.
- Mobil varsayılanı `https://okulkitapligi.tr`; eski LAN adresi kaldırıldı.
- Android: `usesCleartextTraffic=true` (HTTPS öncesi http fallback, K13.12).
- Mobil sürüm `1.1.5+2`, masaüstü `1.1.8+2`.
- Testler: `sunucu_adresi_test.dart` (mobil + masaüstü).

### Masaüstü dağıtım
- **Tek komutla kurulum (K13.10):** `GET /masaustu/uzaktan-kur.sh` sunucu
  adaylarını deneyip paketi indirir, kurar; `MASAUSTU_ORIGIN` ile adres zorlanır.
- `yukle_masaustu.sh` artık `uzaktan-kur.sh`'ı da yayınlar; indirme sayfasına
  tek-komut satırı eklendi.

### Doküman
- `IS_KURALLARI.md` K13.10–K13.12; `MASAUSTU_YAYIN.md` + `MOBIL_YAYIN.md` güncellendi.

## [1.1.7] — 2026-09-26

Masaüstü (Linux) uygulaması için sunucudan otomatik güncelleme (K13.6–K13.9).

### Backend
- `GET /api/masaustu/surum/` (auth'suz): `MASAUSTU_DIST_DIR/surum.json`'dan sürüm
  bilgisi döner (`surum`, `surumKodu`, `minSurumKodu`, `url`, `sha256`); yoksa 404.
- `settings.MASAUSTU_DIST_DIR`; ortak `_SurumView` tabanına geçildi.
- Testler: `MasaustuSurumApiTests` (3).

### Masaüstü
- Açılışta sürüm kontrolü; zorunlu/opsiyonel bildirim.
- Otomatik güncelleme: paket indirme + **sha256** doğrulama + uygulama kapanınca
  kurulum klasörünü değiştirme ve yeniden başlatma (yalnız `~/.local/share/kutuphane-masaustu`).
- `--dart-define=APP_VERSION/APP_VERSION_CODE` ile sürüm; `crypto` bağımlılığı.
- Testler: `update_service_test.dart`.

### Dağıtım / doküman
- `masaustu/kur.sh` (kurulum + `.desktop`), `masaustu/yukle_masaustu.sh`
  (release derle + paketle + yükle + sha256).
- Sunucu: `/srv/kutuphane-masaustu/` + nginx `/masaustu/`; `MASAUSTU_DIST_DIR` env.
- `docs/MASAUSTU_YAYIN.md`; `IS_KURALLARI.md` K13.6–K13.9.

## [1.1.6] — 2026-09-26

Katalog sayfasına mobil uygulama kurulum bağlantısı.

### Web
- `katalog.html`: footer'a "Mobil Uygulama" bağlantısı; telefon ekranlarında
  (`max-width: 680px`) arama kutusunun altında belirgin **"Mobil Uygulamayı İndir"**
  düğmesi → `/mobil/` (göreli bağlantı, IP/alan adından bağımsız).

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
