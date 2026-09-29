import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../config.dart';
import 'print_fonts.dart';
import 'sablon.dart';

/// Tek fiş satırı. `kod` alanın şablon anahtarıdır (K14.12): boşsa çıktıya
/// koşulsuz girer, doluysa içerik editörü alanı kapatılınca satır düşer.
class ReceiptLine {
  final String text;
  final bool bold;
  final double size;
  final bool center;
  final double spaceAfter;
  final bool divider;
  final String kod;

  const ReceiptLine(
    this.text, {
    this.bold = false,
    this.size = 10,
    this.center = false,
    this.spaceAfter = 2,
    this.divider = false,
    this.kod = '',
  });
}

/// 70 mm termal fiş PDF üretimi (K14).
///
/// İçerik satırları saf Dart'ta üretilir (`build*Fisi(...)`); test edilebilir.
/// `renderReceipt` bunları 70 mm genişliğinde (yükseklik otomatik) PDF yapar.
class ReceiptPdf {
  static const double mm = PdfPageFormat.mm;

  /// Fiş genişliği (mm).
  static const double genislikMm = 70;
  static const double minYukseklikMm = 40;
  static const double kenarMm = 3;

  // ------------------------------------------------------------ ortak başlık

  static List<ReceiptLine> baslik(KurumBilgisi kurum, String unvan) {
    final lines = <ReceiptLine>[];
    final bas = kurum.baslik.trim();
    if (bas.isNotEmpty) {
      lines.add(ReceiptLine(bas,
          bold: true, size: 12, center: true, spaceAfter: 1, kod: 'kurumBasligi'));
    }
    lines.add(ReceiptLine(unvan,
        size: 12,
        center: true,
        bold: true,
        spaceAfter: 6,
        kod: 'unvan'));
    lines.add(const ReceiptLine('', divider: true, spaceAfter: 4, kod: 'unvan'));
    return lines;
  }

  /// Alt bilgi: adres/telefon/e-posta/web **ayrı alanlardır** (K14.12) ve
  /// kırpılmaz; hangilerinin basılacağı içerik editöründe belirlenir.
  static List<ReceiptLine> altBilgi(KurumBilgisi kurum) {
    final lines = <ReceiptLine>[
      const ReceiptLine('', divider: true, spaceAfter: 2, kod: 'altBilgiAyrac'),
    ];
    final alt = <String, String>{
      'adres': kurum.adres,
      'telefon': kurum.telefon.trim().isEmpty
          ? ''
          : 'Tel: ${kurum.telefon.trim()}',
      'eposta': kurum.eposta,
      'website': kurum.website,
    };
    for (final e in alt.entries) {
      final v = e.value.trim();
      if (v.isEmpty) continue;
      lines.add(ReceiptLine(v, size: 8, center: true, spaceAfter: 1, kod: e.key));
    }
    return lines;
  }

  static List<ReceiptLine> _tarihSatiri(String etiket, String deger,
      {String kod = 'tarih'}) {
    return [
      ReceiptLine(
          '${etiket.trim()}: ${deger.trim()}',
          size: 9,
          spaceAfter: 6,
          kod: kod),
    ];
  }

  // ----------------------------------------------------------------- fişler

  static List<ReceiptLine> oduncFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String kitap,
    required String yazar,
    required String barkod,
    required String oduncTarihi,
    required String iadeTarihi,
  }) {
    return [
      ...baslik(kurum, 'ÖDÜNÇ FİŞİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(ogrenci, bold: true, size: 11, spaceAfter: 1, kod: 'ogrenci'),
      if (sinif.trim().isNotEmpty)
        ReceiptLine(sinif, size: 9, spaceAfter: 5, kod: 'sinif'),
      const ReceiptLine('', divider: true, spaceAfter: 3, kod: 'sinif'),
      ReceiptLine(kitap, bold: true, size: 11, spaceAfter: 1, kod: 'kitap'),
      if (yazar.trim().isNotEmpty)
        ReceiptLine(yazar, size: 9, spaceAfter: 1, kod: 'yazar'),
      ReceiptLine('Barkod: ${barkod.trim()}',
          size: 10, spaceAfter: 5, kod: 'barkod'),
      const ReceiptLine('', divider: true, spaceAfter: 3, kod: 'barkod'),
      ..._tarihSatiri('Ödünç', oduncTarihi, kod: 'oduncTarihi'),
      ReceiptLine('İADE TARİHİ: ${iadeTarihi.trim()}',
          bold: true, size: 11, spaceAfter: 6, kod: 'iadeTarihi'),
      ReceiptLine('Operatör: ${operator.trim()}',
          size: 9, spaceAfter: 2, kod: 'operator'),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> iadeFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String kitap,
    required String yazar,
    required String barkod,
    required String durumEtiketi,
    String cezaTutari = '',
    String odemeNotu = '',
  }) {
    return [
      ...baslik(kurum, 'İADE FİŞİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(ogrenci, bold: true, size: 11, spaceAfter: 1, kod: 'ogrenci'),
      if (sinif.trim().isNotEmpty)
        ReceiptLine(sinif, size: 9, spaceAfter: 5, kod: 'sinif'),
      const ReceiptLine('', divider: true, spaceAfter: 3, kod: 'sinif'),
      ReceiptLine(kitap, bold: true, size: 11, spaceAfter: 1, kod: 'kitap'),
      if (yazar.trim().isNotEmpty)
        ReceiptLine(yazar, size: 9, spaceAfter: 1, kod: 'yazar'),
      ReceiptLine('Barkod: ${barkod.trim()}',
          size: 10, spaceAfter: 5, kod: 'barkod'),
      ReceiptLine('İade durumu: ${durumEtiketi.trim()}',
          bold: true, size: 10, spaceAfter: 2, kod: 'durum'),
      if (cezaTutari.trim().isNotEmpty)
        ReceiptLine(cezaTutari, size: 10, spaceAfter: 2, kod: 'ceza'),
      if (odemeNotu.trim().isNotEmpty)
        ReceiptLine(odemeNotu, size: 9, spaceAfter: 2, kod: 'odemeNotu'),
      ReceiptLine('Operatör: ${operator.trim()}',
          size: 9, spaceAfter: 2, kod: 'operator'),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> borcuYoktur({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String aktifOdunc,
  }) {
    return [
      ...baslik(kurum, 'BORÇSÜZLÜK BELGESİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(
          '${ogrenci.trim()}${sinif.trim().isNotEmpty ? ' • ${sinif.trim()}' : ''}',
          bold: true,
          size: 11,
          spaceAfter: 6,
          kod: 'ogrenci'),
      ReceiptLine('Kütüphane kayıtlarımıza göre öğrencinin',
          size: 9, spaceAfter: 1, kod: 'aktifOdunc'),
      ReceiptLine('aktif ödünç sayısı: ${aktifOdunc.trim()}',
          size: 9, spaceAfter: 1, kod: 'aktifOdunc'),
      ReceiptLine('Gecikme borcu: YOKTUR',
          bold: true, size: 11, spaceAfter: 8, kod: 'borcuYoktur'),
      ReceiptLine('İmza/Kaşe:', size: 9, spaceAfter: 10, kod: 'imza'),
      ReceiptLine('Operatör: ${operator.trim()}',
          size: 9, spaceAfter: 2, kod: 'operator'),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> cezaOdemeFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String tutar,
    String kalan = '',
  }) {
    return [
      ...baslik(kurum, 'CEZA TAHSİLAT FİŞİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(
          '${ogrenci.trim()}${sinif.trim().isNotEmpty ? ' • ${sinif.trim()}' : ''}',
          bold: true,
          size: 11,
          spaceAfter: 5,
          kod: 'ogrenci'),
      const ReceiptLine('', divider: true, spaceAfter: 3, kod: 'ogrenci'),
      ReceiptLine('Ödenen tutar: ${tutar.trim()} ₺',
          bold: true, size: 12, spaceAfter: 3, kod: 'tutar'),
      if (kalan.trim().isNotEmpty)
        ReceiptLine('Kalan borç: ${kalan.trim()} ₺',
            size: 10, spaceAfter: 2, kod: 'kalan'),
      ReceiptLine('Operatör: ${operator.trim()}',
          size: 9, spaceAfter: 2, kod: 'operator'),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> sifreFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String kullaniciAdi,
    required String sifre,
  }) {
    return [
      ...baslik(kurum, 'ÜYE GİRİŞ BİLGİLERİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(ogrenci, bold: true, size: 11, spaceAfter: 5, kod: 'ogrenci'),
      const ReceiptLine('', divider: true, spaceAfter: 3, kod: 'ogrenci'),
      ReceiptLine('Kullanıcı adı: ${kullaniciAdi.trim()}',
          bold: true, size: 11, spaceAfter: 2, kod: 'kullaniciAdi'),
      ReceiptLine('Şifre: ${sifre.trim()}',
          bold: true, size: 11, spaceAfter: 6, kod: 'sifre'),
      ReceiptLine('İlk girişte şifrenizi değiştirmeniz istenir.',
          size: 8, center: true, spaceAfter: 2, kod: 'ilkGirisNotu'),
      ReceiptLine('Operatör: ${operator.trim()}',
          size: 9, spaceAfter: 2, kod: 'operator'),
      ...altBilgi(kurum),
    ];
  }

  // --------------------------------------------------------------- PDF üretimi

  /// Şablona göre satır süzme/sıralama (K14.12): kapalı alanlar ve onların
  /// ayraçları düşer, açık alanlar kullanıcı sırasına göre dizilir.
  static List<ReceiptLine> sablonla(
      List<ReceiptLine> lines, String sahne, BasimSablonu sablon) {
    return Sablon.sirala(lines, sahne, sablon, kod: (l) => l.kod);
  }

  /// Fiş satırlarından geçen (tüm alanları açık) en yüksek ölçü — A4'e
  /// sığdırma ölçüsü ve yapısal önizleme aynı satırlardan beslenir (K14.12).
  /// Satır sarması `genislikMm` (varsayılan 70 mm) üzerinden hesaba katılır;
  /// böylece ölçü PDF'in gerçek yüksekliğiyle aynı mantıkta ilerler (R1.10).
  static double sayfaYuksekligiMm(List<ReceiptLine> lines,
      {double kenar = kenarMm, double? genislikMm}) {
    final kullanilabilirMm =
        ((genislikMm ?? ReceiptPdf.genislikMm) - kenar.clamp(0.0, 20.0))
            .clamp(1.0, 1000.0);
    return _toplamYukseklikMm(lines, kenar * mm, kullanilabilirMm * mm);
  }

  /// Satır listesinin toplam yüksekliği (punto). `kullanilabilirPt` null ise
  /// sarma hesaba katılmaz (genişlik bilinmiyor → eski davranış).
  static double _toplamYukseklikMm(
      List<ReceiptLine> lines, double kenarPt, double? kullanilabilirPt) {
    var h = kenarPt * 2;
    for (final l in lines) {
      if (l.divider) {
        h += 3.0 + l.spaceAfter;
        continue;
      }
      final gorsel = kullanilabilirPt == null
          ? 1
          : _tahminiGorselSatir(l.text, kullanilabilirPt, l.size);
      h += gorsel * l.size * 1.35 + l.spaceAfter;
    }
    return h;
  }

  /// Bir fiş satırının kaç görsel satıra saracağını **üst sınır** olarak tahmin
  /// eder (R1.10). Yazı tipi (LiberationSans) sabit aralıklı değildir; karakter
  /// sınıflarına yaklaşık ilerleme genişlikleri (em) kullanılır. Kelime sarması
  /// karakter sarmasından daha az satır üretir; bu yüzden sonuç **fazla** yükseklik
  /// verir → fişin altı kırpılmaz, gerekirse boşluk kalır.
  static int _tahminiGorselSatir(
      String text, double kullanilabilirPt, double fontPt) {
    if (text.isEmpty) return 1;
    if (kullanilabilirPt <= 0) return 1;
    final em = fontPt <= 0 ? 1.0 : fontPt;
    var satirlar = 1;
    var dolu = 0.0;
    for (final rune in text.runes) {
      final cw = em * _emGenislik(String.fromCharCode(rune));
      if (dolu + cw > kullanilabilirPt) {
        satirlar++;
        dolu = cw;
      } else {
        dolu += cw;
      }
    }
    return satirlar;
  }

  /// Yaklaşık karakter ilerleme genişliği (em) — LiberationSans/Arial metrikleri.
  static double _emGenislik(String ch) {
    const darKume = ' .,:;\'!|iljftr()[]{}-';
    const genisKume = 'mwMW@';
    const rakamKume = '0123456789';
    const buyukKume = 'ABCDEFGHJKLNOPQRSTUVXYZ';
    const kucukKume = 'abcdeghknopsuvxyz';
    if (darKume.contains(ch)) return 0.30;
    if (genisKume.contains(ch)) return 0.83;
    if (rakamKume.contains(ch)) return 0.56;
    if (buyukKume.contains(ch)) return 0.68;
    if (kucukKume.contains(ch)) return 0.55;
    return 0.55;
  }

  /// Sayfa ölçüleri (punto). `render` bunu kullanır; testler de "fiş genişliği
  /// verilen mm'ye uyuyor mu / sarma yüksekliğe yansıyor mu" kontrolünü buradan
  /// yapar (PDF sıkıştırıldığı için MediaBox ham baytlarda okunamaz).
  static ({double genislikPt, double yukseklikPt}) sayfaOlculeriPt(
      List<ReceiptLine> lines,
      {double? genislikMm, double kenar = kenarMm}) {
    final w = (genislikMm ?? ReceiptPdf.genislikMm) * mm;
    final margin = kenar.clamp(0.0, 20.0) * mm;
    final h = _toplamYukseklikMm(lines, margin, w - margin * 2);
    final minH = minYukseklikMm * mm;
    return (genislikPt: w, yukseklikPt: h < minH ? minH : h);
  }

  /// Fiş satırlarını fiş genişliğinde PDF yapar (yükseklik içeriğe göre).
  /// `genislikMm` verilmezse varsayılan 70 mm (K14.8), `kenar` içerik kenar
  /// boşluğudur (K14.12, 0–8 mm). Yükseklik dar ruloda satır sarmasını hesaba
  /// katarak büyür (R1.10).
  static Future<List<int>> render(List<ReceiptLine> lines,
      {double? genislikMm, double kenar = kenarMm}) async {
    final regular = await PrintFonts.regular();
    final bold = await PrintFonts.bold();

    final o = sayfaOlculeriPt(lines, genislikMm: genislikMm, kenar: kenar);
    final w = o.genislikPt;
    final margin = kenar.clamp(0.0, 20.0) * mm;
    final pageH = o.yukseklikPt;

    final children = <pw.Widget>[];
    for (final l in lines) {
      if (l.divider) {
        children.add(pw.Container(
            height: 2,
            margin: const pw.EdgeInsets.symmetric(vertical: 1),
            color: PdfColors.black));
        continue;
      }
      final text = pw.Text(l.text,
          style: pw.TextStyle(font: l.bold ? bold : regular, fontSize: l.size));
      children.add(pw.Container(
        alignment: l.center ? pw.Alignment.center : pw.Alignment.centerLeft,
        margin: pw.EdgeInsets.only(bottom: l.spaceAfter),
        child: text,
      ));
    }

    final doc = pw.Document();
    doc.addPage(pw.Page(
      pageFormat: PdfPageFormat(w, pageH, marginAll: margin),
      build: (_) => pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.stretch,
        mainAxisSize: pw.MainAxisSize.min,
        children: children,
      ),
    ));
    return doc.save();
  }
}