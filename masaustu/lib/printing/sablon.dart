import '../config.dart';

/// Fiş sahnesi (K14.12).
enum Sahne {
  odunc('Ödünç Fişi', 'odunc'),
  iade('İade Fişi', 'iade'),
  sifre('Şifre Fişi', 'sifre'),
  borcuYoktur('Borcu Yoktur', 'borcuYoktur'),
  ceza('Ceza Tahsilat', 'ceza'),
  etiket('Etiket', 'etiket');

  const Sahne(this.ad, this.kod);

  /// Ekranda gösterilen ad.
  final String ad;

  /// `config.json` içindeki anahtar.
  final String kod;

  static Sahne? byKod(String kod) {
    for (final s in Sahne.values) {
      if (s.kod == kod) return s;
    }
    return null;
  }
}

/// Editörde listelenen tek alan (K14.12).
class Alan {
  /// Alan kodu — basım satırlarının `kod` etiketiyle eşleşir.
  final String kod;

  /// Ekranda gösterilen ad.
  final String etiket;

  /// Önizlemede örnek değer.
  final String ornek;

  /// Zorunlu alan kapatılamaz (anahtar ikonlu).
  final bool zorunlu;

  const Alan(this.kod, this.etiket, this.ornek, {this.zorunlu = false});
}

/// Alt bilgi (iletişim) satırları — etiket/ayraç kuralı bunlara bağlıdır.
const Set<String> altBilgiKodlari = {'adres', 'telefon', 'eposta', 'website'};

/// Sahneye göre alan katalogları (K14.12). Varsayılan sıra = bugünkü çıktı sırası.
class Sablon {
  const Sablon._();

  static const _kurum = Alan('kurumBasligi', 'Kurum başlığı', 'Okul Kütüphanesi');
  static const _unvan = Alan('unvan', 'Fiş başlığı', 'ÖDÜNÇ FİŞİ', zorunlu: true);
  static const _tarih = Alan('tarih', 'Tarih / saat', '27.09.2026 22:31');
  static const _ogrenci = Alan('ogrenci', 'Öğrenci adı soyadı', 'Ali Yılmaz', zorunlu: true);
  static const _operator = Alan('operator', 'Operatör', 'Kütüphane Personeli');
  static const _adres = Alan('adres', 'Alt bilgi: adres', 'Atatürk Mah. Gazi Cad. No:1');
  static const _telefon = Alan('telefon', 'Alt bilgi: telefon', 'Tel: 0 312 123 45 67');
  static const _eposta = Alan('eposta', 'Alt bilgi: e-posta', 'kutuphane@okul.edu.tr');
  static const _website = Alan('website', 'Alt bilgi: web sitesi', 'www.okul.edu.tr');

  static const List<Alan> _ortakAlt = [_adres, _telefon, _eposta, _website];

  static const Map<String, List<Alan>> katalog = {
    'odunc': [
      _kurum,
      _unvan,
      _tarih,
      _ogrenci,
      Alan('sinif', 'Sınıf', '10-A'),
      Alan('kitap', 'Kitap adı', 'Sefere Seven Yedi Kule', zorunlu: true),
      Alan('yazar', 'Yazar', 'Tolga Özçelik'),
      Alan('barkod', 'Barkod (yazı)', 'B-2026-000123', zorunlu: true),
      Alan('oduncTarihi', 'Ödünç tarihi', 'Ödünç: 27.09.2026'),
      Alan('iadeTarihi', 'İade tarihi (vurgulu)', 'İADE TARİHİ: 11.10.2026',
          zorunlu: true),
      _operator,
      ..._ortakAlt,
    ],
    'iade': [
      _kurum,
      _unvan,
      _tarih,
      _ogrenci,
      Alan('sinif', 'Sınıf', '10-A'),
      Alan('kitap', 'Kitap adı', 'Sefere Seven Yedi Kule', zorunlu: true),
      Alan('yazar', 'Yazar', 'Tolga Özçelik'),
      Alan('barkod', 'Barkod (yazı)', 'B-2026-000123', zorunlu: true),
      Alan('durum', 'İade durumu', 'İade durumu: Zamanında'),
      Alan('ceza', 'Gecikme cezası', 'Gecikme cezası: 12,00 TL'),
      Alan('odemeNotu', 'Ödeme notu', 'Ceza tahsil edildi: 12,00 TL'),
      _operator,
      ..._ortakAlt,
    ],
    'sifre': [
      _kurum,
      _unvan,
      _tarih,
      _ogrenci,
      Alan('kullaniciAdi', 'Kullanıcı adı', 'Kullanıcı adı: 2026-0145', zorunlu: true),
      Alan('sifre', 'Geçici şifre', 'Şifre: A7k92p', zorunlu: true),
      Alan('ilkGirisNotu', 'İlk giriş notu', 'İlk girişte şifrenizi değiştirin.'),
      _operator,
      ..._ortakAlt,
    ],
    'borcuYoktur': [
      _kurum,
      _unvan,
      _tarih,
      _ogrenci,
      Alan('aktifOdunc', 'Aktif ödünç sayısı', 'aktif ödünç sayısı: 3', zorunlu: true),
      Alan('borcuYoktur', 'Borç durumu (vurgulu)', 'Gecikme borcu: YOKTUR', zorunlu: true),
      Alan('imza', 'İmza / kaşe satırı', 'İmza/Kaşe:'),
      _operator,
      ..._ortakAlt,
    ],
    'ceza': [
      _kurum,
      _unvan,
      _tarih,
      _ogrenci,
      Alan('tutar', 'Ödenen tutar (vurgulu)', 'Ödenen tutar: 25,00 TL', zorunlu: true),
      Alan('kalan', 'Kalan borç', 'Kalan borç: 5,00 TL'),
      _operator,
      ..._ortakAlt,
    ],
    'etiket': [
      _kurum,
      Alan('baslik', 'Kitap adı', 'Sefere Seven Yedi Kule', zorunlu: true),
      Alan('yazar', 'Yazar', 'Tolga Özçelik'),
      Alan('kategori', 'Kategori', 'Genel'),
      Alan('barkodMetni', 'Barkod yazısı', 'B-2026-000123', zorunlu: true),
      Alan('barkodCubugu', 'Barkod çubuğu', '(Code-128 çubuk)', zorunlu: true),
    ],
  };

  /// Bir sahnenin alanları (tanımsız sahne için boş liste).
  static List<Alan> alanlar(String sahne) => katalog[sahne] ?? const [];

  static Alan? alan(String sahne, String kod) {
    for (final a in alanlar(sahne)) {
      if (a.kod == kod) return a;
    }
    return null;
  }

  /// Kullanıcı seçimi + katalog birleşimi: sırayı kullanıcı belirler, eksik
  /// alanlar katalog sırasında ve varsayılan **açık** olarak sona eklenir;
  /// bilinmeyen kodlar yok sayılır; zorunlu alanlar her zaman açıktır.
  static List<SahneAlanDurumu> durum(String sahne, BasimSablonu sablon) {
    final katalogAlanlari = alanlar(sahne);
    final secim = <String, bool>{};
    for (final d in sablon.alan(sahne)) {
      if (alan(sahne, d.kod) != null) secim[d.kod] = d.acik;
    }
    final sonuc = <SahneAlanDurumu>[];
    for (final d in sablon.alan(sahne)) {
      if (alan(sahne, d.kod) != null) {
        sonuc.add(SahneAlanDurumu(d.kod,
            acik: alan(sahne, d.kod)!.zorunlu ? true : d.acik));
      }
    }
    for (final a in katalogAlanlari) {
      if (!secim.containsKey(a.kod)) {
        sonuc.add(SahneAlanDurumu(a.kod));
      }
    }
    return sonuc;
  }

  /// Sahnede açık alan kodları (katalog sırasında).
  static Set<String> acikKodlar(String sahne, BasimSablonu sablon) => durum(
        sahne,
        sablon,
      ).where((d) => d.acik).map((d) => d.kod).toSet();

  /// Satır listesini şablona göre süzer/sıralar (K14.12).
  ///
  /// - Kapalı alanın satırları **ve o alana ait ayraç** düşer.
  /// - Alt bilgi ayracı, alt bilgi alanlarından en az biri açıksa korunur.
  /// - `kod` etiketi olmayan satırlar (gövde/ayraç) sona eklenir.
  /// - Sıra kullanıcının belirlediği sırayla katalog sırasının birleşimidir.
  static List<T> sirala<T>(
    List<T> satirlar,
    String sahne,
    BasimSablonu sablon, {
    required String Function(T) kod,
  }) {
    if (alanlar(sahne).isEmpty) return List<T>.of(satirlar);
    final acik = acikKodlar(sahne, sablon);
    final altBilgiAcik = acik.any(altBilgiKodlari.contains);
    final kova = <String, List<T>>{};
    final etiketsizler = <T>[];

    for (final s in satirlar) {
      final k = kod(s);
      if (k.isEmpty) {
        etiketsizler.add(s);
        continue;
      }
      if (k == 'altBilgiAyrac') {
        if (altBilgiAcik) (kova['altBilgiAyrac'] ??= []).add(s);
        continue;
      }
      if (alan(sahne, k) == null) {
        // Katalogda olmayan kod: içerik kaybı olmasın diye korunur.
        etiketsizler.add(s);
        continue;
      }
      if (!acik.contains(k)) continue;
      (kova[k] ??= []).add(s);
    }

    final sira = durum(sahne, sablon).map((d) => d.kod).toList();
    final sonuc = <T>[];
    var altBilgiAyracEklendi = false;
    for (final k in sira) {
      if (!acik.contains(k)) continue;
      if (altBilgiKodlari.contains(k) && !altBilgiAyracEklendi) {
        altBilgiAyracEklendi = true;
        sonuc.addAll(kova['altBilgiAyrac'] ?? const []);
      }
      sonuc.addAll(kova[k] ?? const []);
    }
    sonuc.addAll(etiketsizler);
    return sonuc;
  }
}
